"""In-memory per-investigation event queues bridging the (threaded) background
investigation to the (async) SSE endpoint.

The orchestrator runs in a FastAPI BackgroundTask worker thread and `publish`es
events; the SSE endpoint drains the thread-safe queue. `None` is the end sentinel.
"""
from __future__ import annotations

import queue
import threading

_queues: dict[str, "queue.Queue[dict | None]"] = {}
_lock = threading.Lock()

END = None  # sentinel pushed when an investigation finishes


def create(investigation_id: str) -> "queue.Queue[dict | None]":
    with _lock:
        q: "queue.Queue[dict | None]" = queue.Queue()
        _queues[investigation_id] = q
        return q


def get(investigation_id: str) -> "queue.Queue[dict | None] | None":
    with _lock:
        return _queues.get(investigation_id)


def publish(investigation_id: str, event: dict | None) -> None:
    q = get(investigation_id)
    if q is not None:
        q.put(event)


def finish(investigation_id: str) -> None:
    """Signal end-of-stream, then forget the queue."""
    publish(investigation_id, END)
    with _lock:
        _queues.pop(investigation_id, None)
