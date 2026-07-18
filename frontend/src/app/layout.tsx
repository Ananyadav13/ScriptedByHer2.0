import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Nav } from "@/components/Nav";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Meesho · Build Trust — agentic marketplace integrity",
  description:
    "A Meesho hackathon prototype: two agentic AI systems that protect buyers and sellers — counterfeit defense, fair disputes, catalog integrity, and seller onboarding.",
};

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span
        className="grid h-9 w-9 place-items-center rounded-[11px] shadow-sm"
        style={{ background: "#55103f" }}
        aria-hidden
      >
        {/* Meesho orange "m" — thick, rounded double hump */}
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none">
          <path
            d="M9 29 V19 Q9 13 14.5 13 Q20 13 20 19 V29 M20 19 Q20 13 25.5 13 Q31 13 31 19 V29"
            stroke="#F7941D"
            strokeWidth="5.5"
            strokeLinecap="round"
            strokeLinejoin="round"
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
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:px-5">
            <div className="shrink-0">
              <Logo />
            </div>
            {/* faux marketplace search */}
            <div className="hidden min-w-0 flex-1 md:block">
              <div className="mx-auto flex max-w-md items-center gap-2 rounded-lg border border-line bg-[#f7f7fb] px-3 py-2 text-sm text-ink-faint">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                  <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                Try “cotton kurti” or “running shoes”
              </div>
            </div>
            <Nav />
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
