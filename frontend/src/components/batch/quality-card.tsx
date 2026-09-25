import { ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Quality } from "@/lib/types";

function Stat({ label, value, tone }: { label: string; value: number; tone?: "warn" | "bad" }) {
  return (
    <div className="rounded-2xl bg-surface-2 p-3.5">
      <p className="eyebrow">{label}</p>
      <p className={`num mt-1 text-2xl font-extrabold ${tone === "bad" && value > 0 ? "text-red" : tone === "warn" && value > 0 ? "text-orange" : ""}`}>{value.toLocaleString()}</p>
    </div>
  );
}

export function QualityCard({ q }: { q: Quality }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Data quality</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Stat label="Rows uploaded" value={q.rows_uploaded} />
          <Stat label="Rows valid" value={q.rows_valid} />
          <Stat label="Rows removed" value={q.rows_removed} tone="bad" />
          <Stat label="Missing values fixed" value={q.missing_values_fixed} tone="warn" />
          <Stat label="Outliers flagged" value={q.outliers_flagged} tone="warn" />
        </div>
        {q.warnings.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-orange">
            {q.warnings.map((w) => (
              <li key={w}>⚠ {w}</li>
            ))}
          </ul>
        )}
        {q.issues.length > 0 && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-semibold text-muted hover:text-ink">
              Why were {q.rows_removed} row(s) removed? ({Object.entries(q.issue_counts).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(", ")})
            </summary>
            <ul className="mt-2 max-h-56 space-y-1 overflow-auto rounded-xl bg-surface-2 p-3 text-xs">
              {q.issues.map((i, k) => (
                <li key={k}>
                  <span className="font-semibold">Row {i.row}{i.order_id ? ` (${i.order_id})` : ""}:</span> <span className="text-muted">{i.reason}</span>
                </li>
              ))}
              {q.issues_truncated && <li className="text-muted">...and more (first 100 shown).</li>}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
