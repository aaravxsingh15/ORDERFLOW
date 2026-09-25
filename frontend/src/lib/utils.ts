import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Status } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export const DISCLAIMER =
  "ORDERFLOW is an independent portfolio project inspired by food-delivery operations. It is not affiliated with, endorsed by, or sponsored by Zomato.";

export function fmt(v: number | null | undefined, digits = 0, suffix = ""): string {
  return v === null || v === undefined || Number.isNaN(v) ? "-" : `${v.toFixed(digits)}${suffix}`;
}

export function pct(v: number | null | undefined, digits = 0): string {
  return v === null || v === undefined || Number.isNaN(v) ? "-" : `${(v * 100).toFixed(digits)}%`;
}

export const STATUS_STYLE: Record<Status, { text: string; bg: string; ring: string; dot: string; color: string }> = {
  "ON TIME": { text: "text-green", bg: "bg-green-soft", ring: "border-green/40", dot: "bg-green", color: "var(--green)" },
  "AT RISK": { text: "text-orange", bg: "bg-orange-soft", ring: "border-orange/40", dot: "bg-orange", color: "var(--orange)" },
  "DELAY LIKELY": { text: "text-red", bg: "bg-red-soft", ring: "border-red/40", dot: "bg-red", color: "var(--red)" },
};

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Parse "HH:MM" -> decimal hour, or null if malformed. */
export function parseTime(s: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(s.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const mi = Number(m[2]);
  return h <= 23 && mi <= 59 ? h + mi / 60 : null;
}

export function toCsv<T extends object>(rows: T[], columns: { key: keyof T & string; header: string }[]): string {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.map((c) => c.header).join(","), ...rows.map((r) => columns.map((c) => esc(r[c.key])).join(","))].join("\n");
}

export function download(filename: string, content: string | Blob, type = "text/csv;charset=utf-8") {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
