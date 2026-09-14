"""
Ontology MCP tools — import OWL ontologies and map DB schemas.

Hive/Iceberg introspection and SQL are provided by iceberg-mcp-server-hive.
Pass schema_info from get_database_schema_info into map_db_schema_to_ontology.
"""

from __future__ import annotations

import logging

from mcp.schemas import IMPORT_ONTOLOGY, MAP_DB_SCHEMA
from mcp.session import get_graph
from semantica.mcp_server.ontology_tools import (
    handle_import_ontology,
    handle_map_db_schema_to_ontology,
)

log = logging.getLogger("semantica.mcp.tools.ontology")


def _handle_import_ontology(args: dict) -> dict:
    return handle_import_ontology(args, get_graph)


def _handle_map_db_schema(args: dict) -> dict:
    return handle_map_db_schema_to_ontology(args, get_graph)


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
        "name": "map_db_schema_to_ontology",
        "description": (
            "Map tables/columns to OntologyClass nodes using schema_info from "
            "iceberg-mcp get_database_schema_info or a SQL connection string."
        ),
        "inputSchema": MAP_DB_SCHEMA,
        "_handler": _handle_map_db_schema,
    },
]
