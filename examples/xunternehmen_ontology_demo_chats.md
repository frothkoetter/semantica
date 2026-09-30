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

## Agent Studio — Vollständiger Beispiel-Chat (Analytics)

**Workflow:** Manager OFF · Sequential · Agent 1 `ontology_mapper` (semantica) → Agent 2 `sql_executor` (iceberg-hive)

**MCP env (semantica):**

```
SEMANTICA_KG_PATH=/workflow_data/config/xunternehmen_kg_with_decisions.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/xunternehmen_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/xunternehmen_business_rules.yaml
HIVE_DATABASE=xunternehmen   # nur auf iceberg-hive Agent
```

### User

```
Wie viele juristische Personen haben sowohl eine Eintragung als auch einen Sitz?
Nutze die Business Rules aus dem Knowledge Graph.
```

### Agent 1 — ontology_mapper

**Tool:** `get_graph_summary` → `graph_ready: true`, OntologyClass `JuristischePerson`, …

**Tool:** `get_business_rules` → `RegisterEingetragen`, `HatSitz`, `organisation_completeness_rules`

**Output (Mapping Plan):**

```json
{
  "ready_for_sql": true,
  "question_intent": "Register-Vollständigkeit JuristischePerson",
  "ontology_terms": ["JuristischePerson", "Eintragung", "Sitz", "RegisterEingetragen", "HatSitz"],
  "business_rules_applied": ["RegisterEingetragen", "HatSitz"],
  "database": "xunternehmen",
  "tables": ["juristische_person", "zuordnung_eintragung", "zuordnung_sitz"],
  "joins": [
    {"from": "juristische_person jp", "to": "zuordnung_eintragung ze",
     "on": "ze.owner_id = jp.id AND ze.owner_typ = 'JuristischePerson'"},
    {"from": "juristische_person jp", "to": "zuordnung_sitz zs",
     "on": "zs.owner_id = jp.id AND zs.owner_typ = 'JuristischePerson'"}
  ],
  "metrics": [
    {"name": "juristische_personen", "expr": "COUNT(*)"},
    {"name": "vollstaendig_register",
     "expr": "SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END)"}
  ]
}
```

### Agent 2 — sql_executor

**Tool:** `execute_query`

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
  ON zs.owner_id = jp.id AND zs.owner_typ = 'JuristischePerson';
```

### Agent 3 — Antwort (Beispiel)

```
Von den juristischen Personen im Kerndatenmodell haben X % sowohl eine Eintragung
(RegisterEingetragen) als auch einen Sitz (HatSitz) — Y von Z Personen insgesamt.
Die Zuordnung läuft über zuordnung_eintragung und zuordnung_sitz mit owner_typ = 'JuristischePerson'.
```

### Phoenix — erwartete Tool-Kette

```text
semantica     → get_graph_summary
semantica     → get_business_rules
iceberg-hive  → execute_query
```

**Nicht:** `extract_entities`, `get_schema` vor Mapping Plan, Hive-Agent für YAML.

---

## Agent Studio — Beispiel-Chat (Governance / Entscheidung)

**User:**

```
Warum wurde Antrag an-001902 blockiert?
```

### Agent 1 — ontology_mapper

**Tool:** `get_graph_summary` → Graph enthält `decision`-Knoten

**Tool:** `get_business_rules` → `vorgang_readiness_rules`, `AntragEinreichbar`

**Output:** `ready_for_sql: false` — Governance-Frage, keine SQL nötig; Kontext an Agent 3.

### Agent 3 — answer_synthesizer (semantica)

**Tool:** `find_precedents`

```json
{ "scenario": "Antragsteller ohne Register-Eintragung" }
```

**Tool:** `get_causal_chain`

```json
{ "decision_id": "<antrag_block uuid>", "direction": "upstream" }
```

### Antwort (Beispiel)

```
Antrag an-001902 wurde blockiert, weil der Antragsteller (JuristischePerson jp-000519)
nur Tier B (TierB_Teilweise) hat — keine Register-Eintragung (RegisterEingetragen fehlt).
Kausale Kette: register_completeness → TierB_Teilweise → AntragBlockiert_RegisterUnvollstaendig.
```

**Kein** `execute_query` — Vorgangsdaten liegen im Graph (`decision`-Knoten), nicht als Hive-Tabelle `vorgang`.

Demo laden: `python kdm/record_xunternehmen_decisions.py --reload-demo`

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

## Audit, explainability, and comparing outcomes

Three layers participate in every Agent Studio turn. Only some are durable.

| Layer | What is stored | Durable? | Audit use |
|---|---|---|---|
| **A — Conversation** | Mapping plan, SQL, rows, chat answer | Session only | Agent Studio logs / export |
| **B — Semantica graph** | Ontology, BusinessRule, `decision` nodes, causal edges | Yes (`xunternehmen_kg_with_decisions.json`) | Precedents, causal chains |
| **C — Hive/Iceberg** | Live KDM tables | Yes (DB) | Re-run SQL; point-in-time counts |

Analytics demos (Chats 1–6) explain via **rules + mapping + SQL** (layers A + C). Governance demos (Chat 7) explain via **decision nodes** (layer B). Analytics turns are **not** written to the graph unless you call `record_decision`.

### Explainability chain (analytics)

```text
User question
  → get_business_rules (data_quality_tier_rules, anschrift_type_rules, …)
  → mapping plan (ontology_terms, business_rules_applied, tables, joins, metrics)
  → execute_query (SQL + rows)
  → answer_synthesizer (KDM-language reply)
