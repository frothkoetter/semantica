"""
Hive / Iceberg schema introspection for Semantica MCP tools.

Connects via impyla using HIVE_* environment variables (same as iceberg-mcp-server-hive).
Produces schema_info dicts compatible with map_db_schema_to_ontology.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set

_FK_COLUMN_RE = re.compile(r"^(.+)_id$", re.IGNORECASE)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_hive_connection():
    """Open HiveServer2 connection (impyla). Reuses iceberg-mcp helper when installed."""
    try:
        from iceberg_mcp_server.tools.hive_tools import get_db_connection

        return get_db_connection()
    except ImportError:
        from impala.dbapi import connect

        return connect(
            host=os.getenv("HIVE_HOST", "localhost"),
            port=int(os.getenv("HIVE_PORT", "443")),
            user=os.getenv("HIVE_USER", ""),
            password=os.getenv("HIVE_PASSWORD", ""),
            database=os.getenv("HIVE_DATABASE", "default"),
            auth_mechanism=os.getenv("HIVE_AUTH_MECHANISM", "LDAP"),
            use_http_transport=_env_bool("HIVE_USE_HTTP_TRANSPORT", True),
            http_path=os.getenv("HIVE_HTTP_PATH", "cliservice"),
            use_ssl=_env_bool("HIVE_USE_SSL", True),
        )


def _quote_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _list_tables(cursor: Any, database: str) -> List[str]:
    cursor.execute(f"SHOW TABLES IN {_quote_ident(database)}")
    return [row[0] for row in cursor.fetchall()]


def _describe_table(cursor: Any, database: str, table: str) -> List[Dict[str, Any]]:
    cursor.execute(f"DESCRIBE {_quote_ident(database)}.{_quote_ident(table)}")
    columns: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        col_name = row[0] if row else None
        if not col_name or not str(col_name).strip():
            continue
        name = str(col_name).strip()
        if name.startswith("#") or name.startswith("Partition"):
            break
        data_type = str(row[1]).strip() if len(row) > 1 and row[1] is not None else "string"
        comment = str(row[2]).strip() if len(row) > 2 and row[2] is not None else None
        entry: Dict[str, Any] = {
            "name": name,
            "type": data_type,
            "nullable": True,
        }
        if comment:
            entry["comment"] = comment
        columns.append(entry)
    return columns


def _normalize_table_token(name: str) -> str:
    token = name.lower().replace("_", "").replace("-", "")
    return token


def infer_foreign_keys(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Infer FK relationships from *_id column names against tables in the same database.

    Example: anschrift.juristische_person_id → juristische_person.id
    """
    by_token: Dict[str, str] = {_normalize_table_token(t["name"]): t["name"] for t in tables}
    foreign_keys: List[Dict[str, Any]] = []
    seen: Set[tuple] = set()

    for table in tables:
        table_name = table["name"]
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            if col_name.lower() == "id":
                continue
            match = _FK_COLUMN_RE.match(col_name)
            if not match:
                continue
            ref_token = _normalize_table_token(match.group(1))
            referred = by_token.get(ref_token)
            if not referred or referred == table_name:
                continue
            key = (table_name, col_name, referred)
            if key in seen:
                continue
            seen.add(key)
            foreign_keys.append(
                {
                    "constrained_table": table_name,
                    "referred_table": referred,
                    "constrained_columns": [col_name],
                    "referred_columns": ["id"],
                }
            )
    return foreign_keys


def introspect_hive_database(
    database: str,
    tables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Introspect Hive/Iceberg database → schema_info for map_db_schema_to_ontology.

    Uses SHOW TABLES + DESCRIBE per table (same data as iceberg-mcp get_schema + execute_query).
    """
    conn = None
    try:
        conn = get_hive_connection()
        cur = conn.cursor()

        table_names = tables or _list_tables(cur, database)
        table_defs: List[Dict[str, Any]] = []
        for table_name in table_names:
            columns = _describe_table(cur, database, table_name)
            table_defs.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "primary_keys": ["id"] if any(c["name"] == "id" for c in columns) else [],
                    "indexes": [],
                }
            )

        foreign_keys = infer_foreign_keys(table_defs)
        cur.close()

        return {
            "database": database,
            "tables": table_defs,
            "views": [],
            "foreign_keys": foreign_keys,
            "analysis": {
                "total_tables": len(table_defs),
                "total_views": 0,
                "total_foreign_keys": len(foreign_keys),
                "source": "hive_introspection",
                "hive_host": os.getenv("HIVE_HOST"),
            },
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def introspect_hive_database_json(database: str, tables: Optional[List[str]] = None) -> str:
    """JSON wrapper for MCP tools."""
    try:
        payload = introspect_hive_database(database, tables=tables)
        return json.dumps(payload, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps(
            {
                "error": (
                    "impyla is required. Install with: pip install impyla "
                    "or use iceberg-mcp-server-hive with get_database_schema_info."
                )
            }
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})
