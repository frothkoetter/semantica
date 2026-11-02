#!/usr/bin/env python3
"""
Add DatabaseTable nodes for mapping YAML ``views`` to a persisted ContextGraph JSON.

Example (Triton defense):
  export SEMANTICA_MAPPING_CONFIG=/path/to/defense_r2rml_db_mapping.yaml
  python scripts/sync_kg_mapping_views.py \\
    --kg /path/to/triton_defense_graph.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync mapping YAML views into KG JSON")
    parser.add_argument("--kg", required=True, help="Path to graph JSON (updated in place)")
    parser.add_argument(
        "--mapping",
        help="Mapping YAML (default: SEMANTICA_MAPPING_CONFIG or --kg sibling)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print stats only")
    args = parser.parse_args()

    kg_path = Path(args.kg).resolve()
    if not kg_path.is_file():
        print(f"KG not found: {kg_path}", file=sys.stderr)
        return 1

    from semantica.context import ContextGraph
    from semantica.mcp_server.schema_mappings import (
        load_mapping_config,
        materialize_mapping_views_in_graph,
        resolve_mapping_config_path,
    )

    mapping_path = args.mapping or resolve_mapping_config_path()
    if not mapping_path:
        sibling = kg_path.parent.parent / "defense_r2rml_db_mapping.yaml"
        if sibling.is_file():
            mapping_path = str(sibling)
    if not mapping_path:
        print("No mapping YAML — set SEMANTICA_MAPPING_CONFIG or pass --mapping", file=sys.stderr)
        return 1

    cfg = load_mapping_config(mapping_path)
    if not cfg.get("views"):
        print(f"No views section in {mapping_path}")
        return 0

    graph = ContextGraph(advanced_analytics=False)
    graph.load_from_file(str(kg_path))
    stats = materialize_mapping_views_in_graph(graph, cfg)
    print(f"views added={stats['views']} skipped={stats['skipped']} mapping={mapping_path}")

    if args.dry_run:
        return 0

    graph.save_to_file(str(kg_path))
    print(f"Wrote {kg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
