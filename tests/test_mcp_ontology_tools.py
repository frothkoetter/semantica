"""Tests for MCP ontology import and DB schema mapping tools."""

import os
import tempfile

import pytest

from semantica.context import ContextGraph
from semantica.mcp_server.ontology_tools import (
    handle_import_ontology,
    handle_map_db_schema_to_ontology,
    materialize_ontology_to_graph,
    suggest_db_schema_mappings,
)

SAMPLE_TTL = """
@prefix : <https://w3id.org/kdm/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<https://w3id.org/kdm/> a owl:Ontology ;
    owl:versionInfo "test" .

:Person a owl:Class ;
    rdfs:label "Natürliche Person" .

:Organisation a owl:Class ;
    rdfs:label "Juristische Person" .

:PersonName a owl:DatatypeProperty ;
    rdfs:label "Name" ;
    rdfs:domain :Person ;
    rdfs:range <http://www.w3.org/2001/XMLSchema#string> .
"""


@pytest.fixture
def graph():
    return ContextGraph()


@pytest.fixture
def sample_ontology_path():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttl", mode="w") as tmp:
        tmp.write(SAMPLE_TTL)
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_materialize_ontology_to_graph(graph, sample_ontology_path):
    from semantica.ingest import OntologyIngestor

    ontology = OntologyIngestor().ingest_ontology(sample_ontology_path).data
    stats = materialize_ontology_to_graph(graph, ontology, namespace_filter="https://w3id.org/kdm/")

    assert stats["class_nodes"] == 2
    assert stats["property_nodes"] == 1
    classes = list(graph.find_nodes(node_type="OntologyClass"))
    assert len(classes) == 2


def test_handle_import_ontology(graph, sample_ontology_path):
    result = handle_import_ontology(
        {"file_path": sample_ontology_path, "namespace_filter": "https://w3id.org/kdm/"},
        lambda: graph,
    )
    assert result["status"] == "imported"
    assert result["stats"]["class_nodes"] == 2


def test_suggest_db_schema_mappings():
    schema_info = {
        "tables": [
            {
                "name": "natuerliche_person",
                "columns": [{"name": "vorname", "type": "VARCHAR"}],
            },
            {
                "name": "unrelated_table",
                "columns": [{"name": "foo", "type": "INT"}],
            },
        ],
        "foreign_keys": [],
    }
    classes = [
        {
            "uri": "https://w3id.org/kdm/Person",
            "label": "Natürliche Person",
            "normalized": "natuerlichepersonperson",
        },
        {
            "uri": "https://w3id.org/kdm/Organisation",
            "label": "Juristische Person",
            "normalized": "juristischepersonorganisation",
        },
    ]
    result = suggest_db_schema_mappings(schema_info, classes)
    assert result["summary"]["tables_mapped"] >= 1
    mapped = [m for m in result["table_mappings"] if m["table"] == "natuerliche_person"][0]
    assert mapped["status"] == "suggested"
    assert mapped["suggested_class_uri"] == "https://w3id.org/kdm/Person"


def test_map_db_schema_requires_ontology_in_graph(graph):
    result = handle_map_db_schema_to_ontology(
        {
            "schema_info": {
                "tables": [{"name": "person", "columns": []}],
                "foreign_keys": [],
            }
        },
        lambda: graph,
    )
    assert "error" in result


def test_map_db_schema_with_ontology(graph, sample_ontology_path):
    handle_import_ontology(
        {"file_path": sample_ontology_path, "namespace_filter": "https://w3id.org/kdm/"},
        lambda: graph,
    )
    result = handle_map_db_schema_to_ontology(
        {
            "schema_info": {
                "tables": [
                    {
                        "name": "person",
                        "columns": [{"name": "name", "type": "TEXT"}],
                    }
                ],
                "foreign_keys": [],
            },
            "apply_mappings": True,
        },
        lambda: graph,
    )
    assert result["status"] == "ok"
    assert result["applied"]["tables"] >= 1
    tables = list(graph.find_nodes(node_type="DatabaseTable"))
    assert len(tables) == 1


