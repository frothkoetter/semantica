# Agent Studio — Multi-Agent Airline Workflow (End-to-End)

Conversational workflow: natural-language questions → ontology mapping → Hive SQL → business answer.

**Settings:** Conversational **ON** · Manager Agent **OFF** · Process **Sequential**

One MCP server per agent. Semantica has **no** `HIVE_*` credentials.

---

## Architecture

```text
User question (natural language)
    │
    ▼
┌─────────────────────┐
│ 1. ontology_mapper  │  semantica MCP
│    get_graph_summary│  → mapping plan JSON (ready_for_sql)
│    get_business_rules│
└──────────┬──────────┘
           │ ready_for_sql: true
           ▼
┌─────────────────────┐
│ 2. sql_executor     │  iceberg-hive MCP
│    execute_query    │  → result rows
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. answer_synthesizer│ semantica MCP (optional)
│    record_decision  │  → ontology-language answer
└─────────────────────┘
```

| Capability | semantica | iceberg-hive |
|---|---|---|
| Ontology / graph | yes | — |
| Business rules YAML | `get_business_rules` | — |
| SQL execution | — | `execute_query` |
| Schema introspection | — | `get_schema` |

---

## Step 0 — Prerequisites

On the CDSW workbench:

```bash
cd /home/cdsw
git clone https://github.com/frothkoetter/semantica.git semantica
git clone <iceberg-mcp-server-hive-repo-url> iceberg-mcp-server-hive

cd semantica
uv run python scripts/build_airline_graph.py   # needs Hive; produces data/airline_graph.json
```

Register both MCP servers in **Agent Studio → Tools Catalog → MCP Servers → Register**
(see [`README.md`](README.md) for JSON templates).

---

## Step 1 — Populate `workflow_data`

Agent Studio bind-mounts `workflow_data` at **`/workflow_data/`** inside the MCP sandbox.
Copy artifacts once per workflow (replace `<workflow_dir>`, e.g. `semanticus__eoNcbDVo`):

```bash
WORKFLOW_DIR=/home/cdsw/agent-studio/studio-data/workflows/<workflow_dir>
mkdir -p "$WORKFLOW_DIR/workflow_data/data" "$WORKFLOW_DIR/workflow_data/config"

cp /home/cdsw/semantica/data/airline_graph.json \
   "$WORKFLOW_DIR/workflow_data/data/"
cp /home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml \
   "$WORKFLOW_DIR/workflow_data/config/"
cp /home/cdsw/semantica/config/airline_business_rules.yaml \
   "$WORKFLOW_DIR/workflow_data/config/"

ls -la "$WORKFLOW_DIR/workflow_data/data/airline_graph.json"
```

---

## Step 2 — Create the workflow

**Agent Studio → Workflows → Create workflow**

| Setting | Value |
|---|---|
| Name | `US DOT Airline Analytics` (or similar) |
| Conversational | **ON** |
| Manager Agent | **OFF** |
| Process | **Sequential** |

Add **three agents** in order (agent 3 is optional):

1. `ontology_mapper`
2. `sql_executor`
3. `answer_synthesizer` (optional)

> **Why Manager OFF?** Crew Manager delegates without MCP tools and tends to hallucinate
> graph content from backstory. Sequential routing sends the user message directly to agent 1.

---

## Step 3 — Agent 1: `ontology_mapper`

### Agent fields (copy-paste)

**Role:**
```
ontology_mapper
```

**Goal:**
```
Resolve natural-language analytics questions into US DOT airline ontology terms
(Flight, Airline, Plane, OnTimeFlight, …) and a structured SQL mapping plan for
the sql_executor. Never execute SQL. Never call import_ontology when the graph
is pre-loaded. Output ready_for_sql and a JSON mapping plan only.
```

