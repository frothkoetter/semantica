-- XUnternehmen.Kerndatenmodell — synthetische Demo-Daten (DML)
-- Ausführen nach xunternehmen_ddl.sql
-- Demo-Szenario:
--   np-001 Erika Mustermann (Einzelunternehmerin)
--   jp-001 Muster Consulting GmbH
--   pg-001 Meyer & Soehne OHG
--   spv-001 Projekt Alpha GbR
--   wt-001 Mustermann IT (eingetragene Einzelgewerbe)
--   wt-002 Muster Consulting GmbH (wirtschaftliche Tätigkeit der GmbH)

-- ---------------------------------------------------------------------------
-- Natürliche Personen
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.natuerliche_person VALUES
  ('np-001', NULL, 'w', '12345678901', '000'),
  ('np-002', 'Dr.', 'm', '23456789012', '000'),
  ('np-003', NULL, 'w', '34567890123', '000'),
  ('np-004', NULL, 'm', '45678901234', '124');

INSERT INTO xunternehmen.name_natuerliche_person VALUES
  ('nn-001', 'np-001', 'Erika', 'Mustermann', 'Muster', FALSE, FALSE, FALSE),
  ('nn-002', 'np-002', 'Thomas', 'Meyer', 'Meyer', FALSE, FALSE, FALSE),
  ('nn-003', 'np-003', 'Anna', 'Schmidt', 'Schmidt', FALSE, FALSE, FALSE),
  ('nn-004', 'np-004', 'Jonas', 'Becker', 'Becker', FALSE, FALSE, FALSE);

INSERT INTO xunternehmen.geburt VALUES
  ('gb-001', 'np-001', '1985-03-15', 'Bremen', '000'),
  ('gb-002', 'np-002', '1978-11-02', 'Hamburg', '000'),
  ('gb-003', 'np-003', '1990-07-21', 'Berlin', '000'),
  ('gb-004', 'np-004', '1982-01-30', 'Wien', '124');

-- ---------------------------------------------------------------------------
-- Juristische Person, Personengesellschaft, sonstige Personenvereinigung
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.juristische_person VALUES
  ('jp-001', 'Muster Consulting GmbH', 'DE1234567890123', '221110');

INSERT INTO xunternehmen.rechtsfaehige_personengesellschaft VALUES
  ('pg-001', 'Meyer & Soehne OHG', 'DE2345678901234', '221200');

INSERT INTO xunternehmen.sonstige_personenvereinigung VALUES
  ('spv-001', 'Projekt Alpha GbR', 'DE3456789012345', '221300');

-- ---------------------------------------------------------------------------
-- Wirtschaftliche Tätigkeiten
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.wirtschaftliche_taetigkeit VALUES
  ('wt-001', 'Mustermann IT', 'DE4567890123456', '221000', 'Mustermann IT', 'IT-Beratung und Softwareentwicklung'),
  ('wt-002', 'Muster Consulting GmbH', 'DE1234567890123', '221110', 'Muster Consulting', 'Unternehmensberatung');

-- ---------------------------------------------------------------------------
-- Anschriften
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.anschrift VALUES
  ('as-001', 'INLAND_STRASSE', '01', 'Hauptstrasse', '42', '28195', 'Bremen', '000', NULL, '04011000', NULL, NULL, NULL),
  ('as-002', 'INLAND_STRASSE', '01', 'Am Wall', '7', '28195', 'Bremen', '000', NULL, '04011000', NULL, NULL, 'Hinterhaus'),
  ('as-003', 'INLAND_POSTFACH', '02', NULL, NULL, '20095', 'Hamburg', '000', '123456', NULL, NULL, NULL, NULL),
  ('as-004', 'INLAND_GROSSEMPFAENGER', '03', 'Industriestr.', '15', '10115', 'Berlin', '000', '998877', NULL, NULL, NULL, NULL),
  ('as-005', 'AUSLAND', '04', 'Ringstrasse', '10', '1010', 'Wien', '124', NULL, NULL, NULL, NULL, NULL),
  ('as-006', 'INLAND_STRASSE', '01', 'Gewerbepark', '3', '28309', 'Bremen', '000', NULL, '04011000', NULL, NULL, NULL);

INSERT INTO xunternehmen.zuordnung_anschrift VALUES
  ('za-001', 'NatuerlichePerson', 'np-001', 'as-001'),
  ('za-002', 'JuristischePerson', 'jp-001', 'as-002'),
  ('za-003', 'RechtsfaehigePersonengesellschaft', 'pg-001', 'as-003'),
  ('za-004', 'SonstigePersonenvereinigung', 'spv-001', 'as-004'),
  ('za-005', 'WirtschaftlicheTaetigkeit', 'wt-001', 'as-001'),
  ('za-006', 'WirtschaftlicheTaetigkeit', 'wt-002', 'as-002');

-- ---------------------------------------------------------------------------
-- Kommunikation
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.kommunikation VALUES
  ('km-001', 'EMAIL', '02', 'Geschaeftlich', 'erika.mustermann@mustermann-it.de', NULL, NULL, NULL, NULL),
  ('km-002', 'TELEFON', '02', 'Geschaeftlich', NULL, '+49 421 1234567', NULL, NULL, NULL),
  ('km-003', 'TELEFAX', '02', 'Geschaeftlich', NULL, NULL, '+49 421 1234568', NULL, NULL),
  ('km-004', 'DEMAIL', '02', 'Geschaeftlich', NULL, NULL, NULL, 'erika.mustermann@mustermann.de-mail.de', NULL),
  ('km-005', 'WEB', '02', 'Geschaeftlich', NULL, NULL, NULL, NULL, 'https://www.mustermann-it.de'),
  ('km-006', 'EMAIL', '02', 'Geschaeftlich', 'info@muster-consulting.de', NULL, NULL, NULL, NULL),
  ('km-007', 'TELEFON', '02', 'Zentrale', NULL, '+49 421 9876543', NULL, NULL, NULL);

