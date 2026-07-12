# Metrics Specification — Kettu Eval v0.1.0

## MetricResult

Единый формат для всех метрик:

```python
@dataclass
class MetricResult:
    name: str                    # "fact_recall"
    value: float | None          # 0.94 или null если не измерено
    unit: str                    # "ratio", "count", "ms", "tokens", "pct"
    measured: bool               # true/false
    sample_count: int            # количество измерений
    confidence_interval: tuple[float, float] | None  # [0.90, 0.97]
    threshold: float | None      # порог для PASS/FAIL
    passed: bool | None          # null если нет порога
    detail: str | None           # дополнительная информация
    warnings: list[str]          # предупреждения
```

## Правила

1. **measured=false → value=null.** Никаких автоматических нулей.
2. **threshold задаётся явно.** Нет скрытых порогов.
3. **passed=null если нет threshold.** Метрика информационная, не оценочная.
4. **sample_count обязателен.** Всегда известно, на скольких измерениях основана метрика.
5. **confidence_interval для недетерминированных метрик.** Для детерминированных — null.

## HardGate

```python
@dataclass
class HardGate:
    name: str                    # "cross_session_leak"
    description: str
    condition: str               # "value == 0"
    actual: float | int
    passed: bool
    severity: str                # "blocking" | "warning"
```

Hard gate violation → общий статус FAIL, независимо от score.

## Coverage

```python
@dataclass
class Coverage:
    total_groups: int
    measured_groups: int
    skipped_groups: int
    unsupported_groups: int
    percentage: float            # measured / total * 100
    details: dict[str, str]      # group_name → "measured" | "skipped" | "unsupported"
```

## Composite Scores

### MES — Memory Effectiveness Score

| Component | Weight | Range |
|-----------|--------|-------|
| Retention | 20 | 0–1 |
| Retrieval quality | 20 | 0–1 |
| Update correctness | 15 | 0–1 |
| Isolation | 15 | 0–1 |
| Long-horizon stability | 10 | 0–1 |
| Noise resistance | 10 | 0–1 |
| Recovery | 10 | 0–1 |

### COS — Context Optimization Score

| Component | Weight | Range |
|-----------|--------|-------|
| Fidelity | 30 | 0–1 |
| Recoverability | 25 | 0–1 |
| Context Safety | 20 | 0–1 |
| Compression Efficiency | 15 | 0–1 |
| Performance | 10 | 0–1 |

### RES — Retrieval Effectiveness Score

| Component | Weight | Range |
|-----------|--------|-------|
| Precision | 25 | 0–1 |
| Recall | 25 | 0–1 |
| Ranking | 15 | 0–1 |
| False retrieval penalty | 15 | 0–1 |
| Temporal relevance | 10 | 0–1 |
| Latency | 10 | 0–1 |

### AES — Agent Effectiveness Score

| Component | Weight | Range |
|-----------|--------|-------|
| Task success | 35 | 0–1 |
| Correctness | 20 | 0–1 |
| Tool efficiency | 15 | 0–1 |
| Recovery | 10 | 0–1 |
| Latency | 10 | 0–1 |
| Cost efficiency | 10 | 0–1 |

## Evaluation Status

```python
class EvalStatus(Enum):
    OFFICIAL = "official"        # все обязательные группы измерены, hard gates clean
    PARTIAL = "partial"          # часть групп не поддерживается адаптером
    INCOMPLETE = "incomplete"    # недостаточно данных
    FAIL = "fail"                # нарушен hard gate
```

## Failure Taxonomy

```
SYSTEM_ERROR       — ошибка инфраструктуры (timeout, network)
ADAPTER_ERROR      — ошибка адаптера (invalid response, crash)
MODEL_ERROR        — ошибка модели (refusal, empty output)
DATASET_ERROR      — ошибка в dataset (missing fixture)
EVALUATOR_ERROR    — ошибка в evaluator logic
TIMEOUT            — превышен лимит времени
RATE_LIMIT         — превышен rate limit
INVALID_OUTPUT     — невалидный output (непарсимый JSON)
TASK_FAILURE       — агент не решил задачу
HARD_GATE_FAILURE  — нарушен hard gate
```

Инфраструктурные ошибки не снижают score, но влияют на operational reliability.
