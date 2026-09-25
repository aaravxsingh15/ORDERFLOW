import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("h-8 w-8", className)} aria-hidden>
      <rect width="32" height="32" rx="9" fill="var(--red)" />
      <path d="M8 12.5h9v7h7" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="12.5" r="2.2" fill="#fff" />
      <circle cx="24" cy="19.5" r="2.2" fill="#fff" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark />
      <span className="leading-none">
        <span className="block font-display text-[1.05rem] font-extrabold tracking-tight">ORDERFLOW</span>
        <span className="mt-0.5 hidden text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-muted sm:block">Food Delivery Delay Intelligence</span>
      </span>
    </span>
  );
}
