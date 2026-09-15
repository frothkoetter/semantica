#!/usr/bin/env python3
"""
Run ontology-first airline analytics against Hive materialized tables.

Resolves ontology terms (Flight, Airline, arrDelay, operatedBy, …) to
flights / airlines / airports / planes via airline_graph.json, then
executes SQL through impyla (same HIVE_* env as iceberg-mcp-server-hive).

Usage:
  export HIVE_DATABASE=airlinedata HIVE_HOST=... HIVE_USER=... HIVE_PASSWORD=...
  python examples/airline_ontology_analytics_demo.py
  python examples/airline_ontology_analytics_demo.py --demo 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from semantica.context import ContextGraph

from airline_ontology_resolver import AirlineOntologyResolver, DEFAULT_DATABASE
GRAPH_PATH = REPO / "data" / "airline_graph.json"


def load_mcp_env() -> None:
    mcp = REPO / ".cursor" / "mcp.json"
    if not mcp.is_file():
        return
    payload = json.loads(mcp.read_text())
    for server in (payload.get("mcpServers") or {}).values():
        for key, value in (server.get("env") or {}).items():
            if key.startswith("HIVE_"):
                os.environ.setdefault(key, str(value))


def _hive_query(sql: str) -> dict:
    from semantica.mcp_server.hive_schema import get_hive_connection

    conn = get_hive_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        cur.close()
        return {"columns": cols, "rows": rows}
    finally:
        conn.close()


def _print_result(title: str, resolver_note: str, sql: str, result: dict) -> None:
    print(f"\n{'=' * 72}")
    print(title)
    print(f"{'-' * 72}")
    print("Ontology resolution:")
    print(f"  {resolver_note}")
    print("SQL (physical):")
    print(sql.strip())
    print("Result:")
    print(json.dumps(result, indent=2, default=str))


def demo_1_carrier_delays(resolver: AirlineOntologyResolver) -> None:
    """Which airlines had the highest average arrival delay in 2008?"""
    flight = resolver.table_for_class("Flight")
    airline = resolver.table_for_class("Airline")
    arr_delay = resolver.column_for_property("Flight", "arrDelay")
    carrier = resolver.column_for_property("Flight", "uniqueCarrier")
    code = resolver.column_for_property("Airline", "airlineCode")
    name = resolver.column_for_property("Airline", "description")
    join = resolver.join_hint("operatedBy")

    sql = f"""
SELECT
  a.{name.column} AS airline_name,
  a.{code.column} AS airline_code,
  ROUND(AVG(f.{arr_delay.column}), 1) AS avg_arr_delay_min,
  COUNT(*) AS flight_count
FROM {flight.qualified} f
JOIN {airline.qualified} a
  ON f.{join['from_column']} = a.{join['to_column']}
WHERE f.year = 2008
  AND f.{arr_delay.column} IS NOT NULL
  AND f.cancelled = 0
GROUP BY a.{code.column}, a.{name.column}
HAVING COUNT(*) >= 5000
ORDER BY avg_arr_delay_min DESC
LIMIT 5
"""
    note = (
        f"Flight.{arr_delay.property_label} → {arr_delay.qualified}; "
        f"Flight.operatedBy → JOIN {airline.qualified} ON uniquecarrier = code"
    )
    _print_result("Demo 1 — Carrier arrival delays (2008)", note, sql, _hive_query(sql))


def demo_2_route_volume(resolver: AirlineOntologyResolver) -> None:
    """Busiest routes from LAX in 2007."""
    flight = resolver.table_for_class("Flight")
    origin = resolver.column_for_property("Flight", "origin")
    dest = resolver.column_for_property("Flight", "dest")

    sql = f"""
SELECT
  f.{origin.column} AS origin_iata,
  f.{dest.column} AS dest_iata,
  COUNT(*) AS flight_count
FROM {flight.qualified} f
WHERE f.year = 2007
  AND f.{origin.column} = 'LAX'
GROUP BY f.{origin.column}, f.{dest.column}
ORDER BY flight_count DESC
LIMIT 5
"""
    note = (
        f"Flight.originAirport (origin) → {origin.qualified}; "
        f"Flight.destinationAirport (dest) → {dest.qualified}"
    )
    _print_result("Demo 2 — Top routes from LAX (2007)", note, sql, _hive_query(sql))


def demo_3_manufacturer_mix(resolver: AirlineOntologyResolver) -> None:
    """Which aircraft manufacturers fly the most segments?"""
    flight = resolver.table_for_class("Flight")
    plane = resolver.table_for_class("Plane")
    manufacturer = resolver.column_for_property("Plane", "manufacturer")
    join = resolver.join_hint("assignedAircraft")

    sql = f"""