**Background:**
```
You are the ontology and semantics layer for the US DOT airline demo
(https://w3id.org/demo/airline#).

The knowledge graph is pre-built in airline_graph.json (SEMANTICA_KG_PATH at
/workflow_data/data/airline_graph.json). It contains OntologyClass nodes, DB
table/column mappings (flights, airlines, airports, planes), and business
rules from airline_business_rules.yaml.

Physical Hive database: airlinedata. Materialized tables only:
flights, airlines, airports, planes — never *_csv views.

MANDATORY tool order:
1. Call get_graph_summary first. Return its raw JSON fields in your output.
2. If graph_ready is false OR node_count < 50: set ready_for_sql false and STOP.
   Never describe ontology classes from memory when the graph is not loaded.
3. Call get_business_rules before building the mapping plan.

NEVER call extract_entities or extract_relations. The graph and business rules
are already loaded — NER/extraction tools load heavy ML models and will timeout.
For OTP questions, use get_business_rules (on_time_max_delay: 15), not NER.

Business semantics (OTP, peak hours, delay severity) come from get_business_rules:
- On-time = FAA 15-minute rule (arrdelay and depdelay <= 15, cancelled = 0)
- Derived classes: OnTimeFlight, DelayedFlight, MorningPeak, etc.

Common ontology links:
- Flight.operatedBy → JOIN airlines ON uniquecarrier = code
- Flight.assignedAircraft → JOIN planes ON tailnum
- Plane.manufacturer for aircraft manufacturer questions
- Flight.arrDelay / depDelay for delay analytics

You do not have Hive credentials. Your job ends with a mapping plan the
sql_executor can run via execute_query.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | `semantica` |
| Tools (check **only** these) | `get_graph_summary`, `get_business_rules`, `run_reasoning` |
| Tools (optional) | `record_decision` (answer_synthesizer agent) |
| Tools (leave **unchecked**) | `extract_entities`, `extract_relations`, `import_ontology`, `add_entity`, `add_relationship`, `export_graph` |

In Agent Studio: edit agent → MCP → semantica → **uncheck** NER/extraction tools.
`extract_entities` loads spaCy/ML and can hang for minutes — it is not needed when the graph
is pre-loaded via `SEMANTICA_KG_PATH`.

**Optional:** `SEMANTICA_MCP_TOOLSET=preloaded_graph` in MCP env hides unused tools server-side
(useful if you prefer not to curate the checklist per agent).

### MCP env (workflow attach)

```
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/airline_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/airline_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/airline_business_rules.yaml
SEMANTICA_LOG_LEVEL=INFO
```

### Task / instructions (agent task description)

```
For every user question:

1. Call get_graph_summary.
   - If node_count < 50 OR graph_ready is false: return
     {"ready_for_sql": false, "error": "Graph not loaded"} and STOP.

2. Call get_business_rules.
   - Use thresholds (on_time_max_delay: 15) for OTP questions.

3. Build a JSON mapping plan (do NOT write final SQL):

{
  "ready_for_sql": true,
  "question_intent": "<short description>",
  "ontology_terms": ["Flight", "Airline", ...],
  "business_rules_applied": ["on_time_max_delay: 15", ...],
  "tables": ["flights", "airlines"],
  "joins": [
    {"from": "flights", "to": "airlines", "on": "flights.uniquecarrier = airlines.code"}
  ],
  "filters": ["year = 2008", "cancelled = 0"],
  "metrics": [
    {"name": "avg_arr_delay", "expr": "AVG(arrdelay)"}
  ],
  "group_by": ["airlines.description"],
  "order_by": "avg_arr_delay DESC",
  "reasoning_summary": "<1-3 sentences>"
}

4. Never call execute_query. Never call import_ontology.
5. Never call extract_entities or extract_relations (ML NER — will hang).
6. Do not call export_graph unless column mappings are required.
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
Execute Hive SQL from the ontology_mapper mapping plan on database airlinedata.
Return query results as structured data. Never invent schema — use the mapping plan.
```

**Background:**
```
You have iceberg-hive MCP only (execute_query, get_schema).

ABORT immediately if the mapping plan from ontology_mapper has ready_for_sql != true.

Allowed tables: flights, airlines, airports, planes (materialized only).
Database: airlinedata. Fully qualify as airlinedata.<table>.

Do not run SELECT * LIMIT 1 for discovery. Use joins, filters, and metrics from
the mapping plan. Apply business-rule filters (cancelled = 0, OTP thresholds)
as described in the plan.

Pass result rows to the next agent.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | `iceberg-hive` |
| Tools | `execute_query`, `get_schema` (fallback only) |

### MCP env (workflow attach — real credentials)

```
HIVE_HOST=<your-hive-host>
HIVE_PORT=443
HIVE_USER=<ldap-user>
HIVE_PASSWORD=<ldap-password>
HIVE_DATABASE=airlinedata
HIVE_USE_HTTP_TRANSPORT=true
HIVE_HTTP_PATH=cliservice
HIVE_USE_SSL=true
HIVE_AUTH_MECHANISM=LDAP
```

### Task / instructions

```
1. Read the mapping plan from ontology_mapper.
2. If ready_for_sql is not true, return {"status": "aborted"} and STOP.
3. Compose Hive SQL from tables, joins, filters, metrics, group_by, order_by.
4. Call execute_query with the SQL.
5. Return {"status": "ok", "sql": "<query>", "rows": <result>}.
```

---

## Step 5 — Agent 3: `answer_synthesizer` (optional)

### Agent fields

**Role:**
```
answer_synthesizer
```

**Goal:**
```
Answer the user's question in business/ontology language using SQL results.
Cite ontology terms (Flight, Airline, OnTimeFlight, etc.).
```

