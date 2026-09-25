# Agent Studio — Multi-Agent XUnternehmen KDM Workflow (End-to-End)

Conversational workflow: natural-language questions in **KDM terms** → ontology mapping → Hive SQL on database **`xunternehmen`** → business answer.

**Settings:** Conversational **ON** · Manager Agent **OFF** · Process **Sequential**

**One MCP server per agent.** Semantica has **no** `HIVE_*` credentials. The `sql_executor` must **not** attach semantica.

Demo chats: [`examples/xunternehmen_ontology_demo_chats.md`](../../examples/xunternehmen_ontology_demo_chats.md)

---

## Architecture

```text
User question (natural language, KDM terms)
    │
    ▼
┌─────────────────────┐
│ 1. ontology_mapper  │  semantica MCP only
│    get_graph_summary│  → mapping plan JSON (ready_for_sql)
│    get_business_rules│
└──────────┬──────────┘
           │ ready_for_sql: true
           ▼
┌─────────────────────┐
│ 2. sql_executor     │  iceberg-hive MCP only
│    execute_query    │  → result rows
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. answer_synthesizer│ semantica MCP (optional)
│    record_decision  │  → answer in KDM language
└─────────────────────┘
```

| Capability | semantica | iceberg-hive |
|---|---|---|
| Ontology / graph | yes | — |
| Business rules YAML | `get_business_rules` | — |
| SQL execution | — | `execute_query` |
| Schema introspection | — | `get_schema` (fallback only) |

---

## Step 0 — Prerequisites

On the CDSW workbench:

```bash
cd /home/cdsw/semantica   # or your clone path
python kdm/build_xunternehmen_graph.py --skip-hive
python kdm/sync_upload_config.py
```

Register both MCP servers in **Agent Studio → Tools Catalog → MCP Servers → Register**
(see [`README.md`](README.md)).

---

## Step 1 — Populate `workflow_data`

Copy the KDM deploy bundle into the workflow directory (replace `<workflow_dir>`):

```bash
WORKFLOW_DIR=/home/cdsw/agent-studio/studio-data/workflows/<workflow_dir>
mkdir -p "$WORKFLOW_DIR/workflow_data/config"

cp /home/cdsw/semantica/upload/kdm/config/xunternehmen_kg_with_decisions.json \
   "$WORKFLOW_DIR/workflow_data/config/"
cp /home/cdsw/semantica/upload/kdm/config/xunternehmen_business_rules.yaml \
   "$WORKFLOW_DIR/workflow_data/config/"
cp /home/cdsw/semantica/upload/kdm/config/xunternehmen_r2rml_db_mapping.yaml \
   "$WORKFLOW_DIR/workflow_data/config/"

ls -la "$WORKFLOW_DIR/workflow_data/config/"
```

---

## Step 2 — Create the workflow

**Agent Studio → Workflows → Create workflow**

| Setting | Value |
|---|---|
| Name | `XUnternehmen KDM Analytics` (or similar) |
| Conversational | **ON** |
| Manager Agent | **OFF** |
| Process | **Sequential** |

Add **three agents** in this exact order:

1. `ontology_mapper`
2. `sql_executor`
3. `answer_synthesizer` (optional)

> **Why Manager OFF?** The manager has no MCP tools and will delegate to agents that guess table names from backstory instead of calling `get_graph_summary`.

---

## Step 3 — Agent 1: `ontology_mapper`

### Agent fields (copy-paste)

**Role:**
```
ontology_mapper
```

**Goal:**
```
Resolve natural-language KDM analytics questions into XUnternehmen ontology terms
(JuristischePerson, Eintragung, Sitz, NatuerlichePerson, Anschrift, …) and a
structured SQL mapping plan for the sql_executor. Never execute SQL. Never call
import_ontology when the graph is pre-loaded. Output ready_for_sql and a JSON
mapping plan only.
```

