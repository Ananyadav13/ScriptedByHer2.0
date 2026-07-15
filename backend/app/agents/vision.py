"""Vision pipeline (Phase 3, hybrid + advisory — PLAN.md §5B, §11).

Evidence is HYBRID: the seller's authentic listing video (`Product.listing_video_path`,
the canonical reference) vs. the buyer's complaint evidence (photo OR video,
`Order.buyer_evidence_json`). When no reference exists we fall back to comparing the
buyer/review media against the listing's `fabric_claim`.

Two stages, deliberately ISOLATED from the orchestrator context:
  1. `extract_keyframes(path)` — sample frames from a video (OpenCV), a folder of
     stills, or a single image. Raw pixels never leave this module.
  2. `check_media_evidence(product_id, db, order_id=None)` — ONE isolated multimodal
     Gemini call that returns a `MediaComparison`: observed discrepancies + a
     mismatch share + a CONFIDENCE + an ADVISORY recommendation. It does NOT decide a
     punishment — media comparison is uncertain (item may not have reached the buyer,
     lighting, wear), so the output is a suggestion for the product manager. The
     orchestrator only ever receives the small text dict this returns.
"""
from __future__ import annotations

from pathlib import Path

import cv2
from google.genai import types
from pydantic import BaseModel

from ..config import settings
from ..models import Order, Product
from ..services.rules import PHOTO_MISMATCH_SHARE
from .gemini_client import generate_with_retry

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
VIDEOS_DIR = MEDIA_ROOT / "videos"
FRAMES_DIR = VIDEOS_DIR / "frames"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

MAX_FRAMES = 6
MAX_EDGE = 1024
JPEG_QUALITY = 85


class MediaComparison(BaseModel):
    """Advisory read comparing seller reference vs buyer/review evidence (NO verdict)."""
    reference_summary: str      # what the seller's listing media shows ('' if none)
    evidence_summary: str       # what the buyer's/reviewers' media shows
    discrepancies: list[str]    # concrete visual differences found
    mismatch: bool              # do they materially disagree (or contradict the claim)?
    mismatch_share: float       # 0-1: fraction of evidence frames that contradict
    confidence: float           # 0-1: how sure, given lighting/angle/wear caveats
    recommended_action: str     # advisory: e.g. "request seller QC video", "hold + notify", "no action"
    suggested_remedy: str       # one plain sentence the product manager can act on


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


def _compare_instruction(claim: str, has_reference: bool) -> str:
    if has_reference:
        return (
            "You are a materials-inspection assistant. The FIRST group of frames is the "
            "seller's own LISTING video of the product (the reference — 'what they said "
            "they are selling'). The SECOND group is a BUYER'S complaint evidence (photo "
            "or video of what arrived). Compare them: do they show the same product and "
            f"material? The listing also claims the material is {claim!r}. Report concrete "
            "visual DISCREPANCIES only. Be careful: differences can be innocent (lighting, "
            "angle, a washed/worn item, or the item may not even be the one delivered) — "
            "reflect that in a calibrated `confidence`. You do NOT decide any punishment; "
            "you RECOMMEND a next step for a human product manager. mismatch_share = "
            "fraction of buyer frames that contradict the reference/claim (0.0-1.0)."
        )
    return (
        "You are a materials-inspection assistant. These frames are customer/review media "
        f"of a product whose listing claims the material is {claim!r}. Report whether the "
        "visible material is consistent with that claim (glossy/plasticky sheen = "
        "synthetic; matte fibrous = natural cotton), citing concrete visual evidence. "
        "Account for lighting/angle in a calibrated `confidence`. You do NOT decide any "
        "punishment; you RECOMMEND a next step for a human product manager. mismatch_share "
        "= fraction of frames contradicting the claim (0.0-1.0). Leave reference_summary empty."
    )


def check_media_evidence(product_id: str, db, order_id: str | None = None) -> dict:
    """Hybrid, ADVISORY media check. Compares the seller's listing reference against
    the buyer's evidence (or against the fabric claim when there is no reference).

    Returns a small text dict for the orchestrator (raw frames stay here). Advisory:
    carries a `confidence`, a `recommended_action` and a `suggested_remedy` for the
    product manager — it never itself locks/bans anything.
    """
    product = db.get(Product, product_id)
    if product is None:
        return {"error": f"product {product_id} not found", "available": False}

    # Reference = seller listing video.
    ref_frames = extract_keyframes(product.listing_video_path) if product.listing_video_path else []

    # Evidence = buyer's dispute media (a specific order) OR the product's review media.
    evidence_paths: list[str] = []
    if order_id:
        order = db.get(Order, order_id)
        if order and order.buyer_evidence_json:
            evidence_paths = list(order.buyer_evidence_json)
    if not evidence_paths:
        evidence_paths = [r.video_path for r in product.reviews if r.has_video and r.video_path]

    ev_frames = _frames_from_many(evidence_paths, MAX_FRAMES)
    if not ev_frames and not ref_frames:
        return {
            "available": False,
            "has_reference": bool(product.listing_video_path),
            "reason": "no seller listing video and no buyer/review media to inspect",
        }

    claim = product.fabric_claim or "(no material stated)"
    has_ref = bool(ref_frames)
    parts = [types.Part(text=_compare_instruction(claim, has_ref))]
    if has_ref:
        parts.append(types.Part(text="--- SELLER LISTING (reference) ---"))
        parts += [types.Part.from_bytes(data=f, mime_type="image/jpeg") for f in ref_frames]
        parts.append(types.Part(text="--- BUYER / REVIEW EVIDENCE ---"))
    parts += [types.Part.from_bytes(data=f, mime_type="image/jpeg") for f in ev_frames]

    resp = generate_with_retry(
        model=settings.llm_model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MediaComparison,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    cmp: MediaComparison = resp.parsed
    usage = getattr(resp, "usage_metadata", None)
    cost = {
        "reference_frames": len(ref_frames),
        "evidence_frames": len(ev_frames),
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }
    print(f"[vision] {product_id} order={order_id}: ref={len(ref_frames)} ev={len(ev_frames)} "
          f"frames, tokens={cost['total_tokens']}, mismatch_share={cmp.mismatch_share} "
          f"conf={cmp.confidence}")

    return {
        "available": True,
        "has_reference": has_ref,
        "reference_frames": len(ref_frames),
        "evidence_frames": len(ev_frames),
        "claimed_material": claim,
        "reference_summary": cmp.reference_summary,
        "evidence_summary": cmp.evidence_summary,
        "discrepancies": cmp.discrepancies,
        "mismatch": cmp.mismatch,
        "mismatch_share": round(cmp.mismatch_share, 2),
        "mismatch_flag": cmp.mismatch_share >= PHOTO_MISMATCH_SHARE,
        "confidence": round(cmp.confidence, 2),
        "recommended_action": cmp.recommended_action,
        "suggested_remedy": cmp.suggested_remedy,
        "advisory": True,  # this tool NEVER auto-punishes; it recommends to the manager
        "_cost": cost,
    }
