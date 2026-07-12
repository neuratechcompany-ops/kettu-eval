# Changelog

## v0.1.0 — 2026-07-12

### Added
- Core framework: adapter contract, data models, metric/hard-gate/coverage models
- Memory Core Benchmark (30 scenarios, 10 categories)
- Context Core Benchmark (43 scenarios, 9 categories)
- Retrieval Core Benchmark (506 documents, 150 queries, 9 query types)
- Composite scores: MES, COS, RES
- Reference adapters: NullBaseline, SimpleSQLiteMemory, KettuSqueeze, KettuMem
- Conformance suite (34 tests)
- CLI: doctor, adapters, datasets, validate
- JSONL run storage
- Dataset versioning and checksums
- Independent audit: 6 findings, 0 CRITICAL, 0 HIGH

### Known Limitations
- Agent Eval not included (planned for v0.2.x)
- No concurrent write safety in runners
- KettuSqueeze integration tests skipped in clean install (optional dependency)
- Context runner: 9/43 scenarios pass (threshold calibration)
- License: Apache 2.0
