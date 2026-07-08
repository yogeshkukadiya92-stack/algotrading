# TradePilot India PRD

## Product Vision

TradePilot India is a full-stack Indian stock market trading platform built around safety, observability, and staged rollout. The product starts with manual and paper trading, then grows toward broker-integrated workflows only after strict operational gates are in place.

## MVP Scope

- Manual trading terminal for Indian equities and derivatives workflows.
- Paper trading mode with realistic order lifecycle simulation.
- Broker adapter architecture with shared contracts and per-broker implementations added later.
- Risk engine enforcement on every order path.
- Order management system with clear order states and duplicate prevention.
- Market data and option chain user experience.
- Structured audit logging for every important action.

## Future Scope

- Live broker execution after explicit approval, risk profile setup, and safety sign-off.
- Strategy engine automation beyond paper mode.
- Multi-broker account management.
- WebSocket streaming for live positions, orders, and market data.
- Portfolio analytics, reporting, and compliance dashboards.

## User Roles

- Trader: Places manual orders, monitors positions, and uses paper trading.
- Strategy user: Runs strategies in paper mode and reviews emitted signals.
- Risk/compliance operator: Reviews limits, audit logs, and execution safety.
- Administrator: Manages broker accounts, infrastructure, and platform controls.

## Core Modules

- Frontend trading terminal
- Backend API
- Broker adapter layer
- Risk engine
- Order management system
- Paper trading engine
- Market data service
- Strategy service
- Audit logging pipeline

## Manual Trading

Manual trading is part of the MVP. The interface should support order entry, quote context, option chain workflows, and clear pre-trade validation feedback.

## Paper Trading

Paper trading is mandatory before any live trading phase. It provides a safe environment to validate order workflows, broker abstractions, and strategy outputs without real market exposure.

## Auto Trading Later

Automated trading is not part of the initial implementation phase. Strategy components may exist early, but they emit signals only. Live strategy execution must wait until safety gates, paper-mode validation, and operational controls are complete.

## Broker Adapters

Broker integrations must follow a common adapter interface so the platform can support multiple Indian brokers without coupling trading logic to a single vendor. Adapter packages are planned for Upstox, Dhan, and Zerodha.

## Risk Engine

Every order must pass risk checks before execution or simulation. The risk engine will own mandatory metadata validation, mode-specific rules, quantity and notional checks, and explicit live trading gates.

## Audit Logging

Audit logging is a first-class requirement. Orders, broker requests and responses, strategy signals, and important system actions must be recorded with traceable correlation metadata.

