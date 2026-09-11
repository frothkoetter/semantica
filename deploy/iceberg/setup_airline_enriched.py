#!/usr/bin/env python3
"""OPTIONAL: create airlinedata.flight_enriched view (not used by Semantica runtime path)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DDL_PATH = Path(__file__).with_name("airline_flight_enriched.sql")


def load_mcp_env(config_path: Path) -> None:
    payload = json.loads(config_path.read_text())
    for server in (payload.get("mcpServers") or {}).values():
        for key, value in (server.get("env") or {}).items():
            if key.startswith("HIVE_"):
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
    parser = argparse.ArgumentParser(description="Create flight_enriched Hive view")
    parser.add_argument(
        "--mcp-config",
        type=Path,
        default=Path(__file__).resolve().parents[2] / ".cursor" / "mcp.json",
    )
    args = parser.parse_args()

    if args.mcp_config.is_file():
        load_mcp_env(args.mcp_config)

    try:
        from iceberg_mcp_server.tools import hive_tools
    except ImportError:
        try:
            from semantica.mcp_server.hive_schema import get_hive_connection

            conn = get_hive_connection()
            cur = conn.cursor()
            for stmt in split_sql_statements(DDL_PATH.read_text(encoding="utf-8")):
                print(stmt[:80], "...")
                cur.execute(stmt)
            cur.close()
            conn.close()
            print("flight_enriched view created via impyla.")
            return 0
        except ImportError:
            print(
                "Install iceberg-mcp-server-hive or semantica with impyla.",
                file=sys.stderr,
            )
            return 1

    for stmt in split_sql_statements(DDL_PATH.read_text(encoding="utf-8")):
        label = re.sub(r"\s+", " ", stmt.split("\n", 1)[0])[:80]
        result = hive_tools.execute_ddl(stmt)
        if result.startswith("Error:"):
            print(f"FAIL: {label}\n  {result}", file=sys.stderr)
            return 1
        print(f"OK: {label}")

    verify = hive_tools.execute_query(
        "SELECT scheduled_in_window, flight_status, COUNT(*) AS n "
        "FROM airlinedata.flight_enriched WHERE year = 2008 "
        "GROUP BY scheduled_in_window, flight_status ORDER BY n DESC LIMIT 5"
    )
    print("Sample:", verify[:500] if isinstance(verify, str) else verify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
