#!/usr/bin/env python3
"""
Build XUnternehmen knowledge graph: ontology + optional Hive mapping + business rules + decisions.

Outputs:
  kdm/xunternehmen_kg.json              — ontology only (via import)
  kdm/xunternehmen_kg_with_decisions.json — full demo graph (default --output)

Usage:
  python kdm/build_xunternehmen_graph.py
  python kdm/build_xunternehmen_graph.py --skip-hive
  python kdm/build_xunternehmen_graph.py --ontology-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KDM = REPO / "kdm"
OWL = KDM / "ontology.owl"
DEFAULT_OUT = KDM / "xunternehmen_kg_with_decisions.json"
ONTOLOGY_OUT = KDM / "xunternehmen_kg.json"
MAPPING = REPO / "config" / "xunternehmen_r2rml_db_mapping.yaml"
RULES = REPO / "config" / "xunternehmen_business_rules.yaml"


def load_hive_env() -> None:
    for path in (REPO / "kdm" / "hive" / "hive.env.local", REPO / ".cursor" / "mcp.json"):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            payload = json.loads(path.read_text())
            for server in (payload.get("mcpServers") or {}).values():
                for key, value in (server.get("env") or {}).items():
                    if key.startswith("HIVE_"):
                        os.environ.setdefault(key, str(value))
        else:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XUnternehmen Semantica graph")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--mapping", default=str(MAPPING))
    parser.add_argument("--business-rules", default=str(RULES))
    parser.add_argument("--database", default=os.getenv("HIVE_DATABASE", "xunternehmen"))
    parser.add_argument("--skip-hive", action="store_true", help="Skip map_db_schema_to_ontology")
    parser.add_argument(
        "--ontology-only",
        action="store_true",
        help="Save ontology-only graph to kdm/xunternehmen_kg.json and exit",
    )
    parser.add_argument("--skip-decisions", action="store_true", help="Skip demo record_decision nodes")
    args = parser.parse_args()
    load_hive_env()

    if not OWL.is_file():
        print(f"Ontology not found: {OWL}", file=sys.stderr)
        return 1

    from semantica.context import ContextGraph
    from semantica.mcp_server.hive_build import handle_map_iceberg_schema_to_ontology
    from semantica.mcp_server.ontology_tools import handle_import_ontology

    graph = ContextGraph(advanced_analytics=True)

    def get_graph():
        return graph

    print(f"Importing {OWL.name} ...")
    result = handle_import_ontology(
        {
            "file_path": str(OWL),
            "namespace_filter": "https://w3id.org/kdm/",
            "include_properties": True,
        },
        get_graph,
    )
    if "error" in result:
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result.get("stats", {}), indent=2))

    if not args.skip_hive and not args.ontology_only:
        print(f"Mapping Hive database {args.database} ...")
        map_result = handle_map_iceberg_schema_to_ontology(
            {
                "database": args.database,
                "mapping_config_path": args.mapping,
                "apply_mappings": True,
            },
            get_graph,
        )
        if map_result.get("error"):
            print(json.dumps(map_result, indent=2), file=sys.stderr)
            print("Continuing without Hive schema nodes (use --skip-hive to suppress this step).")
        else:
            print(json.dumps(map_result.get("applied"), indent=2))

    rules_path = Path(args.business_rules)
    if rules_path.is_file() and not args.ontology_only:
        from semantica.mcp_server.business_rules import ingest_business_rules_into_graph, load_business_rules

        print(f"Ingesting business rules from {rules_path.name} ...")
        rules = load_business_rules(str(rules_path))
        print(json.dumps(ingest_business_rules_into_graph(graph, rules, source_path=str(rules_path)), indent=2))

    if args.ontology_only:
        graph.save_to_file(str(ONTOLOGY_OUT))
        print(f"Saved {ONTOLOGY_OUT} ({graph.stats()['node_count']} nodes)")
        return 0

    if not args.skip_decisions:
        from record_xunternehmen_decisions import record_demo_decisions

        ids = record_demo_decisions(graph)
        print(f"Recorded {len(ids)} demo decisions")

    out = Path(args.output)
    graph.save_to_file(str(out))
    print(f"Saved {out} ({graph.stats()['node_count']} nodes)")

    from sync_upload_config import sync_upload_kdm_config

    uploaded = sync_upload_kdm_config()
    print(f"Uploaded {len(uploaded)} file(s) to upload/kdm/config/")

    upload_dir = (REPO / "upload" / "kdm" / "config").resolve()
    print("\nNext steps (deploy bundle):")
    print(f"  SEMANTICA_KG_PATH={upload_dir / 'xunternehmen_kg_with_decisions.json'}")
    print(f"  SEMANTICA_BUSINESS_RULES={upload_dir / 'xunternehmen_business_rules.yaml'}")
    print(f"  SEMANTICA_MAPPING_CONFIG={upload_dir / 'xunternehmen_r2rml_db_mapping.yaml'}")
    print("  python examples/xunternehmen_ontology_analytics_demo.py --print-sql-only")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(KDM))
    raise SystemExit(main())
