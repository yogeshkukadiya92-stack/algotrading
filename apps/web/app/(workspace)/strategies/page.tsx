"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, FlaskConical, OctagonAlert, Play, Radar, ShieldCheck, Square } from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { DataTable } from "@/components/app/data-table";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LoadingState } from "@/components/app/loading-state";
import { StatusCard } from "@/components/app/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchBacktests, formatBacktestMoney, runDemoBacktest, type BacktestRun } from "@/lib/backtests-api";
import {
  createLiveAutoDemoStrategy,
  createDemoStrategy,
  fetchStrategies,
  fetchStrategySignals,
  formatStrategyMoney,
  startStrategy,
  stopStrategy,
  type Strategy,
  type StrategySignal
} from "@/lib/strategies-api";

const LIVE_AUTO_CONFIRMATION_TEXT = "ENABLE LIVE AUTO TRADING";

function statusTone(status: string): "green" | "amber" | "red" | "blue" | "neutral" {
  if (status === "RUNNING" || status === "ORDER_CREATED") {
    return "green";
  }
  if (status === "ORDER_REJECTED") {
    return "red";
  }
  if (status === "STOPPED") {
    return "amber";
  }
  return "blue";
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [signals, setSignals] = useState<StrategySignal[]>([]);
  const [backtests, setBacktests] = useState<BacktestRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showAdvancedLiveAuto, setShowAdvancedLiveAuto] = useState(false);
  const [liveAutoConfirmation, setLiveAutoConfirmation] = useState("");

  const liveAutoUiEnabled = process.env.NEXT_PUBLIC_ENABLE_LIVE_AUTO_TRADING === "true";

  const selectedStrategy = useMemo(
    () => strategies.find((strategy) => strategy.id === selectedStrategyId) ?? strategies[0] ?? null,
    [strategies, selectedStrategyId]
  );

  useEffect(() => {
    void loadStrategies();
  }, []);

  useEffect(() => {
    if (selectedStrategy) {
      void loadSignals(selectedStrategy.id);
    } else {
      setSignals([]);
    }
  }, [selectedStrategy?.id]);

  async function loadStrategies() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchStrategies();
      const backtestData = await fetchBacktests();
      setStrategies(data);
      setBacktests(backtestData);
      setSelectedStrategyId((current) => current ?? data[0]?.id ?? null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load strategies.");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadSignals(strategyId: string) {
    try {
      setSignals(await fetchStrategySignals(strategyId));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to load strategy signals.");
    }
  }

  async function handleCreateDemo() {
    setIsWorking(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      const created = await createDemoStrategy();
      setMessage("DemoStrategy created in PAPER mode.");
      await loadStrategies();
      setSelectedStrategyId(created.id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create demo strategy.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleCreateLiveAutoDemo() {
    if (liveAutoConfirmation !== LIVE_AUTO_CONFIRMATION_TEXT) {
      setErrorMessage(`Type ${LIVE_AUTO_CONFIRMATION_TEXT} to request live auto strategy enablement.`);
      return;
    }
    setIsWorking(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      const created = await createLiveAutoDemoStrategy();
      setMessage("Live auto strategy request created. Backend gates still decide whether it can start or place orders.");
      setLiveAutoConfirmation("");
      await loadStrategies();
      setSelectedStrategyId(created.id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create live auto strategy request.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleStart(strategyId: string) {
    setIsWorking(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      const response = await startStrategy(strategyId);
      setMessage(response.signal ? "Paper signal emitted and routed through OMS/Risk Engine." : "Strategy started with no signal.");
      await loadStrategies();
      await loadSignals(strategyId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to start strategy.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleStop(strategyId: string) {
    setIsWorking(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      await stopStrategy(strategyId);
      setMessage("Strategy stopped.");
      await loadStrategies();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to stop strategy.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleRunBacktest() {
    setIsWorking(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      await runDemoBacktest();
      setBacktests(await fetchBacktests());
      setMessage("DemoStrategy backtest completed with simulated paper fills.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to run backtest.");
    } finally {
      setIsWorking(false);
    }
  }

  const latestBacktest = backtests[0] ?? null;

  return (
    <AppShell title="Strategies" description="Signal-only strategy controls routed through OMS and Risk Engine.">
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
        PAPER strategy mode is the default. Live auto trading is disabled unless environment, user, broker, strategy, kill switch, and risk gates all approve it.
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="Strategies Loaded" value={String(strategies.length)} helper="Paper deployment set" tone="blue" icon={Bot} />
        <StatusCard title="Signals" value={String(signals.length)} helper="For selected strategy" tone="green" icon={Radar} />
        <StatusCard title="Default Mode" value="PAPER" helper="Live auto hidden by default" tone="amber" icon={ShieldCheck} />
        <StatusCard title="Validation" value="OMS + Risk" helper="No direct broker calls" tone="green" icon={FlaskConical} />
      </section>

      <div className="flex flex-wrap gap-3">
        <Button onClick={handleCreateDemo} disabled={isWorking}>
          <Bot className="h-4 w-4" />
          Create demo strategy
        </Button>
        {selectedStrategy ? (
          <>
            <Button onClick={() => handleStart(selectedStrategy.id)} disabled={isWorking}>
              <Play className="h-4 w-4" />
              Start selected
            </Button>
            <Button variant="secondary" onClick={() => handleStop(selectedStrategy.id)} disabled={isWorking}>
              <Square className="h-4 w-4" />
              Stop selected
            </Button>
          </>
        ) : null}
        <Button variant="secondary" onClick={handleRunBacktest} disabled={isWorking}>
          <FlaskConical className="h-4 w-4" />
          Run demo backtest
        </Button>
        {liveAutoUiEnabled ? (
          <Button variant="secondary" onClick={() => setShowAdvancedLiveAuto((current) => !current)}>
            <OctagonAlert className="h-4 w-4" />
            Advanced live auto
          </Button>
        ) : null}
      </div>

      {liveAutoUiEnabled && showAdvancedLiveAuto ? (
        <Card>
          <CardHeader className="border-b border-border">
            <CardTitle>Live Auto Trading Gate</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 pt-5">
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-950">
              Live auto trading requires explicit user enablement, live broker routing, strategy risk limits, static IP verification, kill switch clearance,
              and final order approval from the Risk Engine. Strategy code still emits signals only and MARKET orders remain blocked.
            </div>
            <section className="grid gap-4 md:grid-cols-3">
              <StatusCard title="Live Auto Status" value="DISABLED" helper="Advanced gate only" tone="red" icon={OctagonAlert} />
              <StatusCard title="Daily P&L" value="₹0.00" helper="Live auto placeholder" tone="neutral" icon={ShieldCheck} />
              <StatusCard title="Strategy P&L" value="₹0.00" helper="Per-strategy gate input" tone="neutral" icon={Radar} />
            </section>
            <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
              <label className="grid gap-2 text-sm font-medium text-foreground">
                Confirmation text
                <Input
                  value={liveAutoConfirmation}
                  onChange={(event) => setLiveAutoConfirmation(event.target.value)}
                  placeholder={LIVE_AUTO_CONFIRMATION_TEXT}
                />
              </label>
              <Button
                variant="danger"
                onClick={handleCreateLiveAutoDemo}
                disabled={isWorking || liveAutoConfirmation !== LIVE_AUTO_CONFIRMATION_TEXT}
              >
                <OctagonAlert className="h-4 w-4" />
                Request live auto strategy
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {message ? <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">{message}</div> : null}
      {errorMessage ? <ErrorState title="Strategy action unavailable" description={errorMessage} /> : null}
      {isLoading ? <LoadingState title="Loading strategies" description="Checking paper strategy workspace." /> : null}

      {!isLoading && !strategies.length ? (
        <EmptyState
          title="No paper strategies yet"
          description="Create DemoStrategy to emit a paper signal and route it through the order service."
        />
      ) : null}

      {strategies.length ? (
        <DataTable
          title="Strategy Console"
          rows={strategies}
          columns={[
            {
              key: "name",
              header: "Name",
              render: (row) => (
                <button className="font-semibold text-primary" onClick={() => setSelectedStrategyId(row.id)}>
                  {row.name}
                </button>
              )
            },
            { key: "version", header: "Version", render: (row) => row.version },
            { key: "mode", header: "Mode", align: "center", render: (row) => <Badge tone="amber">{row.mode.toUpperCase()}</Badge> },
            { key: "status", header: "Status", align: "center", render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge> },
            { key: "symbol", header: "Symbol", render: (row) => String(row.config.symbol ?? "-") }
          ]}
        />
      ) : null}

      <DataTable
        title="Generated Signals"
        description="Signals are persisted first, then routed to the paper order service."
        rows={signals}
        columns={[
          { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold">{row.symbol}</span> },
          { key: "side", header: "Side", render: (row) => row.side },
          { key: "quantity", header: "Qty", align: "right", render: (row) => row.quantity },
          { key: "price", header: "Limit", align: "right", render: (row) => `₹${formatStrategyMoney(row.price)}` },
          { key: "mode", header: "Mode", align: "center", render: (row) => <Badge tone="amber">{row.mode.toUpperCase()}</Badge> },
          { key: "status", header: "Status", align: "center", render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge> },
          { key: "order", header: "Linked Paper Order", render: (row) => row.order ? `${row.order.status} · ${row.order.correlation_id}` : "-" },
          { key: "reason", header: "Reason", render: (row) => row.reason }
        ]}
      />

      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
        Backtest results do not guarantee future returns.
      </div>

      <section className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <Card>
          <CardHeader className="border-b border-border">
            <CardTitle>Backtest Results</CardTitle>
          </CardHeader>
          <CardContent className="pt-5">
            {latestBacktest ? (
              <dl className="grid gap-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Total trades</dt>
                  <dd className="font-semibold">{latestBacktest.total_trades}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Win rate</dt>
                  <dd className="font-semibold">{formatBacktestMoney(latestBacktest.win_rate)}%</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Gross profit</dt>
                  <dd className="font-semibold">₹{formatBacktestMoney(latestBacktest.result.gross_profit)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Gross loss</dt>
                  <dd className="font-semibold">₹{formatBacktestMoney(latestBacktest.result.gross_loss)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Net P&L</dt>
                  <dd className="font-semibold">₹{formatBacktestMoney(latestBacktest.net_pnl)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Max drawdown</dt>
                  <dd className="font-semibold">₹{formatBacktestMoney(latestBacktest.max_drawdown)}</dd>
                </div>
              </dl>
            ) : (
              <EmptyState title="No backtests yet" description="Run DemoStrategy on sample CSV candles to see simulated results." />
            )}
          </CardContent>
        </Card>

        <DataTable
          title="Backtest Trades"
          description="Simulated paper fills only. No broker APIs or real orders are used."
          rows={latestBacktest?.result.trades ?? []}
          columns={[
            { key: "entry_time", header: "Entry", render: (row) => row.entry_time },
            { key: "entry_price", header: "Entry Price", align: "right", render: (row) => `₹${formatBacktestMoney(row.entry_price)}` },
            { key: "exit_time", header: "Exit", render: (row) => row.exit_time },
            { key: "exit_price", header: "Exit Price", align: "right", render: (row) => `₹${formatBacktestMoney(row.exit_price)}` },
            { key: "exit_reason", header: "Reason", render: (row) => row.exit_reason },
            { key: "pnl", header: "P&L", align: "right", render: (row) => `₹${formatBacktestMoney(row.pnl)}` }
          ]}
        />
      </section>
    </AppShell>
  );
}
