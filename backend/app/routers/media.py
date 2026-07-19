"""Live listing-video upload — the demo entry point to the existing vision pipeline.

WHAT THIS IS
------------
A presenter uploads a real 5-15s clip of a garment during the demo; the product's quality
fingerprint is re-extracted from it live. Everything downstream — the deterministic diff,
the dispute verdict, the manager queue — is unchanged and unaware this happened.

WHAT THIS IS NOT
----------------
New capability. `vision.extract_keyframes` (OpenCV) and `vision.extract_quality_fingerprint`
(one multimodal read) already existed and were already unit-tested; the repository simply
shipped no video to point them at, so the seeded demo exercised the diff but never the
extraction. This module is a route to that code, not a reimplementation of it.

DEMO SAFETY
-----------
The flagship dispute depends on `prod_fabric_kurti` having a fingerprint. A failed or slow
Gemini call must therefore never leave the product without one. So the existing fingerprint
is snapshotted before extraction and restored on ANY failure, and the endpoint reports
exactly which happened. Uploading during a demo can improve the story; it cannot break it.
"""
from __future__ import annotations

import logging
import re
from copy import deepcopy

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Product
from ..time_utils import utcnow

router = APIRouter(tags=["media"])
log = logging.getLogger(__name__)

# 15s of phone video is comfortably under this; the cap exists so a mis-drag of a 2GB file
# fails fast with a clear message instead of filling the container disk.
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


def _safe_filename(product_id: str, original: str) -> str:
    """A predictable, traversal-proof name. The uploaded name is never trusted."""
    suffix = "." + original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if suffix not in ALLOWED_SUFFIXES:
        suffix = ".mp4"
    stamp = utcnow().strftime("%Y%m%d%H%M%S")
    return f"{_SAFE_NAME.sub('_', product_id)}_{stamp}{suffix}"


@router.post("/products/{product_id}/listing-video")
async def upload_listing_video(
    product_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Replace a product's listing video and re-extract its quality fingerprint live.

    Returns the extracted golden fields, how many keyframes OpenCV sampled, and the model's
    self-reported confidence — so the extraction can be shown happening rather than asserted.
    """
    from ..agents import vision   # lazy: keeps the import graph free of the LLM path at boot

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, f"product {product_id} not found")

    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            415,
            f"unsupported file type '{suffix or file.filename}' — "
            f"expected one of {sorted(ALLOWED_SUFFIXES)}",
        )

    vision.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(product_id, file.filename or "clip.mp4")
    target = vision.VIDEOS_DIR / filename

    size = 0
    try:
        with target.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        413, f"file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
                out.write(chunk)
    finally:
        await file.close()

    # Snapshot what we are about to replace, so a failed extraction is fully reversible.
    prior_fingerprint = product.quality_fingerprint_json
    prior_path = product.listing_video_path

    frames = vision.extract_keyframes(str(target))
    if not frames:
        target.unlink(missing_ok=True)
        raise HTTPException(
            422,
            "no readable frames — the file may be corrupt or use a codec OpenCV cannot "
            "decode. An H.264 .mp4 works reliably.",
        )

    # Force a fresh read rather than returning the cache.
    product.listing_video_path = filename
    product.quality_fingerprint_json = None
    db.commit()

    try:
        fp = vision.extract_quality_fingerprint(product, db)
    except Exception as exc:  # noqa: BLE001 — quota/network failures are expected mid-demo
        product.quality_fingerprint_json = prior_fingerprint
        product.listing_video_path = prior_path
        db.commit()
        log.warning("live fingerprint extraction failed for %s: %s", product_id, exc)
        raise HTTPException(
            503,
            "the vision model was unavailable, so the previous fingerprint has been "
            "restored and the demo is unaffected. Retry, or continue with the seeded "
            f"fingerprint. ({type(exc).__name__})",
        ) from exc

    if not fp.get("available"):
        product.quality_fingerprint_json = prior_fingerprint
        product.listing_video_path = prior_path
        db.commit()
        raise HTTPException(422, fp.get("reason", "the video produced no usable attributes"))

    log.info("live fingerprint extracted for %s from %s (%s frames, confidence %s)",
             product_id, filename, fp.get("source_frames"), fp.get("confidence"))

    return {
        "product_id": product.id,
        "product_title": product.title,
        "filename": filename,
        "size_bytes": size,
        "frames_sampled": fp.get("source_frames"),
        "attributes": fp.get("attributes"),
        "summary": fp.get("summary"),
        "confidence": fp.get("confidence"),
        "notes": fp.get("notes", []),
        "replaced_seeded_fingerprint": bool(prior_fingerprint),
        "extracted_live": True,
    }


@router.post("/products/{product_id}/listing-video/reset")
def reset_listing_video(product_id: str, db: Session = Depends(get_db)):
    """Restore the seeded fingerprint — the presenter's undo between demo runs.

    Without this, a live extraction permanently changes the golden-path demo data and the
    next run tells a slightly different story.
    """
    from ..seed import SEEDED_FINGERPRINTS

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, f"product {product_id} not found")

    seeded = SEEDED_FINGERPRINTS.get(product_id)
    if seeded is None:
        raise HTTPException(404, f"{product_id} has no seeded fingerprint to restore")

    # deep-copied for the same reason the seeder copies it: never hand the ORM a reference
    # to the module constant.
    product.quality_fingerprint_json = deepcopy(seeded["fingerprint"])
    product.listing_video_path = seeded["listing_video_path"]
    db.commit()
    log.info("restored seeded fingerprint for %s", product_id)
    return {"product_id": product.id, "restored": True,
            "listing_video_path": product.listing_video_path}
