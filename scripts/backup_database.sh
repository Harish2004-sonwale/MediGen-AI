#!/usr/bin/env bash
# ==============================================================================
# MediGen AI - Automated PostgreSQL Database Backup Script
# Creates timestamped, gzip-compressed database dumps with SHA-256 checksums
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/postgresql}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-medigen_ai}"
DB_USER="${POSTGRES_USER:-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILENAME="medigen_ai_${DB_NAME}_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
CHECKSUM_PATH="${BACKUP_PATH}.sha256"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u)] Starting automated backup for database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}..."

# Execute pg_dump with gzip compression
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --no-owner --clean --if-exists | gzip -9 > "${BACKUP_PATH}"; then
    # Verify non-empty backup file
    if [ ! -s "${BACKUP_PATH}" ]; then
        echo "[ERROR] Backup failed: Output file ${BACKUP_PATH} is empty!" >&2
        rm -f "${BACKUP_PATH}"
        exit 1
    fi

    # Calculate SHA-256 integrity checksum
    sha256sum "${BACKUP_PATH}" > "${CHECKSUM_PATH}"
    BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)

    echo "[$(date -u)] [SUCCESS] Backup created successfully!"
    echo "  Location: ${BACKUP_PATH} (${BACKUP_SIZE})"
    echo "  SHA-256 Checksum: $(cat "${CHECKSUM_PATH}")"

    # Prune old backups older than retention threshold
    echo "[$(date -u)] Pruning backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -type f -name "medigen_ai_*_backup_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -delete
    echo "[$(date -u)] Backup and pruning complete."
else
    echo "[ERROR] Database backup failed during pg_dump execution!" >&2
    exit 1
fi