INSERT INTO xunternehmen.zuordnung_kommunikation VALUES
  ('zk-001', 'NatuerlichePerson', 'np-001', 'km-001'),
  ('zk-002', 'NatuerlichePerson', 'np-001', 'km-002'),
  ('zk-003', 'WirtschaftlicheTaetigkeit', 'wt-001', 'km-004'),
  ('zk-004', 'WirtschaftlicheTaetigkeit', 'wt-001', 'km-005'),
  ('zk-005', 'JuristischePerson', 'jp-001', 'km-006'),
  ('zk-006', 'JuristischePerson', 'jp-001', 'km-007');

-- ---------------------------------------------------------------------------
-- Eintragungen, Sitz, effektiver Verwaltungssitz
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.eintragung VALUES
  ('ei-001', '01', 'HRB 12345 KI', 'K1101', 'Amtsgericht Bremen', 'Bremen', '000', NULL),
  ('ei-002', '01', 'HRA 67890', 'K1101', 'Amtsgericht Bremen', 'Bremen', '000', NULL),
  ('ei-003', '01', 'HRB 11111', 'K1101', 'Amtsgericht Bremen', 'Bremen', '000', NULL);

INSERT INTO xunternehmen.zuordnung_eintragung VALUES
  ('ze-001', 'JuristischePerson', 'jp-001', 'ei-001'),
  ('ze-002', 'RechtsfaehigePersonengesellschaft', 'pg-001', 'ei-002'),
  ('ze-003', 'WirtschaftlicheTaetigkeit', 'wt-002', 'ei-003');

INSERT INTO xunternehmen.sitz VALUES
  ('si-001', 'Bremen', '000'),
  ('si-002', 'Hamburg', '000'),
  ('si-003', 'Berlin', '000');

INSERT INTO xunternehmen.zuordnung_sitz VALUES
  ('zs-001', 'JuristischePerson', 'jp-001', 'si-001'),
  ('zs-002', 'RechtsfaehigePersonengesellschaft', 'pg-001', 'si-002'),
  ('zs-003', 'SonstigePersonenvereinigung', 'spv-001', 'si-003');

INSERT INTO xunternehmen.effektiver_verwaltungssitz VALUES
  ('ev-001', 'Bremen', '000'),
  ('ev-002', 'Hamburg', '000');

INSERT INTO xunternehmen.zuordnung_effektiver_verwaltungssitz VALUES
  ('zev-001', 'JuristischePerson', 'jp-001', 'ev-001'),
  ('zev-002', 'RechtsfaehigePersonengesellschaft', 'pg-001', 'ev-002');

-- ---------------------------------------------------------------------------
-- Betriebsstätte, Wirtschaftszweig
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.betriebsstaette VALUES
  ('bs-001', 'wt-001', '01');

INSERT INTO xunternehmen.zuordnung_anschrift VALUES
  ('za-007', 'Betriebsstaette', 'bs-001', 'as-006');

INSERT INTO xunternehmen.zuordnung_kommunikation VALUES
  ('zk-007', 'Betriebsstaette', 'bs-001', 'km-003');

INSERT INTO xunternehmen.wirtschaftszweig VALUES
  ('wz-001', 'wt-001', '62020', 'WZ2008'),
  ('wz-002', 'wt-002', '70220', 'WZ2008');

-- ---------------------------------------------------------------------------
-- Rollen
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.rolle_wirtschaftlich_taetiger VALUES
  ('rwt-001', 'wt-001', 'NatuerlichePerson', 'np-001'),
  ('rwt-002', 'wt-002', 'JuristischePerson', 'jp-001');

INSERT INTO xunternehmen.rolle_gesellschafter VALUES
  ('rgs-001', 'pg-001', 'NatuerlichePerson', 'np-002', '02'),
  ('rgs-002', 'pg-001', 'NatuerlichePerson', 'np-003', '01');

INSERT INTO xunternehmen.rolle_gesetzlicher_vertreter VALUES
  ('rgv-001', 'JuristischePerson', 'jp-001', 'NatuerlichePerson', 'np-001', '3'),
  ('rgv-002', 'NatuerlichePerson', 'np-001', 'NatuerlichePerson', 'np-003', '1');

INSERT INTO xunternehmen.rolle_beteiligter VALUES
  ('rbt-001', 'spv-001', 'np-002'),
  ('rbt-002', 'spv-001', 'np-003');

-- ---------------------------------------------------------------------------
-- Antrag & Anzeige (Vorgänge)
-- ---------------------------------------------------------------------------

INSERT INTO xunternehmen.antrag VALUES
  ('an-001', 'GWA-2026-00042', DATE '2026-03-01');

INSERT INTO xunternehmen.anzeige VALUES
  ('az-001', 'GWA-2026-00108', DATE '2026-03-15');

INSERT INTO xunternehmen.rolle_antragsteller VALUES
  ('rat-001', 'an-001', 'WirtschaftlicheTaetigkeit', 'wt-001', '02');

INSERT INTO xunternehmen.rolle_anzeigender VALUES
  ('raz-001', 'az-001', 'JuristischePerson', 'jp-001', '01');

INSERT INTO xunternehmen.rolle_handelnde_person VALUES
  ('rhp-001', 'Antrag', 'an-001', 'np-001'),
  ('rhp-002', 'Anzeige', 'az-001', 'np-002');

INSERT INTO xunternehmen.rolle_ansprechpartner VALUES
  ('rap-001', 'Antrag', 'an-001', 'np-003'),
  ('rap-002', 'Anzeige', 'az-001', 'np-001');
