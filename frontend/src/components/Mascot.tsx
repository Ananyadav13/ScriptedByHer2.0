"use client";

// "Trusty" — the friendly face of the whole Build Trust AI system. Buyers and sellers meet
// Trusty; the Agent 1 / Agent 2 consoles are its technical back-office. One character, so the
// AI reads as a single helpful presence rather than two abstract "agents".
export function Trusty({ mood = "happy", size = 96 }: { mood?: "happy" | "think" | "cheer"; size?: number }) {
  const eye = mood === "think" ? 3 : 4;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      className="bt-bob"
      role="img"
      aria-label="Trusty, the Build Trust AI guide"
    >
      <defs>
        <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e11d74" />
          <stop offset="1" stopColor="#8a1c6b" />
        </linearGradient>
        <radialGradient id="tglow" cx="0.5" cy="0.4" r="0.6">
          <stop offset="0" stopColor="#ff5ba0" stopOpacity="0.35" />
          <stop offset="1" stopColor="#ff5ba0" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="60" cy="60" r="52" fill="url(#tglow)" />
      <ellipse cx="60" cy="108" rx="26" ry="5" fill="#000" opacity="0.06" />
      <rect x="30" y="34" width="60" height="60" rx="20" fill="url(#tg)" />
      {/* shield emblem */}
      <path d="M60 50 l14 5 v10 c0 9 -6 15 -14 18 c-8 -3 -14 -9 -14 -18 v-10 z" fill="#fff" opacity="0.96" />
      <path d="M54 66 l4 4 l8 -9" stroke="#8a1c6b" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {/* eyes */}
      <circle cx="48" cy="46" r={eye} fill="#fff" />
      <circle cx="72" cy="46" r={eye} fill="#fff" />
      {/* antenna */}
      <line x1="60" y1="34" x2="60" y2="23" stroke="#8a1c6b" strokeWidth="3" />
      <circle cx="60" cy="20" r="4.5" fill={mood === "cheer" ? "#0d9488" : "#ff9ec7"} />
      {/* mouth */}
      {mood === "cheer" ? (
        <path d="M50 74 q10 10 20 0" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" />
      ) : mood === "think" ? (
        <circle cx="60" cy="76" r="2.5" fill="#fff" />
      ) : (
        <path d="M52 74 q8 7 16 0" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" />
      )}
    </svg>
  );
}

/** The Trusty wordmark lockup — mascot + name, so "Trusty" is always visible, not implied. */
export function TrustyMark({
  size = 40,
  tagline,
  mood = "happy",
}: {
  size?: number;
  tagline?: string;
  mood?: "happy" | "think" | "cheer";
}) {
  return (
    <div className="flex items-center gap-2.5">
      <Trusty size={size} mood={mood} />
      <div className="leading-tight">
        <div className="flex items-center gap-1.5">
          <span className="text-base font-extrabold tracking-tight text-ink">Trusty</span>
          <span className="rounded-full bg-brand-wash px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-brand-ink">
            AI
          </span>
        </div>
        {tagline && <div className="text-xs text-ink-faint">{tagline}</div>}
      </div>
    </div>
  );
}

export function SpeechBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative rounded-2xl rounded-bl-none border border-line bg-surface px-4 py-3 text-sm text-ink shadow-sm">
      {children}
      <span className="absolute -bottom-2 left-4 h-4 w-4 rotate-45 border-b border-l border-line bg-surface" />
    </div>
  );
}
