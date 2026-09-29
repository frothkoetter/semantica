#!/usr/bin/env bash
# Create XUnternehmen KDM demo database, tables (Iceberg), and load seed data.
#
# Usage:
#   ./kdm/hive/setup_kdm_demo.sh              # medium (default)
#   ./kdm/hive/setup_kdm_demo.sh small
#   ./kdm/hive/setup_kdm_demo.sh large
#   ./kdm/hive/setup_kdm_demo.sh ddl-only
#
# Requires kdm/hive/hive.env.local (copy from hive.env.example).

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HIVE_DIR="$REPO/kdm/hive"
PROFILE="${1:-medium}"

ENV_FILE="$HIVE_DIR/hive.env.local"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
else
  echo "Missing $ENV_FILE — copy hive.env.example and set HIVE_USER/HIVE_PASSWORD" >&2
  exit 1
fi

export HIVE_DATABASE="${HIVE_DATABASE:-xunternehmen}"
PYTHON="${PYTHON:-$REPO/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

run_sql() {
  echo "==> $1"
  "$PYTHON" "$HIVE_DIR/run_hive_sql.py" "$1"
}

echo "Database target: $HIVE_DATABASE"
echo "Profile: $PROFILE"

run_sql "$HIVE_DIR/xunternehmen_ddl.sql"

case "$PROFILE" in
  ddl-only)
    echo "DDL only — skipping seed."
    ;;
  small)
    run_sql "$HIVE_DIR/xunternehmen_seed.sql"
    ;;
  medium)
    SEED="$HIVE_DIR/xunternehmen_seed_medium.sql"
    if [[ ! -f "$SEED" ]]; then
      echo "Generating medium seed (scale 0.02)..."
      "$PYTHON" "$HIVE_DIR/generate_xunternehmen_seed.py" \
        --scale 0.02 --output "$SEED"
    fi
    run_sql "$SEED"
    ;;
  large)
    SEED="$HIVE_DIR/xunternehmen_seed_large.sql"
    if [[ ! -f "$SEED" ]]; then
      echo "Generating large seed (may take a minute)..."
      "$PYTHON" "$HIVE_DIR/generate_xunternehmen_seed.py" --output "$SEED"
    fi
    run_sql "$SEED"
    ;;
  *)
    echo "Unknown profile: $PROFILE (use small|medium|large|ddl-only)" >&2
    exit 1
    ;;
esac

echo "Done. Verify: SELECT COUNT(*) FROM ${HIVE_DATABASE}.juristische_person;"
