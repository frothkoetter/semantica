#!/usr/bin/env python3
"""Build Semantica technical overview PowerPoint deck."""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "deploy" / "cloudera-agent-studio" / "semantica-technical-overview.pptx"
ASSETS = REPO / "deploy" / "cloudera-agent-studio" / "deck_assets"
KG_OVERVIEW = REPO / "data" / "airline_kg_overview.png"

# Brand colors
NAVY = RGBColor(0x1A, 0x36, 0x5D)
TEAL = RGBColor(0x14, 0x92, 0x87)
SLATE = RGBColor(0x4A, 0x55, 0x68)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF7, 0xFA, 0xFC)
ACCENT = RGBColor(0x3E, 0x79, 0xF2)


def _set_slide_bg(slide, color: RGBColor = LIGHT) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, NAVY)
    box = slide.shapes.add_textbox(Inches(0.6), Inches(2.2), Inches(8.8), Inches(1.2))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.LEFT
    box2 = slide.shapes.add_textbox(Inches(0.6), Inches(3.5), Inches(8.8), Inches(1.5))
    tf2 = box2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(20)
    p2.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE0)
    p2.alignment = PP_ALIGN.LEFT


def _add_section_slide(prs: Presentation, title: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, TEAL)
    box = slide.shapes.add_textbox(Inches(0.6), Inches(3.0), Inches(8.8), Inches(1.0))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.LEFT


def _add_content_slide(
    prs: Presentation,
    title: str,
    bullets: list[str],
    *,
    subtitle: str | None = None,
    code_block: str | None = None,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, LIGHT)

    # Title bar
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.9))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    tbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.7))
    tp = tbox.text_frame.paragraphs[0]
    tp.text = title
    tp.font.size = Pt(26)
    tp.font.bold = True
    tp.font.color.rgb = WHITE

    y = 1.15
    if subtitle:
        sbox = slide.shapes.add_textbox(Inches(0.55), Inches(y), Inches(8.9), Inches(0.5))
        sp = sbox.text_frame.paragraphs[0]
        sp.text = subtitle
        sp.font.size = Pt(14)
        sp.font.italic = True
        sp.font.color.rgb = SLATE
        y += 0.55

    body_top = y
    body_h = 4.8 if not code_block else 2.6
    bbox = slide.shapes.add_textbox(Inches(0.55), Inches(body_top), Inches(8.9), Inches(body_h))
    tf = bbox.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(15)
        p.font.color.rgb = SLATE
        p.space_after = Pt(8)

    if code_block:
        cbox = slide.shapes.add_textbox(Inches(0.55), Inches(body_top + body_h + 0.1), Inches(8.9), Inches(2.0))
        ctf = cbox.text_frame
        ctf.word_wrap = True
        cp = ctf.paragraphs[0]
        cp.text = code_block
        cp.font.name = "Menlo"
        cp.font.size = Pt(10)
        cp.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)


