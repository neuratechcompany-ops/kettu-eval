# Adapter Conformance — Kettu Eval v0.1.0

## Conformance Suite

Located in `tests/conformance/test_conformance.py`. Every adapter must pass the same suite.

## Test Groups

| Group | Tests | What it checks |
|-------|-------|---------------|
| Manifest | 4 | YAML validity, capability deps, type matching, boolean caps |
| Lifecycle | 3 | start→add→get→end→reset cycle, health check |
| Reset | 2 | Data cleared after reset, null adapter noop |
| Isolation | 3 | Session-scoped search/context, null isolation |
| Error Mapping | 2 | Structured errors, no raw exceptions |
| Optional Methods | 4 | update/delete return False, SQLite CRUD |
| Restart | 1 | Persistence across instances |
| Capability Truthfulness | 3 | Behavior matches manifest, method validation |
| Edge Cases | 12 | Empty search, Unicode, top_k, events, concurrent sessions |

**Total: 34 conformance tests**

## Running Conformance

```bash
# Against all available adapters
pytest tests/conformance/ -v

# Against specific adapter
pytest tests/conformance/ -v -k "sqlite"
```

## Adapter Registration

New adapters register by:
1. Adding manifest to `src/kettu_eval/adapters/reference/manifests/`
2. Adding entry to `TestManifestConformance.ADAPTERS`
3. Running full conformance suite

## Failure Classification

- Manifest validation failure → ADAPTER_ERROR (blocking)
- Capability mismatch → ADAPTER_ERROR (blocking)
- Isolation violation → HARD_GATE_FAILURE
- Timeout → SYSTEM_ERROR (non-blocking)
- Reset failure → ADAPTER_RESET_FAILED
