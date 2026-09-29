CREATE TABLE IF NOT EXISTS xunternehmen.rolle_antragsteller (
  id STRING COMMENT 'PK — kdm:Antragsteller',
  antrag_id STRING COMMENT 'FK antrag.id — kdm:antragsteller',
  subject_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit',
  subject_id STRING COMMENT 'FK — kdm:antragstellerID',
  art_angabe_antragsteller_anzeigender_code STRING COMMENT 'kdm:artAngabeAntragstellerAnzeigenderCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_anzeigender (
  id STRING COMMENT 'PK — kdm:Anzeigender',
  anzeige_id STRING COMMENT 'FK anzeige.id — kdm:anzeigender',
  subject_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit',
  subject_id STRING COMMENT 'FK — kdm:anzeigenderID',
  art_angabe_antragsteller_anzeigender_code STRING COMMENT 'kdm:artAngabeAntragstellerAnzeigenderCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_handelnde_person (
  id STRING COMMENT 'PK — kdm:HandelndePerson',
  vorgang_typ STRING COMMENT 'Antrag | Anzeige',
  vorgang_id STRING COMMENT 'FK antrag.id oder anzeige.id',
  natuerliche_person_id STRING COMMENT 'FK natuerliche_person.id — kdm:handelndePersonID'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.rolle_ansprechpartner (
  id STRING COMMENT 'PK — kdm:Ansprechpartner',
  vorgang_typ STRING COMMENT 'Antrag | Anzeige',
  vorgang_id STRING COMMENT 'FK antrag.id oder anzeige.id',
  natuerliche_person_id STRING COMMENT 'FK natuerliche_person.id — kdm:ansprechpartnerID'
)
STORED BY ICEBERG;;