# Kettu Eval

**Independent Evaluation Framework for AI Agent Systems**

[![Tests](https://img.shields.io/badge/tests-185%20PASS-brightgreen)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

Kettu Eval — независимый open-source фреймворк для **воспроизводимой оценки** долговременной памяти, retrieval-систем и оптимизации контекста AI-агентов.

> **Не привязан к Kettu Mem или Kettu Squeeze.** Любая система подключается через единый adapter contract.

---

## Почему это важно

- **Memory-системы** часто измеряют количество сохранённых фактов, а не реальную полезность для агента
- **Retrieval-проекты** показывают similarity score вместо precision/recall/MRR
- **Context-компрессоры** отчитываются token savings без измерения потери критической информации
- **Composite score без hard gates** может скрыть критические утечки и потери

Kettu Eval оценивает не «сколько», а **«насколько корректно»**.

---

## Что входит в v0.1.0

| Профиль | Размер | Что оценивает |
|---------|--------|---------------|
| **Memory Core** | 30 сценариев | Retention, updates, isolation, contradictions, restart, noise |
| **Context Core** | 43 сценария | Fidelity, recoverability, ref safety, Unicode, adversarial |
| **Retrieval Core** | 506 доков, 150 запросов | Precision@K, Recall@K, MRR, nDCG, filtering, isolation |
| **Conformance Suite** | 34 теста | Manifest, lifecycle, reset, isolation, error mapping |
| **Reference Adapters** | 4 шт. | Null, SimpleSQLite, KettuSqueeze, KettuMem |

**Agent Eval не входит в v0.1.0** — появится в v0.2.x.

---

## Архитектура

```
Dataset → Runner → Adapter Contract → System Under Test → Metrics → Hard Gates → Report
```

- **Adapter Contract** — заморожен для v0.1.x. 0 изменений с Phase 2.
- **Scoring logic** — в Kettu Eval, не в адаптере. Адаптер не может «подкрутить» результат.
- **Hard gates** — переопределяют любой числовой score. Утечка данных = FAIL.

---

## Установка

```bash
git clone https://github.com/neuratechcompany-ops/kettu-eval.git
cd kettu-eval
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Пакет пока не опубликован в PyPI.

---

## Быстрый старт

```bash
kettu-eval doctor                    # Проверка окружения
kettu-eval adapters list             # Доступные адаптеры
kettu-eval datasets list             # Доступные датасеты
kettu-eval validate-dataset memory-core
```

---

## Composite Scores

| Score | Название | Hard gates |
|-------|----------|------------|
| **MES** | Memory Effectiveness | cross-session leak, project leak, restart data loss, namespace corruption |
| **COS** | Context Optimization | broken refs, byte-exact recovery, critical recall, source omission, Unicode crash |
| **RES** | Retrieval Effectiveness | namespace isolation, project isolation, forbidden@rank1 |

> **Высокий числовой score не отменяет hard-gate failure.**

---

## Адаптеры

| Adapter | Memory | Context | Retrieval | E2E |
|---------|--------|---------|-----------|-----|
| NullBaseline | ✅ | ✅ | ✅ | ✅ |
| SimpleSQLiteMemory | ✅ | — | limited | ✅ |
| KettuSqueeze | — | ✅ | — | ✅ |
| KettuMem | ✅ | — | ✅ | requires server |

---

## Тесты

| Окружение | Тестов | Примечание |
|-----------|--------|------------|
| Source checkout | **185 PASS** | Полный suite |
| Clean install | **139 PASS + 2 SKIPPED** | 46 тестов требуют kettu-squeeze |

---

## Smoke-результаты (NullBaseline)

| Профиль | Выполнено | Пройдено | Семантика |
|---------|-----------|----------|-----------|
| Memory | 30/30 | 0/30 | Null возвращает пустой контекст — retention fails, expected |
| Context | 43/43 | 9/43 | Passthrough-сценарии проходят, остальные — expected |
| Retrieval | 150/150 | 150 executed | 0 хитов, 0 false positives — valid baseline |

---

## Статус

**Experimental.** Adapter contract заморожен. Datasets versioned. Проект ещё не Stable:
- нет Agent Eval;
- мало сторонних адаптеров;
- результаты относятся к опубликованным datasets.

---

## Документация

- [Architecture](docs/ARCHITECTURE.md)
- [Adapter Spec](docs/ADAPTER_SPEC.md)
- [Metrics Spec](docs/METRICS_SPEC.md)
- [Dataset Spec](docs/DATASET_SPEC.md)
- [MES Spec](docs/MES_SPEC.md) · [COS Spec](docs/COS_SPEC.md) · [RES Spec](docs/RES_SPEC.md)
- [Audit Report](docs/AUDIT_REPORT.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)
- [Security](docs/SECURITY.md)

---

## Roadmap

- **v0.1.x** — bugfixes, compatibility, external adapters
- **v0.2.x** — Agent Eval
- **Future** — external datasets, comparative reports, more systems

---

## License

[Apache License 2.0](LICENSE)
