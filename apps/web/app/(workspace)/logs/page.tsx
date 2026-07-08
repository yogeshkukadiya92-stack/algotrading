"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  fetchAuditLogs,
  fetchOrderLogs,
  fetchSignalLogs,
  fetchSystemLogs,
  formatLogTime,
  type AuditLog,
  type LogFilters,
  type OrderLog,
  type SignalLog,
  type SystemLog
} from "@/lib/alerts-api";

type LogTab = "audit" | "orders" | "signals" | "system";

const tabs: Array<{ key: LogTab; label: string }> = [
  { key: "audit", label: "Audit" },
  { key: "orders", label: "Orders" },
  { key: "signals", label: "Signals" },
  { key: "system", label: "System" }
];

function payloadPreview(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload);
  return text.length > 90 ? `${text.slice(0, 90)}...` : text;
}

export default function LogsPage() {
  const [activeTab, setActiveTab] = useState<LogTab>("audit");
  const [filters, setFilters] = useState<LogFilters>({});
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [orderLogs, setOrderLogs] = useState<OrderLog[]>([]);
  const [signalLogs, setSignalLogs] = useState<SignalLog[]>([]);
  const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeRows = useMemo(() => {
    if (activeTab === "orders") {
      return orderLogs;
    }
    if (activeTab === "signals") {
      return signalLogs;
    }
    if (activeTab === "system") {
      return systemLogs;
    }
    return auditLogs;
  }, [activeTab, auditLogs, orderLogs, signalLogs, systemLogs]);

  async function loadLogs() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const sharedFilters = {
        date: filters.date,
        event_type: filters.event_type,
        symbol: filters.symbol
      };
      const [audit, orders, signals, system] = await Promise.all([
        fetchAuditLogs(sharedFilters),
        fetchOrderLogs(sharedFilters),
        fetchSignalLogs(sharedFilters),
        fetchSystemLogs(sharedFilters)
      ]);
      setAuditLogs(audit);
      setOrderLogs(orders);
      setSignalLogs(signals);
      setSystemLogs(system);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load logs.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadLogs();
  }, []);

  return (
    <AppShell title="Logs" description="Audit, order, signal, and system logs with masked sensitive data.">
      <section className="grid gap-3 rounded-md border border-border bg-white p-4 sm:grid-cols-2 xl:grid-cols-4">
        <Input
          aria-label="Date filter"
          type="date"
          value={filters.date ?? ""}
          onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value }))}
        />
        <Input
          aria-label="Severity filter"
          placeholder="Severity"
          value={filters.severity ?? ""}
          onChange={(event) => setFilters((current) => ({ ...current, severity: event.target.value }))}
        />
        <Input
          aria-label="Event type filter"
          placeholder="Event type"
          value={filters.event_type ?? ""}
          onChange={(event) => setFilters((current) => ({ ...current, event_type: event.target.value }))}
        />
        <div className="flex gap-2">
          <Input
            aria-label="Symbol filter"
            placeholder="Symbol"
            value={filters.symbol ?? ""}
            onChange={(event) => setFilters((current) => ({ ...current, symbol: event.target.value.toUpperCase() }))}
          />
          <Button type="button" onClick={loadLogs}>
            Apply
          </Button>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.key}
            type="button"
            variant={activeTab === tab.key ? "default" : "secondary"}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {errorMessage ? <ErrorState title="Logs unavailable" description={errorMessage} /> : null}
      {isLoading ? <LoadingState title="Loading logs" description="Reading backend observability streams." /> : null}
      {!isLoading && !activeRows.length ? <EmptyState title="No log rows" description="Try clearing filters or generating a paper event." /> : null}

      {activeTab === "audit" && auditLogs.length ? (
        <DataTable
          title="Audit Logs"
          rows={auditLogs}
          columns={[
            { key: "time", header: "Time", render: (row) => formatLogTime(row.created_at) },
            { key: "event", header: "Event", render: (row) => <span className="font-semibold">{row.event_type}</span> },
            { key: "entity", header: "Entity", render: (row) => `${row.entity_type}${row.entity_id ? `:${row.entity_id.slice(0, 8)}` : ""}` },
            { key: "message", header: "Message", render: (row) => row.message },
            { key: "payload", header: "Payload", render: (row) => <span className="text-xs text-muted-foreground">{payloadPreview(row.raw_payload)}</span> }
          ]}
        />
      ) : null}

      {activeTab === "orders" && orderLogs.length ? (
        <DataTable
          title="Order Logs"
          rows={orderLogs}
          columns={[
            { key: "time", header: "Time", render: (row) => formatLogTime(row.created_at) },
            { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
            { key: "event", header: "Event", render: (row) => row.event_type },
            { key: "status", header: "Status", render: (row) => `${row.old_status ?? "-"} -> ${row.new_status ?? "-"}` },
            { key: "message", header: "Message", render: (row) => row.message }
          ]}
        />
      ) : null}

      {activeTab === "signals" && signalLogs.length ? (
        <DataTable
          title="Signal Logs"
          rows={signalLogs}
          columns={[
            { key: "time", header: "Time", render: (row) => formatLogTime(row.created_at) },
            { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
            { key: "side", header: "Side", render: (row) => row.side },
            { key: "qty", header: "Qty", align: "right", render: (row) => row.quantity },
            { key: "status", header: "Status", render: (row) => <Badge tone="blue">{row.status}</Badge> },
            { key: "reason", header: "Reason", render: (row) => row.reason }
          ]}
        />
      ) : null}

      {activeTab === "system" && systemLogs.length ? (
        <DataTable
          title="System Logs"
          rows={systemLogs}
          columns={[
            { key: "time", header: "Time", render: (row) => formatLogTime(row.created_at) },
            { key: "event", header: "Event", render: (row) => <span className="font-semibold">{row.event_type}</span> },
            { key: "entity", header: "Entity", render: (row) => row.entity_type },
            { key: "message", header: "Message", render: (row) => row.message },
            { key: "payload", header: "Payload", render: (row) => <span className="text-xs text-muted-foreground">{payloadPreview(row.raw_payload)}</span> }
          ]}
        />
      ) : null}
    </AppShell>
  );
}
