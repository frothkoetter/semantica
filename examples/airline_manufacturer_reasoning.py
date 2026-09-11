#!/usr/bin/env python3
"""
Semantica reasoning trace for manufacturer segment + OTP analysis (2000-2008).

Loads analysis facts, applies forward-chaining rules (config/airline_manufacturer_reasoning.yaml),
records a decision on the ContextGraph, and exports a JSON reasoning report.

Usage:
  python examples/airline_manufacturer_reasoning.py
  python examples/airline_manufacturer_reasoning.py --graph data/airline_graph.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO = Path(__file__).resolve().parents[1]
RULES_PATH = REPO / "config" / "airline_manufacturer_reasoning.yaml"
DEFAULT_GRAPH = REPO / "data" / "airline_graph.json"
DEFAULT_OUTPUT = REPO / "data" / "airline_manufacturer_analysis_reasoning.json"

# Hive analysis results (2000-2008, ontology-resolved SQL)
SEGMENT_TOTALS = {
    "BOEING": 14_518_058,
    "EMBRAER": 5_176_326,
    "BOMBARDIER_INC": 4_735_636,
    "AIRBUS_INDUSTRIE": 3_733_463,
    "MCDONNELL_DOUGLAS": 2_717_289,
}

OTP_SNAPSHOT = {
    "BOEING": {2003: 81.7, 2007: 74.8},
    "EMBRAER": {2003: 84.1, 2007: 73.3},
    "BOMBARDIER_INC": {2003: 81.4, 2007: 70.9},
    "AIRBUS_INDUSTRIE": {2003: 81.6, 2007: 69.4},
    "MCDONNELL_DOUGLAS": {2003: 83.0, 2007: 70.5},
}

WEAK_OTP_2007 = {"AIRBUS_INDUSTRIE", "BOMBARDIER_INC", "MCDONNELL_DOUGLAS"}
SPARSE_EARLY = {"EMBRAER", "BOMBARDIER_INC"}


def build_facts() -> List[str]:
    facts: List[str] = [
        "analysisPeriod(2000-2008)",
        "ontologyLink(Flight, assignedAircraft, Plane)",
        "ontologyProperty(Plane, manufacturer)",
        "otpMetric(OnTimePerformance)",
    ]
    ranked = sorted(SEGMENT_TOTALS.items(), key=lambda x: x[1], reverse=True)
    total_top5 = sum(v for _, v in ranked)
    for rank, (mfr, count) in enumerate(ranked, start=1):
        facts.append(f"segmentTotal({mfr}, {count})")
        facts.append(f"segmentRank({mfr}, {rank})")
        if count / total_top5 >= 0.40:
            facts.append(f"dominantShare({mfr})")
        y2003, y2007 = OTP_SNAPSHOT[mfr][2003], OTP_SNAPSHOT[mfr][2007]
        facts.append(f"otpYear({mfr}, 2003, {y2003})")
        facts.append(f"otpYear({mfr}, 2007, {y2007})")
        if y2007 < y2003:
            facts.append(f"otpTrend({mfr}, declining)")
        if mfr in WEAK_OTP_2007:
            facts.append(f"weakOtp2007({mfr})")
        if mfr in SPARSE_EARLY:
            facts.append(f"sparseTailnumMatch({mfr})")
    return facts


def load_rules(path: Path) -> List[Dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("rules", [])


def run_reasoning(facts: List[str], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    from semantica.reasoning import Reasoner

    reasoner = Reasoner(max_iterations=20)
    for spec in rules:
        reasoner.add_rule(spec["rule"])

    for fact in facts:
        reasoner.add_fact(fact)

    inferences = reasoner.forward_chain()
    derived = [
        {
            "conclusion": inf.conclusion,
            "rule": inf.rule_used.rule_id if inf.rule_used else None,
            "premises": inf.premises,
            "confidence": inf.confidence,
        }
        for inf in inferences
    ]

    goals = []
    for goal in (yaml.safe_load(RULES_PATH.read_text()) or {}).get("goals", []):
        proof = reasoner.backward_chain(goal)
        goals.append(
            {
                "goal": goal,
                "proven": proof is not None,
                "premises": proof.premises if proof else [],
                "rule": proof.rule_used.rule_id if proof and proof.rule_used else None,
            }
        )

    return {
        "initial_fact_count": len(facts),
        "rule_count": len(rules),
        "derived_facts": derived,
        "derived_conclusions": [d["conclusion"] for d in derived],
        "goals": goals,
    }


def build_narrative(derived: List[str]) -> str:
    lines = [
        "1. Ontologie-Auflösung: Flight → assignedAircraft → Plane.manufacturer auf flights_orc + planes.",
        "2. Aggregation 2000–2008: Boeing führt mit 14,5 Mio. Segmenten (segmentRank=1 → marketLeader).",
        "3. OTP-Klassifikation: FAA 15-min-Regel (OnTimeFlight) pro Jahr und Hersteller.",
        "4. Trend 2003→2007: otpTrend(declining) bei allen Top-5 → punctualityRisk(elevated).",
        "5. Schwachjahr 2007: weakOtp2007 für Airbus, Bombardier, McDonnell Douglas.",
    ]
    if "fleetDominance(BOEING)" in derived:
        lines.append("6. Boeing >40% Top-5-Anteil → fleetDominance(BOEING).")
    if "industryWideStress(2000-2008)" in derived:
        lines.append("7. Marktführer + sinkende OTP → industryWideStress(2000-2008).")
    if "recommendOTPReview(BOEING)" in derived:
        lines.append("8. Empfehlung: recommendOTPReview(BOEING) — dominante Flotte, fallende Pünktlichkeit.")
    return "\n".join(lines)


def record_analysis_decision(
    graph: Any, narrative: str, derived: List[str], confidence: float = 0.92
) -> str:
    outcome = (
        "Boeing ist Marktführer (14,5 Mio. Segmente 2000–2008); "
        "branchenweiter OTP-Rückgang 2003→2007; 2007 schwächstes Jahr; "
        "operative OTP-Überprüfung für Boeing empfohlen."
    )
    return graph.record_decision(
        category="airline_manufacturer_analytics",
        scenario="Welche Hersteller flogen 2000–2008 die meisten Segmente und welche OTP pro Jahr?",
        reasoning=narrative,
        outcome=outcome,
        confidence=confidence,
        entities=["BOEING", "EMBRAER", "BOMBARDIER_INC", "AIRBUS_INDUSTRIE", "MCDONNELL_DOUGLAS"],
        decision_maker="airline_manufacturer_reasoning.py",
        metadata={
            "analysis_period": "2000-2008",
            "derived_facts": derived,
            "otp_definition": "FAA 15-min OnTimeFlight",
            "data_sources": ["airlinedata.flights_orc", "airlinedata.planes"],
        },
    )


def export_reasoning(
    graph_path: Path,
    output_path: Path,
    persist_decision: bool = True,
) -> Dict[str, Any]:
    facts = build_facts()
    rules = load_rules(RULES_PATH)
    reasoning = run_reasoning(facts, rules)
    derived = reasoning["derived_conclusions"]
    narrative = build_narrative(derived)

    report: Dict[str, Any] = {
        "analysis_id": "manufacturer_otp_2000_2008",
        "period": "2000-2008",
        "segment_totals": SEGMENT_TOTALS,
        "otp_snapshot_2003_2007": OTP_SNAPSHOT,
        "initial_facts": facts,
        "rules": [r["rule"] for r in rules],
        "reasoning": reasoning,
        "narrative_de": narrative,
    }

    if persist_decision:
        from semantica.context import ContextGraph

        graph = ContextGraph()
        graph.load_from_file(str(graph_path))
        decision_id = record_analysis_decision(graph, narrative, derived)
        graph.save_to_file(str(graph_path))
        report["decision_id"] = decision_id
        report["graph_path"] = str(graph_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["output_path"] = str(output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run manufacturer OTP analysis reasoning")
    parser.add_argument("--graph", default=str(DEFAULT_GRAPH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--no-persist", action="store_true", help="Skip decision on graph")
    args = parser.parse_args()

    report = export_reasoning(
        Path(args.graph),
        Path(args.output),
        persist_decision=not args.no_persist,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
