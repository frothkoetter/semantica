"""Tests for manufacturer segment + OTP reasoning."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "examples"))

from airline_manufacturer_reasoning import (
    build_facts,
    export_reasoning,
    run_reasoning,
    load_rules,
    RULES_PATH,
)


def test_build_facts_includes_market_leader_inputs():
    facts = build_facts()
    assert "segmentRank(BOEING, 1)" in facts
    assert "dominantShare(BOEING)" in facts
    assert "otpTrend(BOEING, declining)" in facts


def test_forward_chaining_derives_conclusions():
    facts = build_facts()
    rules = load_rules(RULES_PATH)
    result = run_reasoning(facts, rules)
    derived = result["derived_conclusions"]
    assert "marketLeader(BOEING)" in derived
    assert "punctualityRisk(BOEING, elevated)" in derived
    assert "recommendOTPReview(BOEING)" in derived
    assert "industryWideStress(2000-2008)" in derived


def test_backward_chain_proves_market_leader():
    facts = build_facts()
    rules = load_rules(RULES_PATH)
    result = run_reasoning(facts, rules)
    goals = {g["goal"]: g for g in result["goals"]}
    assert goals["marketLeader(BOEING)"]["proven"] is True


def test_pdf_includes_reasoning_pages(tmp_path):
    from export_manufacturer_otp_analysis_pdf import export_pdf

    reasoning = tmp_path / "reasoning.json"
    out = tmp_path / "report.pdf"
    export_reasoning(
        REPO / "data" / "airline_graph.json",
        reasoning,
        persist_decision=False,
    )
    path = export_pdf(out, reasoning)
    assert path.stat().st_size > 70_000


def test_export_reasoning_json(tmp_path):
    out = tmp_path / "reasoning.json"
    report = export_reasoning(
        REPO / "data" / "airline_graph.json",
        out,
        persist_decision=False,
    )
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["analysis_id"] == "manufacturer_otp_2000_2008"
    assert "recommendOTPReview(BOEING)" in payload["reasoning"]["derived_conclusions"]
