"""Null Baseline Adapter — returns nothing, remembers nothing.

Used as control baseline in all benchmark suites.
"""

from __future__ import annotations

from kettu_eval.adapters.base import (
    MemoryAdapter,
    ContextAdapter,
    AgentAdapter,
    RetrievalAdapter,
)


class NullMemoryAdapter(MemoryAdapter):
    """Remembers nothing. Search returns empty. All operations are no-ops."""

    async def health(self) -> dict:
        return {"status": "ok"}

    async def reset(self) -> None:
        pass

    async def start_session(self, session_id: str, user_id: str, metadata: dict) -> None:
        pass

    async def add_event(self, session_id: str, event: dict) -> str:
        return "null-event-0"

    async def add_fact(self, session_id: str, fact: dict) -> str:
        return "null-fact-0"

    async def search(self, session_id: str, query: str, top_k: int = 10) -> list[dict]:
        return []

    async def get_context(self, session_id: str) -> dict:
        return {"events": [], "facts": [], "session_id": session_id}

    async def end_session(self, session_id: str) -> None:
        pass


class NullContextAdapter(ContextAdapter):
    """Returns content unchanged. No compression. No refs."""

    async def health(self) -> dict:
        return {"status": "ok"}

    async def reset(self) -> None:
        pass

    async def process(self, content: str, session_id: str,
                      source_type: str, source_path: str | None = None) -> dict:
        return {
            "content": content,
            "artifact_id": "null-artifact",
            "mode": "raw",
            "lossy": False,
            "original_tokens": len(content) // 3,
            "compressed_tokens": len(content) // 3,
            "refs": [],
        }

    async def expand(self, ref: str, session_id: str) -> dict:
        return {"error": "null adapter has no artifacts", "ref": ref}

    async def inspect(self, artifact_id: str) -> dict:
        return {"error": "null adapter has no artifacts"}

    async def get_context_status(self, session_id: str) -> dict:
        return {"session_id": session_id, "visible_entries": 0}


class NullAgentAdapter(AgentAdapter):
    """Does nothing. All tasks fail."""

    async def health(self) -> dict:
        return {"status": "ok"}

    async def reset(self) -> None:
        pass

    async def run_task(self, task: dict, session_id: str) -> dict:
        return {"success": False, "output": "", "error": "null agent — no model"}

    async def reset_session(self, session_id: str) -> None:
        pass

    async def get_usage(self, session_id: str) -> dict:
        return {"input_tokens": 0, "output_tokens": 0}


class NullRetrievalAdapter(RetrievalAdapter):
    """Indexes nothing. Query returns empty."""

    async def health(self) -> dict:
        return {"status": "ok"}

    async def reset(self) -> None:
        pass

    async def index(self, documents: list[dict]) -> list[str]:
        return [f"null-doc-{i}" for i in range(len(documents))]

    async def query(self, query: str, top_k: int = 10,
                    filters: dict | None = None) -> list[dict]:
        return []

    async def delete(self, doc_ids: list[str]) -> int:
        return len(doc_ids)
