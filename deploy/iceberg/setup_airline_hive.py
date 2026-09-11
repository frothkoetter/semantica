#!/usr/bin/env python3
"""Provision Airline Iceberg tables on Hive/CDW (disjoint from KDM)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DDL_PATH = Path(__file__).with_name("airline_ddl.sql")
SEED_PATH = Path(__file__).with_name("airline_seed.sql")


def load_mcp_env(config_path: Path) -> None:
    payload = json.loads(config_path.read_text())
    servers = payload.get("mcpServers") or {}
    hive = servers.get("iceberg-mcp-server-hive") or {}
    for key, value in (hive.get("env") or {}).items():
        os.environ.setdefault(key, str(value))


def split_sql_statements(sql: str) -> list[str]:
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
    parser = argparse.ArgumentParser(description="Create Airline Iceberg schema on Hive")
    parser.add_argument(
        "--mcp-config",
        type=Path,
        default=Path.home() / ".cursor" / "mcp.json",
    )
    parser.add_argument("--seed", action="store_true", help="Insert demo seed rows")
    args = parser.parse_args()

    if args.mcp_config.is_file():
        load_mcp_env(args.mcp_config)

    try:
        from iceberg_mcp_server.tools import hive_tools
    except ImportError:
        print(
            "Run from iceberg-mcp-server-hive:\n"
            "  uv run python /path/to/setup_airline_hive.py --seed",
            file=sys.stderr,
        )
        return 1

    statements = split_sql_statements(DDL_PATH.read_text(encoding="utf-8"))
    print(f"Running {len(statements)} DDL statements ...")
    for stmt in statements:
        label = re.sub(r"\s+", " ", stmt.split("\n", 1)[0])[:80]
        result = hive_tools.execute_ddl(stmt)
        if result.startswith("Error:"):
            print(f"FAIL: {label}\n  {result}", file=sys.stderr)
            return 1
        print(f"OK: {label}")

    if args.seed:
        for stmt in split_sql_statements(SEED_PATH.read_text(encoding="utf-8")):
            label = re.sub(r"\s+", " ", stmt.split("\n", 1)[0])[:80]
            result = hive_tools.execute_sql(stmt)
            if result.startswith("Error:"):
                print(f"WARN: {label}\n  {result}", file=sys.stderr)
            else:
                print(f"OK: {label}")

    print("\nSchema airline:", hive_tools.get_schema("airline"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