**Background:**
```
You are the ontology and semantics layer for the XUnternehmen Kerndatenmodell (KDM)
(https://w3id.org/kdm/).

The knowledge graph is pre-built in xunternehmen_kg_with_decisions.json
(SEMANTICA_KG_PATH at /workflow_data/config/xunternehmen_kg_with_decisions.json).
It contains OntologyClass nodes, BusinessRule nodes, and demo decision nodes.
Physical table/column mappings live in xunternehmen_r2rml_db_mapping.yaml
(SEMANTICA_MAPPING_CONFIG). Business semantics (TierA_Vollstaendig, RegisterEingetragen,
HatSitz, Anschrift subtypes) come from xunternehmen_business_rules.yaml via
get_business_rules — many are runtime CASE expressions, not Hive columns.

Physical Hive database: xunternehmen. Core tables:
juristische_person, natuerliche_person, rechtsfaehige_personengesellschaft,
wirtschaftliche_taetigkeit, anschrift, eintragung, sitz, geburt, betriebsstaette,
wirtschaftszweig, rolle_gesellschafter.

Zuordnung (junction) tables for polymorphic links — always filter owner_typ:
- JuristischePerson.eintragung → zuordnung_eintragung (owner_typ = 'JuristischePerson')
- JuristischePerson.sitz → zuordnung_sitz (owner_typ = 'JuristischePerson')
- Anschrift / Kommunikation → zuordnung_anschrift, zuordnung_kommunikation

MANDATORY tool order:
1. Call get_graph_summary first. Include its raw JSON fields in your output.
2. If graph_ready is false OR node_count < 100: set ready_for_sql false and STOP.
   Never describe ontology classes from memory when the graph is not loaded.
3. Call get_business_rules before building the mapping plan.

NEVER call extract_entities or extract_relations. The graph and business rules are
already loaded — NER tools load heavy ML models and will timeout.

Common KDM resolution (use in mapping plan ontology_terms, not raw SQL here):
- JuristischePerson → juristische_person
- Eintragung on JuristischePerson → zuordnung_eintragung + eintragung (RegisterEingetragen rule)
- Sitz on JuristischePerson → zuordnung_sitz + sitz (HatSitz rule)
- NatuerlichePerson.geburt → geburt ON natuerliche_person_id
- Anschrift subtypes → runtime anschriftSubtype from business rules (not a Hive column)
- dataQualityTier → runtime CASE from data_quality_tier_rules (not a Hive column)

You do not have Hive credentials. Your job ends with a mapping plan the sql_executor
can run via execute_query.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | `semantica` **only** |
| Tools (check **only** these) | `get_graph_summary`, `get_business_rules`, `run_reasoning` |
| Tools (optional, agent 3) | `record_decision`, `query_decisions`, `find_precedents`, `get_causal_chain` |
| Tools (leave **unchecked**) | `extract_entities`, `extract_relations`, `import_ontology`, `add_entity`, `add_relationship`, `export_graph` |

### MCP env (workflow attach)

```
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/config/xunternehmen_kg_with_decisions.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/xunternehmen_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/xunternehmen_business_rules.yaml
SEMANTICA_MCP_TOOLSET=preloaded_graph
SEMANTICA_MCP_DISABLE_ML=true
SEMANTICA_LOG_LEVEL=INFO
```

### Task / instructions

```
For every user question:

1. Call get_graph_summary.
   - If node_count < 100 OR graph_ready is false: return
     {"ready_for_sql": false, "error": "Graph not loaded"} and STOP.

2. Call get_business_rules.
   - Use RegisterEingetragen, HatSitz, TierA/B/C rules when relevant.

3. Build a JSON mapping plan (do NOT write final SQL):

{
  "ready_for_sql": true,
  "question_intent": "<short description>",
  "ontology_terms": ["JuristischePerson", "Eintragung", "Sitz", "RegisterEingetragen", "HatSitz"],
  "business_rules_applied": ["RegisterEingetragen", "HatSitz"],
  "database": "xunternehmen",
  "tables": ["juristische_person", "zuordnung_eintragung", "zuordnung_sitz"],
  "joins": [
    {"from": "juristische_person jp", "to": "zuordnung_eintragung ze",
     "on": "ze.owner_id = jp.id AND ze.owner_typ = 'JuristischePerson'", "type": "LEFT"},
    {"from": "juristische_person jp", "to": "zuordnung_sitz zs",
     "on": "zs.owner_id = jp.id AND zs.owner_typ = 'JuristischePerson'", "type": "LEFT"}
  ],
  "filters": [],
  "metrics": [
    {"name": "vollstaendig_register",
     "expr": "SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END)"}
  ],
  "group_by": [],
  "reasoning_summary": "<1-3 sentences in KDM terms>"
}

4. Never call execute_query. Never call import_ontology.
5. Never call extract_entities or extract_relations.
6. Pass the mapping plan JSON to the next agent verbatim.
```

---

## Step 4 — Agent 2: `sql_executor`

### Agent fields

**Role:**
```
sql_executor
```

**Goal:**
```
Execute Hive SQL ONLY from the ontology_mapper mapping plan on database xunternehmen.
Return query results as structured data. Never invent schema or table names.
```

**Background:**
```
You have iceberg-hive MCP ONLY (execute_query, get_schema). You do NOT have semantica.

