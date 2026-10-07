# Agent Studio — Multi-Agent Airline Workflow (End-to-End)

Conversational workflow: natural-language questions → ontology mapping → Hive SQL → business answer.

**Settings:** Conversational **ON** · Manager Agent **OFF** · Process **Sequential**

Generic agent Name / Role / Goal / Backstory: [`agent-config.md`](agent-config.md) (this doc adds airline-specific env and examples)

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
> See [Falsification demos](#falsification-demos-ontology-vs-hallucination) for A/B proof.

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
   Never claim you "already reviewed" the graph without a tool call in this turn.
2. If graph_ready is false OR node_count < 50: set ready_for_sql false and STOP.
   Never describe ontology classes from memory when the graph is not loaded.
3. Call get_business_rules before building the mapping plan.
4. Every mapping plan MUST include display_columns and invalid_columns_avoided
   (from sql_agent_hints.do_not_use) for any human-readable labels in results.
5. Set sql_patterns when flights is involved: single_edge_join for originAirport-only
   questions; aggregate_fact_first when both origin and destination are required.
   Never plan JOIN ... ON (origin = iata OR dest = iata).

NEVER call extract_entities or extract_relations. The graph and business rules
are already loaded — NER/extraction tools load heavy ML models and will timeout.
For OTP questions, use get_business_rules (on_time_max_delay: 15), not NER.

Business semantics (OTP, peak hours, delay severity) come from get_business_rules:
- OTP → ontology class OTP (equivalent OnTimePerformance); use otp.sql.expr for otp_pct
- 50 industry KPIs in get_business_rules → kpi_catalog (D0, A0, SevereDelayRate, ASM, …)
- On-time flight = OnTimeFlight: FAA 15-minute rule (arrdelay and depdelay <= 15, cancelled = 0)
- Derived classes: OnTimeFlight, DelayedFlight, MorningPeak, etc.

Common ontology links:
- Flight.operatedBy → JOIN airlines ON uniquecarrier = code
- Flight.assignedAircraft → JOIN planes ON tailnum
- Flight.originAirport → JOIN airports ON origin = iata
- Flight.destinationAirport → JOIN airports ON dest = iata
- Plane.manufacturer for aircraft manufacturer questions
- Flight.arrDelay / depDelay for delay analytics

Display columns (from get_business_rules sql_agent_hints — never guess "name"):
- Airline.airlineCode → airlines.code (NOT airlines.iata)
- Airline.description → airlines.description (NOT airlines.name)
- Airport.iata → airports.iata
- Airport.airportName → airports.airport (NOT airports.name)

You do not have Hive credentials. Your job ends with a mapping plan the
sql_executor can run via execute_query.
```

### MCP attachment (recommended: split registrations)

Register **two** Semantica MCP servers so each agent sees only the tools it needs:

| Registration JSON | MCP name | `SEMANTICA_MCP_TOOLSET` | Tools exposed |
|---|---|---|---|
| [`semantica-mcp-ontology.json`](semantica-mcp-ontology.json) | `semantica-ontology` | `ontology_mapper` | **2** — `get_graph_summary`, `get_business_rules` |
| [`semantica-mcp-decisions.json`](semantica-mcp-decisions.json) | `semantica-decisions` | `decision_store` | **7** — decision store tools |

Attach **`semantica-ontology`** to agent 1 only. Do **not** attach `semantica-decisions` here.

**Legacy (single registration):** one `semantica` MCP with UI checkboxes — check only
`get_graph_summary`, `get_business_rules`. Or `SEMANTICA_MCP_TOOLSET=ontology_mapper`.

Never enable on ontology_mapper: `extract_entities`, `extract_relations`, `import_ontology`,
`add_entity`, `add_relationship`, `export_graph` (ML hang / not needed when graph is pre-loaded).

### MCP env — `semantica-ontology` (workflow attach)

```
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/airline_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/airline_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/airline_business_rules.yaml
SEMANTICA_MCP_TOOLSET=ontology_mapper
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

3. Build a JSON mapping plan (do NOT write final SQL). REQUIRED fields:

{
  "ready_for_sql": true,
  "question_intent": "<short description>",
  "ontology_terms": ["Flight", "Airline", ...],
  "business_rules_applied": ["on_time_max_delay: 15", ...],
  "tables": ["flights", "airlines"],
  "joins": [
    {"edge": "operatedBy", "on": "flights.uniquecarrier = airlines.code"}
  ],
  "display_columns": {
    "Airline.airlineCode": "airlines.code",
    "Airline.description": "airlines.description",
    "Airport.iata": "airports.iata",
    "Airport.airportName": "airports.airport"
  },
  "invalid_columns_avoided": [
    "flights.carrier", "airlines.iata", "airlines.name", "airports.name"
  ],
  "filters": ["year = 2008", "cancelled = 0"],
  "metrics": [
    {"name": "avg_arr_delay", "expr": "AVG(arrdelay)"}
  ],
  "group_by": ["airlines.code", "airlines.description"],
  "order_by": "avg_arr_delay DESC",
  "sql_patterns": {
    "strategy": "single_edge_join",
    "avoid": ["OR in JOIN predicate"],
    "notes": "One equality join; filter year and cancelled before join"
  },
  "reasoning_summary": "<1-3 sentences>"
}

Include only display_columns needed for this question (omit unused ontology properties).
When joining airports, always set Airport.airportName → airports.airport — never airports.name.

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

Use ONLY column names from mapping plan display_columns and group_by — never infer
"name" for airlines or airports (use description / airport per sql_agent_hints).
Call get_schema only after a compile error, not for discovery when the plan is complete.

EFFICIENT SQL (flights has ~86M rows; airports ~300):
- Filter early: year, crsdeptime, cancelled = 0 BEFORE any join.
- Equality joins only — NEVER: JOIN airports a ON (f.origin = a.iata OR f.dest = a.iata).
- Aggregate on fact keys first, then join small result to airports/airlines.
- Do not use COUNT(CASE WHEN f.origin = a.iata THEN 1 END) when the join already
  encodes the match — that pattern usually means the join design is wrong.
- If the mapping plan says originAirport only, do not add destinationAirport.
- Follow sql_patterns.strategy in the mapping plan (see § Efficient SQL patterns).

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
   Use display_columns for SELECT labels — never airports.name or airlines.name.
   Apply efficient SQL patterns (§ below) — reject OR-join designs on flights.
4. Call execute_query with the SQL.
5. Return {"status": "ok", "sql": "<query>", "rows": <result>}.
```

---

## Efficient SQL patterns (airline / Hive)

`airlinedata.flights` is ~86M rows; `airports` and `airlines` are small dimensions.
Agents must **not** join the full fact table to a dimension with `OR`, then aggregate.

### Anti-pattern (slow — nested loop / row explosion)

```sql
-- BAD: OR join + redundant CASE — minutes to hours on 86M rows
SELECT a.iata, a.airport,
  COUNT(CASE WHEN f.origin = a.iata THEN 1 END) AS total_departures,
  COUNT(CASE WHEN f.dest = a.iata THEN 1 END) AS total_arrivals
FROM airlinedata.flights f
LEFT JOIN airlinedata.airports a
  ON (f.origin = a.iata OR f.dest = a.iata)
WHERE f.year BETWEEN 2000 AND 2005
  AND f.crsdeptime BETWEEN 1000 AND 1659
GROUP BY a.iata, a.airport;
```

| Problem | Effect |
|---------|--------|
| `OR` in JOIN | Optimizer cannot hash-join; scans/flights × airports |
| Join before aggregate | Millions of intermediate rows |
| `CASE` inside `COUNT` | Extra expression eval on inflated row set |

### Pattern A — origin only (`originAirport` / congestion at departure)

Use when the question says congestion, severe delay, or hub departures **at** an airport
(ontology: `Flight.originAirport` → `flights.origin = airports.iata`).

```sql
SELECT
  a.iata AS airport_code,
  a.airport AS airport_name,
  COUNT(*) AS total_departures,
  SUM(CASE WHEN GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60
           THEN 1 ELSE 0 END) AS severe_delay_departures
FROM airlinedata.flights f
JOIN airlinedata.airports a ON f.origin = a.iata
WHERE f.year BETWEEN 2000 AND 2005
  AND f.crsdeptime BETWEEN 1000 AND 1659
  AND f.cancelled = 0
GROUP BY a.iata, a.airport
ORDER BY severe_delay_departures DESC
LIMIT 10;
```

One fact scan · one equality join · ~300 groups.

### Pattern B — departures **and** arrivals (both edges)

Use when the user explicitly asks for **both** departures and arrivals. Split into two
pre-aggregations; join ~300-row summaries to `airports` — never OR-join the fact table.

```sql
WITH dep AS (
  SELECT
    f.origin AS iata,
    COUNT(*) AS total_departures,
    SUM(CASE WHEN GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60
             THEN 1 ELSE 0 END) AS severe_delay_departures
  FROM airlinedata.flights f
  WHERE f.year BETWEEN 2000 AND 2005
    AND f.crsdeptime BETWEEN 1000 AND 1659
    AND f.cancelled = 0
  GROUP BY f.origin
),
arr AS (
  SELECT
    f.dest AS iata,
    COUNT(*) AS total_arrivals,
    SUM(CASE WHEN GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60
             THEN 1 ELSE 0 END) AS severe_delay_arrivals
  FROM airlinedata.flights f
  WHERE f.year BETWEEN 2000 AND 2005
    AND f.crsdeptime BETWEEN 1000 AND 1659
    AND f.cancelled = 0
  GROUP BY f.dest
)
SELECT
  a.iata AS airport_code,
  a.airport AS airport_name,
  COALESCE(d.total_departures, 0) AS total_departures,
  COALESCE(r.total_arrivals, 0) AS total_arrivals,
  COALESCE(d.severe_delay_departures, 0) AS severe_delay_departures,
  COALESCE(r.severe_delay_arrivals, 0) AS severe_delay_arrivals
FROM airlinedata.airports a
LEFT JOIN dep d ON a.iata = d.iata
LEFT JOIN arr r ON a.iata = r.iata
ORDER BY total_departures DESC
LIMIT 20;
```

Two filtered scans · two hash aggregates · tiny dimension join.

### Mapping plan hint (`sql_patterns`)

ontology_mapper should set this when both origin and destination are needed:

```json
"sql_patterns": {
  "strategy": "aggregate_fact_first",
  "avoid": ["JOIN airports ON (origin = iata OR dest = iata)"],
  "aggregation_keys": [
    {"edge": "originAirport", "group_by": "flights.origin"},
    {"edge": "destinationAirport", "group_by": "flights.dest"}
  ],
  "notes": "Pre-aggregate dep and arr CTEs; join airports last"
}
```

For origin-only questions: `"strategy": "single_edge_join"`, one join in `joins[]`.

### Physical tuning (optional, table design)

| Lever | Benefit |
|-------|---------|
| Partition `flights` by `year` | Prunes to 2000–2005 slice |
| Iceberg sort on `(year, origin)` | Faster departure aggregations |
| Always filter `cancelled = 0` | Matches business rules, fewer rows |

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
names, in the narrative.

When the user asks to record/save/audit a decision, or after ranked KPI analysis,
you MUST call record_decision — never substitute a Markdown "Decision Record".
Pass category, scenario, reasoning, outcome, confidence, query_intent, query_params,
result_metrics, and sql_text from the SQL step.
```

### MCP attachment

| Setting | Value |
|---|---|
| MCP server | **`semantica-decisions`** (from [`semantica-mcp-decisions.json`](semantica-mcp-decisions.json)) |
| Toolset | `decision_store` — **7 tools**, all pre-selected |

Tools exposed: `record_decision`, `compare_with_history`, `query_decisions`,
`get_decision_store_status`, `explain_decision_delta`, `find_precedents`, `get_causal_chain`.

Do **not** attach `semantica-ontology` here (no graph/rules tools needed for synthesis).

### MCP env — `semantica-decisions` (workflow attach)

```
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/airline_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/airline_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/airline_business_rules.yaml
SEMANTICA_DECISION_STORE=/workspace/decisions
SEMANTICA_MCP_TOOLSET=decision_store
SEMANTICA_LOG_LEVEL=INFO
```

> **Important:** `/workflow_data` is **read-only** in the MCP sandbox. Decisions must
> be written to `/workspace/decisions` (session artifacts, visible in Agent Studio UI).
> Do not use `/workflow_data/decisions` — it will always fail with EROFS.

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

## Example — Midday severe delay congestion (2000–2005)

### User question

```
What airports had the most congestion and severe delays during midday between 2000 and 2005?
```

### Mapping plan (ontology_mapper)

```json
{
  "ready_for_sql": true,
  "question_intent": "Airports with most SevereDelay flights during Midday 2000-2005",
  "ontology_terms": ["Flight", "Airport", "SevereDelay", "Midday", "originAirport"],
  "business_rules_applied": [
    "SevereDelay: GREATEST(arrdelay, depdelay) > 60",
    "Midday: crsdeptime BETWEEN 1000 AND 1659",
    "cancelled = 0"
  ],
  "tables": ["flights", "airports"],
  "joins": [
    {"edge": "originAirport", "on": "flights.origin = airports.iata"}
  ],
  "display_columns": {
    "Airport.iata": "airports.iata",
    "Airport.airportName": "airports.airport"
  },
  "invalid_columns_avoided": ["airports.name"],
  "filters": [
    "flights.year BETWEEN 2000 AND 2005",
    "flights.cancelled = 0",
    "flights.crsdeptime BETWEEN 1000 AND 1659",
    "GREATEST(COALESCE(flights.arrdelay,0), COALESCE(flights.depdelay,0)) > 60"
  ],
  "metrics": [{"name": "severe_delay_count", "expr": "COUNT(*)"}],
  "group_by": ["airports.iata", "airports.airport"],
  "order_by": "severe_delay_count DESC",
  "limit": 10
}
```

### SQL (sql_executor)

```sql
SELECT
  ap.iata,
  ap.airport AS airport_name,
  COUNT(*) AS severe_delay_count
FROM airlinedata.flights f
JOIN airlinedata.airports ap ON f.origin = ap.iata
WHERE f.year BETWEEN 2000 AND 2005
  AND f.cancelled = 0
  AND f.crsdeptime BETWEEN 1000 AND 1659
  AND GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60
GROUP BY ap.iata, ap.airport
ORDER BY severe_delay_count DESC
LIMIT 10;
```

> **Common failure:** first SQL uses `ap.name` → Hive compile error. The mapping plan
> `display_columns` and `invalid_columns_avoided` prevent this when ontology_mapper
> calls `get_business_rules` (see `sql_agent_hints.airport_name_column: airport`).

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

## Falsification demos (ontology vs hallucination)

Controlled **A/B tests** that disprove the claim that an LLM can reliably guess Hive
column names and join keys. Run the **same prompt** in two sessions; compare SQL and
`execute_query` outcomes.

| Arm | Setup | Expected |
|-----|--------|----------|
| **A — Hallucination** | Manager **ON**, or `sql_executor` only (no `ontology_mapper`) | Wrong columns (`carrier`, `iata`, `name`), invented FKs (`airline_id`), compile errors or 0 rows |
| **B — Deterministic ontology** | Sequential: `ontology_mapper` → `sql_executor` | `get_graph_summary` + `get_business_rules` + mapping plan; joins from `airline_r2rml_db_mapping.yaml` `foreign_keys` |

### Quick falsification prompt (use in both arms)

```
Top 5 airlines by on-time performance in 2005. Join flights to airline names.
```

| Check | Arm A (guess) | Arm B (ontology) |
|-------|---------------|------------------|
| Join in SQL | `f.carrier = a.iata` ❌ | `f.uniquecarrier = a.code` ✅ |
| Name column | `a.name` ❌ | `a.description` ✅ |
| Airport name | `ap.name` ❌ | `ap.airport` ✅ |
| OTP rule | invented | `get_business_rules` → 15 min, arr+dep |
| `execute_query` | error / 0 rows | 5 rows |
| Auditable | no | optional `record_decision` + `sql_hash` |

**Ground truth:** `upload/airlinedata/config/airline_r2rml_db_mapping.yaml`
(`invalid_columns`, `foreign_keys`), `airline_business_rules.yaml`, `airline_graph.json`.

Full worked pairs (airport joins, `flights_csv`, invented `flight_id`, OTP semantics):
[`examples/airline_ontology_falsification_examples.md`](../../examples/airline_ontology_falsification_examples.md)

Related demo chats:

- Correct analytics: [`examples/airline_ontology_demo_chats.md`](../../examples/airline_ontology_demo_chats.md)
- Logistics outliers + Decision Store: [`examples/airline_logistics_outlier_demo_chats.md`](../../examples/airline_logistics_outlier_demo_chats.md)

---

## Demo prompt catalog (advanced KPIs)

Copy-paste prompts for Agent Studio conversations. Each should trigger:
`get_graph_summary` → `get_business_rules` → mapping plan → `execute_query`.

Use ontology terms where noted — they map to `airline_graph.json` and
`airline_business_rules.yaml`. Tables: `airlinedata.flights`, `airlines`, `airports`, `planes` only.

### On-Time Performance (OTP)

Uses `OnTimeFlight` and FAA **15-minute rule** from `get_business_rules`.

| # | Prompt |
|---|--------|
| 1 | Which top-10 carriers by volume had the best and worst OTP each year from 2003–2008? Show year-over-year change. |
| 2 | Compare OTP during **MorningPeak**, **EveningPeak**, and **Overnight** for Delta and Southwest in 2007. Which time window hurts OTP most? |
| 3 | For the top 5 **HubAirport** hubs by departures in 2008, which hub has the highest OTP and which the lowest? |
| 4 | Between 2000 and 2008, which **Plane.manufacturer** had the highest average OTP on segments with at least 50,000 flights? |
| 5 | What are the 10 **Route** pairs (origin–dest) with at least 1,000 flights in 2008 and the worst OTP? |

### Delay severity

Uses `MinorDelay`, `ModerateDelay`, `SevereDelay`, `DelayedFlight`.

| # | Prompt |
|---|--------|
| 6 | For American, United, and JetBlue in 2008: what share of non-cancelled flights were **OnTimeFlight**, **MinorDelay**, **ModerateDelay**, and **SevereDelay**? |
| 7 | Which airports as **originAirport** had the highest rate of **SevereDelay** flights in 2008 (min 10,000 departures)? |
| 8 | For delayed flights in 2008, what percentage had arrival delay > departure delay vs the opposite? Break down by **Airline**. |

### Delay attribution (DOT causes)

Uses `delay_reason_priority` and `delay_reason_columns` from business rules.

| # | Prompt |
|---|--------|
| 9 | For Southwest in 2008, which **DelayReason** (carrier, weather, NAS, security, late aircraft) accounts for the most total delay minutes? |
| 10 | Compare total **WeatherDelayReason** vs **CarrierDelayReason** minutes for the five largest carriers in 2008. Who is most weather-sensitive? |
| 11 | Which carriers have the highest **LateAircraftDelayReason** share of total delay minutes in 2007–2008? |

### Time windows & operations

Uses `MorningPeak`, `Midday`, `EveningPeak`, `Overnight`.

| # | Prompt |
|---|--------|
| 12 | Which **TimeWindow** had the most **Flight** departures nationally in 2008? Show counts and share of total. |
| 13 | Is OTP for **Overnight** flights better or worse than **MorningPeak** for the same carriers in 2008? |
| 14 | Show OTP by hour of scheduled departure (`crsdeptime`) for 2008 — identify the worst 3 hour bands. |

### Network, routes & logistics

Uses `Route`, `HubAirport`, `Flight.originAirport` / `destinationAirport`.

| # | Prompt |
|---|--------|
| 15 | List the top 20 **HubAirport** by departures in 2008. How many unique **Route** destinations does each serve? |
| 16 | Split **Route** by distance quartile using `distance`. Which quartile has the best OTP in 2008? |
| 17 | From LAX in 2007: top 10 destinations by volume, average **arrDelay**, and OTP for each. |
| 18 | Which carriers had the highest **CancelledFlight** rate in 2008 among carriers with ≥100,000 segments? |

### Aircraft & fleet

Uses `Plane`, `Flight.assignedAircraft`.

| # | Prompt |
|---|--------|
| 19 | For Boeing vs Airbus segments in 2008: compare average **arrDelay** and OTP (manufacturers with ≥100k flights). |
| 20 | Which **Airline** operated the most distinct **Plane** tail numbers in 2008? Does fleet diversity correlate with lower average delay? |
| 21 | Show **Plane.manufacturer** segment share by year 2000–2008. Did Airbus gain share on high-volume routes? |

### Executive / multi-KPI scorecards

| # | Prompt |
|---|--------|
| 22 | Build a 2008 scorecard for carriers with ≥50,000 flights: OTP %, avg **arrDelay**, **SevereDelay** rate, cancellation rate, and dominant **DelayReason**. Rank top 5 performers. |
| 23 | Which carriers improved OTP the most from 2007 to 2008 (min 25k flights each year)? |
| 24 | Compare **DivertedFlight** and **CancelledFlight** counts by carrier in 2008. Any carrier with unusually high diversions? |
| 25 | For carriers in the bottom OTP quartile in 2008, is low OTP driven more by **CarrierDelayReason** or **NASDelayReason**? |
| 26 | Define reliability = 0.5×OTP + 0.3×(1 − severe_delay_rate) + 0.2×(1 − cancellation_rate). Rank airlines in 2008. |

### Reasoning (`run_reasoning` optional)

| # | Prompt |
|---|--------|
| 27 | Hawaiian had the best OTP in 2005. Using facts from the query and rules from `get_business_rules`, explain what factors typically drive high OTP for a small carrier. |
| 28 | If the FAA on-time threshold changed from 15 to 30 minutes, how would **OnTimeFlight** vs **DelayedFlight** classification shift for 2008? Estimate from rules, then validate with SQL. |

### German prompts

| # | Prompt |
|---|--------|
| 29 | Welche Carrier hatten 2008 die höchste OTP in der **EveningPeak** — und wie schneiden sie in **MorningPeak** ab? |
| 30 | Zeige für 2008 die Top-5 **HubAirport** nach Abflügen und deren durchschnittliche **Ankunftsverzögerung**. |
| 31 | Welcher **DelayReason** dominiert bei **DelayedFlight** für United und Southwest in 2008? |

### Prompt tips

| Technique | Example |
|-----------|---------|
| Name ontology classes | "OTP for **OnTimeFlight**", "**operatedBy** Airline" |
| Set volume filters | "min 5,000 flights", "≥100,000 segments" |
| Anchor business rules | "Use FAA 15-minute rule from `get_business_rules`" |
| Request breakdowns | "by year", "by carrier", "by **TimeWindow**" |
| Business rules only | `get_business_rules` — never ask Hive agent to read YAML |

More worked examples: [`examples/airline_ontology_demo_chats.md`](../../examples/airline_ontology_demo_chats.md) ·
Falsification A/B: [`examples/airline_ontology_falsification_examples.md`](../../examples/airline_ontology_falsification_examples.md)

---

## Troubleshooting: wrong agent or tool

### Business rules → Hive agent

**Symptom:** Manager delegates to "Principal Hive/Iceberg Data Engineer"; agent runs `get_schema` or says YAML is not accessible.

**Fix:** Manager **OFF**. Business rules use semantica **`get_business_rules`** on `ontology_mapper` — not iceberg-hive. Test with prompt: `get_business_rules`.

### Graph empty on new worker

**Symptom:** `get_graph_summary` → `graph_ready: false`, new `hostname`, wrong path like `/workflow_data/config/airline_graph.json`.

**Fix:** Graph file belongs in `/workflow_data/data/airline_graph.json`. Re-copy `workflow_data` on the current worker. See [`README.md`](README.md) §5–6.

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

**Toolset presets** (`SEMANTICA_MCP_TOOLSET`):

| Preset | Tools | Agent |
|--------|-------|-------|
| `ontology_mapper` | 2 | ontology_mapper |
| `decision_store` / `answer_synthesizer` | 7 | answer_synthesizer |
| `preloaded_graph` | 10 | single-agent / dev (union of both + `run_reasoning`) |

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
| `get_business_rules` for rules/YAML | Delegate to Hive agent or `get_schema` |
| Manager **OFF** for rules/graph/SQL | Manager delegates to wrong specialist |

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
- Falsification demos (ontology vs guessing): [`examples/airline_ontology_falsification_examples.md`](../../examples/airline_ontology_falsification_examples.md)
- Logistics outlier demos: [`examples/airline_logistics_outlier_demo_chats.md`](../../examples/airline_logistics_outlier_demo_chats.md)
- Decision Store spec: [`docs/guides/decision-store.md`](../../docs/guides/decision-store.md)
- Workflow env template: [`workflow-env.template`](workflow-env.template)
