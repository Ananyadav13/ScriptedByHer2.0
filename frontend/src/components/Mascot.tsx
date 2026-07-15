"use client";

// "Trusty" — a lightweight SVG onboarding companion. No animation engine; pure SVG + CSS bob.
export function Trusty({ mood = "happy", size = 96 }: { mood?: "happy" | "think" | "cheer"; size?: number }) {
  const eye = mood === "think" ? 3 : 4;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      className="bt-bob"
      role="img"
      aria-label="Trusty, the onboarding guide"
    >
      {/* body */}
      <defs>
        <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#6366f1" />
          <stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
      </defs>
      <ellipse cx="60" cy="108" rx="26" ry="5" fill="#000" opacity="0.06" />
      <rect x="30" y="34" width="60" height="60" rx="20" fill="url(#tg)" />
      {/* shield emblem */}
      <path d="M60 50 l14 5 v10 c0 9 -6 15 -14 18 c-8 -3 -14 -9 -14 -18 v-10 z" fill="#fff" opacity="0.95" />
      <path d="M54 66 l4 4 l8 -9" stroke="#4f46e5" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {/* eyes */}
      <circle cx="48" cy="46" r={eye} fill="#fff" />
      <circle cx="72" cy="46" r={eye} fill="#fff" />
      {/* antenna */}
      <line x1="60" y1="34" x2="60" y2="24" stroke="#4f46e5" strokeWidth="3" />
      <circle cx="60" cy="21" r="4" fill={mood === "cheer" ? "#0d9488" : "#a5b4fc"} />
      {/* smile */}
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

export function SpeechBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative rounded-2xl rounded-bl-none border border-line bg-surface px-4 py-3 text-sm text-ink shadow-sm">
      {children}
      <span className="absolute -bottom-2 left-4 h-4 w-4 rotate-45 border-b border-l border-line bg-surface" />
    </div>
  );
}
