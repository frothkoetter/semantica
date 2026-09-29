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