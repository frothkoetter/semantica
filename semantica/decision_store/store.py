"""Decision Store — JSONL audit log with optional SQLite index."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from semantica.decision_store.compare import (
    build_summary,
    compare_records,
    explain_delta,
    params_overlap,
    scenario_similarity,
)
from semantica.decision_store.fingerprint import (
    compute_query_fingerprint,
    derive_query_intent,
    hash_file,
    hash_sql,
)
from semantica.decision_store.index import DecisionIndex
from semantica.decision_store.writer import (
    append_record,
    ensure_store_dir,
    jsonl_path,
    maybe_offload_blob,
)

SCHEMA_VERSION = "1.0"


def default_store_root() -> str:
    env = (os.environ.get("SEMANTICA_DECISION_STORE") or "").strip()
    if env:
        return os.path.expanduser(env)
    return os.path.expanduser("~/.semantica/decisions")


def index_mode() -> str:
    return (os.environ.get("SEMANTICA_DECISION_STORE_INDEX") or "auto").strip().lower()


def blob_max_inline() -> int:
    try:
        return int(os.environ.get("SEMANTICA_DECISION_BLOB_MAX_INLINE", "8192"))
    except ValueError:
        return 8192


def _rules_hash() -> str:
    from semantica.mcp_server.business_rules import resolve_business_rules_path

    path = resolve_business_rules_path()
    return hash_file(path) if path else ""


def _mapping_hash() -> str:
    path = (os.environ.get("SEMANTICA_MAPPING_CONFIG") or "").strip()
    return hash_file(path) if path and os.path.exists(path) else ""


class DecisionStore:
    def __init__(
        self,
        store_root: Optional[str] = None,
        *,
        index_enabled: Optional[bool] = None,
    ) -> None:
        self.store_root = store_root or default_store_root()
        mode = index_mode()
        if index_enabled is None:
            index_enabled = mode != "none"
        self._index = DecisionIndex(self.store_root, enabled=index_enabled)
        ensure_store_dir(self.store_root)

    def close(self) -> None:
        self._index.close()

    def read_at_offset(self, offset: int) -> Dict[str, Any]:
        path = jsonl_path(self.store_root)
        with open(path, "rb") as fh:
            fh.seek(offset)
            line = fh.readline()
        if not line.strip():
            raise ValueError(f"No record at offset {offset}")
        return json.loads(line.decode("utf-8"))

    def get(self, decision_id: str) -> Optional[Dict[str, Any]]:
        for record in self._scan_jsonl():
            if record.get("decision_id") == decision_id:
                return record
        return None

    def _scan_jsonl(self, *, reverse: bool = False) -> List[Dict[str, Any]]:
        path = jsonl_path(self.store_root)
        if not os.path.exists(path):
            return []
        records: List[Dict[str, Any]] = []
        with open(path, "rb") as fh:
            while True:
                offset = fh.tell()
                line = fh.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line.decode("utf-8"))
                    record["_json_line_offset"] = offset
                    records.append(record)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        if reverse:
            records.reverse()
        return records

    def _load_matches_from_index(
        self,
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                out.append(self.read_at_offset(int(row["json_line_offset"])))
            except (ValueError, KeyError, json.JSONDecodeError):
                continue
        return out

    def record(self, **fields: Any) -> Dict[str, Any]:
        required = ["category", "scenario", "reasoning", "outcome", "confidence"]
        for field in required:
            if field not in fields or fields[field] is None or fields[field] == "":
                raise ValueError(f"missing required field: {field}")

        confidence = float(fields["confidence"])
        if confidence < 0 or confidence > 1:
            raise ValueError("confidence must be between 0 and 1")

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        decision_id = str(fields.get("decision_id") or uuid.uuid4())
        query_intent = derive_query_intent(
            fields["category"],
            fields["scenario"],
            fields.get("query_intent"),
        )
        sql_text = fields.get("sql_text") or ""
        sql_hash = fields.get("sql_hash") or hash_sql(sql_text)
        rules_hash = fields.get("business_rules_hash") or _rules_hash()
        mapping_hash = fields.get("ontology_mapping_hash") or _mapping_hash()
        query_params = fields.get("query_params")

        fingerprint = fields.get("query_fingerprint") or compute_query_fingerprint(
            query_intent=query_intent,
            query_params=query_params,
            sql_hash=sql_hash,
            rules_hash=rules_hash,
            mapping_hash=mapping_hash or None,
        )

        max_inline = blob_max_inline()
        result_metrics = fields.get("result_metrics")
        metrics_inline, metrics_blob = maybe_offload_blob(
            self.store_root, "result_metrics", result_metrics, max_inline
        )
        sql_inline, sql_blob = maybe_offload_blob(
            self.store_root, "sql_text", sql_text if sql_text else None, max_inline
        )

        record: Dict[str, Any] = {
            "decision_id": decision_id,
            "recorded_at": now,
            "schema_version": SCHEMA_VERSION,
            "category": fields["category"],
            "scenario": fields["scenario"],
            "reasoning": fields["reasoning"],
            "outcome": fields["outcome"],
            "confidence": confidence,
            "decision_maker": fields.get("decision_maker", "mcp_client"),
            "query_intent": query_intent,
            "query_fingerprint": fingerprint,
            "sql_hash": sql_hash,
            "business_rules_hash": rules_hash,
        }

        optional_keys = (
            "valid_from", "valid_until", "session_id", "agent_id", "tool_chain",
            "source_refs", "supersedes", "result_row_count", "result_checksum",
            "causal_parent_ids", "ontology_mapping_hash",
        )
        for key in optional_keys:
            if fields.get(key) is not None:
                record[key] = fields[key]

        if query_params:
            record["query_params"] = query_params
        if mapping_hash:
            record["ontology_mapping_hash"] = mapping_hash
        if metrics_inline is not None:
            record["result_metrics"] = metrics_inline
        if metrics_blob:
            record["result_metrics_blob_ref"] = metrics_blob
        if sql_inline:
            record["sql_text"] = sql_inline
        if sql_blob:
            record["sql_blob_ref"] = sql_blob

        offset, path = append_record(self.store_root, record)
        self._index.upsert(record, offset)

        return {
            "decision_id": decision_id,
            "query_fingerprint": fingerprint,
            "recorded_at": now,
            "store_path": path,
            "status": "recorded",
        }

    def query(
        self,
        *,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 100))

        if category and self._index.enabled:
            rows = self._index.find_by_category(category, limit=limit)
            if rows:
                return self._load_matches_from_index(rows)

        records = self._scan_jsonl(reverse=True)
        if category:
            records = [r for r in records if r.get("category") == category]
        if query:
            q = query.lower()
            records = [
                r for r in records
                if q in (r.get("scenario") or "").lower()
                or q in (r.get("reasoning") or "").lower()
                or q in (r.get("outcome") or "").lower()
                or q in (r.get("query_intent") or "").lower()
            ]
        return records[:limit]

    def find_precedents(
        self,
        scenario: str,
        *,
        max_results: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        max_results = max(1, min(max_results, 50))
        records = self._scan_jsonl(reverse=True)
        if category:
            records = [r for r in records if r.get("category") == category]
        scored = [
            (scenario_similarity(scenario, r.get("scenario") or ""), r)
            for r in records
        ]
        scored = [(s, r) for s, r in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1].get("recorded_at", "")))
        return [
            {**r, "similarity_score": round(s, 4)}
            for s, r in scored[:max_results]
        ]

    def get_causal_chain(
        self,
        decision_id: str,
        *,
        direction: str = "downstream",
        max_depth: int = 5,
    ) -> List[Dict[str, Any]]:
        max_depth = max(1, min(max_depth, 100))
        by_id = {r["decision_id"]: r for r in self._scan_jsonl()}
        if decision_id not in by_id:
            return []

        # Build parent -> children map from causal_parent_ids
        children: Dict[str, List[str]] = {}
        for rid, rec in by_id.items():
            for pid in rec.get("causal_parent_ids") or []:
                children.setdefault(pid, []).append(rid)

        chain: List[Dict[str, Any]] = []
        visited = {decision_id}
        frontier = [decision_id]

        for _ in range(max_depth):
            next_frontier: List[str] = []
            for node_id in frontier:
                if direction == "upstream":
                    parents = by_id.get(node_id, {}).get("causal_parent_ids") or []
                    for pid in parents:
                        if pid not in visited and pid in by_id:
                            visited.add(pid)
                            chain.append(by_id[pid])
                            next_frontier.append(pid)
                else:
                    for cid in children.get(node_id, []):
                        if cid not in visited:
                            visited.add(cid)
                            chain.append(by_id[cid])
                            next_frontier.append(cid)
            if not next_frontier:
                break
            frontier = next_frontier
        return chain

    def compare_with_history(
        self,
        *,
        query_fingerprint: Optional[str] = None,
        query_intent: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        sql_text: Optional[str] = None,
        category: Optional[str] = None,
        current_decision_id: Optional[str] = None,
        result_metrics: Optional[Dict[str, Any]] = None,
        lookback_days: int = 90,
        match_mode: str = "fingerprint",
        limit: int = 5,
    ) -> Dict[str, Any]:
        limit = max(1, min(limit, 20))
        match_mode = (match_mode or "fingerprint").lower()

        current: Optional[Dict[str, Any]] = None
        if current_decision_id:
            current = self.get(current_decision_id)

        if current is None:
            intent = query_intent or (
                derive_query_intent(category or "unknown", "") if category else "unknown"
            )
            sql_hash = hash_sql(sql_text or "")
            rules_hash = _rules_hash()
            mapping_hash = _mapping_hash()
            fp = query_fingerprint or compute_query_fingerprint(
                query_intent=intent,
                query_params=query_params,
                sql_hash=sql_hash,
                rules_hash=rules_hash,
                mapping_hash=mapping_hash or None,
            )
            current = {
                "decision_id": None,
                "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "query_fingerprint": fp,
                "query_intent": intent,
                "query_params": query_params,
                "sql_hash": sql_hash,
                "business_rules_hash": rules_hash,
                "result_metrics": result_metrics,
                "category": category,
            }

        exclude_id = current.get("decision_id")
        priors: List[Dict[str, Any]] = []

        if match_mode == "fingerprint" and current.get("query_fingerprint"):
            fp = current["query_fingerprint"]
            if self._index.enabled:
                rows = self._index.find_by_fingerprint(
                    fp, limit=limit + 1, exclude_id=exclude_id, lookback_days=lookback_days
                )
                priors = self._load_matches_from_index(rows)
            else:
                priors = [
                    r for r in self._scan_jsonl(reverse=True)
                    if r.get("query_fingerprint") == fp
                    and r.get("decision_id") != exclude_id
                ][:limit]

        elif match_mode == "intent" and current.get("query_intent"):
            intent = current["query_intent"]
            if self._index.enabled:
                rows = self._index.find_by_intent(
                    intent, limit=limit + 5, exclude_id=exclude_id, lookback_days=lookback_days
                )
                candidates = self._load_matches_from_index(rows)
            else:
                candidates = [
                    r for r in self._scan_jsonl(reverse=True)
                    if r.get("query_intent") == intent
                    and r.get("decision_id") != exclude_id
                ]
            cur_params = current.get("query_params") or query_params
            scored = [
                (params_overlap(cur_params, r.get("query_params")), r)
                for r in candidates
            ]
            scored.sort(key=lambda x: -x[0])
            priors = [r for s, r in scored if s > 0][:limit]

        else:
            scenario = current.get("scenario") or ""
            if not scenario and query_intent:
                scenario = query_intent
            all_recs = self._scan_jsonl(reverse=True)
            if category:
                all_recs = [r for r in all_recs if r.get("category") == category]
            scored = [
                (scenario_similarity(scenario, r.get("scenario") or ""), r)
                for r in all_recs
                if r.get("decision_id") != exclude_id
            ]
            scored.sort(key=lambda x: -x[0])
            priors = [r for s, r in scored if s > 0][:limit]
            match_mode = "scenario"

        matches: List[Dict[str, Any]] = []
        for prior in priors[:limit]:
            reason = f"identical query_fingerprint" if match_mode == "fingerprint" else (
                f"query_intent match" if match_mode == "intent" else "scenario similarity"
            )
            score = 1.0 if match_mode == "fingerprint" else (
                params_overlap(current.get("query_params"), prior.get("query_params"))
                if match_mode == "intent"
                else scenario_similarity(
                    current.get("scenario") or "", prior.get("scenario") or ""
                )
            )
            matches.append(
                compare_records(current, prior, match_score=round(score, 4), match_reason=reason)
            )

        current_summary = {
            "decision_id": current.get("decision_id"),
            "recorded_at": current.get("recorded_at"),
            "result_metrics": current.get("result_metrics"),
            "query_fingerprint": current.get("query_fingerprint"),
        }

        return {
            "current": current_summary,
            "matches": matches,
            "summary": build_summary(matches, current_recorded_at=current.get("recorded_at")),
        }

    def explain_decision_delta(
        self,
        decision_id: str,
        *,
        baseline_decision_id: Optional[str] = None,
        auto_baseline: bool = False,
    ) -> Dict[str, Any]:
        current = self.get(decision_id)
        if not current:
            return {"error": f"decision not found: {decision_id}"}

        baseline: Optional[Dict[str, Any]] = None
        if baseline_decision_id:
            baseline = self.get(baseline_decision_id)
            if not baseline:
                return {"error": f"baseline decision not found: {baseline_decision_id}"}
        elif auto_baseline:
            cmp = self.compare_with_history(
                query_fingerprint=current.get("query_fingerprint"),
                query_intent=current.get("query_intent"),
                query_params=current.get("query_params"),
                current_decision_id=decision_id,
                match_mode="fingerprint",
                limit=1,
            )
            match_rows = cmp.get("matches") or []
            if match_rows:
                baseline = self.get(match_rows[0]["decision_id"])
        if not baseline:
            return {
                "error": "no baseline decision available",
                "decision_id": decision_id,
            }

        structured = compare_records(current, baseline, match_reason="baseline")
        return {
            "explanation": explain_delta(current, baseline),
            "structured_delta": structured,
            "decision_id": decision_id,
            "baseline_decision_id": baseline.get("decision_id"),
        }

    def reindex(self) -> int:
        return self._index.reindex_from_jsonl(jsonl_path(self.store_root))
