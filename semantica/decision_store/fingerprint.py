"""Query fingerprint and content hashing for the Decision Store."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Optional


def sha256_hex(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def hash_content(content: str) -> str:
    return f"sha256:{sha256_hex(content)}"


def hash_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as fh:
            return f"sha256:{hashlib.sha256(fh.read()).hexdigest()}"
    except OSError:
        return None


def normalize_sql(sql: str) -> str:
    """Collapse whitespace and lowercase SQL keywords for stable hashing."""
    text = " ".join(sql.split())
    keywords = (
        "select", "from", "where", "group", "by", "order", "having",
        "join", "left", "right", "inner", "outer", "on", "as", "and",
        "or", "not", "in", "with", "union", "limit", "offset", "distinct",
    )
    for kw in keywords:
        text = re.sub(rf"\b{kw}\b", kw, text, flags=re.IGNORECASE)
    return text.lower()


def hash_sql(sql: str) -> str:
    if not sql or not sql.strip():
        return ""
    return hash_content(normalize_sql(sql))


def normalize_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not params:
        return {}
    skip = {"session_id", "recorded_at", "decision_id"}
    out: Dict[str, Any] = {}
    for key in sorted(params):
        if key in skip:
            continue
        value = params[key]
        if isinstance(value, list):
            out[key] = sorted(value)
        elif isinstance(value, str) and value.isdigit():
            out[key] = int(value)
        else:
            out[key] = value
    return out


def derive_query_intent(
    category: str,
    scenario: str,
    query_intent: Optional[str] = None,
) -> str:
    if query_intent and query_intent.strip():
        return query_intent.strip()
    slug = f"{category} {scenario[:120]}".lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug or "unknown_intent"


def compute_query_fingerprint(
    *,
    query_intent: str,
    query_params: Optional[Dict[str, Any]] = None,
    sql_hash: str = "",
    rules_hash: str = "",
    mapping_hash: Optional[str] = None,
) -> str:
    payload = {
        "intent": query_intent,
        "params": normalize_params(query_params),
        "sql_hash": sql_hash or "",
        "rules_hash": rules_hash or "",
        "mapping_hash": mapping_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"fp:sha256:{sha256_hex(canonical)[:16]}"
