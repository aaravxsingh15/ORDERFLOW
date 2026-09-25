import type { Influence, Status } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ImportanceBars({ items, status }: { items: Influence[]; status: Status }) {
  const max = Math.max(...items.map((i) => i.influence_pct), 1);
  return (
    <div>
      <h3 className="eyebrow">{status === "ON TIME" ? "What shapes this order's risk?" : "Why was this order flagged?"}</h3>
      <ul className="mt-4 space-y-3.5">
        {items.map((it) => {
          const tone = it.direction === "increases" ? "bg-red" : it.direction === "reduces" ? "bg-green" : "bg-line";
          const sign = it.direction === "increases" ? "+" : it.direction === "reduces" ? "−" : "";
          return (
            <li key={it.label}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="font-semibold">
                  {it.label} <span className="font-normal text-muted">· {it.value}</span>
                </span>
                <span className="num shrink-0 font-extrabold">{sign}{Math.round(it.influence_pct)}%</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${it.label} ${it.direction} delay risk, ${Math.round(it.influence_pct)} percent of model influence`}>
                <div className={cn("h-full rounded-full transition-[width] duration-700", tone)} style={{ width: `${(it.influence_pct / max) * 100}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red" /> raises delay risk</span>
        <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-green" /> lowers it</span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-muted">
        Feature importance shows model influence and does not prove direct causation. Each bar is the change in delay probability when that input is set to a typical value.
      </p>
    </div>
  );
}
