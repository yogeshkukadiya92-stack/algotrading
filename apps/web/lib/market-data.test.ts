import assert from "node:assert/strict";
import test from "node:test";

import { resolveMarketStreamUrl } from "./market-data-url.ts";

test("market stream URL resolves from relative api base in browser", () => {
  assert.equal(
    resolveMarketStreamUrl("/api", "https://algotrading-production-2852.up.railway.app"),
    "wss://algotrading-production-2852.up.railway.app/market/stream",
  );
});

test("market stream URL preserves explicit api host", () => {
  assert.equal(resolveMarketStreamUrl("http://localhost:8000"), "ws://localhost:8000/market/stream");
});
