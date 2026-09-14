#!/usr/bin/env python3
"""Generate Cloudera Agent Studio MCP JSON from .cursor/mcp.json (no secrets written)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MCP = REPO / ".cursor" / "mcp.json"
OUT_DIR = REPO / "deploy" / "cloudera-agent-studio" / "generated"
DEFAULT_SEMANTICA_GIT = "git+https://github.com/frothkoetter/semantica.git@main"

SECRET_KEYS = {"HIVE_PASSWORD", "HIVE_USER", "AWS_SECRET_ACCESS_KEY", "API_KEY"}


def _placeholder(key: str, value: str) -> str:
    if key in SECRET_KEYS:
        return f"YOUR_{key}"
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-config", type=Path, default=DEFAULT_MCP)
    parser.add_argument("--semantica-root", default="/home/cdsw/semantica")
    parser.add_argument("--semantica-git", default=DEFAULT_SEMANTICA_GIT)
    parser.add_argument("--iceberg-root", default="/home/cdsw/iceberg-mcp-server-hive")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    env: dict[str, str] = {}
    if args.mcp_config.is_file():
        payload = json.loads(args.mcp_config.read_text(encoding="utf-8"))
        sem = (payload.get("mcpServers") or {}).get("semantica", {})
        for key, value in (sem.get("env") or {}).items():
            env[key] = _placeholder(key, str(value))

    semantica_env = {
        "SEMANTICA_KG_PATH": f"{args.semantica_root}/data/airline_graph.json",
        "SEMANTICA_MAPPING_CONFIG": f"{args.semantica_root}/config/airline_r2rml_db_mapping.yaml",
        "SEMANTICA_LOG_LEVEL": "WARNING",
    }
    hive_env = {k: v for k, v in env.items() if k.startswith("HIVE_")}
    if not hive_env.get("HIVE_DATABASE"):
        hive_env["HIVE_DATABASE"] = "airlinedata"

    configs = {
        "semantica-mcp.json": {
            "mcpServers": {
                "semantica": {
                    "command": "uvx",
                    "args": ["--from", args.semantica_git, "semantica-mcp"],
                    "env": semantica_env,
                }
            }
        },
        "iceberg-hive-mcp.json": {
            "mcpServers": {
                "iceberg-hive": {
                    "command": "uvx",
                    "args": ["--from", args.iceberg_root, "run-server"],
                    "env": hive_env,
                }
            }
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, body in configs.items():
        path = args.output_dir / name
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
