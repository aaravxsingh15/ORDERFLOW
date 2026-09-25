"use client";

import * as React from "react";
import { AlertCircle, Loader2, Search } from "lucide-react";
import { OrderAnalysisView } from "@/components/analysis/order-analysis";
import { OrderForm } from "@/components/analysis/order-form";
import { useData } from "@/components/data-provider";
import { PageHeading } from "@/components/page-heading";
import { api, ApiError } from "@/lib/api";
import { EXAMPLE_FORM, orderToForm, toOrderInput, type FormState } from "@/lib/order-form";
import type { OrderAnalysis, OrderInput } from "@/lib/types";
import { DEMO_MODE } from "@/lib/utils";

export default function AnalysePage() {
  const { pendingOrder, setPendingOrder } = useData();
  const [form, setForm] = React.useState<FormState>(EXAMPLE_FORM);
  const [result, setResult] = React.useState<{ analysis: OrderAnalysis; input: OrderInput } | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<ApiError | null>(null);
  const resultRef = React.useRef<HTMLDivElement>(null);
  const booted = React.useRef(false);

  const run = React.useCallback(async (order: OrderInput, scroll = false) => {
    setLoading(true);
    setError(null);
    try {
      const analysis = await api.analyzeOrder(order);
      setResult({ analysis, input: order });
      if (scroll && window.matchMedia("(max-width: 1023px)").matches) {
        requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("Analysis failed."));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    if (pendingOrder) {
      setForm(orderToForm(pendingOrder));
      void run(pendingOrder);
      setPendingOrder(null);
    } else if (DEMO_MODE) {
      const { order } = toOrderInput(EXAMPLE_FORM);
      if (order) void run(order);
    }
  }, [pendingOrder, run, setPendingOrder]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <PageHeading
        eyebrow="Analyse order"
        title="Analyse a single order"
        text="Enter an order, or start from the example, and ORDERFLOW returns the delay risk, estimated delivery time and the most likely bottleneck."
      />
      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[26rem_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-24">
          <OrderForm value={form} onChange={setForm} onSubmit={(o) => run(o, true)} loading={loading} />
        </div>
        <div ref={resultRef} className="min-w-0 scroll-mt-24">
          {error && (
            <div role="alert" className="mb-4 flex gap-3 rounded-2xl border border-red/40 bg-red-soft p-4 text-sm">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red" />
              <div>
                <p className="font-semibold text-red">{error.message}</p>
                {error.issues.length > 1 && (
                  <ul className="mt-1 list-disc pl-4 text-muted">
                    {error.issues.slice(0, 5).map((i, k) => (
                      <li key={k}>{i.field ? `${i.field}: ` : ""}{i.reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
          {result ? (
            <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>
              <OrderAnalysisView analysis={result.analysis} input={result.input} />
            </div>
          ) : (
            <div className="card flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center text-muted">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : <Search className="h-6 w-6" />}
              <p className="max-w-sm text-sm">{loading ? "Running the pipeline..." : "Fill in the order and press Analyse order to see the prediction."}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
