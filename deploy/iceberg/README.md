# KDM on Cloudera Iceberg (Hive)

Iceberg tables for [XUnternehmen.Kerndatenmodell](https://w3id.org/kdm/) on CDW Hive, aligned with `config/kdm_db_mapping.yaml`.

## Database: `kdm`

| Table | KDM-Klasse |
|-------|------------|
| `natuerliche_person` | NatuerlichePerson |
| `juristische_person` | JuristischePerson |
| `anschrift` | Anschrift |
| `eintragung` | Eintragung |
| `betriebsstaette` | Betriebsstaette |
| `kommunikation` | Kommunikation |
| `gesellschafter` | Gesellschafter |
| `wirtschaftliche_taetigkeit` | WirtschaftlicheTaetigkeit |

## Provision (einmalig)

Uses credentials from `~/.cursor/mcp.json` → `iceberg-mcp-server-hive`:

```bash
cd /path/to/iceberg-mcp-server-hive
uv run python /path/to/semantica/deploy/iceberg/setup_kdm_hive.py --seed
```

DDL only (no demo data):

```bash
uv run python deploy/iceberg/setup_kdm_hive.py
```

## MCP (iceberg-mcp-server-hive)

After restart (with `execute_ddl` tool from latest server build):

```text
execute_ddl("CREATE DATABASE IF NOT EXISTS kdm")
get_schema(database="kdm")
execute_query("SELECT * FROM kdm.natuerliche_person LIMIT 5")
```

## Semantica MCP mapping

### One-shot (recommended)

Set the same `HIVE_*` env vars on `semantica-mcp` as on `iceberg-mcp-server-hive`, then:

```text
map_iceberg_schema_to_ontology({ "database": "kdm" })
```

This introspects Hive, imports KDM if needed, maps via `kdm_db_mapping.yaml`, and writes graph edges.

### Two-step (cross-MCP)

**iceberg-mcp-server-hive:**

```text
get_database_schema_info({ "database": "kdm" })
```

**semantica-mcp:**

```text
import_kdm_ontology()
map_db_schema_to_ontology({
  "schema_info": <from iceberg>,
  "use_kdm_defaults": true,
  "apply_mappings": true
})
```

### Semantica-only introspection

```text
get_hive_schema_info({ "database": "kdm" })
map_db_schema_to_ontology({ "schema_info": ..., "use_kdm_defaults": true })
```

Requires `pip install impyla` and `HIVE_*` environment variables.

## Airline domain (replace KDM)

KDM and Airline are **disjoint domains**. To switch from `kdm` to airline data, see **[AIRLINE_REPLACE_KDM.md](AIRLINE_REPLACE_KDM.md)**.

Quick start:

```bash
uv run python deploy/iceberg/setup_airline_hive.py --seed
```

```text
map_iceberg_schema_to_ontology({
  "database": "airline",
  "import_kdm_if_missing": false,
  "use_kdm_defaults": false,
  "ontology_file_path": "/path/to/semantica/data/airline_ontology.owl.xml",
  "mapping_config_path": "/path/to/semantica/config/airline_db_mapping.yaml"
})
```
