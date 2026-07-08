import { getApiBaseUrl, getAuthToken } from "@/lib/auth";

export type AlertItem = {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  entity_type: string;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
};

export type AuditLog = {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  message: string;
  raw_payload: Record<string, unknown>;
  created_at: string;
};

export type OrderLog = {
  id: string;
  order_id: string;
  event_type: string;
  old_status: string | null;
  new_status: string | null;
  message: string;
  raw_payload: Record<string, unknown>;
  symbol: string;
  created_at: string;
};

export type SignalLog = {
  id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  quantity: number;
  status: string;
  reason: string;
  mode: string;
  created_at: string;
};

export type SystemLog = AuditLog;

export type LogFilters = {
  date?: string;
  severity?: string;
  event_type?: string;
  symbol?: string;
};

function requireToken() {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Your session expired. Sign in again.");
  }
  return token;
}

function queryString(filters: LogFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? "Log request failed.");
  }
  return body as T;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<T>(response);
}

export function fetchAlerts(filters: LogFilters = {}) {
  return apiGet<AlertItem[]>(`/alerts${queryString(filters)}`);
}

export async function markAlertRead(id: string) {
  const response = await fetch(`${getApiBaseUrl()}/alerts/${id}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${requireToken()}` }
  });
  return parseResponse<AlertItem>(response);
}

export async function reportMarketDataDisconnected() {
  const response = await fetch(`${getApiBaseUrl()}/alerts/market-data-disconnected`, {
    method: "POST",
    headers: { Authorization: `Bearer ${requireToken()}` }
  });
  return parseResponse<AlertItem>(response);
}

export function fetchAuditLogs(filters: LogFilters = {}) {
  return apiGet<AuditLog[]>(`/logs/audit${queryString(filters)}`);
}

export function fetchOrderLogs(filters: LogFilters = {}) {
  return apiGet<OrderLog[]>(`/logs/orders${queryString(filters)}`);
}

export function fetchSignalLogs(filters: LogFilters = {}) {
  return apiGet<SignalLog[]>(`/logs/signals${queryString(filters)}`);
}

export function fetchSystemLogs(filters: LogFilters = {}) {
  return apiGet<SystemLog[]>(`/logs/system${queryString(filters)}`);
}

export function formatLogTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
