"""Quality-fingerprint diff tests — the cross-variant FALSE-FLAG safeguard. No LLM.

The scenario these exist for: a seller films ONE listing video (a black kurti) but sells the
same kurti in blue. A buyer disputes the BLUE one. Naive frame-vs-frame comparison reports
"different colour -> different product" and false-flags an honest seller.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.services import quality_fingerprint as qf
from app.services.rules import QUALITY_DIVERGENCE_SHARE, QUALITY_INVARIANT_ATTRS

# a real pure-cotton kurti as filmed by the seller (the BLACK variant)
COTTON_REF = {
    "weave_structure": "woven, tight plain weave",
    "surface_sheen": "matte",
    "fibre_texture": "fibrous",
    "opacity": "opaque",
    "stitch_quality": "dense even seams",
    "drape": "structured",
    "embellishment_type": "block print",
    "colour": "black",
    "shade": "jet black",
}


def _observed(**overrides):
    """Buyer's media read: same garment unless a golden field is explicitly overridden."""
    return {**COTTON_REF, **overrides}


# --------------------------------------------------------------------------
# The mentor's case: same product, different colourway -> MUST NOT flag.
# --------------------------------------------------------------------------
def test_different_colour_same_fabric_is_not_a_mismatch():
    observed = _observed(colour="blue", shade="royal blue")
    r = qf.compare_fingerprints(COTTON_REF, observed)
    assert r["mismatch"] is False
    assert r["divergence_share"] == 0.0
    assert "colour" in r["ignored_attributes"]
    assert "colour" not in r["compared_attributes"]


def test_colour_is_never_scored_even_when_every_variant_field_differs():
    # every variant-specific field disagrees; not one may reach the score
    observed = _observed(colour="red", shade="crimson", print_colourway="red on white")
    ref = {**COTTON_REF, "print_colourway": "black on grey"}
    r = qf.compare_fingerprints(ref, observed)
    assert r["mismatch"] is False
    assert set(r["compared_attributes"]).issubset(set(QUALITY_INVARIANT_ATTRS))
    assert not set(r["compared_attributes"]) & {"colour", "shade", "print_colourway"}


# --------------------------------------------------------------------------
# The real complaint must still land: cotton claimed, polyester delivered.
# --------------------------------------------------------------------------
def test_synthetic_swap_still_flags_across_a_colour_change():
    # buyer's blue kurti is ALSO shiny polyester -> the golden fields move together
    observed = _observed(colour="blue", shade="royal blue", surface_sheen="glossy",
                         fibre_texture="plasticky smooth", weave_structure="knit, loose")
    r = qf.compare_fingerprints(COTTON_REF, observed)
    assert r["mismatch"] is True
    assert r["divergence_share"] >= QUALITY_DIVERGENCE_SHARE
    assert set(r["diverged"]) == {"surface_sheen", "fibre_texture", "weave_structure"}
    assert "colour" in r["ignored_attributes"]  # the swap was found WITHOUT colour


def test_single_attribute_drift_is_noise_not_mismatch():
    # one field off (lighting/wear) is under the threshold
    r = qf.compare_fingerprints(COTTON_REF, _observed(drape="fluid"))
    assert r["mismatch"] is False
    assert r["diverged"] == ["drape"]


def test_phrasing_differences_do_not_count_as_divergence():
    observed = _observed(surface_sheen="matte, fibrous finish", opacity="fully opaque")
    r = qf.compare_fingerprints(COTTON_REF, observed)
    assert r["diverged"] == []
    assert r["mismatch"] is False


# --------------------------------------------------------------------------
# Thin / missing data must never produce a verdict.
# --------------------------------------------------------------------------
def test_unreadable_attributes_are_not_evidence():
    observed = {k: "unclear" for k in QUALITY_INVARIANT_ATTRS}
    r = qf.compare_fingerprints(COTTON_REF, observed)
    assert r["comparable"] is False
    assert r["mismatch"] is False


def test_too_few_comparable_attributes_is_not_comparable():
    r = qf.compare_fingerprints(COTTON_REF, {"surface_sheen": "glossy", "colour": "blue"})
    assert r["comparable"] is False
    assert r["mismatch"] is False


def test_missing_fingerprint_is_not_comparable():
    assert qf.compare_fingerprints(None, _observed())["comparable"] is False
    assert qf.compare_fingerprints(COTTON_REF, None)["comparable"] is False


# --------------------------------------------------------------------------
# Colour is not permanently blind: a wrong-colour complaint is heard, separately.
# --------------------------------------------------------------------------
def test_wrong_colour_claim_surfaces_colour_separately():
    observed = _observed(colour="blue", shade="royal blue")
    r = qf.compare_fingerprints(COTTON_REF, observed, claim_type="wrong_colour")
    assert r["colour_note"] is not None
    assert "black" in r["colour_note"] and "blue" in r["colour_note"]
    # ...but it STILL is not a material mismatch
    assert r["mismatch"] is False


def test_colour_note_absent_for_a_fabric_claim():
    observed = _observed(colour="blue")
    assert qf.compare_fingerprints(COTTON_REF, observed, claim_type="fabric_mismatch")["colour_note"] is None


# --------------------------------------------------------------------------
# variant_context: does the trace explain WHY colour was ignored?
# --------------------------------------------------------------------------
def _variant(vid, name, ref=False):
    return SimpleNamespace(id=vid, name=name, colour=name.lower(), is_listing_reference=ref)


def test_cross_variant_detected_and_explained():
    black = _variant("v_black", "Black", ref=True)
    blue = _variant("v_blue", "Blue")
    product = SimpleNamespace(variants=[black, blue])
    order = SimpleNamespace(variant_id="v_blue")
    ctx = qf.variant_context(product, order)
    assert ctx["cross_variant"] is True
    assert ctx["listing_video_variant"] == "Black"
    assert ctx["ordered_variant"] == "Blue"
    assert "EXPECTED" in ctx["reason"]


def test_same_variant_is_not_cross_variant():
    black = _variant("v_black", "Black", ref=True)
    product = SimpleNamespace(variants=[black, _variant("v_blue", "Blue")])
    ctx = qf.variant_context(product, SimpleNamespace(variant_id="v_black"))
    assert ctx["cross_variant"] is False


def test_no_variants_recorded_is_safe():
    ctx = qf.variant_context(SimpleNamespace(variants=[]), None)
    assert ctx["cross_variant"] is False
    assert ctx["has_variants"] is False
