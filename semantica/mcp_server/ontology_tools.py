"""
MCP ontology tools — import OWL/RDF ontologies into ContextGraph and map DB schemas.

Used by semantica-mcp and the repo-root mcp/ package.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

log = logging.getLogger("semantica.mcp.ontology")

_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _normalize_token(value: str) -> str:
    """Lowercase identifier token for fuzzy name matching."""
    token = value.translate(_UMLAUT_MAP).lower()
    token = re.sub(r"[^a-z0-9]+", "", token)
    return token


def _local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _download_ontology(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    suffix = os.path.splitext(parsed.path)[1] or ".ttl"
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="semantica-ontology-")
    os.close(fd)
    try:
        urllib.request.urlretrieve(url, path)
        return path
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise


def _resolve_ontology_path(file_path: Optional[str], url: Optional[str]) -> Tuple[str, bool]:
    """Return (local_path, is_temp)."""
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Ontology file not found: {file_path}")
        return file_path, False
    if url:
        return _download_ontology(url), True
    raise ValueError("Either file_path or url is required")


def _ingest_ontology_file(path: str) -> Dict[str, Any]:
    from semantica.ingest import OntologyIngestor

    return OntologyIngestor().ingest_ontology(path).data


def materialize_ontology_to_graph(
    graph: Any,
    ontology: Dict[str, Any],
    *,
    include_properties: bool = True,
    namespace_filter: Optional[str] = None,
) -> Dict[str, int]:
    """
    Add ontology classes (and optionally properties) from an OntologyIngestor dict
    into a ContextGraph.

    Creates:
      - one Ontology root node
      - OntologyClass nodes for each class
      - subClassOf edges for rdfs:subClassOf parents
      - OntologyProperty nodes + domain/range edges when include_properties=True
    """
    stats = {
        "ontology_nodes": 0,
        "class_nodes": 0,
        "property_nodes": 0,
        "hierarchy_edges": 0,
        "property_edges": 0,
        "skipped": 0,
    }

    ontology_uri = ontology.get("uri") or "urn:semantica:ontology:imported"
    ontology_id = ontology_uri

    graph.add_node(
        ontology_id,
        node_type="Ontology",
        content=ontology.get("name") or _local_name(ontology_uri),
        uri=ontology_uri,
        version=ontology.get("version"),
        description=ontology.get("description"),
        source="ontology_import",
    )
    stats["ontology_nodes"] = 1

    class_uris: Set[str] = set()

    for cls in ontology.get("classes", []):
        uri = cls.get("uri")
        if not uri:
            stats["skipped"] += 1
            continue
        if namespace_filter and not str(uri).startswith(namespace_filter):
            stats["skipped"] += 1
            continue

        label = cls.get("label") or cls.get("name") or _local_name(uri)
        graph.add_node(
            uri,
            node_type="OntologyClass",
            content=label,
            uri=uri,
            label=label,
            ontology_uri=ontology_uri,
            description=cls.get("description"),
            parents=cls.get("parents", []),
            source="ontology_import",
        )
        class_uris.add(uri)
        stats["class_nodes"] += 1

        graph.add_edge(uri, ontology_id, edge_type="definedIn", source="ontology_import")

        for parent_uri in cls.get("parents", []):
            if not parent_uri:
                continue
            graph.add_edge(uri, parent_uri, edge_type="subClassOf", source="ontology_import")
            stats["hierarchy_edges"] += 1

    if not include_properties:
        return stats

    for prop in ontology.get("properties", []):
        uri = prop.get("uri")
        if not uri:
            stats["skipped"] += 1
            continue
        if namespace_filter and not str(uri).startswith(namespace_filter):
            stats["skipped"] += 1
            continue

        prop_kind = prop.get("type", "property")
        node_type = "OntologyProperty"
        if prop_kind == "object":
            node_type = "ObjectProperty"
        elif prop_kind == "data":
            node_type = "DatatypeProperty"

        label = prop.get("label") or prop.get("name") or _local_name(uri)
        graph.add_node(
            uri,
            node_type=node_type,
            content=label,
            uri=uri,
            label=label,
            ontology_uri=ontology_uri,
            property_kind=prop_kind,
            description=prop.get("description"),
            domain=prop.get("domain"),
            range=prop.get("range"),
            source="ontology_import",
        )
        stats["property_nodes"] += 1
        graph.add_edge(uri, ontology_id, edge_type="definedIn", source="ontology_import")

        domain = prop.get("domain")
        if domain:
            graph.add_edge(uri, domain, edge_type="domain", source="ontology_import")
            stats["property_edges"] += 1

        range_uri = prop.get("range")
        if range_uri:
            graph.add_edge(uri, range_uri, edge_type="range", source="ontology_import")
            stats["property_edges"] += 1

    return stats


def _collect_ontology_classes_from_graph(graph: Any) -> List[Dict[str, Any]]:
    classes: List[Dict[str, Any]] = []
    for node in graph.find_nodes(node_type="OntologyClass"):
        uri = node.get("uri") or node.get("id")
        label = node.get("label") or node.get("content") or _local_name(str(uri))
        classes.append(
            {
                "uri": uri,
                "label": label,
                "normalized": _normalize_token(label) + _normalize_token(_local_name(str(uri))),
            }
        )
    return classes


def _best_class_match(
    name: str, classes: List[Dict[str, Any]]
) -> Optional[Tuple[Dict[str, Any], float]]:
    token = _normalize_token(name)
    if not token:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for cls in classes:
        uri_token = _normalize_token(_local_name(str(cls["uri"])))
        label_token = _normalize_token(str(cls["label"]))
        score = 0.0
        if token == uri_token or token == label_token:
            score = 1.0
        elif token in uri_token or uri_token in token:
            score = 0.85
        elif token in label_token or label_token in token:
            score = 0.75
        if score > best_score:
            best_score = score
            best = cls
    if best is None or best_score < 0.75:
        return None
    return best, best_score


def suggest_db_schema_mappings(
    schema_info: Dict[str, Any],
    ontology_classes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Heuristic table/column → ontology class/property mapping suggestions."""
    table_mappings: List[Dict[str, Any]] = []
    column_mappings: List[Dict[str, Any]] = []
    fk_mappings: List[Dict[str, Any]] = []

    table_to_class: Dict[str, Dict[str, Any]] = {}

    for table in schema_info.get("tables", []):
        table_name = table.get("name", "")
        match = _best_class_match(table_name, ontology_classes)
        entry = {
            "table": table_name,
            "suggested_class_uri": None,
            "suggested_class_label": None,
            "confidence": 0.0,
            "status": "unmapped",
        }
        if match:
            cls, score = match
            entry.update(
                {
                    "suggested_class_uri": cls["uri"],
                    "suggested_class_label": cls["label"],
                    "confidence": round(score, 2),
                    "status": "suggested",
                }
            )
            table_to_class[table_name] = cls
        table_mappings.append(entry)

        mapped_class = table_to_class.get(table_name)
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            col_entry = {
                "table": table_name,
                "column": col_name,
                "sql_type": col.get("type"),
                "suggested_property_uri": None,
                "suggested_property_label": None,
                "confidence": 0.0,
                "status": "unmapped",
            }
            if mapped_class:
                prop_match = _best_class_match(col_name, ontology_classes)
                if prop_match:
                    _, score = prop_match
                    col_entry.update(
                        {
                            "suggested_property_label": col_name,
                            "confidence": round(min(score, 0.7), 2),
                            "status": "column_name_hint",
                        }
                    )
            column_mappings.append(col_entry)

    for fk in schema_info.get("foreign_keys", []):
        src_table = fk.get("constrained_table") or fk.get("table_name") or ""
        tgt_table = fk.get("referred_table") or fk.get("referred_schema") or ""
        if not src_table or not tgt_table:
            continue
        src_cls = table_to_class.get(src_table)
        tgt_cls = table_to_class.get(tgt_table)
        fk_mappings.append(
            {
                "source_table": src_table,
                "target_table": tgt_table,
                "source_class_uri": src_cls["uri"] if src_cls else None,
                "target_class_uri": tgt_cls["uri"] if tgt_cls else None,
                "suggested_edge_type": "references",
                "status": "suggested" if src_cls and tgt_cls else "unmapped",
            }
        )

    mapped_tables = sum(1 for m in table_mappings if m["status"] == "suggested")
    return {
        "table_mappings": table_mappings,
        "column_mappings": column_mappings,
        "foreign_key_mappings": fk_mappings,
        "summary": {
            "tables": len(table_mappings),
            "tables_mapped": mapped_tables,
            "columns": len(column_mappings),
            "foreign_keys": len(fk_mappings),
        },
    }


