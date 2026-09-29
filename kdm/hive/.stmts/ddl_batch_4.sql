CREATE TABLE IF NOT EXISTS xunternehmen.anzeige (
  id STRING COMMENT 'PK — kdm:Anzeige',
  vorgangsnummer STRING COMMENT 'Demo: Aktenzeichen',
  eingangsdatum DATE COMMENT 'Demo-Metadatum'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_wirtschaftlich_taetiger (
  id STRING COMMENT 'PK — kdm:WirtschaftlichTaetiger',
  wirtschaftliche_taetigkeit_id STRING COMMENT 'FK wirtschaftliche_taetigkeit.id',
  subject_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung',
  subject_id STRING COMMENT 'FK — kdm:wirtschaftlichTaetigerID'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_gesellschafter (
  id STRING COMMENT 'PK — kdm:Gesellschafter',
  personengesellschaft_id STRING COMMENT 'FK rechtsfaehige_personengesellschaft.id — kdm:Personengesellschaft/gesellschafter',
  subject_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft',
  subject_id STRING COMMENT 'FK — kdm:gesellschafterID',
  art_gesellschafter_code STRING COMMENT 'kdm:artGesellschafterCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_gesetzlicher_vertreter (
  id STRING COMMENT 'PK — kdm:GesetzlicherVertreter',
  represented_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson',
  represented_id STRING COMMENT 'FK — Domain kdm:gesetzlicherVertreter',
  vertreter_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson',
  vertreter_id STRING COMMENT 'FK — kdm:gesetzlicherVertreterID',
  art_gesetzlicher_vertreter_code STRING COMMENT 'kdm:artGesetzlicherVertreterCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_beteiligter (
  id STRING COMMENT 'PK — kdm:Beteiligter',
  sonstige_personenvereinigung_id STRING COMMENT 'FK sonstige_personenvereinigung.id — kdm:beteiligter',
  natuerliche_person_id STRING COMMENT 'FK natuerliche_person.id — kdm:beteiligterID'
)
STORED BY ICEBERG;