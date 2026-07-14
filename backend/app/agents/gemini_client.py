"""Single Gemini client + a retry wrapper.

`gemini-3-flash-preview` returns transient 503 (UNAVAILABLE / high demand) and
429 (RESOURCE_EXHAUSTED) under load — observed during Phase 1 verification, mid
tool-loop. Every model call in the app goes through `generate_with_retry` so a
single flaky response doesn't abort an investigation.
"""
from __future__ import annotations

import random
import time

from google import genai
from google.genai import errors

from ..config import settings

_RETRYABLE_CODES = {429, 500, 503}
_MAX_ATTEMPTS = 5

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def generate_with_retry(**kwargs):
    """client().models.generate_content(**kwargs) with backoff on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return client().models.generate_content(**kwargs)
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code in _RETRYABLE_CODES and attempt < _MAX_ATTEMPTS - 1:
                last_exc = exc
                time.sleep(min(2 ** attempt, 8) + random.random())
                continue
            raise
    assert last_exc is not None
    raise last_exc
