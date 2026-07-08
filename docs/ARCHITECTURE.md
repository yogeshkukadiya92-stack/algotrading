# TradePilot India Architecture

## Frontend

The frontend lives in `apps/web` and is built with Next.js, TypeScript, Tailwind CSS, and shadcn-style primitives. It is responsible for the trading terminal, paper trading views, option chain experiences, and safety-oriented user flows.

## Backend API

The backend API currently lives in `services/api` and is built with FastAPI. Over time the target monorepo shape includes `apps/api` as the application entrypoint, while domain services are split into focused service boundaries.

In the current phase, the preserved backend contains paper-first order scaffolding and disabled live-mode guards. It should not be interpreted as a live broker execution implementation.

## Broker Adapter Layer

The broker adapter layer will live under `packages/`. `broker_core` defines shared interfaces and contracts, while broker-specific packages such as `broker_upstox`, `broker_dhan`, and `broker_zerodha` implement those contracts.

At this stage, these packages are placeholders only. No real broker connector is wired for production use.

## Risk Engine

The risk engine is a mandatory gate in the order path. It validates order metadata, mode restrictions, quantity and notional limits, and live trading controls before any broker or paper execution step.

## Order Management System

The OMS accepts validated order intents, prevents duplicates, manages state transitions, records audit events, and routes execution requests to either paper trading or broker adapters.

## Paper Trading Engine

The paper trading engine simulates execution behavior without touching live brokers. It is the default execution mode for early product phases and the proving ground for order flow, strategy outputs, and UI behavior.

## Strategy Engine

The strategy engine is separated from broker execution. It emits signals, not orders-to-broker directly. Signals can later be reviewed, approved, or converted into paper orders through controlled flows.

## PostgreSQL

PostgreSQL is the system of record for orders, risk profiles, audit events, broker account metadata, and future portfolio state. Migration assets are expected to consolidate under `db/migrations` over time.

## Redis

Redis supports cache, queues, pub/sub, and transient state for market data fan-out, execution pipelines, and websocket broadcasting.

## WebSocket Flow

The planned websocket flow is:

1. Market data and execution updates enter backend services.
2. Relevant services publish normalized events to Redis pub/sub or stream channels.
3. The API websocket layer subscribes to those channels.
4. The frontend receives live updates for quotes, order status, positions, and strategy signals.

This phase creates the documented shape only. It does not implement the websocket runtime or any real live broker execution path.