ABORT immediately if:
- There is no mapping plan JSON from ontology_mapper in the conversation, OR
- ready_for_sql is not true.

NEVER infer table names (juristische_person, zuordnung_eintragung, …) from your
training data or backstory. ONLY use tables, joins, filters, and metrics listed
in the mapping plan from agent 1.

Do not run SELECT * LIMIT 1 or get_schema for discovery unless the mapping plan
explicitly references unknown columns.

Database: xunternehmen. Fully qualify as xunternehmen.<table>.

Pass result rows to the next agent.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | `iceberg-hive` **only** — do **not** attach semantica |
| Tools | `execute_query` |

### MCP env

```
HIVE_HOST=<your-hive-host>
HIVE_PORT=443
HIVE_USER=<ldap-user>
HIVE_PASSWORD=<ldap-password>
HIVE_DATABASE=xunternehmen
HIVE_USE_HTTP_TRANSPORT=true
HIVE_HTTP_PATH=cliservice
HIVE_USE_SSL=true
HIVE_AUTH_MECHANISM=LDAP
```

### Task / instructions

```
1. Locate the mapping plan JSON from ontology_mapper in the conversation history.
2. If missing or ready_for_sql is not true: return {"status": "aborted", "reason": "no mapping plan"} and STOP.
3. Compose Hive SQL from tables, joins, filters, metrics, group_by, order_by in the plan.
4. Call execute_query with the SQL.
5. Return {"status": "ok", "sql": "<query>", "rows": <result>}.
```

---

## Step 5 — Agent 3: `answer_synthesizer` (optional)

**Role:** `answer_synthesizer`

**Goal:** Answer in KDM language (JuristischePerson, Eintragung, Sitz — not raw column names).

**MCP:** semantica only — optional `record_decision` for decision-intelligence demos.

---

## Step 6 — Verify graph before analytics

Start a **new conversation** and send only to agent 1 (or full workflow):

```
get_graph_summary
```

Expected:

```json
{
  "node_count": 198,
  "ontology_class_count": 36,
  "business_rule_count": 26,
  "kg_path": "/workflow_data/config/xunternehmen_kg_with_decisions.json",
  "graph_ready": true,
  "database_table_count": 0
}
```

`database_table_count: 0` is expected when the graph was built with `--skip-hive`.
Mapping still works via `SEMANTICA_MAPPING_CONFIG` and business rules YAML.

---

## End-to-end example — Demo Chat 1

### User question (German)

```
Wie viele juristische Personen haben sowohl eine Eintragung als auch einen Sitz?
```

### Correct tool trace

| Step | Agent | Tool | What happens |
|---|---|---|---|
| 1 | ontology_mapper | `get_graph_summary` | 198 nodes, graph_ready true |
| 2 | ontology_mapper | `get_business_rules` | RegisterEingetragen, HatSitz, Tier rules |
| 3 | ontology_mapper | — | Emits mapping plan JSON |
| 4 | sql_executor | `execute_query` | SQL from plan only |
| 5 | answer_synthesizer | — | Answer in KDM terms |

### Wrong trace (your symptom)

```
Initializing MCP servers... iceberg-hive + semantica
sql_executor → execute_query (no get_graph_summary, no mapping plan)
```

**Cause:** Only `sql_executor` in the workflow, or `sql_executor` has **both** MCPs attached, or Manager ON routed past ontology_mapper.

### Mapping plan (ontology_mapper)

```json
{
  "ready_for_sql": true,
  "question_intent": "Count JuristischePerson with both Eintragung and Sitz",
  "ontology_terms": ["JuristischePerson", "Eintragung", "Sitz", "RegisterEingetragen", "HatSitz"],
  "business_rules_applied": ["RegisterEingetragen", "HatSitz"],
  "database": "xunternehmen",
  "tables": ["juristische_person", "zuordnung_eintragung", "zuordnung_sitz"],
  "joins": [
    {"from": "juristische_person jp", "to": "zuordnung_eintragung ze",
     "on": "ze.owner_id = jp.id AND ze.owner_typ = 'JuristischePerson'", "type": "LEFT"},
    {"from": "juristische_person jp", "to": "zuordnung_sitz zs",
     "on": "zs.owner_id = jp.id AND zs.owner_typ = 'JuristischePerson'", "type": "LEFT"}
  ],
  "filters": ["jp.eingetragenerName IS NOT NULL"],
  "metrics": [
    {"name": "juristische_personen", "expr": "COUNT(*)"},
    {"name": "vollstaendig_register",
     "expr": "SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END)"},
    {"name": "pct_vollstaendig",
     "expr": "ROUND(100.0 * SUM(CASE WHEN ze.eintragung_id IS NOT NULL AND zs.sitz_id IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)"}
  ]
}
```

