"""
Resolve airline ontology terms → physical Hive tables/columns via Semantica graph.

Physical tables: flights_orc, airlines, airports, planes (never *_csv).

Business semantics (TimeWindow, flightStatus, primaryDelayReason, …) are **not**
stored in Hive — they are compiled at query time from airline_business_rules.yaml
into inline SQL (subqueries / CASE / JOINs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from airline_business_sql import (
    load_business_rules,
    sql_delay_severity_expr,
    sql_flight_status_expr,
    sql_hub_airports_subquery,
    sql_primary_delay_reason_expr,
    sql_route_expr,
    sql_runtime_flight_subquery,
    sql_time_window_expr,
)

ONTOLOGY_NS = "https://w3id.org/demo/airline#"
DEFAULT_DATABASE = "airlinedata"

PREFERRED_TABLES: Dict[str, str] = {
    "Flight": "flights_orc",
    "Airline": "airlines",
    "Airport": "airports",
    "Plane": "planes",
}

# Ontology-derived Flight columns (exist only inside runtime subquery output).
RUNTIME_FLIGHT_PROPERTIES: Dict[str, str] = {
    "scheduledInWindowClass": "scheduled_in_window",
    "flightStatus": "flight_status",
    "delaySeverity": "delay_severity",
    "primaryDelayReason": "primary_delay_reason",
    "routeId": "route_id",
}

OBJECT_PROPERTY_JOINS: Dict[str, Dict[str, str]] = {
    "operatedBy": {
        "from_class": "Flight",
        "from_column": "uniquecarrier",
        "to_class": "Airline",
        "to_column": "code",
    },
    "assignedAircraft": {
        "from_class": "Flight",
        "from_column": "tailnum",
        "to_class": "Plane",
        "to_column": "tailnum",
    },
    "originAirport": {
        "from_class": "Flight",
        "from_column": "origin",
        "to_class": "Airport",
        "to_column": "iata",
    },
    "destinationAirport": {
        "from_class": "Flight",
        "from_column": "dest",
        "to_class": "Airport",
        "to_column": "iata",
    },
}


def _local_name(uri: str) -> str:
    if not uri:
        return ""
    return uri.split("#", 1)[-1].lstrip("/")


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


class AirlineOntologyResolver:
    """
    Ontology → physical mapping + runtime SQL compilation for business rules.

    Use table_for_class / column_for_property for raw Hive columns.
    Use flight_runtime_from() when the query needs business-logic fields.
    """

    def __init__(
        self,
        graph: Any,
        database: str = DEFAULT_DATABASE,
        business_rules_path: Optional[str] = None,
    ):
        self.graph = graph
        self.database = database
        self.business_rules = load_business_rules(business_rules_path)
        self._class_uri_by_label = self._index_classes()
        self._table_by_class: Dict[str, str] = dict(PREFERRED_TABLES)
        self._column_by_class_prop: Dict[Tuple[str, str], str] = {}
        self._runtime_props: set[str] = set(RUNTIME_FLIGHT_PROPERTIES.keys())
        self._build_physical_index()

    def _index_classes(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for node in self.graph.find_nodes(node_type="OntologyClass"):
            label = node.get("content") or _local_name(node.get("id", ""))
            out[label] = node.get("id") or node.get("uri")
        return out

    def _build_physical_index(self) -> None:
        for node in self.graph.find_nodes(node_type="DatabaseColumn"):
            meta = node.get("metadata") or {}
            table = meta.get("table_name") or ""
            if table.endswith("_csv"):
                continue
            col = meta.get("column_name") or node.get("content") or ""
            prop_uri = self._edge_target(node.get("id"), "mapsToProperty")
            if not prop_uri:
                continue
            prop_label = _local_name(prop_uri)
            class_label = self._class_for_table(table)
            if class_label:
                self._column_by_class_prop[(class_label, prop_label)] = col

        for prop, col in RUNTIME_FLIGHT_PROPERTIES.items():
            self._column_by_class_prop[("Flight", prop)] = col

    def _edge_target(self, node_id: str, edge_type: str) -> Optional[str]:
        for edge in self.graph.find_edges(edge_type):
            if edge.get("source") == node_id:
                return edge.get("target")
        return None

    def _class_for_table(self, table: str) -> Optional[str]:
        table_id = f"db:table:{table}"
        class_uri = self._edge_target(table_id, "mapsToClass")
        if not class_uri:
            for label, preferred in PREFERRED_TABLES.items():
                if preferred == table:
                    return label
            return None
        return _local_name(class_uri)

    def class_uri(self, class_label: str) -> str:
        return self._class_uri_by_label.get(class_label, f"{ONTOLOGY_NS}{class_label}")

    def table_for_class(self, class_label: str) -> PhysicalTable:
        table = self._table_by_class.get(class_label) or PREFERRED_TABLES.get(class_label)
        if not table:
            raise KeyError(f"No materialized table for ontology class {class_label}")
        return PhysicalTable(
            database=self.database,
            table=table,
            class_label=class_label,
            class_uri=self.class_uri(class_label),
        )

    def column_for_property(
        self,
        class_label: str,
        property_label: str,
        *,
        require_runtime: bool = False,
    ) -> PhysicalColumn:
        table = self.table_for_class(class_label)
        col = self._column_by_class_prop.get((class_label, property_label))
        if not col:
            raise KeyError(
                f"No mapping for {class_label}.{property_label} "
                f"(physical table {table.table})"
            )
        is_runtime = property_label in self._runtime_props
        if require_runtime and not is_runtime:
            raise KeyError(f"{property_label} is a physical column, not runtime-derived")
        if is_runtime:
            table_name = table.table
        else:
            table_name = table.table
        return PhysicalColumn(
            database=self.database,
            table=table_name,
            column=col,
            property_label=property_label,
            class_label=class_label,
            runtime_derived=is_runtime,
        )

    def join_hint(self, object_property: str) -> Dict[str, str]:
        hint = OBJECT_PROPERTY_JOINS.get(object_property)
        if not hint:
            raise KeyError(f"Unknown object property: {object_property}")
        return hint

    def join_sql(
        self,
        object_property: str,
        from_alias: str = "f",
        to_alias: str = "a",
    ) -> str:
        """Runtime JOIN ON clause for an ontology object property."""
        hint = self.join_hint(object_property)
        to_table = self.table_for_class(hint["to_class"])
        return (
            f"JOIN {to_table.qualified} {to_alias} "
            f"ON {from_alias}.{hint['from_column']} = {to_alias}.{hint['to_column']}"
        )

    def time_window_sql(self, crs_deptime_col: str = "crsdeptime") -> str:
        return sql_time_window_expr(crs_deptime_col, self.business_rules)

    def flight_status_sql(self) -> str:
        return sql_flight_status_expr(self.business_rules)

    def delay_severity_sql(self) -> str:
        return sql_delay_severity_expr(self.business_rules)

    def primary_delay_reason_sql(self) -> str:
        return sql_primary_delay_reason_expr(self.business_rules)

    def route_sql(self) -> str:
        return sql_route_expr()

    def flight_runtime_from(self, alias: str = "f") -> str:
        """
        FROM clause: flights_orc wrapped with business-rule CASE expressions.

        This is the primary path — no Hive view, all semantics compiled at runtime.
        """
        return sql_runtime_flight_subquery(
            database=self.database,
            source_table=PREFERRED_TABLES["Flight"],
            alias=alias,
            rules=self.business_rules,
        )

    def hub_airports_sql(self, year: Optional[int] = None, top_n: Optional[int] = None) -> str:
        logistics = self.business_rules.get("logistics", {}).get("hub_airport", {})
        return sql_hub_airports_subquery(
            database=self.database,
            flights_table=PREFERRED_TABLES["Flight"],
            reference_year=year or logistics.get("default_reference_year", 2008),
            top_n=top_n or logistics.get("default_top_n", 20),
        )

    def describe_materialized_layer(self) -> List[Dict[str, str]]:
        rows = []
        for class_label in ("Flight", "Airline", "Airport", "Plane"):
            pt = self.table_for_class(class_label)
            rows.append(
                {
                    "ontology_class": class_label,
                    "class_uri": pt.class_uri,
                    "physical_table": pt.qualified,
                }
            )
        return rows

    def describe_runtime_layer(self) -> List[Dict[str, str]]:
        return [
            {
                "ontology_property": prop,
                "runtime_column": col,
                "compiled_from": "config/airline_business_rules.yaml",
            }
            for prop, col in RUNTIME_FLIGHT_PROPERTIES.items()
        ]

    def list_business_classes(self) -> List[str]:
        return sorted(self._class_uri_by_label.keys())