def handle_import_ontology(args: dict, get_graph) -> dict:
    """Import a local or remote OWL/RDF/TTL ontology into the ContextGraph."""
    file_path = (args.get("file_path") or "").strip() or None
    url = (args.get("url") or "").strip() or None
    include_properties = bool(args.get("include_properties", True))
    namespace_filter = (args.get("namespace_filter") or "").strip() or None

    temp_path: Optional[str] = None
    try:
        path, is_temp = _resolve_ontology_path(file_path, url)
        if is_temp:
            temp_path = path

        ontology = _ingest_ontology_file(path)
        stats = materialize_ontology_to_graph(
            get_graph(),
            ontology,
            include_properties=include_properties,
            namespace_filter=namespace_filter,
        )
        return {
            "status": "imported",
            "ontology_uri": ontology.get("uri"),
            "ontology_name": ontology.get("name"),
            "version": ontology.get("version"),
            "source": file_path or url,
            "stats": stats,
        }
    except Exception as exc:
        log.exception("import_ontology failed")
        return {"error": str(exc)}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                log.debug("Could not remove temp ontology file %s", temp_path)


def _merge_mapping_suggestions(
    explicit: Dict[str, Any],
    heuristic: Dict[str, Any],
) -> Dict[str, Any]:
    """Prefer explicit mapping-config entries; fill gaps with heuristic suggestions."""
    explicit_tables = {m["table"]: m for m in explicit.get("table_mappings", [])}
    merged_tables: List[Dict[str, Any]] = []

    for entry in heuristic.get("table_mappings", []):
        table = entry["table"]
        if table in explicit_tables and explicit_tables[table]["status"] == "mapped":
            merged_tables.append(explicit_tables[table])
        else:
            merged_tables.append(entry)

    explicit_cols = {
        (m["table"], m["column"]): m for m in explicit.get("column_mappings", [])
    }
    merged_cols: List[Dict[str, Any]] = []
    for entry in heuristic.get("column_mappings", []):
        key = (entry["table"], entry["column"])
        if key in explicit_cols and explicit_cols[key]["status"] == "mapped":
            merged_cols.append(explicit_cols[key])
        else:
            merged_cols.append(entry)

    explicit_fks = {
        (m["source_table"], m["target_table"]): m
        for m in explicit.get("foreign_key_mappings", [])
    }
    merged_fks: List[Dict[str, Any]] = []
    for entry in heuristic.get("foreign_key_mappings", []):
        key = (entry["source_table"], entry["target_table"])
        if key in explicit_fks and explicit_fks[key]["status"] == "mapped":
            merged_fks.append(explicit_fks[key])
        else:
            merged_fks.append(entry)

    tables_mapped = sum(
        1 for m in merged_tables if m["status"] in ("mapped", "suggested")
    )
    columns_mapped = sum(1 for m in merged_cols if m["status"] in ("mapped", "column_name_hint"))

    return {
        "table_mappings": merged_tables,
        "column_mappings": merged_cols,
        "foreign_key_mappings": merged_fks,
        "mapping_config": explicit.get("mapping_config"),
        "summary": {
            "tables": len(merged_tables),
            "tables_mapped": tables_mapped,
            "columns": len(merged_cols),
            "columns_mapped": columns_mapped,
            "foreign_keys": len(merged_fks),
        },
    }