### SQL (sql_executor — from plan)

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
WHERE jp.eingetragenerName IS NOT NULL;
```

### Agent 3 answer (example)

```
Von den juristischen Personen im Kerndatenmodell haben X % sowohl eine Eintragung
(RegisterEingetragen) als auch einen Sitz (HatSitz) — Y von Z Personen insgesamt.
```

---

## Troubleshooting: MCP init or get_graph_summary takes minutes

**Symptom:** `Initializing MCP servers... semantica (4m)` or first `get_graph_summary` / `get_business_rules` very slow.

**Causes:**

1. **`uvx --from git+https://...`** installs the full Semantica package (torch, transformers, opencv, …) on every cold start — often **2–5 minutes** on CDSW.
2. **Old MCP behaviour:** `get_graph_summary` imported `ContextGraph` → pulled in **torch/sentence-transformers** (~5–30s) even for a 198-node JSON file.
3. Agent Studio **sandbox** may not persist `uvx` cache between sessions.

**Fixes:**

| Fix | Effect |
|---|---|
| Use **local clone** MCP: `"args": ["--from", "/home/cdsw/semantica", "semantica-mcp"]` | No git fetch; reuse workbench install |
| Pre-install once: `cd /home/cdsw/semantica && uv sync` | Warm deps on the worker |
| `SEMANTICA_MCP_TOOLSET=preloaded_graph` + `SEMANTICA_MCP_DISABLE_ML=true` | Blocks NER tools |
| **Updated semantica** (kg_snapshot fast path): `get_graph_summary` / `get_business_rules` read JSON/YAML only (~50ms) | No torch on status checks |
| For “Ist der Graph geladen?” use `get_graph_summary` — fast path returns `source: kg_file_snapshot` | |

**Expected after fix:** MCP subprocess start ~1–3s (local clone); `get_graph_summary` **&lt;1s**; first analytics question still loads ContextGraph only when tools like `record_decision` need the in-memory graph.

---

## Troubleshooting: sql_executor skips ontology

| Symptom | Fix |
|---|---|
| Log shows `sql_executor` only, no `ontology_mapper` | Add agent 1; verify **Sequential** order: ontology_mapper → sql_executor → answer_synthesizer |
| Both `semantica` and `iceberg-hive` initialize under `sql_executor` | Remove semantica from sql_executor — **one MCP per agent** |
| Agent writes SQL without `get_graph_summary` | Manager **OFF**; tighten sql_executor Background (abort without mapping plan) |
| Long hang on first tool | Uncheck `extract_entities` / `extract_relations` on ontology_mapper |
| Wrong database | `HIVE_DATABASE=xunternehmen` on iceberg-hive only (not airlinedata) |

### Conversational mode checklist

| Do | Don't |
|---|---|
| Manager **OFF**, Sequential **ON** | Single-agent workflow with sql_executor only |
| Agent 1: semantica only | Both MCPs on sql_executor |
| Agent 2: iceberg-hive only | sql_executor guessing `zuordnung_*` from backstory |
| First tools: `get_graph_summary`, `get_business_rules` | `get_schema` / `execute_query` before mapping plan |
| Abort when no mapping plan | Run SQL from LLM memory |

---

## Demo prompt catalog (KDM)

Each prompt should trigger: `get_graph_summary` → `get_business_rules` → mapping plan → `execute_query`.

| # | Prompt |
|---|--------|
| 1 | Wie viele juristische Personen haben sowohl eine Eintragung als auch einen Sitz? |
| 2 | Wie viele natürliche Personen haben keine verknüpfte Geburt? |
| 3 | Verteilung der Anschrift-Typen (Straße, Postfach, Ausland)? |
| 4 | Welche Personengesellschaften haben die meisten Gesellschafter? |
| 5 | Wirtschaftliche Tätigkeiten mit Hauptbetriebsstätte und Wirtschaftszweig? |
| 6 | Wie verteilen sich die Datenqualitäts-Tiers bei juristischen Personen? |
| 7 | Warum wurde Antrag an-001902 blockiert? (decision intelligence — agent 3 + query_decisions) |

More detail: [`examples/xunternehmen_ontology_demo_chats.md`](../../examples/xunternehmen_ontology_demo_chats.md)

---

## Related docs

- MCP registration: [`README.md`](README.md)
- KDM env template: [`workflow-env-kdm.template`](workflow-env-kdm.template)
- Airline reference workflow: [`multi-agent-workflow.md`](multi-agent-workflow.md)
