"use client";

// The persistent pipeline strip for the guided walkthrough. It makes the hand-offs between
// roles visible: who acts, in what order, and where you are right now. Done stops are checked,
// the active stop is filled, upcoming stops are muted.
export type RailStop = { role: string; label: string; icon: string };

export function FlowRail({ stops, active }: { stops: RailStop[]; active: number }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto rounded-xl border border-line bg-surface px-3 py-2.5 [-ms-overflow-style:none] [scrollbar-width:none]">
      {stops.map((s, i) => {
        const state = i < active ? "done" : i === active ? "active" : "todo";
        return (
          <div key={i} className="flex shrink-0 items-center">
            <div
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
                state === "active"
                  ? "bg-brand text-white"
                  : state === "done"
                    ? "bg-brand-wash text-brand-ink"
                    : "bg-[#f2f3f8] text-ink-faint"
              }`}
            >
              <span>{state === "done" ? "✓" : s.icon}</span>
              <span className="whitespace-nowrap">
                <span className="opacity-70">{s.role}</span> · {s.label}
              </span>
            </div>
            {i < stops.length - 1 && (
              <span className={`px-0.5 text-sm ${i < active ? "text-brand" : "text-line"}`}>→</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
