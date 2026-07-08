# TradePilot India Vibe Coding Rules

- Never implement live order placement unless the phase explicitly asks for it.
- Never bypass the risk engine for any order path.
- Never store secrets, broker credentials, or tokens in source code.
- Keep changes small and focused.
- Add tests for risk checks and the order state machine when those modules change.
- Do not rewrite working modules unnecessarily.
- Prefer broker-neutral interfaces over broker-specific coupling.
- Strategy code may emit signals only and must not call broker APIs directly.
- Every order path must preserve auditability.

