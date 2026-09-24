#!/usr/bin/env python3
"""
Run ontology-first XUnternehmen KDM analytics against Hive/Iceberg (xunternehmen DB).

Resolves KDM classes (JuristischePerson, Anschrift, WirtschaftlicheTaetigkeit, …)
via xunternehmen_kg.json + xunternehmen_r2rml_db_mapping.yaml, then executes SQL
through impyla (HIVE_* env, same as kdm/hive/run_hive_sql.py).

Usage:
  export HIVE_DATABASE=xunternehmen HIVE_HOST=... HIVE_USER=... HIVE_PASSWORD=...
  python examples/xunternehmen_ontology_analytics_demo.py
  python examples/xunternehmen_ontology_analytics_demo.py --demo 3 --print-sql-only
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

from xunternehmen_ontology_resolver import DEFAULT_DATABASE, XUnternehmenOntologyResolver

GRAPH_PATH = REPO / "kdm" / "xunternehmen_kg_with_decisions.json"
FALLBACK_GRAPH = REPO / "kdm" / "xunternehmen_kg.json"


def load_mcp_env() -> None:
    mcp = REPO / ".cursor" / "mcp.json"
    if not mcp.is_file():
        hive_env = REPO / "kdm" / "hive" / "hive.env.local"
        if hive_env.is_file():
            for line in hive_env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"'))
        return
    payload = json.loads(mcp.read_text())
    for server in (payload.get("mcpServers") or {}).values():
        for key, value in (server.get("env") or {}).items():
            if key.startswith("HIVE_") or key.startswith("SEMANTICA_"):
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


def demo_1_jp_register_completeness(resolver: XUnternehmenOntologyResolver) -> None:
    """Share of JuristischePerson with Eintragung and Sitz (RegisterEingetragen + HatSitz)."""
    jp = resolver.table_for_class("JuristischePerson")
    name = resolver.column_for_property("JuristischePerson", "eingetragenerName")
    ze_join, zs_join, _ze = resolver.jp_register_links_sql("jp")

    sql = f"""
SELECT
  COUNT(*) AS juristische_personen,
  SUM(CASE WHEN ze.eintragung_id IS NOT NULL THEN 1 ELSE 0 END) AS mit_eintragung,
  SUM(CASE WHEN zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END) AS mit_sitz,
  SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END) AS vollstaendig_register,
  ROUND(
    100.0 * SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0),
    1
  ) AS pct_vollstaendig
FROM {jp.qualified} jp
{ze_join}
{zs_join}
WHERE jp.{name.column} IS NOT NULL
"""
    note = (
        f"JuristischePerson.eingetragenerName → {name.qualified}; "
        "RegisterEingetragen/HatSitz via zuordnung_eintragung + zuordnung_sitz"
    )
    _print_result("Demo 1 — Register completeness (JuristischePerson)", note, sql, _hive_query(sql))


def demo_2_np_geburt_coverage(resolver: XUnternehmenOntologyResolver) -> None:
    """Natürliche Personen with vs. without linked Geburt."""
    np = resolver.table_for_class("NatuerlichePerson")
    geb = resolver.table_for_class("Geburt")
    geschlecht = resolver.column_for_property("NatuerlichePerson", "geschlechtCode")
    geb_join = resolver.join_sql("geburt", from_alias="np", to_alias="g")

    sql = f"""
