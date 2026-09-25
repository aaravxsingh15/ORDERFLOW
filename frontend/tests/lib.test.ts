import { describe, expect, it } from "vitest";
import { batchOrderToInput, EXAMPLE_FORM, orderToForm, toOrderInput } from "@/lib/order-form";
import { filterSort } from "@/lib/table";
import type { BatchOrder } from "@/lib/types";
import { parseTime, toCsv } from "@/lib/utils";

const row = (o: Partial<BatchOrder>): BatchOrder => ({
  order_id: "ORD-1", order_time: "20:15", hour: 20, day_of_week: "Friday", num_items: 3, order_value: 400, prep_time: 15,
  restaurant_load: "Moderate", rider_assignment_delay: 3, pickup_wait: 3, distance_km: 3, traffic_level: "Low", weather: "Clear",
  area_type: "Urban", rider_experience: "Moderate", peak_hour: 1, batch_delivery: 0, promised_eta: 40, promised_eta_estimated: false,
  distance_category: "2-5 km", status: "ON TIME", delay_probability: 0.1, delay_confidence: "High", eta_minutes: 35,
  primary_bottleneck: "No Major Bottleneck", primary_pct: 0, secondary_bottleneck: null, secondary_pct: 0,
  actual_delivery_time: null, actual_delayed: null, outlier_flag: false, ...o,
});

describe("order form", () => {
  it("accepts the example order", () => {
    const { order, errors } = toOrderInput(EXAMPLE_FORM);
    expect(errors).toEqual({});
    expect(order).toMatchObject({ order_id: "ZF2048", num_items: 5, distance_km: 7.2, peak_hour: true, promised_eta: null });
  });

  it("reports readable errors for impossible values", () => {
    const { order, errors } = toOrderInput({ ...EXAMPLE_FORM, distance_km: "0", prep_time: "-4", num_items: "2.5", order_time: "25:99", order_id: " " });
    expect(order).toBeUndefined();
    expect(errors.distance_km).toMatch(/greater than 0/);
    expect(errors.prep_time).toMatch(/negative/);
    expect(errors.num_items).toMatch(/whole number/);
    expect(errors.order_time).toMatch(/HH:MM/);
    expect(errors.order_id).toBeTruthy();
  });

  it("round-trips between form and API shapes", () => {
    const { order } = toOrderInput(EXAMPLE_FORM);
    expect(orderToForm(order!)).toEqual(EXAMPLE_FORM);
  });

  it("drops an estimated promise when re-analysing a batch row", () => {
    expect(batchOrderToInput(row({ promised_eta_estimated: true })).promised_eta).toBeNull();
    expect(batchOrderToInput(row({ promised_eta_estimated: false, promised_eta: 44 })).promised_eta).toBe(44);
  });
});

describe("orders table logic", () => {
  const rows = [
    row({ order_id: "ORD-2", status: "DELAY LIKELY", delay_probability: 0.9, primary_bottleneck: "Rider Assignment", traffic_level: "Heavy" }),
    row({ order_id: "ORD-10", status: "AT RISK", delay_probability: 0.5, primary_bottleneck: "Restaurant Preparation" }),
    row({ order_id: "ORD-1", status: "ON TIME", delay_probability: 0.05 }),
  ];
  const base = { query: "", status: "ALL" as const, bottleneck: "ALL", sortKey: "delay_probability" as const, sortDir: "desc" as const };

  it("sorts and filters", () => {
    expect(filterSort(rows, base).map((r) => r.order_id)).toEqual(["ORD-2", "ORD-10", "ORD-1"]);
    expect(filterSort(rows, { ...base, sortKey: "order_id", sortDir: "asc" }).map((r) => r.order_id)).toEqual(["ORD-1", "ORD-10", "ORD-2"]);
    expect(filterSort(rows, { ...base, status: "AT RISK" })).toHaveLength(1);
    expect(filterSort(rows, { ...base, bottleneck: "Rider Assignment" })).toHaveLength(1);
    expect(filterSort(rows, { ...base, query: "heavy" }).map((r) => r.order_id)).toEqual(["ORD-2"]);
    expect(filterSort(rows, { ...base, query: "nomatch" })).toHaveLength(0);
  });
});

describe("utils", () => {
  it("parses times", () => {
    expect(parseTime("20:15")).toBeCloseTo(20.25);
    expect(parseTime("25:00")).toBeNull();
    expect(parseTime("abc")).toBeNull();
  });
  it("escapes CSV fields", () => {
    expect(toCsv([{ a: 'x,"y"', b: 1 }], [{ key: "a", header: "a" }, { key: "b", header: "b" }])).toBe('a,b\n"x,""y""",1');
  });
});
