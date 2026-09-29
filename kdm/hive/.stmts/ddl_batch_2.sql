CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_kommunikation (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit | Betriebsstaette',
  owner_id STRING COMMENT 'FK zum Owner',
  kommunikation_id STRING COMMENT 'FK kommunikation.id — kdm:kommunikation'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.eintragung (
  id STRING COMMENT 'PK — kdm:Eintragung',
  art_eintragung_code STRING COMMENT 'kdm:artEintragungCode',
  eintragungsnummer STRING COMMENT 'kdm:eintragungsnummer',
  registergericht_code STRING COMMENT 'kdm:registergerichtCode',
  registergericht_bezeichnung STRING COMMENT 'kdm:registergerichtBezeichnung',
  ort STRING COMMENT 'kdm:ort',
  staat STRING COMMENT 'kdm:staat',
  stiftungsverzeichnis STRING COMMENT 'kdm:stiftungsverzeichnis'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_eintragung (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit',
  owner_id STRING COMMENT 'FK zum Owner',
  eintragung_id STRING COMMENT 'FK eintragung.id — kdm:eintragung'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.sitz (
  id STRING COMMENT 'PK — kdm:Sitz',
  ort STRING COMMENT 'kdm:ort',
  staat STRING COMMENT 'kdm:staat'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_sitz (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung',
  owner_id STRING COMMENT 'FK zum Owner',
  sitz_id STRING COMMENT 'FK sitz.id — kdm:sitz'
)
STORED BY ICEBERG;