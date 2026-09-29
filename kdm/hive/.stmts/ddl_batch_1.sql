CREATE TABLE IF NOT EXISTS xunternehmen.sonstige_personenvereinigung (
  id STRING COMMENT 'PK — kdm:SonstigePersonenvereinigung',
  eingetragener_name STRING COMMENT 'kdm:eingetragenerName',
  bundeseinheitliche_wirtschaftsnummer STRING COMMENT 'kdm:bundeseinheitlicheWirtschaftsnummer',
  rechtsformen_code STRING COMMENT 'kdm:rechtsformenCode'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.wirtschaftliche_taetigkeit (
  id STRING COMMENT 'PK — kdm:WirtschaftlicheTaetigkeit',
  eingetragener_name STRING COMMENT 'kdm:eingetragenerName',
  bundeseinheitliche_wirtschaftsnummer STRING COMMENT 'kdm:bundeseinheitlicheWirtschaftsnummer',
  rechtsformen_code STRING COMMENT 'kdm:rechtsformenCode',
  geschaeftsbezeichnung STRING COMMENT 'kdm:geschaeftsbezeichnung',
  taetigkeit STRING COMMENT 'kdm:taetigkeit'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.anschrift (
  id STRING COMMENT 'PK — kdm:Anschrift',
  anschrift_typ STRING COMMENT 'INLAND_STRASSE | INLAND_POSTFACH | INLAND_GROSSEMPFAENGER | AUSLAND',
  art_anschrift_code STRING COMMENT 'kdm:artAnschriftCode',
  strasse STRING COMMENT 'kdm:strasse',
  hausnummer STRING COMMENT 'kdm:hausnummer',
  postleitzahl STRING COMMENT 'kdm:postleitzahl',
  ort STRING COMMENT 'kdm:ort',
  staat STRING COMMENT 'kdm:staat',
  postfach STRING COMMENT 'kdm:postfach (Großempfänger/Postfach)',
  gemeindeschluessel_code STRING COMMENT 'kdm:gemeindeschluesselCode (Straßenanschrift)',
  frueherer_gemeindename STRING COMMENT 'kdm:fruehererGemeindename',
  wohnungsinhaber STRING COMMENT 'kdm:wohnungsinhaber',
  zusatzangaben_anschrift STRING COMMENT 'kdm:zusatzangabenAnschrift'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_anschrift (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit | Betriebsstaette',
  owner_id STRING COMMENT 'FK zum Owner',
  anschrift_id STRING COMMENT 'FK anschrift.id — kdm:anschrift'
)
STORED BY ICEBERG;
CREATE TABLE IF NOT EXISTS xunternehmen.kommunikation (
  id STRING COMMENT 'PK — kdm:Kommunikation',
  kommunikation_art STRING COMMENT 'EMAIL | TELEFON | TELEFAX | DEMAIL | WEB',
  klassifikation_kommunikation_code STRING COMMENT 'kdm:klassifikationKommunikationCode',
  kommunikation_hinweis STRING COMMENT 'kdm:kommunikationHinweis',
  emailadresse STRING COMMENT 'kdm:emailadresse — kdm:Email',
  telefonnummer STRING COMMENT 'kdm:telefonnummer — kdm:Telefon',
  telefaxnummer STRING COMMENT 'kdm:telefaxnummer — kdm:Telefax',
  demailadresse STRING COMMENT 'kdm:demailadresse — kdm:Demail',
  webadresse STRING COMMENT 'kdm:webadresse — kdm:WebAdresse'
)
STORED BY ICEBERG;