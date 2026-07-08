"use client";

import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Activity, DatabaseZap, ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { StatusCard } from "@/components/app/status-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reportMarketDataDisconnected } from "@/lib/alerts-api";
import { fetchControlStatus, formatControlTime, type ControlStatus } from "@/lib/controls-api";
import { dashboardCards, logsRows, statusBadge, watchlistRows } from "@/lib/mock-data";
import { fetchWatchlist, formatPrice, getMarketStreamUrl, type MarketTick } from "@/lib/market-data";

export default function DashboardPage() {
  const [ticks, setTicks] = useState<MarketTick[]>([]);
  const [streamStatus, setStreamStatus] = useState<"connecting" | "live" | "offline">("connecting");
  const [controlStatus, setControlStatus] = useState<ControlStatus | null>(null);

  useEffect(() => {
    let isMounted = true;
    let disconnectAlertSent = false;

    function handleMarketDisconnect() {
      setStreamStatus("offline");
      if (!disconnectAlertSent) {
        disconnectAlertSent = true;
        void reportMarketDataDisconnected().catch(() => undefined);
      }
    }

    async function loadWatchlist() {
      try {
        const data = await fetchWatchlist();
        if (isMounted) {
          setTicks(data);
        }
      } catch {
        setStreamStatus("offline");
      }
    }

    void loadWatchlist();
    void fetchControlStatus()
      .then(setControlStatus)
      .catch(() => setControlStatus(null));

    const socket = new WebSocket(getMarketStreamUrl());
    socket.onopen = () => setStreamStatus("live");
    socket.onclose = handleMarketDisconnect;
    socket.onerror = handleMarketDisconnect;
    socket.onmessage = (event) => {
      setTicks(JSON.parse(event.data) as MarketTick[]);
      setStreamStatus("live");
    };

    return () => {
      isMounted = false;
      socket.close();
    };
  }, []);

  const dashboardCardsWithMarketStatus = useMemo(
    () =>
      dashboardCards.map((card) =>
        card.title === "Market Data Status"
          ? {
              ...card,
              value: streamStatus === "live" ? "Live mock feed" : "Mock feed offline",
              helper: streamStatus === "live" ? "WebSocket ticks updating" : "Last REST snapshot retained",
              tone: streamStatus === "live" ? ("green" as const) : ("amber" as const)
            }
          : card.title === "Kill Switch Status"
            ? {
                ...card,
                value: controlStatus?.kill_switch_enabled ? "ACTIVE" : "Ready",
                helper: controlStatus?.kill_switch_enabled
                  ? controlStatus.reason ?? "Emergency stop enabled"
                  : "New orders allowed in PAPER mode",
                tone: controlStatus?.kill_switch_enabled ? ("red" as const) : ("green" as const)
              }
          : card
      ),
    [controlStatus, streamStatus]
  );

  const marketRows = ticks.length
    ? ticks.map((tick) => ({
        symbol: tick.symbol,
        ltp: formatPrice(tick.ltp),
        change: `${formatPrice(tick.bid)} / ${formatPrice(tick.ask)}`,
        volume: tick.volume.toLocaleString("en-IN"),
        signal: tick.segment
      }))
    : watchlistRows;

  const sessionHealth: Array<{ label: string; value: string; icon: LucideIcon }> = [
    { label: "Risk engine", value: "Protected", icon: ShieldCheck },
    { label: "Mock market feed", value: streamStatus === "live" ? "Live mock feed" : "Connecting", icon: DatabaseZap },
    {
      label: "Kill switch",
      value: controlStatus?.kill_switch_enabled ? `Active · ${formatControlTime(controlStatus.enabled_at)}` : "Ready",
      icon: ShieldCheck
    },
    { label: "Audit stream", value: "Paper-only events", icon: Activity }
  ];

  return (
    <AppShell title="Dashboard" description="High-level paper trading status across terminal, risk, and strategy systems.">
      <section className="rounded-lg border border-slate-800 bg-slate-950 px-5 py-5 text-white shadow-[0_18px_45px_rgba(15,23,42,0.18)]">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase text-cyan-200">Paper command center</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight">Trade safely before switching anything live.</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              Market data, order routing, strategy signals, and kill switch controls stay visible in one guarded workspace.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              ["Mode", "PAPER"],
              ["Broker", "Sandbox"],
              ["Risk", "On"]
            ].map(([label, value]) => (
              <div key={label} className="min-w-[88px] rounded-md border border-slate-800 bg-slate-900/80 px-3 py-3">
                <div className="text-[11px] uppercase text-slate-400">{label}</div>
                <div className="mt-1 text-sm font-bold">{value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dashboardCardsWithMarketStatus.map((card) => (
          <StatusCard key={card.title} {...card} />
        ))}
      </section>
      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <DataTable
          title="Watchlist Snapshot"
          description="Mock market pulse for the current session."
          rows={marketRows}
          columns={[
            { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
            { key: "ltp", header: "LTP", align: "right", render: (row) => row.ltp },
            { key: "change", header: "Bid / Ask", align: "right", render: (row) => row.change },
            { key: "volume", header: "Volume", align: "right", render: (row) => row.volume },
            { key: "signal", header: "Segment", render: (row) => row.signal }
          ]}
        />
        <div className="space-y-4">
          <Card>
            <CardHeader className="border-b border-border">
              <CardTitle>Session Health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              {sessionHealth.map(({ label, value, icon: ItemIcon }) => {
                return (
                  <div key={label} className="flex items-center justify-between rounded-md border border-border/80 bg-white p-3 shadow-sm">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-100 text-slate-700 ring-1 ring-slate-200">
                        <ItemIcon className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold">{label}</div>
                        <div className="text-xs text-muted-foreground">Workspace telemetry</div>
                      </div>
                    </div>
                    {statusBadge(value)}
                  </div>
                );
              })}
            </CardContent>
          </Card>
          <DataTable
            title="Recent Audit Events"
            rows={logsRows.slice(0, 3)}
            columns={[
              { key: "time", header: "Time", render: (row) => row.time },
              { key: "event", header: "Event", render: (row) => row.event },
              { key: "result", header: "Result", align: "right", render: (row) => statusBadge(row.result) }
            ]}
          />
        </div>
      </section>
    </AppShell>
  );
}
