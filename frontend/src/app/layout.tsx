import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Meesho · Build Trust — agentic marketplace integrity",
  description:
    "A Meesho hackathon prototype: two agentic AI systems that protect buyers and sellers — counterfeit defense, fair disputes, catalog integrity, and seller onboarding.",
};

const NAV = [
  { href: "/", label: "Shop" },
  { href: "/cart", label: "Cart" },
  { href: "/seller", label: "Sell" },
  { href: "/agent1", label: "Agent 1" },
  { href: "/admin", label: "Agent 2" },
  { href: "/manager", label: "Manager" },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span
        className="grid h-9 w-9 place-items-center rounded-[11px] shadow-sm"
        style={{ background: "linear-gradient(140deg, #5a0d4d 0%, #7a1160 100%)" }}
        aria-hidden
      >
        {/* Meesho-style orange "m" */}
        <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
          <path
            d="M4 24V15c0-3.3 2.7-6 6-6 2 0 3.8 1 4.9 2.5A6 6 0 0 1 20 9c3.3 0 6 2.7 6 6v9"
            stroke="#F57C1D"
            strokeWidth="3.6"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      </span>
      <span className="text-2xl font-extrabold tracking-tight" style={{ color: "#57123f" }}>
        meesho
      </span>
      <span className="hidden rounded-md bg-brand-wash px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-brand-ink sm:inline">
        Build&nbsp;Trust
      </span>
    </Link>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-2.5">
            <Logo />
            {/* faux marketplace search */}
            <div className="hidden flex-1 md:block">
              <div className="mx-auto flex max-w-md items-center gap-2 rounded-lg border border-line bg-[#f7f7fb] px-3 py-2 text-sm text-ink-faint">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                  <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                Try “cotton kurti” or “running shoes”
              </div>
            </div>
            <nav className="ml-auto flex items-center gap-0.5 text-sm">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="rounded-md px-2.5 py-1.5 font-medium text-ink-soft transition hover:bg-brand-wash hover:text-brand-ink"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <div className="flex-1">{children}</div>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-5 py-6 text-xs text-ink-faint">
            <span className="font-semibold text-ink-soft">Build Trust</span> — a hackathon prototype of an
            agentic marketplace-integrity layer, themed as Meesho for the demo. Not the official Meesho
            app; product photos are royalty-free stock.
          </div>
        </footer>
      </body>
    </html>
  );
}