```

Reproduce any analytics answer from the mapping plan JSON + SQL in the chat trace.

### Decision record shape (governance)

Each `decision` node in the graph stores:

| Field | Example |
|---|---|
| `category` | `vorgang_readiness`, `data_quality_tier`, `register_completeness` |
| `scenario` | *Antrag an-001902: Antragsteller jp-000519 ohne Register-Eintragung* |
| `reasoning` | *Antragsteller hat TierB_Teilweise — Einreichung blockiert…* |
| `outcome` | `AntragBlockiert_RegisterUnvollstaendig` |
| `confidence` | `0.89` |
| `decision_maker` | `kdm_vorgang_agent` |
| `entities` | Linked via `involves` edges (e.g. `Antrag/an-001902`, `JuristischePerson/jp-000519`) |

Causal links (demo): `jp_tier_b` —**CAUSED**→ `antrag_block`.

Reload demo decisions and run precedent comparison locally:

```bash
python kdm/record_xunternehmen_decisions.py --reload-demo --compare
```

### MCP tools for audit

| Tool | Agent | Purpose |
|---|---|---|
| `get_business_rules` | `ontology_mapper` | Declarative *why* (tiers, Anschrift, Vorgang rules) |
| `find_precedents` | `answer_synthesizer` | Similar past decisions by scenario text |
| `query_decisions` | `answer_synthesizer` | List/filter decisions by query or category |
| `get_causal_chain` | `answer_synthesizer` | Upstream/downstream *because-of* chain |
| `record_decision` | `answer_synthesizer` | Persist a new audited outcome (+ optional causal link) |

**Chat 7 — correct MCP trace (no SQL):**

```text
find_precedents({ "scenario": "Antragsteller ohne Register-Eintragung" })
get_causal_chain({ "decision_id": "<antrag_block uuid>", "direction": "upstream" })
```

### Comparing outcomes over time

**Analytics (SQL KPIs)** — data or rules may change between runs:

| Compare | How |
|---|---|
| Same question, different day | Re-run workflow; diff `sql` + `rows` from chat or Agent Ops logs |
| Rule change | Diff `xunternehmen_business_rules.yaml`; check `business_rules_applied` in mapping plan |
| Ontology/mapping change | Diff KG JSON + `xunternehmen_r2rml_db_mapping.yaml` |

**Governance (decisions)** — compare in the graph:

| Compare | How |
|---|---|
| Similar scenario, different outcome | `find_precedents` → similarity score + outcome/reasoning side by side |
| Root cause for one Antrag | `get_causal_chain` upstream (e.g. `TierB` → `AntragBlockiert`) |
| All Vorgang decisions | `query_decisions({ "category": "vorgang_readiness" })` |

### Recording analytics runs for audit (optional)

High-stakes KPI runs are not auto-persisted. Call `record_decision` after `sql_executor` to create a durable audit entry:

```json
{
  "category": "data_quality_tier",
  "scenario": "Tier-Verteilung JuristischePerson — Agent Studio 2026-09-25",
  "reasoning": "Runtime CASE from data_quality_tier_rules; JOIN zuordnung_eintragung + zuordnung_sitz; TierA=222, TierB=1163, TierC=1615",
  "outcome": "TierA_Vollstaendig:222,TierB_Teilweise:1163,TierC_Minimal:1615",
  "confidence": 0.95,
  "entities": ["https://w3id.org/kdm/JuristischePerson"],
  "decision_maker": "kdm_analytics_agent"
}
```

Later: `query_decisions({ "query": "Tier-Verteilung JuristischePerson" })`.

### Full audit bundle (one turn)

For compliance or post-mortem, capture:

1. **Mapping plan** — `ontology_terms`, `business_rules_applied`, `ready_for_sql`
2. **SQL** — exact query from `sql_executor`
3. **Rows** — Hive result at time T
4. **Decision** (if governance) — `scenario`, `reasoning`, `outcome`, `confidence`
5. **Causal chain** — `get_causal_chain` for linked decisions
6. **Artifact versions** — paths/mtimes of `xunternehmen_business_rules.yaml`, `xunternehmen_kg_with_decisions.json`, mapping YAML

Items 1–3 live in Agent Studio conversation context unless exported. Items 4–5 live in the graph (demo + any `record_decision` calls). Item 6 is under `/workflow_data/config/`.

### Agent routing for audit

| Question type | Path | Do not use |
|---|---|---|
| KPI / distribution / counts | `ontology_mapper` → `sql_executor` → `answer_synthesizer` | `find_precedents` alone |
| Warum blockiert / governance | `ontology_mapper` → `answer_synthesizer` + decision MCP tools | SQL on `vorgang` (table does not exist) |

Workflow: [`multi-agent-workflow-kdm.md`](../deploy/cloudera-agent-studio/multi-agent-workflow-kdm.md) — sequential, Manager OFF, one MCP per agent.

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
