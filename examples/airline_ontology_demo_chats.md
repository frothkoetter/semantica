# Airline Ontology Demo Chats

These demos show **ontology-first** analytics: the user speaks in domain terms (`Flight`, `arrDelay`, `operatedBy`), the agent resolves physical tables via `data/airline_graph.json`, and runs SQL only against **materialized** Hive tables (`flights`, `airlines`, `airports`, `planes` — never `*_csv`).

## Prerequisites

| MCP / env | Value |
|---|---|
| Semantica graph | `data/airline_graph.json` |
| Hive database | `airlinedata` |
| Iceberg MCP | `execute_query` |
| Semantica MCP | `get_graph_summary` (optional) |

**Ontology → physical layer (preferred tables):**

| Ontology class | Physical table |
|---|---|
| `Flight` (raw) | `airlinedata.flights` |
| `Flight` (+ business logic) | **runtime subquery** on `flights` (no Hive view) |
| `Airline` | `airlinedata.airlines` |
| `Airport` | `airlinedata.airports` |
| `Plane` | `airlinedata.planes` |

Runnable script (same logic as below): `python examples/airline_ontology_analytics_demo.py`

Agent Studio workflow: 31 advanced KPI prompts in
[`deploy/cloudera-agent-studio/multi-agent-workflow.md`](../deploy/cloudera-agent-studio/multi-agent-workflow.md#demo-prompt-catalog-advanced-kpis).

---

## Demo Chat 1 — Carrier delay ranking

**User:** Which airlines had the worst average arrival delays in 2008? Only carriers with at least 5,000 flights.

**Agent (reasoning, not shown to user):**

1. Load Semantica graph → class `Flight` maps to `flights`, property `arrDelay` → column `arrdelay`.
2. Relationship `Flight.operatedBy` → join `Flight.uniqueCarrier` to `Airline.airlineCode` (`uniquecarrier` = `code`).
3. Filter non-cancelled flights, partition year 2008.

**Agent (to user):** I'll analyze **Flight** records from 2008, using **arrDelay** grouped by the **operatedBy** airline.

**SQL generated (via ontology resolver):**

```sql
SELECT
  a.description AS airline_name,
  a.code AS airline_code,
  ROUND(AVG(f.arrdelay), 1) AS avg_arr_delay_min,
  COUNT(*) AS flight_count
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2008
  AND f.arrdelay IS NOT NULL
  AND f.cancelled = 0
GROUP BY a.code, a.description
HAVING COUNT(*) >= 5000
ORDER BY avg_arr_delay_min DESC
LIMIT 5;
```

**Result:**

| airline_name | airline_code | avg_arr_delay_min | flight_count |
|---|---|---:|---:|
| American Airlines Inc. | AA | 12.6 | 585,485 |
| Comair Inc. | OH | 11.8 | 190,695 |
| Mesa Airlines Inc. | YV | 11.8 | 245,131 |
| United Air Lines Inc. | UA | 11.3 | 437,979 |
| JetBlue Airways | B6 | 11.1 | 192,114 |

**Agent:** American Airlines had the highest average arrival delay (~12.6 min) among major carriers in 2008, with nearly 586k completed flights.

---

## Demo Chat 2 — Route volume from an airport

**User:** What were the top 5 destinations from Los Angeles (LAX) in 2007 by number of flights?

**Agent (reasoning):**

1. `Flight.originAirport` → column `origin` on `flights`.
2. `Flight.destinationAirport` → column `dest`.
3. Filter `origin = 'LAX'`, year 2007.

**Agent (to user):** I'll count **Flight** segments where the **originAirport** is LAX and rank **destinationAirport** by volume.

**SQL:**

```sql
SELECT f.origin AS origin_iata, f.dest AS dest_iata, COUNT(*) AS flight_count
FROM airlinedata.flights f
WHERE f.year = 2007 AND f.origin = 'LAX'
GROUP BY f.origin, f.dest
ORDER BY flight_count DESC
LIMIT 5;
```

**Result:**

| origin_iata | dest_iata | flight_count |
|---|---|---:|
| LAX | LAS | 14,385 |
| LAX | SAN | 12,767 |
| LAX | SFO | 11,792 |
| LAX | PHX | 11,194 |
| LAX | SJC | 10,878 |

**Agent:** Las Vegas (LAS) was the busiest destination from LAX in 2007, followed by San Diego and San Francisco.

---

## Demo Chat 3 — Aircraft manufacturer mix

**User:** Which plane manufacturers operated the most flight segments in 2008?

**Agent (reasoning):**

1. `Flight.assignedAircraft` → join `Flight.tailNum` to `Plane.tailNum`.
2. Aggregate by `Plane.manufacturer`.

**Agent (to user):** I'll link each **Flight** to its **assignedAircraft** (**Plane**) and rank **manufacturer** by segment count.

**SQL:**

```sql
SELECT p.manufacturer, COUNT(*) AS flight_segments
FROM airlinedata.flights f
JOIN airlinedata.planes p ON f.tailnum = p.tailnum
WHERE f.year = 2008
  AND p.manufacturer IS NOT NULL AND p.manufacturer <> ''
GROUP BY p.manufacturer
ORDER BY flight_segments DESC
LIMIT 5;
```

**Result:**

| manufacturer | flight_segments |
|---|---:|
| BOEING | 2,661,577 |
| BOMBARDIER INC | 974,690 |
| EMBRAER | 887,408 |
| AIRBUS INDUSTRIE | 537,734 |
| MCDONNELL DOUGLAS | 329,353 |

**Agent:** Boeing aircraft dominated US segment volume in 2008, with ~2.7M flights — roughly 2.7× the next manufacturer (Bombardier).

---

## Demo Chat 4 — Delay cause comparison

**User:** For Southwest, American, Delta, United, and US Airways in 2008: compare total carrier-caused delay vs weather delay.

**Agent (reasoning):**

1. Properties `Flight.carrierDelay` → `carrierdelay`, `Flight.weatherDelay` → `weatherdelay`.
2. Filter majors via `Flight.operatedBy` / `uniqueCarrier`.
3. Sum delay minutes (ontology datatype properties on **Flight**).

**Agent (to user):** I'll sum **carrierDelay** and **weatherDelay** on **Flight** records **operatedBy** each major **Airline**.

**SQL:**

```sql
SELECT
  a.description AS airline_name,
  SUM(COALESCE(f.carrierdelay, 0)) AS total_carrier_delay_min,
  SUM(COALESCE(f.weatherdelay, 0)) AS total_weather_delay_min
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2008
  AND f.carrierdelay IS NOT NULL AND f.weatherdelay IS NOT NULL
  AND f.uniquecarrier IN ('WN', 'AA', 'DL', 'UA', 'US')
GROUP BY a.code, a.description
ORDER BY total_carrier_delay_min DESC;
```

**Result:**

| airline_name | total_carrier_delay_min | total_weather_delay_min |
|---|---:|---:|
| American Airlines Inc. | 2,821,907 | 418,677 |
| Southwest Airlines Co. | 2,261,002 | 510,665 |
| United Air Lines Inc. | 1,720,150 | 214,132 |
| Delta Air Lines Inc. | 1,411,220 | 167,124 |
| US Airways Inc. | 1,109,335 | 101,863 |

**Agent:** All five majors accumulated more **carrierDelay** than **weatherDelay** in 2008. Southwest had the highest weather-delay total (~511k min) despite ranking second on carrier delay.

---

## Agent playbook (ontology-first)

```text
1. User question → identify ontology classes & properties (Flight, arrDelay, operatedBy, …)
2. Semantica graph (airline_graph.json):
   - DatabaseTable --mapsToClass--> OntologyClass
   - DatabaseColumn --mapsToProperty--> DatatypeProperty / ObjectProperty
3. Prefer materialized tables: flights, airlines, airports, planes
4. Object properties → join hints (operatedBy, assignedAircraft, originAirport, destinationAirport)
5. iceberg-mcp execute_query with resolved SQL
6. Answer in domain language; cite ontology terms, not raw column names
```

**Do not** query `flights_csv`, `airlines_csv`, etc. in these demos — they are staging copies; the ontology mapping targets the curated Iceberg/ORC layer.

### Runtime compilation (wichtig)

Business-Felder existieren **nicht** als Hive-Spalten. Der Agent baut sie pro Query:

```text
ontology: EveningPeak, OnTimeFlight
    → airline_business_rules.yaml
    → sql_runtime_flight_subquery(flights)
    → SELECT … FROM (SELECT *, CASE … END AS flight_status, … FROM flights) f
```

`--print-sql-only` zeigt das generierte SQL ohne Hive-Ausführung.

---

## Demo Chat 5 — OTP by business hour band

**User:** What was on-time performance by peak business hour in 2008?

**Agent:** Compiles `TimeWindow` + `OnTimePerformance` at runtime on `flights`.

---

## Demo Chat 6 — Primary delay reason

**User:** For delayed flights in 2008, which DOT delay cause dominates?

**Agent:** Runtime `primaryDelayReason` CASE + filter `flight_status = 'DelayedFlight'`.

---

## Demo Chat 7 — Hub route logistics

**User:** Which routes from the busiest hub airports had the worst OTP in 2008?

**Agent:** Runtime hub CTE + `route_id` + JOIN + OTP aggregation.

```bash
python examples/airline_ontology_analytics_demo.py --demo 5 --print-sql-only
```
