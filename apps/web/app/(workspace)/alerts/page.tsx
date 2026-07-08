"use client";

import { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchAlerts, formatLogTime, markAlertRead, type AlertItem } from "@/lib/alerts-api";

function severityTone(severity: string): "green" | "amber" | "red" | "blue" | "neutral" {
  if (severity === "CRITICAL" || severity === "BLOCK") {
    return "red";
  }
  if (severity === "WARN") {
    return "amber";
  }
  if (severity === "INFO") {
    return "blue";
  }
  return "neutral";
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadAlerts() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setAlerts(await fetchAlerts());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load alerts.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadAlerts();
  }, []);

  async function handleMarkRead(id: string) {
    await markAlertRead(id);
    await loadAlerts();
  }

  return (
    <AppShell title="Alerts" description="Notification center for risk, order, strategy, broker, and system events.">
      {errorMessage ? <ErrorState title="Alerts unavailable" description={errorMessage} /> : null}
      {isLoading ? <LoadingState title="Loading alerts" description="Checking notification center." /> : null}
      {!isLoading && !alerts.length ? <EmptyState title="No alerts" description="Risk, order, strategy, and system alerts will appear here." /> : null}
      {alerts.length ? (
        <DataTable
          title="Notification Center"
          rows={alerts}
          columns={[
            { key: "created_at", header: "Time", render: (row) => formatLogTime(row.created_at) },
            { key: "severity", header: "Severity", render: (row) => <Badge tone={severityTone(row.severity)}>{row.severity}</Badge> },
            { key: "title", header: "Title", render: (row) => <span className="font-semibold">{row.title}</span> },
            { key: "message", header: "Message", render: (row) => row.message },
            { key: "type", header: "Type", render: (row) => row.alert_type },
            {
              key: "read",
              header: "Read",
              align: "right",
              render: (row) =>
                row.is_read ? (
                  <Badge tone="green">Read</Badge>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => handleMarkRead(row.id)}>
                    <CheckCircle2 className="h-4 w-4" />
                    Mark read
                  </Button>
                )
            }
          ]}
        />
      ) : null}
    </AppShell>
  );
}
