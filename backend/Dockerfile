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
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
