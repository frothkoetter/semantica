#!/usr/bin/env python3
"""Generate data/xunternehmen_mapping.ttl (R2RML) from KDM Hive schema + YAML bridge."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "xunternehmen_mapping.ttl"

NS = "https://w3id.org/kdm/"
DB = "xunternehmen"

# (table, ontology_class, datatype_columns: [(col, prop, xsd_type)])
ENTITY_MAPS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    (
        "natuerliche_person",
        "NatuerlichePerson",
        [
            ("doktorgrad", "doktorgrad", "xsd:string"),
            ("geschlecht_code", "geschlechtCode", "xsd:string"),
            ("identifikationsnummer", "identifikationsnummer", "xsd:string"),
            ("staatsangehoerigkeit_code", "staatsangehoerigkeitCode", "xsd:string"),
        ],
    ),
    (
        "name_natuerliche_person",
        "NameEinerNatuerlichenPerson",
        [
            ("vornamen", "vornamen", "xsd:string"),
            ("familienname", "familienname", "xsd:string"),
            ("geburtsname", "geburtsname", "xsd:string"),
            ("familienname_nicht_vorhanden", "familiennameNichtVorhanden", "xsd:boolean"),
            ("geburtsname_nicht_vorhanden", "geburtsnameNichtVorhanden", "xsd:boolean"),
            ("vornamen_nicht_vorhanden", "vornamenNichtVorhanden", "xsd:boolean"),
        ],
    ),
    (
        "geburt",
        "Geburt",
        [
            ("geburtsdatum", "geburtsdatum", "xsd:string"),
            ("ort_der_geburt", "ortDerGeburt", "xsd:string"),
            ("staat", "staat", "xsd:string"),
        ],
    ),
    (
        "juristische_person",
        "JuristischePerson",
        [
            ("eingetragener_name", "eingetragenerName", "xsd:string"),
            ("bundeseinheitliche_wirtschaftsnummer", "bundeseinheitlicheWirtschaftsnummer", "xsd:string"),
            ("rechtsformen_code", "rechtsformenCode", "xsd:string"),
        ],
    ),
    (
        "rechtsfaehige_personengesellschaft",
        "RechtsfaehigePersonengesellschaft",
        [
            ("eingetragener_name", "eingetragenerName", "xsd:string"),
            ("bundeseinheitliche_wirtschaftsnummer", "bundeseinheitlicheWirtschaftsnummer", "xsd:string"),
            ("rechtsformen_code", "rechtsformenCode", "xsd:string"),
        ],
    ),
    (
        "sonstige_personenvereinigung",
        "SonstigePersonenvereinigung",
        [
            ("eingetragener_name", "eingetragenerName", "xsd:string"),
            ("bundeseinheitliche_wirtschaftsnummer", "bundeseinheitlicheWirtschaftsnummer", "xsd:string"),
            ("rechtsformen_code", "rechtsformenCode", "xsd:string"),
        ],
    ),
    (
        "wirtschaftliche_taetigkeit",
        "WirtschaftlicheTaetigkeit",
        [
            ("eingetragener_name", "eingetragenerName", "xsd:string"),
            ("bundeseinheitliche_wirtschaftsnummer", "bundeseinheitlicheWirtschaftsnummer", "xsd:string"),
            ("rechtsformen_code", "rechtsformenCode", "xsd:string"),
            ("geschaeftsbezeichnung", "geschaeftsbezeichnung", "xsd:string"),
            ("taetigkeit", "taetigkeit", "xsd:string"),
        ],
    ),
    (
        "anschrift",
        "Anschrift",
        [
            ("art_anschrift_code", "artAnschriftCode", "xsd:string"),
            ("strasse", "strasse", "xsd:string"),
            ("hausnummer", "hausnummer", "xsd:string"),
            ("postleitzahl", "postleitzahl", "xsd:string"),
            ("ort", "ort", "xsd:string"),
            ("staat", "staat", "xsd:string"),
            ("postfach", "postfach", "xsd:string"),
            ("gemeindeschluessel_code", "gemeindeschluesselCode", "xsd:string"),
            ("frueherer_gemeindename", "fruehererGemeindename", "xsd:string"),
            ("wohnungsinhaber", "wohnungsinhaber", "xsd:string"),
            ("zusatzangaben_anschrift", "zusatzangabenAnschrift", "xsd:string"),
        ],
    ),
    (
        "kommunikation",
        "Kommunikation",
        [
            ("klassifikation_kommunikation_code", "klassifikationKommunikationCode", "xsd:string"),
            ("kommunikation_hinweis", "kommunikationHinweis", "xsd:string"),
            ("emailadresse", "emailadresse", "xsd:string"),
            ("telefonnummer", "telefonnummer", "xsd:string"),
            ("telefaxnummer", "telefaxnummer", "xsd:string"),
            ("demailadresse", "demailadresse", "xsd:string"),
            ("webadresse", "webadresse", "xsd:string"),
        ],
    ),
    (
        "eintragung",
        "Eintragung",
        [
            ("art_eintragung_code", "artEintragungCode", "xsd:string"),
            ("eintragungsnummer", "eintragungsnummer", "xsd:string"),
            ("registergericht_code", "registergerichtCode", "xsd:string"),
            ("registergericht_bezeichnung", "registergerichtBezeichnung", "xsd:string"),
            ("ort", "ort", "xsd:string"),
            ("staat", "staat", "xsd:string"),
            ("stiftungsverzeichnis", "stiftungsverzeichnis", "xsd:string"),
        ],
    ),
    (
        "sitz",
        "Sitz",
        [
            ("ort", "ort", "xsd:string"),
            ("staat", "staat", "xsd:string"),
        ],
    ),
    (
        "effektiver_verwaltungssitz",
        "EffektiverVerwaltungssitz",
        [
            ("ort", "ort", "xsd:string"),
            ("staat", "staat", "xsd:string"),
        ],
    ),
    (
        "betriebsstaette",
        "Betriebsstaette",
        [
            ("art_betriebsstaette_code", "artBetriebsstaetteCode", "xsd:string"),
        ],
    ),
    (
        "wirtschaftszweig",
        "Wirtschaftszweig",
        [
            ("wirtschaftszweigschluessel", "wirtschaftszweigschluessel", "xsd:string"),
            ("version_wirtschaftszweigschluessel_code", "versionWirtschaftszweigschluesselCode", "xsd:string"),
        ],
    ),
    (
        "antrag",
        "Antrag",
        [
            ("vorgangsnummer", "vorgangsnummer", "xsd:string"),
            ("eingangsdatum", "eingangsdatum", "xsd:date"),
        ],
    ),
    (
        "anzeige",
        "Anzeige",
        [
            ("vorgangsnummer", "vorgangsnummer", "xsd:string"),
            ("eingangsdatum", "eingangsdatum", "xsd:date"),
        ],
    ),
    (
        "rolle_wirtschaftlich_taetiger",
        "WirtschaftlichTaetiger",
        [],
    ),
    (
        "rolle_gesellschafter",
        "Gesellschafter",
        [
            ("art_gesellschafter_code", "artGesellschafterCode", "xsd:string"),
        ],
    ),
    (
        "rolle_gesetzlicher_vertreter",
        "GesetzlicherVertreter",
        [
            ("art_gesetzlicher_vertreter_code", "artGesetzlicherVertreterCode", "xsd:string"),
        ],
    ),
    ("rolle_beteiligter", "Beteiligter", []),
    (
        "rolle_antragsteller",
        "Antragsteller",
        [
            ("art_angabe_antragsteller_anzeigender_code", "artAngabeAntragstellerAnzeigenderCode", "xsd:string"),
        ],
    ),
    (
        "rolle_anzeigender",
        "Anzeigender",
        [
            ("art_angabe_antragsteller_anzeigender_code", "artAngabeAntragstellerAnzeigenderCode", "xsd:string"),
        ],
    ),
    ("rolle_handelnde_person", "HandelndePerson", []),
    ("rolle_ansprechpartner", "Ansprechpartner", []),
]

# Parent-side object property maps: (table, subject_class, subject_col, predicate, object_class, object_col)
PARENT_LINKS: list[tuple[str, str, str, str, str, str]] = [
    (
        "name_natuerliche_person",
        "NatuerlichePerson",
        "natuerliche_person_id",
        "nameEinerNatuerlichenPerson",
        "NameEinerNatuerlichenPerson",
        "id",
    ),
    ("geburt", "NatuerlichePerson", "natuerliche_person_id", "geburt", "Geburt", "id"),
    (
        "betriebsstaette",
        "WirtschaftlicheTaetigkeit",
        "wirtschaftliche_taetigkeit_id",
        "betriebsstaette",
        "Betriebsstaette",
        "id",
    ),
    (
        "wirtschaftszweig",
        "WirtschaftlicheTaetigkeit",
        "wirtschaftliche_taetigkeit_id",
        "wirtschaftszweig",
        "Wirtschaftszweig",
        "id",
    ),
    (
        "rolle_wirtschaftlich_taetiger",
        "WirtschaftlicheTaetigkeit",
        "wirtschaftliche_taetigkeit_id",
        "wirtschaftlichTaetiger",
        "WirtschaftlichTaetiger",
        "id",
    ),
    (
        "rolle_gesellschafter",
        "RechtsfaehigePersonengesellschaft",
        "personengesellschaft_id",
        "gesellschafter",
        "Gesellschafter",
        "id",
    ),
    (
        "rolle_beteiligter",
        "SonstigePersonenvereinigung",
        "sonstige_personenvereinigung_id",
        "beteiligter",
        "Beteiligter",
        "id",
    ),
    ("rolle_antragsteller", "Antrag", "antrag_id", "antragsteller", "Antragsteller", "id"),
    ("rolle_anzeigender", "Anzeige", "anzeige_id", "anzeigender", "Anzeigender", "id"),
]

# Role participant links (subject=role, predicate, object class from typ column)
ROLE_PARTICIPANT_LINKS: list[tuple[str, str, str, str, str]] = [
    ("rolle_beteiligter", "beteiligterID", "NatuerlichePerson", "natuerliche_person_id"),
    ("rolle_handelnde_person", "handelndePersonID", "NatuerlichePerson", "natuerliche_person_id"),
    ("rolle_ansprechpartner", "ansprechpartnerID", "NatuerlichePerson", "natuerliche_person_id"),
]

# Zuordnung junction tables: (table, predicate, target_class, target_fk_col, owner_types)
ZUORDNUNG_MAPS: list[tuple[str, str, str, str, list[str]]] = [
    (
        "zuordnung_anschrift",
        "anschrift",
        "Anschrift",
        "anschrift_id",
        [
            "NatuerlichePerson",
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "SonstigePersonenvereinigung",
            "WirtschaftlicheTaetigkeit",
            "Betriebsstaette",
        ],
    ),
    (
        "zuordnung_kommunikation",
        "kommunikation",
        "Kommunikation",
        "kommunikation_id",
        [
            "NatuerlichePerson",
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "SonstigePersonenvereinigung",
            "WirtschaftlicheTaetigkeit",
            "Betriebsstaette",
        ],
    ),
    (
        "zuordnung_eintragung",
        "eintragung",
        "Eintragung",
        "eintragung_id",
        [
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "SonstigePersonenvereinigung",
            "WirtschaftlicheTaetigkeit",
        ],
    ),
    (
        "zuordnung_sitz",
        "sitz",
        "Sitz",
        "sitz_id",
        [
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "SonstigePersonenvereinigung",
        ],
    ),
    (
        "zuordnung_effektiver_verwaltungssitz",
        "effektiverVerwaltungssitz",
        "EffektiverVerwaltungssitz",
        "effektiver_verwaltungssitz_id",
        [
            "JuristischePerson",
            "RechtsfaehigePersonengesellschaft",
            "SonstigePersonenvereinigung",
        ],
    ),
]

# Vorgang role links split by vorgang_typ
VORGANG_ROLE_MAPS: list[tuple[str, str, str, str, str, str]] = [
    ("rolle_handelnde_person", "Antrag", "antrag", "handelndePerson", "HandelndePerson", "id"),
    ("rolle_handelnde_person", "Anzeige", "anzeige", "handelndePerson", "HandelndePerson", "id"),
    ("rolle_ansprechpartner", "Antrag", "antrag", "ansprechpartner", "Ansprechpartner", "id"),
    ("rolle_ansprechpartner", "Anzeige", "anzeige", "ansprechpartner", "Ansprechpartner", "id"),
]


def _triples_map_name(table: str, suffix: str = "") -> str:
    base = "".join(part.capitalize() for part in table.split("_"))
    return f"kdm:TriplesMap_{base}{suffix}"


def _entity_triples_map(table: str, cls: str, columns: list[tuple[str, str, str]]) -> str:
    lines = [
        f"{_triples_map_name(table)} a rr:TriplesMap ;",
        f'    rr:logicalTable [ rr:tableName "{table}" ] ;',
        "    rr:subjectMap [",
        f'        rr:template "{NS}{cls}/{{id}}" ;',
        f"        rr:class kdm:{cls} ;",
        "    ] ;",
    ]
    for col, prop, dtype in columns:
        lines.append(
            "    rr:predicateObjectMap [ "
            f"rr:predicate kdm:{prop} ; "
            f'rr:objectMap [ rr:column "{col}" ; rr:datatype {dtype} ] ] ;'
        )
    if lines[-1].endswith(" ;"):
        lines[-1] = lines[-1][:-2] + " ."
    else:
        lines.append("    .")
    return "\n".join(lines)


def _parent_link_map(
    table: str,
    subject_cls: str,
    subject_col: str,
    predicate: str,
    object_cls: str,
    object_col: str,
) -> str:
    obj_template = f"{NS}{object_cls}/{{{object_col}}}"
    return "\n".join(
        [
            f"{_triples_map_name(table, '_Link')} a rr:TriplesMap ;",
            f'    rr:logicalTable [ rr:tableName "{table}" ] ;',
            "    rr:subjectMap [",
            f'        rr:template "{NS}{subject_cls}/{{{subject_col}}}" ;',
            f"        rr:class kdm:{subject_cls} ;",
            "    ] ;",
            "    rr:predicateObjectMap [",
            f"        rr:predicate kdm:{predicate} ;",
            f'        rr:objectMap [ rr:template "{obj_template}" ]',
            "    ] .",
        ]
    )


def _zuordnung_map(
    table: str,
    predicate: str,
    target_cls: str,
    target_fk: str,
    owner_typ: str,
) -> str:
    suffix = owner_typ.replace(" ", "")
    return "\n".join(
        [
            f"{_triples_map_name(table, f'_{suffix}')} a rr:TriplesMap ;",
            "    rr:logicalTable [",
            f'        rr:sqlQuery """SELECT * FROM {DB}.{table} WHERE owner_typ = \'{owner_typ}\'"""',
            "    ] ;",
            "    rr:subjectMap [",
            f'        rr:template "{NS}{owner_typ}/{{owner_id}}" ;',
            f"        rr:class kdm:{owner_typ} ;",
            "    ] ;",
            "    rr:predicateObjectMap [",
            f"        rr:predicate kdm:{predicate} ;",
            f'        rr:objectMap [ rr:template "{NS}{target_cls}/{{{target_fk}}}" ]',
            "    ] .",
        ]
    )


