# KDM Entity-Relationship Model

XUnternehmen.Kerndatenmodell (KDM) v1.2 — `https://w3id.org/kdm/`

This document describes two layers:

1. **Conceptual ERM** — official KDM ontology (OWL classes & object properties)
2. **Physical ERM** — Iceberg/Hive implementation in database `kdm` (8 tables)

Semantica maps physical → conceptual via `config/kdm_db_mapping.yaml`.

---

## 1. Conceptual ERM (KDM Ontologie)

### 1.1 Kern-Entitäten (Agenten)

```mermaid
erDiagram
    NatuerlichePerson ||--o{ Geburt : "hat Geburt"
    NatuerlichePerson ||--o{ NameEinerNatuerlichenPerson : "hat Name"
    NatuerlichePerson ||--o{ Anschrift : "hat Anschrift"
    NatuerlichePerson ||--o{ Kommunikation : "hat Kommunikation"

    JuristischePerson ||--o{ Anschrift : "hat Anschrift"
    JuristischePerson ||--o{ Eintragung : "hat Eintragung"
    JuristischePerson ||--o{ Sitz : "hat Sitz"
    JuristischePerson ||--o{ Kommunikation : "hat Kommunikation"
    JuristischePerson ||--o{ EffektiverVerwaltungssitz : "hat eff. Verwaltungssitz"

    RechtsfaehigePersonengesellschaft ||--o{ Gesellschafter : "hat Gesellschafter"
    Personengesellschaft ||--o{ Gesellschafter : "hat Gesellschafter"

    WirtschaftlicheTaetigkeit ||--o{ Betriebsstaette : "hat Betriebsstaette"
    WirtschaftlicheTaetigkeit ||--o{ Wirtschaftszweig : "hat Wirtschaftszweig"
    WirtschaftlichTaetiger ||--o{ WirtschaftlicheTaetigkeit : "ist"

    NatuerlichePerson {
        string familienname
        string vornamen
        date geburtsdatum
        code geschlechtCode
        code staatsangehoerigkeitCode
        string identifikationsnummer
    }

    JuristischePerson {
        string eingetragenerName
        code rechtsformenCode
        string bundeseinheitlicheWirtschaftsnummer
    }

    Anschrift {
        string strasse
        string hausnummer
        string postleitzahl
        string ort
        code artAnschriftCode
    }

    Eintragung {
        code artEintragungCode
        code registergerichtCode
        string registergerichtBezeichnung
        string eintragungsnummer
    }

    Betriebsstaette {
        code artBetriebsstaetteCode
        string geschaeftsbezeichnung
    }

    Kommunikation {
        code klassifikationKommunikationCode
    }

    Gesellschafter {
        code artGesellschafterCode
    }

    WirtschaftlicheTaetigkeit {
        string taetigkeit
        string geschaeftsbezeichnung
    }
```

### 1.2 Vererbung (Auszug)

```mermaid
flowchart TB
    Agent["Agent (CCO)"]
    NP["NatuerlichePerson"]
    JP["JuristischePerson"]
    RPG["RechtsfaehigePersonengesellschaft"]
    SPV["SonstigePersonenvereinigung"]

    Agent --> NP
    Agent --> JP
    Agent --> RPG
    Agent --> SPV

    Anschrift["Anschrift"]
    AInland["AnschriftInland"]
    AStr["AnschriftInlandStrassenanschrift"]
    APf["AnschriftInlandPostfachanschrift"]
    AAus["AnschriftAusland"]

    Anschrift --> AInland
    Anschrift --> AAus
    AInland --> AStr
    AInland --> APf

    Kommunikation["Kommunikation"]
    Email["Email"]
    Telefon["Telefon"]
    Telefax["Telefax"]
    Demail["Demail"]
    Web["WebAdresse"]

    Kommunikation --> Email
    Kommunikation --> Telefon
    Kommunikation --> Telefax
    Kommunikation --> Demail
    Kommunikation --> Web
```

### 1.3 Rollen-Muster (KDM)

KDM modelliert Beteiligungen und Rollen als **eigenständige Klassen** mit Verweis auf die tragende Person:

| Rolle (Klasse) | Object Property | Träger (Range) |
|---|---|---|
| `Gesellschafter` | `gesellschafterID` | `NatuerlichePerson` \| `JuristischePerson` \| `RechtsfaehigePersonengesellschaft` |
| `GesetzlicherVertreter` | `gesetzlicherVertreterID` | `NatuerlichePerson` \| `JuristischePerson` |
| `Ansprechpartner` | `ansprechpartnerID` | `NatuerlichePerson` |
| `Antragsteller` | `antragstellerID` | Agent-Union |
| `HandelndePerson` | `handelndePersonID` | Agent-Union |
| `WirtschaftlichTaetiger` | — | `JuristischePerson` \| … |

```mermaid
erDiagram
    Personengesellschaft ||--|{ Gesellschafter : "hat Gesellschafter"
    Gesellschafter }o--|| NatuerlichePerson : "Gesellschafter ist"
    Gesellschafter }o--o| JuristischePerson : "Gesellschafter ist"

    JuristischePerson ||--o{ GesetzlicherVertreter : "hat gesetzl. Vertreter"
    GesetzlicherVertreter }o--|| NatuerlichePerson : "Vertreter ist"
```

---

## 2. Physical ERM (Iceberg `kdm` — implementiert)

Vereinfachtes relationales Schema für Demo/Analytics. PK = `id` (STRING).

```mermaid
erDiagram
    natuerliche_person ||--o{ anschrift : "natuerliche_person_id"
    juristische_person ||--o{ anschrift : "juristische_person_id"
    juristische_person ||--o{ eintragung : "juristische_person_id"
    juristische_person ||--o{ betriebsstaette : "juristische_person_id"
    juristische_person ||--o{ wirtschaftliche_taetigkeit : "wirtschaftlich_taetiger_id"
    juristische_person ||--o{ gesellschafter : "personengesellschaft_id"
    natuerliche_person ||--o{ gesellschafter : "gesellschafter_person_id"
    juristische_person ||--o{ gesellschafter : "gesellschafter_unternehmen_id"

    natuerliche_person ||--o{ kommunikation : "bezug_id (typ=np)"
    juristische_person ||--o{ kommunikation : "bezug_id (typ=jp)"

    natuerliche_person {
        string id PK
        string familienname
        string vornamen
        date geburtsdatum
        string geschlecht_code
        string staatsangehoerigkeit_code
        string identifikationsnummer
    }

    juristische_person {
        string id PK
        string firmenname
        string rechtsform_code
        string wirtschaftsnummer
    }

    anschrift {
        string id PK
        string juristische_person_id FK
        string natuerliche_person_id FK
        string strasse
        string hausnummer
        string postleitzahl
        string ort
        string art_anschrift_code
    }

    eintragung {
        string id PK
        string juristische_person_id FK
        string art_eintragung_code
        string registergericht_code
        string registergericht_bezeichnung
        string eintragungsnummer
    }

    betriebsstaette {
        string id PK
        string juristische_person_id FK
        string art_betriebsstaette_code
        string geschaeftsbezeichnung
    }

    kommunikation {
        string id PK
        string bezug_id FK
        string bezug_typ
        string kanal
        string wert
        string klassifikation_code
    }

    gesellschafter {
        string id PK
        string personengesellschaft_id FK
        string gesellschafter_person_id FK
        string gesellschafter_unternehmen_id FK
        string art_gesellschafter_code
    }

    wirtschaftliche_taetigkeit {
        string id PK
        string wirtschaftlich_taetiger_id FK
        string taetigkeit
        string geschaeftsbezeichnung
    }
```

### Kardinalitäten (Physical)

| Beziehung | Kardinalität | Hinweis |
|---|---|---|
| Person → Anschrift | 1:N | XOR: NP **oder** JP pro Zeile |
| JP → Eintragung | 1:N | HRB/HRA-Einträge |
| JP → Betriebsstätte | 1:N | Standorte |
| JP → Wirtschaftliche Tätigkeit | 1:N | Branchen |
| Personengesellschaft → Gesellschafter | 1:N | NP oder JP als Beteiligter |
| Agent → Kommunikation | 1:N | Polymorph via `bezug_typ` |

---

## 3. Mapping Conceptual ↔ Physical

