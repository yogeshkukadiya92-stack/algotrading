#!/bin/sh
set -eu

export PORT="${PORT:-8080}"
export INTERNAL_API_PORT="${INTERNAL_API_PORT:-8000}"
export INTERNAL_WEB_PORT="${INTERNAL_WEB_PORT:-3000}"
export INTERNAL_API_BASE_URL="${INTERNAL_API_BASE_URL:-http://127.0.0.1:${INTERNAL_API_PORT}}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-/api}"
export PYTHONPATH="/app/apps/api:${PYTHONPATH:-}"

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
