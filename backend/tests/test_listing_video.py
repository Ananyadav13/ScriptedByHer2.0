"""Live listing-video upload — the demo path, and above all its failure behaviour.

The flagship dispute depends on `prod_fabric_kurti` having a quality fingerprint. This
endpoint replaces that fingerprint, so its failure modes matter more than its happy path:
a quota-exhausted Gemini call mid-presentation must leave the demo exactly as it was.

The multimodal read is stubbed throughout — these tests exercise the real OpenCV keyframe
extraction on a real generated .mp4, but never spend Gemini quota.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.db import SessionLocal
from app.models import Product

KURTI = "prod_fabric_kurti"


@pytest.fixture(scope="module")
def video_bytes(tmp_path_factory) -> bytes:
    """A real, decodable 4-second .mp4 written with OpenCV.

    Generated rather than committed: the point is to exercise the true VideoCapture path
    without adding a binary asset to the repository.
    """
    import cv2

    path = tmp_path_factory.mktemp("media") / "clip.mp4"
    w, h, fps = 320, 240, 12
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    rng = np.random.default_rng(0)
    for i in range(fps * 4):
        frame = np.full((h, w, 3), 40 + (i % 12), np.uint8)
        writer.write(cv2.add(frame, rng.integers(0, 16, (h, w, 3), dtype=np.uint8)))
    writer.release()
    data = path.read_bytes()
    assert len(data) > 1000, "OpenCV produced an empty video"
    return data


def _fingerprint_of(product_id: str) -> tuple[dict | None, str | None]:
    db = SessionLocal()
    try:
        p = db.get(Product, product_id)
        return p.quality_fingerprint_json, p.listing_video_path
    finally:
        db.close()


def _stub_read(monkeypatch, sheen="glossy"):
    """Replace only the model call. Keyframe extraction stays real."""
    from app.agents import vision

    def fake(frames, label):
        assert frames, "the model should never be called with zero frames"
        return vision.FingerprintRead(
            attributes=vision.QualityAttributes(
                weave_structure="knit, loose", surface_sheen=sheen,
                fibre_texture="slippery", opacity="semi-sheer",
                stitch_quality="even seams", drape="fluid",
                embellishment_type="none", colour="navy",
            ),
            summary="Glossy semi-sheer knit — reads synthetic.",
            confidence=0.71, notes=[],
        ), {"frames": len(frames), "total_tokens": 999}

    monkeypatch.setattr(vision, "_read_frames", fake)


def _stub_read_failure(monkeypatch, exc: Exception):
    from app.agents import vision

    def boom(frames, label):
        raise exc

    monkeypatch.setattr(vision, "_read_frames", boom)


class TestLiveExtraction:
    def test_upload_extracts_a_fingerprint_from_real_keyframes(self, client, video_bytes, monkeypatch):
        _stub_read(monkeypatch)
        before, _ = _fingerprint_of(KURTI)
        assert before["attributes"]["surface_sheen"] == "semi-matte", "seeded state changed"

        r = client.post(f"/products/{KURTI}/listing-video",
                        files={"file": ("kurti.mp4", video_bytes, "video/mp4")})
        assert r.status_code == 200
        body = r.json()

        # OpenCV really sampled frames from the uploaded file
        assert body["frames_sampled"] >= 1
        assert body["extracted_live"] is True
        assert body["replaced_seeded_fingerprint"] is True
        assert body["attributes"]["surface_sheen"] == "glossy"

        stored, path = _fingerprint_of(KURTI)
        assert stored["attributes"]["surface_sheen"] == "glossy"
        assert path.endswith(".mp4")

    def test_reset_restores_the_seeded_fingerprint(self, client, video_bytes, monkeypatch):
        """The presenter's undo: re-running the demo must start from the seeded story."""
        from app.seed import SEEDED_FINGERPRINTS

        _stub_read(monkeypatch)
        client.post(f"/products/{KURTI}/listing-video",
                    files={"file": ("kurti.mp4", video_bytes, "video/mp4")})

        r = client.post(f"/products/{KURTI}/listing-video/reset")
        assert r.status_code == 200

        stored, path = _fingerprint_of(KURTI)
        seeded = SEEDED_FINGERPRINTS[KURTI]
        assert stored == seeded["fingerprint"]
        assert path == seeded["listing_video_path"]

    def test_reset_does_not_mutate_the_module_constant(self, client, video_bytes, monkeypatch):
        """The seeded fingerprint is handed out by deep copy. If it were passed by
        reference, one ORM mutation would silently rewrite the seed for the whole process."""
        from app.seed import SEEDED_FINGERPRINTS

        client.post(f"/products/{KURTI}/listing-video/reset")
        db = SessionLocal()
        try:
            p = db.get(Product, KURTI)
            p.quality_fingerprint_json["attributes"]["surface_sheen"] = "TAMPERED"
            db.commit()
        finally:
            db.close()

        assert SEEDED_FINGERPRINTS[KURTI]["fingerprint"]["attributes"]["surface_sheen"] == "semi-matte"
        client.post(f"/products/{KURTI}/listing-video/reset")


