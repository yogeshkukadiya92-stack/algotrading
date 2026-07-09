# Live Wiring Inventory

TradePilot India is wired as a guarded paper-first trading platform. Live broker order placement remains disabled by default and must stay blocked until the live trading checklist in `docs/FINAL_REVIEW.md` is completed.

| Area | Interaction | Current live behavior | Dependency | Status |
| --- | --- | --- | --- | --- |
| Auth | Login form | Calls `POST /auth/login`, stores development token in session storage, redirects to dashboard | FastAPI auth, JWT, `users` table | Live |
| Auth | Logout button | Clears token and returns to `/login` | Frontend auth helper | Live |
| Navigation | Sidebar links | Routes to all workspace pages | Next.js app routes | Live |
| Top bar | Search input | Enter opens known modules or filters watchlist by symbol query | Next.js router, watchlist route | Live |
| Top bar | Notification bell | Opens `/alerts` and shows unread count from API | `GET /alerts` | Live |
| App shell | Emergency Stop | Confirms and calls kill-switch API | `POST /controls/kill-switch/enable` | Live |
| Dashboard | Status cards | Uses authenticated orders, positions, controls, market stream, audit logs | `/orders`, `/positions`, `/controls/status`, `/logs/audit`, market WS | Live |
| Dashboard | Watchlist snapshot | Uses market service REST/WS feed | `/market/watchlist`, `/market/stream` | Live paper feed |
| Watchlist | Quick Buy / Quick Sell | Fills order ticket with selected symbol and paper price | Order ticket state | Live |
| Watchlist | Symbol filtering | Reads `?symbol=` from URL and filters the table | Top bar search | Live |
| Order ticket | Submit | Calls `POST /orders`; defaults to PAPER; MARKET is not offered | Order service, risk engine, paper adapter | Live paper trading |
| Orders | Order book | Loads authenticated orders from API | `GET /orders` | Live |
| Orders | Cancel | Confirms and calls paper cancel endpoint | `POST /orders/{id}/cancel` | Live |
| Orders | Modify | Calls paper modify endpoint; current UI uses prompt fields | `POST /orders/{id}/modify` | Live, UI can be improved |
| Positions | Positions table | Loads authenticated positions from database and marks with paper feed | `GET /positions`, market WS | Live |
| Risk | Risk settings | Shows current guarded UI and live toggles disabled | Risk service/gates | Partially live; editable persistence needs product approval |
| Option chain | Underlying/expiry selectors | Calls chain API and shows MOCK/BROKER source | `GET /options/chain` | Live read-only |
| Option chain | CE/PE Ticket | Fills order ticket with paper NFO contract | Order ticket state | Live |
| Option chain | Add to basket | Saves/removes basket legs in browser storage and can fill ticket | Local paper basket storage | Live local basket |
| Brokers | Add/connect broker | Read-only account flow, normalized DTOs, audit logging | Broker read-only service and env credentials | Live read-only |
| Brokers | Funds/positions/orders | Reads normalized broker data when credentials exist; otherwise shows safe errors | Broker adapter packages | Blocked by missing real broker secrets |
| Strategies | Create/start/stop demo strategy | Uses backend strategy service; emits signals only; paper orders routed through order service | Strategy engine, risk engine, order service | Live paper strategy |
| Backtests | Run backtest | Uses sample candles and simulated paper fills | Backtest service | Live offline simulation |
| Alerts | Mark read | Calls `POST /alerts/{id}/read` | Alerts API | Live |
| Logs | Filter tabs | Reads audit/order/signal/system logs with masked payloads | Logs API | Live |
| Settings | Reset paper session | Cancels open paper orders, records audit event, preserves history | `POST /controls/paper-session/reset` | Live |
| Live trading | Manual LIVE orders | Guarded by env, user, risk profile, static IP, confirmation, kill switch, risk engine | Live trading guard and broker adapter | Disabled by default |
| Auto trading | LIVE strategy orders | Guarded by env/user/risk/strategy gates and disabled by default | Auto trading guard | Disabled by default |

## Blocked Or Intentionally Mocked

- Real market data is not connected because broker market-data credentials and product rate-limit decisions are not configured. The market service remains a paper/mock feed.
- Real broker option chain can be used only when supported credentials are configured; otherwise the API falls back to mock data and labels the source.
- Broker order placement must not be enabled from this wiring pass. Paper trading is the verified execution path.
- Risk settings persistence should be implemented only after confirming which fields users can edit and whether approvals are required for live-trading toggles.
