CREATE TABLE IF NOT EXISTS xunternehmen.effektiver_verwaltungssitz (
  id STRING COMMENT 'PK — kdm:EffektiverVerwaltungssitz',
  ort STRING COMMENT 'kdm:ort',
  staat STRING COMMENT 'kdm:staat'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_effektiver_verwaltungssitz (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung',
  owner_id STRING COMMENT 'FK zum Owner',
  effektiver_verwaltungssitz_id STRING COMMENT 'FK effektiver_verwaltungssitz.id — kdm:effektiverVerwaltungssitz'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.betriebsstaette (
  id STRING COMMENT 'PK — kdm:Betriebsstaette',
  wirtschaftliche_taetigkeit_id STRING COMMENT 'FK wirtschaftliche_taetigkeit.id — kdm:betriebsstaette',
  art_betriebsstaette_code STRING COMMENT 'kdm:artBetriebsstaetteCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.wirtschaftszweig (
  id STRING COMMENT 'PK — kdm:Wirtschaftszweig',
  wirtschaftliche_taetigkeit_id STRING COMMENT 'FK wirtschaftliche_taetigkeit.id — kdm:wirtschaftszweig',
  wirtschaftszweigschluessel STRING COMMENT 'kdm:wirtschaftszweigschluessel',
  version_wirtschaftszweigschluessel_code STRING COMMENT 'kdm:versionWirtschaftszweigschluesselCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.antrag (
  id STRING COMMENT 'PK — kdm:Antrag',
  vorgangsnummer STRING COMMENT 'Demo: Aktenzeichen',
  eingangsdatum DATE COMMENT 'Demo-Metadatum'
)
STORED BY ICEBERG;