# TradePilot India

TradePilot India is a paper-first Indian stock market trading platform being organized into a clean monorepo. The active backend entrypoint now lives in `apps/api`, while older scaffolding in `services/api` remains preserved for continuity. This phase does not introduce any real live broker execution.

## Current Phase

- Create the initial monorepo layout.
- Keep existing working modules intact.
- Add architecture and compliance documentation.
- Reserve clear locations for broker adapters, risk, order, strategy, and paper trading services.
- Defer actual live broker execution and deeper trading workflows to later phases.

## Monorepo Layout

```text
apps/
  web/                  Next.js frontend
  api/                  Active FastAPI backend scaffold
services/
  api/                  Preserved earlier backend scaffold
  market_data_service/
  order_service/
  strategy_service/
  risk_service/
  paper_trading_service/
packages/
  broker_core/
  broker_upstox/
  broker_dhan/
  broker_zerodha/
  shared_types/
db/
infra/
docs/
tests/
scripts/
```

## Existing Code Preserved

- `apps/web` contains the current frontend scaffold.
- `apps/api` contains the active minimal FastAPI backend scaffold.
- `services/api` contains the earlier preserved backend scaffold and tests.
- New top-level folders added in this phase are placeholders for the longer-term monorepo split.
- `services/api` includes disabled live-trading guards and paper-mode scaffolding, but no live broker adapter implementation.

## Safety Rules

- Live trading stays disabled by default.
- No MARKET orders in algo mode.
- Every order must pass the risk engine.
- Every order must carry audit metadata.
- Secrets must never be committed to git.
- Strategy code must emit signals only.

## Docs

- [PRD](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Compliance](docs/COMPLIANCE.md)
- [Broker Adapter Spec](docs/BROKER_ADAPTER_SPEC.md)
- [Vibe Coding Rules](docs/VIBE_CODING_RULES.md)

## Existing Local Run Notes

1. Create a local `.env` from `.env.example`.
2. Use the monorepo scaffold compose file:

```bash
docker compose -f infra/docker-compose.yml up --build
```

3. Open:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

## Authentication

- API auth endpoints are available at `POST /auth/register`, `POST /auth/login`, and `GET /auth/me`.
- The frontend login screen now uses the backend JWT login flow.
- For development, the web app stores the access token in browser session storage and clears it on logout.
- The demo seed creates `demo@tradepilot.in` with password `DemoPass123` for local paper-mode access.

The root `docker-compose.yml` now points the `api` service at `apps/api`. The `infra/` scaffold remains useful for monorepo planning, but the root compose file is the simplest local entrypoint for the current backend.

## Phase Boundary

- No production broker adapter is implemented.
- No live order placement path is enabled.
- Live-mode references in the preserved backend exist only as disabled safety scaffolding.
- Paper-mode and structural scaffolding may exist before the final monorepo split is complete.
