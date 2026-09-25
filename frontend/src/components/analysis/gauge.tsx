import { STATUS_STYLE } from "@/lib/utils";
import type { Status } from "@/lib/types";

/** Ring gauge for the delay probability. */
export function ProbabilityGauge({ probability, status }: { probability: number; status: Status }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const color = STATUS_STYLE[status].color;
  return (
    <div className="relative h-36 w-36 shrink-0" role="img" aria-label={`Delay probability ${Math.round(probability * 100)} percent`}>
      <svg viewBox="0 0 130 130" className="h-full w-full -rotate-90">
        <circle cx="65" cy="65" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="11" />
        <circle
          cx="65" cy="65" r={r} fill="none" stroke={color} strokeWidth="11" strokeLinecap="round"
          strokeDasharray={`${c * probability} ${c}`} style={{ transition: "stroke-dasharray 0.7s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-[2rem] font-extrabold leading-none" style={{ color }}>{Math.round(probability * 100)}%</span>
        <span className="mt-1 text-[0.62rem] font-bold uppercase tracking-widest text-muted">delay risk</span>
      </div>
    </div>
  );
}
