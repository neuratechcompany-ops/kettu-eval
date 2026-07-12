"""Tests for Kettu Eval — Phase 1 Core."""

import json
import tempfile
from pathlib import Path

import pytest

from kettu_eval.core.models import (
    MetricResult,
    HardGate,
    Coverage,
    RunRecord,
    RunConfig,
    RunStatus,
    EvalStatus,
    FailureClass,
    AdapterType,
    CompositeScore,
)
from kettu_eval.adapters.base import (
    AdapterManifest,
    MemoryAdapter,
    ContextAdapter,
    validate_manifest,
    validate_adapter_against_manifest,
)
from kettu_eval.adapters.null_adapter import (
    NullMemoryAdapter,
    NullContextAdapter,
    NullAgentAdapter,
    NullRetrievalAdapter,
)
from kettu_eval.storage.run_storage import RunStorage


# ═══════════════════════════════════════════════════════════════════════════════
# MetricResult Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetricResult:
    def test_measured_with_value(self):
        m = MetricResult(name="recall", value=0.94, measured=True, sample_count=100)
        assert m.value == 0.94
        assert m.measured is True
        assert m.sample_count == 100

    def test_unmeasured_sets_null(self):
        m = MetricResult(name="recall", value=0.94, measured=False)
        assert m.value is None
        assert m.measured is False

    def test_threshold_pass(self):
        m = MetricResult(name="recall", value=0.96, measured=True, threshold=0.9)
        assert m.passed is True

    def test_threshold_fail(self):
        m = MetricResult(name="recall", value=0.8, measured=True, threshold=0.9)
        assert m.passed is False

    def test_no_threshold_no_pass(self):
        m = MetricResult(name="latency", value=42.0, measured=True)
        assert m.passed is None

    def test_confidence_interval(self):
        m = MetricResult(
            name="recall", value=0.94, measured=True,
            sample_count=50, confidence_interval=(0.90, 0.97)
        )
        assert m.confidence_interval == (0.90, 0.97)

    def test_warnings(self):
        m = MetricResult(name="recall", value=0.5, warnings=["low sample count"])
        assert len(m.warnings) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# HardGate Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHardGate:
    def test_passing_gate(self):
        h = HardGate(name="broken_refs", description="No broken refs",
                     condition="value == 0", actual=0, passed=True)
        assert h.passed is True

    def test_failing_gate(self):
        h = HardGate(name="broken_refs", description="No broken refs",
                     condition="value == 0", actual=3, passed=False)
        assert h.passed is False
        assert h.actual == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Coverage Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoverage:
    def test_full_coverage(self):
        c = Coverage(total_groups=10, measured_groups=10,
                     skipped_groups=0, unsupported_groups=0)
        assert c.percentage == 100.0

    def test_partial_coverage(self):
        c = Coverage(total_groups=10, measured_groups=7,
                     skipped_groups=2, unsupported_groups=1)
        assert c.percentage == 70.0

    def test_empty(self):
        c = Coverage(total_groups=0, measured_groups=0,
                     skipped_groups=0, unsupported_groups=0)
        assert c.percentage == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# RunRecord Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunRecord:
    def test_creation(self):
        r = RunRecord(suite_id="memory-core", scenario_id="fact-retention-001",
                      adapter="kettu-mem", adapter_version="0.2.1",
                      model="deepseek-v4-pro", runtime="api", seed=42)
        assert r.run_id is not None
        assert r.status == RunStatus.PASS

    def test_finish_updates_timestamps(self):
        r = RunRecord()
        assert r.finished_at is None
        r.finish(RunStatus.PASS)
        assert r.finished_at is not None

    def test_to_dict(self):
        r = RunRecord(suite_id="test", scenario_id="s1", adapter="null",
                      adapter_version="0.1", model="test", runtime="local")
        d = r.to_dict()
        assert d["run_id"] == r.run_id
        assert d["suite_id"] == "test"
        assert d["status"] == "pass"

    def test_with_metrics(self):
        r = RunRecord()
        r.metrics = [
            MetricResult(name="recall", value=0.94, measured=True, sample_count=10),
            MetricResult(name="latency", value=None, measured=False),
        ]
        r.hard_gates = [
            HardGate(name="no_leak", description="", condition="==0", actual=0, passed=True),
        ]
        d = r.to_dict()
        assert len(d["metrics"]) == 2
        assert d["metrics"][0]["value"] == 0.94
        assert d["metrics"][1]["value"] is None
        assert len(d["hard_gates"]) == 1

    def test_failure_class(self):
        r = RunRecord(failure_class=FailureClass.ADAPTER_ERROR, failure_detail="timeout")
        d = r.to_dict()
        assert d["failure_class"] == "adapter_error"


