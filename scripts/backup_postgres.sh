#!/usr/bin/env bash
set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-verbpractice-pg}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-verbpractice}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

timestamp="$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
backup_path="${BACKUP_DIR}/${POSTGRES_DB}_${timestamp}.dump"

echo "Creating PostgreSQL backup at ${backup_path}"
docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${backup_path}"
echo "Backup completed: ${backup_path}"
