#!/usr/bin/env python3
"""Generate interactive HTML visualizations of data/airline_graph.json."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import plotly.graph_objects as go

from semantica.context import ContextGraph

REPO = Path(__file__).resolve().parents[1]
GRAPH_PATH = REPO / "data" / "airline_graph.json"
OUT_OVERVIEW = REPO / "data" / "airline_graph_overview.html"
OUT_FULL = REPO / "data" / "airline_graph_full.html"
OUT_META = REPO / "data" / "airline_graph_viz_meta.json"

MATERIALIZED_TABLES = {"flights_orc", "airlines", "airports", "planes"}

TYPE_COLORS = {
    "Ontology": "#6366f1",
    "OntologyClass": "#2563eb",
    "ObjectProperty": "#7c3aed",
    "DatatypeProperty": "#a855f7",
    "DatabaseTable": "#059669",
    "DatabaseColumn": "#34d399",
    "entity": "#94a3b8",
}

EDGE_COLORS = {
    "definedIn": "#cbd5e1",
    "subClassOf": "#93c5fd",
    "domain": "#c4b5fd",
    "range": "#c4b5fd",
    "mapsToClass": "#34d399",
    "hasColumn": "#86efac",
    "mapsToProperty": "#6ee7b7",
}


def _normalize_uri(uri: str) -> str:
    """Canonicalize fragment URIs (#/Flight → #Flight)."""
    if not uri or "#" not in uri:
        return uri
    base, frag = uri.split("#", 1)
    return f"{base}#{frag.lstrip('/')}"


def _local_name(uri: str) -> str:
    if not uri:
        return ""
    if "#" in uri:
        return uri.split("#", 1)[-1].lstrip("/")
    if "/" in uri:
        return uri.rsplit("/", 1)[-1]
    return uri


def _node_label(node: Dict[str, Any]) -> str:
    meta = node.get("metadata") or {}
    ntype = node.get("type") or "entity"
    content = node.get("content") or _local_name(node.get("id", ""))
    if ntype == "DatabaseColumn":
        table = meta.get("table_name", "")
        col = meta.get("column_name") or content
        return f"{table}.{col}" if table else col
    if ntype == "DatabaseTable":
        return meta.get("table_name") or content
    if ntype in ("OntologyClass", "ObjectProperty", "DatatypeProperty"):
        return content or _local_name(node.get("id", ""))
    return content or _local_name(node.get("id", ""))


def _load_graph(path: Path) -> ContextGraph:
    graph = ContextGraph()
    graph.load_from_file(str(path))
    return graph


def _build_index(graph: ContextGraph) -> Tuple[List[Dict], List[Dict]]:
    nodes = list(graph.find_nodes())
    for node in nodes:
        nid = node.get("id")
        if nid:
            node["id"] = _normalize_uri(nid)
    edges = [
        {
            "source": _normalize_uri(e["source"]),
            "target": _normalize_uri(e["target"]),
            "type": e.get("type"),
        }
        for e in graph.find_edges()
    ]
    return nodes, edges


def _filter_overview(nodes: List[Dict], edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Architecture view: ontology + materialized tables + object properties only."""
    keep_ids: Set[str] = set()
    for node in nodes:
        ntype = node.get("type") or "entity"
        nid = node.get("id", "")
        if ntype in ("Ontology", "OntologyClass", "ObjectProperty"):
            keep_ids.add(nid)
        elif ntype == "DatabaseTable":
            label = _node_label(node)
            if label in MATERIALIZED_TABLES:
                keep_ids.add(nid)

    kept_edges = []
    for edge in edges:
        if edge["type"] not in (
            "definedIn",
            "domain",
            "range",
            "mapsToClass",
        ):
            continue
        if edge["source"] in keep_ids and edge["target"] in keep_ids:
            kept_edges.append(edge)

    kept_nodes = [n for n in nodes if n.get("id") in keep_ids]
    return kept_nodes, kept_edges


def _layer_positions(nodes: List[Dict]) -> Dict[str, Tuple[float, float]]:
    """Place nodes in semantic layers for readability."""
    layers: Dict[str, List[Dict]] = defaultdict(list)
    for node in nodes:
        ntype = node.get("type") or "entity"
        if ntype == "Ontology":
            layer = "ontology"
        elif ntype == "OntologyClass":
            layer = "class"
        elif ntype == "ObjectProperty":
            layer = "object_property"
        elif ntype == "DatabaseTable":
            layer = "table"
        elif ntype == "DatatypeProperty":
            layer = "datatype_property"
        elif ntype == "DatabaseColumn":
            layer = "column"
        else:
            layer = "other"
        layers[layer].append(node)

    order = [
        "ontology",
        "class",
        "object_property",
        "datatype_property",
        "table",
        "column",
        "other",
    ]
    positions: Dict[str, Tuple[float, float]] = {}
    y_gap = 1.4
    for yi, layer in enumerate(order):
        items = sorted(layers.get(layer, []), key=lambda n: _node_label(n))
        if not items:
            continue
        width = max(len(items) - 1, 1)
        for xi, node in enumerate(items):
            x = (xi - width / 2) * 2.2
            y = -yi * y_gap
            positions[node["id"]] = (x, y)
    return positions


def _plot_network(
    nodes: List[Dict],
    edges: List[Dict],
    title: str,
    out_path: Path,
    show_legend: bool = True,
) -> Dict[str, Any]:
    positions = _layer_positions(nodes)
    node_ids = {n["id"] for n in nodes}

    # Edge traces grouped by type for legend
    edge_traces: List[go.Scatter] = []
    for etype, color in EDGE_COLORS.items():
        xs, ys = [], []
        for edge in edges:
            if edge.get("type") != etype:
                continue
            s, t = edge["source"], edge["target"]
            if s not in positions or t not in positions:
                continue
            x0, y0 = positions[s]
            x1, y1 = positions[t]
            xs.extend([x0, x1, None])
            ys.extend([y0, y1, None])
        if xs:
            edge_traces.append(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line=dict(width=1.5, color=color),
                    hoverinfo="none",
                    name=etype,
                    showlegend=show_legend,
                )
            )

    # Node traces grouped by type
    node_traces: List[go.Scatter] = []
    type_counts = Counter(n.get("type") or "entity" for n in nodes)
    for ntype, count in sorted(type_counts.items()):
        subset = [n for n in nodes if (n.get("type") or "entity") == ntype]
        xs = [positions[n["id"]][0] for n in subset]
        ys = [positions[n["id"]][1] for n in subset]
        labels = [_node_label(n) for n in subset]
        hover = [
            f"<b>{_node_label(n)}</b><br>type: {ntype}<br>id: {n.get('id')}"
            for n in subset
        ]
        size = 22 if ntype in ("OntologyClass", "DatabaseTable") else 14
        if ntype == "Ontology":
            size = 26
        node_traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=labels,
                textposition="top center",
                textfont=dict(size=10),
                marker=dict(
                    size=size,
                    color=TYPE_COLORS.get(ntype, "#64748b"),
                    line=dict(width=1, color="#1e293b"),
                ),
                hovertext=hover,
                hoverinfo="text",
                name=f"{ntype} ({count})",
                showlegend=show_legend,
            )
        )

    fig = go.Figure(data=edge_traces + node_traces)
    fig.update_layout(
        title=dict(text=title, x=0.5),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=20, r=20, t=80, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        height=max(640, 120 + len(type_counts) * 40),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "node_types": dict(type_counts),
        "edge_types": dict(Counter(e.get("type") for e in edges)),
        "output": str(out_path),
    }


def _column_summary(nodes: List[Dict]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = defaultdict(int)
    for node in nodes:
        if (node.get("type") or "") != "DatabaseColumn":
            continue
        meta = node.get("metadata") or {}
        table = meta.get("table_name") or "?"
        counts[table] += 1
    return [
        {"table": table, "mapped_columns": count}
        for table, count in sorted(counts.items())
    ]


def main() -> int:
    graph = _load_graph(GRAPH_PATH)
    nodes, edges = _build_index(graph)

    overview_nodes, overview_edges = _filter_overview(nodes, edges)
    overview_meta = _plot_network(
        overview_nodes,
        overview_edges,
        "Airline Semantica Graph — Architecture (ontology + materialized tables)",
        OUT_OVERVIEW,
    )

    full_meta = _plot_network(
        nodes,
        edges,
        "Airline Semantica Graph — Full (192 nodes, incl. column mappings)",
        OUT_FULL,
        show_legend=True,
    )

    stats = graph.stats()
    meta = {
        "source": str(GRAPH_PATH),
        "graph_stats": stats,
        "column_mapping_by_table": _column_summary(nodes),
        "materialized_tables": sorted(MATERIALIZED_TABLES),
        "overview": overview_meta,
        "full": full_meta,
    }
    OUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
