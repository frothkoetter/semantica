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

> **Registration vs workflow attach:** `semantica-mcp.json` uses workbench paths as registration
> placeholders. When attaching the MCP server to a **workflow**, override with `/workflow_data/...`
> paths (§5). Agent Studio does not persist secret env values from registration.

### Semantica tools exposed (15)

Ontology: `import_ontology`, `get_graph_summary`, `get_business_rules`, `map_db_schema_to_ontology` (`export_graph` only if column mappings needed)  
Analytics: `run_reasoning`, `record_decision`, `query_decisions`, `find_precedents`  
Graph: `add_entity`, `add_relationship`, `extract_entities`, `extract_relations`, …

**No Hive/SQL on Semantica** — use `iceberg-hive` MCP for `execute_query` and schema introspection.

Set `SEMANTICA_KG_PATH`, `SEMANTICA_MAPPING_CONFIG`, and `SEMANTICA_BUSINESS_RULES` to **absolute**
`/workflow_data/...` paths at workflow attach (see §5 — Agent Studio mounts `workflow_data` into the MCP
session). Do **not** use bare filenames or `/workspace/...` unless the file is in the session sandbox.
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
   - **ontology_mapper / semantica:** check `get_graph_summary`, `get_business_rules` only; **uncheck** `extract_entities`, `extract_relations` (ML NER hangs). Optional: `SEMANTICA_MCP_TOOLSET=preloaded_graph` in MCP env for server-side filtering.
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

Agent Studio runs MCP inside a **bubblewrap** sandbox. Only certain directories are visible to the MCP
process. For workflow runs, **`workflow_data` is bind-mounted at `/workflow_data/`** inside MCP
(`cwd` is typically `/workspace`). Use `/workflow_data/...` paths in workflow MCP env — not
`/home/cdsw/semantica/...` or `/home/cdsw/agent-studio/...` unless insecure mode exposes host paths.

### Workflow runtime (MCP env — use these at workflow attach)

| Item | MCP path (`SEMANTICA_*` env) |
|---|---|
| Airline graph | `/workflow_data/data/airline_graph.json` |
| Mapping YAML | `/workflow_data/config/airline_r2rml_db_mapping.yaml` |
| Business rules | `/workflow_data/config/airline_business_rules.yaml` |

Example workflow env block (see [`workflow-env.template`](workflow-env.template)):

```bash
ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true
SEMANTICA_KG_PATH=/workflow_data/data/airline_graph.json
SEMANTICA_MAPPING_CONFIG=/workflow_data/config/airline_r2rml_db_mapping.yaml
SEMANTICA_BUSINESS_RULES=/workflow_data/config/airline_business_rules.yaml
SEMANTICA_LOG_LEVEL=INFO
```

Success criteria from `get_graph_summary`:

```json
{
  "node_count": 262,
  "ontology_class_count": 29,
  "kg_path_exists": true,
  "graph_ready": true,
  "business_rules_path_exists": true
}
```

> **Note:** `business_rule_count` may be `0` in the graph even when `business_rules_path_exists` is
> `true` — rules are loaded from YAML at runtime via `get_business_rules`. Call that tool before
> building SQL plans.

### Host workbench (build + copy source)

| Item | Workbench path (default) |
|---|---|
| Semantica repo | `/home/cdsw/semantica` |
| Airline graph (build output) | `/home/cdsw/semantica/data/airline_graph.json` |
| Mapping YAML | `/home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml` |
| Business rules | `/home/cdsw/semantica/config/airline_business_rules.yaml` |
| Workflow data (host) | `/home/cdsw/agent-studio/studio-data/workflows/<workflow_dir>/workflow_data/` |
| Iceberg MCP repo | `/home/cdsw/iceberg-mcp-server-hive` |
| Hive database | `airlinedata` |

### Populate `workflow_data` (once per workflow)

Copy built artifacts from the semantica clone into the workflow's `workflow_data` tree on the
workbench (replace `<workflow_dir>` with your folder, e.g. `semanticus__eoNcbDVo`):

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

List workflow folders:

```bash
ls /home/cdsw/agent-studio/studio-data/workflows/
```

`workflow_data` persists at the **workflow** level (not per chat session under `session/<id>/`), so
you do not need to re-copy for every new conversation.

## 6. Troubleshooting: graph file not found

