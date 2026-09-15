# Airline data on Cloudera Iceberg (Hive)

US DOT airline analytics on CDW Hive (`airlinedata`), aligned with `config/airline_r2rml_db_mapping.yaml`.

## Database: `airlinedata`

| Table | Ontology class |
|-------|----------------|
| `flights` | Flight |
| `airlines` | Airline |
| `airports` | Airport |
| `planes` | Plane |

## Provision (one-time)

Uses credentials from `~/.cursor/mcp.json` → `iceberg-mcp-server-hive`:

```bash
cd /path/to/semantica
uv run python deploy/iceberg/setup_airline_hive.py --seed
```

DDL only (no demo data):

```bash
uv run python deploy/iceberg/setup_airline_hive.py
```

## Build knowledge graph

```bash
export HIVE_DATABASE=airlinedata HIVE_HOST=... HIVE_USER=... HIVE_PASSWORD=...
uv run python scripts/build_airline_graph.py
```

Writes `data/airline_graph.json` — set as `SEMANTICA_KG_PATH` for the Semantica MCP.

## MCP workflow (Agent Studio)

**semantica** (ontology): `get_graph_summary`, `run_reasoning`  
**iceberg-hive** (SQL): `execute_query`

See `deploy/cloudera-agent-studio/multi-agent-workflow.md`.

### Cross-MCP mapping (build-time)

**iceberg-hive:**

```text
get_database_schema_info({ "database": "airlinedata" })
```

**semantica:**

```text
map_db_schema_to_ontology({
  "schema_info": <from iceberg>,
  "mapping_config_path": "/path/to/semantica/config/airline_r2rml_db_mapping.yaml",
  "apply_mappings": true
})
```
