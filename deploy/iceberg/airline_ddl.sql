-- Airline Data Ontology — Iceberg tables on Hive/CDW
-- Database: airline
-- Ontology: https://w3id.org/airline/ontology#

CREATE DATABASE IF NOT EXISTS airline
COMMENT 'Airline domain — disjoint from KDM';

CREATE TABLE IF NOT EXISTS airline.airline (
  id STRING COMMENT 'PK',
  name STRING COMMENT 'Airline name',
  iata_code STRING COMMENT 'IATA airline code',
  icao_code STRING COMMENT 'ICAO airline code'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS airline.airport (
  id STRING COMMENT 'PK',
  name STRING,
  iata_code STRING COMMENT 'IATA airport code',
  city STRING,
  country_code STRING
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS airline.aircraft (
  id STRING COMMENT 'PK',
  registration STRING COMMENT 'Tail number',
  aircraft_type STRING,
  airline_id STRING COMMENT 'FK airline.id'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS airline.flight (
  id STRING COMMENT 'PK',
  flight_number STRING,
  airline_id STRING COMMENT 'FK airline.id — operatedBy',
  origin_airport_id STRING COMMENT 'FK airport.id — originAirport',
  destination_airport_id STRING COMMENT 'FK airport.id — destinationAirport',
  aircraft_id STRING COMMENT 'FK aircraft.id — assignedAircraft',
  scheduled_departure TIMESTAMP,
  scheduled_arrival TIMESTAMP,
  status STRING COMMENT 'scheduled | departed | arrived | cancelled | delayed'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS airline.delay_breakdown (
  id STRING COMMENT 'PK',
  flight_id STRING COMMENT 'FK flight.id — hasDelayBreakdown',
  cause_code STRING,
  cause_description STRING,
  delay_minutes INT
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');