# ═══════════════════════════════════════════════════════════════════════════════
# CompositeScore Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeScore:
    def test_compute_clean(self):
        components = {"retention": 0.9, "retrieval": 0.85, "isolation": 1.0}
        weights = {"retention": 0.4, "retrieval": 0.4, "isolation": 0.2}
        gates: list[HardGate] = []
        score = CompositeScore.compute("MES", components, weights, gates)
        assert score.total == pytest.approx(0.9 * 0.4 + 0.85 * 0.4 + 1.0 * 0.2)
        assert score.status == EvalStatus.OFFICIAL

    def test_hard_gate_fail(self):
        components = {"retention": 0.95}
        weights = {"retention": 1.0}
        gates = [HardGate(name="leak", description="", condition="==0", actual=1, passed=False)]
        score = CompositeScore.compute("MES", components, weights, gates)
        assert score.status == EvalStatus.FAIL
        assert "leak" in score.hard_gate_violations

    def test_partial_coverage(self):
        components = {"a": 1.0}
        weights = {"a": 1.0}
        gates: list[HardGate] = []
        cov = Coverage(total_groups=10, measured_groups=5, skipped_groups=3, unsupported_groups=2)
        score = CompositeScore.compute("MES", components, weights, gates, cov)
        assert score.status == EvalStatus.PARTIAL


# ═══════════════════════════════════════════════════════════════════════════════
# Adapter Manifest Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdapterManifest:
    def test_valid_manifest(self):
        m = AdapterManifest(
            name="test-adapter", version="0.1.0",
            adapter_type=AdapterType.MEMORY,
            capabilities={"add_event": True, "add_fact": False},
        )
        assert m.has_capability("add_event") is True
        assert m.has_capability("add_fact") is False
        assert m.has_capability("nonexistent") is False

    def test_validate_clean(self):
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.MEMORY
        )
        assert validate_manifest(m) == []

    def test_validate_issues(self):
        m = AdapterManifest(
            name="", version="", adapter_type=AdapterType.MEMORY
        )
        issues = validate_manifest(m)
        assert len(issues) >= 2

    def test_validate_capability_types(self):
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.MEMORY,
            capabilities={"bad_cap": "not_bool"}  # type: ignore
        )
        assert len(validate_manifest(m)) >= 1

    def test_unknown_adapter_type(self):
        m = AdapterManifest(
            name="test", version="1.0", adapter_type="invalid_type"  # type: ignore
        )
        issues = validate_manifest(m)
        assert any("unknown adapter_type" in i for i in issues)


