#!/usr/bin/env bash
# ==============================================================================
# MediGen AI - Database Restoration Script
# Safely restores a compressed PostgreSQL database backup with checksum check
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup.sql.gz> [--force]"
    exit 1
fi

BACKUP_FILE="$1"
FORCE_MODE="${2:-}"

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-medigen_ai}"
DB_USER="${POSTGRES_USER:-postgres}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

# Verify SHA-256 checksum if .sha256 file exists
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
    echo "[$(date -u)] Verifying SHA-256 checksum against ${CHECKSUM_FILE}..."
    if sha256sum -c "${CHECKSUM_FILE}"; then
        echo "[SUCCESS] SHA-256 checksum verified."
    else
        echo "[ERROR] Checksum verification failed! File may be corrupted or tampered with." >&2
        exit 1
    fi
else
    echo "[WARNING] No SHA-256 checksum file found. Proceeding with caution."
fi

# Confirmation prompt unless --force is specified
if [ "${FORCE_MODE}" != "--force" ]; then
    echo ""
    echo "================================================================="
    echo " WARNING: THIS WILL OVERWRITE DATA IN DATABASE: ${DB_NAME}"
    echo " Target: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo " Backup: ${BACKUP_FILE}"
    echo "================================================================="
    read -p "Are you sure you want to proceed with restore? (yes/no): " CONFIRMATION
    if [ "${CONFIRMATION}" != "yes" ]; then
        echo "Restore cancelled by user."
        exit 0
    fi
fi

echo "[$(date -u)] Starting database restoration into ${DB_NAME} on ${DB_HOST}:${DB_PORT}..."

if gunzip -c "${BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"; then
    echo "[$(date -u)] [SUCCESS] Database restore completed successfully!"
    # Verify connectivity & basic schema
    TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
    echo "  Total public tables verified: ${TABLE_COUNT}"
else
    echo "[ERROR] Database restoration encountered an error!" >&2
    exit 1
fi
