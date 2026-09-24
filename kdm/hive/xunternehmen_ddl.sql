-- XUnternehmen.Kerndatenmodell (KDM) v1.2 — Hive / Iceberg DDL
-- Ontology: https://w3id.org/kdm/
-- Database: xunternehmen

CREATE DATABASE IF NOT EXISTS xunternehmen
COMMENT 'XUnternehmen Kerndatenmodell — Demo-Schema aligned to kdm/ontology.owl';

-- ---------------------------------------------------------------------------
-- Kerndatenobjekte: Personen & wirtschaftliche Tätigkeit
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS xunternehmen.natuerliche_person (
  id STRING COMMENT 'PK — kdm:NatuerlichePerson',
  doktorgrad STRING COMMENT 'kdm:doktorgrad',
  geschlecht_code STRING COMMENT 'kdm:geschlechtCode (urn:xoev-de:xinneres:codeliste:geschlecht)',
  identifikationsnummer STRING COMMENT 'kdm:identifikationsnummer (IDNrG)',
  staatsangehoerigkeit_code STRING COMMENT 'kdm:staatsangehoerigkeitCode'
)
STORED BY ICEBERG;

CREATE TABLE IF NOT EXISTS xunternehmen.name_natuerliche_person (
  id STRING COMMENT 'PK — kdm:NameEinerNatuerlichenPerson',
  natuerliche_person_id STRING COMMENT 'FK natuerliche_person.id — kdm:nameEinerNatuerlichenPerson',
  vornamen STRING COMMENT 'kdm:vornamen',
  familienname STRING COMMENT 'kdm:familienname',
  geburtsname STRING COMMENT 'kdm:geburtsname',
  familienname_nicht_vorhanden BOOLEAN COMMENT 'kdm:familiennameNichtVorhanden',
  geburtsname_nicht_vorhanden BOOLEAN COMMENT 'kdm:geburtsnameNichtVorhanden',
  vornamen_nicht_vorhanden BOOLEAN COMMENT 'kdm:vornamenNichtVorhanden'
)
STORED BY ICEBERG;

CREATE TABLE IF NOT EXISTS xunternehmen.geburt (
  id STRING COMMENT 'PK — kdm:Geburt',
  natuerliche_person_id STRING COMMENT 'FK natuerliche_person.id — kdm:geburt',
  geburtsdatum STRING COMMENT 'kdm:geburtsdatum (teilbekanntes Datum als String)',
  ort_der_geburt STRING COMMENT 'kdm:ortDerGeburt',
  staat STRING COMMENT 'kdm:staat'
)
STORED BY ICEBERG;

CREATE TABLE IF NOT EXISTS xunternehmen.juristische_person (
  id STRING COMMENT 'PK — kdm:JuristischePerson',
  eingetragener_name STRING COMMENT 'kdm:eingetragenerName',
  bundeseinheitliche_wirtschaftsnummer STRING COMMENT 'kdm:bundeseinheitlicheWirtschaftsnummer',
  rechtsformen_code STRING COMMENT 'kdm:rechtsformenCode'
)
STORED BY ICEBERG;

CREATE TABLE IF NOT EXISTS xunternehmen.rechtsfaehige_personengesellschaft (
  id STRING COMMENT 'PK — kdm:RechtsfaehigePersonengesellschaft',
  eingetragener_name STRING COMMENT 'kdm:eingetragenerName',
  bundeseinheitliche_wirtschaftsnummer STRING COMMENT 'kdm:bundeseinheitlicheWirtschaftsnummer',
  rechtsformen_code STRING COMMENT 'kdm:rechtsformenCode'
)
STORED BY ICEBERG;

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

-- ---------------------------------------------------------------------------
-- Kerndatenobjekte: Anschrift (Inland/Ausland-Subtypen via anschrift_typ)
-- ---------------------------------------------------------------------------

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

-- ---------------------------------------------------------------------------
-- Kerndatenobjekte: Kommunikation (+ Email, Telefon, Telefax, De-Mail, Web)
-- ---------------------------------------------------------------------------

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

CREATE TABLE IF NOT EXISTS xunternehmen.zuordnung_kommunikation (
  id STRING COMMENT 'PK',
  owner_typ STRING COMMENT 'NatuerlichePerson | JuristischePerson | RechtsfaehigePersonengesellschaft | SonstigePersonenvereinigung | WirtschaftlicheTaetigkeit | Betriebsstaette',
  owner_id STRING COMMENT 'FK zum Owner',
  kommunikation_id STRING COMMENT 'FK kommunikation.id — kdm:kommunikation'
)
STORED BY ICEBERG;

-- ---------------------------------------------------------------------------
-- Kerndatenobjekte: Eintragung, Sitz, effektiver Verwaltungssitz
-- ---------------------------------------------------------------------------

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

-- ---------------------------------------------------------------------------
-- Kerndatenobjekte: Betriebsstätte, Wirtschaftszweig
-- ---------------------------------------------------------------------------

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

-- ---------------------------------------------------------------------------
-- Vorgänge: Antrag, Anzeige
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS xunternehmen.antrag (
  id STRING COMMENT 'PK — kdm:Antrag',
  vorgangsnummer STRING COMMENT 'Demo: Aktenzeichen',
  eingangsdatum DATE COMMENT 'Demo-Metadatum'
)
STORED BY ICEBERG;

CREATE TABLE IF NOT EXISTS xunternehmen.anzeige (
  id STRING COMMENT 'PK — kdm:Anzeige',
  vorgangsnummer STRING COMMENT 'Demo: Aktenzeichen',
  eingangsdatum DATE COMMENT 'Demo-Metadatum'
)
STORED BY ICEBERG;

-- ---------------------------------------------------------------------------
-- Rollen (BFO-Rollen im KDM)
-- ---------------------------------------------------------------------------

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
STORED BY ICEBERG;
