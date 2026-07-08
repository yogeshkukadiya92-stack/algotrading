export type ActiveBrokerSelection = {
  id: string;
  broker_name: string;
  display_name: string;
};

const STORAGE_KEY = "tradepilot.activeBrokerAccount";

export function getActiveBrokerSelection(): ActiveBrokerSelection | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as ActiveBrokerSelection;
  } catch {
    return null;
  }
}

export function setActiveBrokerSelection(selection: ActiveBrokerSelection) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
}
