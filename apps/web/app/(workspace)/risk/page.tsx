"use client";

import { FormEvent, useState } from "react";
import { BellOff, Save, ShieldAlert, ShieldCheck, ShieldEllipsis } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { StatusCard } from "@/components/app/status-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export default function RiskPage() {
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavedMessage("Risk settings saved locally for this UI phase. Backend persistence will be added with the risk profile API.");
  }

  return (
    <AppShell title="Risk" description="Paper-mode limits, guardrails, and operator protection switches.">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Pre-trade Checks" value="Enabled" helper="Every order must pass risk" tone="green" icon={ShieldCheck} />
        <StatusCard title="Blocked Order Types" value="MARKET" helper="Terminal exposes LIMIT and SL_LIMIT only" tone="red" icon={BellOff} />
        <StatusCard title="Kill Switch" value="Armed" helper="Paper safety posture visible" tone="green" icon={ShieldEllipsis} />
        <StatusCard title="Live Routing" value="Disabled" helper="Live controls locked in UI" tone="red" icon={ShieldAlert} />
      </section>

      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>Risk Settings</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Configure the paper profile limits used by the terminal experience.</p>
        </CardHeader>
        <CardContent className="pt-5">
          <form className="grid gap-5" onSubmit={saveSettings}>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="max-daily-loss">Max daily loss</Label>
                <Input id="max-daily-loss" defaultValue="25000" inputMode="decimal" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max-order-value">Max order value</Label>
                <Input id="max-order-value" defaultValue="200000" inputMode="decimal" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max-lots">Max lots per order</Label>
                <Input id="max-lots" defaultValue="5" inputMode="numeric" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max-trades">Max trades per day</Label>
                <Input id="max-trades" defaultValue="20" inputMode="numeric" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max-open-positions">Max open positions</Label>
                <Input id="max-open-positions" defaultValue="10" inputMode="numeric" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="square-off">Auto square-off time</Label>
                <Input id="square-off" type="time" defaultValue="15:20" />
              </div>
            </section>

            <section className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="allowed-start">Allowed trading start</Label>
                <Input id="allowed-start" type="time" defaultValue="09:15" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="allowed-end">Allowed trading end</Label>
                <Input id="allowed-end" type="time" defaultValue="15:25" />
              </div>
            </section>

            <section className="rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm font-semibold text-red-900">Live trading enablement</div>
                  <p className="mt-1 text-sm text-red-800">
                    Visible for operator awareness, but disabled until explicit live-trading gates are implemented and approved.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-red-900">Disabled</span>
                  <Switch checked={false} disabled aria-label="Live trading disabled" />
                </div>
              </div>
            </section>

            {savedMessage ? (
              <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{savedMessage}</div>
            ) : null}

            <div>
              <Button type="submit">
                <Save className="h-4 w-4" />
                Save paper risk settings
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </AppShell>
  );
}