def test_explicit_mapping_config(graph):
    from pathlib import Path

    from semantica.mcp_server.schema_mappings import (
        apply_explicit_mappings,
        load_mapping_config,
        resolve_column_property,
        resolve_table_class,
    )

    config_path = str(
        Path(__file__).resolve().parents[1] / "config" / "airline_r2rml_db_mapping.yaml"
    )
    config = load_mapping_config(config_path)
    assert config.get("tables")

    resolved = resolve_table_class("flights", config)
    assert resolved is not None
    assert resolved[1] == "Flight"

    col = resolve_column_property("flights", "arrdelay", config)
    assert col is not None
    assert col[1] == "arrDelay"

    airline_ttl = (
        Path(__file__).resolve().parents[1] / "data" / "airline_demo_ontology.ttl"
    )
    handle_import_ontology(
        {
            "file_path": str(airline_ttl),
            "namespace_filter": "https://w3id.org/demo/airline#",
        },
        lambda: graph,
    )
    result = handle_map_db_schema_to_ontology(
        {
            "schema_info": {
                "tables": [
                    {
                        "name": "flights",
                        "columns": [
                            {"name": "arrdelay", "type": "INT"},
                            {"name": "year", "type": "INT"},
                        ],
                    }
                ],
                "foreign_keys": [],
            },
            "mapping_config_path": config_path,
            "apply_mappings": True,
        },
        lambda: graph,
    )
    assert result["status"] == "ok"
    assert result["used_mapping_config"] is True
    assert result["applied"]["tables"] == 1
    assert result["applied"]["columns"] == 2

    explicit = apply_explicit_mappings(
        {
            "tables": [{"name": "flights", "columns": []}],
            "foreign_keys": [],
        },
        config,
    )
    assert explicit["summary"]["tables_mapped"] == 1


def test_infer_foreign_keys():
    from semantica.mcp_server.hive_schema import infer_foreign_keys

    tables = [
        {
            "name": "juristische_person",
            "columns": [{"name": "id", "type": "string"}],
        },
        {
            "name": "anschrift",
            "columns": [
                {"name": "id", "type": "string"},
                {"name": "juristische_person_id", "type": "string"},
            ],
        },
    ]
    fks = infer_foreign_keys(tables)
    assert len(fks) == 1
    assert fks[0]["referred_table"] == "juristische_person"


def test_map_iceberg_schema_with_mocked_introspection(graph):
    from pathlib import Path
    from unittest.mock import patch

    from semantica.mcp_server.hive_build import handle_map_iceberg_schema_to_ontology
    from semantica.mcp_server.ontology_tools import handle_import_ontology

    config_path = str(
        Path(__file__).resolve().parents[1] / "config" / "airline_r2rml_db_mapping.yaml"
    )
    airline_ttl = (
        Path(__file__).resolve().parents[1] / "data" / "airline_demo_ontology.ttl"
    )
    handle_import_ontology(
        {
            "file_path": str(airline_ttl),
            "namespace_filter": "https://w3id.org/demo/airline#",
        },
        lambda: graph,
    )

    mock_schema = {
        "database": "airlinedata",
        "tables": [
            {
                "name": "flights",
                "columns": [
                    {"name": "year", "type": "int"},
                    {"name": "arrdelay", "type": "int"},
                ],
            }
        ],
        "views": [],
        "foreign_keys": [],
        "analysis": {"total_tables": 1},
    }

    with patch(
        "semantica.mcp_server.hive_schema.introspect_hive_database",
        return_value=mock_schema,
    ):
        result = handle_map_iceberg_schema_to_ontology(
            {
                "database": "airlinedata",
                "mapping_config_path": config_path,
                "apply_mappings": True,
            },
            lambda: graph,
        )

    assert result["status"] == "ok"
    assert result["database"] == "airlinedata"
    assert result["applied"]["tables"] == 1


def test_get_graph_summary_includes_ontology_counts(sample_ontology_path):
    import semantica.mcp_server as mcp_mod

    mcp_mod._graph = None
    graph = ContextGraph()
    handle_import_ontology(
        {"file_path": sample_ontology_path, "namespace_filter": "https://w3id.org/kdm/"},
        lambda: graph,
    )
    mcp_mod._graph = graph

    summary = mcp_mod._tool_get_graph_summary({})
    assert summary["ontology_class_count"] == 2
    assert summary["graph_ready"] is True
    assert "Person" in summary["ontology_classes"] or "Natürliche Person" in summary["ontology_classes"]

    mcp_mod._graph = None
