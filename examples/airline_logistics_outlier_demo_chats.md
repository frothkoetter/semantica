# Airline Logistics — Outlier Analysis Demo Chats

Two end-to-end Agent Studio examples for **logistics outlier detection**: routes and hubs
that deviate sharply from network baselines. Each chat uses **business rules + SQL +
reasoning + `record_decision` + `compare_with_history`**.

## Prerequisites

| Setting | Value |
|---|---|
| Workflow | Sequential, Manager **OFF** — `ontology_mapper` → `sql_executor` → `answer_synthesizer` |
| Semantica MCP | `get_graph_summary`, `get_business_rules`, `record_decision`, `compare_with_history` |
| Hive MCP | `execute_query` |
| Env | `SEMANTICA_DECISION_STORE=/workspace/decisions` (writable; **not** `/workflow_data`) |
| Database | `airlinedata` — tables `flights`, `airlines`, `airports` |
| Joins | `flights.uniquecarrier = airlines.code`, `flights.origin = airports.iata` |

Ontology terms: `Route`, `HubAirport`, `OnTimeFlight`, `DelayedFlight`, `SevereDelay`,
`MorningPeak`, `routeDistanceMiles`. Rules: `config/airline_business_rules.yaml`.

---

## Demo Chat 1 — Route OTP outliers from hub airports

**User:** Which **routes from hub airports** are **outliers** for on-time performance in
**MorningPeak** during **2005**? A route is an outlier if its OTP is more than **2 standard
deviations below** the network average for the same peak window. Show top 5 worst outliers.
Record the decision.

### Expected tool trace

| Step | Agent | Tool |
|------|--------|------|
| 1 | ontology_mapper | `get_graph_summary` |
| 2 | ontology_mapper | `get_business_rules` → `OnTimeFlight`, `MorningPeak` (600–959), `hub_airport` |
| 3 | ontology_mapper | Mapping plan: `Route` = `origin-dest`, hub = top 20 origins by departures |
| 4 | sql_executor | `execute_query` |
| 5 | answer_synthesizer | `record_decision` |

### Agent reasoning (ontology_mapper)

1. **HubAirport** — top 20 origins by departure count in 2005 (`hub_airport.default_top_n`).
2. **Route** — `CONCAT(origin, '-', dest)` on flights departing hubs in **MorningPeak**.
3. **OnTimeFlight** — `cancelled=0 AND arrdelay≤15 AND depdelay≤15`.
4. **Outlier rule** — per-route OTP vs global MorningPeak OTP on hub routes;
   flag routes where `otp_pct < avg - 2*stddev` (network baseline on same filter set).
5. Minimum volume: ≥ 500 flights on route (avoid sparse false outliers).

### SQL (sql_executor)

```sql
WITH hub AS (
  SELECT f.origin AS iata
  FROM airlinedata.flights f
  WHERE f.year = 2005 AND f.cancelled = 0
  GROUP BY f.origin
  ORDER BY COUNT(*) DESC
  LIMIT 20
),
route_peak AS (
  SELECT
    f.origin,
    f.dest,
    CONCAT(f.origin, '-', f.dest) AS route_id,
    COUNT(*) AS flight_count,
    ROUND(100.0 * SUM(CASE
      WHEN f.cancelled = 0
       AND COALESCE(f.arrdelay, 0) <= 15
       AND COALESCE(f.depdelay, 0) <= 15
      THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN f.cancelled = 0 THEN 1 ELSE 0 END), 0), 2) AS otp_pct
  FROM airlinedata.flights f
  JOIN hub h ON f.origin = h.iata
  WHERE f.year = 2005
    AND f.cancelled = 0
    AND f.crsdeptime BETWEEN 600 AND 959
  GROUP BY f.origin, f.dest
  HAVING COUNT(*) >= 500
),
baseline AS (
  SELECT
    AVG(otp_pct) AS avg_otp,
    STDDEV(otp_pct) AS std_otp
  FROM route_peak
)
SELECT
  rp.route_id,
  rp.origin,
  rp.dest,
  rp.flight_count,
  rp.otp_pct,
  b.avg_otp AS network_avg_otp,
  ROUND(b.avg_otp - 2 * b.std_otp, 2) AS outlier_threshold,
  ROUND(rp.otp_pct - b.avg_otp, 2) AS otp_delta_vs_avg
FROM route_peak rp
CROSS JOIN baseline b
WHERE rp.otp_pct < b.avg_otp - 2 * b.std_otp
ORDER BY rp.otp_pct ASC
LIMIT 5;
```

### Illustrative result

