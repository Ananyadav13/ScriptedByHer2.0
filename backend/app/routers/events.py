"""SSE stream of an investigation's live tool-call / verdict events."""
from __future__ import annotations

import asyncio
import json
import queue

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agents import events

router = APIRouter(tags=["events"])

_POLL_SECONDS = 0.25


async def _stream(investigation_id: str):
    q = events.get(investigation_id)
    if q is None:
        # Investigation already finished (or unknown). Tell the client to fall
        # back to GET /investigations/{id}.
        yield f"data: {json.dumps({'type': 'closed'})}\n\n"
        return
    while True:
        try:
            event = q.get_nowait()
        except queue.Empty:
            await asyncio.sleep(_POLL_SECONDS)
            continue
        if event is events.END:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/events/{investigation_id}")
async def stream_events(investigation_id: str):
    return StreamingResponse(
        _stream(investigation_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
