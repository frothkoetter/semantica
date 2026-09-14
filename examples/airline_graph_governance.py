"""
Phase-1 governance for the airline Semantica stack:

- Validate merged OWL/TTL ontologies (OntologyEvaluator + airline checks)
- Export ContextGraph to Turtle for governance / Git diff
- Generate OntologyVisualizer HTML (class hierarchy + property graph)

Used by scripts/build_airline_graph.py and tests/test_airline_graph_phase1.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import yaml

REPO = Path(__file__).resolve().parents[1]

DEFAULT_ONTOLOGY_TTLS = (
    REPO / "data" / "airline_demo_ontology.ttl",
    REPO / "data" / "airline_business_ontology.ttl",
)
DEFAULT_MAPPING = REPO / "config" / "airline_r2rml_db_mapping.yaml"
DEFAULT_RULES = REPO / "config" / "airline_business_rules.yaml"
DEFAULT_GRAPH_JSON = REPO / "data" / "airline_graph.json"
DEFAULT_GRAPH_TTL = REPO / "data" / "airline_graph.ttl"
DEFAULT_VALIDATION_JSON = REPO / "data" / "airline_ontology_validation.json"
DEFAULT_ONTO_VIZ_DIR = REPO / "data" / "airline_ontology_viz"

AIRLINE_NS = "https://w3id.org/demo/airline#"

REQUIRED_CLASSES = (
    "Flight",
    "Airline",
    "Airport",
    "Plane",
    "Route",
    "TimeWindow",
    "MorningPeak",
    "EveningPeak",
    "OnTimeFlight",
    "DelayedFlight",
    "DelayReason",
    "CarrierDelayReason",
    "WeatherDelayReason",
    "NASDelayReason",
    "SecurityDelayReason",
    "LateAircraftDelayReason",
    "OnTimePerformance",
)

MATERIALIZED_TABLES = {
    "flights": "Flight",
    "airlines": "Airline",
    "airports": "Airport",
    "planes": "Plane",
}

FLIGHT_KEY_COLUMNS = (
    "arrdelay",
    "depdelay",
    "cancelled",
    "carrierdelay",
    "weatherdelay",
    "nasdelay",
    "securitydelay",
    "lateaircraftdelay",
)

AIRLINE_COMPETENCY_QUESTIONS = (
    "What is the on-time performance of flights by carrier?",
    "What is the primary delay reason for delayed flights?",
    "Which time window is a flight scheduled in?",
    "Which route has the worst on-time performance?",
    "Which airline operates a given flight?",
)


def _normalize_table(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _normalize_class_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1].lstrip("/")
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _class_keys(cls: Dict[str, Any]) -> Set[str]:
    keys: Set[str] = set()
    uri = cls.get("uri")
    if uri:
        keys.add(_local_name(str(uri)))
    for field in ("name", "label"):
        value = cls.get(field)
        if value:
            keys.add(str(value))
    return {_normalize_class_key(k) for k in keys if k}


def _ontology_class_index(ontology: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for cls in ontology.get("classes", []):
        for key in _class_keys(cls):
            index.setdefault(key, cls)
    return index


def ingest_ttl_paths(paths: Sequence[Path]) -> Dict[str, Any]:
    from semantica.ingest import OntologyIngestor

    ingestor = OntologyIngestor()
    chunks: List[Dict[str, Any]] = []
    for path in paths:
        chunks.append(ingestor.ingest_ontology(str(path)).data)
    return merge_ontology_dicts(chunks)


def merge_ontology_dicts(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "uri": AIRLINE_NS,
        "name": "Airline merged ontology",
        "classes": [],
        "properties": [],
    }
    class_uris: Set[str] = set()
    prop_uris: Set[str] = set()
    for chunk in chunks:
        for cls in chunk.get("classes", []):
            uri = cls.get("uri")
            if uri and uri not in class_uris:
                merged["classes"].append(cls)
                class_uris.add(uri)
        for prop in chunk.get("properties", []):
            uri = prop.get("uri")
            if uri and uri not in prop_uris:
                merged["properties"].append(prop)
                prop_uris.add(uri)
    return merged


@dataclass
class ValidationReport:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ontology_evaluation: Dict[str, Any] = field(default_factory=dict)
    mapping_checks: Dict[str, Any] = field(default_factory=dict)
    graph_checks: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_airline_ontology(
    ontology: Dict[str, Any],
    *,
    mapping_path: Path = DEFAULT_MAPPING,
    rules_path: Path = DEFAULT_RULES,
) -> ValidationReport:
    report = ValidationReport(ok=True)

    class_index = _ontology_class_index(ontology)
    missing = [
        name
        for name in REQUIRED_CLASSES
        if _normalize_class_key(name) not in class_index
    ]
    if missing:
        report.errors.append(f"Missing required classes: {', '.join(missing)}")
        report.ok = False

    from semantica.ontology import OntologyEvaluator

    evaluator = OntologyEvaluator()
    eval_result = evaluator.evaluate_ontology(
        ontology,
        competency_questions=list(AIRLINE_COMPETENCY_QUESTIONS),
    )
    report.ontology_evaluation = {
        "coverage_score": eval_result.coverage_score,
        "completeness_score": eval_result.completeness_score,
        "gaps": eval_result.gaps,
        "suggestions": eval_result.suggestions,
        "metrics": eval_result.metrics,
        "competency_questions": list(AIRLINE_COMPETENCY_QUESTIONS),
    }
    if eval_result.coverage_score < 1.0:
        report.warnings.append(
            f"Competency coverage {eval_result.coverage_score:.0%} "
            f"({eval_result.metrics.get('competency_question_coverage', 0):.0%} answerable)"
        )
    if eval_result.completeness_score < 0.8:
        report.warnings.append(
            f"Ontology completeness score low: {eval_result.completeness_score:.2f}"
        )

    mapping_checks = _validate_mapping_yaml(mapping_path, class_index)
    report.mapping_checks = mapping_checks
    for err in mapping_checks.get("errors", []):
        report.errors.append(err)
        report.ok = False
    for warn in mapping_checks.get("warnings", []):
        report.warnings.append(warn)

    rules_checks = _validate_rules_yaml(rules_path, class_index)
    report.mapping_checks["rules"] = rules_checks
    for err in rules_checks.get("errors", []):
        report.errors.append(err)
        report.ok = False

    return report


def _validate_mapping_yaml(
    mapping_path: Path, class_index: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    payload = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    tables = payload.get("tables") or {}
    errors: List[str] = []
    warnings: List[str] = []

    for table, expected_class in MATERIALIZED_TABLES.items():
        key = _normalize_table(table)
        mapped = tables.get(key)
        if not mapped:
            errors.append(f"Mapping YAML missing table key '{key}' ({table})")
            continue
        if _normalize_class_key(mapped) not in class_index:
            errors.append(
                f"Table '{table}' maps to unknown class '{mapped}' (not in ontology)"
            )
        elif _normalize_class_key(mapped) != _normalize_class_key(expected_class):
            warnings.append(
                f"Table '{table}' maps to '{mapped}' (expected '{expected_class}')"
            )

    for table_key, cls_name in tables.items():
        if _normalize_class_key(cls_name) not in class_index:
            errors.append(
                f"Mapping tables.{table_key} → '{cls_name}' references unknown class"
            )

    return {
        "mapping_path": str(mapping_path),
        "table_mappings": len(tables),
        "errors": errors,
        "warnings": warnings,
    }


def _validate_rules_yaml(
    rules_path: Path, class_index: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    errors: List[str] = []
    time_windows = payload.get("time_windows") or {}
    for window_name, spec in time_windows.items():
        cls = (spec or {}).get("class", window_name)
        if _normalize_class_key(cls) not in class_index:
            errors.append(f"Business rules time window class '{cls}' not in ontology")
    return {"rules_path": str(rules_path), "time_windows": list(time_windows), "errors": errors}


def _graph_node_field(node: Any, field: str, default: Any = "") -> Any:
    if isinstance(node, dict):
        if field == "metadata":
            return node.get("metadata") or {}
        return node.get(field, default)
    return getattr(node, field, default)


def validate_graph_mappings(graph: Any) -> Dict[str, Any]:
    """Check materialized Hive tables are mapped in a built ContextGraph."""
    errors: List[str] = []
    warnings: List[str] = []

    def _get_node(node_id: str) -> Any:
        raw = graph.nodes.get(node_id)
        if raw is not None:
            return raw
        for candidate in graph.find_nodes():
            if str(candidate.get("id")) == str(node_id):
                return candidate
        return None

    table_nodes: Dict[str, Any] = {}
    for node in graph.find_nodes(node_type="DatabaseTable"):
        meta = _graph_node_field(node, "metadata") or {}
        raw = meta.get("table_name") or _graph_node_field(node, "content") or ""
        table_nodes[_normalize_table(str(raw))] = node

    class_by_table: Dict[str, str] = {}
    for edge in graph.edges:
        edge_type = (
            edge.get("type")
            if isinstance(edge, dict)
            else getattr(edge, "edge_type", None)
        )
        if edge_type != "mapsToClass":
            continue
        source_id = (
            edge.get("source_id")
            if isinstance(edge, dict)
            else edge.source_id
        )
        target_id = (
            edge.get("target_id")
            if isinstance(edge, dict)
            else edge.target_id
        )
        src = _get_node(str(source_id))
        tgt = _get_node(str(target_id))
        if not src or not tgt:
            continue
        meta = _graph_node_field(src, "metadata") or {}
        table_key = _normalize_table(
            str(meta.get("table_name") or _graph_node_field(src, "content") or "")
        )
        tgt_id = _graph_node_field(tgt, "id") or _graph_node_field(tgt, "node_id")
        class_by_table[table_key] = (
            _graph_node_field(tgt, "content") or _local_name(str(tgt_id))
        )

    for table, expected in MATERIALIZED_TABLES.items():
        key = _normalize_table(table)
        if key not in table_nodes:
            errors.append(f"Graph has no DatabaseTable node for '{table}'")
            continue
        mapped = class_by_table.get(key)
        if not mapped:
            errors.append(f"Table '{table}' has no mapsToClass edge in graph")
        elif _normalize_class_key(mapped) != _normalize_class_key(expected):
            warnings.append(f"Table '{table}' maps to '{mapped}' (expected '{expected}')")

    flights_key = _normalize_table("flights")
    flight_cols: Set[str] = set()
    for node in graph.find_nodes(node_type="DatabaseColumn"):
        meta = _graph_node_field(node, "metadata") or {}
        if _normalize_table(str(meta.get("table_name") or "")) != flights_key:
            continue
        col = str(meta.get("column_name") or _graph_node_field(node, "content") or "").lower()
        flight_cols.add(_normalize_table(col))

    missing_cols = [
        col for col in FLIGHT_KEY_COLUMNS if _normalize_table(col) not in flight_cols
    ]
    if missing_cols:
        warnings.append(
            f"flights missing mapped columns: {', '.join(missing_cols)}"
        )

    return {
        "tables_in_graph": sorted(table_nodes),
        "class_by_table": class_by_table,
        "errors": errors,
        "warnings": warnings,
    }


def export_graph_turtle(graph: Any, output_path: Path) -> Dict[str, Any]:
    from semantica.export import RDFExporter

    kg = graph.to_kg_dict()
    exporter = RDFExporter()
    turtle = exporter.export_to_rdf(kg, format="turtle")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(turtle, encoding="utf-8")
    return {
        "output": str(output_path),
        "bytes": len(turtle.encode("utf-8")),
        "entity_count": kg.get("statistics", {}).get("entity_count"),
        "relationship_count": kg.get("statistics", {}).get("relationship_count"),
    }


def export_ontology_visualizations(
    ontology: Dict[str, Any],
    output_dir: Path = DEFAULT_ONTO_VIZ_DIR,
) -> Dict[str, Any]:
    from semantica.visualization import OntologyVisualizer

    output_dir.mkdir(parents=True, exist_ok=True)
    viz = OntologyVisualizer(color_scheme="default", layout="force")
    hierarchy_path = output_dir / "airline_ontology_hierarchy.html"
    properties_path = output_dir / "airline_ontology_properties.html"
    structure_path = output_dir / "airline_ontology_structure.html"

    viz.visualize_hierarchy(
        ontology,
        output="html",
        file_path=str(hierarchy_path),
    )
    viz.visualize_properties(
        ontology,
        output="html",
        file_path=str(properties_path),
    )
    viz.visualize_structure(
        ontology,
        output="html",
        file_path=str(structure_path),
    )
    return {
        "output_dir": str(output_dir),
        "hierarchy_html": str(hierarchy_path),
        "properties_html": str(properties_path),
        "structure_html": str(structure_path),
        "class_count": len(ontology.get("classes", [])),
        "property_count": len(ontology.get("properties", [])),
    }


def run_phase1(
    graph: Any,
    *,
    ontology_paths: Sequence[Path] = DEFAULT_ONTOLOGY_TTLS,
    mapping_path: Path = DEFAULT_MAPPING,
    rules_path: Path = DEFAULT_RULES,
    graph_json_path: Path = DEFAULT_GRAPH_JSON,
    graph_ttl_path: Path = DEFAULT_GRAPH_TTL,
    validation_json_path: Path = DEFAULT_VALIDATION_JSON,
    ontology_viz_dir: Path = DEFAULT_ONTO_VIZ_DIR,
    skip_validate: bool = False,
    skip_export: bool = False,
    skip_ontology_viz: bool = False,
    validate_graph: bool = True,
) -> Dict[str, Any]:
    """Run validation, RDF export, and ontology visualizations after graph build."""
    result: Dict[str, Any] = {"phase": 1}

    ontology = ingest_ttl_paths(ontology_paths)
    result["ontology"] = {
        "class_count": len(ontology.get("classes", [])),
        "property_count": len(ontology.get("properties", [])),
    }

    if not skip_validate:
        report = validate_airline_ontology(
            ontology,
            mapping_path=mapping_path,
            rules_path=rules_path,
        )
        if validate_graph:
            graph_checks = validate_graph_mappings(graph)
            report.graph_checks = graph_checks
            for err in graph_checks.get("errors", []):
                report.errors.append(err)
                report.ok = False
            for warn in graph_checks.get("warnings", []):
                report.warnings.append(warn)
        result["validation"] = report.to_dict()
        validation_json_path.parent.mkdir(parents=True, exist_ok=True)
        validation_json_path.write_text(
            json.dumps(result["validation"], indent=2),
            encoding="utf-8",
        )
        result["validation_json"] = str(validation_json_path)
        if not report.ok:
            raise ValueError(
                "Airline ontology validation failed:\n"
                + "\n".join(f"  - {e}" for e in report.errors)
            )

    if not skip_export:
        result["export"] = export_graph_turtle(graph, graph_ttl_path)

    if not skip_ontology_viz:
        result["ontology_viz"] = export_ontology_visualizations(
            ontology, output_dir=ontology_viz_dir
        )

    result["graph_json"] = str(graph_json_path)
    return result
