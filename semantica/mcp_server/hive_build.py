"""
Internal Hive/Iceberg build helpers — not exposed as MCP tools.

Used by scripts/build_airline_graph.py and tests. Runtime SQL/schema access
belongs to iceberg-mcp-server-hive; pass schema_info into
map_db_schema_to_ontology via MCP when needed.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from semantica.mcp_server.ontology_tools import (
    _collect_ontology_classes_from_graph,
    handle_import_ontology,
    handle_map_db_schema_to_ontology,
)

log = logging.getLogger("semantica.mcp.hive_build")


def _default_hive_database(args: dict) -> str:
    return (args.get("database") or os.environ.get("HIVE_DATABASE") or "").strip()


def handle_get_hive_schema_info(args: dict) -> dict:
    """Introspect Hive/Iceberg and return schema_info for map_db_schema_to_ontology."""
    database = _default_hive_database(args)
    if not database:
        return {"error": "database is required (argument or HIVE_DATABASE env)"}
    tables = args.get("tables")
    if tables is not None and not isinstance(tables, list):
        return {"error": "tables must be a list of table names"}

    try:
        from semantica.mcp_server.hive_schema import introspect_hive_database

        schema_info = introspect_hive_database(database, tables=tables)
        return {
            "status": "ok",
            "database": database,
            "schema_info": schema_info,
            "summary": schema_info.get("analysis", {}),
        }
    except ImportError as exc:
        return {
            "error": (
                "Hive introspection requires impyla and HIVE_* env vars. "
                "Use iceberg-mcp-server-hive get_database_schema_info at runtime."
            ),
            "detail": str(exc),
        }
    except Exception as exc:
        log.exception("get_hive_schema_info failed")
        return {"error": str(exc)}


def handle_map_iceberg_schema_to_ontology(args: dict, get_graph) -> dict:
    """Build-time one-shot: introspect Hive → optional ontology import → map to graph."""
    database = _default_hive_database(args)
    if not database:
        return {"error": "database is required (argument or HIVE_DATABASE env)"}
    tables = args.get("tables")
    import_if_missing = bool(args.get("import_ontology_if_missing", False))
    ontology_file_path = (args.get("ontology_file_path") or "").strip() or None
    ontology_url = (args.get("ontology_url") or "").strip() or None
    namespace_filter = (args.get("namespace_filter") or "").strip() or None

    try:
        from semantica.mcp_server.hive_schema import introspect_hive_database

        schema_info = introspect_hive_database(database, tables=tables)

        graph = get_graph()
        if not _collect_ontology_classes_from_graph(graph):
            if ontology_file_path or ontology_url:
                import_args: Dict[str, Any] = {
                    "include_properties": args.get("include_properties", True),
                }
                if ontology_file_path:
                    import_args["file_path"] = ontology_file_path
                if ontology_url:
                    import_args["url"] = ontology_url
                if namespace_filter:
                    import_args["namespace_filter"] = namespace_filter
                import_result = handle_import_ontology(import_args, get_graph)
                if "error" in import_result:
                    return {
                        "error": "Ontology import failed before mapping",
                        "import_error": import_result["error"],
                        "schema_info": schema_info,
                    }
            elif import_if_missing:
                return {
                    "error": (
                        "No OntologyClass nodes in graph. "
                        "Provide ontology_file_path, ontology_url, or call import_ontology first."
                    ),
                    "schema_info": schema_info,
                }
            else:
                return {
                    "error": (
                        "No OntologyClass nodes in graph. "
                        "Call import_ontology first or set import_ontology_if_missing with a source."
                    ),
                    "schema_info": schema_info,
                }

        map_result = handle_map_db_schema_to_ontology(
            {
                "schema_info": schema_info,
                "mapping_config_path": args.get("mapping_config_path"),
                "apply_mappings": args.get("apply_mappings", True),
            },
            get_graph,
        )
        map_result["database"] = database
        map_result["schema_info_summary"] = schema_info.get("analysis", {})
        return map_result
    except ImportError as exc:
        return {
            "error": (
                "Hive introspection requires impyla and HIVE_* env vars. "
                "Use iceberg-mcp get_database_schema_info, then map_db_schema_to_ontology."
            ),
            "detail": str(exc),
        }
    except Exception as exc:
        log.exception("map_iceberg_schema_to_ontology failed")
        return {"error": str(exc)}