| Physical (Tabelle) | KDM-Klasse | URI |
|---|---|---|
| `natuerliche_person` | `NatuerlichePerson` | `https://w3id.org/kdm/NatuerlichePerson` |
| `juristische_person` | `JuristischePerson` | `https://w3id.org/kdm/JuristischePerson` |
| `anschrift` | `Anschrift` | `https://w3id.org/kdm/Anschrift` |
| `eintragung` | `Eintragung` | `https://w3id.org/kdm/Eintragung` |
| `betriebsstaette` | `Betriebsstaette` | `https://w3id.org/kdm/Betriebsstaette` |
| `kommunikation` | `Kommunikation` | `https://w3id.org/kdm/Kommunikation` |
| `gesellschafter` | `Gesellschafter` | `https://w3id.org/kdm/Gesellschafter` |
| `wirtschaftliche_taetigkeit` | `WirtschaftlicheTaetigkeit` | `https://w3id.org/kdm/WirtschaftlicheTaetigkeit` |

### Abweichungen Physical vs. vollständiges KDM

| KDM-Konzept | Status in `kdm` DB |
|---|---|
| `Geburt`, `NameEinerNatuerlichenPerson` | In NP-Tabelle denormalisiert (`geburtsdatum`, `vornamen`/`familienname`) |
| `Email`, `Telefon`, `WebAdresse` | In `kommunikation.kanal` + `wert` vereinheitlicht |
| `Personengesellschaft` | Implizit über `juristische_person` + `gesellschafter` |
| `GesetzlicherVertreter`, `Ansprechpartner`, `Antrag` | Nicht implementiert (nur Ontologie) |
| `Sitz`, `EffektiverVerwaltungssitz` | Nicht als eigene Tabelle |
| `Wirtschaftszweig` | In `wirtschaftliche_taetigkeit.taetigkeit` |

---

## 4. Gesamtarchitektur (Semantica + Iceberg)

```mermaid
flowchart LR
    subgraph Ontology["KDM Ontologie (OWL)"]
        OC[36 Klassen]
        OP[76 Properties]
    end

    subgraph Physical["Iceberg kdm"]
        T8[8 Tabellen]
        D9k[~9000 Zeilen]
    end

    subgraph Semantica["Semantica Graph"]
        MAP[mapsToClass / mapsToProperty]
        KG[kdm_graph.json]
    end

    Ontology --> MAP
    T8 --> MAP
    MAP --> KG
    T8 --> D9k
```

- **Iceberg MCP** — SQL auf Physical ERM (Fakten)
- **Semantica MCP** — Ontologie + Mapping (Bedeutung)
- **Gemeinsam** — KDM als semantische Schicht über dem Data Lake

---

## 5. Architektur & MCP-Grenzen

Wie Ontologie, Mapping, Graph und Physical zusammenpassen — und welcher MCP welche Rolle in der Analyse übernimmt.

### 5.1 Die vier Schichten

```mermaid
flowchart TB
    subgraph L1["1. Ontologie (konzeptionell)"]
        OWL["kdm_ontology.ttl<br/>36 Klassen, 76 Properties"]
    end

    subgraph L2["2. Physical (operational)"]
        ICE["Iceberg/Hive kdm.*<br/>8 Tabellen, Instanzdaten"]
    end

    subgraph L3["3. Mapping (Übersetzung)"]
        YAML["kdm_db_mapping.yaml"]
    end

    subgraph L4["4. Graph (Semantica)"]
        KG["kdm_graph.json<br/>Metamodell"]
    end

    OWL -->|"import_kdm_ontology"| KG
    ICE -->|"introspect schema"| YAML
    YAML -->|"map_iceberg_schema_to_ontology"| KG
    ICE -.->|"kein Auto-Sync"| KG
```

| Schicht | Artefakt | Inhalt | Ändert sich wenn … |
|---|---|---|---|
| **Ontologie** | `data/kdm_ontology.ttl` | XÖV-KDM-Bedeutung: Klassen, Properties, Rollen | KDM-Release aktualisiert wird |
| **Physical** | `kdm.*` in Hive | Instanzen: Personen, Firmen, Adressen, Beteiligungen | ETL, Bulk-Seed, SQL INSERT |
| **Mapping** | `config/kdm_db_mapping.yaml` | Brücke: Tabelle/Spalte → KDM-URI | YAML editiert wird |
| **Graph** | `data/kdm_graph.json` | Metamodell: Ontologie + Schema-Mappings | `import_*` / `map_*` ausgeführt wird |

### 5.2 Verknüpfung der Schichten

**Ontologie → Graph** (`import_kdm_ontology`)

