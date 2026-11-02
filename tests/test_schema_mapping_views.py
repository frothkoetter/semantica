"""Mapping YAML views → MCP summary and graph materialization."""

from __future__ import annotations

from pathlib import Path

import yaml

from semantica.context import ContextGraph
from semantica.mcp_server.schema_mappings import (
    load_mapping_config,
    materialize_mapping_views_in_graph,
    summarize_mapping_config,
)


def test_summarize_mapping_config_includes_views(tmp_path, monkeypatch):
    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        yaml.dump(
            {
                "ontology_namespace": "https://example.org/defense#",
                "database": "defense",
                "preferred_tables": {"Ship": "ships"},
                "views": {
                    "vessel_proximity": "VesselProximityAssessment",
                    "lagebild": "SituationPictureEntry",
                },
                "join_hints": [{"description": "prox", "sql": "defense.vessel_proximity"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SEMANTICA_MAPPING_CONFIG", str(mapping))

    summary = summarize_mapping_config()
    assert summary["mapping_view_count"] == 2
    assert summary["mapping_views"]["vessel_proximity"] == "VesselProximityAssessment"
    assert summary["mapping_database"] == "defense"
    assert len(summary["mapping_join_hints"]) == 1
    assert summary["schema_mappings_ready"] is True


def test_materialize_mapping_views_in_graph(tmp_path):
    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        yaml.dump(
            {
                "ontology_namespace": "https://example.org/defense#",
                "views": {"vessel_proximity": "VesselProximityAssessment"},
            }
        ),
        encoding="utf-8",
    )
    cfg = load_mapping_config(str(mapping))
    graph = ContextGraph(advanced_analytics=False)
    graph.add_node(
        "https://example.org/defense#VesselProximityAssessment",
        node_type="OntologyClass",
        content="VesselProximityAssessment",
        uri="https://example.org/defense#VesselProximityAssessment",
    )

    stats = materialize_mapping_views_in_graph(graph, cfg)
    assert stats["views"] == 1

    tables = list(graph.find_nodes(node_type="DatabaseTable"))
    assert len(tables) == 1
    assert tables[0].get("table_name") == "vessel_proximity" or tables[0].get("content") == "vessel_proximity"

    stats2 = materialize_mapping_views_in_graph(graph, cfg)
    assert stats2["skipped"] == 1
    assert stats2["views"] == 0


def test_get_graph_summary_envelope_lists_database_views(tmp_path, monkeypatch):
    import semantica.mcp_server as mcp_mod

    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        yaml.dump(
            {
                "ontology_namespace": "https://example.org/defense#",
                "views": {"vessel_proximity": "VesselProximityAssessment"},
            }
        ),
        encoding="utf-8",
    )
    kg = tmp_path / "kg.json"
    kg.write_text(
        '{"nodes": [{"id": "n1", "type": "OntologyClass", "properties": {"label": "X"}}], "edges": []}',
        encoding="utf-8",
    )
    monkeypatch.setenv("SEMANTICA_MAPPING_CONFIG", str(mapping))
    monkeypatch.setenv("SEMANTICA_KG_PATH", str(kg))
    mcp_mod._graph = None
    mcp_mod._graph_loaded_from = None

    summary = mcp_mod._tool_get_graph_summary({})
    assert summary["database_views"] == ["vessel_proximity"]
    assert summary["mapping_views"]["vessel_proximity"] == "VesselProximityAssessment"
    assert "vessel_proximity" in summary["database_objects"]
