import { getApiBaseUrl, getAuthToken } from "@/lib/auth";
import type { TradingOrder } from "@/lib/trading-api";

export type Strategy = {
  id: string;
  user_id: string;
  name: string;
  version: string;
  status: string;
  mode: "paper" | "live";
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type StrategySignal = {
  id: string;
  strategy_id: string;
  order_id: string | null;
  user_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  order_type: string;
  price: string;
  stop_loss: string | null;
  target: string | null;
  reason: string;
  mode: "paper" | "live";
  status: string;
  created_at: string;
  order: TradingOrder | null;
};

export type StrategyActionResponse = {
  strategy: Strategy;
  signal: StrategySignal | null;
  message: string;
};

function requireToken() {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Your session expired. Sign in again.");
  }
  return token;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : "Strategy request failed.");
  }
  return body as T;
}

export async function fetchStrategies(): Promise<Strategy[]> {
  const response = await fetch(`${getApiBaseUrl()}/strategies`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<Strategy[]>(response);
}

export async function createDemoStrategy(): Promise<Strategy> {
  const response = await fetch(`${getApiBaseUrl()}/strategies`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      name: "DemoStrategy",
      version: "0.1.0",
      mode: "paper",
      broker_account_id: process.env.NEXT_PUBLIC_DEFAULT_PAPER_BROKER_ACCOUNT_ID ?? "paper_zerodha_001",
      symbol: "NIFTY",
      quantity: 1,
      price: "24800",
      stop_loss: "24750",
      target: "24900"
    })
  });
  return parseResponse<Strategy>(response);
}

export async function createLiveAutoDemoStrategy(): Promise<Strategy> {
  const response = await fetch(`${getApiBaseUrl()}/strategies`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      name: "DemoStrategy",
      version: "0.1.0-live",
      mode: "live",
      broker_account_id: process.env.NEXT_PUBLIC_DEFAULT_LIVE_BROKER_ACCOUNT_ID ?? "live_zerodha_001",
      symbol: "NIFTY",
      quantity: 1,
      price: "24800",
      stop_loss: "24750",
      target: "24900",
      live_auto_confirmation_text: "ENABLE LIVE AUTO TRADING",
      max_daily_loss: "1000",
      max_trades_per_day: 5,
      max_open_positions: 1,
      allowed_symbols: ["NIFTY"],
      start_time: "09:15:00",
      stop_time: "15:20:00"
    })
  });
  return parseResponse<Strategy>(response);
}

export async function startStrategy(strategyId: string): Promise<StrategyActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/strategies/${strategyId}/start`, {
    method: "POST",
    headers: { Authorization: `Bearer ${requireToken()}` }
  });
  return parseResponse<StrategyActionResponse>(response);
}

export async function stopStrategy(strategyId: string): Promise<StrategyActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/strategies/${strategyId}/stop`, {
    method: "POST",
    headers: { Authorization: `Bearer ${requireToken()}` }
  });
  return parseResponse<StrategyActionResponse>(response);
}

export async function fetchStrategySignals(strategyId: string): Promise<StrategySignal[]> {
  const response = await fetch(`${getApiBaseUrl()}/strategies/${strategyId}/signals`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<StrategySignal[]>(response);
}

export function formatStrategyMoney(value: string | number | null) {
  if (value === null) {
    return "-";
  }
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}
