"""SQLite index for fast Decision Store lookups (embedded, no server)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
  decision_id       TEXT PRIMARY KEY,
  recorded_at       TEXT NOT NULL,
  category          TEXT,
  query_fingerprint TEXT,
  query_intent      TEXT,
  sql_hash          TEXT,
  business_rules_hash TEXT,
  outcome           TEXT,
  confidence        REAL,
  session_id        TEXT,
  supersedes        TEXT,
  json_line_offset  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fingerprint ON decisions(query_fingerprint, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_intent ON decisions(query_intent, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_category ON decisions(category, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_session ON decisions(session_id);
"""


def index_path(store_root: str) -> str:
    return os.path.join(store_root, "index.sqlite")


class DecisionIndex:
    def __init__(self, store_root: str, *, enabled: bool = True) -> None:
        self.store_root = store_root
        self.enabled = enabled
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(self.store_root, exist_ok=True)
            self._conn = sqlite3.connect(index_path(self.store_root))
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def upsert(self, record: Dict[str, Any], json_line_offset: int) -> None:
        if not self.enabled:
            return
        conn = self._connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO decisions (
              decision_id, recorded_at, category, query_fingerprint, query_intent,
              sql_hash, business_rules_hash, outcome, confidence, session_id,
              supersedes, json_line_offset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("decision_id"),
                record.get("recorded_at"),
                record.get("category"),
                record.get("query_fingerprint"),
                record.get("query_intent"),
                record.get("sql_hash"),
                record.get("business_rules_hash"),
                record.get("outcome"),
                record.get("confidence"),
                record.get("session_id"),
                record.get("supersedes"),
                json_line_offset,
            ),
        )
        conn.commit()

    def _cutoff_iso(self, lookback_days: Optional[int]) -> Optional[str]:
        if lookback_days is None or lookback_days <= 0:
            return None
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        return cutoff.isoformat().replace("+00:00", "Z")

    def find_by_fingerprint(
        self,
        fingerprint: str,
        *,
        limit: int = 5,
        exclude_id: Optional[str] = None,
        lookback_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        conn = self._connect()
        cutoff = self._cutoff_iso(lookback_days)
        sql = """
            SELECT decision_id, recorded_at, json_line_offset, query_fingerprint,
                   query_intent, sql_hash, business_rules_hash, outcome, confidence
            FROM decisions
            WHERE query_fingerprint = ?
        """
        params: List[Any] = [fingerprint]
        if exclude_id:
            sql += " AND decision_id != ?"
            params.append(exclude_id)
        if cutoff:
            sql += " AND recorded_at >= ?"
            params.append(cutoff)
        sql += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def find_by_intent(
        self,
        query_intent: str,
        *,
        limit: int = 5,
        exclude_id: Optional[str] = None,
        lookback_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        conn = self._connect()
        cutoff = self._cutoff_iso(lookback_days)
        sql = """
            SELECT decision_id, recorded_at, json_line_offset, query_fingerprint,
                   query_intent, sql_hash, business_rules_hash, outcome, confidence
            FROM decisions WHERE query_intent = ?
        """
        params: List[Any] = [query_intent]
        if exclude_id:
            sql += " AND decision_id != ?"
            params.append(exclude_id)
        if cutoff:
            sql += " AND recorded_at >= ?"
            params.append(cutoff)
        sql += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def find_by_category(
        self,
        category: str,
        *,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT decision_id, recorded_at, json_line_offset, query_fingerprint,
                   query_intent, outcome, confidence, category
            FROM decisions WHERE category = ?
            ORDER BY recorded_at DESC LIMIT ?
            """,
            (category, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_recent(
        self,
        *,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        conn = self._connect()
        if category:
            return self.find_by_category(category, limit=limit)
        rows = conn.execute(
            """
            SELECT decision_id, recorded_at, json_line_offset, query_fingerprint,
                   query_intent, outcome, confidence, category
            FROM decisions
            ORDER BY recorded_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def reindex_from_jsonl(self, jsonl: str) -> int:
        """Rebuild index from JSONL; return number of indexed records."""
        if not os.path.exists(jsonl):
            return 0
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        db = index_path(self.store_root)
        if os.path.exists(db):
            os.remove(db)
        count = 0
        with open(jsonl, "rb") as fh:
            while True:
                offset = fh.tell()
                line = fh.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                self.upsert(record, offset)
                count += 1
        return count