def _vorgang_role_map(
    table: str,
    vorgang_typ: str,
    vorgang_table: str,
    predicate: str,
    role_cls: str,
    role_id_col: str,
) -> str:
    vorgang_cls = vorgang_typ
    return "\n".join(
        [
            f"{_triples_map_name(table, f'_{vorgang_typ}')} a rr:TriplesMap ;",
            "    rr:logicalTable [",
            f"        rr:sqlQuery \"\"\"SELECT * FROM {DB}.{table} WHERE vorgang_typ = '{vorgang_typ}'\"\"\"",
            "    ] ;",
            "    rr:subjectMap [",
            f'        rr:template "{NS}{vorgang_cls}/{{vorgang_id}}" ;',
            f"        rr:class kdm:{vorgang_cls} ;",
            "    ] ;",
            "    rr:predicateObjectMap [",
            f"        rr:predicate kdm:{predicate} ;",
            f'        rr:objectMap [ rr:template "{NS}{role_cls}/{{{role_id_col}}}" ]',
            "    ] .",
        ]
    )


def _role_participant_link(table: str, role_cls: str, predicate: str, object_cls: str, object_col: str) -> str:
    return "\n".join(
        [
            f"{_triples_map_name(table, f'_{predicate}Link')} a rr:TriplesMap ;",
            f'    rr:logicalTable [ rr:tableName "{table}" ] ;',
            "    rr:subjectMap [",
            f'        rr:template "{NS}{role_cls}/{{id}}" ;',
            f"        rr:class kdm:{role_cls} ;",
            "    ] ;",
            "    rr:predicateObjectMap [",
            f"        rr:predicate kdm:{predicate} ;",
            f'        rr:objectMap [ rr:template "{NS}{object_cls}/{{{object_col}}}" ]',
            "    ] .",
        ]
    )


