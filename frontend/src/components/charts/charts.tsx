"use client";

import * as React from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Charts, GroupRow, Status } from "@/lib/types";
import { STATUS_STYLE } from "@/lib/utils";

const RED = "var(--red)";
const ORANGE = "var(--orange)";
const GREEN = "var(--green)";
const BLUE = "var(--blue)";
const GRID = "var(--line)";

const tooltipStyle: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, fontSize: 12, color: "var(--ink)", boxShadow: "var(--shadow)",
};
const axis = { stroke: GRID, tickLine: false } as const;
const pctFmt = (v: unknown) => `${Math.round(Number(v) * 100)}%`;

export function ChartCard({ title, note, height = 250, label, children }: { title: string; note?: string; height?: number; label: string; children: React.ReactElement }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div role="img" aria-label={label} style={{ height }} className="w-full">
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
        {note && <p className="mt-2 text-xs text-muted">{note}</p>}
      </CardContent>
    </Card>
  );
}

export function ProbabilityHistogram({ data }: { data: Charts["probability_histogram"] }) {
  return (
    <ChartCard title="Delay probability distribution" label="Histogram of predicted delay probability across orders" note="Orders per 10% probability band. Green < 30% (on time), orange 30-60% (at risk), red ≥ 60% (delay likely).">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="bin" {...axis} interval={0} tick={{ fontSize: 10 }} />
        <YAxis {...axis} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }} formatter={(v) => [String(v), "Orders"]} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={i < 3 ? GREEN : i < 6 ? ORANGE : RED} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}

export function ActualVsPredicted({ data, title = "Actual vs predicted delivery time", height = 260 }: { data: { actual: number; predicted: number }[]; title?: string; height?: number }) {
  const max = Math.ceil(Math.max(...data.map((d) => Math.max(d.actual, d.predicted)), 10) / 10) * 10;
  const min = Math.floor(Math.min(...data.map((d) => Math.min(d.actual, d.predicted)), 10) / 10) * 10;
  return (
    <ChartCard title={title} height={height} label="Scatter plot of actual against predicted delivery time in minutes" note="Each dot is an order; the dashed line is a perfect prediction.">
      <ScatterChart margin={{ top: 8, right: 12, left: -8, bottom: 14 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis type="number" dataKey="actual" name="Actual" domain={[min, max]} {...axis} label={{ value: "Actual (min)", position: "insideBottom", offset: -8, fontSize: 11, fill: "var(--muted)" }} />
        <YAxis type="number" dataKey="predicted" name="Predicted" domain={[min, max]} {...axis} label={{ value: "Predicted (min)", angle: -90, position: "insideLeft", offset: 12, fontSize: 11, fill: "var(--muted)" }} />
        <ReferenceLine segment={[{ x: min, y: min }, { x: max, y: max }]} stroke="var(--muted)" strokeDasharray="5 4" />
        <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: "3 3" }} formatter={(v) => `${Number(v).toFixed(0)} min`} />
        <Scatter data={data} fill={RED} fillOpacity={0.45} />
      </ScatterChart>
    </ChartCard>
  );
}

export function StatusChart({ data }: { data: Charts["status_counts"] }) {
  const total = data.reduce((a, d) => a + d.count, 0) || 1;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Orders by status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <div role="img" aria-label="Donut chart of orders by predicted status" className="h-[190px] w-[190px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="count" nameKey="status" innerRadius={56} outerRadius={84} paddingAngle={2} stroke="var(--surface)" strokeWidth={2}>
                  {data.map((d) => (
                    <Cell key={d.status} fill={STATUS_STYLE[d.status as Status].color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [String(v), "Orders"]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="min-w-0 flex-1 space-y-2.5 text-sm">
            {data.map((d) => (
              <li key={d.status} className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 font-semibold">
                  <i className="h-2.5 w-2.5 rounded-full" style={{ background: STATUS_STYLE[d.status as Status].color }} />
                  {d.status}
                </span>
                <span className="num font-extrabold">{d.count} <span className="font-normal text-muted">({Math.round((d.count / total) * 100)}%)</span></span>
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

export function DelayByGroup({ title, data, label }: { title: string; data: GroupRow[]; label: string }) {
  const hasActual = data.some((d) => d.actual_delay_rate != null);
  return (
    <ChartCard title={title} label={label} note={hasActual ? "Predicted = average model delay probability; actual = share of orders that really ran late." : "Average model delay probability per group."}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...axis} />
        <YAxis {...axis} tickFormatter={pctFmt} domain={[0, 1]} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }} formatter={(v) => pctFmt(v)} />
        {hasActual && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        <Bar dataKey="avg_delay_probability" name="Predicted" fill={RED} radius={[6, 6, 0, 0]} />
        {hasActual && <Bar dataKey="actual_delay_rate" name="Actual" fill={BLUE} radius={[6, 6, 0, 0]} />}
      </BarChart>
    </ChartCard>
  );
}

export function EtaByDistance({ data }: { data: GroupRow[] }) {
  const hasActual = data.some((d) => d.actual_avg != null);
  return (
    <ChartCard title="Average ETA by distance" label="Average predicted delivery time by distance band" note="Minutes, by delivery distance band.">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...axis} />
        <YAxis {...axis} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }} formatter={(v) => `${Number(v).toFixed(0)} min`} />
        {hasActual && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        <Bar dataKey="avg_eta" name="Predicted" fill={RED} radius={[6, 6, 0, 0]} />
        {hasActual && <Bar dataKey="actual_avg" name="Actual" fill={BLUE} radius={[6, 6, 0, 0]} />}
      </BarChart>
    </ChartCard>
  );
}

export function BottleneckChart({ data }: { data: Charts["bottlenecks"] }) {
  return (
    <ChartCard title="Bottleneck distribution" height={Math.max(220, data.length * 34 + 30)} label="Number of orders by primary bottleneck" note="Primary likely contributing factor per order.">
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 0 }}>
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" {...axis} allowDecimals={false} />
        <YAxis type="category" dataKey="name" width={150} {...axis} tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }} formatter={(v) => [String(v), "Orders"]} />
        <Bar dataKey="count" radius={[0, 6, 6, 0]}>
          {data.map((d, i) => (
            <Cell key={d.name} fill={d.name === "No Major Bottleneck" ? "var(--muted)" : i === 0 ? RED : ORANGE} fillOpacity={d.name === "No Major Bottleneck" ? 0.4 : 1} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}

export function HourlyChart({ data }: { data: Charts["hourly"] }) {
  const hasActual = data.some((d) => d.actual_delay_rate != null);
  return (
    <ChartCard title="Hourly delay pattern" label="Delay probability by hour of day" note="Delay risk by order hour. Lunch and dinner rushes usually stand out." height={260}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...axis} interval="preserveStartEnd" />
        <YAxis {...axis} tickFormatter={pctFmt} domain={[0, 1]} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => pctFmt(v)} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="avg_delay_probability" name="Predicted" stroke={RED} strokeWidth={2.5} dot={{ r: 3 }} />
        {hasActual && <Line type="monotone" dataKey="actual_delay_rate" name="Actual" stroke={BLUE} strokeWidth={2} strokeDasharray="5 4" dot={false} connectNulls />}
      </LineChart>
    </ChartCard>
  );
}
