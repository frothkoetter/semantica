"""Tests for OTP SQL helpers (airline demo)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "examples"))

from airline_business_sql import (
    list_kpi_catalog,
    load_business_rules,
    resolve_kpi_by_alias,
    sql_kpi_expr,
    sql_otp_expr,
    sql_otp_having_min_completed,
)


def test_sql_otp_expr_uses_business_rules():
    rules = load_business_rules(str(REPO / "config" / "airline_business_rules.yaml"))
    expr = sql_otp_expr(rules)
    assert "AS otp_pct" in expr
    assert "arrdelay" in expr
    assert "depdelay" in expr
    assert "cancelled = 0" in expr


def test_sql_otp_having_default():
    rules = load_business_rules(str(REPO / "config" / "airline_business_rules.yaml"))
    assert sql_otp_having_min_completed(rules) == 1000


def test_kpi_catalog_merged():
    rules = load_business_rules(str(REPO / "config" / "airline_business_rules.yaml"))
    catalog = list_kpi_catalog(rules)
    assert catalog["kpi_count"] == 50
    assert "SevereDelayRate" in catalog["kpis"]
    assert "PunctualityKPI" in catalog["categories"]


def test_sql_kpi_expr_severe_delay():
    rules = load_business_rules(str(REPO / "config" / "airline_business_rules.yaml"))
    expr = sql_kpi_expr("SevereDelayRate", rules)
    assert "AS severe_delay_pct" in expr
    assert "> 60" in expr


def test_resolve_kpi_by_alias():
    rules = load_business_rules(str(REPO / "config" / "airline_business_rules.yaml"))
    assert resolve_kpi_by_alias("D0", rules) == "D0DepartureOTP"
    assert resolve_kpi_by_alias("ASM", rules) == "AvailableSeatMiles"