**Background:**
```
You receive the user question, ontology_mapper mapping plan, and sql_executor
results. Summarize findings clearly. Use ontology class names, not raw column
names, in the narrative. Optionally record the decision via record_decision.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | `semantica` |
| Tools | `record_decision` (optional) |

Use the same `/workflow_data/...` env as ontology_mapper if you attach semantica here.

---

## Step 6 — Verify graph before analytics

Start a **new conversation** and send:

```
get_graph_summary
```

Expected (abbreviated):

```json
{
  "node_count": 262,
  "ontology_class_count": 29,
  "kg_path": "/workflow_data/data/airline_graph.json",
  "kg_path_exists": true,
  "graph_ready": true,
  "business_rules_path_exists": true
}
```

If `graph_ready` is false, fix paths in [`README.md`](README.md) §5–6 before running analytics.

---

## End-to-end example

### User question (German)

```
Welche Airlines hatten 2008 die höchste durchschnittliche Ankunftsverzögerung?
```

### Expected tool trace

| Step | Agent | Tool | What happens |
|---|---|---|---|
| 1 | ontology_mapper | `get_graph_summary` | Confirms graph loaded (262 nodes) |
| 2 | ontology_mapper | `get_business_rules` | OTP rule: 15 min; flight status rules |
| 3 | ontology_mapper | — | Emits mapping plan JSON |
| 4 | sql_executor | `execute_query` | Runs SQL on `flights` JOIN `airlines` |
| 5 | answer_synthesizer | — | Answers in ontology terms |

### Agent 1 output (mapping plan)

```json
{
  "ready_for_sql": true,
  "question_intent": "Airlines with highest average arrival delay in 2008",
  "ontology_terms": ["Flight", "Airline", "arrDelay", "operatedBy"],
  "business_rules_applied": ["exclude cancelled flights"],
  "tables": ["flights", "airlines"],
  "joins": [
    {"from": "flights", "to": "airlines", "on": "flights.uniquecarrier = airlines.code"}
  ],
  "filters": ["flights.year = 2008", "flights.cancelled = 0", "flights.arrdelay IS NOT NULL"],
  "metrics": [
    {"name": "avg_arr_delay", "expr": "ROUND(AVG(flights.arrdelay), 1)"},
    {"name": "flight_count", "expr": "COUNT(*)"}
  ],
  "group_by": ["airlines.code", "airlines.description"],
  "order_by": "avg_arr_delay DESC",
  "limit": 10
}
```

### Agent 2 SQL (generated from plan)

```sql
SELECT
  a.description AS airline_name,
  a.code AS airline_code,
  ROUND(AVG(f.arrdelay), 1) AS avg_arr_delay,
  COUNT(*) AS flight_count
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2008
  AND f.cancelled = 0
  AND f.arrdelay IS NOT NULL
GROUP BY a.code, a.description
ORDER BY avg_arr_delay DESC
LIMIT 10;
```

### Agent 3 answer (example)

```
Im Jahr 2008 hatte American Airlines (AA) unter den großen Carriern die höchste
durchschnittliche Ankunftsverzögerung (Flight.arrDelay) bei abgeschlossenen Flügen
(cancelled = 0): etwa 12,6 Minuten über ~585.000 Flight-Segmente, gruppiert nach
Flight.operatedBy → Airline.
```

---

## Example — Best airline OTP in 2005

### User question

```
What airline has the best OTP in 2005?
```

### Correct tool trace (not extract_entities)

| Step | Tool | Purpose |
|---|---|---|
| 1 | `get_graph_summary` | Confirm graph loaded |
| 2 | `get_business_rules` | OTP = 15-min rule (`on_time_max_delay`) |
| 3 | — | Mapping plan → sql_executor |

### Mapping plan (ontology_mapper)

```json
{
  "ready_for_sql": true,
  "question_intent": "Airline with highest on-time performance in 2005",
  "ontology_terms": ["Flight", "Airline", "OnTimeFlight", "OnTimePerformance", "operatedBy"],
  "business_rules_applied": ["on_time_max_delay: 15", "cancelled = 0"],
  "tables": ["flights", "airlines"],
  "joins": [
    {"from": "flights", "to": "airlines", "on": "flights.uniquecarrier = airlines.code"}
  ],
  "filters": ["flights.year = 2005", "flights.cancelled = 0"],
  "metrics": [
    {
      "name": "otp_pct",
      "expr": "100.0 * SUM(CASE WHEN arrdelay <= 15 AND depdelay <= 15 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)"
    },
    {"name": "flight_count", "expr": "COUNT(*)"}
  ],
  "group_by": ["airlines.code", "airlines.description"],
  "order_by": "otp_pct DESC",
  "having": "COUNT(*) >= 1000"
}
```

### SQL (sql_executor)

```sql
SELECT
  a.description AS airline_name,
  a.code AS airline_code,
  ROUND(100.0 * SUM(CASE WHEN f.arrdelay <= 15 AND f.depdelay <= 15 THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0), 1) AS otp_pct,
  COUNT(*) AS flight_count
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2005
  AND f.cancelled = 0
