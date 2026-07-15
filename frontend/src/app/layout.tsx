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
  { href: "/manager", label: "Manager" },
  { href: "/admin", label: "Admin" },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-white">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3L4 8Z" fill="currentColor" />
          <path d="M8.5 8a3.5 3.5 0 1 1 7 0" stroke="#fff" strokeWidth="1.6" fill="none" />
        </svg>
      </span>
      <span className="text-2xl font-extrabold tracking-tight text-brand">meesho</span>
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
