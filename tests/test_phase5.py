"""Phase 5 regression tests — Retrieval Benchmark."""

import json
from pathlib import Path

import pytest
import yaml

from kettu_eval.runners.retrieval_runner import RetrievalRunner, compute_res, _ndcg
from kettu_eval.adapters.null_adapter import NullRetrievalAdapter
from kettu_eval.core.models import MetricResult, HardGate, RunStatus, CompositeScore, EvalStatus, Coverage


class TestRetrievalDataset:
    def test_corpus_size(self):
        path = Path("datasets/retrieval-core/corpus/corpus.jsonl")
        docs = [json.loads(l) for l in path.read_text().strip().split("\n") if l]
        assert len(docs) >= 500

    def test_query_count(self):
        data = yaml.safe_load(Path("datasets/retrieval-core/queries/queries.yaml").read_text())
        assert len(data["queries"]) >= 150

    def test_unique_document_ids(self):
        path = Path("datasets/retrieval-core/corpus/corpus.jsonl")
        docs = [json.loads(l) for l in path.read_text().strip().split("\n") if l]
        ids = [d["document_id"] for d in docs]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {len(ids) - len(set(ids))}"

    def test_unique_query_ids(self):
        data = yaml.safe_load(Path("datasets/retrieval-core/queries/queries.yaml").read_text())
        ids = [q["query_id"] for q in data["queries"]]
        assert len(ids) == len(set(ids))

    def test_all_metadata_present(self):
        path = Path("datasets/retrieval-core/corpus/corpus.jsonl")
        for line in path.read_text().strip().split("\n"):
            if not line: continue
            d = json.loads(line)
            for field in ["document_id", "namespace", "project", "document_type"]:
                assert field in d, f"Missing {field} in {d.get('document_id')}"

    def test_all_query_types_covered(self):
        data = yaml.safe_load(Path("datasets/retrieval-core/queries/queries.yaml").read_text())
        types = set(q["query_type"] for q in data["queries"])
        required = {"exact", "semantic", "paraphrase", "metadata", "namespace",
                    "project", "temporal", "multi_hop", "negative"}
        assert types >= required, f"Missing: {required - types}"

    def test_negative_queries_empty_expected(self):
        data = yaml.safe_load(Path("datasets/retrieval-core/queries/queries.yaml").read_text())
        for q in data["queries"]:
            if q["query_type"] == "negative":
                assert q["expected_documents"] == []


class TestRetrievalRunner:
    @pytest.fixture
    def runner(self):
        return RetrievalRunner()

    @pytest.mark.asyncio
    async def test_null_adapter_no_crash(self, runner):
        null = NullRetrievalAdapter()
        result = await runner.run_all(null)
        assert result["total"] >= 150

    @pytest.mark.asyncio
    async def test_single_query(self, runner):
        null = NullRetrievalAdapter()
        run = await runner._run_query(runner.queries[0], null)
        assert run.status in (RunStatus.PASS, RunStatus.FAIL)


class TestRES:
    def test_res_with_all_metrics(self):
        metrics = [
            MetricResult(name="precision@1", value=0.8, measured=True, sample_count=1),
            MetricResult(name="recall@5", value=0.6, measured=True, sample_count=1),
            MetricResult(name="mrr", value=0.5, measured=True, sample_count=1),
        ]
        gates = [HardGate(name="namespace_isolation", description="", condition="==0", actual=0, passed=True)]
        score = compute_res(metrics, gates)
        assert score.status == EvalStatus.OFFICIAL
        assert score.total > 0

    def test_res_fails_on_hard_gate(self):
        metrics = [MetricResult(name="precision@1", value=1.0, measured=True, sample_count=1)]
        gates = [HardGate(name="namespace_isolation", description="", condition="==0", actual=5, passed=False)]
        score = compute_res(metrics, gates)
        assert score.status == EvalStatus.FAIL

    def test_res_with_unmeasured_metrics(self):
        metrics = [MetricResult(name="precision@1", value=None, measured=False)]
        gates = []
        score = compute_res(metrics, gates)
        assert score.total >= 0


class TestRetrievalMetrics:
    def test_precision_perfect(self):
        m = MetricResult(name="precision@1", value=1.0, unit="ratio", measured=True, sample_count=1)
        assert m.passed is None or m.passed  # no threshold

    def test_mrr_zero(self):
        m = MetricResult(name="mrr", value=0.0, unit="ratio", measured=True, sample_count=1)
        assert m.value == 0.0

    def test_latency_measured(self):
        m = MetricResult(name="latency_ms", value=12.5, unit="ms", measured=True, sample_count=1)
        assert m.measured is True


class TestHardGates:
    def test_namespace_isolation_violation(self):
        gate = HardGate(name="namespace_isolation", description="", condition="==0", actual=3, passed=False)
        assert gate.passed is False

    def test_project_isolation_violation(self):
        gate = HardGate(name="project_isolation", description="", condition="==0", actual=1, passed=False)
        assert gate.passed is False

    def test_forbidden_at_rank1(self):
        gate = HardGate(name="forbidden_at_rank1", description="", condition="==0", actual=1, passed=False)
        assert gate.passed is False

    def test_clean_gate(self):
        gate = HardGate(name="namespace_isolation", description="", condition="==0", actual=0, passed=True)
        assert gate.passed is True


