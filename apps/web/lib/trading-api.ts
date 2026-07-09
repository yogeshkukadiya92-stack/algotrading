import { getApiBaseUrl, getAuthToken } from "@/lib/auth";

export type OrderSide = "BUY" | "SELL";
export type OrderType = "LIMIT" | "SL_LIMIT";
export type ProductType = "CNC" | "MIS" | "NRML";
export type Exchange = "NSE" | "BSE" | "NFO" | "BFO";
export type Segment = "EQ" | "FNO";

export type OrderCreatePayload = {
  broker_account_id: string;
  symbol: string;
  exchange: Exchange;
  segment: Segment;
  transaction_type: OrderSide;
  product_type: ProductType;
  order_type: OrderType;
  quantity: number;
  price: string;
  trigger_price?: string | null;
  source: "manual";
  mode: "paper" | "live";
  lot_size: number;
  confirmation_text?: string | null;
  confirmation_token?: string | null;
};

export type OrderModifyPayload = {
  quantity?: number;
  price?: string;
  trigger_price?: string | null;
};

export type OrderEvent = {
  id: string;
  event_type: string;
  old_status: string | null;
  new_status: string | null;
  message: string;
  raw_payload: Record<string, unknown>;
  created_at: string;
};

export type TradingOrder = {
  id: string;
  correlation_id: string;
  broker_account_id: string;
  broker_name: string;
  symbol: string;
  exchange: string;
  segment: string;
  transaction_type: OrderSide;
  product_type: ProductType;
  order_type: string;
  quantity: number;
  price: string;
  trigger_price: string | null;
  status: string;
  broker_order_id: string | null;
  risk_status: string;
  source: string;
  mode: string;
  created_at: string;
  updated_at: string;
  events?: OrderEvent[];
};

export type OrderActionResponse = {
  order: TradingOrder;
  message: string;
};

export type TradingPosition = {
  id: string;
  broker_account_id: string;
  symbol: string;
  quantity: number;
  average_price: string;
  ltp: string;
  realized_pnl: string;
  unrealized_pnl: string;
  product_type: ProductType;
  updated_at: string;
};

export type PaperSessionResetResponse = {
  reset_at: string;
  cancelled_orders: number;
  message: string;
};

export function getDefaultPaperBrokerAccountId() {
  return process.env.NEXT_PUBLIC_DEFAULT_PAPER_BROKER_ACCOUNT_ID ?? "paper_zerodha_001";
}

function requireToken() {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Your session expired. Sign in again to place paper orders.");
  }
  return token;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed.");
  }
  return body as T;
}

export async function createOrder(payload: OrderCreatePayload): Promise<OrderActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/orders`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  return parseResponse<OrderActionResponse>(response);
}

export async function fetchOrders(): Promise<TradingOrder[]> {
  const response = await fetch(`${getApiBaseUrl()}/orders`, {
    headers: {
      Authorization: `Bearer ${requireToken()}`
    },
    cache: "no-store"
  });

  return parseResponse<TradingOrder[]>(response);
}

export async function fetchPositions(): Promise<TradingPosition[]> {
  const response = await fetch(`${getApiBaseUrl()}/positions`, {
    headers: {
      Authorization: `Bearer ${requireToken()}`
    },
    cache: "no-store"
  });

  return parseResponse<TradingPosition[]>(response);
}

export async function cancelOrder(orderId: string): Promise<OrderActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/orders/${orderId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`
    }
  });

  return parseResponse<OrderActionResponse>(response);
}

export async function modifyOrder(orderId: string, payload: OrderModifyPayload): Promise<OrderActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/orders/${orderId}/modify`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  return parseResponse<OrderActionResponse>(response);
}

export async function resetPaperSession(): Promise<PaperSessionResetResponse> {
  const response = await fetch(`${getApiBaseUrl()}/controls/paper-session/reset`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`
    }
  });

  return parseResponse<PaperSessionResetResponse>(response);
}

export function orderRiskMessage(order: TradingOrder) {
  if (order.status !== "RISK_REJECTED") {
    return null;
  }

  const rejection = order.events?.find((event) => event.event_type === "RISK_REJECTED");
  return rejection?.message ?? "Risk engine rejected this order.";
}
