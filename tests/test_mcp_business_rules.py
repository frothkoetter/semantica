"""Tests for business rules MCP integration."""

from __future__ import annotations

from pathlib import Path

import pytest

import semantica.mcp_server as mcp_mod
from semantica.context import ContextGraph
from semantica.mcp_server import _tool_get_business_rules, _tool_get_graph_summary
from semantica.mcp_server.business_rules import (
    ingest_business_rules_into_graph,
    load_business_rules,
)


@pytest.fixture
def rules_path() -> Path:
    path = Path(__file__).resolve().parents[1] / "config" / "airline_business_rules.yaml"
    if not path.exists():
        pytest.skip("airline_business_rules.yaml missing")
    return path


@pytest.fixture
def airline_graph_path() -> Path:
    path = Path(__file__).resolve().parents[1] / "data" / "airline_graph.json"
    if not path.exists():
        pytest.skip("airline_graph.json not built")
    return path


@pytest.fixture
def mcp_session(airline_graph_path, rules_path, monkeypatch):
    monkeypatch.setenv("SEMANTICA_KG_PATH", str(airline_graph_path))
    monkeypatch.setenv("SEMANTICA_BUSINESS_RULES", str(rules_path))
    mcp_mod._graph = None
    graph = ContextGraph(advanced_analytics=False)
    graph.load_from_file(str(airline_graph_path))
    mcp_mod._graph = graph
    yield
    mcp_mod._graph = None


def test_load_business_rules(rules_path):
    rules = load_business_rules(str(rules_path))
    assert rules["thresholds"]["on_time_max_delay"] == 15
    assert "MorningPeak" in rules["time_windows"]


def test_ingest_business_rules_into_graph(rules_path):
    graph = ContextGraph(advanced_analytics=False)
    rules = load_business_rules(str(rules_path))
    stats = ingest_business_rules_into_graph(graph, rules, source_path=str(rules_path))
    assert stats["business_rule_nodes"] > 0
    assert graph.nodes.get("business_rule:threshold:on_time_max_delay")


def test_get_business_rules_tool(mcp_session, rules_path):
    result = _tool_get_business_rules({})
    assert result["rules_loaded"] is True
    assert result["rules_path_exists"] is True
    assert result["rules"]["thresholds"]["on_time_max_delay"] == 15
    assert "flight_status_rules" in result["classification_rules"]
    assert "sql" not in result
    assert result["graph_business_rule_count"] > 0
    assert result["reasoning_rules"]


def test_get_graph_summary_includes_business_rules(mcp_session):
    summary = _tool_get_graph_summary({})
    assert summary["graph_ready"] is True
    assert summary["business_rules_path_exists"] is True
    assert summary["business_rules_summary"]["thresholds"]["on_time_max_delay"] == 15
