# Agent Studio — Multi-Agent Airline Workflow (Phase 2)

**Conversational:** ON · **Manager Agent:** OFF · **Process:** Sequential

One MCP server per agent. Semantica has **no** `HIVE_*` credentials.

## Agents

### 1. `ontology_mapper` — Semantica only

| Field | Value |
|---|---|
| Role | `ontology_mapper` |
| Goal | Resolve user questions into ontology terms and a SQL mapping plan. Never execute SQL. |
| MCP | `semantica` |
| Tools | `get_graph_summary`, `run_reasoning` (optional: `export_graph` with `subset: ontology`) |

**Env:** `SEMANTICA_KG_PATH`, `SEMANTICA_MAPPING_CONFIG` only.

**Task 1 — abort rules:**
- If `get_graph_summary.node_count < 50` → `ready_for_sql: false`, STOP
- If `ontology_class_count == 0` → STOP
- Never call `import_ontology` when graph is pre-loaded
- **Do not call `export_graph` unless column-level mappings are required** — use `get_graph_summary` first; if needed, `export_graph({format: "json", subset: "ontology"})` only
- Output JSON mapping plan; never write SQL

### 2. `sql_executor` — iceberg-hive only

| Field | Value |
|---|---|
| Role | `sql_executor` |
| Goal | Execute Hive SQL from the mapping plan on `airlinedata`. |
| MCP | `iceberg-hive` |
| Tools | `execute_query`, `get_schema` (fallback only) |

**Env:** all `HIVE_*` credentials.

**Task 2 — gate:**
- ABORT if Task 1 `ready_for_sql != true`
- Tables: `flights_orc`, `airlines`, `airports`, `planes` only
- No `SELECT * LIMIT 1` discovery — use Task 1 mappings

### 3. `answer_synthesizer` — Semantica (optional)

| Field | Value |
|---|---|
| Role | `answer_synthesizer` |
| MCP | `semantica` |
| Tools | `record_decision` (optional) |

**Task 3:** Answer in ontology language; cite `Flight`, `Airline`, etc.

## Tool split

| Capability | semantica | iceberg-hive |
|---|---|---|
| Ontology / graph | yes | — |
| SQL execution | — | yes |
| Schema introspection | — | `get_schema`, `get_database_schema_info` |
| Iceberg branches | — | yes |

## Build-time (not runtime)

```bash
cd /home/cdsw/semantica
export HIVE_DATABASE=airlinedata HIVE_HOST=... HIVE_USER=... HIVE_PASSWORD=...
uv run python scripts/build_airline_graph.py
```

Or chain MCP at build time:
1. `iceberg-hive.get_database_schema_info({database: "airlinedata"})`
2. `semantica.map_db_schema_to_ontology({schema_info, apply_mappings: true})`

## Smoke test

> Welche Airlines hatten 2008 die höchste durchschnittliche Ankunftsverzögerung?

Expected trace:
1. `get_graph_summary` → `node_count: 262`, `ontology_classes: [Flight, Airline, ...]`
2. `execute_query` → SQL on `flights_orc` JOIN `airlines` WHERE `year = 2008`
3. Business answer with ontology terms
