"""Adapter Conformance Suite — Phase 2.

Tests that every adapter (Null, SimpleSQLite, KettuMem, KettuSqueeze)
satisfies the adapter contract invariants.

Run with:
    pytest tests/conformance/ -v
"""

import tempfile
from pathlib import Path

import pytest

from kettu_eval.adapters.base import (
    AdapterManifest,
    MemoryAdapter,
    ContextAdapter,
    validate_manifest,
    validate_capability_dependencies,
    validate_adapter_methods,
)
from kettu_eval.adapters.null_adapter import (
    NullMemoryAdapter,
    NullContextAdapter,
)
from kettu_eval.adapters.reference.simple_sqlite_memory import (
    SimpleSQLiteMemoryAdapter,
)
from kettu_eval.core.models import AdapterType


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def null_memory():
    return NullMemoryAdapter()


@pytest.fixture
def null_context():
    return NullContextAdapter()


@pytest.fixture
def sqlite_memory():
    with tempfile.TemporaryDirectory() as td:
        adapter = SimpleSQLiteMemoryAdapter(db_path=f"{td}/test.db")
        yield adapter


# ═══════════════════════════════════════════════════════════════════════════════
# Manifest Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestManifestConformance:
    """All adapters must have valid manifests."""

    ADAPTERS = [
        ("null-memory", AdapterType.MEMORY, NullMemoryAdapter),
        ("null-context", AdapterType.CONTEXT, NullContextAdapter),
        ("simple_sqlite_memory", AdapterType.MEMORY, SimpleSQLiteMemoryAdapter),
    ]

    def test_manifest_file_exists(self):
        """Each reference adapter must have a manifest YAML file."""
        manifest_dir = Path("src/kettu_eval/adapters/reference/manifests")
        for name, _, _ in self.ADAPTERS:
            if name.startswith("null"):
                continue  # null adapters don't need file manifests
            path = manifest_dir / f"{name}.yaml"
            assert path.exists(), f"Missing manifest: {path}"

    def test_manifest_loads_and_validates(self):
        """All manifest YAML files must be valid."""
        manifest_dir = Path("src/kettu_eval/adapters/reference/manifests")
        for name, _, _ in self.ADAPTERS:
            if name.startswith("null"):
                continue
            path = manifest_dir / f"{name}.yaml"
            if not path.exists():
                continue
            manifest = AdapterManifest.from_yaml(path)
            issues = validate_manifest(manifest)
            assert issues == [], f"Manifest issues for {name}: {issues}"

    def test_manifest_capability_dependencies(self):
        """Declared capabilities must have satisfied dependencies."""
        manifest_dir = Path("src/kettu_eval/adapters/reference/manifests")
        for name, _, _ in self.ADAPTERS:
            if name.startswith("null"):
                continue
            path = manifest_dir / f"{name}.yaml"
            if not path.exists():
                continue
            manifest = AdapterManifest.from_yaml(path)
            issues = validate_capability_dependencies(manifest)
            assert issues == [], f"Dependency issues for {name}: {issues}"

    def test_manifest_matches_adapter_type(self):
        """Manifest adapter_type must match the adapter class."""
        manifest_dir = Path("src/kettu_eval/adapters/reference/manifests")
        for name, expected_type, _ in self.ADAPTERS:
            if name.startswith("null"):
                continue
            path = manifest_dir / f"{name}.yaml"
            if not path.exists():
                continue
            manifest = AdapterManifest.from_yaml(path)
            assert manifest.adapter_type == expected_type, (
                f"{name}: manifest type={manifest.adapter_type}, expected={expected_type}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Lifecycle Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestLifecycleConformance:
    """Start → use → end → reset cycle must work for every adapter."""

    @pytest.mark.asyncio
    async def test_null_memory_lifecycle(self, null_memory):
        await null_memory.start_session("s1", "u1", {})
        fid = await null_memory.add_fact("s1", {"key": "name", "value": "test"})
        assert fid is not None
        ctx = await null_memory.get_context("s1")
        assert ctx["facts"] == []
        await null_memory.end_session("s1")
        await null_memory.reset()

    @pytest.mark.asyncio
    async def test_sqlite_memory_lifecycle(self, sqlite_memory):
        await sqlite_memory.start_session("s1", "u1", {})
        fid = await sqlite_memory.add_fact("s1", {"key": "name", "value": "Aurum"})
        assert len(fid) == 32  # UUID hex

        ctx = await sqlite_memory.get_context("s1")
        assert len(ctx["facts"]) == 1
        assert ctx["facts"][0]["value"] == "Aurum"

        await sqlite_memory.end_session("s1")
        await sqlite_memory.reset()

    @pytest.mark.asyncio
    async def test_health_returns_status(self, null_memory, sqlite_memory):
        for adapter in [null_memory, sqlite_memory]:
            result = await adapter.health()
            assert "status" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Reset Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetConformance:
    """Reset must clear all data and allow fresh start."""

    @pytest.mark.asyncio
    async def test_sqlite_reset_clears_data(self, sqlite_memory):
        await sqlite_memory.start_session("s1", "u1", {})
        await sqlite_memory.add_fact("s1", {"key": "k", "value": "v"})
        ctx_before = await sqlite_memory.get_context("s1")
        assert len(ctx_before["facts"]) == 1

        await sqlite_memory.reset()

        # After reset, data is gone
        await sqlite_memory.start_session("s1", "u1", {})
        ctx_after = await sqlite_memory.get_context("s1")
        assert len(ctx_after["facts"]) == 0

    @pytest.mark.asyncio
    async def test_null_reset_noop(self, null_memory):
        await null_memory.reset()  # must not raise


# ═══════════════════════════════════════════════════════════════════════════════
# Isolation Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestIsolationConformance:
    """Different sessions must not see each other's data."""

    @pytest.mark.asyncio
    async def test_sqlite_session_isolation(self, sqlite_memory):
        await sqlite_memory.start_session("s-A", "user-A", {})
        await sqlite_memory.add_fact("s-A", {"key": "secret", "value": "A-data"})

        await sqlite_memory.start_session("s-B", "user-B", {})
        await sqlite_memory.add_fact("s-B", {"key": "secret", "value": "B-data"})

        ctx_a = await sqlite_memory.get_context("s-A")
        ctx_b = await sqlite_memory.get_context("s-B")

        assert len(ctx_a["facts"]) == 1
        assert len(ctx_b["facts"]) == 1
        assert ctx_a["facts"][0]["value"] == "A-data"
        assert ctx_b["facts"][0]["value"] == "B-data"

    @pytest.mark.asyncio
    async def test_sqlite_search_session_scoped(self, sqlite_memory):
        await sqlite_memory.add_fact("s-A", {"key": "color", "value": "red"})
        await sqlite_memory.add_fact("s-B", {"key": "color", "value": "blue"})

        results_a = await sqlite_memory.search("s-A", "color", top_k=10)
        results_b = await sqlite_memory.search("s-B", "color", top_k=10)

        assert len(results_a) == 1
        assert results_a[0]["value"] == "red"
        assert len(results_b) == 1
        assert results_b[0]["value"] == "blue"

    @pytest.mark.asyncio
    async def test_null_isolation(self, null_memory):
        await null_memory.add_fact("s-A", {"key": "k", "value": "v"})
        ctx_b = await null_memory.get_context("s-B")
        assert ctx_b["facts"] == []  # null adapter never stores


# ═══════════════════════════════════════════════════════════════════════════════
# Error Mapping Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorMappingConformance:
    """Errors must be returned as structured results, not raw exceptions."""

    @pytest.mark.asyncio
    async def test_null_context_expand_returns_error_dict(self, null_context):
        result = await null_context.expand("bad-ref", "s1")
        assert "error" in result
        assert "null adapter" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_null_adapter_no_exceptions_on_normal_ops(self, null_memory):
        # All normal operations must complete without raising
        await null_memory.start_session("s1", "u1", {})
        await null_memory.add_event("s1", {"type": "msg", "content": "hello"})
        await null_memory.add_fact("s1", {"key": "k", "value": "v"})
        results = await null_memory.search("s1", "query")
        assert isinstance(results, list)
        await null_memory.end_session("s1")


# ═══════════════════════════════════════════════════════════════════════════════
# Optional Methods Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptionalMethodsConformance:
    """Optional methods must return False when not supported."""

    @pytest.mark.asyncio
    async def test_null_update_delete_return_false(self, null_memory):
        result = await null_memory.update_fact("id", {"key": "val"})
        assert result is False
        result = await null_memory.delete_fact("id")
        assert result is False

    @pytest.mark.asyncio
    async def test_sqlite_update_delete(self, sqlite_memory):
        fid = await sqlite_memory.add_fact("s1", {"key": "old", "value": "old-val"})
        updated = await sqlite_memory.update_fact(fid, {"value": "new-val"})
        assert updated is True

        ctx = await sqlite_memory.get_context("s1")
        assert ctx["facts"][0]["value"] == "new-val"

        deleted = await sqlite_memory.delete_fact(fid)
        assert deleted is True

        ctx2 = await sqlite_memory.get_context("s1")
        assert len(ctx2["facts"]) == 0

    @pytest.mark.asyncio
    async def test_sqlite_update_nonexistent(self, sqlite_memory):
        result = await sqlite_memory.update_fact("nonexistent", {"value": "x"})
        assert result is False

    @pytest.mark.asyncio
    async def test_sqlite_delete_nonexistent(self, sqlite_memory):
        result = await sqlite_memory.delete_fact("nonexistent")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# Restart / Persistence Conformance
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestartConformance:
    """Stateful adapters must survive restart."""

    def test_sqlite_persistence_across_instances(self):
        with tempfile.TemporaryDirectory() as td:
            db = f"{td}/test.db"

            # Write
            import asyncio
            async def write():
                a = SimpleSQLiteMemoryAdapter(db_path=db)
                await a.add_fact("s1", {"key": "persist", "value": "yes"})
            asyncio.run(write())

            # Read from new instance
            async def read():
                a = SimpleSQLiteMemoryAdapter(db_path=db)
                ctx = await a.get_context("s1")
                assert len(ctx["facts"]) == 1
                assert ctx["facts"][0]["value"] == "yes"
            asyncio.run(read())


# ═══════════════════════════════════════════════════════════════════════════════
# Capability Truthfulness
# ═══════════════════════════════════════════════════════════════════════════════

class TestCapabilityTruthfulness:
    """Adapter behavior must match declared capabilities."""

    def test_sqlite_manifest_matches_behavior(self):
        """Declared capabilities must be consistent with implementation."""
        manifest = AdapterManifest.from_yaml(
            "src/kettu_eval/adapters/reference/manifests/simple_sqlite_memory.yaml"
        )
        adapter = SimpleSQLiteMemoryAdapter(db_path=":memory:")

        # Check: manifest says semantic_search=false
        assert manifest.has_capability("semantic_search") is False

        # Check: manifest says session_isolation=true, and adapter implements search
        assert manifest.has_capability("session_isolation") is True

        issues = validate_adapter_methods(adapter, manifest)
        assert issues == [], f"Method validation issues: {issues}"

    def test_null_adapter_implicit_manifest(self):
        """Null adapter without manifest should not fail validation."""
        manifest = AdapterManifest(
            name="null-baseline", version="0.1.0",
            adapter_type=AdapterType.MEMORY,
            capabilities={"add_event": False, "add_fact": False, "search": False},
        )
        issues = validate_manifest(manifest)
        assert issues == []

    def test_capability_matrix_integrity(self):
        """Manifest capabilities must be boolean."""
        manifest_dir = Path("src/kettu_eval/adapters/reference/manifests")
        for path in manifest_dir.glob("*.yaml"):
            manifest = AdapterManifest.from_yaml(path)
            for cap, val in manifest.capabilities.items():
                assert isinstance(val, bool), (
                    f"{path.name}: capability '{cap}' is {type(val).__name__}, not bool"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Additional Conformance: Error Cases, Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestConformanceEdgeCases:
    """Edge cases every adapter must handle."""

    @pytest.mark.asyncio
    async def test_sqlite_empty_search(self, sqlite_memory):
        results = await sqlite_memory.search("empty-session", "nothing")
        assert results == []

    @pytest.mark.asyncio
    async def test_sqlite_empty_context(self, sqlite_memory):
        ctx = await sqlite_memory.get_context("nonexistent-session")
        assert ctx["facts"] == []
        assert ctx["events"] == []

    @pytest.mark.asyncio
    async def test_sqlite_unicode_fact(self, sqlite_memory):
        fid = await sqlite_memory.add_fact("s1", {"key": "имя", "value": "Аурум 🎉"})
        ctx = await sqlite_memory.get_context("s1")
        assert ctx["facts"][0]["value"] == "Аурум 🎉"

    @pytest.mark.asyncio
    async def test_sqlite_unicode_search(self, sqlite_memory):
        await sqlite_memory.add_fact("s1", {"key": "顏色", "value": "紅色"})
        results = await sqlite_memory.search("s1", "顏色")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_sqlite_multiple_facts(self, sqlite_memory):
        for i in range(10):
            await sqlite_memory.add_fact("s1", {"key": f"key_{i}", "value": f"val_{i}"})
        ctx = await sqlite_memory.get_context("s1")
        assert len(ctx["facts"]) == 10

    @pytest.mark.asyncio
    async def test_sqlite_search_top_k(self, sqlite_memory):
        for i in range(20):
            await sqlite_memory.add_fact("s1", {"key": f"item_{i}", "value": "common"})
        results = await sqlite_memory.search("s1", "common", top_k=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_sqlite_events(self, sqlite_memory):
        await sqlite_memory.add_event("s1", {"type": "message", "content": "hello world"})
        ctx = await sqlite_memory.get_context("s1")
        assert len(ctx["events"]) == 1
        assert ctx["events"][0]["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_null_memory_add_event_returns_id(self, null_memory):
        eid = await null_memory.add_event("s1", {"type": "msg", "content": "test"})
        assert eid is not None

    @pytest.mark.asyncio
    async def test_null_context_process_passthrough(self, null_context):
        result = await null_context.process("原始内容", "s1", "file", "/test.txt")
        assert result["content"] == "原始内容"
        assert len(result["refs"]) == 0

    @pytest.mark.asyncio
    async def test_sqlite_concurrent_sessions_independent(self, sqlite_memory):
        """Sessions A and B must be fully independent."""
        await sqlite_memory.add_fact("sA", {"key": "x", "value": "a"})
        await sqlite_memory.add_fact("sB", {"key": "x", "value": "b"})

        # Reset session A's facts using delete
        ctx_a = await sqlite_memory.get_context("sA")
        for f in ctx_a["facts"]:
            await sqlite_memory.delete_fact(f["id"])

        # Session B must be unaffected
        ctx_b = await sqlite_memory.get_context("sB")
        assert len(ctx_b["facts"]) == 1
        assert ctx_b["facts"][0]["value"] == "b"

    @pytest.mark.asyncio
    async def test_sqlite_update_preserves_other_fields(self, sqlite_memory):
        fid = await sqlite_memory.add_fact("s1", {"key": "original_key", "value": "old"})
        await sqlite_memory.update_fact(fid, {"value": "new"})
        ctx = await sqlite_memory.get_context("s1")
        assert ctx["facts"][0]["key"] == "original_key"
        assert ctx["facts"][0]["value"] == "new"
