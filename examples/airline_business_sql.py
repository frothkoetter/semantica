"""SQL expression builders from config/airline_business_rules.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPO / "config" / "airline_business_rules.yaml"


def load_business_rules(path: Optional[str] = None) -> Dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_RULES_PATH
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def sql_time_window_expr(
    crs_deptime_col: str = "crsdeptime",
    rules: Optional[Dict[str, Any]] = None,
    alias: str = "scheduled_in_window",
) -> str:
    """CASE expression mapping crsDepTime → TimeWindow ontology class name."""
    cfg = (rules or load_business_rules()).get("time_windows") or {}
    parts: List[str] = []
    for name, win in cfg.items():
        if win.get("wrap_midnight"):
            parts.append(
                f"WHEN {crs_deptime_col} >= {win['crs_deptime_min']} "
                f"OR {crs_deptime_col} <= {win['crs_deptime_max']} "
                f"THEN '{win.get('class', name)}'"
            )
        else:
            parts.append(
                f"WHEN {crs_deptime_col} BETWEEN {win['crs_deptime_min']} "
                f"AND {win['crs_deptime_max']} THEN '{win.get('class', name)}'"
            )
    body = "\n  ".join(parts)
    return f"CASE\n  {body}\n  ELSE 'Unknown'\nEND AS {alias}"


def sql_flight_status_expr(
    rules: Optional[Dict[str, Any]] = None,
    alias: str = "flight_status",
) -> str:
    """CASE for OnTimeFlight / DelayedFlight / CancelledFlight / DivertedFlight."""
    cfg = (rules or load_business_rules()).get("flight_status_rules") or []
    parts = [f"WHEN {rule['when']} THEN '{rule['class']}'" for rule in cfg]
    body = "\n  ".join(parts)
    return f"CASE\n  {body}\n  ELSE 'Flight'\nEND AS {alias}"


def sql_delay_severity_expr(
    rules: Optional[Dict[str, Any]] = None,
    alias: str = "delay_severity",
) -> str:
    cfg = (rules or load_business_rules()).get("delay_severity_rules") or []
    parts = [
        f"WHEN cancelled = 0 AND ({rule['when']}) THEN '{rule['class']}'"
        for rule in cfg
    ]
    body = "\n  ".join(parts)
    return f"CASE\n  {body}\n  ELSE NULL\nEND AS {alias}"


def sql_primary_delay_reason_expr(
    rules: Optional[Dict[str, Any]] = None,
    alias: str = "primary_delay_reason",
) -> str:
    """Argmax over DOT delay cause columns with YAML priority tie-break."""
    cfg = rules or load_business_rules()
    priority: List[str] = cfg.get("delay_reason_priority") or []
    columns: Dict[str, str] = cfg.get("delay_reason_columns") or {}
    parts: List[str] = []
    for reason_class in priority:
        col = columns.get(reason_class)
        if not col:
            continue
        conditions = [
            f"COALESCE({col}, 0) >= COALESCE({columns[r]}, 0)"
            for r in priority
            if columns.get(r)
        ]
        cond = " AND ".join(conditions)
        parts.append(
            f"WHEN cancelled = 0 AND COALESCE({col}, 0) > 0 AND ({cond}) "
            f"THEN '{reason_class}'"
        )
    body = "\n  ".join(parts)
    return f"CASE\n  {body}\n  ELSE NULL\nEND AS {alias}"


def sql_route_expr(
    origin_col: str = "origin",
    dest_col: str = "dest",
    alias: str = "route_id",
) -> str:
    return f"CONCAT({origin_col}, '-', {dest_col}) AS {alias}"


def sql_runtime_flight_subquery(
    database: str = "airlinedata",
    source_table: str = "flights_orc",
    alias: str = "f",
    rules: Optional[Dict[str, Any]] = None,
) -> str:
    """Compile business rules into an inline Flight subquery (no Hive view)."""
    r = rules or load_business_rules()
    return f"""(
  SELECT
    src.*,
    {sql_route_expr('origin', 'dest', 'route_id')},
    {sql_time_window_expr('crsdeptime', r, 'scheduled_in_window')},
    {sql_flight_status_expr(r, 'flight_status')},
    {sql_delay_severity_expr(r, 'delay_severity')},
    {sql_primary_delay_reason_expr(r, 'primary_delay_reason')}
  FROM {database}.{source_table} src
) {alias}"""


# Back-compat alias
sql_enriched_flight_subquery = sql_runtime_flight_subquery


def sql_hub_airports_subquery(
    database: str = "airlinedata",
    flights_table: str = "flights_orc",
    reference_year: int = 2008,
    top_n: int = 20,
) -> str:
    """Top-N origin airports by departures → HubAirport candidates."""
    return f"""
SELECT origin AS iata
FROM {database}.{flights_table}
WHERE year = {reference_year}
GROUP BY origin
ORDER BY COUNT(*) DESC
LIMIT {top_n}
"""
