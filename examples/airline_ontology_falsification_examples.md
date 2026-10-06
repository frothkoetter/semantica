# Airline Ontology — Falsification Examples

Controlled **A/B demos** that **falsify** (disprove) the claim that an LLM can reliably
guess Hive column names and join keys. The **deterministic path** (graph + mapping YAML +
`get_business_rules`) produces SQL that **executes and returns rows**; the **guessing path**
produces SQL that **fails or returns empty/wrong results** — with the same natural-language
question.

Use these in Agent Studio or manual `execute_query` to prove ontology-first routing vs
hallucination.

---

## Experimental design

| Arm | Setup | Expected outcome |
|-----|--------|------------------|
| **A — Hallucination** | Manager ON, or single `sql_executor` **without** `ontology_mapper`; no `get_graph_summary` / mapping plan | Wrong columns (`carrier`, `iata`, `name`), wrong tables (`flights_csv`), invented FKs |
| **B — Deterministic ontology** | Sequential workflow: `ontology_mapper` → `sql_executor`; `SEMANTICA_KG_PATH` + mapping YAML loaded | Mapping plan cites `foreign_keys` / `invalid_columns`; SQL uses `uniquecarrier`, `code`, `description` |

**Pass criterion for B:** `execute_query` succeeds, row count > 0, joins match known DOT schema.

**Pass criterion for falsifying A:** Same question → Hive error **or** 0 rows **or** absurd counts (e.g. cartesian product) while B succeeds.

Evidence chain for B:

```text
get_graph_summary → graph_ready: true
get_business_rules → on_time_max_delay: 15
mapping plan JSON → joins from airline_r2rml_db_mapping.yaml foreign_keys
execute_query → rows returned
record_decision (optional) → query_fingerprint + sql_hash auditable
```

---

## Falsification 1 — `carrier` vs `uniquecarrier` (operatedBy)

**User question (same for A and B):**

```
Top 5 airlines by on-time performance in 2005. Join flights to airline names.
```

### Arm A — Hallucinated SQL (typical LLM guess)

```sql
SELECT a.name AS airline_name,
       ROUND(100.0 * SUM(CASE WHEN f.arrdelay <= 15 THEN 1 ELSE 0 END) / COUNT(*), 2) AS otp
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.carrier = a.iata
WHERE f.year = 2005 AND f.cancelled = 0
GROUP BY a.name
ORDER BY otp DESC
LIMIT 5;
```

| Check | Result |
|-------|--------|
| Column `f.carrier` | **Invalid** — not in `flights` (see `invalid_columns` in mapping YAML) |
| Column `a.iata` | **Invalid** on `airlines` — PK is `code` |
| Column `a.name` | **Invalid** — use `description` |
| Hive error | `Error while compiling statement: ... cannot resolve 'f.carrier'` **or** silent wrong join |

**Falsification:** If the agent claims OTP rankings without ontology tools, ask it to run
the SQL above — execution **refutes** the answer.

### Arm B — Ontology-resolved SQL

**Mapping plan excerpt:**

```json
{
  "ontology_terms": ["Flight", "Airline", "OnTimeFlight", "operatedBy"],
  "business_rules_applied": ["OnTimeFlight: cancelled=0, arrdelay<=15, depdelay<=15"],
  "joins": [{
    "edge": "operatedBy",
    "on": "flights.uniquecarrier = airlines.code"
  }],
  "invalid_columns_avoided": ["flights.carrier", "airlines.iata", "airlines.name"]
}
```

```sql
SELECT a.description AS airline_name,
       a.code AS airline_code,
       ROUND(100.0 * SUM(CASE
         WHEN f.cancelled = 0
          AND COALESCE(f.arrdelay,0) <= 15
          AND COALESCE(f.depdelay,0) <= 15
         THEN 1 ELSE 0 END)
       / NULLIF(SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END), 0), 2) AS otp_pct
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2005
GROUP BY a.code, a.description
HAVING SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END) > 0
ORDER BY otp_pct DESC
LIMIT 5;
```

