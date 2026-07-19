"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

// How long a dropdown stays open after the pointer leaves it. Long enough that the small
// visual gap between the trigger and the panel (the `mt-1`) never closes the menu before
// the pointer crosses it — the gap is dead space with no element in it, so during that
// transit the "hovered" target briefly isn't a descendant of the trigger and a naive
// mouseleave would fire immediately. Short enough that the menu doesn't feel sticky.
const CLOSE_DELAY_MS = 220;

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
  const [lastPath, setLastPath] = useState(pathname);
  const navRef = useRef<HTMLElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset an open dropdown when the route changes — the React-recommended "adjust state
  // during render" pattern rather than an effect. This component lives in the shared
  // layout and never remounts across routes, so without this a menu left open while
  // following a top-level link would keep rendering on the destination page.
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(null);
  }

  // Stable across renders (only touches refs + setState), so the effects below can list it
  // as a dependency without re-subscribing their listeners on every render.
  const closeNow = useCallback(() => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    setOpen(null);
  }, []);

  const clearCloseTimer = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  // Open immediately, cancelling any pending close from a group the pointer just left —
  // this is what makes moving straight across the nav bar between two open groups feel
  // instant rather than flickering closed in between.
  const openGroup = (label: string) => {
    clearCloseTimer();
    setOpen(label);
  };

  // Close on a short delay instead of instantly. The dropdown sits `mt-1` below its
  // trigger — a real visual gap with no element rendered in it — so a pointer moving
  // straight down from the button to the panel spends a frame over that dead space. With
  // an immediate close, the browser treats that as "left the trigger," fires mouseleave,
  // and the menu is gone before the pointer arrives. The delay gives the pointer time to
  // land on the panel (which cancels the timer via its own onMouseEnter) before anything
  // actually closes.
  const scheduleClose = (label: string) => {
    clearCloseTimer();
    closeTimer.current = setTimeout(() => {
      setOpen((o) => (o === label ? null : o));
      closeTimer.current = null;
    }, CLOSE_DELAY_MS);
  };

  // Escape closes an open dropdown — the conventional keyboard exit. Without it a
  // keyboard user who opens a group has no way to dismiss it.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeNow();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, closeNow]);

  // Clicking (or tapping) anywhere outside the whole nav dismisses an open dropdown. This
  // matters most on touch, where there is no hover to close it and a menu left open would
  // otherwise sit there until the next tap inside the nav.
  useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent | TouchEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) closeNow();
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
    };
  }, [open, closeNow]);

  useEffect(() => () => clearCloseTimer(), []);

  const linkClass = (active: boolean) =>
    `shrink-0 whitespace-nowrap rounded-md px-2 py-1.5 font-medium transition sm:px-2.5 ` +
    // a visible keyboard focus ring; `focus-visible` keeps it off mouse clicks
    `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-1 ${
      active ? "bg-brand-wash text-brand-ink" : "text-ink-soft hover:bg-brand-wash hover:text-brand-ink"
    }`;

  return (
    // NOTE: no `overflow` here — an overflow container would clip the absolutely-positioned
    // dropdowns. Items wrap on narrow screens instead of scrolling.
    <nav ref={navRef} className="ml-auto flex flex-wrap items-center justify-end gap-0.5 text-sm">
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
            onMouseEnter={() => openGroup(e.label)}
            onMouseLeave={() => scheduleClose(e.label)}
          >
            <button
              onClick={() => (isOpen ? closeNow() : openGroup(e.label))}
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
                // Explicitly cancel/reschedule the close on the panel too, so the menu
                // stays open while the pointer is anywhere over it — not relying on the
                // wrapper's mouseenter re-firing across the trigger↔panel gap.
                onMouseEnter={() => openGroup(e.label)}
                onMouseLeave={() => scheduleClose(e.label)}
                // A bridge over the `mt-1` dead-zone: a transparent strip filling the gap so
                // the pointer is always over a real element on its way from button to menu.
                className="absolute right-0 top-full z-40 mt-1 min-w-44 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-lg before:absolute before:-top-1 before:left-0 before:h-1 before:w-full before:content-['']"
              >
                {e.items.map((i) => (
                  <Link
                    key={i.href}
                    href={i.href}
                    role="menuitem"
                    onClick={closeNow}
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
