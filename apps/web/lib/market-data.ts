import { getApiBaseUrl } from "./auth";
import { resolveMarketStreamUrl } from "./market-data-url";

export type MarketTick = {
  symbol: string;
  exchange: string;
  segment: string;
  ltp: string;
  bid: string;
  ask: string;
  volume: number;
  oi: number;
  timestamp: string;
};

export type MarketCandle = {
  symbol: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
  start_time: string;
};

export async function fetchWatchlist(): Promise<MarketTick[]> {
  const response = await fetch(`${getApiBaseUrl()}/market/watchlist`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Unable to load watchlist.");
  }

  return response.json();
}

export function getMarketStreamUrl() {
  return resolveMarketStreamUrl(getApiBaseUrl(), typeof window === "undefined" ? undefined : window.location.origin);
}

export function formatPrice(value: string | number) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  });
}

export function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}
