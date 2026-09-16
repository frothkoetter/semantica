"""
Domain-agnostic business rules YAML loading, graph ingestion, and MCP payloads.

Rules YAML is opaque to the MCP server beyond common patterns (thresholds, lists of
{class, when} classification rules, nested section dicts). SQL compilation for a
specific domain belongs in application code (e.g. examples/airline_business_sql.py).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from semantica.mcp_server.schema_mappings import ontology_uri

_RESERVED_KEYS = frozenset({"ontology_namespace"})


def resolve_business_rules_path(path: Optional[str] = None) -> Optional[str]:
    """Resolve rules YAML from explicit path or SEMANTICA_BUSINESS_RULES env."""
    if path:
        return path if os.path.exists(path) else None
    env_path = (os.environ.get("SEMANTICA_BUSINESS_RULES") or "").strip()
    if env_path and os.path.exists(env_path):
        return env_path
    return None


def load_business_rules(path: Optional[str] = None) -> Dict[str, Any]:
    """Load business rules YAML. Returns empty dict when no file is configured."""
    import yaml

    config_path = resolve_business_rules_path(path)
    if not config_path:
        return {}
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _normalize_token(value: str) -> str:
    return value.lower().replace("_", "").replace("-", "")


def _find_class_uri(
    graph: Any,
    class_name: str,
    ontology_namespace: str = "",
) -> Optional[str]:
    key = _normalize_token(class_name)
    for node in graph.find_nodes(node_type="OntologyClass"):
        label = _normalize_token(str(node.get("label") or node.get("content") or ""))
        uri = str(node.get("uri") or node.get("id") or "")
        local = _normalize_token(uri.rsplit("#", 1)[-1])
        if label == key or local == key:
            return str(node.get("uri") or node.get("id"))
    ns = (ontology_namespace or "").strip()
    if ns:
        return ontology_uri(class_name, ns)
    return None


def _classification_rule_sections(rules: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Lists of {class, when, ...} keyed by YAML section name (e.g. *_rules)."""
    sections: Dict[str, List[Dict[str, Any]]] = {}
    for key, value in rules.items():
        if key in _RESERVED_KEYS or not isinstance(value, list):
            continue
        items = [item for item in value if isinstance(item, dict) and item.get("class")]
        if items:
            sections[key] = items
    return sections


def ingest_business_rules_into_graph(
    graph: Any,
    rules: Dict[str, Any],
    *,
    source_path: str = "",
) -> Dict[str, int]:
    """
    Materialize YAML business rules as BusinessRule nodes linked to ontology classes.

    Idempotent: skips rule IDs that already exist in the graph.
    """
    stats = {
        "business_rule_nodes": 0,
        "applies_to_edges": 0,
        "skipped_existing": 0,
    }
    if not rules:
        return stats

    ns = rules.get("ontology_namespace") or ""
    source = source_path or "business_rules.yaml"

    def _add_rule(
        rule_id: str,
        *,
        rule_kind: str,
        content: str,
        ontology_class: Optional[str] = None,
        when: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if graph.nodes.get(rule_id):
            stats["skipped_existing"] += 1
            return
        graph.add_node(
            rule_id,
            node_type="BusinessRule",
            content=content,
            rule_kind=rule_kind,
            ontology_class=ontology_class,
            when=when,
            source=source,
            metadata=metadata or {},
        )
        stats["business_rule_nodes"] += 1
        if ontology_class:
            class_uri = _find_class_uri(graph, ontology_class, ns)
            if class_uri:
                graph.add_edge(rule_id, class_uri, edge_type="appliesToClass")
                stats["applies_to_edges"] += 1

    thresholds = rules.get("thresholds")
    if isinstance(thresholds, dict):
        for key, value in thresholds.items():
            _add_rule(
                f"business_rule:threshold:{key}",
                rule_kind="threshold",
                content=key,
                metadata={"value": value},
            )

    classification_sections = _classification_rule_sections(rules)
    for section, items in classification_sections.items():
        for idx, rule in enumerate(items):
            cls = str(rule.get("class", f"rule_{idx}"))
            _add_rule(
                f"business_rule:{section}:{cls}",
                rule_kind=section,
                content=cls,
                ontology_class=cls,
                when=rule.get("when"),
                metadata={k: v for k, v in rule.items() if k not in {"class", "when"}},
            )

    for key, value in rules.items():
        if key in _RESERVED_KEYS or key == "thresholds" or key in classification_sections:
            continue
        if isinstance(value, dict):
            for name, spec in value.items():
                if not isinstance(spec, dict):
                    continue
                cls = spec.get("class")
                _add_rule(
                    f"business_rule:{key}:{name}",
                    rule_kind=key,
                    content=str(cls or name),
                    ontology_class=str(cls) if cls else None,
                    metadata=spec,
                )

    return stats


def summarize_business_rules(rules: Dict[str, Any]) -> Dict[str, Any]:
    """Compact summary for get_graph_summary (domain-agnostic)."""
    if not rules:
        return {}
    summary: Dict[str, Any] = {
        "ontology_namespace": rules.get("ontology_namespace"),
        "section_counts": {},
        "classification_rule_counts": {},
    }
    if isinstance(rules.get("thresholds"), dict):
        summary["thresholds"] = rules["thresholds"]
    for key, value in rules.items():
        if key in _RESERVED_KEYS:
            continue
        if isinstance(value, (list, dict)):
            summary["section_counts"][key] = len(value)
    for section, items in _classification_rule_sections(rules).items():
        summary["classification_rule_counts"][section] = len(items)
    return summary


def rules_to_reasoning_strings(rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Convert YAML rules to facts/rules strings for run_reasoning."""
    facts: List[str] = []
    reasoning_rules: List[str] = []

    thresholds = rules.get("thresholds")
    if isinstance(thresholds, dict):
        for key, value in thresholds.items():
            facts.append(f"Threshold({key}, {value})")

    for section, items in _classification_rule_sections(rules).items():
        for rule in items:
            cls = rule.get("class")
            when = rule.get("when")
            if cls and when:
                reasoning_rules.append(f"IF ({when}) THEN {cls}")

    return facts, reasoning_rules


def build_business_rules_payload(
    rules: Dict[str, Any],
    *,
    rules_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Full payload for get_business_rules MCP tool (declarative rules only)."""
    if not rules:
        return {
            "rules_loaded": False,
            "rules_path": rules_path,
            "rules_path_exists": bool(rules_path and os.path.exists(rules_path)),
        }

    facts, reasoning_rules = rules_to_reasoning_strings(rules)
    return {
        "rules_loaded": True,
        "rules_path": rules_path,
        "rules_path_exists": bool(rules_path and os.path.exists(rules_path)),
        "ontology_namespace": rules.get("ontology_namespace"),
        "rules": rules,
        "classification_rules": _classification_rule_sections(rules),
        "reasoning_facts": facts,
        "reasoning_rules": reasoning_rules,
    }
