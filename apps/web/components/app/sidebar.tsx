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
    <aside className="flex h-full w-full flex-col overflow-hidden rounded-lg border border-slate-200/80 bg-white/95 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_20px_45px_rgba(15,23,42,0.06)] backdrop-blur">
      <div className="border-b border-border/80 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-950 text-white shadow-sm">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-950">TradePilot India</div>
            <div className="text-xs text-muted-foreground">Paper trading workspace</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-all",
                active
                  ? "bg-slate-950 text-white shadow-sm"
                  : "text-muted-foreground hover:bg-slate-100 hover:text-slate-950"
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-cyan-200" : "text-slate-400")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border/80 p-3">
        <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-50 shadow-sm">
          <div className="font-semibold">Paper mode active</div>
          <div className="mt-1 text-xs text-slate-300">Live trading remains locked across the workspace.</div>
        </div>
      </div>
    </aside>
  );
}
