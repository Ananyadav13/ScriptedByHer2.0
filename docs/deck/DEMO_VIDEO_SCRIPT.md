# Build Trust — Demo Video Script

**Target length:** 3:00 (hard cap). Timings below total 2:58, leaving a breath at the end.
**Recording against:** the deployed app — https://scripted-by-her2-0.vercel.app

---

## Before you hit record

| # | Check | Why it matters |
| --- | --- | --- |
| 1 | **Warm the backend.** Open https://scriptedbyher2-0.onrender.com/health and wait for `{"status":"ok"}`. | Render's free tier sleeps. A cold start is ~50 s of spinner on camera. Do this 2 minutes before recording and keep a tab open. |
| 2 | **Confirm the demo state is clean.** Open `/agent1` — the Rolex case should be un-run, and the kurti order should be disputable. | If a previous run already locked the listing, the live trace has nothing to do. |
| 3 | **Check your Gemini quota.** Run one investigation as a rehearsal. | The live trace is the money shot. If quota is exhausted the deterministic panels still work, but the trace won't stream. |
| 4 | Browser at **1920×1080**, zoom **90%**, bookmarks bar hidden, no extensions visible. | The UI is dense; 90% fits the agent console without scrolling mid-sentence. |
| 5 | Close Slack/mail. Do-not-disturb on. | Notification toasts on a *trust* demo look bad. |

> **Fallback if the LLM is down mid-record:** say "the reasoning layer needs a key; every deterministic
> surface you're seeing runs without one" and continue with the always-watching evidence panel. It is a
> true statement about the architecture, not an excuse — but rehearse it so it doesn't sound like one.

---

## The script

### 0:00 – 0:18 · The hook

**On screen:** Trustpilot page for Meesho — 1.4★, then the 1-star bar at 91%. Hold 3 s, then cut to the Build Trust storefront.

> Meesho averages about one-point-seven stars across public review aggregators. Reading ten thousand of
> those complaints, they don't scatter — they cluster. Counterfeits. Broken deliveries. Listings that
> lie about what they are.
>
> Every platform's answer is a report button and a queue. Mine is two agents that actually investigate.

---

### 0:18 – 0:32 · What it is

**On screen:** the storefront, scroll once through the product grid. Hover the "Trust" badges.

> This is Build Trust — a working marketplace with two autonomous agents underneath it. Agent 1
> verifies. Agent 2 audits the catalog. Both are deployed and running right now.
>
> Let me show you the moment a buyer stops trusting a product.

---

### 0:32 – 1:28 · Journey A — the buyer dispute *(the centrepiece — do not rush this)*

**On screen:** `/orders` → the Rayon Embroidered Anarkali Kurti order → **File a complaint** → fabric issue → submit.

> I bought this kurti in blue. It arrived sheer and glossy — it feels like crepe, not the opaque rayon
> the listing promised. I file a fabric complaint.

**On screen:** Agent 1 trace panel — let the SSE steps stream. **Do not cut away.** Let each tool call land visibly.

> Agent 1 picks it up and you can watch it work. Delivery signals first — was the OTP scanned for the
> right number of items, is this hub flagged, is this buyer a serial claimer. Then it compares the
> seller's listing video against my photos.
>
> And here's the part I'm proudest of. The seller only filmed the **black** kurti. I received the
> **blue** one. A naive image diff would scream "colour mismatch" and punish an honest seller.

**On screen:** highlight the golden-fields panel — weave, sheen, opacity, drape.

> So it never compares colour. The listing video is distilled once into seven attributes every
> colourway physically shares — weave, sheen, texture, opacity, stitch, drape. The comparison that
> decides is pure Python, and colour is dropped before scoring. The vision model *cannot* produce a
> colour false-flag, even if it insists the colour differs.

**On screen:** the verdict lands — `recommend_review`, advisory.

> Media evidence is uncertain by nature, so it refuses to punish on it. It issues an advisory, soft-flags
> the listing, and routes the case to a human manager.

---

### 1:28 – 1:48 · The human decision

**On screen:** `/manager` → Priya's queue → rule on the case → cut to the buyer notification.

> The manager decides. Both the buyer and the seller are notified automatically, in plain language —
> and the whole thing is one row in an auditable trail.

---

### 1:48 – 2:22 · Journey B — Agent 2 audits the catalog

**On screen:** `/seller/new` → try to submit with no measurements → the gate blocks it, naming the missing fields.

> Now the seller side. A listing with no size chart doesn't get in — the gate names exactly what's missing.

**On screen:** `/admin` → **Run catalog audit** → findings populate.

> Agent 2 sweeps the catalog. It clusters what buyers actually complain about into real defect patterns,
> and applies deterministic delisting tiers — below three stars across a thousand reviews, and it tightens
> as the rating gets worse.
>
> But it doesn't stop at flagging.

**On screen:** `/seller` → the drafted correction → **Approve** → listing returns to full visibility.

> It drafts the fix — real measurements for this bag — and hands it to the seller. One tap, and the
> listing is back to full visibility. The complaint becomes a correction instead of a dead listing.

---

### 2:22 – 2:44 · Why it's fair, not just automated

**On screen:** `/agent1` → click **Honest viral seller** scenario → it clears.

> One more, because this is what separates a trust system from a blunt instrument. This seller had a
> huge review spike — the classic fake-review signature. Agent 1 clears them, because the reviews came
> from established accounts, not new ones. A spike alone is never enough.
>
> A hard lock needs twenty orders of evidence. Refunds need two independent signals. And a knockoff
> that buyers knowingly love gets relabelled honestly — not banned.

---

### 2:44 – 2:58 · Close

**On screen:** split — the architecture slide, then the passing test run in a terminal (`127 passed`).

> Underneath all of it, one rule: the model gathers evidence, pure functions decide. Every threshold
> lives in one file, it's LLM-free, and it's covered by a hundred and twenty-seven passing tests.
>
> Authenticity matters — but not at the cost of the buyer or the seller. That's Build Trust.

---

## If you need to cut to 2:00

Drop in this order — each is self-contained:

1. **0:18–0:32 "What it is"** (−14 s) — the storefront is self-explanatory.
2. **2:22–2:44 the fairness beat** (−22 s) — painful to lose, but Journey A already shows restraint.
3. **1:28–1:48 the manager step** (−20 s) — compress to one line over a fast cut: "a human rules on it, both sides are notified."

Never cut the golden-fields explanation at 0:52–1:15. It is the single most defensible piece of
engineering in the build and the only part no other team will have.

---

## Delivery notes

- **Pace:** ~150 words/minute. The script is ~430 words of voiceover — that is deliberate, so the
  screen has room to breathe while the trace streams.
- **The trace is the star.** During 0:52–1:15, stop narrating for ~3 seconds and let the tool calls
  land on screen. Silence reads as confidence.
- **Say the numbers.** "Seven attributes", "twenty orders", "two signals", "a hundred and twenty-seven
  tests" — specifics are what make a prototype sound built rather than described.
- **Don't apologise for scope.** Say "seeded data" plainly if it comes up; the honest-limitations slide
  in the deck already covers it and judges reward it.
