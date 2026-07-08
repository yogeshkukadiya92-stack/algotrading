import { getApiBaseUrl, getAuthToken } from "@/lib/auth";

export type BrokerAccount = {
  id: string;
  broker_name: string;
  display_name: string;
  is_active: boolean;
  is_paper: boolean;
  static_ip_verified: boolean;
  token_expires_at: string | null;
  login_url: string | null;
  status: string;
};

export type BrokerFunds = {
  broker_name: string;
  available_cash: string;
  collateral: string;
  utilized_margin: string;
  net: string;
};

export type BrokerPosition = {
  broker_name: string;
  exchange: string;
  segment: string;
  symbol: string;
  quantity: number;
  average_price: string;
  last_price: string;
  product_type: string;
  realized_pnl: string;
  unrealized_pnl: string;
};

export type BrokerOrder = {
  broker_order_id: string;
  broker_status: string;
  normalized_status: string;
  filled_quantity: number;
  pending_quantity: number;
  average_price: string | null;
  message: string | null;
  updated_at: string | null;
};

export type BrokerConnectResponse = {
  account: BrokerAccount;
  login_url: string;
  message: string;
};

export type SupportedBroker = "zerodha" | "upstox";

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
    throw new Error(typeof body?.detail === "string" ? body.detail : "Broker request failed.");
  }
  return body as T;
}

export async function fetchBrokerAccounts(): Promise<BrokerAccount[]> {
  const response = await fetch(`${getApiBaseUrl()}/brokers`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<BrokerAccount[]>(response);
}

export async function connectBroker(brokerName: SupportedBroker): Promise<BrokerConnectResponse> {
  const displayName = brokerName === "upstox" ? "Upstox Read Only" : "Zerodha Read Only";
  const response = await fetch(`${getApiBaseUrl()}/brokers/connect`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ broker_name: brokerName, display_name: displayName })
  });
  return parseResponse<BrokerConnectResponse>(response);
}

export async function fetchBrokerFunds(accountId: string): Promise<BrokerFunds> {
  const response = await fetch(`${getApiBaseUrl()}/brokers/${accountId}/funds`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<BrokerFunds>(response);
}

export async function fetchBrokerPositions(accountId: string): Promise<BrokerPosition[]> {
  const response = await fetch(`${getApiBaseUrl()}/brokers/${accountId}/positions`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<BrokerPosition[]>(response);
}

export async function fetchBrokerOrders(accountId: string): Promise<BrokerOrder[]> {
  const response = await fetch(`${getApiBaseUrl()}/brokers/${accountId}/orders`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<BrokerOrder[]>(response);
}

export function formatMoney(value: string | number) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  });
}