- Materialisiert `OntologyClass`- und Property-Knoten mit `subClassOf`, `definedIn`, `domain`, `range`
- Enthält **keine** Firmen- oder Personeninstanzen

**Physical → Mapping → Graph** (`map_iceberg_schema_to_ontology`)

1. Hive-Introspection (`SHOW TABLES`, `DESCRIBE`)
2. Heuristik (Tabellenname ≈ Klassenname) + explizite YAML-Regeln
3. Optional `apply_mappings: true` → Graph-Knoten

Beispielpfad im Graph (Schema-Ebene, 2–3 Hops):

```
db:table:gesellschafter  --mapsToClass-->   kdm:Gesellschafter
db:table:gesellschafter  --hasColumn-->    db:column:gesellschafter.personengesellschaft_id
kdm:Anschrift            --references-->   kdm:JuristischePerson   (FK-Inferenz)
```

**Physical → Instanzen** (bleiben in Iceberg)

- Zeilen wie `np-00013` (Peter Meyer) existieren **nur** in `kdm.natuerliche_person`
- Es gibt **keinen automatischen Pfad** Graph-Knoten → Iceberg-Zeile
- Verbindung läuft indirekt: Graph erklärt Semantik → SQL nutzt Spaltennamen/FKs

### 5.3 MCP-Verantwortlichkeiten

#### `iceberg-mcp-server-hive` — Fakten & Instanzen

| Tool | Funktion |
|---|---|
| `execute_query` | SQL: JOINs, Filter (z. B. PLZ `80%`), Aggregationen (Hub ≥ 3 Firmen) |
| `get_schema` | Tabellennamen in `kdm` |
| `list_databases` | Datenbank-Übersicht |
| `list_iceberg_snapshots` | Iceberg-Versionierung |

**Stärke:** Beliebig tiefe relationale Pfade — JOIN-Tiefe nur durch die SQL-Query begrenzt.

**Grenze:** Kein KDM-Vokabular, nur Spalten- und Tabellennamen.

#### `semantica` MCP — Bedeutung & Metamodell

| Tool | Funktion |
|---|---|
| `import_kdm_ontology` | KDM-Ontologie in den Graph laden |
| `map_iceberg_schema_to_ontology` | One-Shot: Hive-Schema + KDM + Mapping |
| `map_db_schema_to_ontology` | Mapping mit vorgegebenem `schema_info` |
| `get_hive_schema_info` | Schema-Introspection (impyla, `HIVE_*`) |
| `get_graph_summary` | Knoten-/Decision-Count |
| `get_graph_analytics` | PageRank, Community Detection auf dem Graph |
| `export_graph` | Turtle / JSON-LD des Metamodells |
| `extract_entities` / `extract_relations` | Text → Entities (nicht Iceberg-Daten) |
| `get_causal_chain` | Kausalketten bei Decisions (`max_depth` default 5) |

**Stärke:** Erklärt, *warum* eine Spalte semantisch zu welcher KDM-Klasse/Property gehört.

**Grenze:** Graph enthält **keine** Instanzdaten aus Iceberg.

### 5.4 Kombinierter Analyse-Ablauf

```mermaid
sequenceDiagram
    participant Chat
    participant Sem as semantica MCP
    participant Ice as iceberg MCP
    participant KG as kdm_graph.json
    participant DB as kdm Iceberg

    Note over Sem,KG: Einmalig / bei Schema-Änderung
    Chat->>Sem: import_kdm_ontology()
    Sem->>KG: Klassen + Properties
    Chat->>Sem: map_iceberg_schema_to_ontology(kdm)
    Sem->>DB: SHOW TABLES / DESCRIBE
    Sem->>KG: mapsToClass / mapsToProperty

    Note over Chat,DB: Jede Inhalts-Analyse
    Chat->>Ice: SELECT ... JOIN gesellschafter ...
    Ice->>DB: SQL
    DB-->>Ice: Zeilen
    Ice-->>Chat: Fakten
    Chat->>Sem: optional get_graph_analytics()
    Sem->>KG: PageRank / Communities
    Sem-->>Chat: Metamodell-Struktur
```

