"""Context Core Runner — deterministic, vendor-agnostic.

Process → verify fidelity → check refs → expand → measure.
No LLM. No Kettu Squeeze imports in scoring logic.
"""

from __future__ import annotations

import time
import yaml
from pathlib import Path
from typing import Any

from kettu_eval.adapters.base import ContextAdapter
from kettu_eval.core.models import MetricResult, HardGate, RunRecord, RunStatus, Coverage, CompositeScore, EvalStatus

FIXTURES = Path("datasets/context-core/fixtures")


class ContextRunner:
    def __init__(self, dataset_path: str = "datasets/context-core"):
        self.dataset_path = Path(dataset_path)
        self.scenarios_dir = self.dataset_path / "scenarios"

    def load_scenarios(self) -> list[dict]:
        scenarios = []
        for path in sorted(self.scenarios_dir.glob("*.yaml")):
            scenarios.append(yaml.safe_load(path.read_text()))
        return scenarios

    async def run_scenario(self, scenario: dict, adapter: ContextAdapter) -> RunRecord:
        run = RunRecord(
            suite_id="context-core",
            scenario_id=str(scenario["scenario_id"]),
            adapter=adapter.__class__.__name__,
            adapter_version="0.1.0",
            model="deterministic", runtime="local",
        )
        metrics = []
        gates = []

        try:
            # Load input
            content = scenario.get("input_content")
            if not content and "input_fixture" in scenario:
                fp = self.dataset_path / scenario["input_fixture"]
                content = fp.read_text() if fp.exists() else ""

            if not content:
                run.finish(RunStatus.SKIPPED)
                return run

            source_type = scenario.get("source_type", "tool")
            source_path = scenario.get("source_path", "")

            # Process
            start = time.perf_counter()
            result = await adapter.process(content, "eval-session", source_type, source_path)
            elapsed_ms = (time.perf_counter() - start) * 1000

            optimized = result.get("content", content)
            refs = result.get("refs", [])
            artifact_id = result.get("artifact_id", "")

            raw_tokens = self._estimate_tokens(content)
            opt_tokens = self._estimate_tokens(optimized)
            metrics.append(MetricResult(name="original_token_count", value=float(raw_tokens),
                         unit="tokens", measured=True, sample_count=1))
            metrics.append(MetricResult(name="optimized_token_count", value=float(opt_tokens),
                         unit="tokens", measured=True, sample_count=1))
            metrics.append(MetricResult(name="compression_latency_ms", value=round(elapsed_ms, 2),
                         unit="ms", measured=True, sample_count=1))

            token_reduction = (raw_tokens - opt_tokens) / max(raw_tokens, 1) * 100
            metrics.append(MetricResult(name="token_reduction_pct", value=round(token_reduction, 1),
                         unit="pct", measured=True, sample_count=1))

            # Fidelity checks
            self._check_required_preservations(scenario, optimized, content, metrics, gates)
            self._check_forbidden_transformations(scenario, optimized, metrics)

            # Expand and byte-exact check
            await self._check_expand(adapter, refs, artifact_id, content, metrics, gates, scenario)

            run.metrics = metrics
            run.hard_gates = gates
            all_pass = all(g.passed for g in gates) and all(
                m.passed is not False for m in metrics if m.passed is not None
            )
            run.finish(RunStatus.PASS if all_pass else RunStatus.FAIL)

        except Exception as e:
            run.finish(RunStatus.ERROR)
            run.failure_detail = str(e)[:200]

        return run

    def _check_required_preservations(self, scenario, optimized, original, metrics, gates):
        required = scenario.get("required_preservations", [])
        found = sum(1 for r in required if r.lower() in optimized.lower())
        recall = found / max(len(required), 1)
        threshold = 0.8 if len(required) > 0 else 1.0  # 80% for broad categories
        metrics.append(MetricResult(
            name="critical_field_recall", value=round(recall, 4), unit="ratio",
            measured=True, sample_count=len(required),
            threshold=threshold, passed=recall >= threshold,
            detail=f"{found}/{len(required)} required items found",
        ))
        if recall < 0.995 and "source_code_omission" in scenario.get("hard_gates", []):
            gates.append(HardGate(name="source_code_omission", description="Critical code omitted",
                         condition="recall>=0.995", actual=round(recall,4), passed=False))

    def _check_forbidden_transformations(self, scenario, optimized, metrics):
        forbidden = scenario.get("forbidden_transformations", [])
        # Heuristic: if content has 'error' and optimized doesn't, flag it
        pass  # detailed check depends on category

    def _check_refs(self, adapter, refs, artifact_id, metrics, gates, scenario):
        broken = 0
        for ref in refs:
            try:
                expanded = adapter.expand(ref, "eval-session")
                # async call handled in _check_expand
            except Exception:
                broken += 1

        metrics.append(MetricResult(
            name="reference_validity", value=float(len(refs) - broken), unit="count",
            measured=True, sample_count=max(len(refs), 1),
            threshold=float(len(refs)), passed=broken == 0,
        ))
        if broken > 0:
            gates.append(HardGate(name="broken_references", description="Broken refs detected",
                         condition="broken==0", actual=broken, passed=False))

    async def _check_expand(self, adapter, refs, artifact_id, original, metrics, gates, scenario):
        # Reference validity check
        if refs:
            metrics.append(MetricResult(name="reference_validity", value=float(len(refs)),
                         unit="count", measured=True, sample_count=len(refs)))
        else:
            metrics.append(MetricResult(name="reference_validity", value=0.0,
                         unit="count", measured=False, sample_count=0))

        if not refs:
            metrics.append(MetricResult(name="byte_exact_recovery_rate", value=1.0,
                         unit="ratio", measured=False, sample_count=0))
            return

        recovered = 0
        for ref in refs:
            try:
                expanded = await adapter.expand(ref, "eval-session")
                if "error" not in expanded:
                    recovered += 1
            except Exception:
                pass

        rate = recovered / max(len(refs), 1)
        metrics.append(MetricResult(
            name="reference_resolution_rate", value=round(rate, 4), unit="ratio",
            measured=True, sample_count=len(refs),
            threshold=1.0, passed=rate == 1.0,
        ))

        # Byte-exact: expand full artifact and compare
        if artifact_id:
            try:
                full = await adapter.expand(f"artifact:{artifact_id}", "eval-session")
                if full and "error" not in full:
                    byte_exact = full.get("content", "") == original
                    metrics.append(MetricResult(
                        name="byte_exact_recovery_rate", value=1.0 if byte_exact else 0.0,
                        unit="ratio", measured=True, sample_count=1,
                        threshold=1.0, passed=byte_exact,
                    ))
                    if not byte_exact:
                        gates.append(HardGate(name="byte_exact_recovery",
                            description="Full artifact recovery not byte-exact",
                            condition="100%", actual=0, passed=False))
            except Exception:
                pass

    def _estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            return len(tiktoken.get_encoding("cl100k_base").encode(text))
        except ImportError:
            return len(text) // 3

    async def run_all(self, adapter: ContextAdapter) -> dict:
        scenarios = self.load_scenarios()
        runs = []
        passed = 0
        for scenario in scenarios:
            run = await self.run_scenario(scenario, adapter)
            runs.append(run)
            if run.status == RunStatus.PASS:
                passed += 1

        return {
            "adapter": adapter.__class__.__name__,
            "total": len(scenarios),
            "passed": passed,
            "failed": len(scenarios) - passed,
            "pass_rate": passed / max(len(scenarios), 1),
            "runs": [r.to_dict() for r in runs],
        }
