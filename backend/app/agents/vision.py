"""Vision pipeline (Phase 3) — video review evidence, PLAN.md §11.

Two stages, deliberately ISOLATED from the orchestrator context:
  1. `extract_keyframes(video_path)` — sample representative frames from a review
     video (OpenCV) OR, when no physical video exists yet, load the committed
     fallback still-frames. Raw pixels never leave this module.
  2. `analyze_video_reviews(product_id, db)` — ONE isolated multimodal Gemini call
     over those frames that returns OBSERVATIONS ONLY (a structured verdict-free
     read of the fabric/material vs the listing's claim). The orchestrator only
     ever receives the small text dict this returns — the images stay here so the
     agent's context never balloons with raw media.

This is the 4th Agent-1 tool (`check_video_reviews`), risk-gated by the prompt so
it is called only when a fabric/quality claim is in doubt, not on every product.
"""
from __future__ import annotations

from pathlib import Path

import cv2
from google.genai import types
from pydantic import BaseModel

from ..config import settings
from ..models import Product
from ..services.rules import PHOTO_MISMATCH_SHARE
from .gemini_client import generate_with_retry

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
VIDEOS_DIR = MEDIA_ROOT / "videos"
FRAMES_DIR = VIDEOS_DIR / "frames"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}

MAX_FRAMES = 6
MAX_EDGE = 1024
JPEG_QUALITY = 85


class FabricObservation(BaseModel):
    """Observation-only read of the review frames (NO buy/lock verdict)."""
    observed_material: str      # what the fabric/surface actually looks like
    claimed_material: str       # echoed back from the listing for grounding
    matches_claim: bool         # does what you see match the listing claim?
    mismatch_share: float       # 0-1: fraction of frames that contradict the claim
    notes: str                  # one plain sentence of visual evidence


def _resize_jpeg(img) -> bytes:
    """Resize a BGR OpenCV frame to max-edge and JPEG-encode to bytes."""
    h, w = img.shape[:2]
    scale = MAX_EDGE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else b""


def _resolve(video_path: str) -> Path:
    """Map a review's `video_path` to a real file or a fallback frames directory.

    `video_path` may be an actual video file (physical-world recording) OR a logical
    key naming a committed frames folder (e.g. 'kurti_synthetic_a'). Absolute/relative
    paths are honoured; bare keys resolve under media/videos[/frames].
    """
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return p
    for cand in (VIDEOS_DIR / video_path, FRAMES_DIR / video_path, FRAMES_DIR / p.name):
        if cand.exists():
            return cand
    return VIDEOS_DIR / video_path


def extract_keyframes(video_path: str, max_frames: int = MAX_FRAMES) -> list[bytes]:
    """Return up to `max_frames` JPEG-encoded keyframes (bytes).

    Real video -> even interval sampling via OpenCV. Fallback frames dir -> the
    committed stills. Either way the output is identical (list of JPEG bytes), so
    the vision call is agnostic to whether a physical video exists.
    """
    target = _resolve(video_path)

    # Fallback: a directory of committed still frames.
    if target.is_dir():
        stills = sorted(p for p in target.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        out = []
        for f in stills[:max_frames]:
            img = cv2.imread(str(f))
            if img is not None:
                out.append(_resize_jpeg(img))
        return out

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


_VISION_INSTRUCTION = (
    "You are a materials-inspection assistant. You are shown still frames captured "
    "from customer REVIEW VIDEOS of one product. The seller's listing claims the "
    "material is: {claim!r}. Look ONLY at what the frames actually show (weave, "
    "sheen, texture, drape) and report whether the visible material is consistent "
    "with that claim. A smooth glossy/plasticky sheen indicates synthetic/polyester; "
    "a matte fibrous surface indicates natural cotton. Do NOT decide any marketplace "
    "action — observations only. mismatch_share = fraction of the frames whose "
    "appearance contradicts the claim (0.0 to 1.0)."
)


def analyze_video_reviews(product_id: str, db) -> dict:
    """Isolated multimodal sub-call: frames -> fabric observations (no verdict).

    Returns a small text dict for the orchestrator (raw frames stay in this module).
    Includes a `_cost` block (frames + token counts) for the deck's cost slide.
    """
    product = db.get(Product, product_id)
    if product is None:
        return {"error": f"product {product_id} not found", "available": False}

    video_reviews = [r for r in product.reviews if r.has_video and r.video_path]
    if not video_reviews:
        return {
            "available": False,
            "video_review_count": 0,
            "reason": "no video reviews attached to this product",
        }

    frames: list[bytes] = []
    for r in video_reviews:
        frames.extend(extract_keyframes(r.video_path))
        if len(frames) >= MAX_FRAMES:
            frames = frames[:MAX_FRAMES]
            break
    if not frames:
        return {
            "available": False,
            "video_review_count": len(video_reviews),
            "reason": "video reviews present but no frames could be extracted",
        }

    claim = product.fabric_claim or "(no material stated)"
    parts = [types.Part(text=_VISION_INSTRUCTION.format(claim=claim))]
    parts += [types.Part.from_bytes(data=f, mime_type="image/jpeg") for f in frames]

    resp = generate_with_retry(
        model=settings.llm_model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FabricObservation,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    obs: FabricObservation = resp.parsed
    usage = getattr(resp, "usage_metadata", None)
    cost = {
        "frames": len(frames),
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }
    print(f"[vision] {product_id}: {len(frames)} frames, tokens={cost['total_tokens']}, "
          f"mismatch_share={obs.mismatch_share}")

    return {
        "available": True,
        "video_review_count": len(video_reviews),
        "frames_analyzed": len(frames),
        "claimed_material": obs.claimed_material or claim,
        "observed_material": obs.observed_material,
        "matches_claim": obs.matches_claim,
        "photo_mismatch_share": round(obs.mismatch_share, 2),
        "mismatch_flag": obs.mismatch_share >= PHOTO_MISMATCH_SHARE,
        "notes": obs.notes,
        "_cost": cost,
    }
