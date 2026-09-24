#!/usr/bin/env python3
"""
Execute Hive SQL files via impyla (HS2 HTTP + LDAP).

Uses HIVE_* environment variables (same as iceberg-mcp-server-hive):
  HIVE_HOST, HIVE_PORT, HIVE_USER, HIVE_PASSWORD, HIVE_DATABASE,
  HIVE_USE_HTTP_TRANSPORT, HIVE_HTTP_PATH, HIVE_USE_SSL, HIVE_AUTH_MECHANISM

Example:
  export HIVE_HOST=hs2-cdw-aw-se-hive.dw-se-sandbox-aws.a465-9q4k.cloudera.site
  export HIVE_PORT=443
  export HIVE_USER=your_user
  export HIVE_PASSWORD=your_password
  export HIVE_DATABASE=default
  export HIVE_USE_HTTP_TRANSPORT=true
  export HIVE_HTTP_PATH=cliservice
  export HIVE_USE_SSL=true
  export HIVE_AUTH_MECHANISM=LDAP

  python kdm/hive/run_hive_sql.py kdm/hive/xunternehmen_ddl.sql
  python kdm/hive/run_hive_sql.py kdm/hive/xunternehmen_seed_large.sql
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def split_sql(text: str) -> list[str]:
    """Split SQL file into statements (handles trailing semicolons)."""
    # Remove line comments
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    parts = re.split(r";\s*\n", body)
    return [p.strip() for p in parts if p.strip()]


def get_connection():
    from semantica.mcp_server.hive_schema import get_hive_connection

    return get_hive_connection()


def run_file(path: Path, *, dry_run: bool = False, start_at: int = 0) -> dict:
    statements = split_sql(path.read_text(encoding="utf-8"))
    stats = {"file": str(path), "total": len(statements), "ok": 0, "failed": 0, "errors": []}

    if dry_run:
        print(f"Dry run: {len(statements)} statements in {path.name}")
        for i, stmt in enumerate(statements[:5], start=1):
            print(f"  [{i}] {stmt[:120]}...")
        return stats

    conn = get_connection()
    cur = conn.cursor()
    try:
        for i, stmt in enumerate(statements):
            if i < start_at:
                continue
            t0 = time.time()
            try:
                cur.execute(stmt)
                stats["ok"] += 1
                elapsed = time.time() - t0
                if (i + 1) % 10 == 0 or elapsed > 5:
                    print(f"[{i + 1}/{len(statements)}] ok ({elapsed:.1f}s)")
            except Exception as exc:
                stats["failed"] += 1
                stats["errors"].append({"index": i, "error": str(exc), "sql": stmt[:500]})
                print(f"[{i + 1}/{len(statements)}] FAILED: {exc}", file=sys.stderr)
                if stats["failed"] >= 5:
                    print("Too many errors; aborting.", file=sys.stderr)
                    break
    finally:
        cur.close()
        conn.close()

    return stats


def _load_local_env() -> None:
    """Load kdm/hive/hive.env.local if present (gitignored)."""
    env_file = Path(__file__).resolve().parent / "hive.env.local"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hive SQL file via impyla")
    parser.add_argument("sql_files", nargs="+", type=Path, help="SQL files to execute in order")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-at", type=int, default=0, help="Resume at statement index")
    args = parser.parse_args()

    _load_local_env()

    required = ["HIVE_HOST", "HIVE_USER", "HIVE_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing and not args.dry_run:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("Set HIVE_* variables (see script docstring).", file=sys.stderr)
        return 1

    for path in args.sql_files:
        if not path.is_file():
            print(f"Not found: {path}", file=sys.stderr)
            return 1
        stats = run_file(path, dry_run=args.dry_run, start_at=args.start_at)
        print(f"{path.name}: {stats['ok']}/{stats['total']} ok, {stats['failed']} failed")
        if stats["failed"]:
            for err in stats["errors"][:3]:
                print(f"  error at #{err['index']}: {err['error']}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
