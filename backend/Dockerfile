FROM python:3.13-slim

WORKDIR /app

# deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# writable dirs for the SQLite DB and logs (mounted as volumes in compose)
RUN mkdir -p /data /app/logs

EXPOSE 8000

# Render/other PaaS inject $PORT; default to 8000 locally.
#
# SINGLE WORKER, deliberately. Live investigation traces are streamed over SSE from
# in-memory per-investigation queues (app/agents/events.py). With >1 worker the request
# that subscribes to a trace can land in a different process than the one publishing it,
# and the stream silently stays empty. Scaling out requires moving those queues to a
# shared broker (Redis pub/sub) first — do not add --workers before that.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
