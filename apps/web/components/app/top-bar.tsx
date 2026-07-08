"use client";

import { Bell, LogOut, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clearAuthToken } from "@/lib/auth";
import { fetchAlerts } from "@/lib/alerts-api";

export function TopBar({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  const router = useRouter();
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  useEffect(() => {
    void fetchAlerts()
      .then((alerts) => setUnreadAlerts(alerts.filter((alert) => !alert.is_read).length))
      .catch(() => setUnreadAlerts(0));
  }, []);

  function handleLogout() {
    clearAuthToken();
    router.replace("/login");
  }

  return (
    <header className="space-y-3">
      <div className="rounded-lg border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm text-amber-950 shadow-sm">
        <span className="font-semibold">Paper mode active. Live trading disabled.</span>
      </div>
      <div className="flex flex-col gap-4 rounded-lg border border-border/80 bg-white/95 px-5 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_14px_34px_rgba(15,23,42,0.04)] backdrop-blur xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input aria-label="Search" className="pl-9" placeholder="Search symbols, orders, logs" />
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="green">
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
              Safety checks on
            </Badge>
            <Button type="button" variant="secondary" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
            <Link
              href="/alerts"
              aria-label="Notifications"
              className="relative flex h-9 w-9 items-center justify-center rounded-md border border-border bg-white text-muted-foreground shadow-sm transition hover:-translate-y-px hover:bg-slate-50 hover:text-foreground"
            >
              <Bell className="h-4 w-4" />
              {unreadAlerts ? (
                <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
                  {unreadAlerts}
                </span>
              ) : null}
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
