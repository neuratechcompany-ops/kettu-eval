# LLM Judge Policy — Kettu Eval v0.1.0

## Primary Rule

**LLM judge is supplementary. Never the sole source of truth.**

Deterministic evaluation (ground truth, expected_contains, regex, AST) always takes precedence.

## When LLM Judge is Permitted

- Open-ended answers (no deterministic ground truth)
- Semantic equivalence checks
- Answer quality assessment (coherence, completeness)
- Breaking ties in deterministic evaluation

## When LLM Judge is FORBIDDEN

- Fact recall (use exact match)
- Code correctness (use unit tests)
- Numeric values (use ==)
- Paths, URLs, IDs (use string match)
- Exit codes (use integer comparison)
- JSON structure (use schema validation)

## Judge Configuration

- Model: fixed (e.g., DeepSeek v4 Pro)
- Temperature: 0
- Prompt: versioned, stored with run artifacts
- Minimum 2 passes for disputed cases
- Judge output saved in run artifacts

## Judge Constraints

- Cannot override hard gate
- Cannot override deterministic evaluator
- Judge score contribution to composite capped at 20%
- Judge must not evaluate its own response (if agent uses same model)

## Blind Judge

When comparing two systems, judge receives anonymized outputs (SYSTEM_A, SYSTEM_B).
Mapping revealed after scoring.