GROUP BY a.code, a.description
HAVING COUNT(*) >= 1000
ORDER BY otp_pct DESC
LIMIT 5;
```

---

## Second example — Manufacturer OTP 2000–2008

### User question

```
Welche Flugzeughersteller flogen zwischen 2000 und 2008 die meisten Segmente,
und wie war die On-Time Performance pro Jahr?
```

### Key ontology resolution

| Concept | Mapping |
|---|---|
| Segments | `COUNT(*)` on `Flight` |
| Manufacturer | `Plane.manufacturer` via `Flight.assignedAircraft` → `planes.tailnum` |
| OTP | FAA 15-min rule from `get_business_rules` |
| Time range | `year BETWEEN 2000 AND 2008` |

### Expected SQL shape

```sql
SELECT
  p.manufacturer,
  f.year,
  COUNT(*) AS segments,
  ROUND(100.0 * SUM(CASE WHEN f.cancelled = 0 AND f.arrdelay <= 15 AND f.depdelay <= 15
    THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END), 0), 1)
    AS otp_pct
FROM airlinedata.flights f
JOIN airlinedata.planes p ON f.tailnum = p.tailnum
WHERE f.year BETWEEN 2000 AND 2008
  AND p.manufacturer IS NOT NULL
GROUP BY p.manufacturer, f.year
ORDER BY f.year, segments DESC;
```

---

## Troubleshooting: `extract_entities` hangs

**Symptom:** Tool log shows `extract_entities` with a long synthetic paragraph; run never completes.

**Cause:** The agent chose NER extraction instead of ontology tools. `extract_entities` instantiates
`NamedEntityRecognizer()` (spaCy/ML) on **every call** — first run can take many minutes in Agent Studio
(especially after cold `uvx` start).

**Fix (Agent Studio):**

1. Edit `ontology_mapper` → MCP → semantica → **uncheck** `extract_entities`, `extract_relations`
2. Ensure **checked:** `get_graph_summary`, `get_business_rules` (+ optional `run_reasoning`)
3. Add to agent Background: `First tool: get_graph_summary. Never call extract_entities.`
4. Restart workflow session

**Optional server-side filter:** `SEMANTICA_MCP_TOOLSET=preloaded_graph` in MCP env (hides NER
tools from `tools/list` even if left checked).

**Fallback:** `SEMANTICA_MCP_DISABLE_ML=true` — if the agent still calls NER tools, they fail
fast instead of loading spaCy.

**Wrong trace (your log):**

```
extract_entities({"text": "On-Time Performance (OTP) is a KPI defined in..."})
```

**Correct trace for OTP 2005:**

```
get_graph_summary({})
get_business_rules({})
→ mapping plan JSON
→ sql_executor: execute_query(...)
```

If the agent role shows as "Lead Semantic Architect" or similar, ensure **Manager is OFF** and
agent 1 is `ontology_mapper` with the restricted tool list above.

---

## Conversational mode tips

| Do | Don't |
|---|---|
| Manager **OFF**, Sequential **ON** | Crew Manager ON (no MCP access, hallucination risk) |
| First tool call: `get_graph_summary` | Describe graph from backstory when `graph_ready: false` |
| `get_business_rules` for OTP/delay | `extract_entities` (ML NER — hangs) |
| Uncheck NER tools on ontology_mapper | Leave all 15 semantica tools enabled |
| Use `/workflow_data/...` MCP paths | `/home/cdsw/semantica/...` in workflow env |
| One MCP per agent | Both semantica + iceberg-hive on same agent |
| Abort when `ready_for_sql: false` | Run SQL against empty graph |

---

## Build-time (not runtime)

```bash
cd /home/cdsw/semantica
export HIVE_DATABASE=airlinedata HIVE_HOST=... HIVE_USER=... HIVE_PASSWORD=...
uv run python scripts/build_airline_graph.py
```

Or chain MCP at build time:

1. `iceberg-hive.get_database_schema_info({database: "airlinedata"})`
2. `semantica.map_db_schema_to_ontology({schema_info, apply_mappings: true})`

Then copy outputs into `workflow_data/` (Step 1).

---

## Related docs

- MCP registration and paths: [`README.md`](README.md)
- Demo chat transcripts: [`examples/airline_ontology_demo_chats.md`](../../examples/airline_ontology_demo_chats.md)
- Workflow env template: [`workflow-env.template`](workflow-env.template)
