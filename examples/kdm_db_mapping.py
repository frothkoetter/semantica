#!/usr/bin/env python3
"""
XUnternehmen.Kerndatenmodell (KDM) — DB schema mapping example.

Workflow:
  1. Import KDM ontology into ContextGraph
  2. Map a SQL schema using explicit config/kdm_db_mapping.yaml
  3. Export resulting context graph

Usage:
  python examples/kdm_db_mapping.py
  python examples/kdm_db_mapping.py --db postgresql://user:pass@localhost/kdm_db
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from semantica.context import ContextGraph
from semantica.mcp_server.kdm_mappings import (
    apply_explicit_mappings,
    default_mapping_config_path,
    load_mapping_config,
)
from pathlib import Path

from semantica.mcp_server.ontology_tools import (
    handle_import_ontology,
    handle_map_db_schema_to_ontology,
)

KDM_NAMESPACE = "https://w3id.org/kdm/"


def _demo_schema() -> dict:
    """Representative German business-register style tables."""
    return {
        "tables": [
            {
                "name": "natuerliche_person",
                "columns": [
                    {"name": "id", "type": "UUID"},
                    {"name": "familienname", "type": "VARCHAR"},
                    {"name": "vornamen", "type": "VARCHAR"},
                    {"name": "geburtsdatum", "type": "DATE"},
                    {"name": "geschlecht", "type": "VARCHAR"},
                ],
            },
            {
                "name": "juristische_person",
                "columns": [
                    {"name": "id", "type": "UUID"},
                    {"name": "firmenname", "type": "VARCHAR"},
                    {"name": "rechtsform", "type": "VARCHAR"},
                ],
            },
            {
                "name": "anschrift",
                "columns": [
                    {"name": "id", "type": "UUID"},
                    {"name": "strasse", "type": "VARCHAR"},
                    {"name": "hausnummer", "type": "VARCHAR"},
                    {"name": "postleitzahl", "type": "VARCHAR"},
                    {"name": "ort", "type": "VARCHAR"},
                ],
            },
            {
                "name": "eintragung",
                "columns": [
                    {"name": "id", "type": "UUID"},
                    {"name": "registergericht", "type": "VARCHAR"},
                    {"name": "eintragungsnummer", "type": "VARCHAR"},
                ],
            },
        ],
        "foreign_keys": [
            {
                "constrained_table": "anschrift",
                "referred_table": "juristische_person",
            }
        ],
        "views": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="KDM DB schema mapping demo")
    parser.add_argument(
        "--db",
        help="SQLAlchemy connection string (optional; uses demo schema if omitted)",
    )
    parser.add_argument("--schema", help="Database schema name", default=None)
    parser.add_argument(
        "--mapping-config",
        help="Path to kdm_db_mapping.yaml",
        default=default_mapping_config_path(),
    )
    parser.add_argument(
        "--output",
        help="Write ContextGraph JSON to this path",
        default="kdm_context_graph.json",
    )
    args = parser.parse_args()

    graph = ContextGraph(advanced_analytics=True)
    get_graph = lambda: graph

    kdm_path = Path(__file__).resolve().parents[1] / "data" / "kdm_ontology.ttl"
    print("1. Importing KDM ontology from", kdm_path)
    import_result = handle_import_ontology(
        {
            "file_path": str(kdm_path),
            "namespace_filter": KDM_NAMESPACE,
        },
        get_graph,
    )
    if "error" in import_result:
        print("Import failed:", import_result["error"], file=sys.stderr)
        return 1
    print(json.dumps(import_result.get("stats", {}), indent=2))

    print("\n2. Loading mapping config:", args.mapping_config)
    config = load_mapping_config(args.mapping_config)
    print(f"   Tables defined: {len(config.get('tables', {}))}")

    map_args = {
        "mapping_config_path": args.mapping_config,
        "apply_mappings": True,
    }
    if args.db:
        map_args["connection_string"] = args.db
        map_args["schema"] = args.schema
    else:
        map_args["schema_info"] = _demo_schema()

    print("\n3. Mapping DB schema to KDM...")
    map_result = handle_map_db_schema_to_ontology(map_args, get_graph)
    if "error" in map_result:
        print("Mapping failed:", map_result["error"], file=sys.stderr)
        return 1

    summary = map_result["suggestions"]["summary"]
    print(json.dumps(summary, indent=2))
    print("Applied:", map_result.get("applied", {}))

    print(f"\n4. Saving graph to {args.output}")
    graph.save_to_file(args.output)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
