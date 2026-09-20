#!/bin/bash
# ============================================================
# ONE-SHOT MIGRATION COMPLETION SCRIPT
# Run: bash run_migration_complete.sh
# ============================================================

set -e
cd "$(dirname "$0")"

echo ""
echo "=================================================="
echo "  MYNTRA DB: PostgreSQL + DuckDB Migration Setup"
echo "=================================================="
echo ""

# ── 1. Check PostgreSQL is up ─────────────────────────────
echo "[1/5] Checking PostgreSQL connection..."
export PGPASSWORD=alan1234
PG_BIN="/opt/homebrew/opt/postgresql@17/bin"
if [ ! -d "$PG_BIN" ]; then
    PG_BIN="/opt/homebrew/bin"
fi
PSQL="$PG_BIN/psql"

if ! $PSQL -U postgres -c "SELECT 1" postgres > /dev/null 2>&1; then
    echo "  → Starting PostgreSQL..."
    brew services start postgresql@17 2>/dev/null || brew services start postgresql 2>/dev/null || true
    sleep 3
fi

if ! $PSQL -U postgres -c "SELECT 1" postgres > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to PostgreSQL. Check that it is running."
    echo "  Try: brew services start postgresql@17"
    exit 1
fi
echo "  ✓ PostgreSQL is up"

# ── 2. Create database if missing ────────────────────────
echo ""
echo "[2/5] Ensuring 'myntra' database exists..."
DB_EXISTS=$($PSQL -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='myntra'" postgres 2>/dev/null || echo "")
if [ "$DB_EXISTS" != "1" ]; then
    $PSQL -U postgres -c "CREATE DATABASE myntra;" postgres
    echo "  ✓ Database 'myntra' created"
else
    echo "  ✓ Database 'myntra' already exists"
fi

# ── 3. Install Python deps ────────────────────────────────
echo ""
echo "[3/5] Installing Python dependencies..."
pip3 install psycopg2-binary duckdb python-dotenv --quiet --break-system-packages 2>/dev/null || \
pip3 install psycopg2-binary duckdb python-dotenv --quiet 2>/dev/null || true
echo "  ✓ Dependencies ready"

# ── 4. Run schema ─────────────────────────────────────────
echo ""
echo "[4/5] Running PostgreSQL schema creation..."
python3 pg_schema.py
echo "  ✓ Schema created"

# ── 5. Build DuckDB analytics ─────────────────────────────
echo ""
echo "[5/5] Building DuckDB analytics layer..."
python3 build_duckdb.py 2>/dev/null || python3 sync_pg_to_duckdb.py
echo "  ✓ DuckDB analytics ready"

# ── Done ──────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  ✅ ALL DONE! PostgreSQL + DuckDB setup complete."
echo ""
echo "  Next steps:"
echo "  • Validate:  python3 validate_migration.py"
echo "  • Benchmark: python3 benchmark_migration.py"
echo "  • Start app: python3 server.py"
echo "=================================================="
