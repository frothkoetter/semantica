-- Demo seed data for KDM Iceberg tables (Semantica MCP integration tests)

INSERT INTO kdm.natuerliche_person VALUES
  ('np-001', 'Mueller', 'Anna', DATE '1985-03-12', 'w', 'DE', 'ID-NP-001'),
  ('np-002', 'Schmidt', 'Thomas', DATE '1978-11-04', 'm', 'DE', 'ID-NP-002');

INSERT INTO kdm.juristische_person VALUES
  ('jp-001', 'Muster GmbH', 'GmbH', 'DE123456789'),
  ('jp-002', 'Beispiel AG', 'AG', 'DE987654321');

INSERT INTO kdm.anschrift VALUES
  ('adr-001', 'jp-001', NULL, 'Hauptstrasse', '10', '10115', 'Berlin', 'strassenanschrift'),
  ('adr-002', NULL, 'np-001', 'Gartenweg', '3a', '80331', 'Muenchen', 'strassenanschrift');

INSERT INTO kdm.eintragung VALUES
  ('enr-001', 'jp-001', 'hrb', 'F1103', 'Amtsgericht Berlin-Charlottenburg', 'HRB 123456 B'),
  ('enr-002', 'jp-002', 'hrb', 'D2601', 'Amtsgericht Muenchen', 'HRB 654321');

INSERT INTO kdm.betriebsstaette VALUES
  ('bs-001', 'jp-001', 'hauptniederlassung', 'Muster GmbH Hauptsitz'),
  ('bs-002', 'jp-001', 'zweigniederlassung', 'Muster GmbH Filiale Sued');

INSERT INTO kdm.kommunikation VALUES
  ('kom-001', 'jp-001', 'juristische_person', 'email', 'info@muster-gmbh.de', 'geschaeftlich'),
  ('kom-002', 'np-001', 'natuerliche_person', 'telefon', '+49 30 1234567', 'privat');

INSERT INTO kdm.gesellschafter VALUES
  ('gs-001', 'jp-001', 'np-001', NULL, 'natuerliche_person'),
  ('gs-002', 'jp-002', NULL, 'jp-001', 'juristische_person');

INSERT INTO kdm.wirtschaftliche_taetigkeit VALUES
  ('wt-001', 'jp-001', 'Softwareentwicklung', 'IT-Dienstleistungen'),
  ('wt-002', 'jp-002', 'Beratung', 'Unternehmensberatung');
