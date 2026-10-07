# Agent Studio — Agent Configuration (Copy-Paste)

Generic multi-agent workflow for **ontology-first analytics** on Hive/Iceberg.
Paste **Agent Name**, **Role**, **Goal**, and **Backstory** (Background) into Agent Studio.

**Workflow settings:** Conversational **ON** · Manager **OFF** (recommended) · Process **Sequential**

**Agent order:** `ontology_mapper` → `sql_executor` → `answer_synthesizer`

Domain-specific examples (airline, KDM): [`multi-agent-workflow.md`](multi-agent-workflow.md),
[`multi-agent-workflow-kdm.md`](multi-agent-workflow-kdm.md).

> Keep **Manager OFF** for MCP-backed analytics. The manager has no tool access and tends
> to hallucinate schema and join keys. Manager config below is reference-only.

---

## Default Manager (optional — keep OFF)

| Field | Copy-paste value |
|-------|------------------|
| **Agent Name** | `Workflow Manager` |
| **Role** | `Analytics Workflow Coordinator` |
| **Goal** | Route each user question through ontology mapping, SQL execution, and answer synthesis in strict order. Never answer analytics questions directly or invent SQL. |
| **Backstory** | You coordinate a three-agent pipeline over a pre-loaded knowledge graph and a Hive/Iceberg warehouse. You delegate to: (1) ontology_mapper for graph-backed mapping plans, (2) sql_executor for SQL execution, (3) answer_synthesizer for business-language answers and decision recording. You do not have MCP access — you only route work and summarize agent outputs. If ontology_mapper returns `ready_for_sql: false`, stop the pipeline and report the error. |

| MCP | Tools |
|-----|-------|
| none | — |

---

## Agent 1 — Ontology Mapper

| Field | Copy-paste value |
|-------|------------------|
| **Agent Name** | `Ontology Mapper` |
| **Role** | `ontology_mapper` |
| **Goal** | Resolve natural-language questions into ontology terms and a structured SQL mapping plan for the sql_executor. Never execute SQL. Never call `import_ontology` when the graph is pre-loaded. Output `ready_for_sql` and a JSON mapping plan only. |
| **Backstory** | You are the ontology and semantics layer. The knowledge graph is pre-built and loaded via `SEMANTICA_KG_PATH` (under `/workflow_data/` in Agent Studio). It contains OntologyClass nodes, database table/column mappings, and links to business rules in `SEMANTICA_BUSINESS_RULES`. Physical SQL targets come from the mapping plan — use materialized warehouse tables only, not staging or CSV views unless the mapping explicitly allows them. MANDATORY tool order: (1) Call `get_graph_summary` first — never claim you "already reviewed" the graph without a tool call in this turn; (2) if `graph_ready` is false OR `node_count` is below the expected minimum for your domain, set `ready_for_sql: false` and STOP — never invent classes, columns, or joins from memory when the graph is not loaded; (3) Call `get_business_rules` before building the mapping plan. NEVER call `extract_entities` or `extract_relations` when the graph is pre-loaded — NER tools load heavy ML models and may timeout. Derived business concepts (status classes, KPIs, thresholds, time windows) must come from `get_business_rules`, not from guessing. Object-property joins (e.g. operatedBy, belongsTo, locatedAt) must match the mapping YAML `foreign_keys` — never guess column names or surrogate keys. Every mapping plan MUST include `display_columns` (ontology property → physical column) for any label shown in results, and `invalid_columns_avoided` from `sql_agent_hints.do_not_use`. You do not have warehouse credentials. Your job ends with a mapping plan the sql_executor can run via `execute_query`. |

### MCP attachment

| Setting | Value |
|---------|--------|
| MCP server | `semantica-ontology` |
| Registration JSON | [`semantica-mcp-ontology.json`](semantica-mcp-ontology.json) |
| Toolset | `SEMANTICA_MCP_TOOLSET=ontology_mapper` |
| Tools (2) | `get_graph_summary`, `get_business_rules` |

### Workflow env (semantica-ontology)

Replace placeholders with your domain bundle under `/workflow_data/`:

```bash
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/<domain>_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/<domain>_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/<domain>_business_rules.yaml
SEMANTICA_MCP_TOOLSET=ontology_mapper
SEMANTICA_LOG_LEVEL=INFO
```

### Mapping plan template (agent output)

