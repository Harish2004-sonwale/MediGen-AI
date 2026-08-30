#!/usr/bin/env bash
# ==============================================================================
# MediGen AI - Production Database Migration Script
# Safe migration execution with automatic pre-migration backup & lock timeouts
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend"

echo "================================================================="
echo " MediGen AI - Production Database Migration Runner"
echo "================================================================="

# Step 1: Create automatic safety backup before running migrations
echo "[$(date -u)] [1/4] Triggering pre-migration database snapshot..."
if [ -f "${SCRIPT_DIR}/backup_database.sh" ]; then
    bash "${SCRIPT_DIR}/backup_database.sh" || {
        echo "[ERROR] Pre-migration backup failed! Aborting migration to prevent data loss risk." >&2
        exit 1
    }
fi

# Step 2: Validate Alembic migrations via SQL dry-run
echo "[$(date -u)] [2/4] Validating pending migrations via SQL dry-run..."
cd "${BACKEND_DIR}"
if alembic upgrade head --sql > /dev/null; then
    echo "[SUCCESS] Alembic SQL generation check passed."
else
    echo "[ERROR] Alembic SQL dry-run failed! Aborting migration." >&2
    exit 1
fi

# Step 3: Apply migrations with lock timeout safeguard
echo "[$(date -u)] [3/4] Applying migrations to production database (alembic upgrade head)..."
# Setting statement & lock timeouts (10 seconds) prevents migration from deadlocking live transactions
export PGOPTIONS="-c lock_timeout=10000 -c statement_timeout=60000"

if alembic upgrade head; then
    echo "[$(date -u)] [4/4] [SUCCESS] All database migrations applied successfully!"
    CURRENT_REV=$(alembic current)
    echo "  Current database revision: ${CURRENT_REV}"
else
    echo ""
    echo "[ERROR] Migration failed! Live database may be in an inconsistent state." >&2
    echo "  Recommended recovery action:"
    echo "    1. Review the error log above."
    echo "    2. Execute rollback: alembic downgrade -1"
    echo "    3. If necessary, restore pre-migration snapshot using scripts/restore_database.sh."
    exit 1
fi
