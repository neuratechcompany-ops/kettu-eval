"""Kettu Mem Adapter — HTTP transport to Kettu Mem server."""

from __future__ import annotations

import os
import json
import urllib.request
import urllib.error

from kettu_eval.adapters.base import MemoryAdapter


class KettuMemAdapter(MemoryAdapter):
    """Adapter for Kettu Mem via HTTP API.

    Requires KETTU_MEM_ENDPOINT env var (default: http://127.0.0.1:8765).
    """

    def __init__(self, endpoint: str | None = None):
        self.endpoint = (endpoint or os.environ.get("KETTU_MEM_ENDPOINT", "http://127.0.0.1:8765")).rstrip("/")
        self._timeout = 30

    async def health(self) -> dict:
        try:
            return self._get("/health")
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def reset(self) -> None:
        try:
            self._post("/reset", {})
        except Exception:
            pass  # best-effort reset

    async def start_session(self, session_id: str, user_id: str, metadata: dict) -> None:
        self._post("/session/start", {
            "session_id": session_id, "user_id": user_id, "metadata": metadata,
        })

    async def add_event(self, session_id: str, event: dict) -> str:
        result = self._post("/events/add", {
            "session_id": session_id, "event": event,
        })
        return result.get("event_id", "unknown")

    async def add_fact(self, session_id: str, fact: dict) -> str:
        result = self._post("/facts/add", {
            "session_id": session_id, "fact": fact,
        })
        return result.get("fact_id", "unknown")

    async def search(self, session_id: str, query: str, top_k: int = 10) -> list[dict]:
        result = self._post("/search", {
            "session_id": session_id, "query": query, "top_k": top_k,
        })
        return result.get("results", [])

    async def get_context(self, session_id: str) -> dict:
        return self._get(f"/context/{session_id}")

    async def end_session(self, session_id: str) -> None:
        self._post("/session/end", {"session_id": session_id})

    async def update_fact(self, fact_id: str, updates: dict) -> bool:
        result = self._post("/facts/update", {"fact_id": fact_id, "updates": updates})
        return result.get("updated", False)

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.endpoint}{path}")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: dict) -> dict:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{self.endpoint}{path}", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": str(e)}
        except Exception as e:
            return {"error": str(e)}
