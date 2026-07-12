# Kettu Eval v0.1.0 — Architecture

## Overview

Kettu Eval — независимый evaluation framework. Тестируемые системы подключаются через адаптеры. Логика оценки неизменна и находится в Kettu Eval.

## Data Flow

```
Config (YAML)
    │
    ▼
┌──────────────┐
│  Runner      │  Оркестрирует запуск
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  Dataset     │────▶│  Scenario    │  Группы тестов
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Adapter    │  Тестируемая система
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Evaluator   │  Детерминированная оценка
                    └──────┬───────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
            ┌──────────┐   ┌──────────┐
            │ Metrics  │   │ HardGate │
            └────┬─────┘   └────┬─────┘
                 │              │
                 ▼              ▼
            ┌──────────────────────┐
            │  CompositeScore      │
            │  MES / COS / RES / AES│
            └──────────┬───────────┘
                       │
                       ▼
                ┌──────────────┐
                │  RunRecord   │  JSONL storage
                └──────────────┘
```

## Component Map

| Component | Location | Phase |
|-----------|----------|-------|
| Core models | `core/models.py` | 1 ✅ |
| Adapter base | `adapters/base.py` | 1 ✅ |
| Null adapter | `adapters/null_adapter.py` | 1 ✅ |
| Run storage | `storage/run_storage.py` | 1 ✅ |
| CLI | `cli/main.py` | 1 ✅ |
| Memory evaluator | `evaluators/memory.py` | 3 |
| Retrieval evaluator | `evaluators/retrieval.py` | 3 |
| Context evaluator | `evaluators/context.py` | 4 |
| Agent evaluator | `evaluators/agent.py` | 5 |
| LLM Judge | `judges/` | 5 |
| Report generator | `reports/` | 3 |
| KettuMemAdapter | `adapters/kettu_mem.py` | 2 |
| KettuSqueezeAdapter | `adapters/kettu_squeeze.py` | 2 |
| SQLiteAdapter | `adapters/sqlite_simple.py` | 2 |

## Profiles

Каждый профиль — независимый evaluator со своими сценариями, метриками и hard gates:

- **Memory** — факты, обновления, изоляция, долговременность
- **Retrieval** — precision/recall, ranking, latency
- **Context** — сжатие, fidelity, recoverability
- **Agent** — task success, planning, tool use
- **System** — throughput, concurrency, recovery

## Adapter Contract

См. `docs/ADAPTER_SPEC.md`. Ключевое: адаптер не знает о scoring. Kettu Eval не знает о реализации адаптера.

## Storage

`.kettu-eval/runs/runs.jsonl` — append-only JSONL с RunRecord.
Raw prompts/outputs — `.kettu-eval/artifacts/` (не коммитить).