# ═══════════════════════════════════════════════════════════════════════════════
# Null Adapter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNullAdapters:
    @pytest.mark.asyncio
    async def test_null_memory_health(self):
        a = NullMemoryAdapter()
        result = await a.health()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_null_memory_search_empty(self):
        a = NullMemoryAdapter()
        await a.start_session("s1", "u1", {})
        await a.add_fact("s1", {"key": "val"})
        results = await a.search("s1", "query")
        assert results == []

    @pytest.mark.asyncio
    async def test_null_memory_context_empty(self):
        a = NullMemoryAdapter()
        await a.start_session("s1", "u1", {})
        ctx = await a.get_context("s1")
        assert ctx["facts"] == []
        assert ctx["events"] == []

    @pytest.mark.asyncio
    async def test_null_context_passthrough(self):
        a = NullContextAdapter()
        result = await a.process("hello world", "s1", "file", "/test.txt")
        assert result["content"] == "hello world"
        assert result["lossy"] is False
        assert result["refs"] == []

    @pytest.mark.asyncio
    async def test_null_context_expand_error(self):
        a = NullContextAdapter()
        result = await a.expand("ref:123", "s1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_null_agent_fails(self):
        a = NullAgentAdapter()
        result = await a.run_task({"prompt": "test"}, "s1")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_null_retrieval_empty(self):
        a = NullRetrievalAdapter()
        await a.index([{"id": 1, "text": "hello"}])
        results = await a.query("hello")
        assert results == []

    @pytest.mark.asyncio
    async def test_null_adapters_reset_noop(self):
        for adapter in [NullMemoryAdapter(), NullContextAdapter(),
                        NullAgentAdapter(), NullRetrievalAdapter()]:
            await adapter.reset()  # must not raise


# ═══════════════════════════════════════════════════════════════════════════════
# Run Storage Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunStorage:
    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as td:
            s = RunStorage(td)
            r = RunRecord(suite_id="test", scenario_id="s1",
                         adapter="null", adapter_version="0.1",
                         model="test-model", runtime="local")
            s.write(r)
            assert s.count() == 1
            last = s.last()
            assert last["run_id"] == r.run_id
            assert last["suite_id"] == "test"

    def test_multiple_writes(self):
        with tempfile.TemporaryDirectory() as td:
            s = RunStorage(td)
            for i in range(5):
                r = RunRecord(suite_id=f"test-{i}", scenario_id="s1",
                             adapter="null", adapter_version="0.1",
                             model="test", runtime="local")
                s.write(r)
            assert s.count() == 5

    def test_clear(self):
        with tempfile.TemporaryDirectory() as td:
            s = RunStorage(td)
            s.write(RunRecord())
            s.clear()
            assert s.count() == 0

    def test_recovery_after_corrupt_line(self):
        with tempfile.TemporaryDirectory() as td:
            s = RunStorage(td)
            s.write(RunRecord(suite_id="good", scenario_id="s1",
                             adapter="null", adapter_version="0.1",
                             model="t", runtime="l"))
            # Append garbage
            with open(s._file, "a") as f:
                f.write("not valid json\n")
            s.write(RunRecord(suite_id="good2", scenario_id="s2",
                             adapter="null", adapter_version="0.1",
                             model="t", runtime="l"))
            records = s.read_all()
            assert len(records) == 2  # corrupt line skipped


# ═══════════════════════════════════════════════════════════════════════════════
# Enums Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnums:
    def test_adapter_types(self):
        assert AdapterType.MEMORY.value == "memory"
        assert AdapterType.CONTEXT.value == "context"
        assert AdapterType.AGENT.value == "agent"
        assert AdapterType.RETRIEVAL.value == "retrieval"

    def test_eval_status(self):
        assert EvalStatus.OFFICIAL.value == "official"
        assert EvalStatus.FAIL.value == "fail"

    def test_run_status(self):
        assert RunStatus.PASS.value == "pass"
        assert RunStatus.ERROR.value == "error"

    def test_failure_classes(self):
        assert FailureClass.TIMEOUT.value == "timeout"
        assert FailureClass.SYSTEM_ERROR.value == "system_error"


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_unicode_in_run_record(self):
        r = RunRecord(suite_id="test-Привет", scenario_id="s1-🎉",
                     adapter="null", adapter_version="0.1",
                     model="test", runtime="local")
        d = r.to_dict()
        assert "Привет" in d["suite_id"]

    def test_empty_metrics_list(self):
        r = RunRecord()
        d = r.to_dict()
        assert d["metrics"] == []

    def test_null_values_in_to_dict(self):
        r = RunRecord(failure_class=None, failure_detail=None)
        d = r.to_dict()
        assert d["failure_class"] is None
        assert d["failure_detail"] is None

    def test_composite_score_zero_components(self):
        score = CompositeScore.compute("MES", {}, {}, [])
        assert score.total == 0.0
        assert score.status == EvalStatus.OFFICIAL

    def test_adapter_manifest_minimal(self):
        m = AdapterManifest(name="min", version="0.1", adapter_type=AdapterType.CONTEXT)
        assert m.transport == "stdio"
        assert m.capabilities == {}
        assert m.limitations == []


# ═══════════════════════════════════════════════════════════════════════════════
# Composite Score Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeScoreEdgeCases:
    def test_all_hard_gates_pass(self):
        components = {"a": 0.8, "b": 0.9}
        weights = {"a": 0.5, "b": 0.5}
        gates = [
            HardGate(name="g1", description="", condition="==0", actual=0, passed=True),
            HardGate(name="g2", description="", condition="==0", actual=0, passed=True),
        ]
        score = CompositeScore.compute("MES", components, weights, gates)
        assert score.status == EvalStatus.OFFICIAL

    def test_mixed_gates_one_fail(self):
        components = {"a": 0.95}
        weights = {"a": 1.0}
        gates = [
            HardGate(name="g1", description="", condition="", actual=0, passed=True),
            HardGate(name="g2", description="", condition="", actual=1, passed=False),
        ]
        score = CompositeScore.compute("MES", components, weights, gates)
        assert score.status == EvalStatus.FAIL

    def test_missing_component_weight_zero(self):
        components = {"a": 1.0}
        weights = {"a": 0.5, "missing": 0.5}
        gates: list[HardGate] = []
        score = CompositeScore.compute("MES", components, weights, gates)
        assert score.total == 0.5  # only 'a' contributes


# ═══════════════════════════════════════════════════════════════════════════════
# Contract Audit Regression Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestContractAudit:
    """Tests added during Phase 1 contract audit to prevent regression."""

    def test_capability_dependency_validation(self):
        """F1: compression=True requires process=True."""
        from kettu_eval.adapters.base import validate_capability_dependencies
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.CONTEXT,
            capabilities={"compression": True}  # missing 'process'
        )
        issues = validate_capability_dependencies(m)
        assert len(issues) >= 1
        assert any("process" in i for i in issues)

    def test_capability_dependency_clean(self):
        """All dependencies satisfied → no issues."""
        from kettu_eval.adapters.base import validate_capability_dependencies
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.CONTEXT,
            capabilities={"compression": True, "process": True}
        )
        assert validate_capability_dependencies(m) == []

    def test_recoverable_refs_requires_expand(self):
        """recoverable_refs → expand required."""
        from kettu_eval.adapters.base import validate_capability_dependencies
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.CONTEXT,
            capabilities={"recoverable_refs": True, "process": True}  # missing expand
        )
        issues = validate_capability_dependencies(m)
        assert any("expand" in i for i in issues)

    def test_semantic_search_requires_search(self):
        """semantic_search → search required."""
        from kettu_eval.adapters.base import validate_capability_dependencies
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.MEMORY,
            capabilities={"semantic_search": True}  # missing search
        )
        issues = validate_capability_dependencies(m)
        assert any("search" in i for i in issues)

    def test_adapter_method_validation(self):
        """F3: declared capability → matching method required."""
        from kettu_eval.adapters.base import validate_adapter_methods, _has_method
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.CONTEXT,
            capabilities={"compression": True, "process": True}
        )

        # ContextAdapter's process() is abstract → _has_method returns False
        # NullContextAdapter's process() is concrete → _has_method returns True
        assert not _has_method(ContextAdapter, "process")
        assert _has_method(NullContextAdapter, "process")

    @pytest.mark.asyncio
    async def test_optional_methods_no_longer_raise(self):
        """F4: update_fact/delete_fact return False, not NotImplementedError."""
        adapter = NullMemoryAdapter()
        result = await adapter.update_fact("id", {"key": "val"})
        assert result is False
        result = await adapter.delete_fact("id")
        assert result is False

    def test_hard_gate_overrides_score(self):
        """Regression: hard gate fail → FAIL regardless of score."""
        components = {"a": 1.0, "b": 1.0, "c": 1.0}
        weights = {"a": 0.34, "b": 0.33, "c": 0.33}
        gates = [
            HardGate(name="broken_refs", description="",
                     condition="==0", actual=5, passed=False)
        ]
        score = CompositeScore.compute("COS", components, weights, gates)
        assert score.status == EvalStatus.FAIL
        assert score.total > 0.9  # high score, but FAIL due to hard gate

    def test_partial_coverage_not_official(self):
        """5/10 suites → PARTIAL, not OFFICIAL."""
        cov = Coverage(total_groups=10, measured_groups=5,
                       skipped_groups=3, unsupported_groups=2)
        assert cov.percentage == 50.0
        components = {"a": 1.0}
        weights = {"a": 1.0}
        gates: list[HardGate] = []
        score = CompositeScore.compute("MES", components, weights, gates, cov)
        assert score.status == EvalStatus.PARTIAL

    def test_unmeasured_metric_is_null(self):
        """measured=false → value=null, never zero."""
        m = MetricResult(name="latency", measured=False)
        assert m.value is None
        assert m.measured is False
        # Verify it's not accidentally 0
        assert m.value != 0

    def test_malformed_manifest_rejected(self):
        """Empty name → validation fails."""
        m = AdapterManifest(name="", version="", adapter_type=AdapterType.MEMORY)
        issues = validate_manifest(m)
        assert len(issues) >= 2

    def test_cross_type_capability_not_leaked(self):
        """Memory capability 'compression' doesn't require context methods."""
        from kettu_eval.adapters.base import validate_capability_dependencies
        m = AdapterManifest(
            name="test", version="1.0", adapter_type=AdapterType.MEMORY,
            capabilities={"compression": True}  # memory can compress internally
        )
        # Memory has no dependency rules for 'compression' — should pass
        issues = validate_capability_dependencies(m)
        assert issues == []
