#!/usr/bin/env bash
# Cursor MCP launcher — uses project venv (no global semantica-mcp on PATH required).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/.venv/bin/python" -m semantica.mcp_server
