import { getApiBaseUrl, getAuthToken } from "@/lib/auth";

export type ControlStatus = {
  kill_switch_enabled: boolean;
  reason: string | null;
  enabled_at: string | null;
  disabled_at: string | null;
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
    throw new Error(typeof detail === "string" ? detail : "Control request failed.");
  }
  return body as T;
}

export async function fetchControlStatus(): Promise<ControlStatus> {
  const response = await fetch(`${getApiBaseUrl()}/controls/status`, {
    headers: { Authorization: `Bearer ${requireToken()}` },
    cache: "no-store"
  });
  return parseResponse<ControlStatus>(response);
}

export async function enableKillSwitch(reason = "Emergency stop from TradePilot India UI"): Promise<ControlStatus> {
  const response = await fetch(`${getApiBaseUrl()}/controls/kill-switch/enable`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${requireToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ reason })
  });
  return parseResponse<ControlStatus>(response);
}

export async function disableKillSwitch(): Promise<ControlStatus> {
  const response = await fetch(`${getApiBaseUrl()}/controls/kill-switch/disable`, {
    method: "POST",
    headers: { Authorization: `Bearer ${requireToken()}` }
  });
  return parseResponse<ControlStatus>(response);
}

export function formatControlTime(value: string | null) {
  if (!value) {
    return "Not triggered";
  }
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
