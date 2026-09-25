"""Fast KG snapshot path for MCP tools (no ContextGraph import)."""

from __future__ import annotations

import time
from pathlib import Path

import semantica.mcp_server as mcp_mod
from semantica.mcp_server import _tool_get_business_rules, _tool_get_graph_summary
from semantica.mcp_server.kg_snapshot import snapshot_kg_file


def test_snapshot_kg_file_xunternehmen():
    path = Path(__file__).resolve().parents[1] / "kdm" / "xunternehmen_kg_with_decisions.json"
    if not path.is_file():
        return
    stats = snapshot_kg_file(str(path))
    assert stats["node_count"] == 198
    assert stats["ontology_class_count"] == 36
    assert stats["business_rule_count"] == 26
    assert stats["decision_count"] == 8
    assert stats["graph_ready"] is True
    assert stats["source"] == "kg_file_snapshot"


def test_get_graph_summary_fast_path(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "kdm" / "xunternehmen_kg_with_decisions.json"
    rules = Path(__file__).resolve().parents[1] / "config" / "xunternehmen_business_rules.yaml"
    if not path.is_file() or not rules.is_file():
        return

    monkeypatch.setenv("SEMANTICA_KG_PATH", str(path))
    monkeypatch.setenv("SEMANTICA_BUSINESS_RULES", str(rules))
    mcp_mod._graph = None
    mcp_mod._graph_loaded_from = None

    t0 = time.perf_counter()
    summary = _tool_get_graph_summary({})
    elapsed = time.perf_counter() - t0

    assert summary["graph_ready"] is True
    assert summary["node_count"] == 198
    assert summary["source"] == "kg_file_snapshot"
    assert elapsed < 2.0, f"fast summary took {elapsed:.2f}s"


def test_get_business_rules_fast_path(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "kdm" / "xunternehmen_kg_with_decisions.json"
    rules = Path(__file__).resolve().parents[1] / "config" / "xunternehmen_business_rules.yaml"
    if not path.is_file() or not rules.is_file():
        return

    monkeypatch.setenv("SEMANTICA_KG_PATH", str(path))
    monkeypatch.setenv("SEMANTICA_BUSINESS_RULES", str(rules))
    mcp_mod._graph = None
    mcp_mod._graph_loaded_from = None

    t0 = time.perf_counter()
    result = _tool_get_business_rules({})
    elapsed = time.perf_counter() - t0

    assert result["rules_loaded"] is True
    assert result["kg_snapshot"] is True
    assert result["graph_business_rule_count"] == 26
    assert elapsed < 2.0, f"fast business rules took {elapsed:.2f}s"
