#!/usr/bin/env python3
"""Execute XUnternehmen seed chunks via iceberg hive_tools (same backend as MCP execute_ddl).

Loads Hive credentials from ~/.cursor/mcp.json (never from argv/shell env).
Respects kdm/hive/.load_progress.json for resume.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHUNKS = REPO / "kdm/hive/.chunks250"
PROGRESS = REPO / "kdm/hive/.load_progress.json"
BATCHES = REPO / "kdm/hive/.batches"


def load_mcp_env(config_path: Path) -> None:
    payload = json.loads(config_path.read_text())
    servers = payload.get("mcpServers") or {}
    hive = servers.get("iceberg-mcp-server-hive") or {}
    for key, value in (hive.get("env") or {}).items():
        os.environ.setdefault(key, str(value))


def load_progress() -> dict:
    if PROGRESS.is_file():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"next_chunk": 0, "total_chunks": 0}


def save_progress(p: dict) -> None:
    PROGRESS.write_text(json.dumps(p, indent=2), encoding="utf-8")


def run_batches(start: int, end: int, use_batch_files: bool = True) -> int:
    from iceberg_mcp_server.tools import hive_tools

    p = load_progress()
    total = p.get("total_chunks", 0)
    errors: list[str] = []

    if use_batch_files and BATCHES.is_dir():
        batch_files = sorted(BATCHES.glob("*.json"))
        for bf in batch_files:
            meta = json.loads(bf.read_text())
            bs, be = meta["start"], meta["end"]
            if be < start:
                continue
            if bs > end:
                break
            if bs < start:
                continue
            query = meta["query"]
            label = f"batch {bf.stem} chunks {bs}-{be}"
            result = hive_tools.execute_ddl(query)
            if isinstance(result, str) and result.startswith("Error:"):
                errors.append(f"{label}: {result}")
                print(f"FAIL {label}\n  {result}", file=sys.stderr)
                return 1
            p["next_chunk"] = be + 1
            save_progress(p)
            if (be + 1) % 20 == 0 or be == end:
                print(f"Progress: chunk {be + 1}/{total} ({100 * (be + 1) / total:.1f}%)")
            print(f"OK {label}")
    else:
        for idx in range(start, end + 1):
            path = CHUNKS / f"{idx:04d}.sql"
            if not path.is_file():
                errors.append(f"missing {path}")
                continue
            query = path.read_text(encoding="utf-8")
            result = hive_tools.execute_ddl(query)
            if isinstance(result, str) and result.startswith("Error:"):
                errors.append(f"chunk {idx}: {result}")
                print(f"FAIL chunk {idx}\n  {result}", file=sys.stderr)
                return 1
            p["next_chunk"] = idx + 1
            save_progress(p)
            if (idx + 1) % 20 == 0 or idx == end:
                print(f"Progress: chunk {idx + 1}/{total} ({100 * (idx + 1) / total:.1f}%)")
            print(f"OK chunk {idx}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XUnternehmen seed chunks via hive_tools")
    parser.add_argument("--mcp-config", type=Path, default=Path.home() / ".cursor" / "mcp.json")
    parser.add_argument("--start", type=int, default=None, help="First chunk (default: from progress)")
    parser.add_argument("--end", type=int, default=381, help="Last chunk inclusive")
    parser.add_argument("--per-chunk", action="store_true", help="Use .chunks250/ not .batches/")
    args = parser.parse_args()

    if args.mcp_config.is_file():
        load_mcp_env(args.mcp_config)

    p = load_progress()
    start = args.start if args.start is not None else p.get("next_chunk", 0)
    end = args.end
    print(f"Loading chunks {start}-{end} ...")
    return run_batches(start, end, use_batch_files=not args.per_chunk)


if __name__ == "__main__":
    raise SystemExit(main())
