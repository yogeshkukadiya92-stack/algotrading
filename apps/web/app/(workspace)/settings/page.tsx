"use client";

import { useState } from "react";
import { BellRing, Lock, Shield } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { StatusCard } from "@/components/app/status-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sessionResetAt, setSessionResetAt] = useState<string | null>(null);

  return (
    <AppShell title="Settings" description="Workspace preferences, safety policy visibility, and mock operator actions.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Workspace Mode" value="Paper" helper="Immutable for this phase" tone="green" icon={Lock} />
        <StatusCard title="Notifications" value="Enabled" helper="Mock desk alerts" tone="blue" icon={BellRing} />
        <StatusCard title="Protection Policy" value="Strict" helper="Live routing hard disabled" tone="green" icon={Shield} />
        <StatusCard title="Last Session Reset" value={sessionResetAt ?? "Never"} helper="Mock operator action" tone="amber" icon={Lock} />
      </section>
      <ErrorState
        title="Live broker orders are unavailable"
        description="Even if UI controls exist later, live order routing is intentionally disabled in this phase. Only mock data and paper-mode workflows are supported."
      />
      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>Session Controls</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold">Reset paper session</div>
            <div className="mt-1 text-sm text-muted-foreground">Clears the current mock workspace state without touching any real account.</div>
          </div>
          <Button onClick={() => setDialogOpen(true)}>Open confirm dialog</Button>
        </CardContent>
      </Card>
      <ConfirmDialog
        open={dialogOpen}
        title="Reset paper session?"
        description="This mock action clears local paper-session state only. Live trading remains disabled."
        confirmLabel="Reset session"
        onCancel={() => setDialogOpen(false)}
        onConfirm={() => {
          setSessionResetAt("Just now");
          setDialogOpen(false);
        }}
      />
    </AppShell>
  );
}

