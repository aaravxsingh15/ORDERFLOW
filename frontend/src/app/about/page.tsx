import { PageHeading } from "@/components/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DISCLAIMER } from "@/lib/utils";

export const metadata = { title: "About - ORDERFLOW" };

const PIPELINE = [
  ["Validation", "Rejects negative times, zero or negative distance, impossible order values, invalid categories, malformed timestamps, duplicate order IDs and empty files, with a readable reason for every row."],
  ["Cleaning", "Normalises text and units (\"Rs. 1,240\", \"24 min\", \"very high\"), imputes only fields that are safe to impute, removes duplicates, flags and clips extreme outliers, and reports a data-quality summary."],
  ["Feature engineering", "Adds pre-pickup time, operational delay, per-item ratios, assignment and pickup delay ratios, a peak-hour score, traffic and load scores, order complexity, estimated travel burden and a combined operational-pressure index."],
  ["Delay classifier", "RandomForestClassifier on a Pipeline with one-hot encoding. Returns the delay probability, class and confidence. LogisticRegression and GradientBoosting are trained for comparison."],
  ["ETA regressor", "RandomForestRegressor predicts total delivery minutes. The expected range comes from held-out residual quantiles, and confidence from how much the trees agree."],
  ["Bottleneck detector", "Rules measure each stage's excess minutes over a normal duration; a what-if re-prediction of the ETA model is blended in at 30%. Output is a likely contributing factor, never a proven cause."],
  ["Report", "A one-page PDF with status, probability, ETA, bottleneck, pipeline and feature contributions."],
];

const CSV = [
  ["order_id", "Unique order identifier"], ["order_time", "HH:MM (24h), 8:15 PM, or a full date-time"], ["day_of_week", "Monday-Sunday (optional if order_time has a date)"],
  ["num_items", "Whole number ≥ 1"], ["order_value", "Positive amount (₹)"], ["prep_time", "Restaurant preparation, minutes"], ["restaurant_load", "Low, Moderate, High, Very High"],
  ["rider_assignment_delay", "Minutes waiting for a rider"], ["pickup_wait", "Minutes the rider waited at the restaurant"], ["distance_km", "Greater than 0"],
  ["traffic_level", "Low, Moderate, Heavy, Severe"], ["weather", "Clear, Rain, Fog, Hot, Cold"], ["area_type", "Urban, Dense Urban, Suburban"],
  ["rider_experience", "New, Moderate, Experienced"], ["peak_hour", "Yes/No (derived from order_time if absent)"],
  ["promised_eta", "Optional. Minutes; a baseline quote is used if absent"], ["actual_delivery_time", "Optional. Enables scoring against reality"],
  ["customer_zone, restaurant_zone, batch_delivery", "Optional extras"],
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-10 sm:px-6">
      <PageHeading
        eyebrow="About"
        title="ORDERFLOW predicts delays before they happen"
        text="It predicts whether food-delivery orders will be delayed, estimates delivery time, and identifies the likely operational bottleneck behind each delay."
      />

      <Card>
        <CardHeader><CardTitle>The delay definition</CardTitle></CardHeader>
        <CardContent>
          <p className="rounded-xl bg-surface-2 p-4 font-display text-lg font-extrabold">Delayed if actual delivery time &gt; promised ETA + 5 minutes</p>
          <p className="mt-3 text-sm leading-relaxed text-muted">The 5-minute grace lives in <code>ml/feature_config.py</code> (<code>DELAY_GRACE_MINUTES</code>, overridable with the <code>ORDERFLOW_DELAY_GRACE_MIN</code> environment variable). Models are retrained automatically when it changes. Predictions are made once the restaurant and rider stages are known, so preparation, assignment and pickup times are inputs.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>How the pipeline works</CardTitle></CardHeader>
        <CardContent>
          <ol className="space-y-4">
            {PIPELINE.map(([t, d], i) => (
              <li key={t} className="flex gap-4">
                <span className="num flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-soft text-sm font-extrabold text-red">{i + 1}</span>
                <div><h3 className="font-display text-base font-extrabold">{t}</h3><p className="text-sm leading-relaxed text-muted">{d}</p></div>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>CSV format</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[28rem] text-sm">
              <tbody>
                {CSV.map(([k, v]) => (
                  <tr key={k} className="border-b border-line/60 last:border-0"><td className="py-2 pr-4 align-top"><code className="text-xs font-semibold">{k}</code></td><td className="py-2 text-muted">{v}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Limitations</CardTitle></CardHeader>
        <CardContent>
          <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
            <li>Predictions are based on synthetic or user-provided data.</li>
            <li>The project has no access to Zomato&apos;s internal systems, or any other platform&apos;s.</li>
            <li>Predictions are demonstrations of operational ML techniques, not production forecasts.</li>
            <li>Bottleneck outputs indicate likely contributing factors rather than proven causes, and feature importance does not prove causation.</li>
            <li>The bundled dataset is generated with logical but simplified relationships; real operations have more noise and more structure than a generator can capture.</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          <p className="font-display text-lg font-extrabold">Designed &amp; Developed by Aarav Singh</p>
          <p className="mt-3 text-xs leading-relaxed text-muted">{DISCLAIMER}</p>
        </CardContent>
      </Card>
    </div>
  );
}