SELECT
  COUNT(*) AS natuerliche_personen,
  SUM(CASE WHEN g.id IS NOT NULL THEN 1 ELSE 0 END) AS mit_geburt,
  SUM(CASE WHEN g.id IS NULL THEN 1 ELSE 0 END) AS ohne_geburt,
  ROUND(100.0 * SUM(CASE WHEN g.id IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS pct_mit_geburt
FROM {np.qualified} np
{geb_join}
WHERE np.{geschlecht.column} IS NOT NULL
"""
    note = (
        f"NatuerlichePerson.geburt → LEFT JOIN {geb.qualified}; "
        f"geschlechtCode → {geschlecht.qualified}"
    )
    _print_result("Demo 2 — Geburt coverage (NatuerlichePerson)", note, sql, _hive_query(sql))


def demo_3_anschrift_subtypes(resolver: XUnternehmenOntologyResolver) -> None:
    """Distribution of Anschrift subtypes (runtime anschriftSubtype)."""
    ans = resolver.table_for_class("Anschrift")
    subtype_expr = resolver.anschrift_subtype_sql("a")

    sql = f"""
SELECT
  {subtype_expr} AS anschrift_subtype,
  COUNT(*) AS anschrift_count
FROM {ans.qualified} a
GROUP BY {subtype_expr}
ORDER BY anschrift_count DESC
"""
    note = (
        f"Anschrift.anschriftSubtype (runtime CASE on anschrift_typ) → {ans.qualified}; "
        "rules: config/xunternehmen_business_rules.yaml anschrift_type_rules"
    )
    _print_result("Demo 3 — Anschrift subtype distribution", note, sql, _hive_query(sql))


def demo_4_pg_gesellschafter(resolver: XUnternehmenOntologyResolver) -> None:
    """Personengesellschaften by number of Gesellschafter roles."""
    pg = resolver.table_for_class("RechtsfaehigePersonengesellschaft")
    gs = resolver.table_for_class("Gesellschafter")
    name = resolver.column_for_property("RechtsfaehigePersonengesellschaft", "eingetragenerName")
    art = resolver.column_for_property("Gesellschafter", "artGesellschafterCode")

    sql = f"""
SELECT
  pg.{name.column} AS personengesellschaft,
  COUNT(rg.id) AS gesellschafter_count,
  COUNT(DISTINCT rg.{art.column}) AS art_codes
FROM {pg.qualified} pg
LEFT JOIN {gs.qualified} rg ON rg.personengesellschaft_id = pg.id
GROUP BY pg.id, pg.{name.column}
HAVING COUNT(rg.id) > 0
ORDER BY gesellschafter_count DESC
LIMIT 10
"""
    note = (
        f"RechtsfaehigePersonengesellschaft.gesellschafter → {gs.qualified}; "
        f"artGesellschafterCode → {art.qualified}"
    )
    _print_result("Demo 4 — Top Personengesellschaften by Gesellschafter count", note, sql, _hive_query(sql))


def demo_5_wt_betriebsstaette_wz(resolver: XUnternehmenOntologyResolver) -> None:
    """Wirtschaftliche Tätigkeit with Hauptbetriebsstaette and Wirtschaftszweig."""
    wt = resolver.table_for_class("WirtschaftlicheTaetigkeit")
    bs = resolver.table_for_class("Betriebsstaette")
    wz = resolver.table_for_class("Wirtschaftszweig")
    taetigkeit = resolver.column_for_property("WirtschaftlicheTaetigkeit", "taetigkeit")
    bs_art = resolver.column_for_property("Betriebsstaette", "artBetriebsstaetteCode")
    wz_key = resolver.column_for_property("Wirtschaftszweig", "wirtschaftszweigschluessel")

    sql = f"""
SELECT
  wt.{taetigkeit.column} AS taetigkeit,
  MAX(CASE WHEN bs.{bs_art.column} = '01' THEN 1 ELSE 0 END) AS hat_hauptbetriebsstaette,
  MAX(wz.{wz_key.column}) AS wirtschaftszweig,
  COUNT(DISTINCT bs.id) AS betriebsstaetten,
  COUNT(DISTINCT wz.id) AS wirtschaftszweige
FROM {wt.qualified} wt
LEFT JOIN {bs.qualified} bs ON bs.wirtschaftliche_taetigkeit_id = wt.id
LEFT JOIN {wz.qualified} wz ON wz.wirtschaftliche_taetigkeit_id = wt.id
WHERE wt.{taetigkeit.column} IS NOT NULL
GROUP BY wt.id, wt.{taetigkeit.column}
HAVING MAX(CASE WHEN bs.{bs_art.column} = '01' THEN 1 ELSE 0 END) = 1
  AND COUNT(DISTINCT wz.id) >= 1
ORDER BY betriebsstaetten DESC
LIMIT 10
"""
    note = (
        f"WirtschaftlicheTaetigkeit.betriebsstaette → {bs.qualified}; "
        f"wirtschaftszweig → {wz.qualified}; artBetriebsstaetteCode '01' = Hauptbetriebsstaette"
    )
    _print_result("Demo 5 — WT with Hauptbetriebsstaette + WZ", note, sql, _hive_query(sql))


def demo_6_jp_data_quality_tiers(resolver: XUnternehmenOntologyResolver) -> None:
    """Runtime data quality tiers for JuristischePerson (business rules)."""
    jp = resolver.table_for_class("JuristischePerson")
    tier_expr = resolver.jp_data_quality_tier_sql("jp")
    ze_join, zs_join, _ = resolver.jp_register_links_sql("jp")

    sql = f"""
SELECT
  {tier_expr} AS data_quality_tier,
  COUNT(*) AS entity_count
FROM {jp.qualified} jp
{ze_join}
{zs_join}
GROUP BY {tier_expr}
ORDER BY entity_count DESC
"""
    note = (
        "Runtime dataQualityTier CASE (TierA_Vollstaendig / TierB_Teilweise / TierC_Minimal); "
        "compiled from xunternehmen_business_rules.yaml data_quality_tier_rules"
    )
    _print_result("Demo 6 — Data quality tiers (JuristischePerson)", note, sql, _hive_query(sql))


DEMOS = {
    1: demo_1_jp_register_completeness,
    2: demo_2_np_geburt_coverage,
    3: demo_3_anschrift_subtypes,
    4: demo_4_pg_gesellschafter,
    5: demo_5_wt_betriebsstaette_wz,
    6: demo_6_jp_data_quality_tiers,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ontology-first XUnternehmen KDM analytics")
    parser.add_argument(
        "--graph",
        default=str(GRAPH_PATH if GRAPH_PATH.is_file() else FALLBACK_GRAPH),
        help="Path to xunternehmen_kg.json or xunternehmen_kg_with_decisions.json",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("HIVE_DATABASE", DEFAULT_DATABASE),
        help="Hive database (default: xunternehmen)",
    )
    parser.add_argument("--demo", type=int, choices=sorted(DEMOS), help="Run single demo (1-6)")
    parser.add_argument("--list-layer", action="store_true", help="Show ontology→table map")
    parser.add_argument("--list-runtime", action="store_true", help="Show runtime-derived properties")
    parser.add_argument(
        "--print-sql-only",
        action="store_true",
        help="Print SQL without executing Hive queries",
    )
    args = parser.parse_args()
    load_mcp_env()

    graph = ContextGraph()
    graph.load_from_file(args.graph)
    resolver = XUnternehmenOntologyResolver(graph, database=args.database)

    if args.list_layer:
        print(json.dumps(resolver.describe_materialized_layer(), indent=2))
        return 0

    if args.list_runtime:
        print(json.dumps(resolver.describe_runtime_layer(), indent=2))
        return 0

    print("Physical layer (Hive/Iceberg):")
    for row in resolver.describe_materialized_layer():
        print(f"  {row['ontology_class']:32} → {row['physical_table']}")
    print("Runtime layer (SQL compiled from xunternehmen_business_rules.yaml):")
    for row in resolver.describe_runtime_layer():
        print(f"  {row['ontology_property']:24} → {row['runtime_column']}")

    if args.print_sql_only:
        def _noop(sql: str) -> dict:
            return {"skipped": True, "reason": "print-sql-only"}

        global _hive_query
        orig = _hive_query
        _hive_query = _noop
        try:
            to_run = [args.demo] if args.demo else sorted(DEMOS)
            for n in to_run:
                DEMOS[n](resolver)
        finally:
            _hive_query = orig
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
