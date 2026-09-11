#!/usr/bin/env python3
"""Provision KDM Iceberg tables on Hive/CDW using iceberg-mcp-server-hive connection."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DDL_PATH = Path(__file__).with_name("kdm_ddl.sql")
SEED_PATH = Path(__file__).with_name("kdm_seed.sql")


def load_mcp_env(config_path: Path) -> None:
    payload = json.loads(config_path.read_text())
    servers = payload.get("mcpServers") or {}
    hive = servers.get("iceberg-mcp-server-hive") or {}
    for key, value in (hive.get("env") or {}).items():
        os.environ.setdefault(key, str(value))


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL file on semicolons outside comments (simple splitter)."""
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buffer).rstrip(";").strip())
            buffer = []
    if buffer:
        statements.append("\n".join(buffer).strip())
    return [s for s in statements if s]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create KDM Iceberg schema on Hive")
    parser.add_argument(
        "--mcp-config",
        type=Path,
        default=Path.home() / ".cursor" / "mcp.json",
        help="Cursor MCP config with iceberg-mcp-server-hive env block",
    )
    parser.add_argument("--seed", action="store_true", help="Also insert demo seed rows")
    parser.add_argument("--ddl-only", action="store_true", help="Skip seed data")
    args = parser.parse_args()

    if args.mcp_config.is_file():
        load_mcp_env(args.mcp_config)

    try:
        from iceberg_mcp_server.tools import hive_tools
    except ImportError:
        print(
            "iceberg_mcp_server not installed. Run from iceberg-mcp-server-hive repo:\n"
            "  uv run python /path/to/setup_kdm_hive.py",
            file=sys.stderr,
        )
        return 1

    ddl_sql = DDL_PATH.read_text(encoding="utf-8")
    statements = split_sql_statements(ddl_sql)

    print(f"Running {len(statements)} DDL statements against {os.getenv('HIVE_HOST')} ...")
    for stmt in statements:
        label = re.sub(r"\s+", " ", stmt.split("\n", 1)[0])[:80]
        result = hive_tools.execute_ddl(stmt)
        if result.startswith("Error:"):
            print(f"FAIL: {label}\n  {result}", file=sys.stderr)
            return 1
        print(f"OK: {label}")

    if args.seed and not args.ddl_only:
        seed_sql = SEED_PATH.read_text(encoding="utf-8")
        seed_stmts = split_sql_statements(seed_sql)
        print(f"\nInserting {len(seed_stmts)} seed batches ...")
        for stmt in seed_stmts:
            label = re.sub(r"\s+", " ", stmt.split("\n", 1)[0])[:80]
            result = hive_tools.execute_sql(stmt)
            if result.startswith("Error:"):
                print(f"WARN: {label}\n  {result}", file=sys.stderr)
            else:
                print(f"OK: {label}")

    schema = hive_tools.get_schema("kdm")
    print("\nSchema kdm:", schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
