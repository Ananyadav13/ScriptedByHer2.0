"""Gemini client pool + a retry/rotation wrapper.

`gemini-3-flash-preview` on the free tier fails two different ways:
  - transient 503 (high demand) / per-minute 429 — retry with backoff.
  - daily-cap 429 RESOURCE_EXHAUSTED (20 requests/day PER PROJECT) — backoff can't
    fix it; the whole key is spent for the day.

To keep a demo alive we support a POOL of keys (`GEMINI_API_KEYS=key1,key2,...`),
each a separate project with its own daily quota. On any retryable error we rotate
to the next key; we only sleep once we've cycled through every key. The last key
that succeeded becomes the starting point for the next call, so a spent key isn't
retried first every time. A single `GEMINI_API_KEY` still works (pool of one).
"""
from __future__ import annotations

import random
import threading
import time

from google import genai
from google.genai import errors

from ..config import settings

_RETRYABLE_CODES = {429, 500, 503}
_MAX_ATTEMPTS = 6

_lock = threading.Lock()
_clients: dict[str, genai.Client] = {}   # key -> client (cached)
_start_idx = 0                            # rotates to the last-good key


def _keys() -> list[str]:
    keys = settings.gemini_key_list
    if not keys:
        raise RuntimeError("No Gemini API key configured (set GEMINI_API_KEY or GEMINI_API_KEYS).")
    return keys


def _client_for(key: str) -> genai.Client:
    with _lock:
        c = _clients.get(key)
        if c is None:
            c = genai.Client(api_key=key)
            _clients[key] = c
        return c


def client() -> genai.Client:
    """The current primary client (first usable key) — used by simple callers."""
    return _client_for(_keys()[_start_idx % len(_keys())])


def generate_with_retry(**kwargs):
    """generate_content with backoff on transient errors AND key rotation on
    daily-cap exhaustion. Raises the last error only after every key is spent."""
    global _start_idx
    keys = _keys()
    n = len(keys)
    last_exc: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        idx = (_start_idx + attempt) % n
        try:
            resp = _client_for(keys[idx]).models.generate_content(**kwargs)
            _start_idx = idx  # stick with the key that just worked
            return resp
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code not in _RETRYABLE_CODES or attempt == _MAX_ATTEMPTS - 1:
                raise
            last_exc = exc
            # Sleep only after we've tried every key this round (all rate-limited).
            if (attempt + 1) % n == 0:
                time.sleep(min(2 ** (attempt // n), 8) + random.random())
    assert last_exc is not None
    raise last_exc
