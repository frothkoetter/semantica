"""Append-only JSONL writer for decision records."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple


def ensure_store_dir(store_root: str) -> None:
    os.makedirs(store_root, exist_ok=True)
    os.makedirs(os.path.join(store_root, "blobs"), exist_ok=True)


def jsonl_path(store_root: str) -> str:
    return os.path.join(store_root, "decisions.jsonl")


def maybe_offload_blob(
    store_root: str,
    field_name: str,
    value: Any,
    max_inline: int,
) -> Tuple[Any, Optional[str]]:
    """Write large values to blobs/ and return (inline_value, blob_ref key)."""
    if value is None:
        return None, None
    if isinstance(value, (dict, list)):
        serialized = json.dumps(value, sort_keys=True)
    else:
        serialized = str(value)
    if len(serialized) <= max_inline:
        return value, None
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    blob_name = f"{digest}.json"
    blob_path = os.path.join(store_root, "blobs", blob_name)
    if not os.path.exists(blob_path):
        with open(blob_path, "w", encoding="utf-8") as fh:
            fh.write(serialized)
    blob_key = f"{field_name}_blob_ref"
    return None, f"blobs/{blob_name}"


def append_record(store_root: str, record: Dict[str, Any]) -> Tuple[int, str]:
    """Append record to decisions.jsonl; return (byte_offset, jsonl_path)."""
    ensure_store_dir(store_root)
    path = jsonl_path(store_root)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    data = line.encode("utf-8")
    with open(path, "ab") as fh:
        offset = fh.tell()
        fh.write(data)
    return offset, path
