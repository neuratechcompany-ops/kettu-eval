"""Integration tests for reference adapters.

Kettu Squeeze: always available (in-process).
Kettu Mem: requires running server → skipped if unavailable.
"""

import pytest

from kettu_eval.adapters.reference.kettu_squeeze import KettuSqueezeAdapter


class TestKettuSqueezeAdapter:
    """Integration tests for Kettu Squeeze adapter (in-process)."""

    @pytest.fixture
    def adapter(self):
        return KettuSqueezeAdapter()

    @pytest.mark.asyncio
    async def test_health(self, adapter):
        result = await adapter.health()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_process_lossless(self, adapter):
        result = await adapter.process(
            "line1\nline2\nline2\nline2\nline3\n",
            "test-session", "tool", "test.log",
        )
        assert "content" in result
        assert result["artifact_id"] is not None
        assert result["lossy"] is False

    @pytest.mark.asyncio
    async def test_process_with_refs(self, adapter):
        """Content that produces recoverable refs."""
        long_content = "ERROR: fail\n" * 10
        result = await adapter.process(
            long_content, "test-refs", "tool", "error.log",
        )
        assert result["content"] is not None

    @pytest.mark.asyncio
    async def test_expand_valid_ref(self, adapter):
        result = await adapter.process("hello world", "test-exp", "file", "/test.txt")
        ref = f"artifact:{result['artifact_id']}"
        expanded = await adapter.expand(ref, "test-exp")
        assert expanded["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_expand_invalid_ref(self, adapter):
        result = await adapter.expand("artifact:deadbeef", "s1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_inspect_valid(self, adapter):
        result = await adapter.process("data", "test-inspect", "file", "/t.txt")
        info = await adapter.inspect(result["artifact_id"])
        assert info["source_path"] == "/t.txt"

    @pytest.mark.asyncio
    async def test_inspect_invalid(self, adapter):
        info = await adapter.inspect("nonexistent")
        assert "error" in info

    @pytest.mark.asyncio
    async def test_context_status(self, adapter):
        await adapter.process("data1", "test-ctx", "tool")
        await adapter.process("data2", "test-ctx", "tool")
        status = await adapter.get_context_status("test-ctx")
        assert status["visible_entries"] >= 2

    @pytest.mark.asyncio
    async def test_source_code_strict_raw(self, adapter):
        code = "def authenticate(user, password):\n    return user == 'admin'\n"
        result = await adapter.process(code, "test-src", "file", "/src/auth.py")
        # Source code defaults to STRICT_RAW — content preserved
        assert "def authenticate" in result["content"]

    @pytest.mark.asyncio
    async def test_byte_exact_recovery(self, adapter):
        content = "exact content for recovery test\n" * 5
        result = await adapter.process(content, "test-byte", "file", "/test.txt")
        expanded = await adapter.expand(f"artifact:{result['artifact_id']}", "test-byte")
        assert expanded["content"] == content

    @pytest.mark.asyncio
    async def test_context_isolation(self, adapter):
        await adapter.process("session-A-data", "session-A", "tool")
        await adapter.process("session-B-data", "session-B", "tool")
        ctx_a = await adapter.get_context_status("session-A")
        ctx_b = await adapter.get_context_status("session-B")
        # Each session has its own entries
        assert ctx_a["visible_entries"] >= 1
        assert ctx_b["visible_entries"] >= 1
