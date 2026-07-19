# Build Trust

Two agentic AI systems for a Meesho-style marketplace that **act on evidence, not just flag it**.

- **Agent 1 — Verification & Authenticity**, called **Trusty** in the product UI. Investigates a product or a delivery dispute the moment a buyer doubts it. It runs deterministic risk tools, reasons over the numbers, and then *executes* a graduated action — lock, request a quality-check video, relabel, hold, refund, or clear.
- **Agent 2 — Listing & Catalog Integrity.** Continuously audits the catalog for misleading listings, clusters what buyers actually complain about, and **drafts the correction** for the seller to approve.

The guiding principle, encoded throughout: **authenticity matters, but not at the cost of the buyer or seller community.** A counterfeit people regret gets locked. A knockoff people knowingly love gets relabeled, not banned. Nothing punitive happens on thin evidence, and every uncertain call routes to a human manager.

Built for ScriptedBy{Her} 2.0 (Round 3).

## Try it live

| | |
| --- | --- |
| **Live app** | https://scripted-by-her2-0.vercel.app |
| **Live API** | https://scriptedbyher2-0.onrender.com — [interactive docs](https://scriptedbyher2-0.onrender.com/docs) |

Start at [**/demo**](https://scripted-by-her2-0.vercel.app/demo) for the guided two-journey walkthrough.
The API is on Render's free tier and sleeps when idle, so the first request may take up to a minute to
wake it; everything after that is fast.

> **Status:** feature-complete prototype. Both agents, the buyer/seller/manager consoles, and the full moderation loop execute the complete workflow end to end. 127 tests pass. This is a demo prototype, not a production system — see [Limitations](#limitations).

---

## Table of contents

- [Quick start](#quick-start)
- [Run with Docker](#run-with-docker)
- [Demo walkthrough](#demo-walkthrough)
- [Seeded data](#seeded-data)
- [Architecture](#architecture)
- [AI agent architecture](#ai-agent-architecture)
- [Moderation workflow](#moderation-workflow)
- [Repository structure](#repository-structure)
- [Testing](#testing)
- [Technologies](#technologies)
- [Limitations](#limitations)

---

## Quick start

Two processes. Requires **Python 3.11+** and **Node 20+**.

### 1. Backend → http://localhost:8000

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # then add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Interactive API docs are served at http://localhost:8000/docs.

### 2. Frontend → http://localhost:3000

```bash
cd frontend
npm install
npm run dev
```

The database is SQLite and is **seeded automatically on startup** — no migrations to run. By default (`SEED_RESET=true`) the backend drops and reseeds on every boot, so you always get a clean demo.

### Environment variables

Backend (`backend/.env`, documented in `backend/.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | — | Gemini key. Required for the agent reasoning loop; every deterministic surface works without it. |
| `GEMINI_API_KEYS` | — | Optional comma-separated **pool**. Rotates on daily-quota exhaustion. |
| `DATABASE_URL` | `sqlite:///./build_trust.db` | SQLAlchemy URL. |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Comma-separated allowed CORS origins. |
| `SEED_RESET` | `true` | `true` wipes and reseeds on boot; `false` preserves data. |
| `LLM_MODEL` | `gemini-3-flash-preview` | Gemini model used by both agents. |
| `LOG_LEVEL` | `INFO` | Root log level. |
| `LOG_DIR` | `logs` | Directory for the rotating `app.log` (5 MB × 3 backups), alongside console output. Set empty for console-only. |

Frontend (`frontend/.env.local`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Backend base URL. Inlined at build time. |

> **No API key?** The app still runs. Every deterministic surface — the catalog, the always-watching evidence panel, Agent 2's audit, the mandatory-field gate, the manager console — is LLM-free by design. Only the live agent *reasoning* traces need Gemini.

---

## Run with Docker

One command brings up both services:

```bash
GEMINI_API_KEY=your-key docker compose up --build
```

Then open **http://localhost:3000**. The SQLite database lives on a named volume so data survives restarts (`SEED_RESET=false` in compose), and application logs are written to `./backend/logs/app.log` on the host.

To use a **pool** of Gemini keys instead of one (each key a separate Google project, for daily-quota failover):

```bash
GEMINI_API_KEYS=key1,key2,key3 docker compose up --build
```

> **One worker, deliberately.** Live investigation traces stream over SSE from in-memory
> per-investigation queues. With more than one worker, the request that subscribes to a
> trace can land in a different process than the one publishing it and the stream stays
> empty. Scaling out means moving those queues to a shared broker (e.g. Redis pub/sub)
> first — see [Limitations](#limitations).

---

## Demo walkthrough

The fastest path is **`/demo`** — a guided two-journey walkthrough that drives the real surfaces and the live API.

### Journey A — buyer files a dispute (the variant problem)

1. **`/orders`** — as *buyer_normal*, open the disputed **Rayon Embroidered Anarkali Kurti** order and file a fabric complaint.
2. **Agent 1 investigates live.** The trace streams over SSE: delivery-signal checks first, then the media comparison. The seller filmed only the **Black** variant; the buyer received **Blue**. Colour is excluded from the comparison *by construction*, so the honest seller is never flagged on colour — only on the invariant build attributes (weave, sheen, opacity, drape).
3. **The verdict is advisory.** Because it rests on uncertain media, Agent 1 issues `recommend_review` rather than a punishment: the listing gets a soft `flagged` status, the sale continues, and the case routes to manager **Priya**.
4. **`/manager`** — Priya rules on it. The buyer and the seller are both notified automatically, in plain language.

### Journey B — seller lists a product, Agent 2 audits it

0. **Extract a fingerprint from your own video.** Step 1 of the seller walkthrough has an **Upload a listing video** control — drop in any 5–15 s clip of fabric and the real pipeline runs on screen: OpenCV samples the keyframes, one multimodal read distils them into the seven golden fields, and the colour it recorded is shown *separately* as the thing it will never score. One click restores the seeded fingerprint. See [Extract a fingerprint live](#extract-a-fingerprint-live-from-your-own-video).
1. **`/seller/new`** — try submitting a listing with no description or measurements. The mandatory-field gate blocks it and names the exact missing fields.
2. **`/admin`** (the Agent 2 console) — hit **Run catalog audit**. Agent 2 clusters real buyer complaints, applies the deterministic delisting tiers, and drafts corrections.
3. **`/seller`** — the seller sees the drafted fix (e.g. real bag measurements) and approves it in one tap; the listing returns to full visibility.
4. **`/manager/logs`** — every action, by agent and by human, in one auditable trail.

### Other surfaces worth opening

| Route | What it shows |
| --- | --- |
| `/` and `/shop` | Buyer storefront with trust signals and at-purchase tips |
| `/product/[id]` | Product page + the always-watching evidence panel (no LLM needed) |
| `/agent1` | Agent 1 case console with live SSE traces |
| `/manager` | Manager "action needed" queue — the human decision point |
| `/manager/logs` | Full audit trail of every agent and human action |
| `/admin` | Agent 2 console: catalog audit, findings, catalog actions |

**Scenario products to try:** `prod_counterfeit_rolex` (branded, 0.07% of MRP → counterfeit path), `prod_viral_honest` (huge review spike from *established* accounts → correctly cleared), `prod_knockoff_loved` (knockoff buyers love → relabel, not ban), `prod_fabric_kurti` (the cross-variant media dispute).

---

## Seeded data

Seeded fresh on every boot from `backend/app/seed.py`:

| Entity | Count |
| --- | --- |
| Products | **20** across 7 categories (apparel, watches, beauty, electronics, footwear, home, accessories) |
| Sellers | 15 — spanning honest, sloppy, and outright fraudulent trust profiles |
| Business managers | 3 (North / South / West zones) |
| Reviews | **12,610**, with realistic account-age and recency distributions |
| Orders | 49 |
| Buyers | 2 (`buyer_normal`, `buyer_serial_claimer`) |
| Delivery hubs | 2 (one with a repeat-fraud pattern) |
| Product variants | 3 colourways of the kurti — only one was filmed |

IDs are stable and load-bearing: the frontend scenario buttons and the tests reference them directly.

---

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────────┐
│  Next.js 16 (App Router)    │  HTTP   │  FastAPI                         │
│  React 19 · Tailwind v4     │────────▶│  31 API operations               │
│                             │         │                                  │
│  buyer · seller · manager   │◀────────│  ┌────────────────────────────┐  │
│  · agent consoles · admin   │   SSE   │  │ Agent 1  orchestrator      │  │
└─────────────────────────────┘  trace  │  │  manual function-calling   │  │
                                        │  │  loop over google-genai    │  │
                                        │  └─────────┬──────────────────┘  │
                                        │            │ tools               │
                                        │  ┌─────────▼──────────────────┐  │
                                        │  │ services/  DETERMINISTIC   │  │
                                        │  │ risk_checks · delisting    │  │
                                        │  │ tripwires · fit_prediction │  │
                                        │  │ quality_fingerprint · rules│  │
                                        │  │        NO LLM              │  │
                                        │  └─────────┬──────────────────┘  │
                                        │            │                     │
                                        │  ┌─────────▼──────────────────┐  │
                                        │  │ SQLAlchemy 2.0 → SQLite    │  │
                                        │  └────────────────────────────┘  │
                                        └──────────────────────────────────┘
```

The load-bearing design rule: **the model gathers evidence, pure functions decide.** Everything in `backend/app/services/` is LLM-free, unit-tested, and importable without an API key. `services/__init__.py` enforces this as a package-level contract.

---

## AI agent architecture

### Agent 1 — the investigation loop

A **manual** function-calling loop over `google-genai` (`backend/app/agents/orchestrator.py`), deliberately not automatic function calling, so every tool call can stream to the SSE trace as it happens. Up to 8 tool steps, then one final structured call with a `response_schema` that forces a schema-valid `Verdict`.

Its four tools (`agents/agent1_tools.py`) — each backed by a deterministic service, each returning concrete numbers the agent must cite:

| Tool | Returns | LLM? |
| --- | --- | --- |
| `check_catalog_risk` | Price-vs-MRP ratio, review-burst stats, trustworthy rating, order volume, QC-video SLA | No |
| `check_seller_profile` | Account age, effective rating, trust flags, repeat-case count | No |
| `check_delivery_signals` | OTP-vs-items, hub anomaly, geo-photo proof, claimer classification | No |
| `check_media_evidence` | Variant-aware quality-fingerprint comparison | Yes (vision) |

**The verdict is executed, not just returned.** `_execute_action` applies the outcome: status changes, seller/buyer/ops notifications, catalog-action audit rows.

### The variant problem (why the vision pipeline looks like this)

A seller films **one** listing video but sells the same kurti in black, blue and red. Naively comparing a buyer's photo of the *blue* item against a listing video of the *black* one makes colour the loudest "discrepancy" — false-flagging an honest seller while burying the real complaint.

So pixels are never compared across variants. Instead:

1. The listing video is distilled **once** into variant-invariant *golden fields* — weave, sheen, fibre texture, opacity, stitch, drape, embellishment type — and cached on the product.
2. The buyer's evidence is read into that same schema.
3. A **pure, deterministic diff** (`services/quality_fingerprint.py`) — not the model, not the prompt — decides what counts as a mismatch, and it drops colour/shade *before* scoring.

A vision model therefore cannot produce a colour false-flag even if it insists the colour differs. It is also cheaper: a dispute sends the buyer's frames plus a short text fingerprint, never the listing video again.

#### Media pipeline: what runs live, and what is pre-extracted

Being precise about this, because the distinction matters:

| Stage | Default (seeded) | Implementation |
| --- | --- | --- |
| Keyframe extraction from a listing video | **On demand** — upload a clip in the demo | `vision.extract_keyframes` (OpenCV: video, stills folder, or single image) |
| Listing → golden fields | **Pre-extracted** into `seed.py` | `vision.extract_quality_fingerprint` — one multimodal call, cached on the product |
| Buyer evidence → golden fields | **Pre-extracted** into `seed.py` | `vision._read_frames` — one multimodal call |
| The mismatch verdict | **Runs live, every time** | `services/quality_fingerprint.compare_fingerprints` — pure Python, no LLM |

The reasoning: video files are large and the free Gemini tier is daily-capped, so seeding
the two attribute reads makes the demo byte-identical on every run and costs zero quota.
**The part that actually decides anything — the deterministic diff — is never seeded and
runs for real.**

#### Extract a fingerprint live, from your own video

No asset ships with the repo, so the extraction is available on demand instead. In the
**seller walkthrough** (`/demo` → *Seller: a listing, audited*) there is an
**Upload a listing video** control. Drop in a 5–15 second clip of any fabric and watch the
real pipeline run:

```
your .mp4  →  OpenCV samples up to 6 keyframes  →  one multimodal read
           →  the 7 variant-invariant golden fields, on screen
           →  the same fingerprint every dispute is judged against
```

The panel shows how many keyframes were sampled, the model's own confidence, and — set
apart — the colour/shade/print it recorded **but will never score**, which is the whole
safeguard made visible.

- `POST /products/{id}/listing-video` — upload and re-extract
- `POST /products/{id}/listing-video/reset` — restore the seeded fingerprint, so the demo
  can be run again from a known state

**It cannot break the demo.** The existing fingerprint is snapshotted before extraction and
restored on *any* failure — exhausted quota, a slow network, an undecodable codec — and the
UI says so plainly. Uploading can only improve the story, never derail it. Covered by
`tests/test_listing_video.py` (9 tests), including the quota-failure path and a check that
the flagship dispute still resolves correctly afterwards.

### Agent 2 — catalog integrity

One **batched** structured call clusters distinct negative-review complaints into fixed labels (`fabric_mismatch`, `size_issue`, `damaged_delivery`, `possible_fraud`, `other`), then a second drafts the corrected field. Both degrade gracefully: if the LLM is unavailable the audit still completes on the deterministic tier rules, and fixes fall back to a deterministic draft.

---

## Moderation workflow

### The graduated action ladder

Agent 1 always picks the **least drastic correct action**:

| # | Decision | When | Effect |
| --- | --- | --- | --- |
| 1 | `counterfeit_lock` | Hard authenticity signal **and** buyers don't vouch for it **and** the confidence floor is met | Listing locked |
| 1b | `request_qc_video` | Authenticity signal but **thin evidence** | Reversible — seller must upload a QC video within the SLA |
| 2 | `relabel_required` | Hard signal **but** high trustworthy rating | Stays live; seller must relabel honestly as a knockoff |
| 3 | `notify_only` | Inconsistency but high trustworthy rating | Sale continues; seller + support notified |
| 4 | `hold_pending_fix` | Low trustworthy rating or a fixable gap | Listing on hold |
| 4b | `recommend_review` | Conclusion rests on **uncertain media** | Advisory only — soft flag, routes to a human manager |
| 5 | `ban` | Repeat offender: low rating **and** a case pattern | Seller suspended |
| 6 | `refund_fast_track` | Dispute with **two** independent corroborating signals | Refund issued |
| 7 | `manual_review` | Serial claimer or ambiguous evidence | Routed to a human |
| 8 | `cleared` / `authentic` | No action warranted | Nothing happens |

### The safeguards that make it fair

- **Confidence floor.** A hard lock needs ≥ 20 orders of evidence *or* an overdue QC video. Below that, a `counterfeit_lock` is automatically downgraded to a reversible `request_qc_video`. Thin data never produces a punishment.
- **Trustworthy rating.** The only satisfaction measure used for decisions. Recency-weighted, and it discounts reviews from brand-new accounts *to zero* — so a fake 5-star burst cannot buy a good score, while genuine buyers of a cheap knockoff can still vouch for it.
- **Review bursts need two signals.** A spike is only fake-review evidence when it coincides with a high share of brand-new accounts. An honest viral seller (real, established accounts) is never flagged.
- **Proportional seller penalties.** A delisting penalty scales with the failed product's share of the seller's genuine reviews. 50 good products plus one small failure ≈ no impact; a one-product seller takes the full hit.
- **Two-signal refunds.** OTP-scan mismatch, hub anomaly, and a missing geo-tagged delivery photo are independent signals; two or more fast-track a refund. A serial claimer routes to manual review instead of auto-refunding. A fraudulent hub triggers immediate ops escalation and is never auto-banned (it's infrastructure).
- **Humans hold the final call.** Agents recommend and take *interim* action; the owning manager decides. A manager may only act on their own sellers' listings (enforced server-side, 403 otherwise). Every decision notifies the seller, and the buyer whenever it affects them.

### State integrity

The audit trail is only worth something if it is exact, so the write path is defensive:

- **Every write is idempotent.** `CatalogAction` and `Notification` rows use a primary key derived from *what happened, to what, in which case* (`app/idempotency.py`) rather than a random id. A repeat is a primary-key collision the database refuses, so a double-clicked button, a re-run audit, or two concurrent investigations produce one row — not three. This is a database guarantee, not a check-then-insert, which loses the race: measured, 12 threads released from a barrier previously wrote 12 duplicate locks.
- **Dedupe is scoped to the open case.** A case closes when a manager rules on it. If the product later re-offends, that *is* a new event and is recorded — suppressing it forever would be its own bug.
- **Terminal states stay terminal.** A refunded order is never refunded again, and no dispute can be opened on one. `manual_review` and `refunded` orders are excluded from new disputes, matching what the buyer's My Orders view already shows.
- **One investigation per order.** A second dispute on an order with a live investigation returns `409` instead of starting a second agent loop.
- **Only the seller's own step is self-serve.** `POST /products/{id}/reverify` clears `needs_info` — the seller responding to a quality-check request. Every manager-owned status (`locked`, `suspended`, `on_hold`, `correction_window`) returns `409` and points at the manager route, so the "managers decide" rule cannot be routed around.

All of the above is covered by `tests/test_state_integrity.py` (22 tests), which fails if any guard is removed.

---

## Repository structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/            # LLM layer
│   │   │   ├── orchestrator.py       # Agent 1 investigation loop + action execution
│   │   │   ├── agent1_tools.py       # tool declarations + dispatch table
│   │   │   ├── agent2.py             # catalog integrity: clustering + fix drafting
│   │   │   ├── vision.py             # variant-aware quality fingerprinting
│   │   │   ├── gemini_client.py      # client pool, retry + key rotation
│   │   │   ├── events.py             # SSE event bus
│   │   │   └── prompts.py            # all system prompts
│   │   ├── services/          # DETERMINISTIC decision logic — no LLM imports
│   │   │   ├── risk_checks.py        # price/MRP, review burst, trustworthy rating
│   │   │   ├── delisting.py          # complaint classification + delisting tiers
│   │   │   ├── quality_fingerprint.py# the pure variant-aware diff
│   │   │   ├── mandatory_fields.py   # listing gate
│   │   │   ├── fit_prediction.py     # size-drift prediction
│   │   │   ├── tripwires.py          # deterministic watchers
│   │   │   └── rules.py              # every threshold, in one place
│   │   ├── routers/           # FastAPI endpoints
│   │   ├── models.py          # SQLAlchemy ORM
│   │   ├── schemas.py         # Pydantic DTOs + the Verdict schema
│   │   ├── seed.py            # demo catalog + golden-path scenarios
│   │   ├── time_utils.py      # single source of UTC "now"
│   │   ├── idempotency.py     # deterministic keys — one audit row per event
│   │   ├── logging_config.py  # console + rotating file logs, moderation events
│   │   └── main.py            # app factory, CORS, lifespan
│   ├── tests/                 # 127 tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   │   ├── page.tsx              # buyer home        ├── manager/    # manager console
│   │   │   ├── shop/  product/[id]/  # storefront        ├── agent1/     # Agent 1 console
│   │   │   ├── cart/  orders/        # buyer flows       ├── admin/      # ops view
│   │   │   ├── seller/  seller/new/  # seller portal     └── demo/       # guided walkthrough
│   │   ├── components/        # TracePanel, ProductView, DisputeCard, ...
│   │   └── lib/               # typed API client, catalog helpers
│   ├── public/                # product + evidence imagery
│   └── Dockerfile
├── docs/screenshots/          # captured UI stills for the deck
├── ASSUMPTIONS.md             # product decisions and their rationale
├── ATTRIBUTION.md             # open-source dependency credits
└── docker-compose.yml
```

---

## Testing

```bash
cd backend
.venv\Scripts\activate          # source .venv/bin/activate on macOS/Linux
pytest                          # 127 tests
pytest -v                       # per-test names
pytest tests/test_api_smoke.py  # API layer only
```

Six groups, 127 in total:

- **Unit tests (66)** cover every deterministic decision rule — risk checks (13), delisting tiers (14), the quality-fingerprint diff (13), the mandatory-field gate (12), fit prediction (9), tripwires (5). They use lightweight object stand-ins, so they run in seconds with no database and no API key.
- **API smoke tests (16)** drive the real app through FastAPI's `TestClient`: health, catalog browsing, the seller listing gate, the manager queue and decisions (including the cross-manager 403), buyer dispute intake, dispute resolution, notifications, and both agent surfaces.
- **State-integrity tests (22)** lock in idempotency (repeated and concurrent agent runs write one audit row, not twelve), endpoint validation, legal state transitions, and the governance rule that a manager decision cannot be bypassed.
- **Media / listing-video tests (9)** cover the live extraction path, including the quota-failure
  case and a check that the flagship dispute still resolves correctly afterwards.
- **Delist-endpoint tests (7)** enforce the delisting tiers at the API boundary.
- **Drift tests (7)** enforce that `rules.py` really is the source of truth: every constant is consumed by real code, and no threshold is hardcoded in the prompts — the agent's instructions and the deterministic engine cannot silently diverge.

The tests run **fully offline**. Every LLM entry point is stubbed, and `tests/conftest.py` redirects `DATABASE_URL` to a dedicated `test_build_trust.db` before the app is imported — so running the suite never touches your working database.

Frontend checks:

```bash
cd frontend
npx tsc --noEmit    # type check
npm run build       # production build
npm run lint        # eslint
```

---

## Technologies

**Backend** — Python 3.11+ · FastAPI · SQLAlchemy 2.0 (typed `Mapped[]` ORM) · Pydantic v2 · `google-genai` (Gemini 3 Flash) · OpenCV (keyframe extraction) · pytest · Uvicorn

**Frontend** — Next.js 16 (App Router, Turbopack) · React 19 · TypeScript 5 · Tailwind CSS v4 · Server-Sent Events for live agent traces

**Infrastructure** — SQLite · Docker + Docker Compose

Licensed under the MIT License — see [LICENSE](LICENSE).
Full dependency credits: [ATTRIBUTION.md](ATTRIBUTION.md). Product decisions and their rationale: [ASSUMPTIONS.md](ASSUMPTIONS.md).

---

## Limitations

Honest scope notes for reviewers:

- **No authentication.** Role switching (buyer / seller / manager) is a UI affordance, not a security boundary, and every endpoint is open. Building real auth was out of scope for the hackathon; rather than ship a convincing-looking fake, there is deliberately no login or API-key UI anywhere in the app.
- **SQLite with threaded background workers.** Fine for a demo; a real deployment needs Postgres.
- **Single-process only.** SSE trace events are held in in-memory queues (`app/agents/events.py`), so the API must run with one worker. Horizontal scaling requires a shared broker for those events first.
- **No rate limiting.** `/investigate` and `/dispute` each start a background LLM loop and are unauthenticated — fine behind a demo URL, not on the open internet.
- **Media reads are seeded by default.** The listing/buyer attribute reads are pre-extracted into `seed.py` for a deterministic, zero-quota demo, and no video ships with the repo — but the extraction runs live on demand via the walkthrough's video upload. The deterministic diff that produces the verdict is never seeded. See [Media pipeline](#media-pipeline-what-runs-live-and-what-is-pre-extracted).
- **Buyer-uploaded dispute media leaves the system.** Photos and video a buyer attaches to a dispute
  are sent to an external vision model (Gemini) for attribute extraction, and are used only to
  investigate that dispute. A production deployment would need explicit buyer consent at upload and a
  retention policy; neither is implemented here.
- **Media evidence is advisory by design.** Lighting, wear, and angle make it uncertain, so it never auto-punishes — it routes to a human.
- **Seeded demo data.** Reviews and orders are synthetic, generated to exercise each decision path.
- **Gemini free tier.** Daily quota is limited, hence the API-key pool with rotation. Every deterministic surface works without a key.