def _add_two_column_slide(
    prs: Presentation,
    title: str,
    left_title: str,
    left_bullets: list[str],
    right_title: str,
    right_bullets: list[str],
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, LIGHT)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.9))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    tbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.7))
    tp = tbox.text_frame.paragraphs[0]
    tp.text = title
    tp.font.size = Pt(26)
    tp.font.bold = True
    tp.font.color.rgb = WHITE

    for col, (ctitle, cbullets, x) in enumerate(
        [(left_title, left_bullets, 0.45), (right_title, right_bullets, 5.05)]
    ):
        hbox = slide.shapes.add_textbox(Inches(x), Inches(1.1), Inches(4.4), Inches(0.4))
        hp = hbox.text_frame.paragraphs[0]
        hp.text = ctitle
        hp.font.size = Pt(16)
        hp.font.bold = True
        hp.font.color.rgb = TEAL
        bbox = slide.shapes.add_textbox(Inches(x), Inches(1.55), Inches(4.4), Inches(5.0))
        tf = bbox.text_frame
        tf.word_wrap = True
        for i, b in enumerate(cbullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = b
            p.font.size = Pt(13)
            p.font.color.rgb = SLATE
            p.space_after = Pt(6)


def _add_image_slide(
    prs: Presentation,
    title: str,
    image_path: Path,
    *,
    subtitle: str | None = None,
    caption: str | None = None,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, LIGHT)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.9))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    tbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.7))
    tp = tbox.text_frame.paragraphs[0]
    tp.text = title
    tp.font.size = Pt(26)
    tp.font.bold = True
    tp.font.color.rgb = WHITE

    top = 1.05
    if subtitle:
        sbox = slide.shapes.add_textbox(Inches(0.5), Inches(top), Inches(9), Inches(0.35))
        sp = sbox.text_frame.paragraphs[0]
        sp.text = subtitle
        sp.font.size = Pt(13)
        sp.font.italic = True
        sp.font.color.rgb = SLATE
        top += 0.4

    img_top = top
    img_h = 5.6 - (0.35 if caption else 0)
    if image_path.is_file():
        slide.shapes.add_picture(
            str(image_path),
            Inches(0.45),
            Inches(img_top),
            width=Inches(9.1),
            height=Inches(img_h),
        )
    else:
        miss = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1))
        miss.text_frame.paragraphs[0].text = f"(Missing image: {image_path})"

    if caption:
        cbox = slide.shapes.add_textbox(Inches(0.5), Inches(6.65), Inches(9), Inches(0.5))
        cp = cbox.text_frame.paragraphs[0]
        cp.text = caption
        cp.font.size = Pt(11)
        cp.font.color.rgb = SLATE


