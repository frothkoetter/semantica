"""Ensure core imports do not require torch (lazy ML stack)."""

from __future__ import annotations

import importlib
import sys
import time


def _torch_was_loaded() -> bool:
    return "torch" in sys.modules


def test_context_graph_import_does_not_load_torch():
    """Importing ContextGraph must not pull in torch when ST is not used."""
    # Drop torch if a prior test loaded it
    for mod in list(sys.modules):
        if mod == "torch" or mod.startswith("torch."):
            del sys.modules[mod]

    assert not _torch_was_loaded()

    t0 = time.perf_counter()
    from semantica.context import ContextGraph  # noqa: F401

    elapsed = time.perf_counter() - t0

    assert not _torch_was_loaded(), "ContextGraph import loaded torch"
    assert elapsed < 5.0, f"ContextGraph import took {elapsed:.2f}s"


def test_embeddings_module_import_does_not_load_torch():
    for mod in list(sys.modules):
        if mod == "torch" or mod.startswith("torch."):
            del sys.modules[mod]

    importlib.import_module("semantica.embeddings")

    assert not _torch_was_loaded(), "semantica.embeddings import loaded torch"


def test_mcp_get_graph_summary_fast_path_without_torch(monkeypatch):
    """MCP summary fast path must work without torch."""
    from pathlib import Path

    import semantica.mcp_server as mcp_mod
    from semantica.mcp_server import _tool_get_graph_summary

    path = Path(__file__).resolve().parents[1] / "kdm" / "xunternehmen_kg_with_decisions.json"
    if not path.is_file():
        return

    for mod in list(sys.modules):
        if mod == "torch" or mod.startswith("torch."):
            del sys.modules[mod]

    monkeypatch.setenv("SEMANTICA_KG_PATH", str(path))
    mcp_mod._graph = None
    mcp_mod._graph_loaded_from = None

    summary = _tool_get_graph_summary({})

    assert summary["source"] == "kg_file_snapshot"
    assert not _torch_was_loaded(), "get_graph_summary fast path loaded torch"
