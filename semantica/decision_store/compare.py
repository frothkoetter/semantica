"""History comparison and delta computation for Decision Store records."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def scenario_similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def params_overlap(
    current: Optional[Dict[str, Any]],
    prior: Optional[Dict[str, Any]],
) -> float:
    if not current or not prior:
        return 0.0
    keys_a, keys_b = set(current), set(prior)
    if not keys_a and not keys_b:
        return 1.0
    union = keys_a | keys_b
    if not union:
        return 0.0
    matching = sum(1 for k in keys_a & keys_b if current[k] == prior[k])
    return matching / len(union)


def compute_metric_deltas(
    current: Optional[Dict[str, Any]],
    prior: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Optional[float]]]:
    deltas: Dict[str, Dict[str, Optional[float]]] = {}
    if not isinstance(current, dict) or not isinstance(prior, dict):
        return deltas
    for key in sorted(set(current) | set(prior)):
        cur_val, prior_val = current.get(key), prior.get(key)
        if isinstance(cur_val, (int, float)) and isinstance(prior_val, (int, float)):
            absolute = cur_val - prior_val
            relative_pct = (absolute / prior_val * 100) if prior_val else None
            deltas[key] = {"absolute": absolute, "relative_pct": relative_pct}
    return deltas


def build_summary(
    matches: List[Dict[str, Any]],
    *,
    current_recorded_at: Optional[str] = None,
) -> str:
    if not matches:
        return "No prior decisions found for comparison."
    best = matches[0]
    prior_at = best.get("recorded_at", "unknown date")
    delta = best.get("delta") or {}
    if not delta:
        if best.get("outcome_changed"):
            return f"Outcome changed vs. prior run on {prior_at}."
        return f"Prior match on {prior_at}; no numeric metrics to compare."
    max_rel = max(
        (abs(v["relative_pct"]) for v in delta.values() if v.get("relative_pct") is not None),
        default=0.0,
    )
    if max_rel < 0.1:
        return f"Results stable within 0.1% vs. last run on {prior_at}."
    if max_rel < 5:
        return f"Results changed slightly (max {max_rel:.1f}%) vs. prior run on {prior_at}."
    return f"Results changed significantly (max {max_rel:.1f}%) vs. prior run on {prior_at}."


def compare_records(
    current: Dict[str, Any],
    prior: Dict[str, Any],
    *,
    match_score: float = 1.0,
    match_reason: str = "match",
) -> Dict[str, Any]:
    cur_metrics = current.get("result_metrics")
    prior_metrics = prior.get("result_metrics")
    delta = compute_metric_deltas(cur_metrics, prior_metrics)
    outcome_changed = current.get("outcome") != prior.get("outcome")
    return {
        "decision_id": prior.get("decision_id"),
        "recorded_at": prior.get("recorded_at"),
        "match_score": match_score,
        "match_reason": match_reason,
        "result_metrics": prior_metrics,
        "outcome": prior.get("outcome"),
        "delta": delta,
        "outcome_changed": outcome_changed,
        "sql_changed": bool(
            current.get("sql_hash")
            and prior.get("sql_hash")
            and current.get("sql_hash") != prior.get("sql_hash")
        ),
        "rules_changed": bool(
            current.get("business_rules_hash")
            and prior.get("business_rules_hash")
            and current.get("business_rules_hash") != prior.get("business_rules_hash")
        ),
    }


def explain_delta(current: Dict[str, Any], baseline: Dict[str, Any]) -> str:
    cmp = compare_records(current, baseline, match_reason="baseline")
    parts = [f"Comparing decision {current.get('decision_id')} to baseline {baseline.get('decision_id')}."]
    if cmp["sql_changed"]:
        parts.append("SQL changed between runs.")
    if cmp["rules_changed"]:
        parts.append("Business rules changed between runs.")
    if cmp["outcome_changed"]:
        parts.append(
            f"Outcome changed from {baseline.get('outcome')!r} to {current.get('outcome')!r}."
        )
    delta = cmp.get("delta") or {}
    if delta:
        changes = []
        for key, d in sorted(delta.items()):
            rel = d.get("relative_pct")
            if rel is not None:
                changes.append(f"{key}: {rel:+.2f}%")
            else:
                changes.append(f"{key}: {d.get('absolute'):+g}")
        parts.append("Metric deltas: " + ", ".join(changes) + ".")
    elif not cmp["outcome_changed"]:
        parts.append("No material changes detected.")
    return " ".join(parts)
