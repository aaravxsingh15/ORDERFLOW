import * as React from "react";
import { cn } from "@/lib/utils";
import { STATUS_STYLE } from "@/lib/utils";
import type { Status } from "@/lib/types";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-display text-[0.7rem] font-bold uppercase tracking-wider", className)}
      {...props}
    />
  );
}

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const s = STATUS_STYLE[status];
  return (
    <Badge className={cn(s.bg, s.text, s.ring, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} aria-hidden />
      {status}
    </Badge>
  );
}
