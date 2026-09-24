"""
Resolve XUnternehmen KDM ontology terms → Hive/Iceberg tables/columns.

Uses config/xunternehmen_r2rml_db_mapping.yaml (+ optional Semantica graph for class URIs).
Business tiers (TierA_Vollstaendig, …) are compiled at query time from business rules YAML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from xunternehmen_business_sql import (
    camel_to_snake,
    load_business_rules,
    sql_anschrift_type_expr,
    sql_jp_data_quality_tier_expr,
    sql_np_completeness_flag,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = REPO / "config" / "xunternehmen_r2rml_db_mapping.yaml"
ONTOLOGY_NS = "https://w3id.org/kdm/"
DEFAULT_DATABASE = "xunternehmen"

# Ontology class → Hive table (kdm/hive/xunternehmen_ddl.sql)
CLASS_TABLE: Dict[str, str] = {
    "NatuerlichePerson": "natuerliche_person",
    "NameEinerNatuerlichenPerson": "name_natuerliche_person",
    "Geburt": "geburt",
    "JuristischePerson": "juristische_person",
    "RechtsfaehigePersonengesellschaft": "rechtsfaehige_personengesellschaft",
    "SonstigePersonenvereinigung": "sonstige_personenvereinigung",
    "WirtschaftlicheTaetigkeit": "wirtschaftliche_taetigkeit",
    "Anschrift": "anschrift",
    "Kommunikation": "kommunikation",
    "Eintragung": "eintragung",
    "Sitz": "sitz",
    "EffektiverVerwaltungssitz": "effektiver_verwaltungssitz",
    "Betriebsstaette": "betriebsstaette",
    "Wirtschaftszweig": "wirtschaftszweig",
    "Antrag": "antrag",
    "Anzeige": "anzeige",
    "Gesellschafter": "rolle_gesellschafter",
}

RUNTIME_PROPERTIES: Dict[str, str] = {
    "dataQualityTier": "data_quality_tier",
    "anschriftSubtype": "anschrift_subtype",
    "hatGeburt": "hat_geburt",
}

OBJECT_PROPERTY_JOINS: Dict[str, Dict[str, str]] = {
    "geburt": {
        "from_class": "NatuerlichePerson",
        "from_column": "id",
        "to_class": "Geburt",
        "to_column": "natuerliche_person_id",
        "join_type": "LEFT",
    },
    "nameEinerNatuerlichenPerson": {
        "from_class": "NatuerlichePerson",
        "from_column": "id",
        "to_class": "NameEinerNatuerlichenPerson",
        "to_column": "natuerliche_person_id",
        "join_type": "LEFT",
    },
    "betriebsstaette": {
        "from_class": "WirtschaftlicheTaetigkeit",
        "from_column": "id",
        "to_class": "Betriebsstaette",
        "to_column": "wirtschaftliche_taetigkeit_id",
        "join_type": "LEFT",
    },
    "wirtschaftszweig": {
        "from_class": "WirtschaftlicheTaetigkeit",
        "from_column": "id",
        "to_class": "Wirtschaftszweig",
        "to_column": "wirtschaftliche_taetigkeit_id",
        "join_type": "LEFT",
    },
    "gesellschafter": {
        "from_class": "RechtsfaehigePersonengesellschaft",
        "from_column": "id",
        "to_class": "Gesellschafter",
        "to_column": "personengesellschaft_id",
        "join_type": "LEFT",
    },
}


def _local_name(uri: str) -> str:
    if not uri:
        return ""
    return uri.split("#", 1)[-1].rstrip("/").rsplit("/", 1)[-1]


def _normalize_key(value: str) -> str:
    return value.lower().replace("_", "").replace("-", "")


@dataclass(frozen=True)
class PhysicalColumn:
    database: str
    table: str
    column: str
    property_label: str
    class_label: str
    runtime_derived: bool = False

    @property
    def qualified(self) -> str:
        return f"{self.database}.{self.table}.{self.column}"


@dataclass(frozen=True)
class PhysicalTable:
    database: str
    table: str
    class_label: str
    class_uri: str

    @property
    def qualified(self) -> str:
        return f"{self.database}.{self.table}"


class XUnternehmenOntologyResolver:
    """Ontology → xunternehmen.* Hive mapping + runtime SQL for business rules."""

    def __init__(
        self,
        graph: Any = None,
        database: str = DEFAULT_DATABASE,
        mapping_path: Optional[str] = None,
        business_rules_path: Optional[str] = None,
    ):
        self.graph = graph
        self.database = database
        self.mapping_path = Path(mapping_path or DEFAULT_MAPPING)
        self.mapping = self._load_mapping()
        self.business_rules = load_business_rules(business_rules_path)
        self._class_uri_by_label = self._index_classes()
        self._column_by_class_prop: Dict[Tuple[str, str], str] = {}
        self._build_column_index()

    def _load_mapping(self) -> Dict[str, Any]:
        if not self.mapping_path.is_file():
            return {}
        with open(self.mapping_path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _index_classes(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if self.graph is not None:
            for node in self.graph.find_nodes(node_type="OntologyClass"):
                label = node.get("content") or _local_name(node.get("id", ""))
                out[label] = node.get("id") or f"{ONTOLOGY_NS}{label}"
        for cls in CLASS_TABLE:
            out.setdefault(cls, f"{ONTOLOGY_NS}{cls}")
        tables = self.mapping.get("tables") or {}
        for _key, cls in tables.items():
            out.setdefault(cls, f"{ONTOLOGY_NS}{cls}")
        return out

    def _build_column_index(self) -> None:
        columns = self.mapping.get("columns") or {}
        global_cols = columns.get("_global") or {}
        class_by_norm = {_normalize_key(k): v for k, v in (self.mapping.get("tables") or {}).items()}

        for norm_table, props in columns.items():
            if norm_table == "_global" or not isinstance(props, dict):
                continue
            class_label = class_by_norm.get(norm_table)
            if not class_label:
                continue
            for norm_col, prop_label in props.items():
                self._column_by_class_prop[(class_label, prop_label)] = camel_to_snake(prop_label)

        for norm_col, prop_label in global_cols.items():
            col = camel_to_snake(prop_label) if prop_label != norm_col else norm_col
            for class_label in CLASS_TABLE:
                if (class_label, prop_label) not in self._column_by_class_prop:
                    self._column_by_class_prop[(class_label, prop_label)] = col

        for prop, runtime_col in RUNTIME_PROPERTIES.items():
            if prop == "dataQualityTier":
                self._column_by_class_prop[("JuristischePerson", prop)] = runtime_col
            elif prop == "anschriftSubtype":
                self._column_by_class_prop[("Anschrift", prop)] = runtime_col
            elif prop == "hatGeburt":
                self._column_by_class_prop[("NatuerlichePerson", prop)] = runtime_col

    def class_uri(self, class_label: str) -> str:
        return self._class_uri_by_label.get(class_label, f"{ONTOLOGY_NS}{class_label}")

    def table_for_class(self, class_label: str) -> PhysicalTable:
        table = CLASS_TABLE.get(class_label)
        if not table:
            raise KeyError(f"No Hive table for ontology class {class_label}")
        return PhysicalTable(
            database=self.database,
            table=table,
            class_label=class_label,
            class_uri=self.class_uri(class_label),
        )

    def column_for_property(self, class_label: str, property_label: str) -> PhysicalColumn:
        col = self._column_by_class_prop.get((class_label, property_label))
        if not col:
            col = camel_to_snake(property_label)
        is_runtime = property_label in RUNTIME_PROPERTIES
        table = self.table_for_class(class_label)
        return PhysicalColumn(
            database=self.database,
            table=table.table,
            column=col,
            property_label=property_label,
            class_label=class_label,
            runtime_derived=is_runtime,
        )

    def join_sql(
        self,
        object_property: str,
        from_alias: Optional[str] = None,
        to_alias: Optional[str] = None,
    ) -> str:
        hint = OBJECT_PROPERTY_JOINS.get(object_property)
        if not hint:
            raise KeyError(f"Unknown object property: {object_property}")
        from_table = self.table_for_class(hint["from_class"])
        to_table = self.table_for_class(hint["to_class"])
        fa = from_alias or hint["from_class"][:2].lower()
        ta = to_alias or hint["to_class"][:2].lower()
        jt = hint.get("join_type", "JOIN")
        return (
            f"{jt} JOIN {to_table.qualified} {ta} "
            f"ON {fa}.{hint['from_column']} = {ta}.{hint['to_column']}"
        )

    def jp_register_links_sql(self, jp_alias: str = "jp") -> Tuple[str, str, str]:
        """LEFT JOINs for zuordnung_eintragung and zuordnung_sitz on JuristischePerson."""
        db = self.database
        ze = "ze"
        zs = "zs"
        eintragung = (
            f"LEFT JOIN {db}.zuordnung_eintragung {ze} "
            f"ON {ze}.owner_id = {jp_alias}.id AND {ze}.owner_typ = 'JuristischePerson'"
        )
        sitz = (
            f"LEFT JOIN {db}.zuordnung_sitz {zs} "
            f"ON {zs}.owner_id = {jp_alias}.id AND {zs}.owner_typ = 'JuristischePerson'"
        )
        return eintragung, sitz, ze

    def jp_data_quality_tier_sql(self, jp_alias: str = "jp") -> str:
        return sql_jp_data_quality_tier_expr(jp_alias)

    def anschrift_subtype_sql(self, as_alias: str = "a") -> str:
        return sql_anschrift_type_expr(as_alias)

    def np_hat_geburt_sql(self, np_alias: str = "np", geb_alias: str = "g") -> str:
        return sql_np_completeness_flag(np_alias, geb_alias)

    def describe_materialized_layer(self) -> List[Dict[str, str]]:
        core = (
            "NatuerlichePerson",
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "WirtschaftlicheTaetigkeit",
            "Anschrift",
            "Eintragung",
            "Betriebsstaette",
            "Wirtschaftszweig",
        )
        return [
            {
                "ontology_class": cls,
                "class_uri": self.class_uri(cls),
                "physical_table": self.table_for_class(cls).qualified,
            }
            for cls in core
        ]

    def describe_runtime_layer(self) -> List[Dict[str, str]]:
        return [
            {
                "ontology_property": prop,
                "runtime_column": col,
                "compiled_from": "config/xunternehmen_business_rules.yaml",
            }
            for prop, col in RUNTIME_PROPERTIES.items()
        ]
