"""Simple SQLite Memory Adapter — minimal baseline.

No embeddings. No semantic search. No LLM. No compression.
Just SQLite with session/project namespaces.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from kettu_eval.adapters.base import MemoryAdapter
from kettu_eval.adapters.reference.error_mapping import (
    AdapterError,
    AdapterErrorCode,
    not_supported,
)
from kettu_eval.core.models import AdapterType


class SimpleSQLiteMemoryAdapter(MemoryAdapter):
    """Minimal SQLite-backed memory adapter.

    Capabilities: add_event, add_fact, search (exact), get_context,
                  start_session, end_session, fact_update, fact_delete,
                  session_isolation, restart_recovery.
    NOT supported: semantic_search, context_builder, compression, ttl.
    """

    def __init__(self, db_path: str | Path = ".kettu-eval/sqlite_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── DB Init ──────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    project_id TEXT DEFAULT 'default',
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    project_id TEXT DEFAULT 'default',
                    namespace TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_facts_session
                    ON facts(session_id, namespace);
                CREATE INDEX IF NOT EXISTS idx_facts_key
                    ON facts(key);
                CREATE INDEX IF NOT EXISTS idx_events_session
                    ON events(session_id, namespace);
            """)

    # ── Health / Reset ───────────────────────────────────────────────────

    async def health(self) -> dict:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1 FROM facts LIMIT 1")
            return {"status": "ok", "db_path": str(self.db_path)}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def reset(self) -> None:
        """Drop all data. Destructive — use only in test namespaces."""
        with self._connect() as conn:
            conn.execute("DELETE FROM facts")
            conn.execute("DELETE FROM events")

    # ── Session ──────────────────────────────────────────────────────────

    async def start_session(self, session_id: str, user_id: str, metadata: dict) -> None:
        """No-op: sessions are implicit in SQLite."""

    async def end_session(self, session_id: str) -> None:
        """No-op: sessions are implicit."""

    # ── Facts ────────────────────────────────────────────────────────────

    async def add_fact(self, session_id: str, fact: dict) -> str:
        fact_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        namespace = fact.get("_namespace", "default")
        user_id = fact.get("user_id", "default")
        project_id = fact.get("project_id", "default")

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO facts (id, session_id, user_id, project_id,
                   namespace, key, value, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fact_id, session_id, user_id, project_id, namespace,
                 fact["key"], fact["value"], now, now),
            )
        return fact_id

    async def add_event(self, session_id: str, event: dict) -> str:
        event_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        namespace = event.get("_namespace", "default")
        user_id = event.get("user_id", "default")
        project_id = event.get("project_id", "default")

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO events (id, session_id, user_id, project_id,
                   namespace, event_type, content, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, session_id, user_id, project_id, namespace,
                 event.get("type", "message"), event.get("content", ""), now),
            )
        return event_id

    # ── Search ───────────────────────────────────────────────────────────

    async def search(self, session_id: str, query: str, top_k: int = 10) -> list[dict]:
        """Exact substring match on fact key and value."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM facts
                   WHERE session_id = ?
                     AND (key LIKE ? OR value LIKE ?)
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (session_id, f"%{query}%", f"%{query}%", top_k),
            ).fetchall()

        return [{"id": r["id"], "key": r["key"], "value": r["value"],
                 "session_id": r["session_id"], "namespace": r["namespace"]}
                for r in rows]

    async def get_context(self, session_id: str) -> dict:
        with self._connect() as conn:
            facts = conn.execute(
                "SELECT * FROM facts WHERE session_id = ? ORDER BY updated_at DESC",
                (session_id,),
            ).fetchall()
            events = conn.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY created_at DESC LIMIT 100",
                (session_id,),
            ).fetchall()

        return {
            "session_id": session_id,
            "facts": [{"id": r["id"], "key": r["key"], "value": r["value"]} for r in facts],
            "events": [{"id": r["id"], "type": r["event_type"], "content": r["content"]}
                       for r in events],
        }

    # ── Updates / Deletes ───────────────────────────────────────────────

    async def update_fact(self, fact_id: str, updates: dict) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE facts SET value = ?, updated_at = ? WHERE id = ?",
                (updates.get("value", ""), now, fact_id),
            )
            return cur.rowcount > 0

    async def delete_fact(self, fact_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            return cur.rowcount > 0
