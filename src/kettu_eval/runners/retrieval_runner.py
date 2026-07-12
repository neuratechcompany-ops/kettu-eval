"""Retrieval Runner — vendor-agnostic.

Indexes corpus via RetrievalAdapter, runs queries, evaluates against ground truth.
No LLM. No special adapter branches.
"""

from __future__ import annotations

import json, time, yaml
from pathlib import Path
from typing import Any

from kettu_eval.adapters.base import RetrievalAdapter
from kettu_eval.core.models import MetricResult, HardGate, RunRecord, RunStatus, CompositeScore, EvalStatus, Coverage


def _dcg(scores: list[float], k: int) -> float:
    import math
    return sum(s / math.log2(i + 2) for i, s in enumerate(scores[:k]))


def _ndcg(relevant: list[float], retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    ideal = sorted(relevant, reverse=True)
    idcg = _dcg(ideal, k)
    if idcg == 0:
        return 0.0
    retrieved_scores = [1.0 if rid in expected_ids else 0.0 for rid in retrieved_ids]
    return _dcg(retrieved_scores, k) / idcg


class RetrievalRunner:
    def __init__(self, dataset_path: str = "datasets/retrieval-core"):
        self.dataset_path = Path(dataset_path)
        self.corpus = self._load_corpus()
        self.queries = self._load_queries()

    def _load_corpus(self) -> list[dict]:
        path = self.dataset_path / "corpus" / "corpus.jsonl"
        if not path.exists():
            return []
        return [json.loads(l) for l in path.read_text().strip().split("\n") if l]

    def _load_queries(self) -> list[dict]:
        path = self.dataset_path / "queries" / "queries.yaml"
        if not path.exists():
            return []
        return yaml.safe_load(path.read_text())["queries"]

    async def run_all(self, adapter: RetrievalAdapter) -> dict:
        await adapter.reset()
        await adapter.index(self.corpus)

        runs = []
        for query in self.queries:
            run = await self._run_query(query, adapter)
            runs.append(run)

        passed = sum(1 for r in runs if r.status == RunStatus.PASS)
        return {
            "adapter": adapter.__class__.__name__,
            "total": len(self.queries),
            "passed": passed,
            "failed": len(self.queries) - passed,
            "runs": [r.to_dict() for r in runs],
        }

    async def _run_query(self, query: dict, adapter: RetrievalAdapter) -> RunRecord:
        run = RunRecord(
            suite_id="retrieval-core", scenario_id=query["query_id"],
            adapter=adapter.__class__.__name__, adapter_version="0.1.0",
            model="deterministic", runtime="local",
        )
        metrics = []
        gates = []

        try:
            filters = {}
            if query.get("required_namespace"):
                filters["namespace"] = query["required_namespace"]
            if query.get("required_project"):
                filters["project"] = query["required_project"]

            start = time.perf_counter()
            results = await adapter.query(query["text"], top_k=10, filters=filters or None)
            elapsed = (time.perf_counter() - start) * 1000

            expected = query.get("expected_documents", [])
            forbidden = query.get("forbidden_documents", [])
            retrieved_ids = [r.get("document_id", r.get("id", "")) for r in results]

            # Precision@k
            for k in [1, 3, 5]:
                top_k = retrieved_ids[:k]
                hits = sum(1 for rid in top_k if rid in expected)
                p = hits / k if k > 0 else 0.0
                metrics.append(MetricResult(name=f"precision@{k}", value=round(p, 4),
                    unit="ratio", measured=True, sample_count=1))

            # Recall@k
            for k in [5, 10]:
                top_k = retrieved_ids[:k]
                hits = sum(1 for rid in top_k if rid in expected)
                r = hits / max(len(expected), 1) if expected else (1.0 if hits == 0 else 0.0)
                metrics.append(MetricResult(name=f"recall@{k}", value=round(r, 4),
                    unit="ratio", measured=True, sample_count=1))

            # MRR
            for rank, rid in enumerate(retrieved_ids, 1):
                if rid in expected:
                    metrics.append(MetricResult(name="mrr", value=round(1.0/rank, 4),
                        unit="ratio", measured=True, sample_count=1))
                    break
            else:
                metrics.append(MetricResult(name="mrr", value=0.0, unit="ratio", measured=True, sample_count=1))

            # nDCG@10
            ndcg = _ndcg([1.0]*len(expected), retrieved_ids, expected, 10)
            metrics.append(MetricResult(name="ndcg@10", value=round(ndcg, 4),
                unit="ratio", measured=True, sample_count=1))

            # False retrieval & miss rate
            false_hits = sum(1 for rid in retrieved_ids if rid in forbidden)
            miss = 0 if not expected else sum(1 for eid in expected if eid not in retrieved_ids)
            metrics.append(MetricResult(name="false_retrieval_rate", value=float(false_hits),
                unit="count", measured=True, sample_count=1))
            metrics.append(MetricResult(name="miss_rate", value=float(miss),
                unit="count", measured=True, sample_count=1))

            # Latency
            metrics.append(MetricResult(name="latency_ms", value=round(elapsed, 2),
                unit="ms", measured=True, sample_count=1))

            # Hard gates
            if query.get("required_namespace"):
                cross_ns = [r for r in results if r.get("namespace") != query["required_namespace"]]
                gates.append(HardGate(name="namespace_isolation", description="Cross-namespace retrieval",
                    condition="==0", actual=len(cross_ns), passed=len(cross_ns)==0,
                    severity="blocking" if len(cross_ns)>0 else "warning"))

            if query.get("required_project"):
                cross_proj = [r for r in results if r.get("project") != query["required_project"]]
                gates.append(HardGate(name="project_isolation", description="Cross-project retrieval",
                    condition="==0", actual=len(cross_proj), passed=len(cross_proj)==0,
                    severity="blocking" if len(cross_proj)>0 else "warning"))

            if forbidden and retrieved_ids and retrieved_ids[0] in forbidden:
                gates.append(HardGate(name="forbidden_at_rank1", description="Forbidden doc at rank 1",
                    condition="==0", actual=1, passed=False))

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


def compute_res(metrics: list[MetricResult], gates: list[HardGate]) -> CompositeScore:
    """Compute Retrieval Effectiveness Score."""
    components = {}
    for m in metrics:
        if m.measured and m.value is not None:
            components[m.name] = m.value

    weights = {
        "precision@1": 25 / 3, "precision@3": 25 / 3, "precision@5": 25 / 3,
        "recall@5": 12.5, "recall@10": 12.5,
        "mrr": 10, "ndcg@10": 5,
        "false_retrieval_rate": -5, "miss_rate": -5,
        "latency_ms": 5,
    }
    # Normalize: all positive components contribute 0-1, negative reduce
    total = sum(components.get(k, 0) * v for k, v in weights.items() if v > 0)
    total -= sum(components.get(k, 0) * abs(v) for k, v in weights.items() if v < 0)
    total = max(0, min(100, total))

    return CompositeScore(
        name="RES", total=round(total, 2), components=components, weights=weights,
        status=EvalStatus.OFFICIAL if all(g.passed for g in gates) else EvalStatus.FAIL,
        hard_gate_violations=[g.name for g in gates if not g.passed],
    )
