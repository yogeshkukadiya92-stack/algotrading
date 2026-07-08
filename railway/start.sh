#!/bin/sh
set -eu

export PORT="${PORT:-8080}"
export INTERNAL_API_PORT="${INTERNAL_API_PORT:-8000}"
export INTERNAL_WEB_PORT="${INTERNAL_WEB_PORT:-3000}"
export INTERNAL_API_BASE_URL="${INTERNAL_API_BASE_URL:-http://127.0.0.1:${INTERNAL_API_PORT}}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-/api}"
export PYTHONPATH="/app/apps/api:${PYTHONPATH:-}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "TradePilot India requires DATABASE_URL to point to PostgreSQL. Add a Railway PostgreSQL service and expose its DATABASE_URL to this app." >&2
  exit 1
fi

case "${DATABASE_URL}" in
  mongodb://*|mongodb+srv://*)
    echo "TradePilot India cannot start with a MongoDB DATABASE_URL. This codebase uses PostgreSQL, SQLAlchemy, and Alembic migrations. Attach a Railway PostgreSQL service and set DATABASE_URL from it." >&2
    exit 1
    ;;
esac

mkdir -p /tmp/nginx
envsubst '${PORT} ${INTERNAL_API_PORT} ${INTERNAL_WEB_PORT}' \
  < /app/railway/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

cd /app/apps/api
alembic upgrade head

if [ "${ENABLE_DEMO_SEED:-false}" = "true" ]; then
  cd /app
  python db/seed/demo_seed.py
fi

exec /usr/bin/supervisord -c /app/railway/supervisord.conf
