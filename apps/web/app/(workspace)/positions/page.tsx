"use client";

import { useEffect, useMemo, useState } from "react";
import { Blocks, CircleDollarSign, Layers3, WalletCards } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { StatusCard } from "@/components/app/status-card";
import { fetchWatchlist, formatPrice, getMarketStreamUrl, type MarketTick } from "@/lib/market-data";
import { fetchPositions, type TradingPosition } from "@/lib/trading-api";

function signedCurrency(value: number) {
  const formatted = `Rs ${Math.abs(value).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
  return value < 0 ? `-${formatted}` : formatted;
}

export default function PositionsPage() {
  const [ticks, setTicks] = useState<MarketTick[]>([]);
  const [positions, setPositions] = useState<TradingPosition[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPositions() {
      setIsLoading(true);
      setError(null);
      try {
        const [positionData, quoteData] = await Promise.all([fetchPositions(), fetchWatchlist().catch(() => [])]);
        if (isMounted) {
          setPositions(positionData);
          setTicks(quoteData);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Unable to load positions.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadPositions();
    const socket = new WebSocket(getMarketStreamUrl());
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data) as MarketTick[];
      if (isMounted) {
        setTicks(data);
      }
    };
    return () => {
      isMounted = false;
      socket.close();
    };
  }, []);

  const rows = useMemo(
    () =>
      positions.map((position) => {
        const tick = ticks.find((item) => item.symbol === position.symbol);
        const averagePrice = Number(position.average_price);
        const ltp = tick ? Number(tick.ltp) : Number(position.ltp);
        const unrealizedPnl = (ltp - averagePrice) * position.quantity;
        return {
          symbol: position.symbol,
          quantity: position.quantity,
          averagePrice,
          ltp,
          realizedPnl: Number(position.realized_pnl),
          unrealizedPnl,
          productType: position.product_type,
          updatedAt: position.updated_at
        };
      }),
    [positions, ticks]
  );

  const realizedPnl = rows.reduce((sum, row) => sum + row.realizedPnl, 0);
  const unrealizedPnl = rows.reduce((sum, row) => sum + row.unrealizedPnl, 0);
  const exposure = rows.reduce((sum, row) => sum + Math.abs(row.quantity * row.ltp), 0);

  return (
    <AppShell title="Positions" description="Authenticated paper positions from the backend, marked with the current paper market feed.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Gross Exposure" value={`Rs ${exposure.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} helper="Paper notional" tone="blue" icon={Blocks} />
        <StatusCard title="Realized P&L" value={signedCurrency(realizedPnl)} helper="Paper closed P&L" tone={realizedPnl < 0 ? "red" : "green"} icon={CircleDollarSign} />
        <StatusCard title="Unrealized P&L" value={signedCurrency(unrealizedPnl)} helper="Paper mark-to-market" tone={unrealizedPnl < 0 ? "red" : "green"} icon={Layers3} />
        <StatusCard title="Open Symbols" value={String(rows.length)} helper="Paper positions only" tone="amber" icon={WalletCards} />
      </section>
      {isLoading ? <LoadingState title="Loading positions" description="Fetching your authenticated paper positions." /> : null}
      {error ? <ErrorState title="Unable to load positions" description={error} /> : null}
      {!isLoading && !error && rows.length === 0 ? (
        <EmptyState title="No positions yet" description="Place a paper order from the watchlist or option chain to create a position." />
      ) : null}
      <DataTable
        title="Positions"
        description="LTP updates use the paper WebSocket feed; no live broker positions are queried."
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
