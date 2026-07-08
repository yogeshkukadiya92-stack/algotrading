#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/restore_postgres.sh backups/tradepilot_file.sql.gz"
  exit 1
fi

BACKUP_FILE="$1"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_USER="${POSTGRES_USER:-tradepilot}"
POSTGRES_DB="${POSTGRES_DB:-tradepilot}"

gzip -dc "${BACKUP_FILE}" | docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

echo "Restore completed from ${BACKUP_FILE}"
