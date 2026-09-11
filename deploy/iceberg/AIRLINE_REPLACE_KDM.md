# KDM durch Airline-Domäne ersetzen

KDM (XUnternehmen) und Airline sind **disjunkte Domänen**. Ein Wechsel bedeutet: neue Hive-DB, neue Ontologie, neues Mapping, neuer Graph — nicht „KDM erweitern“.

## Übersicht

| Schicht | KDM (alt) | Airline (neu) |
|---|---|---|
| Ontologie | `https://w3id.org/kdm/` | `https://w3id.org/airline/ontology#` |
| Ontologie-Datei | `data/kdm_ontology.ttl` | `data/airline_ontology.owl.xml` |
| Hive-Datenbank | `kdm` | `airline` |
| Mapping | `config/kdm_db_mapping.yaml` | `config/airline_db_mapping.yaml` |
| R2RML (CSV) | — | `data/airline_mapping.ttl` → `config/airline_r2rml_db_mapping.yaml` |
| Graph-Datei | `data/kdm_graph.json` | `data/airline_graph.json` |
| Tabellen | 8 (Personen, Firmen, …) | 5 (Flight, Aircraft, …) |

## Schritt 1 — Hive: Airline-DB anlegen

```bash
cd /path/to/iceberg-mcp-server-hive
uv run python /path/to/semantica/deploy/iceberg/setup_airline_hive.py --seed
```

Tabellen: `airline`, `airport`, `aircraft`, `flight`, `delay_breakdown`

## Schritt 2 — MCP: Umgebung auf `airline` umstellen

In `.cursor/mcp.json` für **beide** Server (`iceberg-mcp-server-hive` und `semantica`):

```json
"HIVE_DATABASE": "airline"
```

Semantica-Graph-Pfad:

```json
"SEMANTICA_KG_PATH": "/Users/<you>/semantica/data/airline_graph.json"
```

MCP-Server neu starten.

## Business logic (runtime SQL)

- Ontology extension: `data/airline_business_ontology.ttl`
- Rules: `config/airline_business_rules.yaml`
- Runtime compiler: `examples/airline_business_sql.py`
- Resolver: `examples/airline_ontology_resolver.py` → `flight_runtime_from()`
- Guide: `docs/guides/airline-business-logic.md`
- Rebuild graph: `python scripts/build_airline_graph.py`

## R2RML-Datei (`airline_mapping.ttl`)

Die Datei `data/airline_mapping.ttl` ist **R2RML** (Tabellen → RDF), **keine OWL-Ontologie**.
`import_ontology()` findet **0 Klassen** — das ist erwartet.

Für Semantica wurde daraus `config/airline_r2rml_db_mapping.yaml` abgeleitet (CSV-Tabellen `flights_csv`, `planes_csv`, …).

```text
map_iceberg_schema_to_ontology({
  "database": "airline",
  "import_kdm_if_missing": false,
  "use_kdm_defaults": false,
  "mapping_config_path": "/path/to/semantica/config/airline_r2rml_db_mapping.yaml"
})
```

Zusätzlich eine **OWL-Ontologie** laden (z. B. `data/airline_ontology.owl.xml`) oder Klassen aus R2RML manuell materialisieren.

## Schritt 3 — Ontologie importieren (nicht KDM!)

```text
import_ontology({
  "file_path": "/Users/<you>/semantica/data/airline_ontology.owl.xml"
})
```

**Nicht** `import_kdm_ontology()` verwenden.

## Schritt 4 — Schema → Ontologie mappen

```text
map_iceberg_schema_to_ontology({
  "database": "airline",
  "import_kdm_if_missing": false,
  "use_kdm_defaults": false,
  "mapping_config_path": "/Users/<you>/semantica/config/airline_db_mapping.yaml",
  "apply_mappings": true
})
```

Erwartung: **5/5 Tabellen** gemappt auf `Flight`, `Aircraft`, `Airport`, `Airline`, `DelayBreakdown`.

## Schritt 5 — Graph speichern

Nach Mapping den Graph exportieren oder `save_to_file` — MCP speichert **nicht automatisch**.

Pfad = `SEMANTICA_KG_PATH` (`airline_graph.json`).

## Schritt 6 — KDM-Daten (optional)

Die bestehende `kdm`-Datenbank bleibt in Hive, wird aber nicht mehr angesprochen, wenn `HIVE_DATABASE=airline`.

Zum vollständigen Entfernen (nur wenn gewünscht):

```sql
DROP TABLE airline.flight;  -- Beispiel — KDM-Tabellen separat
-- DROP DATABASE kdm;      -- Vorsicht: irreversibel
```

## Beispiel-Analyse (Airline)

```text
Finde alle verspäteten Flüge (status=delayed) mit Verspätungsursache.
Nutze airline.* über Iceberg MCP.
Erkläre anhand der Ontologie-Klassen Flight und DelayBreakdown.
```

SQL:

```sql
SELECT f.id, f.flight_number, d.cause_code, d.delay_minutes
FROM airline.flight f
JOIN airline.delay_breakdown d ON d.flight_id = f.id
WHERE f.status = 'delayed';
```

## Domänen-Disjunktion

```mermaid
flowchart LR
  KDM["kdm.*<br/>NatuerlichePerson …"]
  AIR["airline.*<br/>Flight …"]
  KDM -.->|kein Mapping| AIR
```

Beide Ontologien können **parallel** im selben Semantica-Graph koexistieren, aber für klare Analysen **eine Domäne pro Graph-Datei** empfohlen (`kdm_graph.json` vs. `airline_graph.json`).
