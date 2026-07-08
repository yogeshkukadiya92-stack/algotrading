import {
  Activity,
  DatabaseZap,
  Lock,
  PlugZap,
  Radar,
  ShieldCheck,
  Wallet
} from "lucide-react";

import { Badge } from "@/components/ui/badge";

export const dashboardCards = [
  {
    title: "Today P&L",
    value: "Rs 12,480",
    helper: "Paper ledger across all simulated orders",
    tone: "green" as const,
    trend: "up" as const,
    icon: Wallet
  },
  {
    title: "Open Positions",
    value: "18",
    helper: "11 equity, 7 index derivatives",
    tone: "blue" as const,
    trend: "steady" as const,
    icon: Activity
  },
  {
    title: "Active Strategies",
    value: "3",
    helper: "Signal-only paper strategies",
    tone: "amber" as const,
    trend: "steady" as const,
    icon: Radar
  },
  {
    title: "Broker Connection",
    value: "Paper sandbox",
    helper: "No live adapter attached",
    tone: "blue" as const,
    trend: "steady" as const,
    icon: PlugZap
  },
  {
    title: "Risk Status",
    value: "Protected",
    helper: "All routes gated by pre-trade checks",
    tone: "green" as const,
    trend: "steady" as const,
    icon: ShieldCheck
  },
  {
    title: "Market Data Status",
    value: "Delayed mock feed",
    helper: "Streaming runtime not enabled",
    tone: "amber" as const,
    trend: "steady" as const,
    icon: DatabaseZap
  },
  {
    title: "Kill Switch Status",
    value: "Armed",
    helper: "Session remains in paper mode",
    tone: "green" as const,
    trend: "steady" as const,
    icon: Lock
  }
];

export const watchlistRows = [
  { symbol: "RELIANCE", ltp: "3,012.40", change: "+0.31%", volume: "24.8L", signal: "Watching breakout" },
  { symbol: "TCS", ltp: "4,172.00", change: "+0.12%", volume: "8.3L", signal: "Range hold" },
  { symbol: "HDFCBANK", ltp: "1,742.90", change: "-0.24%", volume: "18.2L", signal: "Support test" },
  { symbol: "INFY", ltp: "1,611.35", change: "+0.48%", volume: "14.1L", signal: "Momentum positive" }
];

export const brokerRows = [
  { broker: "Zerodha", mode: "Paper only", account: "paper_zerodha_001", status: "Ready", sync: "2 min ago" },
  { broker: "Dhan", mode: "Not configured", account: "No account", status: "Pending", sync: "Never" },
  { broker: "Upstox", mode: "Not configured", account: "No account", status: "Pending", sync: "Never" }
];

export const optionRows = [
  { strike: "24,700", callLtp: "162.40", callOi: "1.26 Cr", putLtp: "26.15", putOi: "0.84 Cr" },
  { strike: "24,750", callLtp: "128.15", callOi: "1.42 Cr", putLtp: "34.55", putOi: "0.96 Cr" },
  { strike: "24,800", callLtp: "94.20", callOi: "1.58 Cr", putLtp: "48.40", putOi: "1.12 Cr" },
  { strike: "24,850", callLtp: "68.95", callOi: "1.66 Cr", putLtp: "72.10", putOi: "1.31 Cr" },
  { strike: "24,900", callLtp: "49.10", callOi: "1.35 Cr", putLtp: "103.80", putOi: "1.48 Cr" }
];

export const ordersRows = [
  { time: "09:23", symbol: "RELIANCE", side: "BUY", qty: "10", type: "LIMIT", status: "Filled", mode: "Paper" },
  { time: "10:11", symbol: "NIFTY24JUL24850CE", side: "SELL", qty: "75", type: "LIMIT", status: "Open", mode: "Paper" },
  { time: "11:42", symbol: "TCS", side: "BUY", qty: "5", type: "SL", status: "Triggered", mode: "Paper" }
];

export const positionsRows = [
  { symbol: "RELIANCE", product: "MIS", qty: "10", avg: "2,998.10", ltp: "3,012.40", pnl: "Rs 143.00" },
  { symbol: "NIFTY24JUL24850CE", product: "NRML", qty: "-75", avg: "82.15", ltp: "68.95", pnl: "Rs 990.00" },
  { symbol: "TCS", product: "CNC", qty: "5", avg: "4,150.00", ltp: "4,172.00", pnl: "Rs 110.00" }
];

export const riskRows = [
  { rule: "Algo MARKET order block", status: "Enabled", scope: "All strategy signals", owner: "Risk engine" },
  { rule: "Max order notional", status: "Rs 2,00,000", scope: "Per order", owner: "Risk engine" },
  { rule: "Kill switch", status: "Armed", scope: "Workspace session", owner: "Operator control" },
  { rule: "Live broker orders", status: "Disabled", scope: "Platform wide", owner: "Phase policy" }
];

export const strategiesRows = [
  { name: "Opening Range Breakout", market: "NSE Equities", mode: "Paper", status: "Active", signals: "12 today" },
  { name: "VWAP Reclaim", market: "NIFTY Options", mode: "Paper", status: "Paused", signals: "4 today" },
  { name: "Mean Reversion Basket", market: "Banking", mode: "Paper", status: "Draft", signals: "0 today" }
];

export const logsRows = [
  { time: "12:31:02", event: "market.snapshot.refresh", source: "mock-feed", result: "ok" },
  { time: "12:31:04", event: "risk.check.completed", source: "risk-service", result: "ok" },
  { time: "12:31:07", event: "strategy.signal.generated", source: "strategy-service", result: "ok" },
  { time: "12:31:12", event: "paper.order.fill.simulated", source: "paper-trading", result: "ok" }
];

export const statusBadge = (value: string) => {
  const normalized = value.toLowerCase();
  if (normalized.includes("emergency") || normalized.includes("blocked")) {
    return <Badge tone="red">{value}</Badge>;
  }
  if (normalized.includes("fill") || normalized.includes("active") || normalized.includes("ready") || normalized.includes("ok") || normalized.includes("armed") || normalized.includes("protected")) {
    return <Badge tone="green">{value}</Badge>;
  }
  if (normalized.includes("paused") || normalized.includes("pending") || normalized.includes("delayed")) {
    return <Badge tone="amber">{value}</Badge>;
  }
  if (normalized.includes("disabled") || normalized.includes("draft")) {
    return <Badge tone="red">{value}</Badge>;
  }
  return <Badge tone="blue">{value}</Badge>;
};
