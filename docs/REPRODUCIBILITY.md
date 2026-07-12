# Reproducibility — Kettu Eval v0.1.0

## Required Metadata

Every RunRecord captures:

- git commit hash
- dataset version + checksum
- adapter name + version
- model provider + name
- runtime type (api/local)
- tokenizer identifier
- config hash (SHA-256 of merged config)
- OS + Python version
- start/end timestamps
- random seeds
- dependency lock hash

## Reproduce Command

```bash
kettu-eval reproduce reports/run-2026-07-12/
```

Должен повторно запустить benchmark с теми же настройками.

Implementation: сохранять полный config + dataset version + adapter manifest в artifacts директории каждого run.

## Deterministic vs Non-deterministic

- Deterministic runs: seed фиксирован, 1 repeat достаточно
- Non-deterministic: минимум 3 repeats, seed записан

## Config Freeze

При запуске конфиг сохраняется копией. Изменение исходного конфига после run не влияет на reproduce.
