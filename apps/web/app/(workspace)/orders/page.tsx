"use client";

import { useEffect, useMemo, useState } from "react";
import { Clock3, ListOrdered, Pencil, ShieldCheck, Trash2, Wallet } from "lucide-react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { DataTable } from "@/components/app/data-table";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { StatusCard } from "@/components/app/status-card";
import { AppShell } from "@/components/app/app-shell";
import { Button } from "@/components/ui/button";
import { cancelOrder, fetchOrders, modifyOrder, orderRiskMessage, type TradingOrder } from "@/lib/trading-api";
import { statusBadge } from "@/lib/mock-data";

function formatPrice(value: string | null) {
  if (!value) {
    return "-";
  }
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function canActOnOrder(order: TradingOrder) {
  return !["CANCELLED", "FILLED", "RISK_REJECTED", "LIVE_DISABLED"].includes(order.status);
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<TradingOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<TradingOrder | null>(null);

  async function loadOrders() {
    try {
      setErrorMessage(null);
      setOrders(await fetchOrders());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load orders.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadOrders();
  }, []);

  const openOrders = useMemo(
    () => orders.filter((order) => ["CREATED", "RISK_APPROVED", "OPEN", "TRIGGER_PENDING", "MODIFIED"].includes(order.status)),
    [orders]
  );
  const riskRejectedCount = orders.filter((order) => order.status === "RISK_REJECTED").length;
  const notional = orders.reduce((sum, order) => sum + Number(order.price || 0) * order.quantity, 0);
  const brokerCount = new Set(orders.map((order) => order.broker_name)).size;

  async function confirmCancel() {
    if (!cancelTarget) {
      return;
    }

    try {
      const response = await cancelOrder(cancelTarget.id);
      setActionMessage(`Cancel request stored. Current status: ${response.order.status}.`);
      setCancelTarget(null);
      await loadOrders();
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Unable to cancel order.");
    }
  }

  async function requestModify(order: TradingOrder) {
    if (!canActOnOrder(order)) {
      setActionMessage(`Order ${order.correlation_id} cannot be modified in ${order.status} state.`);
      return;
    }

    const nextQuantity = window.prompt("Quantity", String(order.quantity));
    if (nextQuantity === null) {
      return;
    }
    const nextPrice = window.prompt("Price", order.price);
    if (nextPrice === null) {
      return;
    }
    const payload = {
      quantity: Number(nextQuantity),
      price: nextPrice.trim(),
      trigger_price: order.order_type === "SL_LIMIT" ? order.trigger_price : null
    };

    try {
      const response = await modifyOrder(order.id, payload);
      setActionMessage(`Modify request stored. Current status: ${response.order.status}.`);
      await loadOrders();
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Unable to modify order.");
    }
  }

  const rows = orders.map((order) => ({
    ...order,
    priceDisplay: formatPrice(order.price),
    riskMessage: orderRiskMessage(order)
  }));

  return (
    <AppShell title="Orders" description="Manual paper order book with risk status, correlation IDs, and OMS actions.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Orders Today" value={String(orders.length)} helper="Loaded from OMS" tone="blue" icon={ListOrdered} />
        <StatusCard title="Open Orders" value={String(openOrders.length)} helper="Cancelable paper states" tone="amber" icon={Clock3} />
        <StatusCard title="Risk Rejections" value={String(riskRejectedCount)} helper="Clear rejection messages shown" tone={riskRejectedCount ? "red" : "green"} icon={ShieldCheck} />
        <StatusCard title="Paper Notional" value={`Rs ${notional.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} helper={`${brokerCount || 1} broker labels in order book`} tone="blue" icon={Wallet} />
      </section>

      {actionMessage ? (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">{actionMessage}</div>
      ) : null}
      {errorMessage ? <ErrorState title="Orders unavailable" description={errorMessage} /> : null}
      {isLoading ? <LoadingState title="Loading orders" description="Fetching paper order book." /> : null}

      {!isLoading && !errorMessage ? (
        <DataTable
          title="Order Book"
          description="Cancel and modify actions remain scoped to paper orders."
          rows={rows}
          columns={[
            { key: "status", header: "Status", render: (row) => statusBadge(row.status) },
            { key: "broker_name", header: "Broker", render: (row) => row.broker_name.toUpperCase() },
            { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
            { key: "side", header: "Side", align: "center", render: (row) => statusBadge(row.transaction_type) },
            { key: "quantity", header: "Quantity", align: "right", render: (row) => row.quantity.toLocaleString("en-IN") },
            { key: "price", header: "Price", align: "right", render: (row) => row.priceDisplay },
            { key: "mode", header: "Mode", align: "center", render: (row) => statusBadge(row.mode.toUpperCase()) },
            { key: "source", header: "Source", align: "center", render: (row) => row.source.toUpperCase() },
            {
              key: "correlation",
              header: "Correlation ID",
              render: (row) => <span className="font-mono text-xs">{row.correlation_id}</span>
            },
            {
              key: "risk",
              header: "Risk Message",
              render: (row) => <span className="text-xs text-red-700">{row.riskMessage ?? "-"}</span>
            },
            {
              key: "cancel",
              header: "Cancel",
              align: "center",
              render: (row) => (
                <Button size="sm" variant="secondary" disabled={!canActOnOrder(row)} onClick={() => setCancelTarget(row)}>
                  <Trash2 className="h-4 w-4" />
                  Cancel
                </Button>
              )
            },
            {
              key: "modify",
              header: "Modify",
              align: "center",
              render: (row) => (
                <Button size="sm" variant="secondary" disabled={!canActOnOrder(row)} onClick={() => requestModify(row)}>
                  <Pencil className="h-4 w-4" />
                  Modify
                </Button>
              )
            }
          ]}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(cancelTarget)}
        title="Cancel paper order"
        description={cancelTarget ? `Send a cancel request for ${cancelTarget.symbol} (${cancelTarget.correlation_id})?` : ""}
        confirmLabel="Cancel order"
        onConfirm={confirmCancel}
        onCancel={() => setCancelTarget(null)}
      />
    </AppShell>
  );
}
