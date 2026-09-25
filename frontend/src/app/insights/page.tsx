"use client";

import * as React from "react";
import { AlertCircle, GitBranch, Loader2, TrendingUp } from "lucide-react";
import { ActualVsPredicted } from "@/components/charts/charts";
import { PageHeading } from "@/components/page-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import type { Importance, Metrics, ModelMetricRow } from "@/lib/types";
import { cn, pct } from "@/lib/utils";

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl bg-surface-2 p-3.5">
      <p className="eyebrow">{label}</p>
      <p className="num mt-1 text-2xl font-extrabold">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function Features({ rows }: { rows: Importance[] }) {
  const max = Math.max(...rows.map((r) => r.importance), 1);
  return (
    <ul className="space-y-2.5">
      {rows.slice(0, 8).map((r) => (
        <li key={r.feature} className="grid grid-cols-[minmax(0,11rem)_1fr_3rem] items-center gap-3 text-sm sm:grid-cols-[14rem_1fr_3rem]">
          <span className="truncate">{r.label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-surface-2"><span className="block h-full rounded-full bg-red" style={{ width: `${(r.importance / max) * 100}%` }} /></span>
          <span className="num text-right font-bold">{r.importance.toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  );
}

function Comparison({ rows, cols }: { rows: ModelMetricRow[]; cols: { key: string; label: string; fmt: (v: number) => string }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[26rem] text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            <th className="eyebrow pb-2 pr-3">Model</th>
            {cols.map((c) => <th key={c.key} className="eyebrow pb-2 pr-3 text-right">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model} className={cn("border-b border-line/60 last:border-0", r.primary && "bg-red-soft/50")}>
              <td className="py-2 pr-3 font-semibold">{r.model}{r.primary && <Badge className="ml-2 border-red/40 bg-red-soft text-red">primary</Badge>}</td>
              {cols.map((c) => <td key={c.key} className="num py-2 pr-3 text-right">{c.fmt(Number(r[c.key]))}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Confusion({ m }: { m: Metrics["classifier"]["confusion_matrix"] }) {
  const cell = (label: string, n: number, good: boolean) => (
    <div className={cn("rounded-2xl p-4 text-center", good ? "bg-green-soft" : "bg-red-soft")}>
      <p className="num text-3xl font-extrabold">{n.toLocaleString()}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
  return (
    <div>
      <div className="grid grid-cols-[auto_1fr_1fr] items-stretch gap-2 text-center text-xs">
        <span />
        <span className="eyebrow">Predicted on time</span>
        <span className="eyebrow">Predicted delayed</span>
        <span className="eyebrow flex items-center [writing-mode:vertical-rl] rotate-180">Actually on time</span>
        {cell("true negative", m.tn, true)}
        {cell("false alarm", m.fp, false)}
        <span className="eyebrow flex items-center [writing-mode:vertical-rl] rotate-180">Actually delayed</span>
        {cell("missed delay", m.fn, false)}
        {cell("true positive", m.tp, true)}
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const [m, setM] = React.useState<Metrics | null>(null);
  const [error, setError] = React.useState<ApiError | null>(null);
  const started = React.useRef(false);

  React.useEffect(() => {
    if (started.current) return;
    started.current = true;
    api.metrics().then(setM).catch((e) => setError(e instanceof ApiError ? e : new ApiError("Could not load metrics.")));
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
      <PageHeading
        eyebrow="Model insights"
        title="Two models, evaluated on held-out data"
        text="A classifier decides whether an order will be late; a separate regressor estimates how long delivery will take. Both are scored on 20% of orders the models never saw in training."
      />
      {error && (
        <div role="alert" className="flex gap-3 rounded-2xl border border-red/40 bg-red-soft p-4 text-sm"><AlertCircle className="h-4 w-4 shrink-0 text-red" /><span className="font-semibold text-red">{error.message}</span></div>
      )}
      {!m && !error && <div className="card flex items-center justify-center gap-3 p-12 text-muted"><Loader2 className="h-5 w-5 animate-spin" /> Loading metrics...</div>}

      {m && (
        <>
          <Card>
            <CardHeader><CardTitle>Training data &amp; setup</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Tile label="Training orders" value={m.dataset.train_rows.toLocaleString()} hint={`of ${m.dataset.rows_total.toLocaleString()} synthetic orders`} />
                <Tile label="Test orders" value={m.dataset.test_rows.toLocaleString()} hint={`${Math.round(m.dataset.test_size * 100)}% held out · seed ${m.dataset.random_state}`} />
                <Tile label="Delay rate" value={pct(m.dataset.delay_rate, 1)} hint="share of orders delayed" />
                <Tile label="Features" value={`${m.classifier.features.length} / ${m.regressor.features.length}`} hint="classifier / regressor" />
              </div>
              <p className="mt-4 rounded-xl bg-surface-2 p-3 text-sm"><span className="font-semibold">Delay definition:</span> {m.config.delay_rule}. Status bands: ON TIME below {pct(m.config.on_time_below)}, AT RISK up to {pct(m.config.delay_likely_from)}, DELAY LIKELY above. Assumptions live in <code>ml/feature_config.py</code>.</p>
            </CardContent>
          </Card>

          <section aria-labelledby="clf" className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="border-red/40 bg-red-soft text-red"><GitBranch className="h-3 w-3" /> Classification</Badge>
              <h2 id="clf" className="font-display text-2xl font-extrabold">Delay classifier · {m.classifier.model}</h2>
            </div>
            <Card>
              <CardHeader><CardTitle>Held-out performance</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                  <Tile label="Accuracy" value={pct(m.classifier.metrics.accuracy, 1)} />
                  <Tile label="Precision" value={pct(m.classifier.metrics.precision, 1)} hint="flagged orders that were late" />
                  <Tile label="Recall" value={pct(m.classifier.metrics.recall, 1)} hint="late orders that were caught" />
                  <Tile label="F1 score" value={(m.classifier.metrics.f1 ?? 0).toFixed(3)} />
                  <Tile label="ROC-AUC" value={(m.classifier.metrics.roc_auc ?? 0).toFixed(3)} />
                </div>
                <div className="mt-6 grid gap-6 lg:grid-cols-2">
                  <div>
                    <h3 className="eyebrow mb-3">Confusion matrix (test set, threshold {m.config.classifier_threshold})</h3>
                    <Confusion m={m.classifier.confusion_matrix} />
                  </div>
                  <div>
                    <h3 className="eyebrow mb-3">Top features (permutation importance)</h3>
                    <Features rows={m.classifier.feature_importance} />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Model comparison</CardTitle></CardHeader>
              <CardContent>
                <Comparison rows={m.classifier.comparison} cols={[
                  { key: "accuracy", label: "Accuracy", fmt: (v) => pct(v, 1) }, { key: "precision", label: "Precision", fmt: (v) => pct(v, 1) },
                  { key: "recall", label: "Recall", fmt: (v) => pct(v, 1) }, { key: "f1", label: "F1", fmt: (v) => v.toFixed(3) }, { key: "roc_auc", label: "ROC-AUC", fmt: (v) => v.toFixed(3) },
                ]} />
                <p className="mt-3 text-xs text-muted">Random Forest is the production model. On this synthetic data the relationships are close to additive, so the linear baseline is competitive: real operational data would usually separate the models more.</p>
              </CardContent>
            </Card>
          </section>

          <section aria-labelledby="reg" className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="border-blue/40 bg-surface-2 text-blue"><TrendingUp className="h-3 w-3" /> Regression</Badge>
              <h2 id="reg" className="font-display text-2xl font-extrabold">ETA regressor · {m.regressor.model}</h2>
            </div>
            <Card>
              <CardHeader><CardTitle>Held-out performance</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Tile label="MAE" value={`${m.regressor.metrics.mae.toFixed(2)} min`} hint="average absolute error" />
                  <Tile label="RMSE" value={`${m.regressor.metrics.rmse.toFixed(2)} min`} hint="penalises big misses" />
                  <Tile label="R²" value={m.regressor.metrics.r2.toFixed(3)} hint="variance explained" />
                  <Tile label="Range coverage" value={pct(m.regressor.range_coverage)} hint="expected range holds this often" />
                </div>
                <div className="mt-6 grid gap-6 lg:grid-cols-2">
                  <div>
                    <h3 className="eyebrow mb-3">Top features (permutation importance)</h3>
                    <Features rows={m.regressor.feature_importance} />
                  </div>
                  <ActualVsPredicted data={m.regressor.actual_vs_predicted} title="Actual vs predicted (test set)" height={280} />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Model comparison</CardTitle></CardHeader>
              <CardContent>
                <Comparison rows={m.regressor.comparison} cols={[
                  { key: "mae", label: "MAE (min)", fmt: (v) => v.toFixed(2) }, { key: "rmse", label: "RMSE (min)", fmt: (v) => v.toFixed(2) }, { key: "r2", label: "R²", fmt: (v) => v.toFixed(3) },
                ]} />
                <p className="mt-3 text-xs text-muted">The baselines show what the models add: quoting the promised ETA, or always predicting the average, is clearly worse.</p>
              </CardContent>
            </Card>
          </section>

          <Card>
            <CardHeader><CardTitle>Selected features</CardTitle></CardHeader>
            <CardContent>
              <p className="mb-2 text-xs font-semibold text-muted">Classifier ({m.classifier.features.length})</p>
              <div className="flex flex-wrap gap-1.5">{m.classifier.features.map((f) => <code key={f} className="rounded-md bg-surface-2 px-2 py-0.5 text-xs">{f}</code>)}</div>
              <p className="mb-2 mt-4 text-xs font-semibold text-muted">Regressor ({m.regressor.features.length}): the same, without the promise-based features</p>
              <div className="flex flex-wrap gap-1.5">{m.regressor.features.map((f) => <code key={f} className="rounded-md bg-surface-2 px-2 py-0.5 text-xs">{f}</code>)}</div>
              <p className="mt-4 text-xs leading-relaxed text-muted">Importance shows how much the model relies on a feature on held-out data. It is not evidence of causation. Trained {new Date(m.dataset.trained_at).toLocaleDateString()} with scikit-learn {m.dataset.sklearn_version}.</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