| Check | Result |
|-------|--------|
| Join | Matches `OBJECT_PROPERTY_JOINS["operatedBy"]` in `examples/airline_ontology_resolver.py` |
| Execution | **5 rows** — e.g. HA ~95%, OO ~83%, … |
| Reproducible | Same SQL hash on re-run → same `query_fingerprint` in Decision Store |

---

## Falsification 2 — Airport name column (`name` vs `airport`)

**User question:**

```
Top 5 origin airports by departure count in 2005. Show airport name, not just IATA code.
```

### Arm A — Hallucinated SQL

```sql
SELECT ap.name AS airport_name, f.origin, COUNT(*) AS deps
FROM airlinedata.flights f
JOIN airlinedata.airports ap ON f.origin = ap.name
WHERE f.year = 2005
GROUP BY ap.name, f.origin
ORDER BY deps DESC
LIMIT 5;
```

| Check | Result |
|-------|--------|
| `airports.name` | **Does not exist** — column is `airport` (maps to ontology `airportName`) |
| Join `origin = name` | Wrong key — must be `origin = iata` |
| Outcome | Compile error **or** **0 rows** (join never matches) |

### Arm B — Ontology-resolved SQL

```json
{
  "joins": [{
    "edge": "originAirport",
    "on": "flights.origin = airports.iata"
  }],
  "columns": {"airportName": "airports.airport"}
}
```

```sql
SELECT ap.iata, ap.airport AS airport_name, COUNT(*) AS deps
FROM airlinedata.flights f
JOIN airlinedata.airports ap ON f.origin = ap.iata
WHERE f.year = 2005 AND f.cancelled = 0
GROUP BY ap.iata, ap.airport
ORDER BY deps DESC
LIMIT 5;
```

| Check | Result |
|-------|--------|
| Top origin 2005 | ATL, ORD, DFW, … with human-readable `airport` labels |
| Falsifies A | A returns error/empty; B returns known hub ranking |

---

## Falsification 3 — Wrong table (`flights_csv` vs `flights`)

**User question:**

```
Average arrival delay by airline in 2008.
```

### Arm A — Hallucinated SQL

```sql
SELECT a.description, AVG(f.arrdelay)
FROM airlinedata.flights_csv f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2008
GROUP BY a.description;
```

| Check | Result |
|-------|--------|
| Table | Agent picks `flights_csv` from schema listing — **not** the materialized analytics table |
| Outcome | Missing table, permission error, or stale/incomplete data vs `flights` |

### Arm B — Ontology-resolved SQL

```json
{
  "preferred_tables": {"Flight": "flights"},
  "tables": ["flights", "airlines"]
}
```

Uses `airlinedata.flights` only (see `preferred_tables` in `airline_r2rml_db_mapping.yaml`).

**Falsification:** Compare row counts — `SELECT COUNT(*) FROM flights WHERE year=2008` vs
any CSV-backed view; ontology path aligns with demo benchmark counts.

---

## Falsification 4 — Invented foreign key (`flight_id`)

**User question:**

```
List flights with their operating airline legal name for January 2005, limit 10.
```

### Arm A — Hallucinated SQL

```sql
SELECT f.flight_id, a.description
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.airline_id = a.id
WHERE f.year = 2005 AND f.month = 1
LIMIT 10;
```

| Check | Result |
|-------|--------|
| `flight_id`, `airline_id`, `a.id` | **None exist** in DOT schema |
| Outcome | Immediate compile failure |

### Arm B — Ontology-resolved SQL

Natural key is composite `(year, month, dayofmonth, uniquecarrier, flightnum, origin)` —
ontology plan states **no surrogate flight_id**; join only via `operatedBy`:

```sql
SELECT f.year, f.month, f.dayofmonth, f.uniquecarrier, f.flightnum,
       f.origin, f.dest, a.description AS airline_name
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2005 AND f.month = 1 AND f.cancelled = 0
LIMIT 10;
```

**Falsification:** A cannot run; B returns 10 rows with valid carrier names.

---

## Falsification 5 — OTP rule guessed vs business-rules deterministic

**User question:**

