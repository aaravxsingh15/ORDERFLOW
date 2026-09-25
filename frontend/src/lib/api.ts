import type { BatchResult, Metrics, OrderAnalysis, OrderInput } from "./types";

export class ApiError extends Error {
  status: number;
  issues: { row?: number; order_id?: string | null; field?: string; reason: string }[];
  constructor(message: string, status = 0, issues: ApiError["issues"] = []) {
    super(message);
    this.status = status;
    this.issues = issues;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("Could not reach the ORDERFLOW API. Check that the backend is running.");
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    let issues: ApiError["issues"] = [];
    try {
      const body = await res.json();
      const d = body?.detail;
      if (typeof d === "string") message = d;
      else if (d?.message) {
        message = d.message;
        issues = d.issues ?? [];
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status, issues);
  }
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  analyzeOrder: (o: OrderInput) => request<OrderAnalysis>("/api/order/analyze", json(o)),
  uploadBatch: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BatchResult>("/api/orders/batch", { method: "POST", body: fd });
  },
  demo: () => request<BatchResult>("/api/demo/orders"),
  metrics: () => request<Metrics>("/api/model/metrics"),
  async report(o: OrderInput): Promise<Blob> {
    let res: Response;
    try {
      res = await fetch("/api/report/order", json(o));
    } catch {
      throw new ApiError("Could not reach the ORDERFLOW API. Check that the backend is running.");
    }
    if (!res.ok) throw new ApiError(`Could not build the report (${res.status}).`, res.status);
    return res.blob();
  },
};

export const SAMPLE_CSV_URL = "/api/sample-csv?kind=clean";
export const SAMPLE_ISSUES_CSV_URL = "/api/sample-csv?kind=issues";
