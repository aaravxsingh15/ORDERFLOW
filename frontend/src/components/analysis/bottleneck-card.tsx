import { CheckCircle2 } from "lucide-react";
import type { OrderAnalysis } from "@/lib/types";
import { cn } from "@/lib/utils";

const NONE = "No Major Bottleneck";

export function BottleneckCard({ b }: { b: OrderAnalysis["bottleneck"] }) {
  const none = b.primary.name === NONE;
  return (
    <div>
      <h3 className="eyebrow">Bottleneck detection</h3>
      {none ? (
        <div className="mt-3 flex items-start gap-3 rounded-2xl bg-green-soft p-4 text-green">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-display text-lg font-extrabold">No major bottleneck</p>
            <p className="text-sm text-ink/80">No delivery stage runs meaningfully past its normal duration for this order.</p>
          </div>
        </div>
      ) : (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-red/30 bg-red-soft p-4">
            <p className="text-[0.7rem] font-bold uppercase tracking-wider text-red">Primary bottleneck</p>
            <p className="mt-1 font-display text-xl font-extrabold leading-tight">{b.primary.name}</p>
            <p className="mt-1 text-sm text-muted">
              Contribution <span className="num font-extrabold text-ink">{Math.round(b.primary.contribution_pct)}%</span> · ~{b.primary.minutes.toFixed(0)} min
            </p>
          </div>
          <div className={cn("rounded-2xl border p-4", b.secondary ? "border-orange/30 bg-orange-soft" : "border-line bg-surface-2")}>
            <p className={cn("text-[0.7rem] font-bold uppercase tracking-wider", b.secondary ? "text-orange" : "text-muted")}>Secondary factor</p>
            <p className="mt-1 font-display text-xl font-extrabold leading-tight">{b.secondary?.name ?? "None significant"}</p>
            {b.secondary && (
              <p className="mt-1 text-sm text-muted">
                Contribution <span className="num font-extrabold text-ink">{Math.round(b.secondary.contribution_pct)}%</span> · ~{b.secondary.minutes.toFixed(0)} min
              </p>
            )}
          </div>
        </div>
      )}
      {!none && b.contributions.length > 0 && (
        <ul className="mt-4 space-y-2">
          {b.contributions.slice(0, 6).map((c, i) => (
            <li key={c.name} className="grid grid-cols-[minmax(0,9.5rem)_1fr_2.6rem] items-center gap-3 text-sm sm:grid-cols-[11rem_1fr_2.6rem]">
              <span className={cn("truncate", i === 0 ? "font-bold" : "text-muted")}>{c.name}</span>
              <span className="h-2 overflow-hidden rounded-full bg-surface-2">
                <span className={cn("block h-full rounded-full", i === 0 ? "bg-red" : i === 1 ? "bg-orange" : "bg-muted/40")} style={{ width: `${c.pct}%` }} />
              </span>
              <span className="num text-right font-bold">{Math.round(c.pct)}%</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs leading-relaxed text-muted">
        Likely contributing factors, shown as a share of the excess minutes identified across stages. They are not proven causes. {b.method}
      </p>
    </div>
  );
}