| Schritt | MCP | Suchtiefe |
|---|---|---|
| KDM-Klassen laden | Semantica | 1× Ontologie-Import |
| Schema → KDM | Semantica | 1 Hop pro Tabelle/Spalte (flach) |
| Hub / Filter auf Inhalten | Iceberg | SQL-JOINs (praktisch unbegrenzt) |
| Ergebnis in KDM erklären | Semantica + Chat | 1–3 Hops im Metamodell-Graph |
| Struktur-Metriken | Semantica | Gesamtgraph (~153 Knoten) |

### 5.5 Grenzen im Detail

#### Graph-Tiefe vs. SQL-Tiefe

| Aspekt | Semantica-Graph | Iceberg-SQL |
|---|---|---|
| Durchsuchtes Material | Ontologie + Schema-Mappings | Instanzdaten |
| Typische Pfadlänge | 1–3 Hops (`table → class → subClassOf`) | 2–6 JOINs in Netzwerk-Analysen |
| Explizites Hop-Limit | Kein MCP-Tool für `get_neighbors(hops=N)` | Kein Limit (außer Query-Komplexität) |
| Global Analytics | PageRank / Louvain über alle Graph-Knoten | — |
| Kausalketten | `get_causal_chain`: default **5**, max **100** — nur für **Decisions** | — |

`ContextGraph.get_neighbors(hops=…)` existiert im Python-API, ist aber **nicht als MCP-Tool exponiert**.

#### Was im Graph ist — und was nicht

| Im Graph (`kdm_graph.json`) | Nicht im Graph |
|---|---|
| 36 `OntologyClass` | Personen-/Firmenzeilen |
| 76 Properties | PLZ-Filterergebnisse |
| 8 `DatabaseTable` | Co-Gesellschafter-Netzwerk als Instanzen |
| 14 `DatabaseColumn` | SQL-Query-Ergebnisse |
| Mapping-Kanten | — |

**Needle-in-haystack auf Inhalten** → Iceberg.  
**Needle semantisch einordnen** → Semantica.

#### Mapping-Abdeckung (Stand Demo)

| Metrik | Wert |
|---|---|
| Tabellen gemappt | 8 / 8 (explizit) |
| Spalten im Graph (`mapsToProperty`) | 14 / 44 |
| Spalten mit Namens-Hinweis (Heuristik) | 27 / 44 |
| FK → Ontologie-Klasse | 4 Kanten |

Nicht als eigene Physical-Tabellen: `GesetzlicherVertreter`, `Antrag`, `Sitz`, `Geburt` (nur Ontologie).

#### Persistenz & Sync

| Thema | Verhalten |
|---|---|
| Graph laden | `SEMANTICA_KG_PATH` beim MCP-Start (`load_from_file`) |
| Graph speichern | Nicht automatisch nach Tool-Calls — `export_graph` oder `save_to_file` |
| Iceberg → Graph | **Kein Auto-Sync** — neue Zeilen ändern den Graph nicht |
| Schema-Änderung | `map_iceberg_schema_to_ontology` erneut ausführen |
| Ontologie-Update | `import_kdm_ontology` erneut ausführen |

#### Bekannte technische Hinweise

- `get_graph_analytics()` / PageRank kann mit `ContextGraph` fehlschlagen — Workaround: Analytics auf exportiertem JSON (NetworkX)
- `import_kdm_ontology` per URL: SSL-Probleme möglich → lokale `data/kdm_ontology.ttl` verwenden
- MCP ohne geladenen Graph: `get_graph_summary` zeigt 0 Knoten trotz vorhandener `kdm_graph.json` → MCP neu starten, `SEMANTICA_KG_PATH` prüfen

### 5.6 Merksatz

```
Physical (Iceberg)  = WAS ist in den Daten?         → iceberg-mcp, SQL
Ontologie (OWL)     = WAS bedeutet es (XÖV/KDM)?    → semantica, import_kdm_ontology
Mapping (YAML)      = WIE heißt Physical in KDM?   → semantica, map_*_to_ontology
Graph (JSON)        = Metamodell (Schema + Ontologie) → semantica, Analytics (~153 Knoten)
```

Volle KDM-Analyse = **Iceberg für Instanzen** + **Semantica für Semantik** + Agent, der beides verbindet.

---

## Referenzen

- Ontologie: `data/kdm_ontology.ttl` (oder https://w3id.org/kdm/)
- DDL: `deploy/iceberg/kdm_ddl.sql`
- Mapping: `config/kdm_db_mapping.yaml`
- Graph: `data/kdm_graph.json`
