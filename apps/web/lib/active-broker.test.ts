import assert from "node:assert/strict";
import test from "node:test";

import { getActiveBrokerSelection, setActiveBrokerSelection } from "./active-broker.ts";

class MockStorage {
  private values = new Map<string, string>();

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }

  clear() {
    this.values.clear();
  }
}

const storage = new MockStorage();

test.beforeEach(() => {
  Object.defineProperty(globalThis, "window", {
    value: { localStorage: storage },
    configurable: true,
  });
  storage.clear();
});

test.afterEach(() => {
  delete (globalThis as { window?: object }).window;
});

test("active broker selection persists and loads from local storage", () => {
  setActiveBrokerSelection({
    id: "broker_123",
    broker_name: "upstox",
    display_name: "Upstox Read Only",
  });

  assert.deepEqual(getActiveBrokerSelection(), {
    id: "broker_123",
    broker_name: "upstox",
    display_name: "Upstox Read Only",
  });
});

test("invalid stored broker selection falls back to null", () => {
  storage.setItem("tradepilot.activeBrokerAccount", "{invalid-json");

  assert.equal(getActiveBrokerSelection(), null);
});
