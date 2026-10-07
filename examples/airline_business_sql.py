"""SQL expression builders from config/airline_business_rules.yaml (airline demo only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPO / "config" / "airline_business_rules.yaml"


def load_business_rules(path: Optional[str] = None) -> Dict[str, Any]:
    """Load business rules + merged airline_kpi_catalog.yaml when present."""
    from semantica.mcp_server.business_rules import load_business_rules as _load

    config_path = str(path) if path else str(DEFAULT_RULES_PATH)
    return _load(config_path)


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


def sql_otp_expr(
    rules: Optional[Dict[str, Any]] = None,
    alias: Optional[str] = None,
) -> str:
    """OTP percentage (ontology class OTP / OnTimePerformance) from business rules."""
    cfg = rules or load_business_rules()
    otp = cfg.get("otp") or {}
    sql_cfg = otp.get("sql") or {}
    expr = sql_cfg.get("expr")
    if not expr:
        threshold = (cfg.get("thresholds") or {}).get("on_time_max_delay", 15)
        expr = (
            f"ROUND(100.0 * SUM(CASE WHEN cancelled = 0 "
            f"AND COALESCE(arrdelay,0) <= {threshold} "
            f"AND COALESCE(depdelay,0) <= {threshold} THEN 1 ELSE 0 END) "
            f"/ NULLIF(SUM(CASE WHEN cancelled = 0 THEN 1 ELSE 0 END), 0), 2)"
        )
    out_alias = alias or sql_cfg.get("alias") or "otp_pct"
    return f"{expr} AS {out_alias}"


def sql_otp_having_min_completed(
    rules: Optional[Dict[str, Any]] = None,
) -> int:
    """Minimum completed flights for OTP rankings (HAVING clause guidance)."""
    cfg = rules or load_business_rules()
    otp = cfg.get("otp") or {}
    return int(otp.get("default_having_min_completed") or 1000)


def list_kpi_catalog(rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return merged KPI catalog from business rules."""
    cfg = rules or load_business_rules()
    return cfg.get("kpi_catalog") or {}


def sql_kpi_expr(
    kpi_class: str,
    rules: Optional[Dict[str, Any]] = None,
    alias: Optional[str] = None,
) -> str:
    """Build SELECT expression for a named KPI class (e.g. SevereDelayRate, D0DepartureOTP)."""
    cfg = rules or load_business_rules()
    catalog = (cfg.get("kpi_catalog") or {}).get("kpis") or {}
    spec = catalog.get(kpi_class)
    if not spec:
        raise KeyError(f"KPI '{kpi_class}' not in kpi_catalog ({len(catalog)} defined)")
    sql_cfg = spec.get("sql") or {}
    expr = sql_cfg.get("expr")
    if not expr:
        raise ValueError(f"KPI '{kpi_class}' has no sql.expr")
    out_alias = alias or sql_cfg.get("alias") or kpi_class
    return f"{expr.strip()} AS {out_alias}"


def resolve_kpi_by_alias(
    term: str,
    rules: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Map user term (D0, ASM, cancellation rate) → KPI class name."""
    needle = term.strip().lower().replace(" ", "_").replace("-", "_")
    cfg = rules or load_business_rules()
    catalog = (cfg.get("kpi_catalog") or {}).get("kpis") or {}
    for class_name, spec in catalog.items():
        if class_name.lower() == needle:
            return class_name
        labels = [spec.get("label_en", ""), spec.get("label_de", "")]
        labels.extend(spec.get("alt_labels") or [])
        for label in labels:
            norm = str(label).lower().replace(" ", "_").replace("-", "_")
            if norm == needle:
                return class_name
    return None


def sql_runtime_flight_subquery(
    database: str = "airlinedata",
    source_table: str = "flights",
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


sql_enriched_flight_subquery = sql_runtime_flight_subquery


def sql_hub_airports_subquery(
    database: str = "airlinedata",
    flights_table: str = "flights",
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