ROLE_CLASS_BY_TABLE = {
    "rolle_beteiligter": "Beteiligter",
    "rolle_handelnde_person": "HandelndePerson",
    "rolle_ansprechpartner": "Ansprechpartner",
}


def generate() -> str:
    sections: list[str] = [
        "# R2RML Mapping File for XUnternehmen Kerndatenmodell (KDM)",
        f"# Database: {DB} — see kdm/hive/xunternehmen_ddl.sql",
        f"# Ontology: {NS}",
        "# Generated by kdm/generate_xunternehmen_r2rml.py",
        "@prefix rr: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        f"@prefix kdm: <{NS}> .",
        "",
    ]

    sections.append("# =============================================================================")
    sections.append("# ENTITY TRIPLES MAPS")
    sections.append("# =============================================================================")
    sections.append("")

    for table, cls, columns in ENTITY_MAPS:
        sections.append(_entity_triples_map(table, cls, columns))
        sections.append("")

    sections.append("# =============================================================================")
    sections.append("# PARENT / FK OBJECT PROPERTY MAPS")
    sections.append("# =============================================================================")
    sections.append("")

    for row in PARENT_LINKS:
        sections.append(_parent_link_map(*row))
        sections.append("")

    for table, predicate, object_cls, object_col in ROLE_PARTICIPANT_LINKS:
        role_cls = ROLE_CLASS_BY_TABLE[table]
        sections.append(_role_participant_link(table, role_cls, predicate, object_cls, object_col))
        sections.append("")

    for row in VORGANG_ROLE_MAPS:
        sections.append(_vorgang_role_map(*row))
        sections.append("")

    sections.append("# =============================================================================")
    sections.append("# ZUORDNUNG (JUNCTION) MAPS — owner_typ filtered")
    sections.append("# =============================================================================")
    sections.append("")

    for table, predicate, target_cls, target_fk, owner_types in ZUORDNUNG_MAPS:
        for owner_typ in owner_types:
            sections.append(_zuordnung_map(table, predicate, target_cls, target_fk, owner_typ))
            sections.append("")

    return "\n".join(sections).rstrip() + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generate(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