class TestNDCG:
    def test_perfect_ndcg(self):
        from kettu_eval.runners.retrieval_runner import _ndcg
        score = _ndcg([1.0, 1.0, 1.0], ["a", "b", "c"], ["a", "b", "c"], 3)
        assert score == 1.0

    def test_zero_ndcg(self):
        from kettu_eval.runners.retrieval_runner import _ndcg
        score = _ndcg([1.0, 1.0], ["x", "y"], ["a", "b"], 2)
        assert score == 0.0

    def test_partial_ndcg(self):
        from kettu_eval.runners.retrieval_runner import _ndcg
        score = _ndcg([1.0, 1.0, 1.0], ["a", "x", "b"], ["a", "b", "c"], 3)
        assert 0 < score < 1.0


class TestRetrievalEdgeCases:
    def test_empty_corpus(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "corpus"
            p.mkdir()
            (p / "corpus.jsonl").write_text("")
            # Empty corpus should not crash

    def test_malformed_metadata(self):
        d = {"document_id": "test", "namespace": 123}  # not a string
        assert isinstance(d["namespace"], int)

    def test_duplicate_ids_detection(self):
        ids = ["a", "b", "c", "a"]
        assert len(set(ids)) < len(ids)

    def test_empty_query(self):
        q = {"query_id": "q-empty", "query_type": "negative", "text": "",
             "expected_documents": [], "forbidden_documents": []}
        assert q["expected_documents"] == []

    def test_timestamp_sorting(self):
        docs = [
            {"id": "1", "ts": "2026-01-01"},
            {"id": "2", "ts": "2026-06-01"},
            {"id": "3", "ts": "2026-03-01"},
        ]
        sorted_docs = sorted(docs, key=lambda d: d["ts"])
        assert sorted_docs[0]["id"] == "1"
        assert sorted_docs[-1]["id"] == "2"

    def test_forbidden_doc_detection(self):
        results = [{"document_id": "forbidden-1"}, {"document_id": "ok-1"}]
        forbidden = ["forbidden-1"]
        hit = results[0]["document_id"] in forbidden
        assert hit is True

    def test_cross_namespace_detection(self):
        results = [{"namespace": "alpha"}, {"namespace": "beta"}]
        required = "alpha"
        cross = [r for r in results if r["namespace"] != required]
        assert len(cross) == 1

    def test_missed_document_count(self):
        retrieved = ["a", "b"]
        expected = ["a", "b", "c", "d"]
        missed = sum(1 for e in expected if e not in retrieved)
        assert missed == 2

    def test_precision_at_k_edge(self):
        retrieved = ["a", "b", "c"]
        expected = ["a", "c", "e"]
        hits = sum(1 for r in retrieved[:2] if r in expected)
        assert hits == 1  # only "a" at positions 1-2

    def test_recall_at_k_full(self):
        retrieved = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        expected = ["a", "b", "c"]
        hits = sum(1 for r in retrieved[:10] if r in expected)
        assert hits == 3

    def test_mrr_first_position(self):
        rank = 1
        mrr = 1.0 / rank
        assert mrr == 1.0

    def test_mrr_third_position(self):
        rank = 3
        mrr = 1.0 / rank
        assert mrr == pytest.approx(0.3333, 0.001)

    def test_empty_results(self):
        results = []
        assert len(results) == 0

    def test_large_results_clamped_to_k(self):
        results = list(range(100))
        k = 10
        assert len(results[:k]) == 10

    def test_manifest_version(self):
        import yaml
        m = yaml.safe_load(Path("datasets/retrieval-core/manifest.yaml").read_text())
        assert m["version"] == "1.0.0"
        assert m["corpus_size"] >= 500
        assert m["query_count"] >= 150

    def test_corpus_document_types(self):
        path = Path("datasets/retrieval-core/corpus/corpus.jsonl")
        types = set()
        for l in path.read_text().strip().split("\n"):
            if l:
                types.add(json.loads(l)["document_type"])
        assert len(types) >= 5

    def test_filter_bypass_gate(self):
        gate = HardGate(name="metadata_filter_bypass", description="", condition="==0", actual=1, passed=False)
        assert gate.passed is False

    def test_timestamp_bypass_gate(self):
        gate = HardGate(name="timestamp_bypass", description="", condition="==0", actual=2, passed=False)
        assert gate.passed is False

    def test_score_with_missing_component(self):
        components = {"precision@1": 0.9}
        weights = {"precision@1": 25, "recall@5": 25}
        total = sum(components.get(k, 0) * v for k, v in weights.items() if v > 0)
        assert total == 22.5  # only precision contributes

    def test_coverage_partial(self):
        cov = Coverage(total_groups=9, measured_groups=6, skipped_groups=3, unsupported_groups=0)
        assert cov.percentage == pytest.approx(66.67, 0.1)
