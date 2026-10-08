#!/usr/bin/env python3
"""Merge Decision Store JSONL records into airline ContextGraph JSON.

Loads data/airline_graph.json (unchanged), ingests decisions from one or more
decisions.jsonl files as graph nodes (type ``decision``), and writes a new file
for Explorer / MCP — default: data/airline_graph_with_decisions.json.

Usage:
  .venv/bin/python scripts/merge_airline_decisions.py
  .venv/bin/python scripts/merge_airline_decisions.py \\
      --decisions ~/Downloads/decisions.jsonl \\
      --decisions ~/Downloads/decisions\\ \\(1\\).jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = REPO / "data" / "airline_graph.json"
DEFAULT_OUT = REPO / "data" / "airline_graph_with_decisions.json"
DEFAULT_DECISIONS = [
    Path.home() / "Downloads" / "decisions.jsonl",
    Path.home() / "Downloads" / "decisions (1).jsonl",
]

_STORE_FIELDS = frozenset(
    {
        "decision_id",
        "category",
        "scenario",
        "reasoning",
        "outcome",
        "confidence",
        "decision_maker",
        "recorded_at",
        "entities",
    }
)


def _parse_recorded_at(recorded_at: str | None) -> float:
    if not recorded_at:
        return datetime.now(timezone.utc).timestamp()
    text = str(recorded_at).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def load_jsonl_records(paths: list[Path]) -> list[dict[str, Any]]:
    """Load and dedupe decision records by decision_id (last file wins)."""
    by_id: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Warning: skip {path}:{line_no} — {exc}", file=sys.stderr)
                    continue
                decision_id = str(record.get("decision_id") or "").strip()
                if not decision_id:
                    print(f"Warning: skip {path}:{line_no} — missing decision_id", file=sys.stderr)
                    continue
                by_id[decision_id] = record
    return list(by_id.values())


def _entities_from_record(record: dict[str, Any], *, max_entities: int = 15) -> list[str]:
    explicit = record.get("entities")
    if isinstance(explicit, list) and explicit:
        return [str(e).strip() for e in explicit if str(e).strip()][:max_entities]

    metrics = record.get("result_metrics")
    if isinstance(metrics, dict) and metrics:
        return [str(k).strip() for k in metrics.keys() if str(k).strip()][:max_entities]
    return []


def jsonl_record_to_graph_decision(record: dict[str, Any]) -> dict[str, Any]:
    """Map Decision Store JSONL line to ContextGraph decision dict."""
    metadata = {
        k: v for k, v in record.items() if k not in _STORE_FIELDS
    }
    metadata["decision_store_id"] = record.get("decision_id")
    metadata["recorded_at"] = record.get("recorded_at")

    return {
        "id": record["decision_id"],
        "category": record.get("category") or "uncategorized",
        "scenario": record.get("scenario") or "",
        "reasoning": record.get("reasoning") or "",
        "outcome": record.get("outcome") or "",
        "confidence": float(record.get("confidence") or 0.0),
        "entities": _entities_from_record(record),
        "decision_maker": record.get("decision_maker") or "mcp_client",
        "timestamp": _parse_recorded_at(record.get("recorded_at")),
        "recorded_at": record.get("recorded_at"),
        "metadata": metadata,
    }


def rebuild_decision_index(graph: Any) -> int:
    """Rebuild in-memory _decisions from persisted decision nodes."""
    graph._decisions = {}
    graph._decision_index = defaultdict(set)
    graph._entity_index = defaultdict(set)
    graph._temporal_index = []

    count = 0
    for node in graph.find_nodes(node_type="decision"):
        if isinstance(node, dict):
            props = dict(node.get("metadata") or {})
            props.update({k: v for k, v in node.items() if k not in {"id", "type", "metadata"}})
            decision_id = str(node.get("id", ""))
            content = node.get("content") or props.get("scenario") or ""
        else:
            props = dict(getattr(node, "properties", None) or {})
            if hasattr(node, "metadata") and node.metadata:
                props.update(node.metadata)
            decision_id = str(getattr(node, "node_id", ""))
            content = getattr(node, "content", "") or props.get("scenario", "")

        if not decision_id:
            continue

        entities: list[str] = []
        for edge in graph.edges:
            src = edge.source_id if hasattr(edge, "source_id") else edge.get("source_id")
            tgt = edge.target_id if hasattr(edge, "target_id") else edge.get("target_id")
            etype = edge.edge_type if hasattr(edge, "edge_type") else edge.get("type")
            if src == decision_id and etype == "involves":
                entities.append(str(tgt))

        ts = props.get("timestamp") or 0.0
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            ts = 0.0

        record = {
            "id": decision_id,
            "category": props.get("category", ""),
            "scenario": props.get("scenario") or content,
            "reasoning": props.get("reasoning", ""),
            "outcome": props.get("outcome", ""),
            "confidence": float(props.get("confidence", 0.0) or 0.0),
            "entities": entities,
            "decision_maker": props.get("decision_maker"),
            "timestamp": ts,
            "recorded_at": props.get("recorded_at"),
            "metadata": {
                k: v
                for k, v in props.items()
                if k
                not in {
                    "category",
                    "scenario",
                    "reasoning",
                    "outcome",
                    "confidence",
                    "decision_maker",
                    "timestamp",
                    "recorded_at",
                    "content",
                }
            },
        }
        graph._decisions[decision_id] = record
        if record["category"]:
            graph._decision_index[record["category"]].add(decision_id)
        for ent in entities:
            graph._entity_index[ent].add(decision_id)
        graph._temporal_index.append((decision_id, ts))
        count += 1

    graph._temporal_index.sort(key=lambda x: x[1], reverse=True)
    return count


def merge_decisions_into_graph(
    graph: Any,
    records: list[dict[str, Any]],
    *,
    skip_existing: bool = True,
) -> dict[str, int]:
    added = 0
    skipped = 0
    for record in records:
        decision_id = str(record.get("decision_id", ""))
        if skip_existing and graph.find_node(decision_id):
            skipped += 1
            continue
        decision = jsonl_record_to_graph_decision(record)
        graph._add_decision_to_graph(decision)
        if not hasattr(graph, "_decisions"):
            graph._decisions = {}
            graph._decision_index = defaultdict(set)
            graph._entity_index = defaultdict(set)
            graph._temporal_index = []
        graph._decisions[decision_id] = decision
        graph._decision_index[decision["category"]].add(decision_id)
        for entity in decision.get("entities") or []:
            graph._entity_index[entity].add(decision_id)
        graph._temporal_index.append((decision_id, decision["timestamp"]))
        added += 1
    if hasattr(graph, "_temporal_index"):
        graph._temporal_index.sort(key=lambda x: x[1], reverse=True)
    return {"added": added, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--graph",
        default=str(DEFAULT_GRAPH),
        help="Source ContextGraph JSON (not modified)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUT),
        help="Merged output ContextGraph JSON",
    )
    parser.add_argument(
        "--decisions",
        action="append",
        default=[],
        help="Decision Store JSONL file (repeatable; defaults to ~/Downloads/decisions*.jsonl)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-add decisions even if node id already exists in graph",
    )
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.is_file():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return 1

    decision_paths = [Path(p) for p in args.decisions] if args.decisions else DEFAULT_DECISIONS
    existing_paths = [p for p in decision_paths if p.is_file()]
    if not existing_paths:
        print(
            "No decisions JSONL files found. Pass --decisions PATH "
            f"(tried: {', '.join(str(p) for p in decision_paths)})",
            file=sys.stderr,
        )
        return 1

    records = load_jsonl_records(existing_paths)
    if not records:
        print("No decision records in JSONL input.", file=sys.stderr)
        return 1

    from semantica.context import ContextGraph

    graph = ContextGraph(advanced_analytics=False)
    graph.load_from_file(str(graph_path))
    base_nodes = graph.stats()["node_count"]
    base_edges = graph.stats()["edge_count"]
    print(f"Loaded {graph_path} ({base_nodes} nodes, {base_edges} edges)")

    stats = merge_decisions_into_graph(
        graph,
        records,
        skip_existing=not args.force,
    )
    rebuild_decision_index(graph)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph.save_to_file(str(out_path))

    final = graph.stats()
    decision_nodes = len(graph.find_nodes(node_type="decision"))
    print(
        f"Merged {stats['added']} decision(s) ({stats['skipped']} skipped) "
        f"from {len(existing_paths)} file(s)"
    )
    print(
        f"Saved {out_path} — {final['node_count']} nodes, "
        f"{final['edge_count']} edges, {decision_nodes} decision nodes"
    )
    print("\nExplorer:")
    print(f"  semantica-explorer --graph {out_path}")
    print("\nDecision IDs:")
    for rec in records:
        print(f"  {rec.get('decision_id')}  [{rec.get('category')}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