SELECT
  p.{manufacturer.column} AS manufacturer,
  COUNT(*) AS flight_segments
FROM {flight.qualified} f
JOIN {plane.qualified} p
  ON f.{join['from_column']} = p.{join['to_column']}
WHERE f.year = 2008
  AND p.{manufacturer.column} IS NOT NULL
  AND p.{manufacturer.column} <> ''
GROUP BY p.{manufacturer.column}
ORDER BY flight_segments DESC
LIMIT 5
"""
    note = (
        f"Flight.assignedAircraft → JOIN {plane.qualified} ON tailnum; "
        f"Plane.manufacturer → {manufacturer.qualified}"
    )
    _print_result("Demo 3 — Manufacturer flight volume (2008)", note, sql, _hive_query(sql))


def demo_4_delay_causes(resolver: AirlineOntologyResolver) -> None:
    """Carrier vs weather delay totals for major carriers."""
    flight = resolver.table_for_class("Flight")
    airline = resolver.table_for_class("Airline")
    carrier = resolver.column_for_property("Flight", "uniqueCarrier")
    carrier_delay = resolver.column_for_property("Flight", "carrierDelay")
    weather_delay = resolver.column_for_property("Flight", "weatherDelay")
    code = resolver.column_for_property("Airline", "airlineCode")
    name = resolver.column_for_property("Airline", "description")
    join = resolver.join_hint("operatedBy")

    sql = f"""
SELECT
  a.{name.column} AS airline_name,
  SUM(COALESCE(f.{carrier_delay.column}, 0)) AS total_carrier_delay_min,
  SUM(COALESCE(f.{weather_delay.column}, 0)) AS total_weather_delay_min
FROM {flight.qualified} f
JOIN {airline.qualified} a
  ON f.{join['from_column']} = a.{join['to_column']}
WHERE f.year = 2008
  AND f.{carrier_delay.column} IS NOT NULL
  AND f.{weather_delay.column} IS NOT NULL
  AND f.{carrier.column} IN ('WN', 'AA', 'DL', 'UA', 'US')
GROUP BY a.{code.column}, a.{name.column}
ORDER BY total_carrier_delay_min DESC
"""
    note = (
        f"Flight.carrierDelay / weatherDelay → "
        f"{carrier_delay.qualified}, {weather_delay.qualified}; "
        f"filtered via Flight.operatedBy → {airline.qualified}"
    )
    _print_result("Demo 4 — Delay cause comparison (majors, 2008)", note, sql, _hive_query(sql))


def demo_5_otp_by_time_window(resolver: AirlineOntologyResolver) -> None:
    """On-time performance by TimeWindow (runtime SQL on flights)."""
    flight_from = resolver.flight_runtime_from()
    status = resolver.column_for_property("Flight", "flightStatus")
    window = resolver.column_for_property("Flight", "scheduledInWindowClass")

    sql = f"""
SELECT
  f.{window.column} AS time_window,
  ROUND(
    100.0 * SUM(CASE WHEN f.{status.column} = 'OnTimeFlight' THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN f.{status.column} IN ('OnTimeFlight','DelayedFlight') THEN 1 ELSE 0 END), 0),
    1
  ) AS otp_pct,
  COUNT(*) AS flight_count
FROM {flight_from}
WHERE f.year = 2008
GROUP BY f.{window.column}
ORDER BY otp_pct ASC
"""
    note = (
        "Runtime: flights + CASE rules → flightStatus, scheduledInWindowClass; "
        "KPI OnTimePerformance (ontology: OnTimeFlight / TimeWindow)"
    )
    _print_result("Demo 5 — OTP by business hour band (2008)", note, sql, _hive_query(sql))


def demo_6_primary_delay_reason(resolver: AirlineOntologyResolver) -> None:
    """Delay attribution share by primaryDelayReason."""
    flight_from = resolver.flight_runtime_from()
    reason = resolver.column_for_property("Flight", "primaryDelayReason")
    status = resolver.column_for_property("Flight", "flightStatus")

    sql = f"""
