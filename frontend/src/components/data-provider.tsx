"use client";

import * as React from "react";
import { api, ApiError } from "@/lib/api";
import type { BatchResult, OrderInput } from "@/lib/types";
import { DEMO_MODE } from "@/lib/utils";

interface DataContext {
  batch: BatchResult | null;
  batchLoading: boolean;
  batchError: ApiError | null;
  loadDemo: () => Promise<void>;
  uploadFile: (file: File) => Promise<boolean>;
  clearError: () => void;
  /** An order picked from the batch table, waiting to be analysed on the Analyse page. */
  pendingOrder: OrderInput | null;
  setPendingOrder: (o: OrderInput | null) => void;
}

const Ctx = React.createContext<DataContext | null>(null);

export function DataProvider({ children }: { children: React.ReactNode }) {
  const [batch, setBatch] = React.useState<BatchResult | null>(null);
  const [batchLoading, setLoading] = React.useState(false);
  const [batchError, setError] = React.useState<ApiError | null>(null);
  const [pendingOrder, setPendingOrder] = React.useState<OrderInput | null>(null);
  const started = React.useRef(false);

  const loadDemo = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setBatch(await api.demo());
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("Could not load demo data."));
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadFile = React.useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      setBatch(await api.uploadBatch(file));
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("Upload failed."));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    // React StrictMode runs effects twice in development; the ref keeps the demo load to a single request.
    if (DEMO_MODE && !started.current) {
      started.current = true;
      void loadDemo();
    }
  }, [loadDemo]);

  const value = React.useMemo<DataContext>(
    () => ({ batch, batchLoading, batchError, loadDemo, uploadFile, clearError: () => setError(null), pendingOrder, setPendingOrder }),
    [batch, batchLoading, batchError, loadDemo, uploadFile, pendingOrder],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData(): DataContext {
  const v = React.useContext(Ctx);
  if (!v) throw new Error("useData must be used inside <DataProvider>");
  return v;
}
