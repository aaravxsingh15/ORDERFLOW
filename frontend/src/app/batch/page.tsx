"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { UploadCard } from "@/components/batch/upload-card";
import { QualityCard } from "@/components/batch/quality-card";
import { SummaryKpis } from "@/components/batch/summary-kpis";
import {
  ActualVsPredicted, BottleneckChart, DelayByGroup, EtaByDistance, HourlyChart, ProbabilityHistogram, StatusChart,
} from "@/components/charts/charts";
import { useData } from "@/components/data-provider";
import { OrdersTable } from "@/components/orders/orders-table";
import { PageHeading } from "@/components/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { pct } from "@/lib/utils";

export default function BatchPage() {
  const { batch, batchLoading, batchError, loadDemo } = useData();
  const ev = batch?.summary.evaluation;
  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
      <PageHeading
        eyebrow="Batch analysis"
        title="Analyse a whole dataset"
        text="Upload a CSV of orders. ORDERFLOW validates and cleans it, scores every order, and summarises delay risk, ETA and bottlenecks."
      />
      <UploadCard />

      {!batch && batchLoading && (
        <div className="card flex items-center justify-center gap-3 p-12 text-muted"><Loader2 className="h-5 w-5 animate-spin" /> Analysing orders...</div>
      )}
      {!batch && !batchLoading && !batchError && (
        <div className="card p-10 text-center text-sm text-muted">
          No dataset loaded yet. Upload a CSV above, or <Button variant="soft" size="sm" onClick={() => void loadDemo()}><RefreshCw className="h-3.5 w-3.5" /> load the demo data</Button>.
        </div>
      )}

      {batch && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-line bg-surface-2 text-muted">{batch.source === "demo" ? "Demo dataset" : "Your upload"}</Badge>
            <span className="text-sm text-muted">{batch.filename ?? "orders"} · {batch.summary.orders_analysed.toLocaleString()} orders · {batch.delay_rule}</span>
            {batchLoading && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
          </div>
          <QualityCard q={batch.quality} />
          <SummaryKpis s={batch.summary} />

          {ev && (
            <Card>
              <CardHeader>
                <CardTitle>Predictions vs what actually happened</CardTitle>
                <span className="text-xs text-muted">{ev.orders_compared.toLocaleString()} orders with actual delivery times · {pct(ev.actual_delay_rate)} really ran late</span>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                  {[
                    ["Accuracy", pct(ev.classification.accuracy)], ["Precision", pct(ev.classification.precision)], ["Recall", pct(ev.classification.recall)],
                    ["F1", ev.classification.f1?.toFixed(2) ?? "-"], ["ROC-AUC", ev.classification.roc_auc?.toFixed(2) ?? "-"],
                    ["ETA MAE", `${ev.eta.mae.toFixed(1)} min`], ["ETA R²", ev.eta.r2.toFixed(2)],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-2xl bg-surface-2 p-3">
                      <p className="eyebrow">{k}</p>
                      <p className="num mt-1 text-xl font-extrabold">{v}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <StatusChart data={batch.charts.status_counts} />
            <ProbabilityHistogram data={batch.charts.probability_histogram} />
            <DelayByGroup title="Delay by traffic level" data={batch.charts.by_traffic} label="Delay probability by traffic level" />
            <DelayByGroup title="Delay by restaurant load" data={batch.charts.by_restaurant_load} label="Delay probability by restaurant load" />
            <EtaByDistance data={batch.charts.eta_by_distance} />
            <BottleneckChart data={batch.charts.bottlenecks} />
            <DelayByGroup title="Peak vs off-peak delay" data={batch.charts.peak_vs_offpeak} label="Delay probability at peak and off-peak hours" />
            <HourlyChart data={batch.charts.hourly} />
            {batch.charts.actual_vs_predicted.length > 0 ? (
              <div className="lg:col-span-2"><ActualVsPredicted data={batch.charts.actual_vs_predicted} height={300} /></div>
            ) : (
              <Card className="lg:col-span-2"><CardContent className="pt-5 text-sm text-muted">Add <code>actual_delivery_time</code> to your CSV to see actual vs predicted delivery time.</CardContent></Card>
            )}
          </div>

          <OrdersTable rows={batch.orders} truncated={batch.orders_truncated} />
        </>
      )}
    </div>
  );
}