```
Which airline had the best OTP in 2005?
```

### Arm A — Hallucinated semantics

Agent assumes OTP = “any arrival delay ≤ 0” (on-time = early only) **without** reading rules:

```sql
-- Wrong rule: only arrdelay <= 0, ignores depdelay and 15-minute FAA threshold
SUM(CASE WHEN f.arrdelay <= 0 THEN 1 ELSE 0 END)
```

| Check | Result |
|-------|--------|
| OTP definition | **Wrong** — contradicts `on_time_max_delay: 15` in YAML |
| Rankings | Different top-5 order vs FAA-compliant SQL |
| Falsifiable | Run both SQL variants; compare results — rankings **diverge** |

### Arm B — Ontology + business rules

**Tool trace must include:** `get_business_rules` before SQL.

```yaml
# From airline_business_rules.yaml
flight_status_rules:
  - class: OnTimeFlight
    when: "cancelled = 0 AND COALESCE(arrdelay,0) <= 15 AND COALESCE(depdelay,0) <= 15"
```

SQL uses exactly that predicate. **Decision Store** records `business_rules_hash` so a
later rule change is detectable via `compare_with_history` → `rules_changed: true`.

| Arm A OTP (arrdelay≤0 only) | Arm B OTP (FAA 15 min) |
|-----------------------------|-------------------------|
| Different airline #1 | HA ~95% (typical 2005 top) |
| Not auditable | `business_rules_hash` in JSONL |

---

## Agent Studio demo script (live falsification)

Run **the same prompt twice** in two sessions:

### Session 1 — Falsification arm (expect failure)

1. Workflow: **Manager ON** or only `sql_executor` with iceberg-hive MCP.
2. Prompt: *“Top 5 airlines by OTP in 2005 with airline names.”*
3. Capture: SQL in chat trace.
4. Verify: contains `carrier`, `iata`, or `name` → **hallucination arm confirmed**.
5. Run SQL in Hive → error or 0 rows.

### Session 2 — Ontology arm (expect success)

1. Workflow: **Manager OFF**, Sequential: `ontology_mapper` → `sql_executor`.
2. Same prompt.
3. Capture: `get_graph_summary`, `get_business_rules`, mapping plan JSON.
4. Verify: join `uniquecarrier = code`, columns `description`, rules 15 min.
5. `execute_query` → 5 rows.
6. Optional: `record_decision` → download `/workspace/decisions/decisions.jsonl`.

### Side-by-side scorecard

| Metric | Arm A (guess) | Arm B (ontology) |
|--------|---------------|------------------|
| `get_graph_summary` called | No | Yes |
| Mapping plan JSON | No | Yes |
| SQL executes | No / wrong | Yes |
| Row count | 0 or error | > 0 |
| Join matches YAML `foreign_keys` | No | Yes |
| OTP rule matches YAML | No | Yes |
| Auditable decision hash | No | Yes |

---

## Ground truth references (deterministic sources)

| Artifact | Path | What it fixes |
|----------|------|----------------|
| R2RML mapping | `upload/airlinedata/config/airline_r2rml_db_mapping.yaml` | `invalid_columns`, `foreign_keys`, `preferred_tables` |
| Business rules | `upload/airlinedata/config/airline_business_rules.yaml` | OTP, peaks, delay severity |
| Graph | `upload/airlinedata/config/airline_graph.json` | OntologyClass → table/column nodes |
| Resolver | `examples/airline_ontology_resolver.py` | `OBJECT_PROPERTY_JOINS` canonical joins |

**Rule for demos:** Any SQL that contradicts these files is **falsified** by executing against
`airlinedata` — not by arguing with the model.

---

## Related examples

- [`airline_ontology_demo_chats.md`](airline_ontology_demo_chats.md) — correct analytics chats
- [`airline_logistics_outlier_demo_chats.md`](airline_logistics_outlier_demo_chats.md) — outlier KPIs with decision store
- [`deploy/cloudera-agent-studio/multi-agent-workflow.md`](../deploy/cloudera-agent-studio/multi-agent-workflow.md) — workflow setup
