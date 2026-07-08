# TradePilot India Final Review

Review date: 2026-07-08

## Scope Reviewed

- Active backend: `apps/api`
- Frontend: `apps/web`
- Broker packages: `packages/broker_core`, `packages/broker_zerodha`, `packages/broker_upstox`
- Shared paper/risk services: `services/paper_trading_service`, `services/risk_service`
- Deployment defaults: `.env.example`, `docker-compose.prod.yml`, `docs/DEPLOYMENT.md`

## Validation Summary

Code review plus automated verification indicates that the current platform is suitable for paper-first development and operator testing.

Automated verification run:

```bash
PYTHONPATH='apps/api:packages/broker_core:packages/broker_upstox:packages/broker_zerodha:services/paper_trading_service:services/risk_service:services/market_data_service' \
./apps/api/.venv/bin/pytest --import-mode=importlib \
  apps/api/app/tests \
  packages/broker_upstox/tests \
  packages/broker_zerodha/tests \
  services/paper_trading_service/tests \
  services/risk_service/tests
```

Result: `202 passed`

## Verification Matrix

1. Paper trading works end-to-end: Yes
   - Order management routes approved paper orders into `PaperTradingBrokerAdapter`.
   - Tested in `apps/api/app/tests/test_orders.py` and `services/paper_trading_service/tests/test_adapter.py`.

2. Manual paper order flow works: Yes, with one caveat
   - Backend flow is working and tested.
   - Frontend order ticket defaults to paper mode and only offers `LIMIT` / `SL_LIMIT`.
   - There is no browser-level end-to-end test for the frontend flow yet.

3. Risk engine cannot be bypassed: Yes
   - OMS stores the order, records `CREATED`, then evaluates risk before any adapter call.
   - Rejected orders do not reach the paper adapter.

4. Strategy engine cannot call broker directly: Yes
   - Strategy emits `Signal`.
   - Signal is persisted, then routed through OMS and risk evaluation.

5. Live trading is disabled by default: Yes
   - Safe defaults are present in `.env.example` and `docker-compose.prod.yml`.

6. MARKET orders are blocked in algo mode: Yes
   - Risk engine blocks `MARKET` orders.
   - Broker-core validation also blocks `MARKET` in strategy/algo contexts.

7. Every order has `correlation_id`: Yes
   - OMS generates one if missing.

8. Every order creates `OrderEvent`: Yes
   - `CREATED` is always recorded.
   - Additional state changes also create `OrderEvent` rows.

9. Every important action creates `AuditEvent`: Mostly yes
   - Orders, risk decisions, kill switch changes, broker request/response metadata, strategy lifecycle, and jobs are audited.
   - The core operator and trading actions are covered.

10. Broker secrets are never logged: Yes
   - Authorization headers, tokens, and key-like fields are masked before logging or audit persistence.

11. Kill switch blocks new orders: Yes
   - Checked before risk approval.
   - Also stops running strategies.

12. Multi-broker architecture is modular: Yes
   - `broker_core` defines DTOs, enums, and adapter contracts.
   - Broker-specific normalization stays inside per-broker packages.

13. Frontend clearly shows PAPER or LIVE mode: Yes
   - Global banner states paper mode is active and live trading is disabled.
   - Order and strategy surfaces show mode labels.

14. Tests cover risk engine: Yes
   - `apps/api/app/tests/test_risk_engine.py`
   - `services/risk_service/tests/test_engine.py`

15. Tests cover order state machine: Yes
   - Order creation, rejection, approval, broker response, modify, cancel, duplicate protection, idempotency, and live gating are covered.

16. Tests cover paper trading: Yes
   - Fill rules, cancel/modify restrictions, trigger behavior, position averaging, and P&L are covered.

17. Tests cover broker adapter normalization: Yes
   - Zerodha and Upstox read-only normalization is covered with mocked responses.

18. Production env defaults are safe: Yes
   - Live broker order placement and auto trading remain disabled by default.

## What Is Complete

- Paper-first FastAPI backend with:
  - auth
  - order management
  - risk engine
  - paper trading adapter
  - strategy engine in paper mode
  - alerts and audit logs
  - kill switch
  - mock market data
  - mock + broker-backed option chain fallback
  - structured logging
  - request IDs
  - rate limiting
  - idempotency and duplicate order prevention
- Frontend shell with:
  - login
  - dashboard
  - watchlist
  - option chain
  - orders
  - positions
  - risk
  - strategies
  - brokers
  - alerts/logs
  - settings
- Multi-broker read-only architecture for Zerodha and Upstox
- Database models, Alembic migrations, and demo seed
- Production-style deployment scaffolding with Docker Compose, Nginx, Redis persistence, backup scripts, and health checks