def _apply_mappings_to_graph(graph: Any, suggestions: Dict[str, Any]) -> Dict[str, int]:
    """Materialize table/column/FK mapping suggestions into the ContextGraph."""
    stats = {"tables": 0, "columns": 0, "foreign_keys": 0}

    for mapping in suggestions.get("table_mappings", []):
        if mapping["status"] not in ("mapped", "suggested"):
            continue
        if not mapping.get("suggested_class_uri"):
            continue
        table_id = f"db:table:{mapping['table']}"
        graph.add_node(
            table_id,
            node_type="DatabaseTable",
            content=mapping["table"],
            table_name=mapping["table"],
            source="db_schema_mapping",
        )
        graph.add_edge(
            table_id,
            mapping["suggested_class_uri"],
            edge_type="mapsToClass",
            confidence=mapping.get("confidence", 1.0),
            mapping_source=mapping.get("mapping_source", "heuristic"),
            source="db_schema_mapping",
        )
        stats["tables"] += 1

    for mapping in suggestions.get("column_mappings", []):
        if mapping["status"] != "mapped":
            continue
        if not mapping.get("suggested_property_uri"):
            continue
        table_id = f"db:table:{mapping['table']}"
        col_id = f"db:column:{mapping['table']}.{mapping['column']}"
        graph.add_node(
            col_id,
            node_type="DatabaseColumn",
            content=mapping["column"],
            table_name=mapping["table"],
            column_name=mapping["column"],
            sql_type=mapping.get("sql_type"),
            source="db_schema_mapping",
        )
        graph.add_edge(table_id, col_id, edge_type="hasColumn", source="db_schema_mapping")
        graph.add_edge(
            col_id,
            mapping["suggested_property_uri"],
            edge_type="mapsToProperty",
            confidence=mapping.get("confidence", 1.0),
            mapping_source=mapping.get("mapping_source", "explicit"),
            source="db_schema_mapping",
        )
        stats["columns"] += 1

    for mapping in suggestions.get("foreign_key_mappings", []):
        if mapping["status"] not in ("mapped", "suggested"):
            continue
        if not mapping.get("source_class_uri") or not mapping.get("target_class_uri"):
            continue
        graph.add_edge(
            mapping["source_class_uri"],
            mapping["target_class_uri"],
            edge_type=mapping.get("suggested_edge_type", "references"),
            source_table=mapping["source_table"],
            target_table=mapping["target_table"],
            mapping_source=mapping.get("mapping_source", "heuristic"),
            source="db_schema_mapping",
        )
        stats["foreign_keys"] += 1

    return stats


