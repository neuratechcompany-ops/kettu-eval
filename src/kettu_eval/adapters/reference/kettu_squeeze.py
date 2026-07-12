"""Kettu Squeeze Adapter — in-process integration.

Requires: kettu-squeeze package installed.
Gracefully degrades if not available.
"""

from __future__ import annotations

from kettu_eval.adapters.base import ContextAdapter

try:
    from kettu_squeeze.api.engine import SqueezeEngine
    from kettu_squeeze.types import CompressionMode, CompressionRequest, ExpandRequest, SourceType
    SQUEEZE_AVAILABLE = True
except ImportError:
    SQUEEZE_AVAILABLE = False


class KettuSqueezeAdapter(ContextAdapter):
    """Adapter for Kettu Squeeze context optimization.

    Uses the SqueezeEngine directly (same process).
    """

    MODE_MAP = {
        "lossless": CompressionMode.LOSSLESS,
        "strict_raw": CompressionMode.STRICT_RAW,
        "recoverable_lossy": CompressionMode.RECOVERABLE_LOSSY,
    }

    def __init__(self):
        self.engine = SqueezeEngine()

    async def health(self) -> dict:
        try:
            self.engine.store.get("nonexistent")
            return {"status": "ok", "engine": "SqueezeEngine"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def reset(self) -> None:
        """Reset is per-session via context ledger eviction."""
        pass

    async def process(self, content: str, session_id: str,
                      source_type: str = "tool",
                      source_path: str | None = None) -> dict:
        st = SourceType.FILE if source_type == "file" else (
            SourceType.TOOL if source_type == "tool" else SourceType.API
        )
        resp = self.engine.compress(
            CompressionRequest(
                content=content, source_type=st,
                source_path=source_path, session_id=session_id,
                agent_id="kettu-eval", mode=CompressionMode.LOSSLESS,
            )
        )
        return {
            "content": resp.content,
            "artifact_id": resp.artifact_id,
            "mode": resp.mode.value,
            "lossy": resp.lossy,
            "recoverable": resp.recoverable,
            "original_tokens": resp.original_tokens,
            "compressed_tokens": resp.compressed_tokens,
            "compression_ratio": resp.compression_ratio,
            "refs": resp.refs,
            "verification_passed": resp.verification.passed,
        }

    async def expand(self, ref: str, session_id: str) -> dict:
        result = self.engine.expand(
            ExpandRequest(ref=ref, session_id=session_id)
        )
        if result is None:
            return {"error": f"Reference not found: {ref}", "ref": ref}
        return {
            "ref": ref,
            "artifact_id": result.artifact_id,
            "content": result.content,
            "line_range": result.line_range,
        }

    async def inspect(self, artifact_id: str) -> dict:
        record = self.engine.store.get(artifact_id)
        if record is None:
            return {"error": f"Artifact not found: {artifact_id}"}
        return {
            "artifact_id": record.artifact_id,
            "content_hash": record.content_hash,
            "source_type": record.source_type.value,
            "source_path": record.source_path,
            "session_id": record.session_id,
            "size_bytes": record.size_bytes,
        }

    async def get_context_status(self, session_id: str) -> dict:
        entries = self.engine.get_context(session_id)
        return {
            "session_id": session_id,
            "visible_entries": len(entries),
            "total_estimated_tokens": sum(e.estimated_tokens for e in entries),
        }
