#!/usr/bin/env python3
"""Build XUnternehmen knowledge graph and HTML visualizations from kdm/ontology.owl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KDM = REPO / "kdm"
OWL = KDM / "ontology.owl"
VIZ_DIR = KDM / "viz"
KG_JSON = KDM / "xunternehmen_kg.json"


def main() -> int:
    if not OWL.is_file():
        print(f"Ontology not found: {OWL}", file=sys.stderr)
        return 1

    from semantica.context import ContextGraph
    from semantica.ingest import OntologyIngestor
    from semantica.mcp_server.ontology_tools import handle_import_ontology
    from semantica.visualization.ontology_visualizer import OntologyVisualizer

    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    ontology = OntologyIngestor().ingest_ontology(str(OWL)).data
    print(
        json.dumps(
            {
                "classes": len(ontology.get("classes", [])),
                "properties": len(ontology.get("properties", [])),
            },
            indent=2,
        )
    )

    graph = ContextGraph(advanced_analytics=True)
    import_result = handle_import_ontology(
        {
            "file_path": str(OWL),
            "namespace_filter": "https://w3id.org/kdm/",
            "include_properties": True,
        },
        lambda: graph,
    )
    if "error" in import_result:
        print(json.dumps(import_result, indent=2), file=sys.stderr)
        return 1

    graph.save_to_file(str(KG_JSON))
    print(f"Saved {KG_JSON} ({graph.stats()['node_count']} nodes)")

    viz = OntologyVisualizer(color_scheme="default", layout="force")
    for stem, method in (
        ("xunternehmen_hierarchy", "visualize_hierarchy"),
        ("xunternehmen_properties", "visualize_properties"),
        ("xunternehmen_structure", "visualize_structure"),
    ):
        out = VIZ_DIR / f"{stem}.html"
        getattr(viz, method)(ontology, output="html", file_path=str(out))
        print(f"Created {out}")

    print(f"Open {VIZ_DIR / 'index.html'} in a browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
