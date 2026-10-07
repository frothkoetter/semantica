# Airline KPI Demo Chats (10 examples)

Copy-paste prompts for **Agent Studio** sequential workflow:
`ontology_mapper` → `sql_executor` → `answer_synthesizer`.

Each demo resolves a **`kpi_catalog`** entry from `get_business_rules` (50 industry KPIs in
`config/airline_kpi_catalog.yaml`). Ontology classes live in `data/airline_kpi_ontology.ttl`.

**Prerequisites:** `airline_graph.json`, `airline_business_rules.yaml`, `airline_kpi_catalog.yaml`
under `/workflow_data/` · Hive `airlinedata` · Manager **OFF**

**Expected tool trace (every demo):**

| Step | Agent | Tool |
|------|--------|------|
| 1 | ontology_mapper | `get_graph_summary` |
| 2 | ontology_mapper | `get_business_rules` → `kpi_catalog.kpis.<Class>` |
| 3 | ontology_mapper | mapping plan JSON (`ontology_terms`, `metrics`, `sql_patterns`) |
| 4 | sql_executor | `execute_query` |
| 5 | answer_synthesizer | narrative (+ optional `record_decision`) |

---

## Demo 1 — OTP ranking by carrier

**User prompt:**

```
Which airlines had the best OTP in 2005? Minimum 1,000 completed flights.
Use the FAA 15-minute rule from business rules.
```

**KPI / ontology:** `OTP` · `OnTimeFlight` · `operatedBy` → `Airline`

**Mapping plan (excerpt):**

```json
{
  "ontology_terms": ["OTP", "OnTimeFlight", "Flight", "Airline", "operatedBy"],
  "business_rules_applied": ["otp.sql.expr", "on_time_max_delay: 15"],
  "metrics": [{"name": "otp_pct", "kpi_class": "OTP", "expr_from": "otp.sql.expr"}],
  "group_by": ["airlines.code", "airlines.description"],
  "having": "COUNT(*) >= 1000"
}
```

**SQL shape:**

```sql
SELECT a.code, a.description,
  ROUND(100.0 * SUM(CASE WHEN f.cancelled = 0 AND f.arrdelay <= 15 AND f.depdelay <= 15 THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END), 0), 2) AS otp_pct
FROM airlinedata.flights f
JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
WHERE f.year = 2005
GROUP BY a.code, a.description
HAVING SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END) >= 1000
ORDER BY otp_pct DESC LIMIT 10;
```

---

## Demo 2 — D0 vs A0 (departure vs arrival punctuality)

> **Troubleshooting:** If `get_graph_summary` shows `database_table_count: 0`, that is
> **not an error** when `graph_ready_for_sql: true` and `schema_mappings_ready: true`.
> The ontology_mapper must still call `get_business_rules` and emit `ready_for_sql: true`.
> Do **not** abort only because DatabaseTable nodes are missing (`--skip-hive` build).

**User prompt:**

```
For American and United in 2008: compare D0 departure OTP vs A0 arrival OTP.
Which metric is worse for each carrier?
```

**KPI / ontology:** `D0DepartureOTP` · `A0ArrivalOTP` · `PunctualityKPI`

**Mapping plan metrics:**

```json
"metrics": [
  {"name": "d0_pct", "kpi_class": "D0DepartureOTP", "expr_from": "kpi_catalog.kpis.D0DepartureOTP.sql.expr"},
  {"name": "a0_pct", "kpi_class": "A0ArrivalOTP", "expr_from": "kpi_catalog.kpis.A0ArrivalOTP.sql.expr"}
]
```

**Agent answer pattern:** Cite **D0** (depDelay ≤ 15) vs **A0** (arrDelay ≤ 15); do not mix into generic OTP unless both dimensions requested.

---

## Demo 3 — Cancellation rate scorecard

**User prompt:**

```
Build a 2008 cancellation rate scorecard for the top 10 carriers by volume.
Rank by CancellationRate KPI.
```

**KPI / ontology:** `CancellationRate` · `CancelledFlight` · `CompletionRate`

**SQL metric (from catalog):**

```sql
ROUND(100.0 * SUM(CASE WHEN cancelled = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS cancellation_pct
```

**Tip:** Denominator is **all scheduled** departures (`COUNT(*)`), not only completed.

---

## Demo 4 — Severe delay rate at hub airports (Midday)

**User prompt:**

```
Which origin airports had the highest SevereDelayRate during Midday (10:00–16:59) in 2008?
At least 10,000 departures. Use originAirport only.
```

**KPI / ontology:** `SevereDelayRate` · `SevereDelay` · `Midday` · `originAirport`

**Efficient SQL pattern:** single join `flights.origin = airports.iata` — no OR join.

```sql
SELECT ap.iata, ap.airport,
  ROUND(100.0 * SUM(CASE WHEN f.cancelled = 0
    AND GREATEST(COALESCE(f.arrdelay,0), COALESCE(f.depdelay,0)) > 60 THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END), 0), 2) AS severe_delay_pct
FROM airlinedata.flights f
JOIN airlinedata.airports ap ON f.origin = ap.iata
WHERE f.year = 2008 AND f.crsdeptime BETWEEN 1000 AND 1659
GROUP BY ap.iata, ap.airport
HAVING SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END) >= 10000
ORDER BY severe_delay_pct DESC LIMIT 10;
```

---

## Demo 5 — Delay attribution: carrier vs weather

**User prompt:**

```
For Southwest in 2008: what share of attributed delay minutes is CarrierDelayShare vs
WeatherDelayShare? Use DOT cause columns only.
```

