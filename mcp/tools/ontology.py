"""
Ontology MCP tools — import OWL ontologies and map DB schemas.
"""

from __future__ import annotations

import logging

from mcp.schemas import (
    GET_HIVE_SCHEMA_INFO,
    IMPORT_KDM_ONTOLOGY,
    IMPORT_ONTOLOGY,
    MAP_DB_SCHEMA,
    MAP_ICEBERG_SCHEMA,
)
from mcp.session import get_graph
from semantica.mcp_server.ontology_tools import (
    handle_get_hive_schema_info,
    handle_import_kdm_ontology,
    handle_import_ontology,
    handle_map_db_schema_to_ontology,
    handle_map_iceberg_schema_to_ontology,
)

log = logging.getLogger("semantica.mcp.tools.ontology")


def _handle_import_ontology(args: dict) -> dict:
    return handle_import_ontology(args, get_graph)


def _handle_import_kdm_ontology(args: dict) -> dict:
    return handle_import_kdm_ontology(args, get_graph)


def _handle_map_db_schema(args: dict) -> dict:
    return handle_map_db_schema_to_ontology(args, get_graph)


def _handle_get_hive_schema_info(args: dict) -> dict:
    return handle_get_hive_schema_info(args)


def _handle_map_iceberg_schema(args: dict) -> dict:
    return handle_map_iceberg_schema_to_ontology(args, get_graph)


ONTOLOGY_TOOLS = [
    {
        "name": "import_ontology",
        "description": (
            "Import an OWL/RDF/TTL ontology from a local file or URL into the "
            "knowledge graph as OntologyClass and property nodes with subClassOf hierarchy."
        ),
        "inputSchema": IMPORT_ONTOLOGY,
        "_handler": _handle_import_ontology,
    },
    {
        "name": "import_kdm_ontology",
        "description": (
            "Import the XUnternehmen.Kerndatenmodell (KDM) ontology "
            "(https://w3id.org/kdm/) into the graph."
        ),
        "inputSchema": IMPORT_KDM_ONTOLOGY,
        "_handler": _handle_import_kdm_ontology,
    },
    {
        "name": "map_db_schema_to_ontology",
        "description": (
            "Analyze a SQL database schema and suggest mappings from tables to "
            "OntologyClass nodes already in the graph."
        ),
        "inputSchema": MAP_DB_SCHEMA,
        "_handler": _handle_map_db_schema,
    },
    {
        "name": "get_hive_schema_info",
        "description": (
            "Introspect Hive/Iceberg via SHOW TABLES + DESCRIBE; returns schema_info "
            "for map_db_schema_to_ontology."
        ),
        "inputSchema": GET_HIVE_SCHEMA_INFO,
        "_handler": _handle_get_hive_schema_info,
    },
    {
        "name": "map_iceberg_schema_to_ontology",
        "description": (
            "One-shot: introspect Hive/Iceberg (default kdm), import KDM if needed, "
            "map to ontology classes, apply graph edges."
        ),
        "inputSchema": MAP_ICEBERG_SCHEMA,
        "_handler": _handle_map_iceberg_schema,
    },
]
