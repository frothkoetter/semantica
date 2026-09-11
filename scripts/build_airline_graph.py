#!/usr/bin/env python3
"""
Import airline + business ontologies, map airlinedata Hive schema, save graph.

Phase 1 (default): validate ontologies, export data/airline_graph.ttl,
write data/airline_ontology_validation.json, and generate ontology HTML viz.

Usage:
  export HIVE_DATABASE=airlinedata HIVE_HOST=... (see .cursor/mcp.json)
  python scripts/build_airline_graph.py
  python scripts/build_airline_graph.py --skip-hive   # ontology only, no DB introspection
  python scripts/build_airline_graph.py --skip-phase1 # graph JSON only, no validate/export/viz
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "examples"))


def load_mcp_env() -> None:
    mcp = REPO / ".cursor" / "mcp.json"
    if not mcp.is_file():
        return
    import json

    payload = json.loads(mcp.read_text())
    for server in (payload.get("mcpServers") or {}).values():
        for key, value in (server.get("env") or {}).items():
            if key.startswith("HIVE_") or key == "SEMANTICA_KG_PATH":
                os.environ.setdefault(key, str(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/airline_graph.json")
    parser.add_argument(
        "--output",
        default=str(REPO / "data" / "airline_graph.json"),
    )
    parser.add_argument(
        "--mapping",
        default=str(REPO / "config" / "airline_r2rml_db_mapping.yaml"),
    )
    parser.add_argument(
        "--database",
        default=os.getenv("HIVE_DATABASE", "airlinedata"),
    )
    parser.add_argument("--skip-hive", action="store_true")
    parser.add_argument(
        "--skip-phase1",
        action="store_true",
        help="Skip validation, Turtle export, and ontology visualizations",
    )
    parser.add_argument(
        "--ttl-output",
        default=str(REPO / "data" / "airline_graph.ttl"),
    )
    parser.add_argument(
        "--validation-output",
        default=str(REPO / "data" / "airline_ontology_validation.json"),
    )
    parser.add_argument(
        "--ontology-viz-dir",
        default=str(REPO / "data" / "airline_ontology_viz"),
    )
    args = parser.parse_args()
    load_mcp_env()

    from semantica.context import ContextGraph
    from semantica.mcp_server.ontology_tools import (
        handle_import_ontology,
        handle_map_iceberg_schema_to_ontology,
    )

    graph = ContextGraph(advanced_analytics=True)

    def get_graph():
        return graph

    ns = "https://w3id.org/demo/airline#"
    for ttl in (
        REPO / "data" / "airline_demo_ontology.ttl",
        REPO / "data" / "airline_business_ontology.ttl",
    ):
        print(f"Importing {ttl.name} ...")
        result = handle_import_ontology(
            {
                "file_path": str(ttl),
                "namespace_filter": ns,
                "include_properties": True,
            },
            get_graph,
        )
        if "error" in result:
            print(json.dumps(result, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(result.get("stats", {}), indent=2))

    if not args.skip_hive:
        print(f"Mapping Hive database {args.database} ...")
        map_result = handle_map_iceberg_schema_to_ontology(
            {
                "database": args.database,
                "import_kdm_if_missing": False,
                "use_kdm_defaults": False,
                "mapping_config_path": args.mapping,
                "apply_mappings": True,
            },
            get_graph,
        )
        if map_result.get("error"):
            print(json.dumps(map_result, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(map_result.get("applied"), indent=2))
        print(json.dumps(map_result.get("suggestions", {}).get("summary"), indent=2))

    graph.save_to_file(args.output)
    print(f"Saved {args.output} ({graph.stats()['node_count']} nodes)")

    if not args.skip_phase1:
        from airline_graph_governance import run_phase1

        try:
            phase1 = run_phase1(
                graph,
                graph_json_path=Path(args.output),
                graph_ttl_path=Path(args.ttl_output),
                validation_json_path=Path(args.validation_output),
                ontology_viz_dir=Path(args.ontology_viz_dir),
                validate_graph=not args.skip_hive,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("Phase 1 governance:")
        print(json.dumps(phase1, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
