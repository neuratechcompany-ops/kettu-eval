# Contributing

## Setup

```bash
git clone https://github.com/neuratechcompany-ops/kettu-eval.git
cd kettu-eval
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -q
```

## Adding an Adapter

1. Implement `MemoryAdapter`/`ContextAdapter`/`RetrievalAdapter` from `kettu_eval.adapters.base`
2. Create manifest YAML in `src/kettu_eval/adapters/reference/manifests/`
3. Run conformance: `pytest tests/conformance/ -v`
4. Adapter must NOT modify evaluator core or scoring logic

## Adding a Dataset

1. Create `datasets/<name>/manifest.yaml` with version
2. Add scenarios/queries with vendor-agnostic ground truth
3. Bump version for any fixture change (1.0.0 → 1.1.0)
4. Update checksum in manifest
5. Published datasets are immutable — do not modify without version bump

## Pull Requests

See `.github/pull_request_template.md` for checklist.
