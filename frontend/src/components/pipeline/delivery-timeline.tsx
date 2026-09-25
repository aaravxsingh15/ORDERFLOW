"use client";

import { AlertTriangle, Bike, CheckCheck, ChefHat, Navigation, PackageCheck, ShoppingBag, Store } from "lucide-react";
import { motion, MotionConfig } from "framer-motion";
import type { Stage } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  placed: ShoppingBag,
  accepted: Store,
  preparing: ChefHat,
  assignment: Bike,
  pickup: PackageCheck,
  transit: Navigation,
  delivered: CheckCheck,
};

const TONE = {
  primary: { ring: "border-red bg-red-soft text-red", bar: "var(--red)", text: "text-red", label: "Primary" },
  secondary: { ring: "border-orange bg-orange-soft text-orange", bar: "var(--orange)", text: "text-orange", label: "Secondary" },
  none: { ring: "border-line bg-surface text-muted", bar: "var(--line)", text: "text-ink", label: "" },
} as const;

/** Horizontal (desktop) / vertical (mobile) delivery timeline with the likely delay stage highlighted. */
export function DeliveryTimeline({ stages, total }: { stages: Stage[]; total: number }) {
  const timed = stages.filter((s) => s.minutes > 0);
  const sum = timed.reduce((a, s) => a + s.minutes, 0) || 1;
  return (
    <MotionConfig reducedMotion="user">
      <div>
        <ol className="relative grid gap-3 md:grid-cols-7 md:gap-2">
          <div className="absolute left-[7%] right-[7%] top-[22px] hidden h-0.5 bg-line md:block" aria-hidden />
          {stages.map((s, i) => {
            const tone = TONE[s.flag ?? "none"];
            const Icon = ICONS[s.key] ?? ShoppingBag;
            const endpoint = s.key === "placed" || s.key === "delivered";
            return (
              <motion.li
                key={s.key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.3 }}
                className="relative flex items-center gap-3 md:flex-col md:gap-2 md:text-center"
              >
                <span className={cn("relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2", tone.ring)}>
                  <Icon className="h-[18px] w-[18px]" />
                  {s.flag && (
                    <span className={cn("absolute -right-1 -top-1 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-surface", tone.text)} title={`${tone.label} contributing stage`}>
                      <AlertTriangle className="h-3.5 w-3.5" aria-label={`${tone.label} contributing stage`} />
                    </span>
                  )}
                </span>
                <span className="min-w-0 flex-1 md:flex-none">
                  <span className="block text-[0.8rem] font-bold leading-tight">{s.label}</span>
                  <span className={cn("num block text-lg font-extrabold leading-tight", tone.text)}>
                    {endpoint ? (s.key === "placed" ? "0 min" : `${Math.round(s.cumulative)} min`) : `${Math.round(s.minutes)} min`}
                  </span>
                  {s.flag && s.excess_minutes >= 1 && <span className={cn("block text-[0.7rem] font-semibold", tone.text)}>+{Math.round(s.excess_minutes)} min over normal</span>}
                </span>
              </motion.li>
            );
          })}
        </ol>

        <div className="mt-6" aria-label="Share of total delivery time by stage">
          <div className="flex h-3.5 w-full overflow-hidden rounded-full bg-surface-2">
            {timed.map((s, i) => (
              <motion.div
                key={s.key}
                initial={{ width: 0 }}
                animate={{ width: `${(s.minutes / sum) * 100}%` }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.5, ease: "easeOut" }}
                style={{ background: TONE[s.flag ?? "none"].bar, opacity: s.flag ? 1 : 0.55 }}
                className="h-full border-r-2 border-surface last:border-r-0"
                title={`${s.label}: ${Math.round(s.minutes)} min`}
              />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
            <span className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red" /> Primary</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-orange" /> Secondary</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-line" /> Normal</span>
            </span>
            <span className="font-semibold text-ink">Estimated total: <span className="num text-base font-extrabold">{Math.round(total)} min</span></span>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}
