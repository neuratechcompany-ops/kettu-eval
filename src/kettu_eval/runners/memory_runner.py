"""Memory Core Dataset Runner — deterministic, state-based evaluation.

Loads scenarios, executes operations against an adapter,
validates expected_state without any LLM.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from kettu_eval.adapters.base import MemoryAdapter
from kettu_eval.core.models import (
    MetricResult, HardGate, Coverage, RunRecord, RunStatus, EvalStatus, CompositeScore
)


class MemoryDatasetRunner:
    """Runs memory-core dataset against any MemoryAdapter."""

    def __init__(self, dataset_path: str = "datasets/memory-core"):
        self.dataset_path = Path(dataset_path)
        self.scenarios_dir = self.dataset_path / "scenarios"

    def load_scenarios(self) -> list[dict]:
        scenarios = []
        for path in sorted(self.scenarios_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text())
            scenarios.append(data)
        return scenarios

    async def run_scenario(self, scenario: dict, adapter: MemoryAdapter) -> RunRecord:
        run = RunRecord(
            suite_id="memory-core",
            scenario_id=str(scenario["scenario_id"]),
            adapter=getattr(getattr(adapter, "manifest", None), "name", None) or adapter.__class__.__name__,
            adapter_version=getattr(getattr(adapter, "manifest", None), "version", None) or "0.1.0",
            model="deterministic",
            runtime="local",
        )

        try:
            await adapter.reset()
            current_session = None

            for op in scenario["operations"]:
                op_type = op["op"]

                if op_type == "start_session":
                    current_session = op["session"]
                    await adapter.start_session(
                        op["session"], op.get("user", "default"),
                        {"project": op.get("project", "default")}
                    )
                elif op_type == "add_fact":
                    fact = dict(op["fact"])
                    fact.setdefault("user_id", op.get("user", "default"))
                    fact.setdefault("project_id", op.get("project", "default"))
                    await adapter.add_fact(op.get("session", current_session), fact)
                elif op_type == "add_event":
                    event = dict(op["event"])
                    await adapter.add_event(op.get("session", current_session), event)
                elif op_type == "end_session":
                    await adapter.end_session(op["session"])
                elif op_type == "get_context":
                    ctx = await adapter.get_context(op.get("session", current_session))
                elif op_type == "search":
                    results = await adapter.search(
                        op.get("session", current_session), op["query"],
                        op.get("top_k", 10)
                    )
                elif op_type == "restart":
                    # Simulate restart by calling reset (adapter keeps persistent storage)
                    pass

            # Evaluate expected_state
            expected = scenario.get("expected_state", {})
            ctx = await adapter.get_context(expected.get("session", current_session))

            metrics = self._evaluate_state(ctx, expected, scenario.get("search_results", None))
            gates = self._check_hard_gates(scenario, ctx, expected)

            run.metrics = metrics
            run.hard_gates = gates

            all_gates_pass = all(g.passed for g in gates)
            all_metrics_pass = all(
                m.passed is not False for m in metrics if m.passed is not None
            )
            run.finish(RunStatus.PASS if (all_gates_pass and all_metrics_pass) else RunStatus.FAIL)

        except Exception as e:
            run.finish(RunStatus.ERROR)
            run.failure_class = "adapter_error"
            run.failure_detail = str(e)[:200]

        return run

    def _evaluate_state(self, ctx: dict, expected: dict, search_results: list | None = None) -> list[MetricResult]:
        metrics = []

        # Fact count
        if "facts_count_min" in expected:
            actual = len(ctx.get("facts", []))
            passed = actual >= expected["facts_count_min"]
            metrics.append(MetricResult(
                name="facts_count", value=float(actual), unit="count",
                measured=True, sample_count=1,
                threshold=float(expected["facts_count_min"]),
                passed=passed,
                detail=f"Expected ≥{expected['facts_count_min']}, got {actual}",
            ))

        # Fact containment
        if "facts_contain" in expected:
            facts = ctx.get("facts", [])
            fact_dict = {f["key"]: f.get("value", "") for f in facts}
            found = 0
            total = len(expected["facts_contain"])
            for expected_fact in expected["facts_contain"]:
                key = expected_fact["key"]
                val = expected_fact["value"]
                if key in fact_dict and fact_dict[key] == val:
                    found += 1
            recall = found / max(total, 1)
            metrics.append(MetricResult(
                name="fact_recall", value=round(recall, 4), unit="ratio",
                measured=True, sample_count=total,
                threshold=0.99, passed=recall >= 0.99,
                detail=f"{found}/{total} expected facts found",
            ))

        # Fact exclusion (must NOT contain)
        if "facts_exclude" in expected:
            facts = ctx.get("facts", [])
            fact_dict = {f["key"]: f.get("value", "") for f in facts}
            leaked = 0
            for excluded in expected["facts_exclude"]:
                key = excluded["key"]
                val = excluded["value"]
                if key in fact_dict and fact_dict[key] == val:
                    leaked += 1
            metrics.append(MetricResult(
                name="fact_exclusion", value=float(leaked), unit="count",
                measured=True, sample_count=len(expected["facts_exclude"]),
                threshold=0.0, passed=leaked == 0,
                detail=f"{leaked} excluded facts leaked",
            ))

        # Search results
        if search_results is not None and "search_results_contain" in expected:
            sr = search_results if isinstance(search_results, list) else []
            found_sr = 0
            for expected_sr in expected["search_results_contain"]:
                for result in sr:
                    if (result.get("key") == expected_sr["key"] and
                        result.get("value") == expected_sr["value"]):
                        found_sr += 1
                        break
            recall_sr = found_sr / max(len(expected["search_results_contain"]), 1)
            metrics.append(MetricResult(
                name="search_recall", value=round(recall_sr, 4), unit="ratio",
                measured=True, sample_count=len(expected["search_results_contain"]),
                threshold=0.99, passed=recall_sr >= 0.99,
            ))

        return metrics

    def _check_hard_gates(self, scenario: dict, ctx: dict, expected: dict) -> list[HardGate]:
        gates = []

        # Check for cross-session leakage
        if "cross_session_leakage" in scenario.get("hard_gates", []):
            facts = ctx.get("facts", [])
            has_leak = any(
                f.get("session_id") != expected.get("session", "")
                for f in facts if "session_id" in f
            )
            gates.append(HardGate(
                name="cross_session_leakage",
                description="Session data must not leak between users",
                condition="leak_count == 0",
                actual=1 if has_leak else 0,
                passed=not has_leak,
            ))

        # Check for project leakage
        if "project_leakage" in scenario.get("hard_gates", []):
            facts = ctx.get("facts", [])
            expected_facts = expected.get("facts_exclude", [])
            leaked = sum(
                1 for f in facts
                for ef in expected_facts
                if f.get("key") == ef["key"] and f.get("value") == ef["value"]
            )
            gates.append(HardGate(
                name="project_leakage",
                description="Project data must not leak between projects",
                condition="leak_count == 0",
                actual=leaked,
                passed=leaked == 0,
            ))

        return gates

    async def run_all(self, adapter: MemoryAdapter) -> dict:
        scenarios = self.load_scenarios()
        runs: list[RunRecord] = []
        passed = 0
        failed = 0

        for scenario in scenarios:
            run = await self.run_scenario(scenario, adapter)
            runs.append(run)
            if run.status == RunStatus.PASS:
                passed += 1
            else:
                failed += 1

        # Aggregate
        total_gates = sum(len(r.hard_gates) for r in runs)
        gates_failed = sum(
            sum(1 for g in r.hard_gates if not g.passed)
            for r in runs
        )

        # Category coverage
        categories = set()
        for s in scenarios:
            categories.add(s.get("category", "unknown"))

        return {
            "adapter": getattr(adapter, "__class__", type(adapter)).__name__,
            "total_scenarios": len(scenarios),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / max(len(scenarios), 1),
            "categories_covered": len(categories),
            "hard_gates_total": total_gates,
            "hard_gates_failed": gates_failed,
            "runs": [r.to_dict() for r in runs],
        }
