#!/usr/bin/env python3
"""Export manufacturer segment + OTP analysis (2000-2008) as PDF."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "examples"))
DEFAULT_OUTPUT = REPO / "data" / "airline_manufacturer_otp_2000_2008.pdf"
DEFAULT_REASONING = REPO / "data" / "airline_manufacturer_analysis_reasoning.json"

TOTALS = [
    ("BOEING", 14_518_058),
    ("EMBRAER", 5_176_326),
    ("BOMBARDIER INC", 4_735_636),
    ("AIRBUS INDUSTRIE", 3_733_463),
    ("MCDONNELL DOUGLAS", 2_717_289),
]

YEARLY = [
    # year, manufacturer, segments, otp_pct
    (2000, "AIRBUS INDUSTRIE", 309_941, 69.3),
    (2002, "AIRBUS INDUSTRIE", 386_936, 82.0),
    (2003, "AIRBUS INDUSTRIE", 462_052, 81.6),
    (2004, "AIRBUS INDUSTRIE", 470_468, 78.2),
    (2005, "AIRBUS INDUSTRIE", 495_007, 76.1),
    (2006, "AIRBUS INDUSTRIE", 511_871, 74.9),
    (2007, "AIRBUS INDUSTRIE", 559_454, 69.4),
    (2008, "AIRBUS INDUSTRIE", 537_734, 76.0),
    (2000, "BOEING", 1_198_090, 71.9),
    (2001, "BOEING", 250_612, 82.4),
    (2002, "BOEING", 1_067_163, 81.8),
    (2003, "BOEING", 1_291_371, 81.7),
    (2004, "BOEING", 1_710_370, 78.1),
    (2005, "BOEING", 1_792_098, 75.8),
    (2006, "BOEING", 1_866_999, 74.8),
    (2007, "BOEING", 2_679_778, 74.8),
    (2008, "BOEING", 2_661_577, 76.4),
    (2001, "BOMBARDIER INC", 1_916, 91.7),
    (2002, "BOMBARDIER INC", 357, 92.2),
    (2003, "BOMBARDIER INC", 359_764, 81.4),
    (2004, "BOMBARDIER INC", 670_367, 78.5),
    (2005, "BOMBARDIER INC", 791_576, 77.9),
    (2006, "BOMBARDIER INC", 930_137, 73.3),
    (2007, "BOMBARDIER INC", 1_006_829, 70.9),
    (2008, "BOMBARDIER INC", 974_690, 75.3),
    (2001, "EMBRAER", 281, 80.1),
    (2002, "EMBRAER", 75, 79.7),
    (2003, "EMBRAER", 480_102, 84.1),
    (2004, "EMBRAER", 714_051, 79.4),
    (2005, "EMBRAER", 973_462, 78.3),
    (2006, "EMBRAER", 1_057_262, 73.1),
    (2007, "EMBRAER", 1_063_685, 73.3),
    (2008, "EMBRAER", 887_408, 74.8),
    (2000, "MCDONNELL DOUGLAS", 361_883, 76.3),
    (2002, "MCDONNELL DOUGLAS", 291_254, 82.9),
    (2003, "MCDONNELL DOUGLAS", 341_000, 83.0),
    (2004, "MCDONNELL DOUGLAS", 350_409, 78.3),
    (2005, "MCDONNELL DOUGLAS", 347_017, 77.3),
    (2006, "MCDONNELL DOUGLAS", 344_144, 75.2),
    (2007, "MCDONNELL DOUGLAS", 352_229, 70.5),
    (2008, "MCDONNELL DOUGLAS", 329_353, 74.2),
]

MANUFACTURERS = [
    "BOEING",
    "EMBRAER",
    "BOMBARDIER INC",
    "AIRBUS INDUSTRIE",
    "MCDONNELL DOUGLAS",
]


def _title_page(pdf: PdfPages) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.5, 0.72, "Airline Ontology Analytics", ha="center", fontsize=22, weight="bold")
    fig.text(
        0.5,
        0.64,
        "Hersteller-Segmente & On-Time Performance (OTP)\n2000 – 2008",
        ha="center",
        fontsize=14,
    )
    fig.text(
        0.5,
        0.48,
        "Datenquelle: airlinedata.flights + planes\n"
        "Ontologie: Flight → assignedAircraft → Plane.manufacturer\n"
        "OTP: FAA 15-min-Regel (OnTimeFlight / abgeschlossene Flüge)",
        ha="center",
        fontsize=10,
        color="#334155",
    )
    fig.text(0.5, 0.18, f"Erstellt: {date.today().isoformat()}", ha="center", fontsize=9, color="#64748b")
    fig.text(0.5, 0.14, "Semantica Airline Demo", ha="center", fontsize=9, color="#64748b")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _summary_page(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    ax.set_title("Zusammenfassung", loc="left", fontsize=16, weight="bold", pad=20)

    bullets = [
        "Boeing dominiert mit ~14,5 Mio. Segmenten (≈48 % der Top-5).",
        "EMBRAER und Bombardier folgen mit ~5,2 Mio. bzw. ~4,7 Mio. Segmenten.",
        "OTP sinkt branchenweit von ~80–84 % (2002–2003) auf ~70–76 % (2006–2008).",
        "2007 war das schwächste OTP-Jahr bei Airbus, Bombardier und McDonnell Douglas.",
        "Embraer/Bombardier: 2000–2002 nur wenige tailnum-Matches — OTP dort unsicher.",
    ]
    y = 0.88
    for item in bullets:
        ax.text(0.06, y, f"• {item}", fontsize=11, va="top", transform=ax.transAxes)
        y -= 0.08

    ax.text(0.06, 0.42, "Top 5 Hersteller — Segmente gesamt (2000–2008)", fontsize=12, weight="bold")
    table_data = [[name, f"{count:,}".replace(",", ".")] for name, count in TOTALS]
    table = ax.table(
        cellText=table_data,
        colLabels=["Hersteller", "Segmente"],
        cellLoc="left",
        colLoc="left",
        loc="center",
        bbox=[0.06, 0.12, 0.88, 0.24],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.4)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _segments_chart(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 6))
    names = [n for n, _ in TOTALS]
    counts = [c / 1_000_000 for _, c in TOTALS]
    colors = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626"]
    bars = ax.barh(names[::-1], counts[::-1], color=colors[::-1])
    ax.set_xlabel("Segmente (Millionen)")
    ax.set_title("Flugsegmente nach Hersteller (2000–2008)")
    for bar, val in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2, f"{val:.1f}M", va="center", fontsize=9)
    ax.set_xlim(0, max(counts) * 1.15)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _otp_trend_chart(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 6))
    palette = {
        "BOEING": "#2563eb",
        "EMBRAER": "#7c3aed",
        "BOMBARDIER INC": "#059669",
        "AIRBUS INDUSTRIE": "#d97706",
        "MCDONNELL DOUGLAS": "#dc2626",
    }
    for mfr in MANUFACTURERS:
        rows = sorted((r for r in YEARLY if r[1] == mfr), key=lambda x: x[0])
        if len(rows) < 2:
            continue
        years = [r[0] for r in rows]
        otps = [r[3] for r in rows]
        ax.plot(years, otps, marker="o", label=mfr, color=palette[mfr], linewidth=2)
    ax.set_title("OTP nach Hersteller und Jahr")
    ax.set_xlabel("Jahr")
    ax.set_ylabel("OTP (%)")
    ax.set_ylim(65, 95)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _load_reasoning(path: Path) -> Dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    from airline_manufacturer_reasoning import export_reasoning

    export_reasoning(
        REPO / "data" / "airline_graph.json",
        path,
        persist_decision=True,
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _text_page(
    pdf: PdfPages,
    title: str,
    lines: List[str],
    *,
    fontsize: int = 10,
    title_size: int = 16,
) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=title_size, weight="bold", pad=20)
    y = 0.92
    for line in lines:
        if not line:
            y -= 0.02
            continue
        wrapped = textwrap.wrap(line, width=95) or [""]
        for part in wrapped:
            ax.text(0.05, y, part, fontsize=fontsize, va="top", transform=ax.transAxes, family="monospace" if line.startswith("IF ") else "sans-serif")
            y -= 0.035
        if y < 0.05:
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")
            ax.set_title(f"{title} (cont.)", loc="left", fontsize=title_size, weight="bold", pad=20)
            y = 0.92
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _reasoning_overview_page(pdf: PdfPages, reasoning: Dict[str, Any]) -> None:
    narrative = reasoning.get("narrative_de", "").split("\n")
    decision_id = reasoning.get("decision_id", "—")
    lines = [
        "Semantica Reasoner — Forward & Backward Chaining",
        "",
        "Narrative:",
        *narrative,
        "",
        f"Decision ID (airline_graph.json): {decision_id}",
        "",
        "Haupt-Empfehlung: recommendOTPReview(BOEING)",
        "Begründung: fleetDominance + punctualityRisk(elevated)",
    ]
    _text_page(pdf, "Semantica Reasoning — Übersicht", lines)


def _reasoning_rules_page(pdf: PdfPages, reasoning: Dict[str, Any]) -> None:
    lines = ["Forward-chaining Regeln (config/airline_manufacturer_reasoning.yaml):", ""]
    for idx, rule in enumerate(reasoning.get("rules", []), start=1):
        lines.append(f"{idx}. {rule}")
    _text_page(pdf, "Reasoning-Regeln", lines, fontsize=9)


def _reasoning_inferences_page(pdf: PdfPages, reasoning: Dict[str, Any]) -> None:
    derived = reasoning.get("reasoning", {}).get("derived_facts", [])
    lines = ["Abgeleitete Fakten (mit Premissen):", ""]
    for item in derived:
        conclusion = item.get("conclusion", "")
        rule = item.get("rule", "?")
        premises = ", ".join(item.get("premises", []))
        lines.append(f"→ {conclusion}")
        lines.append(f"   Regel: {rule} | Premissen: {premises}")
        lines.append("")
    _text_page(pdf, "Inference Trace", lines, fontsize=9)


def _reasoning_goals_page(pdf: PdfPages, reasoning: Dict[str, Any]) -> None:
    goals = reasoning.get("reasoning", {}).get("goals", [])
    lines = ["Backward-chaining — bewiesene Ziele:", ""]
    for goal in goals:
        status = "✓ bewiesen" if goal.get("proven") else "✗ nicht bewiesen"
        lines.append(f"{goal.get('goal')} — {status}")
        if goal.get("premises"):
            lines.append(f"   Premissen: {', '.join(goal['premises'])}")
        lines.append("")
    _text_page(pdf, "Zielbeweise", lines, fontsize=10)


def _reasoning_chain_diagram(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 6))
    ax.axis("off")
    ax.set_title("Reasoning-Kette (Kernpfad)", loc="left", fontsize=14, weight="bold", pad=12)
    steps = [
        ("segmentRank(BOEING,1)", 0.5, 0.88),
        ("marketLeader(BOEING)", 0.5, 0.74),
        ("dominantShare(BOEING)", 0.25, 0.60),
        ("fleetDominance(BOEING)", 0.5, 0.46),
        ("otpTrend(declining)", 0.75, 0.60),
        ("punctualityRisk(elevated)", 0.75, 0.46),
        ("industryWideStress", 0.62, 0.30),
        ("recommendOTPReview(BOEING)", 0.5, 0.14),
    ]
    for label, x, y in steps:
        ax.text(x, y, label, ha="center", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#e0e7ff", edgecolor="#6366f1"))
    arrows = [
        ((0.5, 0.84), (0.5, 0.78)),
        ((0.5, 0.70), (0.5, 0.50)),
        ((0.30, 0.56), (0.45, 0.50)),
        ((0.75, 0.56), (0.75, 0.50)),
        ((0.5, 0.42), (0.58, 0.34)),
        ((0.75, 0.42), (0.66, 0.34)),
        ((0.62, 0.26), (0.52, 0.18)),
    ]
    for (x0, y0), (x1, y1) in arrows:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", color="#64748b", lw=1.2))
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _manufacturer_table_page(pdf: PdfPages, manufacturer: str) -> None:
    rows = sorted((r for r in YEARLY if r[1] == manufacturer), key=lambda x: x[0])
    fig, ax = plt.subplots(figsize=(8.27, 6))
    ax.axis("off")
    ax.set_title(f"{manufacturer} — Segmente & OTP pro Jahr", loc="left", fontsize=14, weight="bold", pad=16)
    table_data = [
        [str(year), f"{segments:,}".replace(",", "."), f"{otp:.1f}"]
        for year, _, segments, otp in rows
    ]
    table = ax.table(
        cellText=table_data,
        colLabels=["Jahr", "Segmente", "OTP %"],
        cellLoc="center",
        colLoc="center",
        loc="center",
        bbox=[0.15, 0.2, 0.7, 0.6],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def export_pdf(
    output: Path,
    reasoning_path: Path = DEFAULT_REASONING,
) -> Path:
    reasoning = _load_reasoning(reasoning_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        _title_page(pdf)
        _summary_page(pdf)
        _segments_chart(pdf)
        _otp_trend_chart(pdf)
        for mfr in MANUFACTURERS:
            _manufacturer_table_page(pdf, mfr)
        _reasoning_overview_page(pdf, reasoning)
        _reasoning_chain_diagram(pdf)
        _reasoning_rules_page(pdf, reasoning)
        _reasoning_inferences_page(pdf, reasoning)
        _reasoning_goals_page(pdf, reasoning)
        d = pdf.infodict()
        d["Title"] = "Airline Manufacturer OTP Analysis 2000-2008"
        d["Author"] = "Semantica Airline Demo"
        d["Subject"] = "Ontology-first analytics + Semantica reasoning on airlinedata Hive"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Export manufacturer OTP analysis PDF")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--reasoning", default=str(DEFAULT_REASONING))
    args = parser.parse_args()
    path = export_pdf(Path(args.output), Path(args.reasoning))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
