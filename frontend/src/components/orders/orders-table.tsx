"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Download, Search } from "lucide-react";
import { useData } from "@/components/data-provider";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { batchOrderToInput } from "@/lib/order-form";
import { filterSort, type SortDir, type SortKey } from "@/lib/table";
import type { BatchOrder, Status } from "@/lib/types";
import { cn, download, toCsv } from "@/lib/utils";

const PAGE = 15;
const COLS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "order_id", label: "Order ID" },
  { key: "status", label: "Predicted status" },
  { key: "delay_probability", label: "Delay prob.", align: "right" },
  { key: "eta_minutes", label: "Pred. ETA", align: "right" },
  { key: "primary_bottleneck", label: "Primary bottleneck" },
  { key: "distance_km", label: "Distance", align: "right" },
  { key: "traffic_level", label: "Traffic" },
  { key: "restaurant_load", label: "Restaurant load" },
];

export function OrdersTable({ rows, truncated }: { rows: BatchOrder[]; truncated?: boolean }) {
  const router = useRouter();
  const { setPendingOrder } = useData();
  const [query, setQuery] = React.useState("");
  const [status, setStatus] = React.useState<Status | "ALL">("ALL");
  const [bottleneck, setBottleneck] = React.useState("ALL");
  const [sortKey, setSortKey] = React.useState<SortKey>("delay_probability");
  const [sortDir, setSortDir] = React.useState<SortDir>("desc");
  const [page, setPage] = React.useState(0);

  const bottlenecks = React.useMemo(() => Array.from(new Set(rows.map((r) => r.primary_bottleneck))).sort(), [rows]);
  const view = React.useMemo(() => filterSort(rows, { query, status, bottleneck, sortKey, sortDir }), [rows, query, status, bottleneck, sortKey, sortDir]);
  const pages = Math.max(1, Math.ceil(view.length / PAGE));
  const current = Math.min(page, pages - 1);
  const slice = view.slice(current * PAGE, current * PAGE + PAGE);

  const sortBy = (k: SortKey) => {
    if (k === sortKey) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(k);
      setSortDir(k === "order_id" || k === "primary_bottleneck" ? "asc" : "desc");
    }
    setPage(0);
  };

  const exportCsv = () => {
    const data = view.map((o) => ({ ...o, delay_probability: Number(o.delay_probability.toFixed(4)), eta_minutes: Number(o.eta_minutes.toFixed(1)) }));
    download(
      "orderflow_predictions.csv",
      toCsv(data, [
        { key: "order_id", header: "order_id" }, { key: "status", header: "predicted_status" }, { key: "delay_probability", header: "delay_probability" },
        { key: "eta_minutes", header: "predicted_eta_min" }, { key: "primary_bottleneck", header: "primary_bottleneck" }, { key: "secondary_bottleneck", header: "secondary_bottleneck" },
        { key: "distance_km", header: "distance_km" }, { key: "traffic_level", header: "traffic_level" }, { key: "restaurant_load", header: "restaurant_load" },
        { key: "promised_eta", header: "promised_eta" }, { key: "actual_delivery_time", header: "actual_delivery_time" },
      ]),
    );
  };

  const open = (o: BatchOrder) => {
    setPendingOrder(batchOrderToInput(o));
    router.push("/analyse");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order table</CardTitle>
        <Button variant="outline" size="sm" onClick={exportCsv} disabled={view.length === 0}>
          <Download className="h-3.5 w-3.5" /> Export CSV ({view.length.toLocaleString()})
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 sm:grid-cols-[1fr_11rem_13rem]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input aria-label="Search orders" placeholder="Search order, bottleneck, traffic..." className="pl-9" value={query} onChange={(e) => { setQuery(e.target.value); setPage(0); }} />
          </div>
          <Select aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value as Status | "ALL"); setPage(0); }}>
            <option value="ALL">All statuses</option>
            <option>ON TIME</option>
            <option>AT RISK</option>
            <option>DELAY LIKELY</option>
          </Select>
          <Select aria-label="Filter by bottleneck" value={bottleneck} onChange={(e) => { setBottleneck(e.target.value); setPage(0); }}>
            <option value="ALL">All bottlenecks</option>
            {bottlenecks.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </Select>
        </div>

        <div className="-mx-5 mt-4 overflow-x-auto px-5">
          <table className="w-full min-w-[46rem] text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                {COLS.map((c) => {
                  const active = c.key === sortKey;
                  const Icon = !active ? ArrowUpDown : sortDir === "asc" ? ArrowUp : ArrowDown;
                  return (
                    <th key={c.key} scope="col" aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"} className={cn("pb-2 pr-3", c.align === "right" && "text-right")}>
                      <button type="button" onClick={() => sortBy(c.key)} className={cn("eyebrow inline-flex items-center gap-1 hover:!text-ink", active && "!text-ink")}>
                        {c.label} <Icon className="h-3 w-3" />
                      </button>
                    </th>
                  );
                })}
                <th className="pb-2"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {slice.map((o) => (
                <tr key={o.order_id} className="border-b border-line/60 last:border-0 hover:bg-surface-2/60">
                  <td className="py-2.5 pr-3 font-semibold">{o.order_id}</td>
                  <td className="py-2.5 pr-3"><StatusBadge status={o.status} /></td>
                  <td className="num py-2.5 pr-3 text-right font-bold">{Math.round(o.delay_probability * 100)}%</td>
                  <td className="num py-2.5 pr-3 text-right">{Math.round(o.eta_minutes)} min</td>
                  <td className="py-2.5 pr-3">{o.primary_bottleneck}</td>
                  <td className="num py-2.5 pr-3 text-right">{o.distance_km.toFixed(1)} km</td>
                  <td className="py-2.5 pr-3">{o.traffic_level}</td>
                  <td className="py-2.5 pr-3">{o.restaurant_load}</td>
                  <td className="py-2.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => open(o)} aria-label={`Analyse order ${o.order_id} in detail`}>Details</Button>
                  </td>
                </tr>
              ))}
              {slice.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-muted">No orders match these filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          <span>
            {view.length === 0 ? "0 orders" : `${current * PAGE + 1}-${Math.min((current + 1) * PAGE, view.length)} of ${view.length.toLocaleString()} orders`}
            {truncated && " (table capped; the analytics above cover every order)"}
          </span>
          <span className="flex items-center gap-1">
            <Button variant="outline" size="icon" aria-label="Previous page" disabled={current === 0} onClick={() => setPage(current - 1)}><ChevronLeft className="h-4 w-4" /></Button>
            <span className="px-2 font-semibold text-ink">{current + 1} / {pages}</span>
            <Button variant="outline" size="icon" aria-label="Next page" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}><ChevronRight className="h-4 w-4" /></Button>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
