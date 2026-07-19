"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string };
type Group = { label: string; items: Item[] };
type Entry = Item | Group;

const NAV: Entry[] = [
  { href: "/demo", label: "Walkthrough" },
  {
    label: "Buyer",
    items: [
      { href: "/", label: "Product catalogue" },
      { href: "/cart", label: "Cart" },
      { href: "/orders", label: "Your orders" },
    ],
  },
  { href: "/seller", label: "Seller" },
  {
    label: "Manager",
    items: [
      { href: "/manager", label: "Action needed" },
      { href: "/manager/logs", label: "Logs" },
    ],
  },
  { href: "/agent1", label: "Agent 1" },
  { href: "/admin", label: "Agent 2" },
];

function isGroup(e: Entry): e is Group {
  return (e as Group).items !== undefined;
}

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState<string | null>(null);

  // Escape closes an open dropdown — the conventional keyboard exit. Without it a
  // keyboard user who opens a group has no way to dismiss it.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const linkClass = (active: boolean) =>
    `shrink-0 whitespace-nowrap rounded-md px-2 py-1.5 font-medium transition sm:px-2.5 ` +
    // a visible keyboard focus ring; `focus-visible` keeps it off mouse clicks
    `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-1 ${
      active ? "bg-brand-wash text-brand-ink" : "text-ink-soft hover:bg-brand-wash hover:text-brand-ink"
    }`;

  return (
    // NOTE: no `overflow` here — an overflow container would clip the absolutely-positioned
    // dropdowns. Items wrap on narrow screens instead of scrolling.
    <nav className="ml-auto flex flex-wrap items-center justify-end gap-0.5 text-sm">
      {NAV.map((e) => {
        if (!isGroup(e)) {
          const active = pathname === e.href;
          return (
            <Link key={e.href} href={e.href} className={linkClass(active)}>
              {e.label}
            </Link>
          );
        }
        const groupActive = e.items.some((i) => pathname === i.href);
        const isOpen = open === e.label;
        const menuId = `nav-menu-${e.label.toLowerCase().replace(/\s+/g, "-")}`;
        return (
          <div
            key={e.label}
            className="relative shrink-0"
            onMouseEnter={() => setOpen(e.label)}
            onMouseLeave={() => setOpen((o) => (o === e.label ? null : o))}
          >
            <button
              onClick={() => setOpen((o) => (o === e.label ? null : e.label))}
              className={linkClass(groupActive) + " inline-flex items-center gap-1"}
              aria-expanded={isOpen}
              aria-haspopup="menu"
              aria-controls={menuId}
            >
              {e.label}
              {/* decorative caret: the button already announces its expanded state */}
              <span aria-hidden="true" className="text-[10px] text-ink-faint">▾</span>
            </button>
            {isOpen && (
              <div
                id={menuId}
                role="menu"
                aria-label={e.label}
                className="absolute right-0 top-full z-40 mt-1 min-w-44 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-lg"
              >
                {e.items.map((i) => (
                  <Link
                    key={i.href}
                    href={i.href}
                    role="menuitem"
                    onClick={() => setOpen(null)}
                    className={`block px-3.5 py-2 text-sm transition focus-visible:outline-none focus-visible:bg-brand-wash ${
                      pathname === i.href ? "bg-brand-wash font-medium text-brand-ink" : "text-ink-soft hover:bg-[#f5f3f9]"
                    }`}
                  >
                    {i.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
