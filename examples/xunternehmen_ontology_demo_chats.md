# XUnternehmen KDM — Ontology Demo Chats

Ontology-first analytics on the **XUnternehmen Kerndatenmodell**: users speak in KDM terms (`JuristischePerson`, `eintragung`, `gesellschafter`), the agent resolves physical Iceberg tables via `kdm/xunternehmen_kg_with_decisions.json` + `config/xunternehmen_r2rml_db_mapping.yaml`, and runs SQL on Hive database **`xunternehmen`**.

## Prerequisites

| MCP / env | Value |
|---|---|
| Semantica graph | `upload/kdm/config/xunternehmen_kg_with_decisions.json` |
| Business rules | `upload/kdm/config/xunternehmen_business_rules.yaml` |
| Mapping YAML | `upload/kdm/config/xunternehmen_r2rml_db_mapping.yaml` |
| Hive database | `xunternehmen` |
| Iceberg MCP / impyla | `execute_query` or `kdm/hive/run_hive_sql.py` |

**Ontology → physical layer (core tables):**

| Ontology class | Physical table |
|---|---|
| `NatuerlichePerson` | `xunternehmen.natuerliche_person` |
| `JuristischePerson` | `xunternehmen.juristische_person` |
| `RechtsfaehigePersonengesellschaft` | `xunternehmen.rechtsfaehige_personengesellschaft` |
| `WirtschaftlicheTaetigkeit` | `xunternehmen.wirtschaftliche_taetigkeit` |
| `Anschrift` | `xunternehmen.anschrift` |
| `Eintragung` | `xunternehmen.eintragung` (via `zuordnung_eintragung`) |
| `Gesellschafter` | `xunternehmen.rolle_gesellschafter` |

Runnable script: `python examples/xunternehmen_ontology_analytics_demo.py`

Build graph + decisions: `python kdm/build_xunternehmen_graph.py`

Agent Studio multi-agent workflow (ontology_mapper → sql_executor → answer_synthesizer):
[`deploy/cloudera-agent-studio/multi-agent-workflow-kdm.md`](../deploy/cloudera-agent-studio/multi-agent-workflow-kdm.md)

---

## Demo Chat 1 — Register completeness

**User:** Wie viele juristische Personen haben sowohl eine Eintragung als auch einen Sitz?

**Agent (reasoning):**

1. Load graph → `JuristischePerson` → `juristische_person`
2. `RegisterEingetragen` / `HatSitz` → `zuordnung_eintragung`, `zuordnung_sitz` filtered by `owner_typ = 'JuristischePerson'`
3. KPI: count with both links / total

**SQL (generated):**

```sql
SELECT
  COUNT(*) AS juristische_personen,
  SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END) AS vollstaendig_register,
  ROUND(100.0 * SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0), 1) AS pct_vollstaendig
FROM xunternehmen.juristische_person jp
LEFT JOIN xunternehmen.zuordnung_eintragung ze
  ON ze.owner_id = jp.id AND ze.owner_typ = 'JuristischePerson'
LEFT JOIN xunternehmen.zuordnung_sitz zs
  ON zs.owner_id = jp.id AND zs.owner_typ = 'JuristischePerson'
```

**Agent:** ~X % der juristischen Personen sind register-vollständig (Eintragung + Sitz).

---

## Demo Chat 2 — Natürliche Person Geburt

**User:** Wie viele natürliche Personen haben keine verknüpfte Geburt?

**Agent:** `NatuerlichePerson.geburt` → LEFT JOIN `geburt` ON `natuerliche_person_id`.

```bash
python examples/xunternehmen_ontology_analytics_demo.py --demo 2
```

---

## Demo Chat 3 — Anschrift subtypes

**User:** Verteilung der Anschrift-Typen (Straße, Postfach, Ausland)?

**Agent:** Compiles runtime `anschriftSubtype` from `anschrift_typ` using `anschrift_type_rules` in business rules YAML — **not** a Hive column.

```bash
python examples/xunternehmen_ontology_analytics_demo.py --demo 3 --print-sql-only
```

---

## Demo Chat 4 — Personengesellschaft structure

**User:** Welche Personengesellschaften haben die meisten Gesellschafter?

**Agent:** `RechtsfaehigePersonengesellschaft.gesellschafter` → `rolle_gesellschafter.personengesellschaft_id`.

---

## Demo Chat 5 — Wirtschaftliche Tätigkeit completeness

**User:** Wirtschaftliche Tätigkeiten mit Hauptbetriebsstätte und Wirtschaftszweig?

**Agent:** JOIN `betriebsstaette` (`artBetriebsstaetteCode = '01'`) + `wirtschaftszweig`.

---

## Demo Chat 6 — Data quality tiers (runtime)

**User:** Wie verteilen sich die Datenqualitäts-Tiers bei juristischen Personen?

**Agent:** Runtime `dataQualityTier` CASE compiled from `data_quality_tier_rules` — Tier A/B/C at query time.

---

## Demo Chat 7 — Decision intelligence (record_decision)

**User:** Warum wurde Antrag an-001902 blockiert?

**Agent:**

1. `query_decisions` / `find_precedents` with scenario *„Antragsteller ohne Register-Eintragung“*
2. `get_causal_chain` on decision `antrag_block` → upstream `register_completeness → TierB_Teilweise`

```bash
python kdm/record_xunternehmen_decisions.py --reload-demo
```

MCP:

```bash
SEMANTICA_KG_PATH=.../upload/kdm/config/xunternehmen_kg_with_decisions.json
SEMANTICA_BUSINESS_RULES=.../upload/kdm/config/xunternehmen_business_rules.yaml
SEMANTICA_MAPPING_CONFIG=.../upload/kdm/config/xunternehmen_r2rml_db_mapping.yaml
```

Deploy bundle is refreshed by `python kdm/sync_upload_config.py` (also runs at end of `build_xunternehmen_graph.py` and `record_xunternehmen_decisions.py`).

**Agent:** Antrag blockiert, weil Juristische Person jp-000519 nur Tier B (keine Eintragung) — kausal verknüpft mit Register-Entscheidung.

---

## Agent playbook (ontology-first)

```text
1. User question → KDM classes & properties (JuristischePerson, eintragung, gesellschafter, …)
2. Semantica graph (xunternehmen_kg_with_decisions.json):
   - OntologyClass, BusinessRule, decision nodes
3. Physical mapping: config/xunternehmen_r2rml_db_mapping.yaml
4. Zuordnung tables for anschrift/kommunikation/eintragung/sitz links
5. Business tiers / subtypes: xunternehmen_business_rules.yaml → runtime CASE (no Hive view)
6. iceberg-mcp execute_query OR impyla with resolved SQL
7. High-stakes outcomes → record_decision + optional causal link
8. Answer in domain language (KDM terms, not raw column names)
```

### Runtime compilation

Business concepts like `TierA_Vollstaendig`, `InlandStrassenanschrift` are **not** Hive columns:

```text
ontology: TierA_Vollstaendig, RegisterEingetragen
    → xunternehmen_business_rules.yaml
    → sql_jp_data_quality_tier_expr()
    → SELECT CASE … END AS data_quality_tier FROM juristische_person …
```

`--print-sql-only` shows generated SQL without Hive execution.
