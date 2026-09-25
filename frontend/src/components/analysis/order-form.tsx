"use client";

import * as React from "react";
import { Loader2, RotateCcw, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Segmented, Select } from "@/components/ui/field";
import { EXAMPLE_FORM, toOrderInput, type FormState } from "@/lib/order-form";
import { AREAS, DAYS, EXPERIENCE, LOADS, TRAFFIC, WEATHER, type OrderInput } from "@/lib/types";

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="min-w-0">
      <legend className="eyebrow mb-2.5">{title}</legend>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </fieldset>
  );
}

export function OrderForm({
  value,
  onChange,
  onSubmit,
  loading,
}: {
  value: FormState;
  onChange: (f: FormState) => void;
  onSubmit: (o: OrderInput) => void;
  loading: boolean;
}) {
  const [errors, setErrors] = React.useState<Partial<Record<keyof FormState, string>>>({});
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => onChange({ ...value, [k]: v });
  const num = (k: keyof FormState, extra?: React.InputHTMLAttributes<HTMLInputElement>) => (
    <Input inputMode="decimal" type="number" step="any" value={value[k] as string} onChange={(e) => set(k, e.target.value as never)} aria-invalid={!!errors[k]} {...extra} />
  );
  const sel = (k: keyof FormState, options: readonly string[]) => (
    <Select value={value[k] as string} onChange={(e) => set(k, e.target.value as never)}>
      {options.map((o) => (
        <option key={o}>{o}</option>
      ))}
    </Select>
  );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const { order, errors: errs } = toOrderInput(value);
    setErrors(errs);
    if (order) onSubmit(order);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order details</CardTitle>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => { onChange(EXAMPLE_FORM); setErrors({}); }}>
            <RotateCcw className="h-3.5 w-3.5" /> Load example
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate className="space-y-5">
          <Group title="Order">
            <Field label="Order ID" error={errors.order_id}>
              <Input value={value.order_id} onChange={(e) => set("order_id", e.target.value)} aria-invalid={!!errors.order_id} />
            </Field>
            <Field label="Order time" hint="24h" error={errors.order_time}>
              <Input value={value.order_time} placeholder="20:15" onChange={(e) => set("order_time", e.target.value)} aria-invalid={!!errors.order_time} />
            </Field>
            <Field label="Day of week">{sel("day_of_week", DAYS)}</Field>
            <Field label="Items" error={errors.num_items}>{num("num_items")}</Field>
            <Field label="Order value" hint="₹" error={errors.order_value}>{num("order_value")}</Field>
            <Field label="Batch delivery">
              <Segmented label="Batch delivery" value={value.batch_delivery} onChange={(v) => set("batch_delivery", v as "Yes" | "No")} options={["No", "Yes"]} />
            </Field>
          </Group>

          <Group title="Restaurant">
            <Field label="Preparation time" hint="min" error={errors.prep_time}>{num("prep_time")}</Field>
            <Field label="Restaurant load">{sel("restaurant_load", LOADS)}</Field>
          </Group>

          <Group title="Rider">
            <Field label="Assignment delay" hint="min" error={errors.rider_assignment_delay}>{num("rider_assignment_delay")}</Field>
            <Field label="Pickup wait" hint="min" error={errors.pickup_wait}>{num("pickup_wait")}</Field>
            <Field label="Rider experience" className="col-span-2">{sel("rider_experience", EXPERIENCE)}</Field>
          </Group>

          <Group title="Route & conditions">
            <Field label="Distance" hint="km" error={errors.distance_km}>{num("distance_km")}</Field>
            <Field label="Peak hour">
              <Segmented label="Peak hour" value={value.peak_hour} onChange={(v) => set("peak_hour", v as FormState["peak_hour"])} options={["Yes", "No", "Auto"]} />
            </Field>
            <Field label="Traffic">{sel("traffic_level", TRAFFIC)}</Field>
            <Field label="Weather">{sel("weather", WEATHER)}</Field>
            <Field label="Area type" className="col-span-2">{sel("area_type", AREAS)}</Field>
          </Group>

          <Group title="Optional">
            <Field label="Promised ETA" hint="min · blank = baseline quote" error={errors.promised_eta} className="col-span-2">
              {num("promised_eta", { placeholder: "e.g. 42" })}
            </Field>
            <Field label="Customer zone" hint="not scored">
              <Input value={value.customer_zone} onChange={(e) => set("customer_zone", e.target.value)} placeholder="Z3" />
            </Field>
            <Field label="Restaurant zone" hint="not scored">
              <Input value={value.restaurant_zone} onChange={(e) => set("restaurant_zone", e.target.value)} placeholder="Z5" />
            </Field>
          </Group>

          <p className="text-xs text-muted">Weekend is derived from the day of week. Peak &quot;Auto&quot; derives it from the order time (12:00-14:30, 19:00-22:30).</p>
          <Button type="submit" size="lg" className="w-full" disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {loading ? "Analysing" : "Analyse order"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
