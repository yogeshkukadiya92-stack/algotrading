# TradePilot India Deployment

TradePilot India is deployed as a Docker Compose stack with separate `api`, `web`, `postgres`, `redis`, and `nginx` services.

Live trading remains disabled by default in every environment:

- `LIVE_TRADING_ENABLED=false`
- `ENABLE_LIVE_BROKER_ORDERS=false`
- `ENABLE_AUTO_TRADING=false`
- `AUTO_TRADING_ENABLED=false`
- `PAPER_TRADING=true`

Do not change these values unless a later phase explicitly enables live trading and all safety gates are complete.

## Local Deployment

Use the development compose file for local work:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Local services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/health`
- Detailed health: `http://localhost:8000/health/details`

## Staging Deployment

Use `docker-compose.prod.yml` with staging environment values:

```bash
cp .env.example .env.staging
docker compose --env-file .env.staging -f docker-compose.prod.yml up --build -d
```

Staging must use:

- A unique `JWT_SECRET`
- A strong `POSTGRES_PASSWORD`
- Staging-specific `CORS_ORIGINS`
- Read-only broker credentials only, if configured
- `LIVE_TRADING_ENABLED=false`
- `ENABLE_LIVE_BROKER_ORDERS=false`
- `ENABLE_AUTO_TRADING=false`

Run migrations before accepting traffic:

```bash
docker compose --env-file .env.staging -f docker-compose.prod.yml exec api alembic upgrade head
```

## Production Deployment

Production uses the same compose file with production secrets supplied by the host or deployment platform:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml exec api alembic upgrade head
```

Expose only Nginx publicly. PostgreSQL and Redis should stay on the private Docker network.

## Railway Notes

Railway deployment for this repository must use:

- One application service built from the repo `Dockerfile`
- One PostgreSQL service
- One Redis service

Do not attach MongoDB as `DATABASE_URL` for this app. TradePilot India currently uses PostgreSQL with SQLAlchemy models and Alembic migrations, so a MongoDB connection string will fail during startup.

Recommended Railway variables:

- `DATABASE_URL` from the Railway PostgreSQL service
- `REDIS_URL` from the Railway Redis service
- `JWT_SECRET` as a manually created secret
- `APP_ENV=production`
- `LIVE_TRADING_ENABLED=false`
- `ENABLE_LIVE_BROKER_ORDERS=false`
- `ENABLE_AUTO_TRADING=false`
- `AUTO_TRADING_ENABLED=false`
- `PAPER_TRADING=true`

## Static IP Requirement

Live broker integrations may require static IP whitelisting. This phase only includes a placeholder:

```bash
STATIC_IP_WHITELIST=
```

Do not enable live broker order placement until the broker account, static IP, user risk profile, and confirmation gates are implemented and verified.

## Environment Variables

Required production variables:

- `APP_ENV=production`
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `NEXT_PUBLIC_API_BASE_URL`
- `CORS_ORIGINS`

Safety variables:

- `LIVE_TRADING_ENABLED=false`
- `ENABLE_LIVE_BROKER_ORDERS=false`
- `ENABLE_AUTO_TRADING=false`
- `AUTO_TRADING_ENABLED=false`
- `PAPER_TRADING=true`

Optional read-only broker variables:

- `ZERODHA_API_KEY`
- `ZERODHA_ACCESS_TOKEN`
- `ZERODHA_REDIRECT_URI`
- `ZERODHA_API_BASE_URL`

Never commit real secrets to git. Use the deployment platform secret store or a private `.env.production` file outside version control.

## Backup And Restore

Create a PostgreSQL backup:

```bash
scripts/backup_postgres.sh
```

Restore from a backup:

```bash
scripts/restore_postgres.sh backups/tradepilot_tradepilot_YYYYMMDDTHHMMSSZ.sql.gz
```

Backups are gzip-compressed SQL dumps. Store production backups outside the application server and test restores in staging.

## Redis Persistence

Production Redis uses `infra/redis/redis.prod.conf` with:

- Append-only file enabled
- RDB snapshots enabled
- Docker volume persistence at `/data`

Redis should be treated as cache/queue state, not the source of record.

## Logs

Service logs:

```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
```

Application audit and order logs are available from:

- `GET /logs/audit`
- `GET /logs/orders`
- `GET /logs/signals`
- `GET /logs/system`

Broker tokens, API keys, authorization headers, and secrets are masked before log responses are returned.

## Health Checks

Basic health:

```bash
curl http://localhost/health
```

Detailed health:

```bash
curl http://localhost/api/health/details
```

The detailed endpoint reports service status, configured dependency URLs, and safety switch state. It does not expose secrets.

Docker health checks are configured for:

- `postgres`
- `redis`
- `api`
- `web`
- `nginx`
