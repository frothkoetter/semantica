#!/usr/bin/env bash
# Verify Decision Store path is writable (same env as semantica MCP in Agent Studio workflow).
set -euo pipefail

STORE="${SEMANTICA_DECISION_STORE:-/workspace/decisions}"

echo "=== Decision Store verification ==="
echo "SEMANTICA_DECISION_STORE: ${STORE}"
echo

if command -v uvx >/dev/null 2>&1; then
  uvx --from "${SEMANTICA_UV_FROM:-git+https://github.com/frothkoetter/semantica.git@main}" \
    python -c "
import json, os
os.environ['SEMANTICA_DECISION_STORE'] = '${STORE}'
from semantica.decision_store.store import check_store_writability
print(json.dumps(check_store_writability(), indent=2))
" 2>/dev/null || true
else
  echo "SKIP uvx not on PATH"
fi

echo
echo "Note: workflow MCP runs in bubblewrap — validate in Agent Studio with get_decision_store_status."
echo "Required Agent Studio env: SEMANTICA_DECISION_STORE=/workspace/decisions"
echo "Do NOT use /workflow_data/decisions — that mount is read-only in the sandbox."
