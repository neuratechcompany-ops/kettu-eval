# Dataset Specification — Kettu Eval v0.1.0

## Format

Каждый dataset — директория с `manifest.yaml` и fixtures.

```
datasets/memory-core/
├── manifest.yaml
├── fixtures/
│   ├── fact_retention_001.json
│   ├── fact_update_001.json
│   └── ...
└── README.md
```

## Manifest

```yaml
dataset_id: memory-core
version: 1.0.0
language: multilingual
license: MIT
scenario_count: 30
checksum: sha256:abc123...
created_at: "2026-07-12"
description: "Core memory evaluation — fact retention, update, isolation"
```

## Rules

1. Dataset version immutable after publication
2. Changes → new version (1.0.0 → 1.1.0 or 2.0.0)
3. Fixtures separate from benchmark logic
4. Checksum mandatory
5. Multilingual support: at minimum English + Russian

## Scenario Format

```json
{
  "scenario_id": "fact-retention-001",
  "group": "fact_retention",
  "description": "Basic fact retention across sessions",
  "setup": {
    "session_1": {
      "facts": [{"key": "user_name", "value": "Aurum"}],
      "events": [{"type": "message", "content": "My name is Aurum"}]
    },
    "session_2": {
      "queries": [
        {"question": "What is my name?", "expected": ["Aurum"]}
      ]
    }
  },
  "metrics": ["fact_recall", "exact_match"],
  "hard_gates": []
}
```
