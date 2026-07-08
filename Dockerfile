FROM node:22-slim AS web-deps
WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-slim AS web-builder
WORKDIR /app/apps/web
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_ENABLE_LIVE_AUTO_TRADING=false
ENV NEXT_PUBLIC_ENABLE_MANUAL_LIVE_TRADING=false
COPY --from=web-deps /app/apps/web/node_modules ./node_modules
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS api-deps
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV LIVE_TRADING_ENABLED=false
ENV ENABLE_LIVE_BROKER_ORDERS=false
ENV ENABLE_AUTO_TRADING=false
ENV AUTO_TRADING_ENABLED=false
ENV PAPER_TRADING=true
ENV NEXT_TELEMETRY_DISABLED=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 nginx supervisor gettext-base ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY --from=web-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=api-deps /opt/venv /opt/venv

COPY apps/api /app/apps/api
COPY apps/web/package.json /app/apps/web/package.json
COPY --from=web-builder /app/apps/web/.next/standalone /app/apps/web
COPY --from=web-builder /app/apps/web/.next/static /app/apps/web/.next/static
COPY packages /app/packages
COPY services/market_data_service /app/services/market_data_service
COPY services/paper_trading_service /app/services/paper_trading_service
COPY db /app/db
COPY railway /app/railway
COPY .env.example /app/.env.example

RUN chmod +x /app/railway/start.sh

EXPOSE 8080

CMD ["/app/railway/start.sh"]