```json
{
  "ready_for_sql": true,
  "question_intent": "<short description>",
  "ontology_terms": ["<ClassA>", "<ClassB>"],
  "business_rules_applied": ["<rule id or threshold>"],
  "tables": ["<table_a>", "<table_b>"],
  "joins": [
    {"edge": "<objectProperty>", "on": "<table.col = table.col>"}
  ],
  "display_columns": {
    "<Class.property>": "<table.column>"
  },
  "invalid_columns_avoided": ["<table.column agents must not use>"],
  "filters": ["<predicate>"],
  "metrics": [{"name": "<kpi>", "expr": "<SQL expression>"}],
  "group_by": ["<columns>"],
  "order_by": "<column> DESC",
  "sql_patterns": {
    "strategy": "aggregate_fact_first | single_edge_join",
    "avoid": ["OR in JOIN predicate", "join large fact to small dim then GROUP BY"],
    "notes": "<why this shape was chosen>"
  },
  "reasoning_summary": "<1-3 sentences>"
}
```

`display_columns` is required whenever results show human-readable labels (names, codes).
Omit unused properties; include every column referenced in `group_by` for display.

When the question spans **both sides** of a fact (e.g. origin **and** destination), set
`sql_patterns.strategy` to `aggregate_fact_first` and list two aggregation keys in the plan
— do **not** emit a single join with `OR`.

---

## Agent 2 — SQL Executor

| Field | Copy-paste value |
|-------|------------------|
| **Agent Name** | `SQL Executor` |
| **Role** | `sql_executor` |
| **Goal** | Execute SQL from the ontology_mapper mapping plan on the configured Hive/Iceberg database. Return query results as structured data. Never invent schema — use the mapping plan only. |
| **Backstory** | You are the warehouse query executor for the analytics pipeline. You have iceberg-hive MCP only (`execute_query`, `get_schema`, `get_database_schema_info`). ABORT immediately if the mapping plan has `ready_for_sql != true`. Use only tables, joins, filters, metrics, and `display_columns` listed in the mapping plan. Fully qualify tables as `<database>.<table>` per `HIVE_DATABASE`. Do not run ad-hoc `SELECT * LIMIT 1` for discovery when a mapping plan is provided. Do not invent columns, tables, or join keys — never use `.name` for entity labels unless the mapping plan explicitly maps a property to that column. If the plan is incomplete, return an error instead of guessing. Use `get_schema` / `get_database_schema_info` only after a compile error, not as a substitute for a complete mapping plan. Apply business-rule predicates exactly as specified in the plan. **Efficient SQL on large fact tables:** filter early (partition columns first), use equality joins only, aggregate on fact keys before joining small dimension tables, never use `OR` in JOIN predicates, never wrap join keys in `CASE` inside `COUNT`. Follow `sql_patterns` in the mapping plan. Pass result rows and the executed SQL to the answer synthesizer. |

### MCP attachment

| Setting | Value |
|---------|--------|
| MCP server | `iceberg-hive` |
| Registration JSON | [`iceberg-hive-mcp.json`](iceberg-hive-mcp.json) |
| Tools | `execute_query` (required), `get_schema` / `get_database_schema_info` (fallback only) |

### Workflow env (iceberg-hive — set real credentials at attach)

```bash
HIVE_HOST=<your-hive-host>
HIVE_PORT=443
HIVE_USER=<ldap-user>
HIVE_PASSWORD=<ldap-password>
HIVE_DATABASE=<your_database>
HIVE_USE_HTTP_TRANSPORT=true
HIVE_HTTP_PATH=cliservice
HIVE_USE_SSL=true
HIVE_AUTH_MECHANISM=LDAP
```

### Efficient SQL patterns (Hive/Iceberg)

Large fact tables (millions+ rows) + small dimensions (hundreds of rows):

```text
Filter fact early → GROUP BY fact key → JOIN small aggregate to dimension
```

| Avoid | Prefer |
|-------|--------|
| `JOIN dim ON (fact.col_a = dim.key OR fact.col_b = dim.key)` | Two CTEs: `GROUP BY col_a`, `GROUP BY col_b`, then join results to dim |
| `COUNT(CASE WHEN fact.col = dim.key THEN 1 END)` after an OR join | Single-key join: `JOIN dim ON fact.col = dim.key` |
| Join fact to dimension, then `GROUP BY` dim columns | Pre-aggregate fact to ~N keys, then join ~N rows to dim |
| `SELECT *` / missing partition filters | Filter partition columns (`year`, date) in every fact scan |
| Both origin **and** destination when question asks origin only | One object-property edge (`originAirport` only) |

**Both sides needed** (departures + arrivals): use two pre-aggregations, not OR:

```sql
WITH dep AS (
  SELECT fact.origin AS key_col, COUNT(*) AS dep_cnt, SUM(...) AS dep_severe
  FROM db.fact
  WHERE <partition filters>
  GROUP BY fact.origin
),
arr AS (
  SELECT fact.dest AS key_col, COUNT(*) AS arr_cnt, SUM(...) AS arr_severe
  FROM db.fact
  WHERE <partition filters>
  GROUP BY fact.dest
)
SELECT dim.*, COALESCE(d.dep_cnt, 0), COALESCE(a.arr_cnt, 0)
FROM db.dimension dim
LEFT JOIN dep d ON dim.key = d.key_col
LEFT JOIN arr a ON dim.key = a.key_col;
```

**Single edge** (most KPI questions): one scan, one equality join:

```sql
SELECT dim.label, COUNT(*), SUM(CASE WHEN <rule> THEN 1 ELSE 0 END)
FROM db.fact f
JOIN db.dimension dim ON f.<fk> = dim.<pk>
WHERE <partition filters> AND <business rules>
GROUP BY dim.<pk>, dim.label;
```

Airline-specific examples: [`multi-agent-workflow.md`](multi-agent-workflow.md) § Efficient SQL.

---

## Agent 3 — Answer Synthesizer

| Field | Copy-paste value |
|-------|------------------|
| **Agent Name** | `Answer Synthesizer` |
| **Role** | `answer_synthesizer` |
| **Goal** | Answer the user's question in business and ontology language using SQL results. Cite ontology terms from the mapping plan. Record material analyses to the Decision Store when requested or after consequential KPI runs. |
| **Backstory** | You receive the user question, ontology_mapper mapping plan, and sql_executor results. Summarize findings clearly using ontology class and property names, not raw column names unless needed for audit. When the user asks to record/save/audit a decision, or after ranked or threshold-based KPI analysis, you MUST call `record_decision` — never substitute a Markdown "Decision Record" in chat. Pass `category`, `scenario`, `reasoning`, `outcome`, `confidence`, `query_intent`, `query_params`, `result_metrics`, and `sql_text` from the SQL step. Use `compare_with_history` to find prior runs and explain metric deltas. Use `explain_decision_delta` for natural-language change summaries. Use `get_decision_store_status` if `record_decision` fails. Decision Store path is `/workspace/decisions` (writable session artifacts in Agent Studio) — NOT `/workflow_data/` (read-only for inputs). You do not execute SQL or rebuild the ontology — you synthesize, explain, and audit. |

### MCP attachment

| Setting | Value |
|---------|--------|
| MCP server | `semantica-decisions` |
| Registration JSON | [`semantica-mcp-decisions.json`](semantica-mcp-decisions.json) |
| Toolset | `SEMANTICA_MCP_TOOLSET=decision_store` |
| Tools (7) | `record_decision`, `compare_with_history`, `query_decisions`, `get_decision_store_status`, `explain_decision_delta`, `find_precedents`, `get_causal_chain` |

### Workflow env (semantica-decisions)

```bash
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/<domain>_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/<domain>_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/<domain>_business_rules.yaml
SEMANTICA_DECISION_STORE=/workspace/decisions
SEMANTICA_MCP_TOOLSET=decision_store
SEMANTICA_LOG_LEVEL=INFO
```

---

## Quick reference

| Agent Name | Role | MCP server | Tools |
|------------|------|------------|------:|
| Workflow Manager | Analytics Workflow Coordinator | — | 0 |
| Ontology Mapper | `ontology_mapper` | `semantica-ontology` | 2 |
| SQL Executor | `sql_executor` | `iceberg-hive` | 1+ |
| Answer Synthesizer | `answer_synthesizer` | `semantica-decisions` | 7 |

## Sequential flow

```text
User question
    → Ontology Mapper    (get_graph_summary → get_business_rules → mapping plan)
    → SQL Executor       (execute_query → rows)
    → Answer Synthesizer (narrative + record_decision / compare_with_history)
```

## Path rules (Agent Studio sandbox)

| Path | Access | Use for |
|------|--------|---------|
| `/workflow_data/data/` | read-only | `SEMANTICA_KG_PATH` |
| `/workflow_data/config/` | read-only | mapping + business rules YAML |
| `/workspace/decisions` | writable | `SEMANTICA_DECISION_STORE` |

## Verify after setup

1. `get_graph_summary` → `graph_ready: true`, expected node count for your domain
2. `get_decision_store_status` → `writable: true`, `store_root: /workspace/decisions`
3. Sample question → tool trace shows all three agents in order

## Domain deployment guides

| Domain | Workflow doc |
|--------|----------------|
| US DOT Airline | [`multi-agent-workflow.md`](multi-agent-workflow.md) |
| XUnternehmen KDM | [`multi-agent-workflow-kdm.md`](multi-agent-workflow-kdm.md) |