## What Is Not Complete

- Real live trading should not be treated as production-ready
- Live order modify/cancel flows remain disabled by design for current brokers
- Dhan adapter is still a placeholder
- Frontend browser-level end-to-end tests are not present
- Distributed operational controls are not implemented for:
  - rate limiting
  - circuit breaker state
  - market reconnect state
- Static IP whitelisting remains a compliance placeholder, not a full operational workflow
- Secrets encryption at rest for persisted broker credentials needs formal key-management review before any real deployment

## Known Risks

1. Hidden manual live UI would still submit the default paper broker account ID if enabled later.
   - File: `apps/web/components/trading/order-ticket.tsx`
   - The order submit payload always uses `getDefaultPaperBrokerAccountId()`, even though the UI has a hidden live mode path.
   - This does not break the current paper-only phase, but it must be corrected before manual live trading is exposed.

2. Rate limiting is process-local.
   - File: `apps/api/app/services/rate_limit.py`
   - In multi-instance deployments, limits will not be shared across replicas.

3. Broker circuit breaker state is process-local.
   - File: `apps/api/app/services/broker_resilience.py`
   - Failure isolation will not be coordinated across multiple API instances.

4. The repo contains both the active backend (`apps/api`) and a preserved earlier scaffold (`services/api`).
   - File: `README.md`
   - This is manageable, but deployment and tooling must consistently target `apps/api`.

5. Frontend paper trading flow is implemented, but not validated with browser automation.
   - Current confidence comes from API tests plus component/code inspection, not end-user scripted UI tests.

## How To Run Locally

1. Create a local environment file:

```bash
cp .env.example .env
```

2. Start the current local stack:

```bash
docker compose up --build
```

3. Open:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Detailed health: `http://localhost:8000/health/details`

4. Run database migrations if needed:

```bash
docker compose exec api alembic upgrade head
```

5. Optional backend test run:

```bash
PYTHONPATH='apps/api:packages/broker_core:packages/broker_upstox:packages/broker_zerodha:services/paper_trading_service:services/risk_service:services/market_data_service' \
./apps/api/.venv/bin/pytest --import-mode=importlib \
  apps/api/app/tests \
  packages/broker_upstox/tests \
  packages/broker_zerodha/tests \
  services/paper_trading_service/tests \
  services/risk_service/tests
```

## How To Deploy Staging

1. Create a staging env file:

```bash
cp .env.example .env.staging
```

2. Keep these staging safety values unchanged:

```bash
LIVE_TRADING_ENABLED=false
ENABLE_LIVE_BROKER_ORDERS=false
ENABLE_AUTO_TRADING=false
AUTO_TRADING_ENABLED=false
PAPER_TRADING=true
```

3. Start the staging stack:

```bash
docker compose --env-file .env.staging -f docker-compose.prod.yml up --build -d
```

4. Run migrations:

```bash
docker compose --env-file .env.staging -f docker-compose.prod.yml exec api alembic upgrade head
```

5. Verify health:

```bash
curl http://localhost/health
curl http://localhost/api/health/details
```

6. If broker credentials are used in staging, keep them read-only only.

## What Must Be Verified Before Real Live Trading

Do not enable real live trading until all of the following are completed and signed off:

1. Fix the manual live order frontend broker account selection path.
2. Add browser-level end-to-end tests for:
   - login
   - manual paper order entry
   - order rejection display
   - kill switch flow
   - strategy start/stop
3. Replace in-memory rate limiting with Redis-backed or gateway-backed enforcement.
4. Replace in-memory broker circuit breaker state with shared, observable state.
5. Complete broker credential encryption and key-management review.
6. Perform a deployment hardening review for:
   - secret injection
   - TLS
   - log retention
   - backup restore drills
   - DB access control
7. Perform broker-specific live order dry-runs in a sandbox or controlled account.
8. Verify static IP requirements operationally with the broker, not just in config.
9. Confirm that every live order path enforces:
   - explicit user enablement
   - risk profile enablement
   - static IP verification
   - manual confirmation text
   - kill switch state
   - risk engine approval
10. Add explicit pre-live runbooks for:
    - incident handling
    - emergency stop
    - broker outage
    - duplicate order investigation
    - reconciliation

## Final Assessment

TradePilot India is in a strong paper-first state.

For paper trading, manual order entry, strategy-to-signal routing, risk enforcement, auditability, and read-only broker integration, the codebase is in good shape.

For real live trading, the platform is not yet ready for production release. The current codebase correctly defaults to that safer posture.
