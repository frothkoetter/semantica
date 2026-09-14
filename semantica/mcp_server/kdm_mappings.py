"""
Backward-compatible shim for KDM-specific examples.

Prefer semantica.mcp_server.schema_mappings for new code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from semantica.mcp_server.schema_mappings import (
    apply_explicit_mappings,
    load_mapping_config as _load_mapping_config,
    normalize_db_token,
    ontology_uri,
    resolve_column_property,
    resolve_table_class,
)

KDM_NAMESPACE = "https://w3id.org/kdm/"


def kdm_uri(local_name: str, namespace: str = KDM_NAMESPACE) -> str:
    return ontology_uri(local_name, namespace)


def default_mapping_config_path() -> Optional[str]:
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
    config_path = path or default_mapping_config_path()
    if config_path:
        return _load_mapping_config(config_path)
    return _load_mapping_config(None)