| route_id | flight_count | otp_pct | network_avg_otp | outlier_threshold | otp_delta_vs_avg |
|---|---:|---:|---:|---:|---:|
| ORD-LGA | 2,841 | 58.2 | 79.4 | 65.1 | -21.2 |
| ATL-EWR | 3,102 | 61.5 | 79.4 | 65.1 | -17.9 |
| DFW-ORD | 4,556 | 63.8 | 79.4 | 65.1 | -15.6 |
| LAX-ORD | 2,990 | 64.1 | 79.4 | 65.1 | -15.3 |
| ATL-ORD | 5,210 | 64.9 | 79.4 | 65.1 | -14.5 |

### Agent answer (answer_synthesizer)

Hub-origin **Route** segments in **MorningPeak** with OTP more than 2σ below the hub-route
network average are logistics outliers — likely congestion or scheduling stress on trunk
links. **ORD-LGA** is the strongest outlier (OTP ~58% vs network ~79%).

### `record_decision`

```json
{
  "category": "airline_logistics_outlier",
  "scenario": "Hub-origin routes with OTP >2 stddev below MorningPeak network average, 2005",
  "reasoning": "Hubs = top 20 origins by departures. OnTimeFlight per business rules. Outlier = otp_pct < avg - 2*stddev on routes with >=500 flights.",
  "outcome": "Worst outlier routes: ORD-LGA, ATL-EWR, DFW-ORD, LAX-ORD, ATL-ORD",
  "confidence": 0.94,
  "decision_maker": "airline-logistics-agent",
  "query_intent": "hub_route_otp_outliers_morning_peak",
  "query_params": {
    "year": 2005,
    "window": "MorningPeak",
    "hub_top_n": 20,
    "outlier_method": "2_stddev_below_mean",
    "min_route_flights": 500,
    "top_k": 5
  },
  "result_metrics": {
    "ORD-LGA_otp": 58.2,
    "ATL-EWR_otp": 61.5,
    "DFW-ORD_otp": 63.8,
    "network_avg_otp": 79.4,
    "outlier_threshold": 65.1
  },
  "sql_text": "<SQL above>"
}
```

### Follow-up — `compare_with_history`

**User:** Re-run the same outlier analysis for **2004** and compare.

**Tool:** `compare_with_history`

```json
{
  "query_intent": "hub_route_otp_outliers_morning_peak",
  "query_params": {"year": 2004, "window": "MorningPeak", "hub_top_n": 20},
  "match_mode": "intent",
  "result_metrics": {
    "ORD-LGA_otp": 62.1,
    "ATL-EWR_otp": 64.0,
    "network_avg_otp": 81.2
  }
}
```

**Expected summary:** ORD-LGA remained an outlier in both years; OTP improved ~4 pp YoY but
still below threshold — persistent logistics stress on that trunk route.

---

## Demo Chat 2 — Short-haul severe-delay rate outliers by carrier

**User:** Find **airline carriers** that are **outliers** for **severe delay rate** on
**short-haul logistics** (routes under **500 miles**) in **2003**. An carrier is an outlier
if its severe-delay rate exceeds the **peer median by more than 1.5× IQR** (upper fence).
Exclude cancelled flights. Record the decision and explain operational implications.

### Expected tool trace

| Step | Agent | Tool |
|------|--------|------|
| 1 | ontology_mapper | `get_business_rules` → `SevereDelay` (>60 min), `routeDistanceMiles` |
| 2 | ontology_mapper | Mapping plan: short-haul = `distance < 500`, group by carrier |
| 3 | sql_executor | `execute_query` |
| 4 | answer_synthesizer | `record_decision` |
| 5 | answer_synthesizer | `compare_with_history` (optional — vs prior severe-delay run) |

### Agent reasoning (ontology_mapper)

1. **routeDistanceMiles** — column `distance` on `flights`; short-haul filter `< 500`.
2. **SevereDelay** — `GREATEST(arrdelay, depdelay) > 60` per `delay_severity_rules`.
3. **KPI** — `severe_rate = severe_delays / non_cancelled_flights` per carrier.
4. **Outlier** — Tukey upper fence: `rate > Q3 + 1.5 * IQR` across carriers with
   ≥ 10,000 short-haul segments (statistical outlier, not fixed threshold).
5. Join **operatedBy**: `uniquecarrier = airlines.code`.

### SQL (sql_executor)

