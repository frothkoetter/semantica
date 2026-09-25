"""
Fast knowledge-graph file stats without importing ContextGraph (avoids torch/transformers).

Used by get_graph_summary and get_business_rules in Agent Studio where the first
ContextGraph import can take many seconds (or minutes when uvx installs deps).
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional


def _local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _node_label(node: Dict[str, Any]) -> str:
    props = node.get("properties") or {}
    if not isinstance(props, dict):
        props = {}
    uri = props.get("uri") or node.get("id") or ""
    return (
        props.get("label")
        or props.get("content")
        or props.get("table_name")
        or _local_name(str(uri))
    )


def snapshot_kg_file(path: str) -> Dict[str, Any]:
    """
    Parse a persisted Semantica graph JSON file and return summary counts.

    Does not load ContextGraph or any ML stack.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    nodes: List[Dict[str, Any]] = list(data.get("nodes") or [])
    type_counts = Counter(str(n.get("type") or "entity") for n in nodes)

    ontology_nodes = [n for n in nodes if n.get("type") == "OntologyClass"]
    db_table_nodes = [n for n in nodes if n.get("type") == "DatabaseTable"]

    return {
        "node_count": len(nodes),
        "edge_count": len(data.get("edges") or []),
        "decision_count": type_counts.get("decision", 0),
        "ontology_class_count": type_counts.get("OntologyClass", 0),
        "database_table_count": type_counts.get("DatabaseTable", 0),
        "database_column_count": type_counts.get("DatabaseColumn", 0),
        "business_rule_count": type_counts.get("BusinessRule", 0),
        "ontology_classes": [_node_label(n) for n in ontology_nodes[:50]],
        "database_tables": [_node_label(n) for n in db_table_nodes[:50]],
        "graph_ready": len(nodes) > 0,
        "source": "kg_file_snapshot",
    }


def fast_kg_stats() -> Optional[Dict[str, Any]]:
    """Return snapshot stats when SEMANTICA_KG_PATH points to a readable file."""
    kg_path = (os.environ.get("SEMANTICA_KG_PATH") or "").strip()
    if not kg_path or not os.path.exists(kg_path):
        return None
    try:
        return snapshot_kg_file(kg_path)
    except (OSError, json.JSONDecodeError, TypeError):
        return None
