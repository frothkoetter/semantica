"""
Default and file-based mappings from SQL schemas to XUnternehmen.Kerndatenmodell (KDM).

Ships with config/kdm_db_mapping.yaml at the repository root. Override via
mapping_config_path in map_db_schema_to_ontology MCP tool calls.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KDM_NAMESPACE = "https://w3id.org/kdm/"

_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def normalize_db_token(value: str) -> str:
    """Normalize DB table/column identifier for lookup."""
    token = value.translate(_UMLAUT_MAP).lower()
    for ch in ("_", "-", " ", "."):
        token = token.replace(ch, "")
    return token


def kdm_uri(local_name: str, namespace: str = KDM_NAMESPACE) -> str:
    return f"{namespace.rstrip('/')}/{local_name}"


def default_mapping_config_path() -> Optional[str]:
    """Resolve bundled kdm_db_mapping.yaml relative to package or repo root."""
    candidates = [
        Path(__file__).resolve().parent / "data" / "kdm_db_mapping.yaml",
        Path(__file__).resolve().parents[2] / "config" / "kdm_db_mapping.yaml",
        Path.cwd() / "config" / "kdm_db_mapping.yaml",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def load_mapping_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load KDM mapping YAML.

    Returns dict with keys: ontology_namespace, tables, columns, foreign_keys.
    """
    import yaml

    config_path = path or default_mapping_config_path()
    if not config_path:
        return {
            "ontology_namespace": KDM_NAMESPACE,
            "tables": {},
            "columns": {},
            "foreign_keys": [],
        }
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"KDM mapping config not found: {config_path}")

    with open(config_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return {
        "ontology_namespace": data.get("ontology_namespace", KDM_NAMESPACE),
        "tables": data.get("tables") or {},
        "columns": data.get("columns") or {},
        "foreign_keys": data.get("foreign_keys") or [],
        "source_path": config_path,
    }


def resolve_table_class(
    table_name: str,
    mapping_config: Dict[str, Any],
) -> Optional[Tuple[str, str, float]]:
    """
    Resolve table → KDM class URI using explicit mapping config.

    Returns (class_uri, class_local_name, confidence) or None.
    """
    token = normalize_db_token(table_name)
    class_local = mapping_config.get("tables", {}).get(token)
    if not class_local:
        return None
    ns = mapping_config.get("ontology_namespace", KDM_NAMESPACE)
    return kdm_uri(class_local, ns), class_local, 1.0


def resolve_column_property(
    table_name: str,
    column_name: str,
    mapping_config: Dict[str, Any],
) -> Optional[Tuple[str, str, float]]:
    """
    Resolve column → KDM property URI using explicit mapping config.

    Returns (property_uri, property_local_name, confidence) or None.
    """
    table_token = normalize_db_token(table_name)
    col_token = normalize_db_token(column_name)
    columns_cfg: Dict[str, Any] = mapping_config.get("columns") or {}

    prop_local = None
    table_cols = columns_cfg.get(table_token) or {}
    if col_token in table_cols:
        prop_local = table_cols[col_token]
    else:
        global_cols = columns_cfg.get("_global") or {}
        prop_local = global_cols.get(col_token)

    if not prop_local:
        return None

    ns = mapping_config.get("ontology_namespace", KDM_NAMESPACE)
    return kdm_uri(prop_local, ns), prop_local, 1.0


def apply_explicit_mappings(
    schema_info: Dict[str, Any],
    mapping_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build table/column mapping suggestions using explicit KDM mapping config.

    Takes precedence over heuristic name matching (confidence = 1.0).
    """
    table_mappings: List[Dict[str, Any]] = []
    column_mappings: List[Dict[str, Any]] = []
    fk_mappings: List[Dict[str, Any]] = []

    table_to_class: Dict[str, Dict[str, str]] = {}

    for table in schema_info.get("tables", []):
        table_name = table.get("name", "")
        resolved = resolve_table_class(table_name, mapping_config)
        entry = {
            "table": table_name,
            "suggested_class_uri": None,
            "suggested_class_label": None,
            "confidence": 0.0,
            "status": "unmapped",
            "mapping_source": "explicit",
        }
        if resolved:
            class_uri, class_local, score = resolved
            entry.update(
                {
                    "suggested_class_uri": class_uri,
                    "suggested_class_label": class_local,
                    "confidence": score,
                    "status": "mapped",
                }
            )
            table_to_class[table_name] = {
                "uri": class_uri,
                "label": class_local,
            }
        table_mappings.append(entry)

        for col in table.get("columns", []):
            col_name = col.get("name", "")
            col_resolved = resolve_column_property(table_name, col_name, mapping_config)
            col_entry = {
                "table": table_name,
                "column": col_name,
                "sql_type": col.get("type"),
                "suggested_property_uri": None,
                "suggested_property_label": None,
                "confidence": 0.0,
                "status": "unmapped",
                "mapping_source": "explicit",
            }
            if col_resolved:
                prop_uri, prop_local, score = col_resolved
                col_entry.update(
                    {
                        "suggested_property_uri": prop_uri,
                        "suggested_property_label": prop_local,
                        "confidence": score,
                        "status": "mapped",
                    }
                )
            column_mappings.append(col_entry)

    configured_fks = mapping_config.get("foreign_keys") or []
    seen_fk_keys = set()

    for fk in schema_info.get("foreign_keys", []):
        src_table = fk.get("constrained_table") or fk.get("table_name") or ""
        tgt_table = fk.get("referred_table") or ""
        if not src_table or not tgt_table:
            continue
        src_cls = table_to_class.get(src_table)
        tgt_cls = table_to_class.get(tgt_table)
        edge_type = "references"
        for cfg in configured_fks:
            if (
                normalize_db_token(cfg.get("source_table", "")) == normalize_db_token(src_table)
                and normalize_db_token(cfg.get("target_table", "")) == normalize_db_token(tgt_table)
            ):
                edge_type = cfg.get("edge_type", edge_type)
                break
        fk_mappings.append(
            {
                "source_table": src_table,
                "target_table": tgt_table,
                "source_class_uri": src_cls["uri"] if src_cls else None,
                "target_class_uri": tgt_cls["uri"] if tgt_cls else None,
                "suggested_edge_type": edge_type,
                "status": "mapped" if src_cls and tgt_cls else "unmapped",
                "mapping_source": "explicit",
            }
        )
        seen_fk_keys.add((src_table, tgt_table))

    mapped_tables = sum(1 for m in table_mappings if m["status"] == "mapped")
    mapped_columns = sum(1 for m in column_mappings if m["status"] == "mapped")

    return {
        "table_mappings": table_mappings,
        "column_mappings": column_mappings,
        "foreign_key_mappings": fk_mappings,
        "mapping_config": mapping_config.get("source_path"),
        "summary": {
            "tables": len(table_mappings),
            "tables_mapped": mapped_tables,
            "columns": len(column_mappings),
            "columns_mapped": mapped_columns,
            "foreign_keys": len(fk_mappings),
        },
    }
