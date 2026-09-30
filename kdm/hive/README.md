# XUnternehmen KDM — Hive/Iceberg Demo-Datenbank

Datenbank **`xunternehmen`**: 29 Iceberg-Tabellen aligned to `kdm/ontology.owl` + synthetische Demo-Daten für Agent-Studio-Analytics.

## Artefakte

| Datei | Inhalt |
|---|---|
| `xunternehmen_ddl.sql` | `CREATE DATABASE` + 29 `CREATE TABLE … STORED BY ICEBERG` |
| `xunternehmen_seed.sql` | Kleines Hand-Demo (~4 NP, 1 JP, Antrag `an-001`) |
| `xunternehmen_seed_medium.sql` | ~18k Zeilen, 800 NP / 600 JP, alle 29 Tabellen + Governance-Anker |
| `xunternehmen_seed_large.sql` | ~90k Zeilen, volle Demo (inkl. `an-001902`, Tier-Analytics) |
| `generate_xunternehmen_seed.py` | Generator für medium/large |
| `run_hive_sql.py` | DDL/DML via impyla (HIVE_* env) |
| `hive.env.example` | Credential-Vorlage |

## Tabellen (29)

**Kerndaten:** `natuerliche_person`, `name_natuerliche_person`, `geburt`, `juristische_person`, `rechtsfaehige_personengesellschaft`, `sonstige_personenvereinigung`, `wirtschaftliche_taetigkeit`

**Anschrift / Kommunikation / Register:** `anschrift`, `kommunikation`, `eintragung`, `sitz`, `effektiver_verwaltungssitz`, `betriebsstaette`, `wirtschaftszweig`

**Zuordnung (polymorph, `owner_typ`):** `zuordnung_anschrift`, `zuordnung_kommunikation`, `zuordnung_eintragung`, `zuordnung_sitz`, `zuordnung_effektiver_verwaltungssitz`

**Vorgänge:** `antrag`, `anzeige`

**Rollen:** `rolle_wirtschaftlich_taetiger`, `rolle_gesellschafter`, `rolle_gesetzlicher_vertreter`, `rolle_beteiligter`, `rolle_antragsteller`, `rolle_anzeigender`, `rolle_handelnde_person`, `rolle_ansprechpartner`

## Schnellstart

### 1. Credentials

```bash
cp kdm/hive/hive.env.example kdm/hive/hive.env.local
# HIVE_USER / HIVE_PASSWORD eintragen
export HIVE_DATABASE=xunternehmen
```

### 2. DDL + Seed laden

```bash
# Kleines Demo (Tutorial, wenige Zeilen)
./kdm/hive/setup_kdm_demo.sh small

# Mittleres Demo (~500–800 Zeilen/Kernentität, empfohlen für Dev + Agent Studio)
./kdm/hive/setup_kdm_demo.sh medium

# Volles Demo (~3k JP, Tier-Verteilung, an-001902 — Agent Studio)
./kdm/hive/setup_kdm_demo.sh large
```

Manuell:

```bash
set -a && source kdm/hive/hive.env.local && set +a
export HIVE_DATABASE=xunternehmen

python kdm/hive/run_hive_sql.py kdm/hive/xunternehmen_ddl.sql
python kdm/hive/run_hive_sql.py kdm/hive/xunternehmen_seed.sql
```

### 3. Prüfen

```sql
USE xunternehmen;
SHOW TABLES;
SELECT COUNT(*) FROM juristische_person;
SELECT COUNT(*) FROM natuerliche_person;
```

Iceberg MCP: `HIVE_DATABASE=xunternehmen`, dann `execute_query`.

## Seed-Profile

| Profil | Datei | JP | NP | Use case |
|---|---|---:|---:|---|
| `small` | `xunternehmen_seed.sql` | 1 | 4 | Ontologie-Smoke-Test |
| `medium` | `xunternehmen_seed_medium.sql` | 600 | 800 | Dev, Agent Studio, `jp-000519` / `an-001902` |
| `large` | `xunternehmen_seed_large.sql` | 3.000 | 5.000 | Volle Tier-Analytics, alle Demo-IDs |

Seed neu erzeugen:

```bash
python kdm/hive/generate_xunternehmen_seed.py --profile medium \
  --output kdm/hive/xunternehmen_seed_medium.sql --force
python kdm/hive/generate_xunternehmen_seed.py --profile large \
  --output kdm/hive/xunternehmen_seed_large.sql --force
```

## Zuordnung-Konvention

Junction-Tabellen verknüpfen Kerndatenobjekte polymorph:

```sql
-- JuristischePerson.eintragung
SELECT jp.* FROM juristische_person jp
LEFT JOIN zuordnung_eintragung ze
  ON ze.owner_id = jp.id AND ze.owner_typ = 'JuristischePerson';
```

`owner_typ`: `NatuerlichePerson`, `JuristischePerson`, `RechtsfaehigePersonengesellschaft`, `WirtschaftlicheTaetigkeit`, …

## Agent Studio

Nach Load:

```bash
python kdm/build_xunternehmen_graph.py --skip-hive
python kdm/sync_upload_config.py
```

Workflow: `HIVE_DATABASE=xunternehmen` auf iceberg-hive MCP.

## Hinweise

- DDL verwendet **Iceberg** (`STORED BY ICEBERG`) — CDW/Hive 3.x erforderlich.
- `xunternehmen_seed_large.sql` ist in `.gitignore` (generieren lokal).
- Ephemere Load-Artefakte (`.stmts/`, `.chunks/`) nicht committen.