def handle_map_db_schema_to_ontology(args: dict, get_graph) -> dict:
    """
    Analyze a SQL database schema and suggest mappings to ontology classes
    already present in the graph (e.g. after import_ontology).
    """
    connection_string = (args.get("connection_string") or "").strip() or None
    schema = (args.get("schema") or "").strip() or None
    schema_info = args.get("schema_info")
    apply_mappings = bool(args.get("apply_mappings", False))
    mapping_config_path = (args.get("mapping_config_path") or "").strip() or None

    try:
        if schema_info is None:
            if not connection_string:
                return {
                    "error": "connection_string or schema_info is required",
                }
            from semantica.ingest import DBIngestor

            schema_info = DBIngestor().analyze_schema(connection_string, schema=schema)

        graph = get_graph()
        ontology_classes = _collect_ontology_classes_from_graph(graph)
        if not ontology_classes:
            return {
                "error": (
                    "No OntologyClass nodes in graph. "
                    "Call import_ontology first or load a graph via SEMANTICA_KG_PATH."
                ),
            }

        heuristic = suggest_db_schema_mappings(schema_info, ontology_classes)

        from semantica.mcp_server.schema_mappings import (
            apply_explicit_mappings,
            load_mapping_config,
            resolve_mapping_config_path,
        )

        config_path = resolve_mapping_config_path(mapping_config_path)
        if config_path:
            mapping_config = load_mapping_config(config_path)
            explicit = apply_explicit_mappings(schema_info, mapping_config)
            suggestions = _merge_mapping_suggestions(explicit, heuristic)
            used_mapping_config = True
        else:
            suggestions = heuristic
            used_mapping_config = False

        applied_stats = {"tables": 0, "columns": 0, "foreign_keys": 0}
        if apply_mappings:
            applied_stats = _apply_mappings_to_graph(graph, suggestions)

        return {
            "status": "ok",
            "suggestions": suggestions,
            "applied": applied_stats,
            "ontology_classes_available": len(ontology_classes),
            "used_mapping_config": used_mapping_config,
            "mapping_config_path": config_path,
        }
    except Exception as exc:
        log.exception("map_db_schema_to_ontology failed")
        return {"error": str(exc)}


IMPORT_ONTOLOGY_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Local path to OWL/TTL/RDF/JSON-LD ontology file",
        },
        "url": {
            "type": "string",
            "description": "HTTP(S) URL to download ontology from (e.g. ontology.ttl)",
        },
        "include_properties": {
            "type": "boolean",
            "description": "Also import properties and domain/range edges (default: true)",
        },
        "namespace_filter": {
            "type": "string",
            "description": "Only import terms whose URI starts with this prefix (optional)",
        },
    },
}

MAP_DB_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "connection_string": {
            "type": "string",
            "description": "SQLAlchemy DB URL, e.g. postgresql://user:pass@host/db",
        },
        "schema": {
            "type": "string",
            "description": "Database schema name (optional)",
        },
        "schema_info": {
            "type": "object",
            "description": (
                "Pre-computed schema (DBIngestor.analyze_schema or "
                "iceberg-mcp-server-hive get_database_schema_info)"
            ),
        },
        "apply_mappings": {
            "type": "boolean",
            "description": "Write table/column/FK mapping edges into the graph (default: false)",
        },
        "mapping_config_path": {
            "type": "string",
            "description": (
                "Path to ontology↔DB mapping YAML. "
                "Falls back to SEMANTICA_MAPPING_CONFIG env when omitted."
            ),
        },
    },
}

ONTOLOGY_TOOL_DEFINITIONS = [
    {
        "name": "import_ontology",
        "description": (
            "Import an OWL/RDF/TTL ontology from a local file or URL into the "
            "knowledge graph as OntologyClass and property nodes with subClassOf hierarchy."
        ),
        "inputSchema": IMPORT_ONTOLOGY_SCHEMA,
    },
    {
        "name": "map_db_schema_to_ontology",
        "description": (
            "Analyze a SQL database schema and suggest mappings from tables/columns "
            "to OntologyClass nodes already in the graph. "
            "Optionally apply table→class mapping edges using a mapping YAML config."
        ),
        "inputSchema": MAP_DB_SCHEMA_SCHEMA,
    },
]
