"""Tests for JSONL Decision Store."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from semantica.decision_store.fingerprint import (
    compute_query_fingerprint,
    hash_sql,
    normalize_params,
)
from semantica.decision_store.store import DecisionStore
from semantica.mcp_server.decision_store_tools import (
    handle_compare_with_history,
    handle_record_decision,
)


class TestFingerprint(unittest.TestCase):
    def test_sql_hash_stable(self):
        a = hash_sql("SELECT  id\nFROM flights")
        b = hash_sql("select id from flights")
        self.assertEqual(a, b)

    def test_fingerprint_stable(self):
        fp1 = compute_query_fingerprint(
            query_intent="top_airports",
            query_params={"year": 2005, "top_k": 5},
            sql_hash="sha256:abc",
            rules_hash="sha256:def",
        )
        fp2 = compute_query_fingerprint(
            query_intent="top_airports",
            query_params={"top_k": 5, "year": 2005},
            sql_hash="sha256:abc",
            rules_hash="sha256:def",
        )
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("fp:sha256:"))

    def test_normalize_params_skips_session(self):
        out = normalize_params({"year": 2005, "session_id": "x"})
        self.assertEqual(out, {"year": 2005})


class TestDecisionStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.store = DecisionStore(self._tmpdir, index_enabled=True)

    def tearDown(self):
        self.store.close()

    def _base_record(self, **overrides):
        data = {
            "category": "airline_analytics",
            "scenario": "Top airports 2005",
            "reasoning": "Grouped by origin",
            "outcome": "ATL, ORD",
            "confidence": 0.9,
            "query_intent": "top_airports_by_year",
            "query_params": {"year": 2005, "top_k": 5},
            "sql_text": "SELECT origin, count(*) FROM flights GROUP BY origin",
            "result_metrics": {"ATL": 100, "ORD": 90},
        }
        data.update(overrides)
        return data

    def test_record_appends_jsonl(self):
        result = self.store.record(**self._base_record())
        self.assertIn("decision_id", result)
        self.assertIn("query_fingerprint", result)
        path = os.path.join(self._tmpdir, "decisions.jsonl")
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            line = json.loads(fh.readline())
        self.assertEqual(line["decision_id"], result["decision_id"])
        self.assertEqual(line["result_metrics"]["ATL"], 100)

    def test_compare_with_history_fingerprint_match(self):
        r1 = self.store.record(**self._base_record(result_metrics={"ATL": 100, "ORD": 90}))
        r2 = self.store.record(**self._base_record(result_metrics={"ATL": 110, "ORD": 88}))
        cmp = self.store.compare_with_history(
            current_decision_id=r2["decision_id"],
            match_mode="fingerprint",
        )
        self.assertEqual(len(cmp["matches"]), 1)
        self.assertEqual(cmp["matches"][0]["decision_id"], r1["decision_id"])
        self.assertEqual(cmp["matches"][0]["delta"]["ATL"]["absolute"], 10)
        self.assertIn("summary", cmp)

    def test_find_precedents(self):
        self.store.record(**self._base_record(scenario="Midday departures top airports"))
        self.store.record(**self._base_record(scenario="Completely unrelated loan approval"))
        precedents = self.store.find_precedents("midday departures analysis", max_results=2)
        self.assertGreaterEqual(len(precedents), 1)
        self.assertIn("similarity_score", precedents[0])

    def test_causal_chain_downstream(self):
        p = self.store.record(**self._base_record(scenario="parent"))
        c = self.store.record(
            **self._base_record(
                scenario="child",
                causal_parent_ids=[p["decision_id"]],
            )
        )
        chain = self.store.get_causal_chain(p["decision_id"], direction="downstream")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["decision_id"], c["decision_id"])

    def test_reindex(self):
        self.store.record(**self._base_record())
        os.remove(os.path.join(self._tmpdir, "index.sqlite"))
        self.store._index._conn = None
        count = self.store.reindex()
        self.assertEqual(count, 1)

    def test_index_none_scan_fallback(self):
        store = DecisionStore(self._tmpdir, index_enabled=False)
        store.record(**self._base_record(result_metrics={"ATL": 50}))
        store.record(**self._base_record(result_metrics={"ATL": 60}))
        rows = store.query(limit=10)
        self.assertEqual(len(rows), 2)
        store.close()


class TestMCPHandlers(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        os.environ["SEMANTICA_DECISION_STORE"] = self._tmpdir
        # Reset module singleton
        import semantica.mcp_server.decision_store_tools as dst
        dst._store = None

    def tearDown(self):
        import semantica.mcp_server.decision_store_tools as dst
        if dst._store is not None:
            dst._store.close()
        dst._store = None
        os.environ.pop("SEMANTICA_DECISION_STORE", None)

    def test_handle_record_and_compare(self):
        rec = handle_record_decision({
            "category": "test",
            "scenario": "demo",
            "reasoning": "because",
            "outcome": "ok",
            "confidence": 0.8,
            "query_intent": "demo_intent",
            "query_params": {"k": 1},
            "result_metrics": {"x": 10},
        })
        self.assertEqual(rec["status"], "recorded")
        rec2 = handle_record_decision({
            "category": "test",
            "scenario": "demo",
            "reasoning": "because",
            "outcome": "ok",
            "confidence": 0.8,
            "query_intent": "demo_intent",
            "query_params": {"k": 1},
            "result_metrics": {"x": 12},
        })
        cmp = handle_compare_with_history({
            "decision_id": rec2["decision_id"],
            "match_mode": "fingerprint",
        })
        self.assertEqual(len(cmp["matches"]), 1)
        self.assertEqual(cmp["matches"][0]["delta"]["x"]["absolute"], 2)


if __name__ == "__main__":
    unittest.main()
