"""MCP tool handlers backed by the JSONL Decision Store (not the knowledge graph)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from semantica.decision_store import DecisionStore
from semantica.decision_store.store import check_store_writability, default_store_root

_store: Optional[DecisionStore] = None


def _get_store() -> DecisionStore:
    global _store
    if _store is None:
        _store = DecisionStore()
    return _store


def handle_get_decision_store_status(_args: dict) -> dict:
    """Report Decision Store path, writability, and env configuration."""
    status = check_store_writability()
    status["index_mode"] = (
        __import__("os").environ.get("SEMANTICA_DECISION_STORE_INDEX") or "auto"
    )
    if status.get("writable"):
        try:
            store = _get_store()
            status["record_count"] = len(store._scan_jsonl())
        except Exception as exc:
            status["record_count_error"] = str(exc)
    return status


def _strip_internal(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if not k.startswith("_")}


def handle_record_decision(args: dict) -> dict:
    required = ["category", "scenario", "reasoning", "outcome", "confidence"]
    for field in required:
        if field not in args:
            return {"error": f"missing required field: {field}"}
    try:
        store = _get_store()
        return store.record(**args)
    except ValueError as exc:
        return {"error": str(exc)}
    except OSError as exc:
        root = default_store_root()
        hint = (
            f"Decision Store path not writable: {root}. "
            "Set SEMANTICA_DECISION_STORE=/workflow_data/decisions in the semantica MCP "
            "workflow env and create that directory under workflow_data on the host."
        )
        if "read-only" in str(exc).lower() or exc.errno in (30, 13):  # EROFS, EACCES
            return {"error": hint, "detail": str(exc)}
        return {"error": f"could not write decision store: {exc}", "store_path": root}


def handle_query_decisions(args: dict) -> dict:
    store = _get_store()
    try:
        results = store.query(
            query=args.get("query") or None,
            category=args.get("category"),
            limit=int(args.get("limit", 10)),
        )
        return {"decisions": [_strip_internal(r) for r in results]}
    except Exception as exc:
        return {"error": str(exc), "decisions": []}


def handle_find_precedents(args: dict) -> dict:
    scenario = args.get("scenario", "")
    if not scenario:
        return {"error": "scenario is required", "precedents": []}
    store = _get_store()
    try:
        precedents = store.find_precedents(
            scenario,
            max_results=int(args.get("max_results", 5)),
            category=args.get("category"),
        )
        return {"precedents": [_strip_internal(r) for r in precedents]}
    except Exception as exc:
        return {"error": str(exc), "precedents": []}


def handle_get_causal_chain(args: dict) -> dict:
    decision_id = (args.get("decision_id") or "").strip()
    if not decision_id:
        return {"error": "decision_id is required", "chain": []}
    direction = args.get("direction", "downstream")
    max_depth = int(args.get("max_depth", 5))
    store = _get_store()
    try:
        chain = store.get_causal_chain(
            decision_id,
            direction=direction,
            max_depth=max_depth,
        )
        return {
            "chain": [_strip_internal(r) for r in chain],
            "count": len(chain),
            "direction": direction,
        }
    except Exception as exc:
        return {"error": str(exc), "chain": []}


def handle_compare_with_history(args: dict) -> dict:
    store = _get_store()
    try:
        return store.compare_with_history(
            query_fingerprint=args.get("query_fingerprint"),
            query_intent=args.get("query_intent"),
            query_params=args.get("query_params"),
            sql_text=args.get("sql_text"),
            category=args.get("category"),
            current_decision_id=args.get("current_decision_id") or args.get("decision_id"),
            result_metrics=args.get("result_metrics"),
            lookback_days=int(args.get("lookback_days", 90)),
            match_mode=args.get("match_mode", "fingerprint"),
            limit=int(args.get("limit", 5)),
        )
    except Exception as exc:
        return {"error": str(exc), "matches": []}


def handle_explain_decision_delta(args: dict) -> dict:
    decision_id = (args.get("decision_id") or "").strip()
    if not decision_id:
        return {"error": "decision_id is required"}
    store = _get_store()
    try:
        return store.explain_decision_delta(
            decision_id,
            baseline_decision_id=args.get("baseline_decision_id"),
            auto_baseline=bool(args.get("auto_baseline", False)),
        )
    except Exception as exc:
        return {"error": str(exc)}
