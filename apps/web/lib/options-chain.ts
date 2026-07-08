import { getApiBaseUrl } from "@/lib/auth";

export type OptionUnderlying = "NIFTY" | "BANKNIFTY";

export type OptionStrike = {
  strike_price: string;
  ce_ltp: string;
  ce_bid: string;
  ce_ask: string;
  ce_oi: number;
  ce_volume: number;
  ce_iv: string;
  ce_delta: string;
  ce_gamma: string;
  ce_theta: string;
  ce_vega: string;
  pe_ltp: string;
  pe_bid: string;
  pe_ask: string;
  pe_oi: number;
  pe_volume: number;
  pe_iv: string;
  pe_delta: string;
  pe_gamma: string;
  pe_theta: string;
  pe_vega: string;
};

export type OptionChain = {
  underlying: OptionUnderlying;
  spot_price: string;
  expiry: string;
  source: "MOCK" | "BROKER";
  fallback_reason: string | null;
  strikes: OptionStrike[];
};

export const optionExpiries = ["2026-07-30", "2026-08-06", "2026-08-27"];

export async function fetchOptionChain(underlying: OptionUnderlying, expiry: string): Promise<OptionChain> {
  const params = new URLSearchParams({ underlying, expiry });
  const response = await fetch(`${getApiBaseUrl()}/options/chain?${params.toString()}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Unable to load option chain.");
  }

  return response.json();
}

export function formatOptionNumber(value: string | number, maximumFractionDigits = 2) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits,
    minimumFractionDigits: maximumFractionDigits
  });
}

export function formatCompact(value: number) {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function optionSymbol(underlying: OptionUnderlying, expiry: string, strike: string, side: "CE" | "PE") {
  const expiryDate = new Date(`${expiry}T00:00:00Z`);
  const month = expiryDate.toLocaleString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase();
  const year = String(expiryDate.getUTCFullYear()).slice(-2);
  const day = String(expiryDate.getUTCDate()).padStart(2, "0");
  return `${underlying}${year}${month}${day}${Number(strike).toFixed(0)}${side}`;
}
