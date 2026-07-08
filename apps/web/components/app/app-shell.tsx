"use client";

import { useEffect, useState } from "react";
import { OctagonAlert, ShieldCheck } from "lucide-react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Sidebar } from "@/components/app/sidebar";
import { TopBar } from "@/components/app/top-bar";
import { Button } from "@/components/ui/button";
import { enableKillSwitch, fetchControlStatus, formatControlTime, type ControlStatus } from "@/lib/controls-api";

export function AppShell({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const [controlStatus, setControlStatus] = useState<ControlStatus | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isWorking, setIsWorking] = useState(false);

  async function refreshStatus() {
    try {
      setControlStatus(await fetchControlStatus());
    } catch {
      setControlStatus(null);
    }
  }

  useEffect(() => {
    void refreshStatus();
  }, []);

  async function handleEmergencyStop() {
    setIsWorking(true);
    try {
      const status = await enableKillSwitch();
      setControlStatus(status);
    } finally {
      setIsWorking(false);
      setConfirmOpen(false);
    }
  }

  return (
    <main className="min-h-screen px-3 py-3 sm:px-5 sm:py-5 lg:px-8">
      <div className="mx-auto grid max-w-[1680px] gap-4 xl:grid-cols-[272px_minmax(0,1fr)]">
        <div className="xl:sticky xl:top-5 xl:h-[calc(100vh-2.5rem)]">
          <Sidebar />
        </div>
        <div className="min-w-0 space-y-5">
          <TopBar title={title} description={description} />
          <div
            className={
              controlStatus?.kill_switch_enabled
                ? "flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50/95 px-4 py-3 text-sm text-red-950 shadow-sm"
                : "flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50/95 px-4 py-3 text-sm text-emerald-950 shadow-sm"
            }
          >
            <div className="flex min-w-0 items-center gap-3">
              {controlStatus?.kill_switch_enabled ? <OctagonAlert className="h-5 w-5 shrink-0" /> : <ShieldCheck className="h-5 w-5 shrink-0" />}
              <div className="min-w-0">
                <div className="font-semibold">
                  {controlStatus?.kill_switch_enabled ? "Kill switch active. New orders and strategies are blocked." : "Kill switch ready. Paper mode active."}
                </div>
                <div className="text-xs opacity-80">
                  {controlStatus?.kill_switch_enabled
                    ? `${controlStatus.reason ?? "Emergency stop enabled"} · ${formatControlTime(controlStatus.enabled_at)}`
                    : "Live trading remains disabled."}
                </div>
              </div>
            </div>
            <Button variant="danger" onClick={() => setConfirmOpen(true)} disabled={isWorking || controlStatus?.kill_switch_enabled}>
              <OctagonAlert className="h-4 w-4" />
              Emergency Stop
            </Button>
          </div>
          {children}
        </div>
      </div>
      <ConfirmDialog
        open={confirmOpen}
        title="Enable emergency stop?"
        description="This will block all new orders immediately and stop running strategies. Existing open paper orders can still be cancelled."
        confirmLabel="Enable Emergency Stop"
        onConfirm={handleEmergencyStop}
        onCancel={() => setConfirmOpen(false)}
      />
    </main>
  );
}
