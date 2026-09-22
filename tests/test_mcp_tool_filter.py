"""Tests for SEMANTICA_MCP_TOOLSET / SEMANTICA_MCP_TOOLS filtering."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from semantica import mcp_server as mcp_mod


class TestMCPToolFilter(unittest.TestCase):
    def test_preloaded_graph_toolset_excludes_ner(self):
        with patch.dict(
            os.environ,
            {"SEMANTICA_MCP_TOOLSET": "preloaded_graph", "SEMANTICA_MCP_TOOLS": ""},
            clear=False,
        ):
            active = mcp_mod.resolve_active_tools(mcp_mod.TOOLS)
        names = {t["name"] for t in active}
        self.assertIn("get_graph_summary", names)
        self.assertIn("get_business_rules", names)
        self.assertNotIn("extract_entities", names)
        self.assertNotIn("extract_relations", names)

    def test_deprecated_airline_analytics_alias(self):
        with patch.dict(
            os.environ,
            {"SEMANTICA_MCP_TOOLSET": "airline_analytics", "SEMANTICA_MCP_TOOLS": ""},
            clear=False,
        ):
            active = mcp_mod.resolve_active_tools(mcp_mod.TOOLS)
        self.assertEqual(
            [t["name"] for t in active],
            mcp_mod.MCP_TOOLSETS["preloaded_graph"],
        )

    def test_explicit_tools_list(self):
        with patch.dict(
            os.environ,
            {
                "SEMANTICA_MCP_TOOLS": "get_graph_summary,get_business_rules",
                "SEMANTICA_MCP_TOOLSET": "",
            },
            clear=False,
        ):
            active = mcp_mod.resolve_active_tools(mcp_mod.TOOLS)
        self.assertEqual([t["name"] for t in active], ["get_graph_summary", "get_business_rules"])

    def test_extract_entities_fast_fail_when_toolset_set(self):
        with patch.dict(os.environ, {"SEMANTICA_MCP_TOOLSET": "preloaded_graph"}, clear=False):
            out = mcp_mod._tool_extract_entities({"text": "Flight delay at JFK"})
        self.assertIn("error", out)
        self.assertIn("disabled", out["error"])

    def test_tools_list_uses_active_tools(self):
        with patch.object(mcp_mod, "ACTIVE_TOOLS", mcp_mod.TOOLS[:2]):
            resp = mcp_mod._handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            )
        self.assertIsNotNone(resp)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 2)


if __name__ == "__main__":
    unittest.main()
