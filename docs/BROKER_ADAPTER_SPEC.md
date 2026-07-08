# Broker Adapter Specification

## Purpose

All broker integrations must conform to a common interface so the platform can swap or add brokers without changing order management, risk logic, or strategy flows.

## Required Interface

Every broker adapter should expose the following operations:

- `login_url()`: Returns the broker login or authorization URL.
- `exchange_token(code: str)`: Exchanges an authorization code or request token for broker session credentials.
- `get_profile()`: Fetches the authenticated user profile from the broker.
- `get_funds()`: Fetches available funds, margins, and buying power details.
- `get_positions()`: Fetches open positions and holdings as supported by the broker.
- `get_orders()`: Fetches historical and active orders.
- `place_order(order_request)`: Places a single order after risk clearance.
- `modify_order(order_id, modify_request)`: Modifies an existing open order when supported.
- `cancel_order(order_id)`: Cancels an existing open order when supported.
- `subscribe_market_data(symbols, callback)`: Subscribes to broker market data streams or a normalized bridge.

## Design Rules

- Adapters must remain thin and broker-specific.
- Adapters must not contain platform risk logic.
- Adapters must not retry `place_order` blindly.
- Adapters must return normalized responses that the OMS can map consistently.
- Adapters must record request and response payloads through the audit layer.
- Secrets must be loaded from encrypted storage or runtime configuration, never hardcoded.

## Notes For This Phase

This document defines the interface only. No production broker adapter implementation is introduced in this phase.

