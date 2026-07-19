# Prototype Submission — form field copy

Paste-ready content for each field on the submission form.

---

## Title

```
Build Trust — Agentic AI for Authenticity & Catalog Integrity
```

---

## Description

> The form's editor supports formatting. Bold the agent names and keep the paragraph breaks.

**Build Trust** is a working marketplace with two autonomous AI agents underneath it, built to act on
evidence rather than route buyers into a support queue. It is deployed and running end to end.

**Agent 1 — Verification & Authenticity.** Fires when a buyer hits Buy Now, when a deterministic
tripwire trips, or when a post-delivery dispute is filed. It runs four evidence tools — catalog risk,
seller profile, delivery signals, and a variant-aware media comparison — reasons over the numbers in a
streaming function-calling loop, and then *executes* a graduated action: clear, notify, relabel, request
a quality-check video, hold, refund, lock, or route to a human.

**Agent 2 — Listing & Catalog Integrity.** Continuously audits the catalog, clusters what buyers
actually complain about into real defect patterns, applies deterministic delisting tiers, and drafts the
corrected size chart or fabric description for the seller to approve in one tap.

**The load-bearing design rule: the model gathers evidence, pure functions decide.** Every decision lives
in an LLM-free, unit-tested service layer that is importable without an API key. The reasoning layer can
never quietly become the thing that decides.

**The hardest problem solved here is the variant problem.** A seller films one listing video but sells the
same kurti in black, blue and red. Naively diffing a buyer's photo of the blue item against a video of the
black one makes colour the loudest discrepancy and false-flags an honest seller. So the listing video is
distilled once into seven variant-invariant attributes — weave, sheen, fibre texture, opacity, stitch,
drape, embellishment type — and a pure deterministic diff drops colour before scoring. The vision model
cannot produce a colour false-flag even if it insists the colour differs.

**Fairness is enforced in code, not promised in a prompt.** A hard lock needs 20+ orders of evidence or it
auto-downgrades to a reversible request. A review spike only counts as fraud evidence alongside a high
share of new accounts, so honest viral sellers are cleared. Refunds need two independent corroborating
signals. Seller penalties scale with the product's share of that seller's genuine reviews. Managers hold
the final call and may only act on their own sellers, enforced server-side.

**Scale:** 31 API operations, 127 passing tests, 20 seeded products across 7 categories, 15 sellers and
12,610 reviews generated to exercise every decision path.

**Honest scope:** no authentication, SQLite rather than Postgres, single-process SSE, and synthetic seed
data. These are stated plainly in the deck rather than papered over.

---

## Video URL

```
<paste your recorded demo link — YouTube unlisted or Drive with link-sharing on>
```

⚠️ If you use Google Drive, set sharing to **"Anyone with the link — Viewer"** and open it in a private
window to confirm. A permission-locked video is the most common way a submission loses its demo score.

---

## Demo Link

```
https://scripted-by-her2-0.vercel.app
```

---

## Repository URL

```
<your GitHub repo URL>
```

---

## Instructions to Run

> The form gives you a rich-text box. Use the numbered list button for the steps.

**Fastest path: just open the deployed app** — https://scripted-by-her2-0.vercel.app — no setup needed.
The guided walkthrough at `/demo` drives the real surfaces and the live API.
*(The backend is on Render's free tier and sleeps when idle. The first request may take ~50 seconds to
wake it; every request after that is fast.)*

**To run it locally.** Requires Python 3.11+ and Node 20+.

1. **Backend** → http://localhost:8000
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # source .venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   cp .env.example .env            # then add your GEMINI_API_KEY
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend** → http://localhost:3000
   ```
   cd frontend
   npm install
   npm run dev
   ```

3. Open **http://localhost:3000/demo** for the guided two-journey walkthrough.

The database is SQLite and seeds itself on startup — no migrations. Interactive API docs are at
http://localhost:8000/docs.

**Or with Docker**, one command:
```
GEMINI_API_KEY=your-key docker compose up --build
```

**No API key?** The app still runs. The catalog, the always-watching evidence panel, Agent 2's audit, the
mandatory-field gate and the manager console are all LLM-free by design. Only the live agent *reasoning*
traces need Gemini.

**To run the tests:**
```
cd backend && pytest        # 127 tests, fully offline, no API key required
```

**What to look at first**

| Route | What it shows |
| --- | --- |
| `/demo` | Guided two-journey walkthrough — start here |
| `/agent1` | Agent 1 console with live SSE investigation traces |
| `/admin` | Agent 2 console — run a catalog audit |
| `/manager` | The human decision queue |
| `/manager/logs` | Full audit trail of every agent and human action |

**Scenario products:** `prod_counterfeit_rolex` (branded, 0.07% of MRP → counterfeit path),
`prod_viral_honest` (huge review spike from established accounts → correctly cleared),
`prod_knockoff_loved` (knockoff buyers love → relabel, not ban), `prod_fabric_kurti` (the cross-variant
media dispute).

---

## Snapshots to upload

From `docs/screenshots/` — recommended order:

1. `01-landing.png` — buyer storefront
2. `06-agent1-console.png` — Agent 1 evidence + live trace
3. `05-agent2-catalog.png` — Agent 2 catalog audit
4. `07-manager-sellers.png` — manager decision queue
5. `08-seller-portal.png` — seller portal with the drafted fix
