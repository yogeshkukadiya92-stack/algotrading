# TradePilot India Compliance Notes

## Live Trading Disabled By Default

Live trading must remain disabled by default in code, configuration, and product behavior until a later phase explicitly enables it with additional controls.

There must be no real live broker adapter implementation active in this phase. Disabled stubs and safety guards are acceptable; executable live broker connectivity is not.

## API Orders Need Audit Tagging

Every API order request must carry traceable metadata including correlation information, user context, account context, source, and mode so it can be audited end to end.

## No MARKET Orders In Algo Mode

Algorithmic or strategy-originated order flows must not place MARKET orders. This rule is mandatory and belongs in the risk engine, not only the UI.

## Static IP Configuration Placeholder

Some broker workflows may eventually require static IP whitelisting. The monorepo includes configuration placeholders for that requirement, but no production networking setup is implemented in this phase.

## Every Order Must Pass Risk Engine

All order flows, whether manual, paper, or future live flows, must pass through the risk engine before execution or simulation.

## Every Order Must Be Logged

Each order and each broker-facing request/response must be recorded in audit logs. Logging is a compliance and debugging requirement, not an optional observability feature.

