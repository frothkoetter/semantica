# Cloudera AI Agent Studio — MCP Configuration (Airline Demo)

Register MCP servers in **Agent Studio → Tools Catalog → MCP Servers → Register**.

Agent Studio supports **stdio** MCP only, launched via **`uvx`** (Python) or **`npx`** (Node).  
Use the same JSON shape as Claude Desktop ([Cloudera MCP guide](https://docs.cloudera.com/machine-learning/cloud/use-ai-studios/topics/ml-mcp-integration-guide.html)).

> **Security:** Placeholder credentials in registration JSON are expected. Agent Studio does not store secret env values — provide real `HIVE_USER` / `HIVE_PASSWORD` when attaching MCP servers to a **workflow**.

## Prerequisites (Workbench)

Clone repos into the CDSW project (adjust paths if your mount differs):

```bash
cd /home/cdsw
git clone https://github.com/frothkoetter/semantica.git semantica
git clone <iceberg-mcp-server-hive-repo-url> iceberg-mcp-server-hive

cd semantica
uv run python scripts/build_airline_graph.py    # builds data/airline_graph.json (needs Hive)
```

Ensure `uv` is available on the workbench (`uvx` command).

> **MCP server** is installed via `uvx` from GitHub (`frothkoetter/semantica@main`).  
> **Graph data** (`airline_graph.json`) still lives in the cloned repo — set `SEMANTICA_KG_PATH` accordingly.

## 1. Register Semantica (ontology + graph)

**Recommended — GitHub `main`** (no local package install):

Copy [`semantica-mcp.json`](semantica-mcp.json):

```json
"args": [
  "--from",
  "git+https://github.com/frothkoetter/semantica.git@main",
  "semantica-mcp"
]
```

**Option B — Local clone path** (offline / fork testing):

Copy [`semantica-mcp-local.json`](semantica-mcp-local.json) and set `--from` to your clone path.

### Semantica tools exposed (14)

Ontology: `import_ontology`, `get_graph_summary`, `export_graph`, `map_db_schema_to_ontology`  
Analytics: `run_reasoning`, `record_decision`, `query_decisions`, `find_precedents`  
Graph: `add_entity`, `add_relationship`, `extract_entities`, `extract_relations`, …

**No Hive/SQL on Semantica** — use `iceberg-hive` MCP for `execute_query` and schema introspection.

Set `SEMANTICA_KG_PATH` to the pre-built `airline_graph.json` and
`SEMANTICA_MAPPING_CONFIG` to `config/airline_r2rml_db_mapping.yaml`.
Do **not** set `HIVE_*` on the Semantica MCP server.

## 2. Register Iceberg Hive MCP (SQL execution)

Copy [`iceberg-hive-mcp.json`](iceberg-hive-mcp.json).

Set `--from` to your `iceberg-mcp-server-hive` clone. Entry point: `run-server`.

Key tools: `execute_query`, `get_schema`, `list_databases`, Iceberg branch tools.

## 3. Workflow setup (multi-agent)

See [`multi-agent-workflow.md`](multi-agent-workflow.md).

1. Create workflow → **Manager OFF**, **Sequential**, **Conversational ON**
2. Add agents: `ontology_mapper` (semantica only), `sql_executor` (iceberg only)
3. Enable tools per agent (do not attach both MCPs to one agent):
   - **ontology_mapper / semantica:** `get_graph_summary`, `export_graph`, `run_reasoning`
   - **sql_executor / iceberg-hive:** `execute_query`
4. Paste `HIVE_*` credentials only on **iceberg-hive** workflow attach step

## 4. Suggested agent architecture

```text
User question (natural language)
    │
    ├─► semantica          → ontology / graph / reasoning / decisions
    │
    └─► iceberg-hive       → SQL on airlinedata.flights_orc (+ dimension tables)
```

## 5. Path cheat sheet

| Item | Workbench path (default) |
|---|---|
| Semantica repo | `/home/cdsw/semantica` |
| Airline graph | `/home/cdsw/semantica/data/airline_graph.json` |
| Mapping YAML | `/home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml` |
| Business rules | `/home/cdsw/semantica/config/airline_business_rules.yaml` |
| Iceberg MCP repo | `/home/cdsw/iceberg-mcp-server-hive` |
| Hive database | `airlinedata` |

## 6. Validate registration

After register, Agent Studio should discover tools. If discovery is incomplete, tools still work when selected manually in the workflow.

Smoke test prompt:

> Welche Airlines hatten 2008 die höchste durchschnittliche Ankunftsverzögerung?

Expected: agent resolves `Flight.arrDelay` + `operatedBy` → SQL on `flights_orc` + `airlines`.

## 7. Generate config from local Cursor env (optional)

On your laptop (not on Agent Studio):

```bash
python scripts/generate-agent-studio-mcp-config.py \
  --semantica-git 'git+https://github.com/frothkoetter/semantica.git@main' \
  --semantica-root /home/cdsw/semantica \
  --iceberg-root /home/cdsw/iceberg-mcp-server-hive
```
