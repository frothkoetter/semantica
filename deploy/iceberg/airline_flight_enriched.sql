-- OPTIONAL / NOT USED by default — Semantica compiles the same logic at runtime.
-- See examples/airline_business_sql.py (sql_runtime_flight_subquery).
-- Keep this file only if you want a pre-materialized Hive view for ad-hoc BI tools.

CREATE DATABASE IF NOT EXISTS airlinedata;

DROP VIEW IF EXISTS airlinedata.flight_enriched;

CREATE VIEW airlinedata.flight_enriched AS
SELECT
  f.*,
  CONCAT(f.origin, '-', f.dest) AS route_id,
  CASE
    WHEN f.crsdeptime BETWEEN 600 AND 959 THEN 'MorningPeak'
    WHEN f.crsdeptime BETWEEN 1000 AND 1659 THEN 'Midday'
    WHEN f.crsdeptime BETWEEN 1700 AND 2059 THEN 'EveningPeak'
    WHEN f.crsdeptime >= 2100 OR f.crsdeptime <= 559 THEN 'Overnight'
    ELSE 'Unknown'
  END AS scheduled_in_window,
  CASE
    WHEN f.cancelled = 1 THEN 'CancelledFlight'
    WHEN f.diverted IN ('1', 'Y') THEN 'DivertedFlight'
    WHEN COALESCE(f.arrdelay, 0) <= 15 AND COALESCE(f.depdelay, 0) <= 15 THEN 'OnTimeFlight'
    WHEN f.cancelled = 0 AND (COALESCE(f.arrdelay, 0) > 15 OR COALESCE(f.depdelay, 0) > 15) THEN 'DelayedFlight'
    ELSE 'Flight'
  END AS flight_status,
  CASE
    WHEN f.cancelled = 0 AND GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) BETWEEN 16 AND 30 THEN 'MinorDelay'
    WHEN f.cancelled = 0 AND GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) BETWEEN 31 AND 60 THEN 'ModerateDelay'
    WHEN f.cancelled = 0 AND GREATEST(COALESCE(f.arrdelay, 0), COALESCE(f.depdelay, 0)) > 60 THEN 'SevereDelay'
    ELSE NULL
  END AS delay_severity,
  CASE
    WHEN f.cancelled = 0 AND COALESCE(f.carrierdelay, 0) > 0
      AND COALESCE(f.carrierdelay, 0) >= COALESCE(f.weatherdelay, 0)
      AND COALESCE(f.carrierdelay, 0) >= COALESCE(f.nasdelay, 0)
      AND COALESCE(f.carrierdelay, 0) >= COALESCE(f.securitydelay, 0)
      AND COALESCE(f.carrierdelay, 0) >= COALESCE(f.lateaircraftdelay, 0) THEN 'CarrierDelayReason'
    WHEN f.cancelled = 0 AND COALESCE(f.weatherdelay, 0) > 0
      AND COALESCE(f.weatherdelay, 0) >= COALESCE(f.carrierdelay, 0)
      AND COALESCE(f.weatherdelay, 0) >= COALESCE(f.nasdelay, 0)
      AND COALESCE(f.weatherdelay, 0) >= COALESCE(f.securitydelay, 0)
      AND COALESCE(f.weatherdelay, 0) >= COALESCE(f.lateaircraftdelay, 0) THEN 'WeatherDelayReason'
    WHEN f.cancelled = 0 AND COALESCE(f.nasdelay, 0) > 0
      AND COALESCE(f.nasdelay, 0) >= COALESCE(f.carrierdelay, 0)
      AND COALESCE(f.nasdelay, 0) >= COALESCE(f.weatherdelay, 0)
      AND COALESCE(f.nasdelay, 0) >= COALESCE(f.securitydelay, 0)
      AND COALESCE(f.nasdelay, 0) >= COALESCE(f.lateaircraftdelay, 0) THEN 'NASDelayReason'
    WHEN f.cancelled = 0 AND COALESCE(f.securitydelay, 0) > 0
      AND COALESCE(f.securitydelay, 0) >= COALESCE(f.carrierdelay, 0)
      AND COALESCE(f.securitydelay, 0) >= COALESCE(f.weatherdelay, 0)
      AND COALESCE(f.securitydelay, 0) >= COALESCE(f.nasdelay, 0)
      AND COALESCE(f.securitydelay, 0) >= COALESCE(f.lateaircraftdelay, 0) THEN 'SecurityDelayReason'
    WHEN f.cancelled = 0 AND COALESCE(f.lateaircraftdelay, 0) > 0
      AND COALESCE(f.lateaircraftdelay, 0) >= COALESCE(f.carrierdelay, 0)
      AND COALESCE(f.lateaircraftdelay, 0) >= COALESCE(f.weatherdelay, 0)
      AND COALESCE(f.lateaircraftdelay, 0) >= COALESCE(f.nasdelay, 0)
      AND COALESCE(f.lateaircraftdelay, 0) >= COALESCE(f.securitydelay, 0) THEN 'LateAircraftDelayReason'
    ELSE NULL
  END AS primary_delay_reason
FROM airlinedata.flights f;
