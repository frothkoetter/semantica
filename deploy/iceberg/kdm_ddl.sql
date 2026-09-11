-- XUnternehmen.Kerndatenmodell (KDM) — Iceberg tables on Hive/CDW
-- Database: kdm
-- Ontology: https://w3id.org/kdm/

CREATE DATABASE IF NOT EXISTS kdm
COMMENT 'XUnternehmen Kerndatenmodell — Semantica demo schema';

-- Natürliche Person (KDM: NatuerlichePerson)
CREATE TABLE IF NOT EXISTS kdm.natuerliche_person (
  id STRING COMMENT 'Technische ID',
  familienname STRING COMMENT 'KDM: familienname',
  vornamen STRING COMMENT 'KDM: vornamen',
  geburtsdatum DATE COMMENT 'KDM: geburtsdatum (Geburt)',
  geschlecht_code STRING COMMENT 'KDM: geschlechtCode (xoev Codeliste)',
  staatsangehoerigkeit_code STRING COMMENT 'KDM: staatsangehoerigkeitCode',
  identifikationsnummer STRING COMMENT 'KDM: identifikationsnummer'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Juristische Person (KDM: JuristischePerson)
CREATE TABLE IF NOT EXISTS kdm.juristische_person (
  id STRING,
  firmenname STRING COMMENT 'KDM: eingetragenerName',
  rechtsform_code STRING COMMENT 'KDM: rechtsformenCode',
  wirtschaftsnummer STRING COMMENT 'KDM: bundeseinheitlicheWirtschaftsnummer'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Anschrift (KDM: Anschrift / AnschriftInlandStrassenanschrift)
CREATE TABLE IF NOT EXISTS kdm.anschrift (
  id STRING,
  juristische_person_id STRING,
  natuerliche_person_id STRING,
  strasse STRING COMMENT 'KDM: strasse',
  hausnummer STRING COMMENT 'KDM: hausnummer',
  postleitzahl STRING COMMENT 'KDM: postleitzahl',
  ort STRING COMMENT 'KDM: ort',
  art_anschrift_code STRING COMMENT 'KDM: artAnschriftCode'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Eintragung (KDM: Eintragung)
CREATE TABLE IF NOT EXISTS kdm.eintragung (
  id STRING,
  juristische_person_id STRING,
  art_eintragung_code STRING COMMENT 'KDM: artEintragungCode',
  registergericht_code STRING COMMENT 'KDM: registergerichtCode',
  registergericht_bezeichnung STRING COMMENT 'KDM: registergerichtBezeichnung',
  eintragungsnummer STRING COMMENT 'KDM: eintragungsnummer'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Betriebsstätte (KDM: Betriebsstaette)
CREATE TABLE IF NOT EXISTS kdm.betriebsstaette (
  id STRING,
  juristische_person_id STRING,
  art_betriebsstaette_code STRING COMMENT 'KDM: artBetriebsstaetteCode',
  geschaeftsbezeichnung STRING COMMENT 'KDM: geschaeftsbezeichnung'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Kommunikation (KDM: Kommunikation / Email / Telefon)
CREATE TABLE IF NOT EXISTS kdm.kommunikation (
  id STRING,
  bezug_id STRING COMMENT 'FK zu natuerliche_person oder juristische_person',
  bezug_typ STRING COMMENT 'natuerliche_person | juristische_person',
  kanal STRING COMMENT 'email | telefon | telefax | demail | web',
  wert STRING COMMENT 'KDM: emailadresse / telefonnummer / ...',
  klassifikation_code STRING COMMENT 'KDM: klassifikationKommunikationCode'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Gesellschafter (KDM: Gesellschafter)
CREATE TABLE IF NOT EXISTS kdm.gesellschafter (
  id STRING,
  personengesellschaft_id STRING,
  gesellschafter_person_id STRING,
  gesellschafter_unternehmen_id STRING,
  art_gesellschafter_code STRING COMMENT 'KDM: artGesellschafterCode'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');

-- Wirtschaftliche Tätigkeit (KDM: WirtschaftlicheTaetigkeit)
CREATE TABLE IF NOT EXISTS kdm.wirtschaftliche_taetigkeit (
  id STRING,
  wirtschaftlich_taetiger_id STRING,
  taetigkeit STRING COMMENT 'KDM: taetigkeit',
  geschaeftsbezeichnung STRING COMMENT 'KDM: geschaeftsbezeichnung'
)
STORED BY 'org.apache.iceberg.mr.hive.HiveIcebergStorageHandler'
TBLPROPERTIES ('format-version'='2');
