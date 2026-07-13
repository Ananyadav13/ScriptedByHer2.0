# Build Trust

Two agentic AI systems for Meesho that **act on evidence, not just flag** — one investigates a product or delivery dispute the moment a buyer doubts it; the other continuously audits the catalog for bad listings and fixes or removes them. Built for ScriptedBy{Her} 2.0 (Round 3).

> Status: **Phase 1 (foundation)** — see PHASES.md for the build roadmap.

## Run locally

Two processes. Requires Python 3.11+ and Node 18+.

**Backend** (`http://localhost:8000`):
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env          # then put your ANTHROPIC_API_KEY in .env
uvicorn app.main:app --port 8000
```

**Frontend** (`http://localhost:3000`):
```bash
cd frontend
npm install
npm run dev
```

The database is SQLite, seeded automatically on backend startup with 8 demo products (6 golden-path scenarios + 2 benign). No migrations to run.

## Architecture

See [PLAN.md](PLAN.md) §1. Backend: FastAPI + SQLAlchemy + the Anthropic SDK tool-runner agent loop. Frontend: Next.js (App Router). Live agent trace streams over Server-Sent Events.

## Attribution

All open-source dependencies are listed in [ATTRIBUTION.md](ATTRIBUTION.md).
