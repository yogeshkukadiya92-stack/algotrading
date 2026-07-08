"use client";

import {
  BarChart3,
  Bell,
  BookOpenText,
  BriefcaseBusiness,
  CandlestickChart,
  ClipboardList,
  FileText,
  LayoutDashboard,
  ListOrdered,
  Radar,
  Settings,
  ShieldAlert
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/brokers", label: "Brokers", icon: BriefcaseBusiness },
  { href: "/watchlist", label: "Watchlist", icon: BookOpenText },
  { href: "/option-chain", label: "Option Chain", icon: CandlestickChart },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/positions", label: "Positions", icon: ClipboardList },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/strategies", label: "Strategies", icon: Radar },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/logs", label: "Logs", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-full flex-col rounded-lg border border-border bg-[hsl(var(--surface))] shadow-sm">
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold">TradePilot India</div>
            <div className="text-xs text-muted-foreground">Paper trading workspace</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm transition",
                active
                  ? "bg-cyan-50 text-cyan-900 ring-1 ring-cyan-200"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <div className="rounded-md bg-slate-900 px-3 py-3 text-sm text-slate-50">
          <div className="font-semibold">Paper mode active</div>
          <div className="mt-1 text-xs text-slate-300">Live trading remains locked across the workspace.</div>
        </div>
      </div>
    </aside>
  );
}
