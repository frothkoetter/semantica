#!/usr/bin/env python3
"""
Record demo data-quality decisions on the XUnternehmen KG and export with decisions.

Loads kdm/xunternehmen_kg.json, ingests business rules, records sample
record_decision() entries (tiers, register completeness, Vorgang readiness),
links causal chains, and saves kdm/xunternehmen_kg_with_decisions.json.

Usage:
  .venv/bin/python kdm/record_xunternehmen_decisions.py
  .venv/bin/python kdm/record_xunternehmen_decisions.py --compare

MCP (absolute paths):
  SEMANTICA_KG_PATH=.../kdm/xunternehmen_kg_with_decisions.json
  SEMANTICA_BUSINESS_RULES=.../config/xunternehmen_business_rules.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
KDM = REPO / "kdm"
KG_IN = KDM / "xunternehmen_kg.json"
KG_OUT = KDM / "xunternehmen_kg_with_decisions.json"
RULES = REPO / "config" / "xunternehmen_business_rules.yaml"
NS = "https://w3id.org/kdm/"


def entity_uri(cls: str, row_id: str) -> str:
    return f"{NS}{cls}/{row_id}"


def rebuild_decision_index(graph: Any) -> int:
    """
    Rebuild in-memory _decisions from persisted decision nodes.

    load_from_file() does not restore _decisions; this enables find_precedents
    after reloading a graph JSON that contains decision nodes.
    """
    graph._decisions = {}
    graph._decision_index = defaultdict(set)
    graph._entity_index = defaultdict(set)
    graph._temporal_index = []

    count = 0
    for node in graph.find_nodes(node_type="decision"):
        if isinstance(node, dict):
            props = dict(node.get("metadata") or {})
            decision_id = str(node.get("id", ""))
            content = node.get("content") or props.get("content") or ""
        else:
            props = {}
            if hasattr(node, "properties"):
                props.update(node.properties or {})
            if hasattr(node, "metadata"):
                props.update(node.metadata or {})
            decision_id = str(getattr(node, "node_id", ""))
            content = getattr(node, "content", "") or props.get("content", "")

        if not decision_id:
            continue

        entities: list[str] = []
        for edge in graph.edges:
            if edge.source_id == decision_id and edge.edge_type == "involves":
                entities.append(edge.target_id)

        ts = props.get("timestamp") or 0.0
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            ts = 0.0

        record = {
            "id": decision_id,
            "category": props.get("category", ""),
            "scenario": props.get("scenario") or content,
            "reasoning": props.get("reasoning", ""),
            "outcome": props.get("outcome", ""),
            "confidence": float(props.get("confidence", 0.0) or 0.0),
            "entities": entities,
            "decision_maker": props.get("decision_maker"),
            "timestamp": ts,
            "recorded_at": props.get("recorded_at"),
            "valid_from": props.get("valid_from"),
            "valid_until": props.get("valid_until"),
            "metadata": {
                k: v
                for k, v in props.items()
                if k
                not in {
                    "category",
                    "scenario",
                    "reasoning",
                    "outcome",
                    "confidence",
                    "decision_maker",
                    "timestamp",
                    "recorded_at",
                    "valid_from",
                    "valid_until",
                    "content",
                }
            },
        }
        graph._decisions[decision_id] = record
        if record["category"]:
            graph._decision_index[record["category"]].add(decision_id)
        for ent in entities:
            graph._entity_index[ent].add(decision_id)
        graph._temporal_index.append((decision_id, ts))
        count += 1

    graph._temporal_index.sort(key=lambda x: x[1], reverse=True)
    return count


def record_demo_decisions(graph: Any) -> dict[str, str]:
    """Record representative KDM data-quality and Vorgang decisions."""
    ids: dict[str, str] = {}

    ids["np_tier_a"] = graph.record_decision(
        category="data_quality_tier",
        scenario="Natürliche Person np-000042: Name, Geburt, Geschlecht, Anschrift und Kommunikation vorhanden",
        reasoning="Alle Pflicht-KDM-Blöcke für NatuerlichePerson erfüllt (Tier-A-Kriterien)",
        outcome="TierA_Vollstaendig",
        confidence=0.94,
        entities=[entity_uri("NatuerlichePerson", "np-000042")],
        decision_maker="kdm_quality_agent",
    )

    ids["np_tier_b"] = graph.record_decision(
        category="data_quality_tier",
        scenario="Natürliche Person np-001287: Name vorhanden, Geburt fehlt, Geschlecht gesetzt",
        reasoning="Kernidentifikation ok, sekundärer KDM-Block Geburt fehlt",
        outcome="TierB_Teilweise",
        confidence=0.88,
        entities=[entity_uri("NatuerlichePerson", "np-001287")],
        decision_maker="kdm_quality_agent",
    )

    ids["jp_tier_b"] = graph.record_decision(
        category="register_completeness",
        scenario="Juristische Person jp-000519: eingetragener Name und BWN vorhanden, keine Eintragung im Register",
        reasoning="RegisterEingetragen-Regel nicht erfüllt; Sitz ebenfalls nicht verknüpft",
        outcome="TierB_Teilweise",
        confidence=0.91,
        entities=[entity_uri("JuristischePerson", "jp-000519")],
        decision_maker="kdm_quality_agent",
    )

    ids["jp_tier_a"] = graph.record_decision(
        category="register_completeness",
        scenario="Juristische Person jp-000003: Name, BWN, Eintragung HRB und Sitz Bremen verknüpft",
        reasoning="VollstaendigeOrganisation: Eintragung + Sitz + Identifikatoren vollständig",
        outcome="TierA_Vollstaendig",
        confidence=0.96,
        entities=[entity_uri("JuristischePerson", "jp-000003")],
        decision_maker="kdm_quality_agent",
    )

    ids["wt_tier_a"] = graph.record_decision(
        category="wirtschaftliche_taetigkeit",
        scenario="Wirtschaftliche Tätigkeit wt-000112: BWN, Hauptbetriebsstätte (01), WZ2008-Klassifikation",
        reasoning="HatHauptbetriebsstaette und HatWirtschaftszweig erfüllt",
        outcome="TierA_Vollstaendig",
        confidence=0.93,
        entities=[entity_uri("WirtschaftlicheTaetigkeit", "wt-000112")],
        decision_maker="kdm_quality_agent",
    )

    ids["pg_tier_c"] = graph.record_decision(
        category="data_quality_tier",
        scenario="Personengesellschaft pg-000891: nur eingetragener Name, kein Gesellschafter, keine Eintragung",
        reasoning="Minimale Kerndaten; Rollen- und Register-Blöcke fehlen",
        outcome="TierC_Minimal",
        confidence=0.87,
        entities=[entity_uri("RechtsfaehigePersonengesellschaft", "pg-000891")],
        decision_maker="kdm_quality_agent",
    )

    ids["antrag_ok"] = graph.record_decision(
        category="vorgang_readiness",
        scenario="Antrag an-000045: Antragsteller (JP) und Handelnde Person verknüpft, Registerdaten des Antragstellers vollständig",
        reasoning="AntragEinreichbar-Regel erfüllt; Referenz jp-000003 als vollständig klassifiziert",
        outcome="AntragEinreichbar",
        confidence=0.92,
        entities=[
            entity_uri("Antrag", "an-000045"),
            entity_uri("JuristischePerson", "jp-000003"),
        ],
        decision_maker="kdm_vorgang_agent",
    )

    ids["antrag_block"] = graph.record_decision(
        category="vorgang_readiness",
        scenario="Antrag an-001902: Antragsteller jp-000519 ohne Register-Eintragung",
        reasoning="Antragsteller hat TierB_Teilweise — Einreichung blockiert bis Registerdaten nachgereicht",
        outcome="AntragBlockiert_RegisterUnvollstaendig",
        confidence=0.89,
        entities=[
            entity_uri("Antrag", "an-001902"),
            entity_uri("JuristischePerson", "jp-000519"),
        ],
        decision_maker="kdm_vorgang_agent",
    )

    # Causal: register assessment → vorgang outcome
    graph.add_causal_relationship(ids["jp_tier_b"], ids["antrag_block"], "CAUSED")
    graph.add_causal_relationship(ids["jp_tier_a"], ids["antrag_ok"], "INFLUENCED")

    return ids


def print_comparison(graph: Any) -> None:
    """Demonstrate precedent search and field comparison."""
    if not getattr(graph, "_decisions", None):
        rebuilt = rebuild_decision_index(graph)
        print(f"Rebuilt decision index from graph nodes ({rebuilt} decisions)")

    scenarios = [
        "Juristische Person ohne Eintragung im Handelsregister",
        "Natürliche Person mit fehlender Geburt",
    ]

    print("\n=== find_precedents (Vergleich ähnlicher Fälle) ===")
    for scenario in scenarios:
        precedents = graph.find_similar_decisions(scenario, max_results=3, min_similarity=0.05)
        print(f"\nSzenario: {scenario}")
        if not precedents:
            print("  (keine Treffer)")
            continue
        for idx, hit in enumerate(precedents, start=1):
            d = hit.get("decision") or hit
            sim = hit.get("similarity", d.get("similarity"))
            print(
                f"  {idx}. [{sim:.2f}] {d.get('outcome')} — {d.get('scenario', '')[:70]}..."
            )
            print(f"      reasoning: {str(d.get('reasoning', ''))[:90]}...")
            print(f"      confidence: {d.get('confidence')}  maker: {d.get('decision_maker')}")

    print("\n=== Kausale Kette (Antrag blockiert, upstream) ===")
    block_id = None
    for did, dec in graph._decisions.items():  # type: ignore[attr-defined]
        if dec.get("outcome") == "AntragBlockiert_RegisterUnvollstaendig":
            block_id = did
            break
    if block_id:
        chain = graph.get_causal_chain(block_id, direction="upstream", max_depth=5)
        for item in chain:
            outcome = getattr(item, "outcome", None)
            category = getattr(item, "category", "")
            depth = getattr(item, "metadata", {}).get("causal_distance", "?")
            if outcome is None and isinstance(item, dict):
                outcome = item.get("outcome")
                category = item.get("category", "")
            print(f"  ← [depth {depth}] {category} → {outcome}")
    else:
        print("  (kein blockierter Antrag gefunden)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record XUnternehmen demo decisions on KG")
    parser.add_argument("--input", default=str(KG_IN))
    parser.add_argument("--output", default=str(KG_OUT))
    parser.add_argument("--rules", default=str(RULES))
    parser.add_argument("--compare", action="store_true", help="Run precedent comparison demo")
    parser.add_argument(
        "--reload-demo",
        action="store_true",
        help="After save, reload JSON and rebuild index (simulates MCP restart)",
    )
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.is_file():
        print(f"Input KG not found: {inp}\nRun: .venv/bin/python kdm/build_kg.py", file=sys.stderr)
        return 1

    from semantica.context import ContextGraph
    from semantica.mcp_server.business_rules import ingest_business_rules_into_graph, load_business_rules

    graph = ContextGraph(advanced_analytics=True)
    graph.load_from_file(str(inp))
    base_nodes = graph.stats()["node_count"]
    print(f"Loaded {inp} ({base_nodes} nodes)")

    rules_path = Path(args.rules)
    if rules_path.is_file():
        rules = load_business_rules(str(rules_path))
        stats = ingest_business_rules_into_graph(graph, rules, source_path=str(rules_path))
        print(f"Business rules ingested: {json.dumps(stats)}")
    else:
        print(f"Warning: rules file missing: {rules_path}", file=sys.stderr)

    decision_ids = record_demo_decisions(graph)
    print(f"Recorded {len(decision_ids)} decisions")

    out = Path(args.output)
    graph.save_to_file(str(out))
    final_nodes = graph.stats()["node_count"]
    decision_nodes = len(graph.find_nodes(node_type="decision"))
    print(f"Saved {out} ({final_nodes} nodes, {decision_nodes} decision nodes)")

    print("\nDecision IDs:")
    for key, did in decision_ids.items():
        print(f"  {key}: {did}")

    from sync_upload_config import sync_upload_kdm_config

    uploaded = sync_upload_kdm_config()
    upload_dir = (REPO / "upload" / "kdm" / "config").resolve()
    print(f"\nSynced {len(uploaded)} file(s) to upload/kdm/config/")

    print("\nMCP env (deploy bundle):")
    print(f"  SEMANTICA_KG_PATH={upload_dir / 'xunternehmen_kg_with_decisions.json'}")
    print(f"  SEMANTICA_BUSINESS_RULES={upload_dir / 'xunternehmen_business_rules.yaml'}")
    print(f"  SEMANTICA_MAPPING_CONFIG={upload_dir / 'xunternehmen_r2rml_db_mapping.yaml'}")

    if args.reload_demo:
        from semantica.context import ContextGraph as CG

        reloaded = CG(advanced_analytics=True)
        reloaded.load_from_file(str(out))
        n = rebuild_decision_index(reloaded)
        print(f"\nReload demo: {n} decisions restored from {out.name}")
        print_comparison(reloaded)
    elif args.compare:
        print_comparison(graph)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