`get_graph_summary` reports `kg_path_exists: false` when the MCP process cannot see the file at
`SEMANTICA_KG_PATH`. In Agent Studio workflows this is almost always a **mount/path** issue, not a
missing build.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `kg_path_exists: false`, `cwd: /workspace` | Path points outside bubblewrap mount (`/home/cdsw/...`) | Use `/workflow_data/data/airline_graph.json` and copy files into `workflow_data/` (§5) |
| `kg_path: airline_graph.json` or `/workspace/...` | Relative path or session sandbox without the file | Use absolute `/workflow_data/...` paths; copy into `workflow_data/`, not only `session/<id>/` |
| `ls` on host OK but MCP `false` | Shell and MCP run on **different CDSW workers** | Compare `hostname` from `get_graph_summary` with your shell's `hostname`; copy files on the workflow worker |
| `business_rules_path: null` | `SEMANTICA_BUSINESS_RULES` not passed to MCP subprocess | Set all three `SEMANTICA_*` paths in **both** MCP registration JSON and workflow attach env; restart session |
| `kg_path_exists: false` after env change | Stale MCP subprocess | Re-attach semantica MCP; restart workflow session |
| File missing entirely | `build_airline_graph.py` not run | `cd /home/cdsw/semantica && uv run python scripts/build_airline_graph.py` |
| `kg_path_exists: true` but `node_count: 0` | Corrupt JSON or load failed silently | Set `SEMANTICA_LOG_LEVEL=INFO`, check stderr for load warnings |

`ALLOW_AGENT_STUDIO_INSECURE_TOOL_EXECUTION=true` can disable bubblewrap so host paths like
`/home/cdsw/semantica/data/` are visible. Prefer `/workflow_data/...` first — it works with the
default sandbox. If you rely on insecure mode, set the variable at **Project Settings → Advanced →
Environment Variables** as well as workflow attach, then restart the Agent Studio application
([Cloudera known issues](https://docs.cloudera.com/machine-learning/cloud/ai-studios-release-notes/topics/ml-ai-studios-known-issues.html)).

**Verify on the workbench** (shell smoke test — paths differ from workflow MCP):

```bash
# Confirm build artifacts exist
ls -la /home/cdsw/semantica/data/airline_graph.json

# Confirm workflow_data copy (host side)
ls -la /home/cdsw/agent-studio/studio-data/workflows/<workflow_dir>/workflow_data/data/airline_graph.json

# uvx smoke test (uses workbench paths, not /workflow_data)
bash /home/cdsw/semantica/deploy/cloudera-agent-studio/verify-kg-path.sh
```

**Verify in the workflow** (authoritative — same view as MCP):

Call `get_graph_summary` and confirm `kg_path_exists: true`, `graph_ready: true`, and
`ontology_class_count > 0`. The `kg_path` field should show `/workflow_data/data/airline_graph.json`.

**Do not** test with plain `uv run python -c "import semantica"` from `$HOME` — there is no
`semantica` package in that directory. Either `cd /home/cdsw/semantica` first, or use `uvx --from
git+https://github.com/frothkoetter/semantica.git@main` (see `verify-kg-path.sh`).

After fixing paths or copying files, restart the workflow (or re-attach the semantica MCP server) so
the MCP subprocess reloads `SEMANTICA_KG_PATH`.

## 7. Validate registration

After register, Agent Studio should discover tools. If discovery is incomplete, tools still work when selected manually in the workflow.

Smoke test prompt:

> Welche Airlines hatten 2008 die höchste durchschnittliche Ankunftsverzögerung?

Expected: agent resolves `Flight.arrDelay` + `operatedBy` → SQL on `flights` + `airlines`.

Advanced KPI prompts (OTP, delay attribution, hub routes, scorecards): see
[`multi-agent-workflow.md` — Demo prompt catalog](multi-agent-workflow.md#demo-prompt-catalog-advanced-kpis).

## 8. Generate config from local Cursor env (optional)

On your laptop (not on Agent Studio):

```bash
python scripts/generate-agent-studio-mcp-config.py \
  --semantica-git 'git+https://github.com/frothkoetter/semantica.git@main' \
  --semantica-root /home/cdsw/semantica \
  --iceberg-root /home/cdsw/iceberg-mcp-server-hive
```
