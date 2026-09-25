import type { BatchOrder, OrderInput } from "./types";
import { parseTime } from "./utils";

export interface FormState {
  order_id: string;
  order_time: string;
  day_of_week: string;
  num_items: string;
  order_value: string;
  prep_time: string;
  restaurant_load: string;
  rider_assignment_delay: string;
  pickup_wait: string;
  distance_km: string;
  traffic_level: string;
  weather: string;
  area_type: string;
  rider_experience: string;
  peak_hour: "Auto" | "Yes" | "No";
  batch_delivery: "Yes" | "No";
  promised_eta: string;
  customer_zone: string;
  restaurant_zone: string;
}

/** The worked example from the brief: a busy Friday-evening order in the rain. */
export const EXAMPLE_FORM: FormState = {
  order_id: "ZF2048",
  order_time: "20:15",
  day_of_week: "Friday",
  num_items: "5",
  order_value: "840",
  prep_time: "24",
  restaurant_load: "High",
  rider_assignment_delay: "8",
  pickup_wait: "6",
  distance_km: "7.2",
  traffic_level: "Heavy",
  weather: "Rain",
  area_type: "Dense Urban",
  rider_experience: "Moderate",
  peak_hour: "Yes",
  batch_delivery: "No",
  promised_eta: "",
  customer_zone: "",
  restaurant_zone: "",
};

type NumRule = { key: keyof FormState; label: string; min: number; max: number; integer?: boolean; exclusiveMin?: boolean; unit?: string };

const NUMERIC: NumRule[] = [
  { key: "num_items", label: "Number of items", min: 1, max: 60, integer: true },
  { key: "order_value", label: "Order value", min: 0, max: 100000, exclusiveMin: true },
  { key: "prep_time", label: "Preparation time", min: 0, max: 240, unit: "min" },
  { key: "rider_assignment_delay", label: "Rider assignment delay", min: 0, max: 180, unit: "min" },
  { key: "pickup_wait", label: "Pickup wait", min: 0, max: 180, unit: "min" },
  { key: "distance_km", label: "Distance", min: 0, max: 100, exclusiveMin: true, unit: "km" },
];

export function toOrderInput(f: FormState): { order?: OrderInput; errors: Partial<Record<keyof FormState, string>> } {
  const errors: Partial<Record<keyof FormState, string>> = {};
  const nums: Record<string, number> = {};
  if (!f.order_id.trim()) errors.order_id = "Enter an order ID.";
  if (parseTime(f.order_time) === null) errors.order_time = "Use 24-hour HH:MM, e.g. 20:15.";
  for (const r of NUMERIC) {
    const raw = f[r.key] as string;
    const v = Number(raw);
    if (raw.trim() === "" || Number.isNaN(v)) errors[r.key] = `${r.label} must be a number.`;
    else if (r.exclusiveMin ? v <= r.min : v < r.min) errors[r.key] = r.exclusiveMin ? `${r.label} must be greater than ${r.min}.` : `${r.label} cannot be negative.`;
    else if (v > r.max) errors[r.key] = `${r.label} looks implausible (max ${r.max}${r.unit ? " " + r.unit : ""}).`;
    else if (r.integer && !Number.isInteger(v)) errors[r.key] = `${r.label} must be a whole number.`;
    else nums[r.key] = v;
  }
  let promised: number | null = null;
  if (f.promised_eta.trim() !== "") {
    const v = Number(f.promised_eta);
    if (Number.isNaN(v) || v <= 0 || v > 300) errors.promised_eta = "Promised ETA must be between 1 and 300 minutes (or leave blank).";
    else promised = v;
  }
  if (Object.keys(errors).length) return { errors };
  return {
    errors,
    order: {
      order_id: f.order_id.trim(),
      order_time: f.order_time.trim(),
      day_of_week: f.day_of_week,
      num_items: nums.num_items,
      order_value: nums.order_value,
      prep_time: nums.prep_time,
      restaurant_load: f.restaurant_load,
      rider_assignment_delay: nums.rider_assignment_delay,
      pickup_wait: nums.pickup_wait,
      distance_km: nums.distance_km,
      traffic_level: f.traffic_level,
      weather: f.weather,
      area_type: f.area_type,
      rider_experience: f.rider_experience,
      peak_hour: f.peak_hour === "Auto" ? null : f.peak_hour === "Yes",
      promised_eta: promised,
      batch_delivery: f.batch_delivery === "Yes",
      customer_zone: f.customer_zone.trim() || null,
      restaurant_zone: f.restaurant_zone.trim() || null,
    },
  };
}

export function orderToForm(o: OrderInput): FormState {
  return {
    order_id: o.order_id,
    order_time: o.order_time,
    day_of_week: o.day_of_week,
    num_items: String(o.num_items),
    order_value: String(o.order_value),
    prep_time: String(o.prep_time),
    restaurant_load: o.restaurant_load,
    rider_assignment_delay: String(o.rider_assignment_delay),
    pickup_wait: String(o.pickup_wait),
    distance_km: String(o.distance_km),
    traffic_level: o.traffic_level,
    weather: o.weather,
    area_type: o.area_type,
    rider_experience: o.rider_experience,
    peak_hour: o.peak_hour === null ? "Auto" : o.peak_hour ? "Yes" : "No",
    batch_delivery: o.batch_delivery ? "Yes" : "No",
    promised_eta: o.promised_eta === null ? "" : String(o.promised_eta),
    customer_zone: o.customer_zone ?? "",
    restaurant_zone: o.restaurant_zone ?? "",
  };
}

/** Rebuilds the API input from a scored batch row (so a table row can be re-analysed in detail). */
export function batchOrderToInput(b: BatchOrder): OrderInput {
  return {
    order_id: b.order_id,
    order_time: b.order_time,
    day_of_week: b.day_of_week,
    num_items: b.num_items,
    order_value: b.order_value,
    prep_time: b.prep_time,
    restaurant_load: b.restaurant_load,
    rider_assignment_delay: b.rider_assignment_delay,
    pickup_wait: b.pickup_wait,
    distance_km: b.distance_km,
    traffic_level: b.traffic_level,
    weather: b.weather,
    area_type: b.area_type,
    rider_experience: b.rider_experience,
    peak_hour: !!b.peak_hour,
    promised_eta: b.promised_eta_estimated ? null : b.promised_eta,
    batch_delivery: !!b.batch_delivery,
  };
}
