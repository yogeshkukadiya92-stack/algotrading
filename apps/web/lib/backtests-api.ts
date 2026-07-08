import { getApiBaseUrl, getAuthToken } from "@/lib/auth";

export type BacktestRun = {
  id: string;
  user_id: string;
  strategy_name: string;
  strategy_version: string;
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  net_pnl: string;
  max_drawdown: string;
  config: Record<string, unknown>;
  result: {
    gross_profit?: string;
    gross_loss?: string;
    average_profit_per_trade?: string;
    average_loss_per_trade?: string;
    trades?: BacktestTrade[];
    warning?: string;
  };
  created_at: string;
};

export type BacktestTrade = {
  symbol: string;
  side: string;
  quantity: number;
  entry_time: string;
  entry_price: string;
  exit_time: string;
  exit_price: string;
  exit_reason: string;
  pnl: string;
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
    throw new Error(typeof detail === "string" ? detail : "Backtest request failed.");
  }
  return body as T;
}

export async function runDemoBacktest(): Promise<BacktestRun> {
  const response = await fetch(`${getApiBaseUrl()}/backtests`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      strategy_name: "DemoStrategy",
      strategy_version: "0.1.0",
      symbol: "NIFTY",
      start_date: "2026-07-01",
      end_date: "2026-07-08",
      initial_capital: "100000",
      quantity: 1,
      stop_loss_points: "40",
      target_points: "80"
    })
  });
  return parseResponse<BacktestRun>(response);
}

export async function fetchBacktests(): Promise<BacktestRun[]> {
  const response = await fetch(`${getApiBaseUrl()}/backtests`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<BacktestRun[]>(response);
}

export function formatBacktestMoney(value: string | number | undefined) {
  return Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}
