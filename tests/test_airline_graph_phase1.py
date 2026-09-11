"""Phase-1 governance: ontology validation, RDF export, ontology viz."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "examples"))

from airline_graph_governance import (
    DEFAULT_ONTOLOGY_TTLS,
    export_graph_turtle,
    ingest_ttl_paths,
    merge_ontology_dicts,
    run_phase1,
    validate_airline_ontology,
    validate_graph_mappings,
)
from semantica.context import ContextGraph
from semantica.mcp_server.ontology_tools import (
    handle_import_ontology,
    materialize_ontology_to_graph,
)


@pytest.fixture
def merged_ontology():
    return ingest_ttl_paths(DEFAULT_ONTOLOGY_TTLS)


def test_merge_airline_ontologies_has_required_classes(merged_ontology):
    from airline_graph_governance import _class_keys

    all_keys = set()
    for cls in merged_ontology["classes"]:
        all_keys.update(_class_keys(cls))
    assert "flight" in all_keys
    assert "ontimeflight" in all_keys
    assert "lateaircraftdelayreason" in all_keys
    assert len(merged_ontology["classes"]) >= 20


def test_validate_airline_ontology_passes(merged_ontology):
    report = validate_airline_ontology(merged_ontology)
    assert report.ok
    assert not report.errors
    assert report.ontology_evaluation["coverage_score"] >= 0.8
    assert report.ontology_evaluation["completeness_score"] >= 0.8


def test_validate_airline_ontology_fails_on_missing_class(merged_ontology):
    slim = dict(merged_ontology)
    slim["classes"] = [
        c for c in merged_ontology["classes"] if c.get("name") != "Flight"
    ]
    report = validate_airline_ontology(slim)
    assert not report.ok
    assert any("Flight" in err for err in report.errors)


def test_export_graph_turtle_from_built_graph(merged_ontology):
    graph = ContextGraph()
    materialize_ontology_to_graph(
        graph,
        merged_ontology,
        namespace_filter="https://w3id.org/demo/airline#",
    )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "airline_graph.ttl"
        meta = export_graph_turtle(graph, out)
        text = out.read_text(encoding="utf-8")
        assert out.exists()
        assert meta["bytes"] > 100
        assert "@prefix" in text or "OntologyClass" in text


def test_ontology_visualizer_wires_hierarchy_and_properties(merged_ontology):
    from semantica.visualization import OntologyVisualizer

    viz = OntologyVisualizer()
    classes, properties = viz._normalize_ontology_for_visualization(
        merged_ontology["classes"],
        merged_ontology["properties"],
    )
    class_names = {c["name"] for c in classes}
    with_parent = sum(1 for c in classes if c.get("parent"))
    assert with_parent >= 10
    assert "Flight" in class_names
    assert properties[0]["domain"] in class_names
    assert properties[0]["range"] in class_names

    hierarchy = viz._build_hierarchy_tree(classes)
    edge_count = sum(len(children) for children in hierarchy.values())
    assert edge_count >= 10


def test_run_phase1_skip_hive_graph(tmp_path, merged_ontology):
    graph = ContextGraph()
    materialize_ontology_to_graph(
        graph,
        merged_ontology,
        namespace_filter="https://w3id.org/demo/airline#",
    )
    json_path = tmp_path / "graph.json"
    ttl_path = tmp_path / "graph.ttl"
    validation_path = tmp_path / "validation.json"
    viz_dir = tmp_path / "viz"
    graph.save_to_file(str(json_path))

    result = run_phase1(
        graph,
        graph_json_path=json_path,
        graph_ttl_path=ttl_path,
        validation_json_path=validation_path,
        ontology_viz_dir=viz_dir,
        validate_graph=False,
    )
    assert ttl_path.is_file()
    assert validation_path.is_file()
    assert (viz_dir / "airline_ontology_hierarchy.html").is_file()
    assert (viz_dir / "airline_ontology_properties.html").is_file()
    assert (viz_dir / "airline_ontology_structure.html").is_file()
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["ok"] is True


@pytest.mark.skipif(
    not os.getenv("HIVE_HOST"),
    reason="Hive mapping validation requires HIVE_HOST",
)
def test_validate_graph_mappings_on_live_build():
    graph_path = REPO / "data" / "airline_graph.json"
    if not graph_path.is_file():
        pytest.skip("airline_graph.json not built yet")
    graph = ContextGraph()
    graph.load_from_file(str(graph_path))
    checks = validate_graph_mappings(graph)
    assert not checks["errors"]


def test_build_script_imports_phase1_module():
    build_script = (REPO / "scripts" / "build_airline_graph.py").read_text(
        encoding="utf-8"
    )
    assert "airline_graph_governance" in build_script
    assert "--skip-phase1" in build_script