class TestDemoSafety:
    """A failed extraction must leave the demo exactly as it was.

    This is the whole reason the endpoint snapshots before it writes. Quota exhaustion on
    the Gemini free tier is not an edge case mid-presentation — it is the expected failure.
    """

    def test_model_failure_restores_the_previous_fingerprint(self, client, video_bytes, monkeypatch):
        client.post(f"/products/{KURTI}/listing-video/reset")
        before = _fingerprint_of(KURTI)

        _stub_read_failure(monkeypatch, RuntimeError("429 RESOURCE_EXHAUSTED"))
        r = client.post(f"/products/{KURTI}/listing-video",
                        files={"file": ("kurti.mp4", video_bytes, "video/mp4")})

        assert r.status_code == 503
        assert "restored" in r.json()["detail"]
        assert _fingerprint_of(KURTI) == before, "state was not restored after failure"

    def test_flagship_dispute_still_works_after_a_failed_upload(self, client, video_bytes, monkeypatch):
        """The comparison the whole demo rests on must survive a failed upload."""
        client.post(f"/products/{KURTI}/listing-video/reset")
        _stub_read_failure(monkeypatch, RuntimeError("503 UNAVAILABLE"))
        client.post(f"/products/{KURTI}/listing-video",
                    files={"file": ("kurti.mp4", video_bytes, "video/mp4")})

        from app.agents.vision import check_media_evidence
        db = SessionLocal()
        try:
            ev = check_media_evidence(KURTI, db, "order_fabric_dispute")
        finally:
            db.close()

        assert ev["available"] is True
        assert ev["mismatch"] is True
        assert set(ev["ignored_attributes"]) == {"colour", "shade", "print_colourway"}


class TestUploadValidation:
    def test_non_video_is_rejected(self, client):
        r = client.post(f"/products/{KURTI}/listing-video",
                        files={"file": ("notes.txt", b"not a video", "text/plain")})
        assert r.status_code == 415

    def test_unknown_product_is_404(self, client, video_bytes):
        r = client.post("/products/prod_does_not_exist/listing-video",
                        files={"file": ("k.mp4", video_bytes, "video/mp4")})
        assert r.status_code == 404

    def test_undecodable_video_is_rejected_before_any_model_call(self, client, monkeypatch):
        """A .mp4 extension on garbage bytes must fail on frame extraction, not by
        spending a multimodal call on nothing."""
        from app.agents import vision

        def must_not_run(frames, label):
            raise AssertionError("the model was called despite unreadable frames")

        monkeypatch.setattr(vision, "_read_frames", must_not_run)
        r = client.post(f"/products/{KURTI}/listing-video",
                        files={"file": ("broken.mp4", b"\x00\x01\x02 not really a video",
                                        "video/mp4")})
        assert r.status_code == 422

    def test_reset_on_a_product_without_a_seeded_fingerprint_is_404(self, client):
        r = client.post("/products/prod_normal_mug/listing-video/reset")
        assert r.status_code == 404
