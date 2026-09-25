"use client";

import * as React from "react";
import { AlertCircle, DatabaseZap, FileDown, FileWarning, Loader2, UploadCloud } from "lucide-react";
import { useData } from "@/components/data-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SAMPLE_CSV_URL, SAMPLE_ISSUES_CSV_URL } from "@/lib/api";
import { cn } from "@/lib/utils";

const COLUMNS =
  "order_id, order_time, day_of_week, num_items, order_value, prep_time, restaurant_load, rider_assignment_delay, pickup_wait, distance_km, traffic_level, weather, area_type, rider_experience, peak_hour, actual_delivery_time, promised_eta";

export function UploadCard() {
  const { uploadFile, loadDemo, batchLoading, batchError, clearError } = useData();
  const [drag, setDrag] = React.useState(false);
  const [fileNote, setFileNote] = React.useState<string | null>(null);
  const input = React.useRef<HTMLInputElement>(null);

  const handle = async (file: File | undefined) => {
    if (!file) return;
    clearError();
    if (!/\.csv$/i.test(file.name) && file.type !== "text/csv") {
      setFileNote(`"${file.name}" is not a CSV file. Please choose a .csv export.`);
      return;
    }
    setFileNote(null);
    await uploadFile(file);
    if (input.current) input.current.value = "";
  };

  return (
    <Card id="upload">
      <CardHeader>
        <CardTitle>Upload dataset</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={SAMPLE_CSV_URL} download><FileDown className="h-3.5 w-3.5" /> Sample CSV</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={SAMPLE_ISSUES_CSV_URL} download><FileWarning className="h-3.5 w-3.5" /> Sample with data issues</a>
          </Button>
          <Button variant="soft" size="sm" onClick={() => { clearError(); setFileNote(null); void loadDemo(); }} disabled={batchLoading}>
            <DatabaseZap className="h-3.5 w-3.5" /> Load demo data
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); void handle(e.dataTransfer.files[0]); }}
          className={cn("flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-8 text-center transition-colors", drag ? "border-red bg-red-soft" : "border-line bg-surface-2/50")}
        >
          {batchLoading ? <Loader2 className="h-7 w-7 animate-spin text-red" /> : <UploadCloud className="h-7 w-7 text-red" />}
          <p className="font-display text-base font-bold">{batchLoading ? "Running the pipeline..." : "Drop a CSV here, or browse"}</p>
          <p className="text-xs text-muted">Up to 15 MB · 50,000 rows · UTF-8 CSV. Nothing leaves your machine except the request to your own API.</p>
          <Button size="sm" onClick={() => input.current?.click()} disabled={batchLoading}>Choose CSV file</Button>
          <input ref={input} type="file" accept=".csv,text/csv" className="sr-only" aria-label="Choose CSV file" onChange={(e) => void handle(e.target.files?.[0])} />
        </div>

        {(fileNote || batchError) && (
          <div role="alert" className="mt-4 flex gap-3 rounded-2xl border border-red/40 bg-red-soft p-4 text-sm">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red" />
            <div className="min-w-0">
              <p className="font-semibold text-red">{fileNote ?? batchError?.message}</p>
              {batchError && batchError.issues.length > 0 && (
                <ul className="mt-2 max-h-44 space-y-1 overflow-auto text-xs text-muted">
                  {batchError.issues.slice(0, 20).map((i, k) => (
                    <li key={k}>{i.row ? `Row ${i.row}: ` : i.field ? `${i.field}: ` : ""}{i.reason}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-semibold text-muted hover:text-ink">Expected CSV columns</summary>
          <p className="mt-2 leading-relaxed text-muted">
            <code className="text-xs">{COLUMNS}</code>. <code className="text-xs">actual_delivery_time</code> and <code className="text-xs">promised_eta</code> are optional
            (with them ORDERFLOW also scores its own predictions against what really happened). Optional extras: <code className="text-xs">customer_zone</code>,{" "}
            <code className="text-xs">restaurant_zone</code>, <code className="text-xs">batch_delivery</code>.
          </p>
        </details>
      </CardContent>
    </Card>
  );
}
