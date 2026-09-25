import { Card } from "@/components/ui/card";
import type { Summary } from "@/lib/types";
import { cn, fmt, pct } from "@/lib/utils";

function Kpi({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: string; tone?: "green" | "orange" | "red" }) {
  return (
    <Card className="p-4">
      <p className="eyebrow">{label}</p>
      <p className={cn("num mt-1.5 break-words text-2xl font-extrabold leading-tight", tone === "green" && "text-green", tone === "orange" && "text-orange", tone === "red" && "text-red")}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </Card>
  );
}

export function SummaryKpis({ s }: { s: Summary }) {
  const share = (n: number) => `${Math.round((n / (s.orders_analysed || 1)) * 100)}% of orders`;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Kpi label="Orders analysed" value={s.orders_analysed.toLocaleString()} />
      <Kpi label="Predicted on time" value={s.on_time.toLocaleString()} sub={share(s.on_time)} tone="green" />
      <Kpi label="Orders at risk" value={s.at_risk.toLocaleString()} sub={share(s.at_risk)} tone="orange" />
      <Kpi label="Likely delayed" value={s.delay_likely.toLocaleString()} sub={share(s.delay_likely)} tone="red" />
      <Kpi label="Average predicted ETA" value={`${fmt(s.avg_eta_minutes, 0)} min`} />
      <Kpi label="Average delay probability" value={pct(s.avg_delay_probability)} />
      <Kpi label="Most common bottleneck" value={s.most_common_bottleneck} />
      <Kpi label="Worst delay window" value={s.worst_delay_window ?? "-"} sub="highest average delay risk" />
    </div>
  );
}
