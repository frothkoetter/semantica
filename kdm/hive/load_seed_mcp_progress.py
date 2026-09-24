#!/usr/bin/env python3
"""Track/resume XUnternehmen seed load via MCP execute_ddl (no credentials in script).

Splits xunternehmen_seed_large.sql using run_hive_sql.split_sql, then writes
250-row chunks under kdm/hive/.chunks250/ for MCP execute_ddl calls.

Usage:
  python kdm/hive/load_seed_mcp_progress.py prepare   # split seed into chunks
  python kdm/hive/load_seed_mcp_progress.py status    # show progress
  python kdm/hive/load_seed_mcp_progress.py next      # print next chunk SQL
  python kdm/hive/load_seed_mcp_progress.py mark N    # mark chunk N done
  python kdm/hive/load_seed_mcp_progress.py mark-range START END  # mark chunks done
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "kdm/hive/xunternehmen_seed_large.sql"
CHUNKS = REPO / "kdm/hive/.chunks250"
PROGRESS = REPO / "kdm/hive/.load_progress.json"


def split_sql(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    parts = re.split(r";\s*\n", body)
    return [p.strip() for p in parts if p.strip()]


def split_insert(stmt: str, chunk_size: int = 250) -> list[str]:
    m = re.match(r"(INSERT INTO \S+ \([^)]+\) VALUES)\s*(.*)", stmt, re.DOTALL | re.IGNORECASE)
    if not m:
        return [stmt]
    header, values_blob = m.group(1), m.group(2).strip()
    rows = re.findall(r"\([^)]*\)", values_blob)
    chunks: list[str] = []
    for i in range(0, len(rows), chunk_size):
        part = ",\n  ".join(rows[i : i + chunk_size])
        chunks.append(f"{header}\n  {part}")
    return chunks


def prepare() -> None:
    CHUNKS.mkdir(exist_ok=True)
    idx = 0
    statements = split_sql(SEED.read_text(encoding="utf-8"))
    for stmt in statements:
        for chunk in split_insert(stmt):
            (CHUNKS / f"{idx:04d}.sql").write_text(chunk, encoding="utf-8")
            idx += 1
    PROGRESS.write_text(
        json.dumps({"next_chunk": 0, "total_chunks": idx, "statements": len(statements)}, indent=2),
        encoding="utf-8",
    )
    print(f"Prepared {idx} chunks from {len(statements)} statements")


def load_progress() -> dict:
    if PROGRESS.is_file():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"next_chunk": 0, "total_chunks": 0, "statements": 0}


def status() -> None:
    p = load_progress()
    done = p.get("next_chunk", 0)
    total = p.get("total_chunks", 0)
    stmts_equiv = done // 2
    print(f"Chunks: {done}/{total} ({100 * done / total:.1f}%)" if total else "Not prepared")
    print(f"~Statements: {stmts_equiv}/{p.get('statements', 191)}")


def next_chunk() -> None:
    p = load_progress()
    idx = p.get("next_chunk", 0)
    total = p.get("total_chunks", 0)
    if idx >= total:
        print("All chunks loaded.", file=sys.stderr)
        sys.exit(0)
    path = CHUNKS / f"{idx:04d}.sql"
    if not path.is_file():
        print(f"Missing chunk file: {path}", file=sys.stderr)
        sys.exit(1)
    print(path.read_text(encoding="utf-8"), end="")


def mark_done(idx: int | None = None) -> None:
    p = load_progress()
    if idx is None:
        idx = p.get("next_chunk", 0)
    p["next_chunk"] = idx + 1
    PROGRESS.write_text(json.dumps(p, indent=2), encoding="utf-8")
    if (idx + 1) % 40 == 0:
        print(f"Progress: chunk {idx + 1}/{p['total_chunks']}")


def mark_range(start: int, end: int) -> None:
    """Mark chunks start..end inclusive as done (next_chunk = end + 1)."""
    p = load_progress()
    expected = p.get("next_chunk", 0)
    if start != expected:
        print(f"Warning: expected next_chunk {expected}, marking from {start}", file=sys.stderr)
    p["next_chunk"] = end + 1
    PROGRESS.write_text(json.dumps(p, indent=2), encoding="utf-8")
    print(f"Marked chunks {start}-{end} done; next_chunk={end + 1}")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "prepare":
        prepare()
    elif cmd == "status":
        status()
    elif cmd == "next":
        next_chunk()
    elif cmd == "mark":
        mark_done(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "mark-range":
        mark_range(int(sys.argv[2]), int(sys.argv[3]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
