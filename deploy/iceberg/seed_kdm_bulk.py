#!/usr/bin/env python3
"""Generate and insert bulk KDM demo data into Hive/Iceberg kdm database."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

FIRST_NAMES_F = [
    "Anna", "Maria", "Sophie", "Laura", "Julia", "Katharina", "Sabine", "Petra", "Monika", "Claudia",
]
FIRST_NAMES_M = [
    "Thomas", "Michael", "Andreas", "Stefan", "Martin", "Peter", "Christian", "Daniel", "Markus", "Frank",
]
LAST_NAMES = [
    "Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann",
    "Koch", "Richter", "Klein", "Wolf", "Schroeder", "Neumann", "Schwarz", "Zimmermann", "Braun", "Krueger",
]
CITIES = [
    ("10115", "Berlin"), ("80331", "Muenchen"), ("20095", "Hamburg"), ("60311", "Frankfurt"),
    ("50667", "Koeln"), ("70173", "Stuttgart"), ("01067", "Dresden"), ("04109", "Leipzig"),
    ("28195", "Bremen"), ("45127", "Essen"), ("90402", "Nuernberg"), ("40213", "Duesseldorf"),
]
STREETS = [
    "Hauptstrasse", "Bahnhofstrasse", "Gartenweg", "Industriestrasse", "Marktplatz", "Lindenallee",
    "Rheinufer", "Schillerstrasse", "Goetheplatz", "Berliner Allee",
]
RECHTSFORMEN = ["GmbH", "AG", "UG", "GbR", "OHG", "KG", "eG"]
BRANCHEN = [
    "Softwareentwicklung", "Unternehmensberatung", "Logistik", "Maschinenbau", "Einzelhandel",
    "Gesundheitswesen", "Finanzdienstleistungen", "Immobilienverwaltung", "Energieversorgung",
]
REGISTER = [
    ("F1103", "Amtsgericht Berlin-Charlottenburg"),
    ("D2601", "Amtsgericht Muenchen"),
    ("T2101", "Amtsgericht Hamburg"),
    ("R3306", "Amtsgericht Frankfurt am Main"),
    ("R2503", "Amtsgericht Koeln"),
]


def load_mcp_env(config_path: Path) -> None:
    payload = json.loads(config_path.read_text())
    servers = payload.get("mcpServers") or {}
    hive = servers.get("iceberg-mcp-server-hive") or {}
    for key, value in (hive.get("env") or {}).items():
        os.environ.setdefault(key, str(value))


def sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sql_date(d: date) -> str:
    return f"DATE '{d.isoformat()}'"


def sql_null(value: str | None) -> str:
    return "NULL" if value is None else sql_str(value)


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def generate_dataset(
    num_persons: int,
    num_companies: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)

    persons = []
    for i in range(1, num_persons + 1):
        female = rng.random() < 0.5
        geschlecht = "w" if female else "m"
        vornamen = rng.choice(FIRST_NAMES_F if female else FIRST_NAMES_M)
        familienname = rng.choice(LAST_NAMES)
        birth = date(1955, 1, 1) + timedelta(days=rng.randint(0, 20000))
        persons.append(
            {
                "id": f"np-{i:05d}",
                "familienname": familienname,
                "vornamen": vornamen,
                "geburtsdatum": birth,
                "geschlecht_code": geschlecht,
                "staatsangehoerigkeit_code": rng.choice(["DE", "DE", "DE", "AT", "PL"]),
                "identifikationsnummer": f"ID-NP-{i:06d}",
            }
        )

    companies = []
    for i in range(1, num_companies + 1):
        base = rng.choice(LAST_NAMES)
        suffix = rng.choice(["Technik", "Service", "Holding", "Consulting", "Logistik", "Digital"])
        rf = rng.choice(RECHTSFORMEN)
        companies.append(
            {
                "id": f"jp-{i:05d}",
                "firmenname": f"{base} {suffix} {rf}",
                "rechtsform_code": rf,
                "wirtschaftsnummer": f"DE{rng.randint(100000000, 999999999)}",
            }
        )

    anschriften = []
    adr_id = 1
    for p in persons:
        plz, ort = rng.choice(CITIES)
        anschriften.append(
            {
                "id": f"adr-{adr_id:06d}",
                "juristische_person_id": None,
                "natuerliche_person_id": p["id"],
                "strasse": rng.choice(STREETS),
                "hausnummer": str(rng.randint(1, 120)),
                "postleitzahl": plz,
                "ort": ort,
                "art_anschrift_code": "strassenanschrift",
            }
        )
        adr_id += 1

    for c in companies:
        for _ in range(rng.randint(1, 2)):
            plz, ort = rng.choice(CITIES)
            anschriften.append(
                {
                    "id": f"adr-{adr_id:06d}",
                    "juristische_person_id": c["id"],
                    "natuerliche_person_id": None,
                    "strasse": rng.choice(STREETS),
                    "hausnummer": str(rng.randint(1, 200)),
                    "postleitzahl": plz,
                    "ort": ort,
                    "art_anschrift_code": rng.choice(["strassenanschrift", "postfachanschrift"]),
                }
            )
            adr_id += 1

    eintragungen = []
    for i, c in enumerate(companies, 1):
        code, name = rng.choice(REGISTER)
        eintragungen.append(
            {
                "id": f"enr-{i:05d}",
                "juristische_person_id": c["id"],
                "art_eintragung_code": "hrb",
                "registergericht_code": code,
                "registergericht_bezeichnung": name,
                "eintragungsnummer": f"HRB {rng.randint(100000, 999999)}",
            }
        )

    betriebsstaetten = []
    bs_id = 1
    for c in companies:
        n = rng.randint(1, 3)
        for j in range(n):
            betriebsstaetten.append(
                {
                    "id": f"bs-{bs_id:05d}",
                    "juristische_person_id": c["id"],
                    "art_betriebsstaette_code": rng.choice(
                        ["hauptniederlassung", "zweigniederlassung", "filiale"]
                    ),
                    "geschaeftsbezeichnung": f"{c['firmenname']} Standort {j + 1}",
                }
            )
            bs_id += 1

    kommunikationen = []
    kom_id = 1
    for p in persons:
        slug = p["familienname"].lower()
        kommunikationen.append(
            {
                "id": f"kom-{kom_id:06d}",
                "bezug_id": p["id"],
                "bezug_typ": "natuerliche_person",
                "kanal": "email",
                "wert": f"{p['vornamen'].lower()}.{slug}@example.de",
                "klassifikation_code": "privat",
            }
        )
        kom_id += 1
        if rng.random() < 0.7:
            kommunikationen.append(
                {
                    "id": f"kom-{kom_id:06d}",
                    "bezug_id": p["id"],
                    "bezug_typ": "natuerliche_person",
                    "kanal": "telefon",
                    "wert": f"+49 {rng.randint(30, 89)} {rng.randint(1000000, 9999999)}",
                    "klassifikation_code": "privat",
                }
            )
            kom_id += 1

    for c in companies:
        slug = c["firmenname"].lower().replace(" ", "-")[:30]
        for kanal, klass in [("email", "geschaeftlich"), ("web", "geschaeftlich"), ("telefon", "geschaeftlich")]:
            if kanal == "email":
                wert = f"kontakt@{slug}.de"
            elif kanal == "web":
                wert = f"https://www.{slug}.de"
            else:
                wert = f"+49 {rng.randint(30, 89)} {rng.randint(100000, 9999999)}"
            kommunikationen.append(
                {
                    "id": f"kom-{kom_id:06d}",
                    "bezug_id": c["id"],
                    "bezug_typ": "juristische_person",
                    "kanal": kanal,
                    "wert": wert,
                    "klassifikation_code": klass,
                }
            )
            kom_id += 1

    gesellschafter = []
    gs_id = 1
    for c in companies:
        n = rng.randint(1, 4)
        for _ in range(n):
            if rng.random() < 0.75:
                person = rng.choice(persons)
                gesellschafter.append(
                    {
                        "id": f"gs-{gs_id:05d}",
                        "personengesellschaft_id": c["id"],
                        "gesellschafter_person_id": person["id"],
                        "gesellschafter_unternehmen_id": None,
                        "art_gesellschafter_code": "natuerliche_person",
                    }
                )
            else:
                other = rng.choice([x for x in companies if x["id"] != c["id"]])
                gesellschafter.append(
                    {
                        "id": f"gs-{gs_id:05d}",
                        "personengesellschaft_id": c["id"],
                        "gesellschafter_person_id": None,
                        "gesellschafter_unternehmen_id": other["id"],
                        "art_gesellschafter_code": "juristische_person",
                    }
                )
            gs_id += 1

    taetigkeiten = []
    wt_id = 1
    for c in companies:
        n = rng.randint(1, 2)
        for _ in range(n):
            branche = rng.choice(BRANCHEN)
            taetigkeiten.append(
                {
                    "id": f"wt-{wt_id:05d}",
                    "wirtschaftlich_taetiger_id": c["id"],
                    "taetigkeit": branche,
                    "geschaeftsbezeichnung": f"{c['firmenname']} — {branche}",
                }
            )
            wt_id += 1

    return {
        "natuerliche_person": persons,
        "juristische_person": companies,
        "anschrift": anschriften,
        "eintragung": eintragungen,
        "betriebsstaette": betriebsstaetten,
        "kommunikation": kommunikationen,
        "gesellschafter": gesellschafter,
        "wirtschaftliche_taetigkeit": taetigkeiten,
    }


def build_insert_batches(table: str, rows: list[dict], batch_size: int) -> list[str]:
    statements: list[str] = []
    if not rows:
        return statements

    if table == "natuerliche_person":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['familienname'])}, {sql_str(r['vornamen'])}, "
                f"{sql_date(r['geburtsdatum'])}, {sql_str(r['geschlecht_code'])}, "
                f"{sql_str(r['staatsangehoerigkeit_code'])}, {sql_str(r['identifikationsnummer'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.natuerliche_person VALUES\n{values}")

    elif table == "juristische_person":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['firmenname'])}, {sql_str(r['rechtsform_code'])}, "
                f"{sql_str(r['wirtschaftsnummer'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.juristische_person VALUES\n{values}")

    elif table == "anschrift":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_null(r['juristische_person_id'])}, "
                f"{sql_null(r['natuerliche_person_id'])}, {sql_str(r['strasse'])}, "
                f"{sql_str(r['hausnummer'])}, {sql_str(r['postleitzahl'])}, {sql_str(r['ort'])}, "
                f"{sql_str(r['art_anschrift_code'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.anschrift VALUES\n{values}")

    elif table == "eintragung":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['juristische_person_id'])}, "
                f"{sql_str(r['art_eintragung_code'])}, {sql_str(r['registergericht_code'])}, "
                f"{sql_str(r['registergericht_bezeichnung'])}, {sql_str(r['eintragungsnummer'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.eintragung VALUES\n{values}")

    elif table == "betriebsstaette":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['juristische_person_id'])}, "
                f"{sql_str(r['art_betriebsstaette_code'])}, {sql_str(r['geschaeftsbezeichnung'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.betriebsstaette VALUES\n{values}")

    elif table == "kommunikation":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['bezug_id'])}, {sql_str(r['bezug_typ'])}, "
                f"{sql_str(r['kanal'])}, {sql_str(r['wert'])}, {sql_str(r['klassifikation_code'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.kommunikation VALUES\n{values}")

    elif table == "gesellschafter":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['personengesellschaft_id'])}, "
                f"{sql_null(r['gesellschafter_person_id'])}, "
                f"{sql_null(r['gesellschafter_unternehmen_id'])}, "
                f"{sql_str(r['art_gesellschafter_code'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.gesellschafter VALUES\n{values}")

    elif table == "wirtschaftliche_taetigkeit":
        for batch in chunked(rows, batch_size):
            values = ",\n".join(
                f"({sql_str(r['id'])}, {sql_str(r['wirtschaftlich_taetiger_id'])}, "
                f"{sql_str(r['taetigkeit'])}, {sql_str(r['geschaeftsbezeichnung'])})"
                for r in batch
            )
            statements.append(f"INSERT INTO kdm.wirtschaftliche_taetigkeit VALUES\n{values}")

    return statements


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk seed KDM Iceberg tables")
    parser.add_argument("--persons", type=int, default=500, help="Number of natural persons")
    parser.add_argument("--companies", type=int, default=200, help="Number of legal entities")
    parser.add_argument("--batch-size", type=int, default=25, help="Rows per INSERT statement")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--mcp-config",
        type=Path,
        default=Path.home() / ".cursor" / "mcp.json",
    )
    args = parser.parse_args()

    if args.mcp_config.is_file():
        load_mcp_env(args.mcp_config)

    try:
        from iceberg_mcp_server.tools import hive_tools
    except ImportError:
        print("Run from iceberg-mcp-server-hive: uv run python seed_kdm_bulk.py", file=sys.stderr)
        return 1

    data = generate_dataset(args.persons, args.companies, args.seed)
    totals = {k: len(v) for k, v in data.items()}
    print("Generated rows:", json.dumps(totals, indent=2))

    order = [
        "natuerliche_person",
        "juristische_person",
        "anschrift",
        "eintragung",
        "betriebsstaette",
        "kommunikation",
        "gesellschafter",
        "wirtschaftliche_taetigkeit",
    ]

    for table in order:
        rows = data[table]
        statements = build_insert_batches(table, rows, args.batch_size)
        print(f"\nInserting {len(rows)} rows into kdm.{table} ({len(statements)} batches)...")
        for idx, stmt in enumerate(statements, 1):
            result = hive_tools.execute_sql(stmt)
            if result.startswith("Error:"):
                print(f"  FAIL batch {idx}/{len(statements)}: {result[:500]}", file=sys.stderr)
                return 1
            if idx % 5 == 0 or idx == len(statements):
                print(f"  batch {idx}/{len(statements)} OK")

    print("\nVerifying row counts...")
    for table in order:
        result = hive_tools.execute_query(f"SELECT COUNT(*) AS cnt FROM kdm.{table}")
        print(f"  {table}: {result}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
