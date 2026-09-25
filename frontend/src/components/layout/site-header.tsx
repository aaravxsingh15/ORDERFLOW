"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

export const NAV = [
  { href: "/", label: "Overview" },
  { href: "/analyse", label: "Analyse Order" },
  { href: "/batch", label: "Batch Analysis" },
  { href: "/insights", label: "Model Insights" },
  { href: "/about", label: "About" },
];

export function SiteHeader() {
  const path = usePathname();
  const links = NAV.map((n) => {
    const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
    return (
      <Link
        key={n.href}
        href={n.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors",
          active ? "bg-red-soft text-red" : "text-muted hover:bg-surface-2 hover:text-ink",
        )}
      >
        {n.label}
      </Link>
    );
  });
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" aria-label="ORDERFLOW home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{links}</nav>
        <ThemeToggle />
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-line px-4 py-2 md:hidden" aria-label="Main (mobile)">{links}</nav>
    </header>
  );
}
