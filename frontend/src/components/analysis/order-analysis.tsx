"use client";

import * as React from "react";
import { FileDown, Info, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { DeliveryTimeline } from "@/components/pipeline/delivery-timeline";
import { api, ApiError } from "@/lib/api";
import type { OrderAnalysis, OrderInput } from "@/lib/types";
import { download } from "@/lib/utils";
import { BottleneckCard } from "./bottleneck-card";
import { ProbabilityGauge } from "./gauge";
import { ImportanceBars } from "./importance-bars";

function Metric({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-surface-2 p-3.5">
      <p className="eyebrow">{label}</p>
      <p className="num mt-1 text-2xl font-extrabold leading-tight">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

export function OrderAnalysisView({ analysis: a, input }: { analysis: OrderAnalysis; input: OrderInput }) {
  const [pdfBusy, setPdfBusy] = React.useState(false);
  const [pdfError, setPdfError] = React.useState<string | null>(null);

  const downloadPdf = async () => {
    setPdfBusy(true);
    setPdfError(null);
    try {
      download(`orderflow_${a.order_id}.pdf`, await api.report(input), "application/pdf");
    } catch (e) {
      setPdfError(e instanceof ApiError ? e.message : "Could not build the report.");
    } finally {
      setPdfBusy(false);
    }
  };

  const late = a.expected_delay_minutes;
  return (
    <div className="space-y-5" data-testid="order-analysis">
      <Card>
        <CardContent className="pt-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="eyebrow">ORDERFLOW · Order intelligence</p>
              <h2 className="mt-1.5 flex flex-wrap items-center gap-3 font-display text-2xl font-extrabold">
                Order {a.order_id}
                <StatusBadge status={a.status} />
              </h2>
            </div>
            <Button variant="outline" size="sm" onClick={downloadPdf} disabled={pdfBusy}>
              {pdfBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileDown className="h-3.5 w-3.5" />} Download PDF report
            </Button>
          </div>
          {pdfError && <p role="alert" className="mt-2 text-sm text-red">{pdfError}</p>}

          <div className="mt-5 flex flex-col items-center gap-5 sm:flex-row sm:items-stretch">
            <ProbabilityGauge probability={a.delay_probability} status={a.status} />
            <div className="grid w-full flex-1 grid-cols-2 gap-3 lg:grid-cols-3">
              <Metric label="Estimated delivery" value={`${Math.round(a.eta.minutes)} min`} sub={`likely ${Math.round(a.eta.low)}-${Math.round(a.eta.high)} min`} />
              <Metric
                label="Expected delay"
                value={`${Math.round(late)} min`}
                sub={`vs promised ${Math.round(a.promised_eta)} min${a.promised_eta_estimated ? " (baseline quote)" : ""}`}
              />
              <Metric label="Prediction confidence" value={a.delay_confidence} sub={`ETA estimate: ${a.eta.confidence}`} />
            </div>
          </div>

          <div className="mt-5 flex items-start gap-2 rounded-xl border border-line bg-surface-2/60 p-3 text-sm text-muted">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{a.summary}</p>
          </div>
          {a.warnings.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-orange">
              {a.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          <BottleneckCard b={a.bottleneck} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          <h3 className="eyebrow mb-5">Delivery pipeline</h3>
          <DeliveryTimeline stages={a.pipeline.stages} total={a.pipeline.total_minutes} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          <ImportanceBars items={a.explanation} status={a.status} />
        </CardContent>
      </Card>
      <p className="px-1 text-xs text-muted">{a.delay_rule}. Thresholds live in <code>ml/feature_config.py</code>.</p>
    </div>
  );
}
