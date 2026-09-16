#!/usr/bin/env python3
"""Export a PNG overview of the airline ContextGraph including BusinessRule nodes."""

from __future__ import annotations

import argparse
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

REPO = Path(__file__).resolve().parents[1]

INCLUDE_NODE_TYPES = frozenset(
    {
        "Ontology",
        "OntologyClass",
        "ObjectProperty",
        "BusinessRule",
        "DatabaseTable",
    }
)

EDGE_TYPES = frozenset(
    {
        "appliesToClass",
        "subClassOf",
        "mapsToClass",
        "domain",
        "range",
    }
)

NODE_COLORS = {
    "Ontology": "#4C78A8",
    "OntologyClass": "#59A14F",
    "ObjectProperty": "#B07AA1",
    "BusinessRule": "#E15759",
    "DatabaseTable": "#F28E2B",
}

EDGE_COLORS = {
    "appliesToClass": "#E15759",
    "subClassOf": "#59A14F",
    "mapsToClass": "#F28E2B",
    "domain": "#B07AA1",
    "range": "#B07AA1",
}


def _node_id(node: dict) -> str:
    return str(node.get("id") or node.get("uri") or "")


def _node_type(node: dict) -> str:
    return str(node.get("type") or node.get("node_type") or "unknown")


def _node_label(node: dict) -> str:
    label = (
        node.get("label")
        or node.get("content")
        or node.get("table_name")
        or _node_id(node)
    )
    text = str(label)
    if _node_type(node) == "BusinessRule":
        kind = node.get("rule_kind") or ""
        if kind:
            text = f"{text}\n[{kind}]"
    if len(text) > 28:
        text = textwrap.shorten(text, width=28, placeholder="…")
    return text


def _edge_endpoints(edge) -> tuple[str, str, str]:
    if isinstance(edge, dict):
        return (
            str(edge.get("source_id") or edge.get("source")),
            str(edge.get("target_id") or edge.get("target")),
            str(edge.get("type") or edge.get("edge_type") or "related"),
        )
    return (
        str(edge.source_id),
        str(edge.target_id),
        str(getattr(edge, "edge_type", "related")),
    )


def build_subgraph(graph) -> nx.DiGraph:
    included = {}
    for node in graph.find_nodes():
        ntype = _node_type(node)
        if ntype in INCLUDE_NODE_TYPES:
            included[_node_id(node)] = node

    digraph = nx.DiGraph()
    for node_id, node in included.items():
        digraph.add_node(node_id, label=_node_label(node), ntype=_node_type(node))

    for edge in graph.edges:
        source, target, etype = _edge_endpoints(edge)
        if etype not in EDGE_TYPES:
            continue
        if source in included and target in included:
            digraph.add_edge(source, target, etype=etype)
    return digraph


def export_image(graph, output: Path, dpi: int = 160) -> dict:
    digraph = build_subgraph(graph)
    if not digraph.nodes:
        raise SystemExit("No nodes to visualize")

    plt.figure(figsize=(20, 14))
    ax = plt.gca()
    ax.set_facecolor("#FAFAFA")

    pos = nx.spring_layout(digraph, seed=42, k=1.8, iterations=120)

    nodes_by_type: dict[str, list[str]] = defaultdict(list)
    for node_id, data in digraph.nodes(data=True):
        nodes_by_type[data["ntype"]].append(node_id)

    for ntype, node_ids in nodes_by_type.items():
        nx.draw_networkx_nodes(
            digraph,
            pos,
            nodelist=node_ids,
            node_color=NODE_COLORS.get(ntype, "#9D9D9D"),
            node_size=900 if ntype == "BusinessRule" else 700,
            alpha=0.92,
            edgecolors="white",
            linewidths=0.8,
            ax=ax,
        )

    for etype in EDGE_TYPES:
        edge_list = [(u, v) for u, v, d in digraph.edges(data=True) if d.get("etype") == etype]
        if not edge_list:
            continue
        nx.draw_networkx_edges(
            digraph,
            pos,
            edgelist=edge_list,
            edge_color=EDGE_COLORS.get(etype, "#AAAAAA"),
            width=1.4 if etype == "appliesToClass" else 1.0,
            alpha=0.65,
            arrows=True,
            arrowsize=12,
            connectionstyle="arc3,rad=0.08",
            ax=ax,
        )

    labels = {n: d["label"] for n, d in digraph.nodes(data=True)}
    nx.draw_networkx_labels(
        digraph,
        pos,
        labels=labels,
        font_size=6,
        font_family="sans-serif",
        ax=ax,
    )

    legend_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color,
            markersize=10,
            label=ntype,
        )
        for ntype, color in NODE_COLORS.items()
        if ntype in nodes_by_type
    ]
    edge_handles = [
        plt.Line2D([0], [0], color=color, linewidth=2, label=etype)
        for etype, color in EDGE_COLORS.items()
        if any(d.get("etype") == etype for _, _, d in digraph.edges(data=True))
    ]
    ax.legend(
        handles=legend_handles + edge_handles,
        loc="upper left",
        fontsize=9,
        framealpha=0.95,
    )
    ax.set_title(
        "Airline Knowledge Graph — Ontology, Business Rules, DB Mapping",
        fontsize=16,
        weight="bold",
        pad=16,
    )
    ax.axis("off")
    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close()

    return {
        "output": str(output),
        "nodes": len(digraph.nodes),
        "edges": len(digraph.edges),
        "node_types": {k: len(v) for k, v in nodes_by_type.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--graph",
        default=str(REPO / "data" / "airline_graph.json"),
        help="Input ContextGraph JSON",
    )
    parser.add_argument(
        "--business-rules",
        default=str(REPO / "config" / "airline_business_rules.yaml"),
        help="Business rules YAML to ingest before export",
    )
    parser.add_argument(
        "--output",
        default=str(REPO / "data" / "airline_kg_with_business_rules.png"),
        help="Output PNG path",
    )
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument(
        "--save-graph",
        action="store_true",
        help="Write graph back with BusinessRule nodes",
    )
    args = parser.parse_args()

    from semantica.context import ContextGraph
    from semantica.mcp_server.business_rules import (
        ingest_business_rules_into_graph,
        load_business_rules,
    )

    graph = ContextGraph(advanced_analytics=False)
    graph.load_from_file(args.graph)

    rules_path = Path(args.business_rules)
    if rules_path.is_file():
        rules = load_business_rules(str(rules_path))
        stats = ingest_business_rules_into_graph(
            graph, rules, source_path=str(rules_path)
        )
        print("Business rules ingested:", stats)
    else:
        print(f"Warning: business rules not found: {rules_path}")

    result = export_image(graph, Path(args.output), dpi=args.dpi)
    print(result)

    if args.save_graph:
        graph.save_to_file(args.graph)
        print(f"Updated graph: {args.graph}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
