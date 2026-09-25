import * as React from "react";
import { cn } from "@/lib/utils";

const control =
  "h-10 w-full rounded-xl border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted/70 transition-colors hover:border-muted/50 focus:border-red focus:outline-none focus:ring-2 focus:ring-red/20 disabled:opacity-50";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(control, className)} {...props} />
));
Input.displayName = "Input";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(control, "appearance-none bg-[length:16px] bg-[right_0.65rem_center] bg-no-repeat pr-8", className)}
    style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23999' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")" }}
    {...props}>
    {children}
  </select>
));
Select.displayName = "Select";

export function Field({ label, hint, error, children, className }: { label: string; hint?: string; error?: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1 flex items-baseline justify-between gap-2 text-xs font-semibold text-ink">
        {label}
        {hint && <span className="font-normal text-muted">{hint}</span>}
      </span>
      {children}
      {error && <span role="alert" className="mt-1 block text-xs text-red">{error}</span>}
    </label>
  );
}

export function Segmented({ value, onChange, options, label }: { value: string; onChange: (v: string) => void; options: string[]; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex h-10 rounded-xl border border-line bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={value === o}
          onClick={() => onChange(o)}
          className={cn("flex-1 rounded-[10px] text-sm font-semibold transition-colors", value === o ? "bg-surface text-red shadow-sm" : "text-muted hover:text-ink")}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
