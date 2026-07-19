"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API, api, type MediaEvidence, type TraceEvent, type Verdict } from "@/lib/api";
import { decisionMeta, toolMeta } from "@/lib/decisions";
import { Badge, Button, Card, Spinner } from "@/components/ui";
import { MediaEvidenceCard } from "@/components/MediaEvidenceCard";

type Step = {
  name: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  done: boolean;
};

type Phase = "idle" | "running" | "done" | "error";

// Poll fallback budget: 1.2s x 50 = 60s, comfortably longer than a real investigation
// (8 tool steps + a verdict call) while still terminating.
const POLL_INTERVAL_MS = 1200;
const POLL_MAX_ATTEMPTS = 50;

// summarise a deterministic tool result dict into one human line.
function resultLine(r: unknown): { text: string; flag?: boolean } {
  if (r == null || typeof r !== "object") return { text: String(r ?? "") };
  const o = r as Record<string, unknown>;
  const flag = typeof o.flag === "boolean" ? o.flag : undefined;
  const reason =
    (o.reason as string) ||
    (o.classification as string) ||
    (o.summary as string) ||
    (o.note as string);
  if (reason) return { text: reason, flag };
  const keys = Object.entries(o)
    .filter(([, v]) => typeof v !== "object")
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${v}`)
    .join(" · ");
  return { text: keys || "checked", flag };
}

export function TracePanel({
  label = "Verify before you buy",
  sublabel,
  start,
  autoStart = false,
  onResolve,
}: {
  label?: string;
  sublabel?: string;
  start: () => Promise<string>;
  autoStart?: boolean;
  onResolve?: (verdict: Verdict | null) => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [steps, setSteps] = useState<Step[]>([]);
  const [statusMsg, setStatusMsg] = useState<string>("");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [error, setError] = useState<string>("");
  const esRef = useRef<EventSource | null>(null);
  const startedRef = useRef(false);
  const verdictRef = useRef<Verdict | null>(null);
  const resolvedRef = useRef(false);
  const onResolveRef = useRef(onResolve);
  // Tracks whether this component is still mounted. Every async continuation checks it
  // before touching state, so navigating away mid-investigation cannot schedule work
  // against a component that no longer exists.
  const aliveRef = useRef(true);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Writing to a ref during render is a React 19 violation (it breaks under concurrent
  // rendering, where a render may be discarded). An effect is the correct place.
  useEffect(() => {
    onResolveRef.current = onResolve;
  }, [onResolve]);

  // Release every resource this component owns. Without it, leaving the page mid-trace
  // left the SSE connection open and the poll chain rescheduling itself indefinitely.
  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      esRef.current?.close();
      esRef.current = null;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    };
  }, []);

  // fire onResolve exactly once when the investigation settles
  useEffect(() => {
    if (resolvedRef.current) return;
    if (verdict) {
      resolvedRef.current = true;
      onResolveRef.current?.(verdict);
    } else if (phase === "error" || phase === "done") {
      resolvedRef.current = true;
      onResolveRef.current?.(null);
    }
  }, [verdict, phase]);

  const applyEvent = useCallback((ev: TraceEvent) => {
    switch (ev.type) {
      case "status":
        setStatusMsg(ev.status);
        break;
      case "tool_call":
        setSteps((s) => [...s, { name: ev.name, args: ev.args, done: false }]);
        break;
      case "tool_result":
        setSteps((s) => {
          const copy = [...s];
          for (let i = copy.length - 1; i >= 0; i--) {
            if (copy[i].name === ev.name && !copy[i].done) {
              copy[i] = {
                ...copy[i],
                result: ev.result as Record<string, unknown>,
                done: true,
              };
              break;
            }
          }
          return copy;
        });
        break;
      case "verdict":
        verdictRef.current = ev;
        setVerdict(ev);
        break;
      case "error":
        setError(ev.error);
        setPhase("error");
        break;
    }
  }, []);

  // Fallback: SSE dropped or the investigation finished before we subscribed.
  //
  // Bounded on purpose. This used to reschedule itself forever with no ceiling, so an
  // investigation that never reached a terminal status — a backend restarted mid-run
  // leaves one stuck on "running" — polled every 1.2s for as long as the tab stayed open.
  // POLL_MAX_ATTEMPTS covers comfortably longer than a real investigation takes, then
  // surfaces an honest error instead of spinning silently.
  const pollUntilSettled = useCallback(async (id: string) => {
    // A loop rather than a self-rescheduling callback: the termination condition is one
    // visible bound instead of a recursion that has to be traced to be trusted.
    for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt++) {
      if (!aliveRef.current) return;
      try {
        const inv = await api.investigation(id);
        if (!aliveRef.current) return;
        if (inv.verdict) {
          verdictRef.current = inv.verdict;
          setVerdict(inv.verdict);
        }
        if (inv.status === "done" || inv.verdict) {
          setPhase("done");
          return;
        }
        if (inv.status === "error") {
          setError("Investigation failed.");
          setPhase("error");
          return;
        }
      } catch {
        if (!aliveRef.current) return;
        setError("Could not reach the backend.");
        setPhase("error");
        return;
      }
      // interruptible wait — the unmount cleanup clears this timer
      await new Promise<void>((resolve) => {
        pollTimerRef.current = setTimeout(resolve, POLL_INTERVAL_MS);
      });
    }
    if (!aliveRef.current) return;
    setError("The investigation is taking longer than expected — check the agent console.");
    setPhase("error");
  }, []);

  const run = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    setPhase("running");
    setSteps([]);
    setVerdict(null);
    setError("");
    setStatusMsg("starting…");
    let id: string;
    try {
      id = await start();
    } catch {
      if (!aliveRef.current) return;
      setError("Could not start the investigation — is the backend running?");
      setPhase("error");
      return;
    }
    // Unmounted while the POST was in flight: never open a stream nobody is watching.
    if (!aliveRef.current) return;

    const es = new EventSource(`${API}/events/${id}`);
    esRef.current = es;
    es.onmessage = (m) => {
      if (!aliveRef.current) return;
      let ev: TraceEvent;
      try {
        ev = JSON.parse(m.data);
      } catch {
        return;
      }
      if (ev.type === "done") {
        es.close();
        setPhase((p) => (p === "error" ? p : "done"));
        return;
      }
      if (ev.type === "closed") {
        es.close();
        void pollUntilSettled(id); // already finished — read the final verdict
        return;
      }
      applyEvent(ev);
    };
    es.onerror = () => {
      es.close();
      if (!aliveRef.current) return;
      // SSE dropped mid-flight → poll for the final state
      if (!verdictRef.current) void pollUntilSettled(id);
    };
  }, [start, applyEvent, pollUntilSettled]);

  // Auto-start on mount (the dispute flow renders this already-started, after the buyer
  // has picked a claim type). `startedRef` inside `run` makes a second invocation a no-op,
  // so React 18+ StrictMode's double-effect cannot open two investigations.
  useEffect(() => {
    if (autoStart) void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dm = verdict ? decisionMeta(verdict.decision) : null;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <div className="text-sm font-semibold text-ink">Live agent trace</div>
          {sublabel && <div className="text-xs text-ink-faint">{sublabel}</div>}
        </div>
        {phase === "idle" && (
          <Button onClick={run}>
            <span>🛡️</span>
            {label}
          </Button>
        )}
        {phase === "running" && (
          <span className="flex items-center gap-2 text-sm text-ink-soft">
            <Spinner /> investigating…
          </span>
        )}
        {phase === "done" && <Badge tone="green">complete</Badge>}
        {phase === "error" && <Badge tone="rose">error</Badge>}
      </div>

      <div className="px-5 py-4">
        {phase === "idle" && (
          <p className="text-sm text-ink-soft">
            An autonomous agent gathers deterministic evidence, reasons over it, and takes an
            action. You&apos;ll watch every step stream in live.
          </p>
        )}

        {phase === "error" && (
          <div className="rounded-xl bg-rose-wash px-4 py-3 text-sm text-rose">{error}</div>
        )}

        {(steps.length > 0 || phase === "running") && (
          <ol className="space-y-2.5">
            {steps.map((s, i) => {
              const tm = toolMeta(s.name);
              const rl = s.result ? resultLine(s.result) : null;
              // a media-evidence result renders as a VISUAL comparison, not a text line
              const media =
                s.name === "check_media_evidence" && s.result && (s.result as MediaEvidence).available
                  ? (s.result as MediaEvidence)
                  : null;
              const mismatch = media?.mismatch;
              return (
                <li key={i} className="bt-rise flex gap-3">
                  <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-wash text-base">
                    {tm.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-ink">{tm.label}</span>
                      {!s.done ? (
                        <Spinner className="text-brand" />
                      ) : media ? (
                        <Badge tone={mismatch ? "rose" : "green"}>{mismatch ? "mismatch" : "consistent"}</Badge>
                      ) : rl?.flag === true ? (
                        <Badge tone="rose">signal</Badge>
                      ) : rl?.flag === false ? (
                        <Badge tone="green">clear</Badge>
                      ) : null}
                    </div>
                    {media ? (
                      <div className="mt-2">
                        <MediaEvidenceCard ev={media} fallbackImg={media.product_id ?? "prod_fabric_kurti"} />
                      </div>
                    ) : rl ? (
                      <p className="mt-0.5 text-sm text-ink-soft">{rl.text}</p>
                    ) : null}
                  </div>
                </li>
              );
            })}
            {phase === "running" && !verdict && (
              <li className="flex gap-3">
                <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#eef0f4]">
                  <span className="bt-pulse text-base">🧠</span>
                </div>
                <div className="flex items-center text-sm text-ink-faint">
                  {statusMsg === "running" || !statusMsg ? "reasoning over evidence…" : statusMsg}
                </div>
              </li>
            )}
          </ol>
        )}

        {verdict && dm && (
          <div className="mt-4 rounded-xl border border-line bg-[#fbfbfe] p-4 bt-rise">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge tone={dm.tone}>{dm.label}</Badge>
              <span className="text-xs text-ink-faint">
                confidence {Math.round((verdict.confidence ?? 0) * 100)}%
              </span>
            </div>
            <p className="mt-3 text-sm text-ink">{verdict.buyer_explanation}</p>
            {verdict.evidence?.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {verdict.evidence.map((e, i) => (
                  <li key={i} className="flex gap-2 text-sm text-ink-soft">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    {e}
                  </li>
                ))}
              </ul>
            )}
            {verdict.suggested_remedy ? (
              <div className="mt-3 rounded-lg bg-teal-wash px-3 py-2 text-sm text-teal">
                Recommended to a human manager: {verdict.suggested_remedy}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </Card>
  );
}
