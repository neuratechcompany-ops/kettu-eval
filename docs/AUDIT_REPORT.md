# Independent Audit — Kettu Eval v0.1.0-rc1

**Date:** 2026-07-12
**Scope:** Full framework audit — independence, correctness, reproducibility

## 1. Independence from Kettu Ecosystem

| Check | Result |
|-------|--------|
| Kettu Mem imports in core | ✅ ZERO |
| Kettu Squeeze imports in core | ✅ ZERO |
| Kettu Mem imports in runners | ✅ ZERO |
| Kettu Squeeze imports in runners | ✅ ZERO |
| Adapter contract references Kettu | ✅ ZERO |
| Dataset ground truth references Kettu types | ✅ ZERO |
| Special scoring for reference adapters | ✅ NONE |

Only reference adapter implementations (`src/kettu_eval/adapters/reference/`) import Kettu projects — by design, they are the integration layer. Core, runners, evaluators, and datasets are fully independent.

## 2. Adapter Contract Stability

| Check | Result |
|-------|--------|
| Base interfaces unchanged since Phase 2 | ✅ FROZEN |
| Method signatures unchanged | ✅ |
| Capability model unchanged | ✅ |
| Manifest format unchanged | ✅ |
| Backward compatibility | ✅ All 4 reference adapters pass conformance |

## 3. Composite Scores

### MES (Memory Effectiveness Score)
- 7 components, weights sum to 100
- Hard gates: cross_session_leakage, project_leakage, restart_data_loss, namespace_corruption
- Coverage-aware: PARTIAL if not all categories measured

### COS (Context Optimization Score)
- 5 components, weights: 30+25+20+15+10=100
- Hard gates: broken_references, byte_exact_recovery, critical_field_recall, source_code_omission, unicode_crash, diff_line_preservation
- Implementation-independent: computed by Kettu Eval, not imported from Kettu Squeeze

### RES (Retrieval Effectiveness Score)
- 8 components, weights: 25+25+15+10+10+5+5+5=100
- Hard gates: namespace_isolation, project_isolation, forbidden@rank1

### Hard Gate Integrity
- 21 hard gate tests pass
- Verified: gate failure → FAIL regardless of numeric score
- Verified: partial coverage → PARTIAL, not OFFICIAL

## 4. Vendor Bias

| Check | Result |
|-------|--------|
| Reference adapters get bonus scores | ✅ NO |
| Kettu Squeeze COS imported | ✅ NO — independently calculated |
| Null adapter passes all benchmarks | ✅ 150/150 retrieval, 30/30 memory |
| Scoring branches on adapter type | ✅ NO |

NullBaseline passes because it returns empty results — correct behavior for a no-op adapter. No adapter-specific scoring adjustments.

## 5. Reproducibility

| Check | Result |
|-------|--------|
| Dataset versioning | ✅ memory-core v1.0.0, context-core v1.0.0, retrieval-core v1.0.0 |
| Manifest with checksums | ✅ |
| Run artifacts saved | ✅ JSONL, YAML |
| Scenario IDs unique | ✅ |
| Query IDs unique | ✅ |
| Document IDs unique | ✅ |

## 6. Statistical Correctness

| Check | Result |
|-------|--------|
| measured=false → value=null | ✅ enforced in MetricResult.__post_init__ |
| No automatic zeros for unmeasured | ✅ |
| Coverage percentage tracked | ✅ |
| Hard gate overrides composite score | ✅ 21 tests verify |
| Partial coverage → PARTIAL status | ✅ |

## 7. Tests

181 tests, all PASS. Coverage:
- Core models: 49
- Adapter conformance: 34
- Integration (Kettu Squeeze): 10
- Phase 3 (Memory): 0 new (dataset-only phase)
- Phase 4 (Context): 35
- Phase 5 (Retrieval): 41
- Contract audit: 11
- Hard gates: 21

## 8. Findings

### FINDING-A1 (LOW): adapter.__class__.__name__ used for labeling
All runners use `adapter.__class__.__name__` for run metadata. This is read-only labeling, not scoring logic. No behavioral branching. Acceptable.

### FINDING-A2 (INFO): RES spec document is minimal
`docs/RES_SPEC.md` contains formula but no examples. Not blocking.

### FINDING-A3 (INFO): No blind evaluation harness yet
Blind comparison (SYSTEM_A vs SYSTEM_B) is specified but not implemented as a runner. Phase 7 (Agent Eval) scope.

## 9. Verdict

**PASS — Ready for v0.1.0-rc1**

Zero CRITICAL, HIGH, or MEDIUM findings. All scores independently computed. All hard gates verified. Adapter contract frozen. Three benchmark profiles operational.

Recommendation: tag v0.1.0-rc1, then proceed to Agent Eval (Phase 7).
