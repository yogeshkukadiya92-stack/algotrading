"use client";

import { useState } from "react";
import { BellRing, Lock, Shield } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { StatusCard } from "@/components/app/status-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { resetPaperSession } from "@/lib/trading-api";

export default function SettingsPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sessionResetAt, setSessionResetAt] = useState<string | null>(null);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  async function handleResetPaperSession() {
    setIsResetting(true);
    setResetError(null);
    setResetMessage(null);
    try {
      const result = await resetPaperSession();
      setSessionResetAt(new Date(result.reset_at).toLocaleString("en-IN"));
      setResetMessage(`${result.message} Cancelled ${result.cancelled_orders} open paper order${result.cancelled_orders === 1 ? "" : "s"}.`);
      setDialogOpen(false);
    } catch (err) {
      setResetError(err instanceof Error ? err.message : "Unable to reset paper session.");
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <AppShell title="Settings" description="Workspace preferences, safety policy visibility, and operator actions.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Workspace Mode" value="Paper" helper="Immutable for this phase" tone="green" icon={Lock} />
        <StatusCard title="Notifications" value="Enabled" helper="Alert center active" tone="blue" icon={BellRing} />
        <StatusCard title="Protection Policy" value="Strict" helper="Live routing hard disabled" tone="green" icon={Shield} />
        <StatusCard title="Last Session Reset" value={sessionResetAt ?? "Never"} helper="Audited backend action" tone="amber" icon={Lock} />
      </section>
      <ErrorState
        title="Live broker orders are unavailable"
        description="Even if UI controls exist later, live order routing is intentionally disabled by default. Paper-mode workflows remain active."
      />
      {resetMessage ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900">{resetMessage}</div> : null}
      {resetError ? <ErrorState title="Paper reset failed" description={resetError} /> : null}
      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>Session Controls</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold">Reset paper session</div>
            <div className="mt-1 text-sm text-muted-foreground">Cancels open paper orders through the backend and keeps audit history intact.</div>
          </div>
          <Button onClick={() => setDialogOpen(true)} disabled={isResetting}>
            {isResetting ? "Resetting..." : "Reset paper session"}
          </Button>
        </CardContent>
      </Card>
      <ConfirmDialog
        open={dialogOpen}
        title="Reset paper session?"
        description="Open paper orders will be cancelled and an audit event will be recorded. Historical orders and logs will remain available."
        confirmLabel="Reset session"
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleResetPaperSession}
      />
    </AppShell>
  );
}
