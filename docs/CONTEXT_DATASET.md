# Context Core Dataset — Kettu Eval v0.1.0

42 deterministic scenarios for evaluating context optimization/compression systems.

## Structure

```
datasets/context-core/
├── manifest.yaml
├── scenarios/       # 43 YAML scenario files
├── fixtures/        # 87 input fixtures (reused from Kettu Squeeze)
└── expected/        # Ground truth per scenario
```

## Categories

| Category | Scenarios | Description |
|----------|-----------|-------------|
| source_code | 7 | Python, Rust, JS — strict_raw required |
| logs | 7 | RLE, errors, stack traces |
| json | 6 | Null semantics, large arrays, Unicode |
| test_outputs | 5 | pytest, cargo test, exit codes |
| git_diff | 4 | Changed lines, renames, deletions |
| configs | 4 | YAML, TOML, .env — strict_raw |
| documents | 3 | Long text with recoverable lossy |
| unicode | 4 | Cyrillic, CJK, emoji, combining |
| adversarial | 3 | Fake refs, prompt injection, binary |

## Scenario Format

```yaml
scenario_id: unique_id
category: source_code|logs|json|...
input_fixture: relative path to fixture
input_content: inline content (alternative to fixture)
source_type: file|tool|api
recommended_policy: strict_raw|lossless|recoverable_lossy
required_preservations: [list of strings that MUST survive]
forbidden_transformations: [list of transformations that MUST NOT happen]
expected_state: {content_preserved: true, ...}
metrics: [list of metrics to evaluate]
hard_gates: [list of hard gates to check]
```

## Ground Truth

Fully vendor-agnostic. No Kettu-specific types (no artifact_id, no representation_id, no KettuRef).

Ground truth is expressed as:
- `required_preservations`: strings/identifiers that must be found in output
- `forbidden_transformations`: operations that must not occur
- `expected_state`: boolean assertions about the output

## Versioning

Version 1.0.0. Immutable after publication. Changes → 1.1.0.
