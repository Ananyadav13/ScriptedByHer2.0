import Link from "next/link";
import type { Tone } from "@/lib/decisions";

const TONE_BADGE: Record<Tone, string> = {
  green: "bg-green-wash text-green",
  rose: "bg-rose-wash text-rose",
  amber: "bg-amber-wash text-amber",
  brand: "bg-brand-wash text-brand-ink",
  teal: "bg-teal-wash text-teal",
  neutral: "bg-[#eef0f4] text-ink-soft",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE_BADGE[tone]}`}
    >
      {children}
    </span>
  );
}

export function Card({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-surface shadow-[0_1px_2px_rgba(16,20,34,0.04)] ${className}`}
    >
      {children}
    </div>
  );
}

type BtnProps = {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "md" | "sm";
  className?: string;
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

const BTN_BASE =
  "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand";
const BTN_VARIANT = {
  primary: "bg-brand text-white hover:bg-brand-ink shadow-sm",
  secondary: "border border-line bg-surface text-ink hover:bg-[#f2f3f8]",
  ghost: "text-brand-ink hover:bg-brand-wash",
  danger: "bg-rose text-white hover:brightness-95",
};
const BTN_SIZE = { md: "px-4 py-2.5 text-sm", sm: "px-3 py-1.5 text-xs" };

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: BtnProps) {
  return (
    <button className={`${BTN_BASE} ${BTN_VARIANT[variant]} ${BTN_SIZE[size]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  variant = "primary",
  size = "md",
  className = "",
  children,
}: {
  href: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "sm";
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`${BTN_BASE} ${BTN_VARIANT[variant]} ${BTN_SIZE[size]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      aria-hidden
    />
  );
}

export function SectionTitle({
  eyebrow,
  title,
  sub,
}: {
  eyebrow?: string;
  title: string;
  sub?: string;
}) {
  return (
    <div className="mb-5">
      {eyebrow && (
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand">{eyebrow}</div>
      )}
      <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
      {sub && <p className="mt-1 text-sm text-ink-soft">{sub}</p>}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-surface p-8 text-center text-sm text-ink-faint">
      {children}
    </div>
  );
}

export function Page({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>;
}
