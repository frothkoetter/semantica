"""SQL expression builders from config/xunternehmen_business_rules.yaml (KDM demo)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPO / "config" / "xunternehmen_business_rules.yaml"


def load_business_rules(path: Optional[str] = None) -> Dict[str, Any]:
    import yaml

    cfg_path = Path(path) if path else DEFAULT_RULES_PATH
    if not cfg_path.is_file():
        return {}
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def camel_to_snake(name: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")


def sql_jp_data_quality_tier_expr(jp_alias: str = "jp") -> str:
    """
    Runtime tier for JuristischePerson (not a Hive column).

    TierA: Name + BWN + Eintragung + Sitz
    TierB: Name + BWN, missing register links
    TierC: otherwise
    """
    return f"""CASE
  WHEN {jp_alias}.eingetragener_name IS NOT NULL
   AND TRIM({jp_alias}.eingetragener_name) <> ''
   AND {jp_alias}.bundeseinheitliche_wirtschaftsnummer IS NOT NULL
   AND ze.eintragung_id IS NOT NULL
   AND zs.sitz_id IS NOT NULL
    THEN 'TierA_Vollstaendig'
  WHEN {jp_alias}.eingetragener_name IS NOT NULL
   AND TRIM({jp_alias}.eingetragener_name) <> ''
   AND {jp_alias}.bundeseinheitliche_wirtschaftsnummer IS NOT NULL
    THEN 'TierB_Teilweise'
  ELSE 'TierC_Minimal'
END"""


def sql_np_completeness_flag(np_alias: str = "np", geb_alias: str = "g") -> str:
    """Boolean-ish flag: NatuerlichePerson has linked Geburt."""
    return f"({geb_alias}.id IS NOT NULL)"


def sql_anschrift_type_expr(as_alias: str = "a") -> str:
    """Map anschrift_typ to ontology-aligned subtype labels."""
    return f"""CASE {as_alias}.anschrift_typ
  WHEN 'INLAND_STRASSE' THEN 'InlandStrassenanschrift'
  WHEN 'INLAND_POSTFACH' THEN 'InlandPostfachanschrift'
  WHEN 'INLAND_GROSSEMPFAENGER' THEN 'InlandGrossempfaengeranschrift'
  WHEN 'AUSLAND' THEN 'AuslandAnschrift'
  ELSE 'Unbekannt'
END"""