SELECT
  f.{reason.column} AS delay_reason,
  COUNT(*) AS delayed_flights,
  ROUND(AVG(f.arrdelay), 1) AS avg_arr_delay_min
FROM {flight_from}
WHERE f.year = 2008
  AND f.{status.column} = 'DelayedFlight'
  AND f.{reason.column} IS NOT NULL
GROUP BY f.{reason.column}
ORDER BY delayed_flights DESC
"""
    note = (
        "Runtime primaryDelayReason CASE on flights; "
        "filter DelayedFlight via flight_status"
    )
    _print_result("Demo 6 — Primary delay reason mix (2008)", note, sql, _hive_query(sql))


def demo_7_hub_route_logistics(resolver: AirlineOntologyResolver) -> None:
    """Worst OTP routes from hub airports (logistics)."""
    flight_from = resolver.flight_runtime_from()
    route = resolver.column_for_property("Flight", "routeId")
    status = resolver.column_for_property("Flight", "flightStatus")
    hubs = resolver.hub_airports_sql(year=2008, top_n=10)

    sql = f"""
WITH hubs AS ({hubs})
SELECT
  f.{route.column} AS route_id,
  f.origin AS origin_iata,
  ROUND(
    100.0 * SUM(CASE WHEN f.{status.column} = 'OnTimeFlight' THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN f.{status.column} IN ('OnTimeFlight','DelayedFlight') THEN 1 ELSE 0 END), 0),
    1
  ) AS otp_pct,
  COUNT(*) AS flights
FROM {flight_from}
INNER JOIN hubs h ON f.origin = h.iata
WHERE f.year = 2008
GROUP BY f.{route.column}, f.origin
HAVING COUNT(*) >= 1000
ORDER BY otp_pct ASC
LIMIT 5
"""
    note = (
        "Runtime: hub CTE + flight subquery + JOIN; "
        "Route.routeId + HubAirport + OnTimePerformance"
    )
    _print_result("Demo 7 — Lowest OTP hub routes (2008)", note, sql, _hive_query(sql))


DEMOS = {
    1: demo_1_carrier_delays,
    2: demo_2_route_volume,
    3: demo_3_manufacturer_mix,
    4: demo_4_delay_causes,
    5: demo_5_otp_by_time_window,
    6: demo_6_primary_delay_reason,
    7: demo_7_hub_route_logistics,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ontology-first airline analytics demos")
    parser.add_argument(
        "--graph",
        default=str(GRAPH_PATH),
        help="Path to airline_graph.json",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("HIVE_DATABASE", DEFAULT_DATABASE),
        help="Hive database (default: airlinedata)",
    )
    parser.add_argument(
        "--demo",
        type=int,
        choices=sorted(DEMOS),
        help="Run a single demo (1-4); default: all",
    )
    parser.add_argument("--list-layer", action="store_true", help="Show ontology→table map")
    parser.add_argument(
        "--list-runtime",
        action="store_true",
        help="Show ontology properties compiled at query time",
    )
    parser.add_argument(
        "--print-sql-only",
        action="store_true",
        help="Print generated SQL without executing Hive queries",
    )
    args = parser.parse_args()
    load_mcp_env()

    graph = ContextGraph()
    graph.load_from_file(args.graph)
    resolver = AirlineOntologyResolver(graph, database=args.database)

    if args.list_layer:
        print(json.dumps(resolver.describe_materialized_layer(), indent=2))
        return 0

    if args.list_runtime:
        print(json.dumps(resolver.describe_runtime_layer(), indent=2))
        return 0

    print("Physical layer (Hive):")
    for row in resolver.describe_materialized_layer():
        print(f"  {row['ontology_class']:8} → {row['physical_table']}")
    print("Runtime layer (SQL compiled from airline_business_rules.yaml):")
    for row in resolver.describe_runtime_layer():
        print(f"  {row['ontology_property']:24} → {row['runtime_column']}")

    if args.print_sql_only:
        global _hive_query

        def _noop_query(sql: str) -> dict:
            return {"skipped": True, "reason": "print-sql-only"}

        _orig = _hive_query
        _hive_query = _noop_query
        try:
            to_run = [args.demo] if args.demo else sorted(DEMOS)
            for n in to_run:
                DEMOS[n](resolver)
        finally:
            _hive_query = _orig
        return 0

    to_run = [args.demo] if args.demo else sorted(DEMOS)
    for n in to_run:
        DEMOS[n](resolver)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
