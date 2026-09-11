-- Demo seed for airline Iceberg tables

INSERT INTO airline.airline VALUES
  ('al-001', 'Lufthansa', 'LH', 'DLH'),
  ('al-002', 'Eurowings', 'EW', 'EWG');

INSERT INTO airline.airport VALUES
  ('ap-001', 'Frankfurt am Main', 'FRA', 'Frankfurt', 'DE'),
  ('ap-002', 'Muenchen', 'MUC', 'Muenchen', 'DE'),
  ('ap-003', 'Berlin Brandenburg', 'BER', 'Berlin', 'DE');

INSERT INTO airline.aircraft VALUES
  ('ac-001', 'D-AIXA', 'A350-900', 'al-001'),
  ('ac-002', 'D-ABYT', 'B747-8', 'al-001'),
  ('ac-003', 'D-AEWM', 'A320neo', 'al-002');

INSERT INTO airline.flight VALUES
  ('fl-001', 'LH400', 'al-001', 'ap-001', 'ap-002', 'ac-001', TIMESTAMP '2026-09-10 08:00:00', TIMESTAMP '2026-09-10 09:10:00', 'arrived'),
  ('fl-002', 'LH100', 'al-001', 'ap-002', 'ap-001', 'ac-002', TIMESTAMP '2026-09-10 14:30:00', TIMESTAMP '2026-09-10 15:45:00', 'delayed'),
  ('fl-003', 'EW8050', 'al-002', 'ap-001', 'ap-003', 'ac-003', TIMESTAMP '2026-09-10 18:00:00', TIMESTAMP '2026-09-10 19:15:00', 'scheduled');

INSERT INTO airline.delay_breakdown VALUES
  ('db-001', 'fl-002', 'WEATHER', 'Thunderstorms Munich area', 45);