```sql
WITH carrier_short AS (
  SELECT
    f.uniquecarrier AS airline_code,
    a.description AS airline_name,
    COUNT(*) AS total_flights,
    SUM(CASE
      WHEN f.cancelled = 0
       AND GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60
      THEN 1 ELSE 0 END) AS severe_delays
  FROM airlinedata.flights f
  JOIN airlinedata.airlines a ON f.uniquecarrier = a.code
  WHERE f.year = 2003
    AND f.distance < 500
    AND f.cancelled = 0
  GROUP BY f.uniquecarrier, a.description
  HAVING COUNT(*) >= 10000
),
rates AS (
  SELECT
    airline_code,
    airline_name,
    total_flights,
    severe_delays,
    ROUND(100.0 * severe_delays / total_flights, 3) AS severe_rate_pct
  FROM carrier_short
),
quartiles AS (
  SELECT
    PERCENTILE(severe_rate_pct, 0.25) AS q1,
    PERCENTILE(severe_rate_pct, 0.50) AS median,
    PERCENTILE(severe_rate_pct, 0.75) AS q3
  FROM rates
)
SELECT
  r.airline_code,
  r.airline_name,
  r.total_flights,
  r.severe_rate_pct,
  q.median AS peer_median_pct,
  ROUND(q.q3 + 1.5 * (q.q3 - q.q1), 3) AS upper_fence_pct,
  ROUND(r.severe_rate_pct / q.median, 2) AS rate_vs_median_ratio
FROM rates r
CROSS JOIN quartiles q
WHERE r.severe_rate_pct > q.q3 + 1.5 * (q.q3 - q.q1)
ORDER BY r.severe_rate_pct DESC;
```

> **Note:** If `PERCENTILE` is unavailable in your Hive version, use `PERCENTILE_APPROX` or
> compute Q1/Q3 in a subquery with `NTILE(4)`.

### Illustrative result

| airline_code | airline_name | total_flights | severe_rate_pct | peer_median_pct | upper_fence_pct |
|---|---|---:|---:|---:|---:|
| EV | Atlantic Southeast Airlines | 412,880 | 2.847 | 1.102 | 2.310 |
| OH | Comair Inc. | 369,967 | 2.654 | 1.102 | 2.310 |
| YV | Mesa Airlines Inc. | 298,441 | 2.421 | 1.102 | 2.310 |

Non-outlier reference: **WN** severe_rate_pct ≈ 0.89% (below median — efficient short-haul ops).

### Agent answer (answer_synthesizer)

Regional carriers **EV**, **OH**, and **YV** are **statistical outliers** for **SevereDelay**
on sub-500-mile **Route** segments — rates above the Tukey upper fence vs peer airlines.
Short-haul logistics should have fewer severe delays; elevated rates suggest turnaround
chain breakdown (connecting **LateAircraftDelayReason**) or hub congestion effects.

### `record_decision`

```json
{
  "category": "airline_logistics_outlier",
  "scenario": "Carriers with severe delay rate outlier on short-haul routes (<500 mi), 2003",
  "reasoning": "SevereDelay >60 min per delay_severity_rules. Tukey fence Q3+1.5*IQR on carrier severe_rate. Min 10k short-haul flights for stability.",
  "outcome": "Outlier carriers: EV, OH, YV — severe rates 2.3-2.8% vs peer median ~1.1%",
  "confidence": 0.96,
  "decision_maker": "airline-logistics-agent",
  "query_intent": "carrier_severe_delay_outlier_short_haul",
  "query_params": {
    "year": 2003,
    "max_distance_miles": 500,
    "outlier_method": "tukey_upper_fence",
    "min_flights": 10000
  },
  "result_metrics": {
    "EV_severe_rate_pct": 2.847,
    "OH_severe_rate_pct": 2.654,
    "YV_severe_rate_pct": 2.421,
    "peer_median_pct": 1.102,
    "upper_fence_pct": 2.310,
    "WN_severe_rate_pct": 0.89
  },
  "sql_text": "<SQL above>"
}
```

### Follow-up — `compare_with_history`

**User:** Compare with the OTP outlier decision we recorded earlier — any carrier overlap?

**Tool:** `query_decisions` with `category=airline_logistics_outlier`, then
`explain_decision_delta` between the two `decision_id`s.

**Agent:** Route OTP outliers (Chat 1) flag **network segments**; carrier severe-delay
outliers (Chat 2) flag **operational performers**. Overlap is indirect — e.g. **OH** appears
in Chat 2; check if OH operates heavily on ORD-LGA-style trunk routes from Chat 1 via a
follow-up SQL join on `uniquecarrier` + `route_id`.

---

## Audit checklist (both chats)

| Check | Pass criteria |
|---|---|
| Business rules cited | `get_business_rules` in trace before SQL |
| Correct joins | `uniquecarrier = code`, not `carrier` |
| Decision persisted | `record_decision` → `store_path: /workspace/decisions/decisions.jsonl` |
| Not markdown-only | Tool response includes `decision_id`, `query_fingerprint` |
| History compare | Second run returns `matches` + `delta` in `compare_with_history` |

## Related docs

- [`airline_ontology_demo_chats.md`](airline_ontology_demo_chats.md) — baseline KPI chats
- [`docs/guides/airline-business-logic.md`](../docs/guides/airline-business-logic.md) — logistics ontology
- [`docs/guides/decision-store.md`](../docs/guides/decision-store.md) — JSONL store spec
- [`deploy/cloudera-agent-studio/multi-agent-workflow.md`](../deploy/cloudera-agent-studio/multi-agent-workflow.md) — agent setup
