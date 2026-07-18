"""Vision pipeline — hybrid + advisory.

THE VARIANT PROBLEM (and why this module is shaped the way it is)
----------------------------------------------------------------
A seller films ONE listing video but sells the same kurti in black, blue and red. Comparing a
buyer's dispute video of the BLUE kurti against a listing video of the BLACK one makes colour
the single loudest "discrepancy" — an honest seller gets false-flagged and the buyer's real
complaint (the fabric) is buried. A seller cannot reasonably film every colourway.

So we never compare pixels across variants. Instead:

  1. `extract_keyframes(path)` — sample frames from a video (OpenCV), a folder of stills, or
     a single image. Raw pixels never leave this module.
  2. `extract_quality_fingerprint(product, db)` — ONE multimodal call that distils the listing
     video into the "golden fields": the variant-INVARIANT quality attributes every colourway
     shares (weave, sheen, texture, opacity, stitch, drape). Cached on the product, so it is
     paid for once and reused by every variant and every later dispute.
  3. `check_media_evidence(product_id, db, order_id=None)` — reads the BUYER's media into the
     same attribute schema, then hands both sides to the PURE, deterministic diff in
     `services.quality_fingerprint`. That module — not the model, and not this prompt —
     decides what counts as a mismatch, and it drops colour/shade before scoring. A vision
     model therefore cannot produce a colour false-flag even if it insists the colour differs.

This is also cheaper: a dispute sends only the buyer's frames plus a short text fingerprint,
instead of re-uploading the listing video every single time.

The read stays ADVISORY: media is uncertain (lighting, wear, the item may not even be the
delivered one), so the output is a recommendation for the product manager, never a punishment.
The orchestrator only ever receives the small text dict this returns.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
from google.genai import types
from pydantic import BaseModel

from ..config import settings
from ..models import Order, Product
from ..services import quality_fingerprint as qf
from ..services.rules import QUALITY_INVARIANT_ATTRS, VARIANT_SPECIFIC_ATTRS
from .gemini_client import generate_with_retry

log = logging.getLogger(__name__)

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
VIDEOS_DIR = MEDIA_ROOT / "videos"
FRAMES_DIR = VIDEOS_DIR / "frames"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

MAX_FRAMES = 6
MAX_EDGE = 1024
JPEG_QUALITY = 85


class QualityAttributes(BaseModel):
    """One structured read of a garment's physical qualities.

    The first seven are the GOLDEN FIELDS (`rules.QUALITY_INVARIANT_ATTRS`) — they describe
    how the item is BUILT and are identical across every colourway, so they are the only
    fields the deterministic diff scores.

    The last three are variant-specific. They are captured for the trace (and for a genuine
    "wrong colour sent" complaint) but `services.quality_fingerprint` drops them before
    computing any mismatch. Use "unclear" when a field genuinely cannot be read — an honest
    "unclear" is treated as no evidence, whereas a guess would become false evidence.
    """
    weave_structure: str = ""     # knit vs woven; tight vs loose
    surface_sheen: str = ""       # matte / semi-matte / glossy
    fibre_texture: str = ""       # fibrous / smooth / plasticky
    opacity: str = ""             # opaque / semi-sheer / sheer
    stitch_quality: str = ""      # seam + hem density and finish
    drape: str = ""               # stiff / structured / fluid
    embellishment_type: str = ""  # print / embroidery / sequins / none (TYPE, not colour)
    # --- variant-specific: recorded, never scored as a mismatch ---
    colour: str = ""
    shade: str = ""
    print_colourway: str = ""


class FingerprintRead(BaseModel):
    """A structured attribute read of one side (listing reference OR buyer evidence)."""
    attributes: QualityAttributes
    summary: str                # one plain sentence describing what is visible
    confidence: float           # 0-1, calibrated for lighting/angle/wear
    notes: list[str] = []       # caveats worth showing a human
    suggested_remedy: str = ""  # advisory only; the mismatch verdict is computed, not asked


def _resize_jpeg(img) -> bytes:
    h, w = img.shape[:2]
    scale = MAX_EDGE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else b""


def _resolve(path: str) -> Path:
    """Map a stored media path to a real file/dir. Accepts an absolute path, a video
    file or image under media/videos/, or a logical key naming a frames/<dir>."""
    p = Path(path)
    if p.is_absolute() and p.exists():
        return p
    for cand in (VIDEOS_DIR / path, FRAMES_DIR / path, FRAMES_DIR / p.name):
        if cand.exists():
            return cand
    return VIDEOS_DIR / path


def extract_keyframes(path: str, max_frames: int = MAX_FRAMES) -> list[bytes]:
    """Up to `max_frames` JPEG keyframes (bytes) from a video, a stills folder, or a
    single image. Output is identical regardless of source, so the vision call is
    agnostic to whether a physical video exists."""
    if not path:
        return []
    target = _resolve(path)

    # Folder of stills.
    if target.is_dir():
        stills = sorted(f for f in target.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES)
        out = []
        for f in stills[:max_frames]:
            img = cv2.imread(str(f))
            if img is not None:
                out.append(_resize_jpeg(img))
        return out

    # Single image (a buyer photo).
    if target.suffix.lower() in IMAGE_SUFFIXES and target.exists():
        img = cv2.imread(str(target))
        return [_resize_jpeg(img)] if img is not None else []

    # Real video: interval-sample frames.
    if target.suffix.lower() in VIDEO_SUFFIXES and target.exists():
        cap = cv2.VideoCapture(str(target))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        out = []
        if total > 0:
            step = max(1, total // max_frames)
            for idx in range(0, total, step):
                if len(out) >= max_frames:
                    break
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if ok:
                    out.append(_resize_jpeg(frame))
        cap.release()
        return out

    return []


def _frames_from_many(paths: list[str], budget: int) -> list[bytes]:
    """Collect keyframes across several media paths, up to `budget` total."""
    out: list[bytes] = []
    for p in paths:
        if len(out) >= budget:
            break
        out.extend(extract_keyframes(p, max_frames=max(1, budget - len(out))))
    return out[:budget]


_GOLDEN = ", ".join(QUALITY_INVARIANT_ATTRS)
_VARIANT = ", ".join(VARIANT_SPECIFIC_ATTRS)

_READ_INSTRUCTION = (
    "You are a textile-inspection assistant. Read the physical QUALITIES of the garment in "
    "these frames into the given fields.\n"
    f"- The build fields ({_GOLDEN}) describe HOW THE ITEM IS MADE. Judge the material from "
    "them: a matte, fibrous, opaque, tightly-woven surface reads as natural cotton; a glossy, "
    "smooth/plasticky, semi-sheer, loosely-knit surface reads as synthetic/polyester.\n"
    f"- The variant fields ({_VARIANT}) are the colourway. Record what you see, but understand "
    "they are NOT used to judge whether the product matches — the same design is sold in many "
    "colours.\n"
    "- Use \"unclear\" for any field you genuinely cannot see. Do not guess: an honest "
    "\"unclear\" is discarded, but a guess becomes false evidence.\n"
    "Give a one-line `summary` and a `confidence` (0-1) that reflects lighting, angle and wear. "
    "You do NOT decide any outcome — a separate rule engine compares your reading."
)


def _read_frames(frames: list[bytes], label: str) -> tuple[FingerprintRead | None, dict]:
    """One multimodal call -> a structured FingerprintRead over `frames`. ISOLATED: raw
    pixels never leave here; the caller gets attributes + a token-cost dict."""
    if not frames:
        return None, {"frames": 0, "total_tokens": None}
    parts = [types.Part(text=_READ_INSTRUCTION), types.Part(text=f"--- {label} ---")]
    parts += [types.Part.from_bytes(data=f, mime_type="image/jpeg") for f in frames]
    resp = generate_with_retry(
        model=settings.llm_model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FingerprintRead,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    usage = getattr(resp, "usage_metadata", None)
    return resp.parsed, {"frames": len(frames), "total_tokens": getattr(usage, "total_token_count", None)}


def extract_quality_fingerprint(product, db, persist: bool = True) -> dict:
    """Distil the seller's listing video into the variant-invariant GOLDEN FIELDS, ONCE.

    Cached on `product.quality_fingerprint_json`, so every variant and every later dispute
    reuses it instead of re-reading the video. Returns the fingerprint dict (attributes +
    summary + confidence), or an {available: False} dict when there is no listing video.
    """
    cached = getattr(product, "quality_fingerprint_json", None)
    if cached:
        return {**cached, "available": True, "cached": True}

    if not product.listing_video_path:
        return {"available": False, "reason": "no listing video to fingerprint"}

    frames = extract_keyframes(product.listing_video_path)
    read, cost = _read_frames(frames, "SELLER LISTING (reference)")
    if read is None:
        return {"available": False, "reason": "listing video produced no readable frames"}

    fp = {
        "attributes": read.attributes.model_dump(),
        "summary": read.summary,
        "confidence": round(read.confidence, 2),
        "notes": read.notes,
        "source_frames": cost["frames"],
    }
    if persist:
        product.quality_fingerprint_json = fp
        db.commit()
    log.info("fingerprint %s: %s frames, tokens=%s, conf=%s",
             product.id, cost["frames"], cost["total_tokens"], fp["confidence"])
    return {**fp, "available": True, "cached": False}


def check_media_evidence(product_id: str, db, order_id: str | None = None) -> dict:
    """ADVISORY media check, variant-aware. Reads the buyer's evidence into the golden-field
    schema and hands it, with the product's cached fingerprint, to the PURE deterministic
    diff in `services.quality_fingerprint`. Colour/shade never reach the mismatch verdict —
    so a dispute on a different colourway cannot false-flag an honest seller.

    Returns a small text dict for the orchestrator (raw frames stay here). Advisory: it
    never locks/bans anything; the manager decides.
    """
    product = db.get(Product, product_id)
    if product is None:
        return {"error": f"product {product_id} not found", "available": False}

    order = db.get(Order, order_id) if order_id else None
    vctx = qf.variant_context(product, order)

    # Reference = the product's quality fingerprint (extract + cache lazily if unseeded).
    fp = extract_quality_fingerprint(product, db)
    reference_attrs = fp.get("attributes") if fp.get("available") else None
    reference_frame_urls = list(product.listing_frame_urls or [])

    # Buyer evidence. Image URLs (for display) + the observed attributes to compare.
    evidence_paths = list(order.buyer_evidence_json) if order and order.buyer_evidence_json else []
    if not evidence_paths:
        evidence_paths = [r.video_path for r in product.reviews if r.has_video and r.video_path]

    # Observed attributes: prefer a SEEDED pre-read (deterministic, zero-quota demo). Only fall
    # back to a live multimodal read when there's no seeded fingerprint AND real frames exist.
    seeded_observed = getattr(order, "buyer_evidence_fingerprint_json", None) if order else None
    observed_summary = ""
    cost = {"frames": 0, "total_tokens": None}
    if seeded_observed:
        observed_attrs = dict(seeded_observed)
        observed_summary = observed_attrs.pop("_summary", "") if isinstance(observed_attrs, dict) else ""
        confidence = 0.72  # media reads are inherently uncertain (lighting/wear/angle)
    else:
        ev_frames = _frames_from_many(evidence_paths, MAX_FRAMES)
        if not ev_frames:
            return {
                "available": False,
                "has_reference": bool(reference_attrs),
                "variant": vctx,
                "reference_frame_urls": reference_frame_urls,
                "reason": "no buyer/review media to inspect",
            }
        buyer_read, cost = _read_frames(ev_frames, "BUYER / REVIEW EVIDENCE")
        observed_attrs = buyer_read.attributes.model_dump() if buyer_read else None
        observed_summary = buyer_read.summary if buyer_read else ""
        confidence = round(min(fp.get("confidence", 1.0), buyer_read.confidence if buyer_read else 1.0), 2)

    claim_type = getattr(order, "claim_type", None) if order else None
    diff = qf.compare_fingerprints(reference_attrs, observed_attrs, claim_type=claim_type)

    log.info("%s order=%s: cross_variant=%s, diverged=%s, ignored=%s, mismatch=%s",
             product_id, order_id, vctx["cross_variant"], diff["diverged"],
             diff["ignored_attributes"], diff["mismatch"])

    return {
        "available": True,
        "product_id": product.id,
        "has_reference": bool(reference_attrs),
        "claimed_material": product.fabric_claim or "(no material stated)",
        "variant": vctx,
        # frame image URLs so the trace can SHOW the comparison, not just describe it
        "reference_frame_urls": reference_frame_urls,
        "evidence_frame_urls": [p for p in evidence_paths if str(p).startswith("/") or str(p).startswith("http")],
        "reference_summary": fp.get("summary", ""),
        "reference_attributes": reference_attrs,
        "observed_summary": observed_summary,
        "observed_attributes": observed_attrs,
        # the verdict is COMPUTED by the deterministic diff, not asked of the model
        "compared_attributes": diff["compared_attributes"],
        "diverged_attributes": diff["diverged"],
        "ignored_attributes": diff["ignored_attributes"],
        "mismatch": diff["mismatch"],
        "mismatch_share": diff["divergence_share"],
        "mismatch_flag": diff["mismatch"],
        "colour_note": diff["colour_note"],
        "confidence": confidence,
        "reason": diff["reason"],
        "recommended_action": ("route to a human product manager" if diff["mismatch"]
                               else "no material mismatch found — no action on the seller"),
        "suggested_remedy": "",
        "advisory": True,  # this tool NEVER auto-punishes; it recommends to the manager
        "_cost": cost,
    }
