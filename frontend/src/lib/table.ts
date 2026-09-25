import type { BatchOrder, Status } from "./types";

export type SortKey = "order_id" | "status" | "delay_probability" | "eta_minutes" | "primary_bottleneck" | "distance_km" | "traffic_level" | "restaurant_load";
export type SortDir = "asc" | "desc";

export interface TableQuery {
  query: string;
  status: Status | "ALL";
  bottleneck: string;
  sortKey: SortKey;
  sortDir: SortDir;
}

const STATUS_RANK: Record<Status, number> = { "ON TIME": 0, "AT RISK": 1, "DELAY LIKELY": 2 };
const TRAFFIC_RANK: Record<string, number> = { Low: 0, Moderate: 1, Heavy: 2, Severe: 3 };
const LOAD_RANK: Record<string, number> = { Low: 0, Moderate: 1, High: 2, "Very High": 3 };

function sortValue(o: BatchOrder, k: SortKey): string | number {
  switch (k) {
    case "status": return STATUS_RANK[o.status];
    case "traffic_level": return TRAFFIC_RANK[o.traffic_level] ?? 0;
    case "restaurant_load": return LOAD_RANK[o.restaurant_load] ?? 0;
    case "order_id": return o.order_id.toLowerCase();
    case "primary_bottleneck": return o.primary_bottleneck.toLowerCase();
    default: return o[k];
  }
}

export function filterSort(rows: BatchOrder[], q: TableQuery): BatchOrder[] {
  const needle = q.query.trim().toLowerCase();
  const out = rows.filter((o) => {
    if (q.status !== "ALL" && o.status !== q.status) return false;
    if (q.bottleneck !== "ALL" && o.primary_bottleneck !== q.bottleneck) return false;
    if (!needle) return true;
    return [o.order_id, o.primary_bottleneck, o.secondary_bottleneck ?? "", o.traffic_level, o.restaurant_load, o.status, o.weather, o.area_type]
      .some((s) => s.toLowerCase().includes(needle));
  });
  const dir = q.sortDir === "asc" ? 1 : -1;
  return out.sort((a, b) => {
    const x = sortValue(a, q.sortKey);
    const y = sortValue(b, q.sortKey);
    if (x === y) return a.order_id.localeCompare(b.order_id, undefined, { numeric: true });
    return (x < y ? -1 : 1) * dir;
  });
}
