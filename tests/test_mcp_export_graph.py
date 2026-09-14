"""Tests for semantica.mcp_server export_graph tool."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from semantica.context import ContextGraph
from semantica.mcp_server import _tool_export_graph, _tool_get_graph_summary
import semantica.mcp_server as mcp_mod


@pytest.fixture
def airline_graph_path() -> Path:
    path = Path(__file__).resolve().parents[1] / "data" / "airline_graph.json"
    if not path.exists():
        pytest.skip("airline_graph.json not built")
    return path


@pytest.fixture
def loaded_airline_graph(airline_graph_path, monkeypatch):
    monkeypatch.setenv("SEMANTICA_KG_PATH", str(airline_graph_path))
    mcp_mod._graph = None
    graph = ContextGraph(advanced_analytics=False)
    graph.load_from_file(str(airline_graph_path))
    mcp_mod._graph = graph
    yield graph
    mcp_mod._graph = None


def test_export_graph_json_ontology_subset(loaded_airline_graph):
    result = _tool_export_graph({"format": "json", "subset": "ontology"})
    assert "error" not in result
    assert result["format"] == "json"
    assert result["subset"] == "ontology"
    assert result["meta"]["node_count"] > 0
    assert result["meta"]["node_count"] < 200
    types = {n.get("type") for n in result["data"]["nodes"]}
    assert "OntologyClass" in types
    assert "DatabaseTable" in types


def test_export_graph_json_ld_ontology_subset(loaded_airline_graph):
    result = _tool_export_graph({"format": "json-ld", "subset": "ontology"})
    assert "error" not in result
    assert result["format"] == "jsonld"
    assert isinstance(result["data"], str)
    assert len(result["data"]) > 100


def test_export_graph_default_is_lightweight_json(loaded_airline_graph):
    result = _tool_export_graph({})
    assert result["format"] == "json"
    assert result["subset"] == "ontology"
    payload_size = len(json.dumps(result["data"], default=str))
    assert payload_size < 200_000


def test_get_graph_summary_still_works(loaded_airline_graph):
    summary = _tool_get_graph_summary({})
    assert summary["graph_ready"] is True
    assert summary["ontology_class_count"] > 0
