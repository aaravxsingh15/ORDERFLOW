"use client";

import Link from "next/link";
import { ArrowRight, Clock3, GitBranch, Layers, ScanSearch, TimerReset, Upload, Zap } from "lucide-react";
import { useData } from "@/components/data-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn, pct } from "@/lib/utils";

const FEATURES = [
  { icon: TimerReset, title: "Delay Prediction", text: "A Random Forest classifier turns preparation, rider, route and weather signals into a delay probability and an ON TIME / AT RISK / DELAY LIKELY status.", href: "/analyse" },
  { icon: Clock3, title: "ETA Estimation", text: "A separate regressor estimates total delivery time in minutes, with an expected range and a confidence level, and lays it out stage by stage.", href: "/analyse" },
  { icon: ScanSearch, title: "Bottleneck Detection", text: "Transparent rules plus a model what-if check name the stage that most likely added the excess minutes: kitchen, rider assignment, pickup, traffic or weather.", href: "/batch" },
];

const STEPS = ["Order data", "Validation", "Cleaning", "Feature engineering", "Delay classifier", "ETA regressor", "Bottleneck detector", "Report"];

export default function OverviewPage() {
  const { batch, batchLoading } = useData();
  const s = batch?.summary;
  return (
    <div>
      <section className="border-b border-line bg-gradient-to-b from-red-soft/60 to-transparent">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 sm:px-6 md:py-20 lg:grid-cols-[1.15fr_1fr]">
          <div>
            <p className="eyebrow !text-red">Food Delivery Delay Intelligence</p>
            <h1 className="mt-3 font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl">Know where the delay starts.</h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              Predict late deliveries, estimate delivery time, and identify operational bottlenecks from order data.
            </p>
            <p className="mt-2 font-display text-sm font-bold text-ink">Predict delays before they happen.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" asChild>
                <Link href="/analyse"><Zap className="h-4 w-4" /> Analyse order</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/batch#upload"><Upload className="h-4 w-4" /> Upload dataset</Link>
              </Button>
            </div>
          </div>

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <p className="eyebrow">Demo dataset · live from the models</p>
              <span className="rounded-full bg-green-soft px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-green">no API keys</span>
            </div>
            {s ? (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-3 gap-2 text-center">
                  {([["On time", s.on_time, "text-green"], ["At risk", s.at_risk, "text-orange"], ["Delay likely", s.delay_likely, "text-red"]] as const).map(([k, v, c]) => (
                    <div key={k} className="rounded-2xl bg-surface-2 p-3">
                      <p className={cn("num text-2xl font-extrabold", c)}>{v}</p>
                      <p className="text-[0.68rem] font-semibold uppercase tracking-wider text-muted">{k}</p>
                    </div>
                  ))}
                </div>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div><dt className="eyebrow">Avg delay probability</dt><dd className="num text-xl font-extrabold">{pct(s.avg_delay_probability)}</dd></div>
                  <div><dt className="eyebrow">Avg predicted ETA</dt><dd className="num text-xl font-extrabold">{Math.round(s.avg_eta_minutes)} min</dd></div>
                  <div><dt className="eyebrow">Top bottleneck</dt><dd className="font-display text-base font-extrabold leading-tight">{s.most_common_bottleneck}</dd></div>
                  <div><dt className="eyebrow">Worst window</dt><dd className="num text-xl font-extrabold">{s.worst_delay_window ?? "-"}</dd></div>
                </dl>
                <Button variant="soft" size="sm" className="w-full" asChild>
                  <Link href="/batch">Open batch analysis <ArrowRight className="h-3.5 w-3.5" /></Link>
                </Button>
              </div>
            ) : (
              <p className="mt-4 rounded-2xl bg-surface-2 p-6 text-center text-sm text-muted">
                {batchLoading ? "Scoring the demo orders..." : "Demo mode is off. Upload a CSV to see results here."}
              </p>
            )}
          </Card>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURES.map((f) => (
            <Link key={f.title} href={f.href} className="group">
              <Card className="h-full p-6 transition-all group-hover:-translate-y-0.5 group-hover:border-red/40">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-red-soft text-red"><f.icon className="h-5 w-5" /></span>
                <h2 className="mt-4 font-display text-xl font-extrabold">{f.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.text}</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-4 sm:px-6">
        <div className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-red" /><h2 className="eyebrow !text-ink">One pipeline, end to end</h2></div>
        <ol className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {STEPS.map((step, i) => (
            <li key={step} className="card relative flex flex-col gap-1 p-3">
              <span className="num text-xs font-extrabold text-red">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-[0.82rem] font-bold leading-tight">{step}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 flex items-start gap-2 text-sm text-muted"><Layers className="mt-0.5 h-4 w-4 shrink-0" /> Validation, cleaning, feature engineering and both models run on every order you analyse, in the same code path for a single form entry and a 50,000-row CSV.</p>
      </section>
    </div>
  );
}
