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

Ontology: `import_ontology`, `get_graph_summary`, `map_db_schema_to_ontology` (`export_graph` only if column mappings needed)  
Analytics: `run_reasoning`, `record_decision`, `query_decisions`, `find_precedents`  
Graph: `add_entity`, `add_relationship`, `extract_entities`, `extract_relations`, …

**No Hive/SQL on Semantica** — use `iceberg-hive` MCP for `execute_query` and schema introspection.

Set `SEMANTICA_KG_PATH` and `SEMANTICA_MAPPING_CONFIG` to **absolute** workbench paths
(see §5 below — not relative paths like `config/...`).
Do **not** set `HIVE_*` on the Semantica MCP server.

If ontology or mapping files fail to load, see
[MCP Server guide — Ontology and mapping files fail to load](../../docs/guides/mcp-server.md#ontology-and-mapping-files-fail-to-load).
Common causes: laptop paths in Agent Studio JSON, missing `airline_graph.json` build,
or `map_db_schema_to_ontology` returning `"used_mapping_config": false` (YAML path not found).

## 2. Register Iceberg Hive MCP (SQL execution)

Copy [`iceberg-hive-mcp.json`](iceberg-hive-mcp.json).

Set `--from` to your `iceberg-mcp-server-hive` clone. Entry point: `run-server`.

Key tools: `execute_query`, `get_schema`, `list_databases`, Iceberg branch tools.

## 3. Workflow setup (multi-agent)

See [`multi-agent-workflow.md`](multi-agent-workflow.md).

1. Create workflow → **Manager OFF**, **Sequential**, **Conversational ON**
2. Add agents: `ontology_mapper` (semantica only), `sql_executor` (iceberg only)
3. Enable tools per agent (do not attach both MCPs to one agent):
   - **ontology_mapper / semantica:** `get_graph_summary`, `run_reasoning` (avoid `export_graph` unless mappings required)
   - **sql_executor / iceberg-hive:** `execute_query`
4. Paste `HIVE_*` credentials only on **iceberg-hive** workflow attach step

## 4. Suggested agent architecture

```text
User question (natural language)
    │
    ├─► semantica          → ontology / graph / reasoning / decisions
    │
    └─► iceberg-hive       → SQL on airlinedata.flights (+ dimension tables)
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

## 6. Troubleshooting: graph file not found

`get_graph_summary` reports `kg_path_exists: false` when `SEMANTICA_KG_PATH` points to a missing file.
This is **not** a `uvx` sandbox issue — `uvx` runs `semantica-mcp` on the workbench with the same
filesystem access as your shell. The path in the env var is simply wrong or the file was never built.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ls` shows file but `kg_path_exists: false` | **Shell and MCP run on different CDSW workers** — file exists on workbench A, workflow session on workbench B | Compare `hostname` from `get_graph_summary` with your shell's `hostname`. Run `ls` on the workflow host, or copy graph into the CDSW **project** directory |
| `kg_path_exists: false` on workflow host | `SEMANTICA_KG_PATH` not passed to MCP subprocess at workflow attach | Re-attach semantica MCP with env block; restart workflow session |
| File missing entirely | `build_airline_graph.py` not run | `cd /home/cdsw/semantica && uv run python scripts/build_airline_graph.py` |
| `kg_path_exists: true` but `node_count: 0` | Corrupt JSON or load failed silently | Set `SEMANTICA_LOG_LEVEL=INFO`, check stderr for load warnings |
| `kg_path_exists: false` with correct path on host | bubblewrap sandbox cannot see the path | Set `ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true` in MCP env (see `semantica-mcp.json`), or copy graph under `agent-studio/studio-data/workflows/` |

`ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true` disables bubblewrap for MCP/tool runs so host paths like `/home/cdsw/semantica/data/` are visible. It is included in the semantica MCP registration JSON and workflow attach env. **Security trade-off:** MCP runs without filesystem sandbox isolation. If bubblewrap is still active after workflow attach, also set the variable at **Project Settings → Advanced → Environment Variables** and restart the Agent Studio application ([Cloudera known issues](https://docs.cloudera.com/machine-learning/cloud/ai-studios-release-notes/topics/ml-ai-studios-known-issues.html)).

**Verify on the workbench** (run on the **same** CDSW session that runs the workflow):

```bash
# Quick check
ls -la /home/cdsw/semantica/data/airline_graph.json
echo "SEMANTICA_KG_PATH=$SEMANTICA_KG_PATH"   # must NOT be /home/cdsw/data/...

# Full smoke test (uses uvx like Agent Studio)
bash /home/cdsw/semantica/deploy/cloudera-agent-studio/verify-kg-path.sh
```

**Do not** test with plain `uv run python -c "import semantica"` from `$HOME` — there is no
`semantica` package in that directory. Either `cd /home/cdsw/semantica` first, or use `uvx --from
git+https://github.com/frothkoetter/semantica.git@main` (see `verify-kg-path.sh`).

After fixing env vars, restart the workflow (or re-attach the semantica MCP server) so the new
`SEMANTICA_KG_PATH` is picked up. `get_graph_summary` should then show `kg_path_exists: true` and
`ontology_class_count > 0`.

## 7. Validate registration

After register, Agent Studio should discover tools. If discovery is incomplete, tools still work when selected manually in the workflow.

Smoke test prompt:

> Welche Airlines hatten 2008 die höchste durchschnittliche Ankunftsverzögerung?

Expected: agent resolves `Flight.arrDelay` + `operatedBy` → SQL on `flights` + `airlines`.

## 8. Generate config from local Cursor env (optional)

On your laptop (not on Agent Studio):

```bash
python scripts/generate-agent-studio-mcp-config.py \
  --semantica-git 'git+https://github.com/frothkoetter/semantica.git@main' \
  --semantica-root /home/cdsw/semantica \
  --iceberg-root /home/cdsw/iceberg-mcp-server-hive
```
