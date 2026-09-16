#!/usr/bin/env bash
# Verify airline_graph.json is reachable the same way semantica-mcp loads it.
# Run on the SAME CDSW workbench host that runs the Agent Studio workflow session.
set -euo pipefail

SEMANTICA_ROOT="${SEMANTICA_ROOT:-/home/cdsw/semantica}"
KG_PATH="${SEMANTICA_KG_PATH:-/home/cdsw/data/airline_graph.json}"
MAPPING_PATH="${SEMANTICA_MAPPING_CONFIG:-${SEMANTICA_ROOT}/config/airline_r2rml_db_mapping.yaml}"

echo "=== Semantica KG path verification ==="
echo "hostname:                      $(hostname)"
echo "cwd:                           $(pwd)"
echo "SEMANTICA_KG_PATH (effective): ${KG_PATH}"
echo "SEMANTICA_MAPPING_CONFIG:      ${MAPPING_PATH}"
echo

fail=0

if [[ -f "${KG_PATH}" ]]; then
  size=$(wc -c < "${KG_PATH}")
  echo "OK   Graph file exists in this shell (${size} bytes)"
else
  echo "FAIL Graph file missing in this shell: ${KG_PATH}"
  for alt in "${SEMANTICA_ROOT}/data/airline_graph.json" "/home/cdsw/data/airline_graph.json"; do
    if [[ -f "${alt}" ]]; then
      echo "     Found alternate: ${alt}"
      echo "     Fix: export SEMANTICA_KG_PATH=${alt}"
    fi
  done
  fail=1
fi

if [[ -f "${MAPPING_PATH}" ]]; then
  echo "OK   Mapping YAML exists"
else
  echo "WARN Mapping YAML missing: ${MAPPING_PATH}"
fi

echo
echo "=== MCP smoke test (uvx, same as Agent Studio) ==="
if command -v uvx >/dev/null 2>&1; then
  out=$(SEMANTICA_KG_PATH="${KG_PATH}" SEMANTICA_LOG_LEVEL=WARNING \
    uvx --from "${SEMANTICA_UV_FROM:-git+https://github.com/frothkoetter/semantica.git@main}" \
    python -c "
import json
import semantica.mcp_server as m
m._graph = None
m._graph_loaded_from = None
from semantica.mcp_server import _tool_get_graph_summary
print(json.dumps(_tool_get_graph_summary({})))
" 2>/dev/null) || { echo "FAIL uvx smoke test"; fail=1; out=""; }

  if [[ -n "${out}" ]]; then
    echo "${out}"
    if echo "${out}" | grep -q '"kg_path_exists": false'; then
      echo
      echo "FAIL MCP process cannot see the graph file (kg_path_exists: false)."
      echo "     Your shell and the Agent Studio MCP subprocess may be on different workers."
      echo "     Compare hostname in the JSON above with: hostname"
      fail=1
    elif echo "${out}" | grep -q '"graph_ready": false'; then
      echo
      echo "WARN File visible but graph empty — check file format or load errors (SEMANTICA_LOG_LEVEL=INFO)."
      fail=1
    fi
  fi
else
  echo "SKIP uvx not on PATH"
fi

exit "${fail}"
