"""Example: minimal custom MemoryAdapter — no Kettu imports required.

This shows how any third-party memory system can integrate with Kettu Eval.
"""

from __future__ import annotations
from kettu_eval.adapters.base import MemoryAdapter, AdapterManifest, AdapterType


class CustomMemoryAdapter(MemoryAdapter):
    """Example in-memory adapter — replace with your own system."""

    manifest = AdapterManifest(
        name="custom-memory",
        version="0.1.0",
        adapter_type=AdapterType.MEMORY,
        transport="direct",
        capabilities={
            "start_session": True,
            "add_fact": True,
            "add_event": False,
            "search": True,
            "get_context": True,
            "end_session": True,
            "reset": True,
            "semantic_search": False,
            "update_fact": True,
            "delete_fact": True,
            "add_event": False,
        },
    )

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._sessions: set[str] = set()

    async def start_session(self, session_id: str, user_id: str, metadata: dict = None):
        self._sessions.add(session_id)
        return {"session_id": session_id}

    async def add_fact(self, session_id: str, fact: dict):
        key = fact.get("key", str(hash(str(fact))))
        self._store[key] = fact
        return {"key": key}

    async def search(self, session_id: str, query: str, top_k: int = 10, filters: dict = None):
        results = []
        for key, fact in self._store.items():
            if query.lower() in str(fact).lower():
                results.append({"key": key, **fact})
        return results[:top_k]

    async def get_context(self, session_id: str):
        return {"facts": list(self._store.values()), "events": [], "session_id": session_id}

    async def end_session(self, session_id: str):
        self._sessions.discard(session_id)
        return {"session_id": session_id}

    async def update_fact(self, fact_id: str, updates: dict):
        if fact_id in self._store:
            self._store[fact_id].update(updates)
            return True
        return False

    async def delete_fact(self, fact_id: str):
        return self._store.pop(fact_id, None) is not None

    async def reset(self):
        self._store.clear()
        self._sessions.clear()
        return {"reset": True}

    async def health(self):
        return {"status": "ok", "facts": len(self._store), "sessions": len(self._sessions)}


# Example usage
if __name__ == "__main__":
    import asyncio

    async def demo():
        adapter = CustomMemoryAdapter()
        await adapter.start_session("s1", "user1")
        await adapter.add_fact("s1", {"key": "model", "value": "gpt-oss"})
        ctx = await adapter.get_context("s1")
        print(f"Context: {ctx}")
        results = await adapter.search("s1", "gpt")
        print(f"Search: {results}")
        await adapter.reset()
        print(f"After reset: {len((await adapter.get_context('s1'))['facts'])} facts")

    asyncio.run(demo())
