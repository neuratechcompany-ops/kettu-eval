# Known Limitations — Kettu Eval v0.1.0

## Framework

- **Agent Eval not included.** Architecture supports it, v0.1.0 ships Memory, Context, and Retrieval Core only.
- **No concurrent write safety in runners.** Runners execute scenarios sequentially. For single-agent deployment this is adequate.

## Context Benchmark

- **Forbidden transformations check is heuristic.** `_check_forbidden_transformations` uses basic string-presence check, not semantic verification.
- **NullBaseline passes 9/43 context scenarios.** Passthrough cases only; remaining 34 require actual compression logic. Expected baseline.
- **Tokenizer metadata absent from run outputs.** All token counts use `len//3` heuristic. `estimated=true` not recorded in run metadata.

## Retrieval Benchmark

- **RES latency normalization is approximate.** Linear [0ms→5, 1000ms→0] normalization. Non-linear latency distributions may not be represented accurately.
- **NullBaseline retrieves 0 hits on 150/150 queries.** Valid baseline — no false positives, no leaks.

## Adapters

- **KettuSqueeze and KettuMem are optional dependencies.** 46 integration tests skipped in clean install when these packages are absent.
- **Only 4 reference adapters.** External adapter ecosystem not yet built.

## Datasets

- **Memory Core: 30 scenarios.** Coverage good but not exhaustive for all memory patterns.
- **Context Core: 43 scenarios.** Threshold calibration may need per-scenario tuning.
- **Retrieval Core: 506 documents, 150 queries.** Query diversity adequate for v0.1 but expandable.

## Composite Scores

- **MES, COS, RES: weights are initial.** No calibration against real-world agent performance yet.
- **Hard gates verified as functional.** Gate logic correct, but threshold values (3%, 99.5%) may need tuning with more data.