def _render_diagrams(assets_dir: Path) -> dict[str, Path]:
    """Generate PNG architecture diagrams for the deck."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    assets_dir.mkdir(parents=True, exist_ok=True)
    navy = "#1A365D"
    teal = "#149287"
    accent = "#3E79F2"
    light = "#F7FAFC"
    paths: dict[str, Path] = {}

    def _save(fig, name: str) -> None:
        path = assets_dir / name
        fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=light)
        plt.close(fig)
        paths[name] = path

    # Multi-agent pipeline
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_facecolor(light)
    boxes = [
        (0.4, 2.0, "User\nquestion", "#E2E8F0", navy),
        (2.0, 2.0, "1. Ontology Mapper\nsemantica MCP", accent, "white"),
        (4.6, 2.0, "2. SQL Executor\niceberg-hive MCP", teal, "white"),
        (7.2, 2.0, "3. Answer Synthesizer\nsemantica-decisions", "#805AD5", "white"),
    ]
    for x, y, text, fill, fg in boxes:
        patch = FancyBboxPatch(
            (x, y),
            1.5,
            1.1,
            boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=fill,
            edgecolor=navy,
            linewidth=1.2,
        )
        ax.add_patch(patch)
        ax.text(x + 0.75, y + 0.55, text, ha="center", va="center", fontsize=9, color=fg, weight="bold")
    for x0, x1 in [(1.9, 2.0), (3.5, 4.6), (6.1, 7.2)]:
        ax.add_patch(
            FancyArrowPatch(
                (x0, 2.55),
                (x1, 2.55),
                arrowstyle="-|>",
                mutation_scale=14,
                color=navy,
                linewidth=1.5,
            )
        )
    ax.text(5, 0.5, "Sequential · Manager OFF · mapping plan → SQL → audit", ha="center", fontsize=10, color=navy)
    _save(fig, "diagram_multi_agent_pipeline.png")

    # Three-layer stack
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_facecolor(light)
    layers = [
        (0.8, 3.6, 8.4, 0.9, "Layer 1 — Ontology (TTL)", "Flight · OTP · SevereDelay · operatedBy", "#EBF8FF"),
        (0.8, 2.4, 8.4, 0.9, "Layer 2 — Knowledge Graph (JSON)", "OntologyClass · BusinessRule · mappings", "#E6FFFA"),
        (0.8, 1.2, 8.4, 0.9, "Layer 3 — Warehouse (Hive/Iceberg)", "airlinedata.flights · airlines · airports", "#EDF2F7"),
    ]
    for x, y, w, h, title, sub, fill in layers:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.05",
                facecolor=fill,
                edgecolor=navy,
            )
        )
        ax.text(x + 0.2, y + h - 0.28, title, fontsize=11, weight="bold", color=navy)
        ax.text(x + 0.2, y + 0.22, sub, fontsize=9, color="#4A5568")
    ax.add_patch(FancyArrowPatch((5, 3.55), (5, 3.35), arrowstyle="-|>", color=teal, mutation_scale=12))
    ax.add_patch(FancyArrowPatch((5, 2.35), (5, 2.15), arrowstyle="-|>", color=teal, mutation_scale=12))
    ax.text(5, 0.45, "MCP tools read layers 1–2; SQL MCP executes layer 3 only", ha="center", fontsize=10, color=navy)
    _save(fig, "diagram_three_layer_stack.png")

    # MCP servers
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_facecolor(light)
    mcps = [
        (0.5, 2.2, "semantica-ontology", "get_graph_summary\nget_business_rules", accent),
        (3.5, 2.2, "iceberg-hive", "execute_query\nget_schema", teal),
        (6.5, 2.2, "semantica-decisions", "record_decision\ncompare_with_history", "#805AD5"),
    ]
    for x, y, name, tools, color in mcps:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.6,
                1.4,
                boxstyle="round,pad=0.06",
                facecolor=color,
                edgecolor=navy,
                alpha=0.92,
            )
        )
        ax.text(x + 1.3, y + 1.05, name, ha="center", fontsize=10, weight="bold", color="white")
        ax.text(x + 1.3, y + 0.45, tools, ha="center", fontsize=8.5, color="white")
    ax.text(5, 4.2, "One MCP server per agent — least privilege", ha="center", fontsize=12, weight="bold", color=navy)
    ax.text(5, 0.6, "Env: SEMANTICA_KG_PATH · MAPPING_CONFIG · BUSINESS_RULES · DECISION_STORE", ha="center", fontsize=9, color="#4A5568")
    _save(fig, "diagram_mcp_servers.png")

    # OTP resolution flow
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_facecolor(light)
    steps = [
        (0.3, 4.8, "User: Top airlines by OTP"),
        (0.3, 3.9, "Ontology: OTP ≡ OnTimePerformance"),
        (0.3, 3.0, "Rules: otp.sql.expr, 15 min threshold"),
        (0.3, 2.1, "Mapping: flights.uniquecarrier → airlines.code"),
        (0.3, 1.2, "SQL: aggregate on airlinedata.flights"),
        (0.3, 0.3, "Decision Store: fingerprint + metrics"),
    ]
    for i, (x, y, text) in enumerate(steps):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                9.4,
                0.65,
                boxstyle="round,pad=0.04",
                facecolor="#FFFFFF" if i % 2 else "#EBF8FF",
                edgecolor=teal if i < 5 else accent,
            )
        )
        ax.text(x + 0.25, y + 0.32, f"{i + 1}. {text}", fontsize=10, color=navy, va="center")
        if i < len(steps) - 1:
            ax.add_patch(
                FancyArrowPatch((5, y), (5, y - 0.05), arrowstyle="-|>", color=navy, mutation_scale=10)
            )
    _save(fig, "diagram_otp_flow.png")

    return paths


def build() -> Path:
    diagram_paths = _render_diagrams(ASSETS)

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    _add_title_slide(
        prs,
        "Semantica",
        "Ontology-Governed Knowledge Graphs · MCP · Multi-Agent Analytics\nDeterministic semantics vs. LLM hallucination",
    )

    _add_content_slide(
        prs,
        "Agenda",
        [
            "1. Semantica concept: ontology + knowledge graph",
            "2. Architecture: MCP servers & multi-agent pipeline",
            "3. Configuration: graph JSON, business rules, R2RML mapping",
            "4. Worked example: OTP from business meaning → SQL",
            "5. Decision Store: audit trail without graph bloat",
            "6. Deterministic layer vs. stochastic LLM behavior",
        ],
    )

    _add_section_slide(prs, "Part 1 — Concepts")

    _add_content_slide(
        prs,
        "What is Semantica?",
        subtitle="A semantic layer between natural language and enterprise data",
        bullets=[
            "Semantica is an open-source platform for building context graphs: ontology + mappings + business rules + optional decision audit.",
            "Agents and humans ask questions in business language; Semantica resolves meaning to validated SQL against Hive/Iceberg, PostgreSQL, etc.",
            "Core modules: ingest, ontology, context graph, MCP server, Knowledge Explorer, decision store.",
            "Design goal: separate what things mean (ontology) from where they live (tables/columns) and how KPIs are computed (rules).",
        ],
    )

    _add_two_column_slide(
        prs,
        "Ontology vs. Knowledge Graph",
        "Ontology (T-box)",
        [
            "Formal vocabulary: classes, properties, hierarchies",
            "Examples: Flight, Airline, OTP, SevereDelay",
            "Object properties: operatedBy, originAirport",
            "Datatype properties: arrDelay, crsDepTime",
            "Stored as OWL/Turtle; compiled into graph nodes",
            "Answers: What concepts exist? How do they relate?",
        ],
        "Knowledge Graph (A-box + schema)",
        [
            "Runtime ContextGraph JSON: nodes + edges",
            "OntologyClass, ObjectProperty, BusinessRule nodes",
            "DatabaseTable mappings (when Hive introspection enabled)",
            "192+ nodes for airline demo (87 classes, 26 rules)",
            "Loaded via SEMANTICA_KG_PATH in MCP",
            "Answers: What is wired to the warehouse today?",
        ],
    )

    _add_image_slide(
        prs,
        "Airline Knowledge Graph Overview",
        KG_OVERVIEW,
        subtitle="Ontology classes, object properties, and business rules (force-directed layout)",
        caption="Generated by scripts/export_kg_business_rules_image.py · 129 nodes in ontology/rules view",
    )

    _add_image_slide(
        prs,
        "Three-Layer Semantic Stack",
        diagram_paths["diagram_three_layer_stack.png"],
        subtitle="Ontology → ContextGraph JSON → physical warehouse",
    )

    _add_content_slide(
        prs,
        "Three-Layer Semantic Stack (detail)",
        bullets=[
            "Layer 1 — Ontology: domain meaning (US DOT airline, KPI catalog, delay severities)",
            "Layer 2 — Knowledge Graph: materialized ontology + rules + DB bindings as traversable JSON",
            "Layer 3 — Physical warehouse: airlinedata.flights, airlines, airports, planes (Iceberg/Hive)",
            "Agents never guess layer 3 from memory; they read layers 1–2 via MCP tools, then execute layer 3 via warehouse MCP.",
            "Invalid columns (e.g. airports.name) are blocked in mapping YAML — a common LLM hallucination vector.",
        ],
        code_block=(
            "User: \"OTP for AA in 2008\"\n"
            "  → Ontology: OTP ≡ OnTimePerformance, Airline, Flight\n"
            "  → Rules: otp.sql.expr, threshold 15 min\n"
            "  → Mapping: flights.uniquecarrier → Airline.code\n"
            "  → SQL: SELECT … FROM airlinedata.flights JOIN airlines …"
        ),
    )

    _add_section_slide(prs, "Part 2 — Architecture")

    _add_image_slide(
        prs,
        "MCP Server Topology",
        diagram_paths["diagram_mcp_servers.png"],
        subtitle="Separate credentials and toolsets per agent role",
    )

    _add_content_slide(
        prs,
        "MCP (Model Context Protocol) Architecture",
        subtitle="One specialized MCP server per agent — least privilege, no credential sprawl",
        bullets=[
            "semantica-ontology MCP: get_graph_summary, get_business_rules (read-only semantics)",
            "iceberg-hive MCP: execute_query, get_schema (warehouse access only)",
            "semantica-decisions MCP: record_decision, compare_with_history, find_precedents (audit log)",
            "Each MCP subprocess loads only its toolset (SEMANTICA_MCP_TOOLSET) — faster cold start, smaller attack surface.",
            "Configuration via env: SEMANTICA_KG_PATH, SEMANTICA_MAPPING_CONFIG, SEMANTICA_BUSINESS_RULES, SEMANTICA_DECISION_STORE.",
            "Agent Studio mounts /workflow_data read-only; writable decisions go to /workspace/decisions.",
        ],
    )

    _add_image_slide(
        prs,
        "Multi-Agent Conversational Pipeline",
        diagram_paths["diagram_multi_agent_pipeline.png"],
        subtitle="Sequential process · Manager OFF · Conversational ON",
        caption="Handoff: mapping plan JSON → SQL rows → narrative + Decision Store record",
    )

    _add_content_slide(
        prs,
        "Multi-Agent Pipeline (detail)",
        subtitle="Why Manager OFF and Sequential routing",
        bullets=[
            "Step 1 — ontology_mapper: NL question → mapping plan JSON (ready_for_sql, tables, joins, metrics, display_columns)",
            "Step 2 — sql_executor: executes SQL from plan only; aborts if ready_for_sql ≠ true",
            "Step 3 — answer_synthesizer: business-language answer + optional record_decision to Decision Store",
            "Why Manager OFF? Crew managers delegate without tools and hallucinate schema/joins from backstory.",
            "Why Sequential? User message flows agent 1 → 2 → 3 with structured handoffs, not parallel guesswork.",
        ],
    )

    _add_two_column_slide(
        prs,
        "Agent Responsibilities",
        "Ontology Mapper",
        [
            "MCP: semantica-ontology",
            "Tools: get_graph_summary, get_business_rules",
            "Output: mapping plan JSON",
            "Must include display_columns",
            "Must list invalid_columns_avoided",
            "Never executes SQL",
            "Never calls NER when graph pre-loaded",
        ],
        "SQL Executor + Synthesizer",
        [
            "SQL: iceberg-hive execute_query",
            "Uses plan tables/joins/metrics only",
            "Efficient patterns: filter early, no OR joins",
            "Synthesizer: semantica-decisions MCP",
            "record_decision with sql_text, metrics",
            "compare_with_history for deltas",
            "No SQL, no ontology rebuild",
        ],
    )

    _add_section_slide(prs, "Part 3 — Configuration")

    _add_content_slide(
        prs,
        "Configuration Trilogy",
        bullets=[
            "① airline_graph.json (SEMANTICA_KG_PATH) — ContextGraph: ontology classes, properties, business rule nodes, optional DatabaseTable nodes",
            "② airline_business_rules.yaml — KPI definitions, thresholds, SQL expressions, object_property_joins, sql_agent_hints (do_not_use columns)",
            "③ airline_r2rml_db_mapping.yaml — class→table, column→property, invalid_columns, preferred_tables",
            "Built by: scripts/build_airline_graph.py (imports TTL ontologies + ingests rules + optional Hive introspection)",
            "Deployed to Agent Studio: /workflow_data/data/ + /workflow_data/config/",
        ],
    )

    _add_two_column_slide(
        prs,
        "Business Rules YAML (excerpt)",
        "Joins & guardrails",
        [
            "operatedBy: flights.uniquecarrier = airlines.code",
            "originAirport: flights.origin = airports.iata",
            "do_not_use: airports.name (use airport)",
            "do_not_use: airlines.name (use description)",
            "do_not_use: flights.carrier (use uniquecarrier)",
        ],
        "OTP rule block",
        [
            "ontology_class: OTP",
            "equivalent: OnTimePerformance",
            "threshold_minutes: 15 (FAA/DOT)",
            "on_time_predicate: arrdelay & depdelay ≤ 15",
            "denominator: cancelled = 0 only",
            "sql.expr: ROUND(100 * on_time / completed, 2)",
        ],
    )

    _add_content_slide(
        prs,
        "Mapping Plan Template (Agent Output)",
        subtitle="Structured contract between ontology_mapper and sql_executor",
        bullets=[
            "ready_for_sql: boolean gate — sql_executor aborts if false",
            "ontology_terms, business_rules_applied, tables, joins",
            "display_columns: {Airport.airportName: airports.airport}",
            "invalid_columns_avoided: [airports.name]",
            "metrics: [{name: otp_pct, expr: <from business rules>}])",
            "sql_patterns: aggregate_fact_first | single_edge_join — prevents OR-join anti-patterns",
        ],
        code_block=(
            '{\n'
            '  "ready_for_sql": true,\n'
            '  "ontology_terms": ["OTP", "Airline", "Flight"],\n'
            '  "tables": ["flights", "airlines"],\n'
            '  "joins": [{"edge": "operatedBy", "on": "f.uniquecarrier = a.code"}],\n'
            '  "metrics": [{"name": "otp_pct", "expr": "<otp.sql.expr>"}],\n'
            '  "display_columns": {"Airline.description": "a.description"}\n'
            '}'
        ),
    )

    _add_section_slide(prs, "Part 4 — OTP Example")

    _add_image_slide(
        prs,
        "OTP: From Meaning to SQL",
        diagram_paths["diagram_otp_flow.png"],
        subtitle="Deterministic resolution chain — config-driven, not invented by the LLM",
    )

    _add_content_slide(
        prs,
        "OTP Resolution (detail)",
        subtitle="End-to-end resolution chain (deterministic config, not LLM invention)",
        bullets=[
            "① User asks: \"Top 5 airlines by OTP in 2003\"",
            "② ontology_mapper calls get_graph_summary → confirms OTP, Airline, Flight classes in graph",
            "③ get_business_rules → resolves OTP → otp.sql.expr, threshold 15 min, alt_labels",
            "④ Mapping YAML → Flight→flights, uniqueCarrier→uniquecarrier, operatedBy→airlines.code",
            "⑤ Mapping plan includes metric expr verbatim from rules; display_columns for airline names",
            "⑥ sql_executor runs qualified SQL on airlinedata; answer_synthesizer records decision with fingerprint",
        ],
    )

    _add_content_slide(
        prs,
        "OTP SQL (Generated from Rules)",
        bullets=[
            "Numerator: completed flights where arrDelay ≤ 15 AND depDelay ≤ 15",
            "Denominator: completed flights only (cancelled = 0)",
            "Join: flights.uniquecarrier = airlines.code (operatedBy)",
            "Partition filter: year = 2003 applied early on fact table",
            "Result: otp_percentage per airline — reproducible from config hashes in decision record",
        ],
        code_block=(
            "SELECT a.description AS airline_name,\n"
            "  COUNT(*) AS total_flights,\n"
            "  SUM(CASE WHEN f.arrdelay <= 15 THEN 1 ELSE 0 END) AS on_time_flights,\n"
            "  ROUND(100.0 * SUM(CASE WHEN f.arrdelay <= 15 AND f.depdelay <= 15\n"
            "    THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN f.cancelled = 0\n"
            "    THEN 1 ELSE 0 END), 0), 2) AS otp_percentage\n"
            "FROM airlinedata.flights f\n"
            "JOIN airlinedata.airlines a ON f.uniquecarrier = a.code\n"
            "WHERE f.year = 2003 AND f.cancelled = 0\n"
            "GROUP BY a.description ORDER BY otp_percentage DESC LIMIT 5"
        ),
    )

    _add_section_slide(prs, "Part 5 — Decision Store")

    _add_content_slide(
        prs,
        "Decision Store",
        subtitle="Append-only audit log — separate from the knowledge graph",
        bullets=[
            "Path: SEMANTICA_DECISION_STORE (Agent Studio: /workspace/decisions/decisions.jsonl)",
            "record_decision appends one JSON line per analysis — does NOT mutate SEMANTICA_KG_PATH",
            "Slim records: category, scenario, reasoning, outcome, confidence, query_fingerprint, sql_hash, result_metrics",
            "Optional SQLite index for fast fingerprint / time-range lookup; JSONL remains source of truth",
            "Tools: compare_with_history, explain_decision_delta, find_precedents, get_causal_chain",
            "Merged graph variant (airline_graph_with_decisions.json) adds decision nodes for Explorer UI only",
        ],
    )

    _add_content_slide(
        prs,
        "Decision Record Example",
        bullets=[
            "decision_id + recorded_at + schema_version for audit",
            "query_intent: top_airlines_by_otp · query_fingerprint for dedup/compare",
            "business_rules_hash + ontology_mapping_hash — prove which config version was used",
            "sql_text + result_metrics — reproducibility without storing full result sets in the graph",
            "Enables: \"Did we change the severe-delay definition between runs?\" via explain_decision_delta",
        ],
        code_block=(
            '{\n'
            '  "decision_id": "ef7fa934-...",\n'
            '  "category": "airline_analytics",\n'
            '  "query_intent": "top_airlines_by_otp",\n'
            '  "query_params": {"year": 2003, "otp_rule": "arrdelay <= 15"},\n'
            '  "result_metrics": {"Hawaiian Airlines Inc.": {"otp_percentage": 91.28}},\n'
            '  "sql_text": "SELECT a.description ...",\n'
            '  "business_rules_hash": "sha256:d4d406fa..."\n'
            '}'
        ),
    )

    _add_section_slide(prs, "Part 6 — Deterministic vs. LLM")

    _add_two_column_slide(
        prs,
        "Deterministic Semantics vs. LLM Hallucination",
        "Deterministic (Semantica config)",
        [
            "Ontology classes & properties from TTL/YAML",
            "Join keys from object_property_joins",
            "KPI formulas from business_rules / kpi_catalog",
            "Invalid columns explicitly blocked",
            "Same question + same config → same SQL shape",
            "Auditable via config hashes in decisions",
            "get_graph_summary forces tool-grounded plans",
        ],
        "Stochastic LLM (unguarded)",
        [
            "Invents columns: airports.name, flights.carrier",
            "OR-joins on fact×dimension (slow, wrong)",
            "Confuses delay minutes with carrier IDs",
            "Parallel record_decision calls with bad types",
            "Manager agent answers without MCP tools",
            "Markdown \"decision records\" instead of store",
            "Different SQL every run — no fingerprint",
        ],
    )

    _add_content_slide(
        prs,
        "Guardrails That Reduce Hallucination",
        bullets=[
            "ready_for_sql gate: sql_executor refuses incomplete plans",
            "Mandatory tool order: get_graph_summary before any mapping",
            "do_not_use column list in business rules (airports.name documented as invalid)",
            "display_columns required — forces explicit label→column binding",
            "One MCP per agent — sql_executor has no ontology write access",
            "Decision Store stores sql_hash + rules_hash — detect config drift vs. ad-hoc answers",
            "Falsification demos: same question with Manager ON vs. OFF shows hallucination rate drop",
        ],
    )

    _add_content_slide(
        prs,
        "Knowledge Explorer & SPARQL",
        bullets=[
            "semantica-explorer --graph airline_graph_with_decisions.json",
            "Interactive graph canvas, ontology hub, decision workspace, SPARQL editor",
            "SPARQL projects ContextGraph to ent:/prop: namespaces (read-only SELECT/ASK/CONSTRUCT)",
            "Example: ?rule a ent:BusinessRule ; rdfs:label ?label . FILTER(CONTAINS(?label,\"otp\"))",
            "Static overview PNG: scripts/export_kg_business_rules_image.py",
        ],
    )

    _add_content_slide(
        prs,
        "Deployment Checklist (Agent Studio)",
        bullets=[
            "Build graph: uv run python scripts/build_airline_graph.py [--skip-hive]",
            "Copy to workflow_data: airline_graph.json, airline_r2rml_db_mapping.yaml, airline_business_rules.yaml, airline_kpi_catalog.yaml",
            "Register MCPs: semantica-mcp-ontology.json, iceberg-hive-mcp.json, semantica-mcp-decisions.json",
            "Three agents sequential: ontology_mapper → sql_executor → answer_synthesizer",
            "Env: SEMANTICA_DECISION_STORE=/workspace/decisions (writable)",
            "Verify: get_graph_summary graph_ready_for_sql true; get_decision_store_status writable true",
        ],
    )

    _add_content_slide(
        prs,
        "Summary",
        bullets=[
            "Semantica = ontology-governed context graph + MCP tools + multi-agent pipeline",
            "Meaning (ontology) · structure (KG) · physics (warehouse) are explicitly separated",
            "OTP exemplifies: business term → rule SQL expr → mapping → qualified Hive query",
            "Decision Store provides append-only audit without bloating the graph",
            "LLMs interpret language; Semantica config makes analytics deterministic and reproducible",
            "Repository: github.com/semantica-agi/semantica · Docs: docs/guides/decision-store.md",
        ],
    )

    _add_title_slide(prs, "Questions?", "Semantica — ontology-first analytics with accountable AI")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")
    print(f"Assets: {ASSETS}/")
