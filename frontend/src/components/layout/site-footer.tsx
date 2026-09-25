import { DISCLAIMER } from "@/lib/utils";
import { Logo } from "./logo";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line bg-surface-2/50">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Logo />
          <p className="font-display text-sm font-bold">Designed &amp; Developed by Aarav Singh</p>
        </div>
        <p className="mt-4 max-w-3xl text-xs leading-relaxed text-muted">{DISCLAIMER}</p>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-muted">
          Predictions are based on synthetic or user-provided data and demonstrate operational ML techniques. Bottleneck outputs indicate likely
          contributing factors, not proven causes.
        </p>
      </div>
    </footer>
  );
}
