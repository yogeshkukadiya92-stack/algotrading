"use client";

import { useEffect, useMemo, useState } from "react";
import { Blocks, CircleDollarSign, Layers3, WalletCards } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { StatusCard } from "@/components/app/status-card";
import { fetchWatchlist, formatPrice, getMarketStreamUrl, type MarketTick } from "@/lib/market-data";

const basePositions = [
  { symbol: "NIFTY", quantity: 1, averagePrice: 24780, realizedPnl: 0, productType: "MIS" },
  { symbol: "NIFTY26JUL24800CE", quantity: 75, averagePrice: 140.5, realizedPnl: 0, productType: "NRML" },
  { symbol: "NIFTY26JUL24800PE", quantity: -75, averagePrice: 130.1, realizedPnl: 525, productType: "NRML" }
];

function signedCurrency(value: number) {
  const formatted = `Rs ${Math.abs(value).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
  return value < 0 ? `-${formatted}` : formatted;
}

export default function PositionsPage() {
  const [ticks, setTicks] = useState<MarketTick[]>([]);

  useEffect(() => {
    let isMounted = true;

    async function loadQuotes() {
      const data = await fetchWatchlist().catch(() => []);
      if (isMounted) {
        setTicks(data);
      }
    }

    void loadQuotes();
    const socket = new WebSocket(getMarketStreamUrl());
    socket.onmessage = (event) => setTicks(JSON.parse(event.data) as MarketTick[]);
    return () => {
      isMounted = false;
      socket.close();
    };
  }, []);

  const rows = useMemo(
    () =>
      basePositions.map((position) => {
        const tick = ticks.find((item) => item.symbol === position.symbol);
        const ltp = tick ? Number(tick.ltp) : position.averagePrice;
        const unrealizedPnl = (ltp - position.averagePrice) * position.quantity;
        return {
          ...position,
          ltp,
          unrealizedPnl
        };
      }),
    [ticks]
  );

  const realizedPnl = rows.reduce((sum, row) => sum + row.realizedPnl, 0);
  const unrealizedPnl = rows.reduce((sum, row) => sum + row.unrealizedPnl, 0);
  const exposure = rows.reduce((sum, row) => sum + Math.abs(row.quantity * row.ltp), 0);

  return (
    <AppShell title="Positions" description="Paper positions marked against the mock market data feed.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Gross Exposure" value={`Rs ${exposure.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} helper="Paper notional" tone="blue" icon={Blocks} />
        <StatusCard title="Realized P&L" value={signedCurrency(realizedPnl)} helper="Paper closed P&L" tone={realizedPnl < 0 ? "red" : "green"} icon={CircleDollarSign} />
        <StatusCard title="Unrealized P&L" value={signedCurrency(unrealizedPnl)} helper="Live mock mark" tone={unrealizedPnl < 0 ? "red" : "green"} icon={Layers3} />
        <StatusCard title="Open Symbols" value={String(rows.length)} helper="Paper positions only" tone="amber" icon={WalletCards} />
      </section>
      <DataTable
        title="Positions"
        description="LTP updates use the mock WebSocket feed; no broker positions are queried."
        rows={rows}
        columns={[
          { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
          { key: "quantity", header: "Quantity", align: "right", render: (row) => row.quantity.toLocaleString("en-IN") },
          { key: "average", header: "Average price", align: "right", render: (row) => formatPrice(row.averagePrice) },
          { key: "ltp", header: "LTP", align: "right", render: (row) => formatPrice(row.ltp) },
          {
            key: "realized",
            header: "Realized P&L",
            align: "right",
            render: (row) => <span className={row.realizedPnl < 0 ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>{signedCurrency(row.realizedPnl)}</span>
          },
          {
            key: "unrealized",
            header: "Unrealized P&L",
            align: "right",
            render: (row) => <span className={row.unrealizedPnl < 0 ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>{signedCurrency(row.unrealizedPnl)}</span>
          }
        ]}
      />
    </AppShell>
  );
}