**KPI / ontology:** `CarrierDelayShare` · `WeatherDelayShare` · `DelayAttributionKPI`

**Metrics from catalog:**

| KPI class | Alias |
|-----------|--------|
| `CarrierDelayShare` | `carrier_delay_share_pct` |
| `WeatherDelayShare` | `weather_delay_share_pct` |

**Filter:** `cancelled = 0` · `uniquecarrier = 'WN'` · `year = 2008`

---

## Demo 6 — Turnaround: average taxi-out at ORD

**User prompt:**

```
What was the AverageTaxiOut KPI at Chicago O'Hare (ORD) in 2007 compared to 2008?
Show year-over-year change in minutes.
```

**KPI / ontology:** `AverageTaxiOut` · `TurnaroundKPI` · `originAirport`

**SQL:**

```sql
SELECT f.year,
  ROUND(AVG(CASE WHEN f.cancelled = 0 THEN COALESCE(f.taxiout, 0) END), 2) AS avg_taxi_out
FROM airlinedata.flights f
WHERE f.origin = 'ORD' AND f.year IN (2007, 2008)
GROUP BY f.year ORDER BY f.year;
```

---

## Demo 7 — Network: ASM proxy and stage length by manufacturer

**User prompt:**

```
Between 2000 and 2008: which Plane.manufacturer had the highest AvailableSeatMiles (ASM proxy)
and what was their AverageStageLength? Min 100,000 completed segments.
```

**KPI / ontology:** `AvailableSeatMiles` · `AverageStageLength` · `NetworkCapacityKPI` · `assignedAircraft`

**Joins:** `flights` → `planes` ON `tailnum`

**Metrics:**

```sql
SUM(CASE WHEN f.cancelled = 0 THEN COALESCE(f.distance, 0) ELSE 0 END) AS asm_proxy,
ROUND(AVG(CASE WHEN f.cancelled = 0 THEN COALESCE(f.distance, 0) END), 1) AS avg_stage_length
```

---

## Demo 8 — Reliability composite score

**User prompt:**

```
Rank the top 5 airlines in 2008 by ReliabilityCompositeScore (min 50,000 flights).
Explain the three components from business rules.
```

**KPI / ontology:** `ReliabilityCompositeScore` · `OTP` · `SevereDelayRate` · `CancellationRate`

**Definition (from catalog):**

> 0.5 × OTP + 0.3 × (1 − severeDelayRate) + 0.2 × (1 − cancellationRate)

**Mapping plan must reference:** `kpi_catalog.kpis.ReliabilityCompositeScore.sql.expr`

**Optional:** `record_decision` with `result_metrics` keyed by airline code.

---

## Demo 9 — Long-haul share vs OTP trade-off

**User prompt:**

```
In 2008, do carriers with a higher LongHaulFlightShare (distance >= 1500 mi) have lower OTP?
Show top 10 carriers by long-haul share with both KPIs.
```

**KPI / ontology:** `LongHaulFlightShare` · `OTP` · `NetworkCapacityKPI` · `PunctualityKPI`

**Metrics (same query, two catalog entries):**

```json
"metrics": [
  {"kpi_class": "LongHaulFlightShare", "alias": "long_haul_pct"},
  {"kpi_class": "OTP", "alias": "otp_pct", "expr_from": "otp.sql.expr"}
]
```

**Group by:** `airlines.code`, `airlines.description` · **HAVING:** volume ≥ 5,000

---

## Demo 10 — German: controllable vs uncontrollable delays

**User prompt (Deutsch):**

```
Zeige für Delta und United 2008 den Anteil beeinflussbarer vs. unbeeinflussbarer
Verzögerungsminuten (ControllableDelayShare vs UncontrollableDelayShare).
Welcher Carrier ist stärker wetter-/NAS-getrieben?
```

**KPI / ontology:** `ControllableDelayShare` · `UncontrollableDelayShare` · `DelayAttributionKPI`

| KPI | Bedeutung |
|-----|-----------|
| `ControllableDelayShare` | carrier + late-aircraft Minuten |
| `UncontrollableDelayShare` | weather + NAS + security Minuten |

**Join:** `operatedBy` · **Filter:** `year = 2008` · `uniquecarrier IN ('DL','UA')`

**Agent answer:** Ontology-Begriffe verwenden, Prozentwerte aus SQL zitieren, kein erfundenes Schwellen-OTP.

---

## Quick reference — KPI class → user phrases

| User says | Resolve to |
|-----------|------------|
| OTP, on-time performance | `OTP` |
| D0, departure OTP | `D0DepartureOTP` |
| A0, arrival OTP | `A0ArrivalOTP` |
| cancellation rate | `CancellationRate` |
| severe delay rate | `SevereDelayRate` |
| carrier delay share | `CarrierDelayShare` |
| taxi-out, rollzeit abflug | `AverageTaxiOut` |
| ASM, seat miles | `AvailableSeatMiles` |
| reliability score / index | `ReliabilityCompositeScore` |
| long-haul share | `LongHaulFlightShare` |
| controllable / uncontrollable delay | `ControllableDelayShare` / `UncontrollableDelayShare` |

Full catalog: `get_business_rules` → `kpi_catalog.kpis` (50 entries).

## Related docs

- KPI ontology: `data/airline_kpi_ontology.ttl`
- SQL definitions: `config/airline_kpi_catalog.yaml`
- Agent workflow: `deploy/cloudera-agent-studio/multi-agent-workflow.md`
- General ontology demos: `examples/airline_ontology_demo_chats.md`
