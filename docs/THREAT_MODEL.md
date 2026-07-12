# Threat Model — Kettu Eval v0.1.0

## Assets

| Asset | Value | Threat |
|-------|-------|--------|
| Evaluation integrity | Critical | Adapter cheating, biased scoring |
| Raw benchmark data | High | Tampering, selective reporting |
| Adapter secrets | High | Leakage via logs/configs |
| Dataset integrity | High | Modification after publication |

## Attack Vectors

### AV-1: Adapter Score Manipulation
Adapter returns pre-computed optimal results instead of real system behavior.
**Mitigation:** Adapter is external, but scoring is internal and deterministic. Adapter cannot modify scores.

### AV-2: Dataset Tampering
Dataset modified after benchmark publication to favor specific system.
**Mitigation:** Checksum verification, version immutability.

### AV-3: Secret Leakage
API keys in configs committed to git or leaked in logs.
**Mitigation:** Env-var only secrets, redaction policy, .gitignore for configs with secrets.

### AV-4: Malicious Adapter Output
Adapter returns payload designed to exploit evaluator (e.g., prompt injection).
**Mitigation:** Deterministic evaluation doesn't interpret adapter output as instructions. LLM judge sandboxed.

### AV-5: YAML Unsafe Load
`yaml.load()` instead of `yaml.safe_load()` enables arbitrary code execution.
**Mitigation:** Enforce `yaml.safe_load()` in code review.

### AV-6: Path Traversal
Malicious dataset path reads arbitrary files.
**Mitigation:** Resolve paths within dataset root only.

### AV-7: Arbitrary Code Execution via Adapter
Adapter plugin system could load arbitrary Python code.
**Mitigation:** Adapters are Python classes, not plugins. No dynamic code loading in v0.1.0.

### AV-8: Benchmark Cheating via Coverage
System claims high score by only running easy scenarios.
**Mitigation:** Coverage percentage mandatory. Partial coverage → PARTIAL status, not OFFICIAL.
