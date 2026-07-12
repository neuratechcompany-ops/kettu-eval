# Invariants — Kettu Eval v0.1.0

Нерушимые гарантии оценочного фреймворка.

1. **Framework ≠ Implementation.** Kettu Eval не зависит от Kettu Mem, Kettu Squeeze или любой другой тестируемой системы. Адаптер — единственная точка связи.

2. **Adapter cannot modify scoring.** Логика оценки неизменна. Адаптер только предоставляет данные.

3. **Reproducible.** Каждый run воспроизводим при фиксированных seed, dataset version, adapter version, model, config.

4. **Raw data preserved.** Все сырые промпты, ответы и метрики сохраняются в JSONL.

5. **Partial ≠ Complete.** Coverage < 100% явно указывается. Неполный результат не выдаётся за полный.

6. **Unmeasured ≠ Zero.** `measured=false` → `value=null`. Никаких автоматических нулей.

7. **Hard gate overrides score.** Нарушение hard gate → FAIL, независимо от числового балла.

8. **LLM judge is supplementary.** Детерминированный evaluator — первичен. Judge только для открытых ответов.

9. **RAW ≠ EXPERIMENT.** Ветки изолированы. Результаты не смешиваются.

10. **Blind comparison.** Evaluator не знает имя реализации при A/B-сравнении.

11. **Full config capture.** Модель, runtime, tokenizer, temperature, seed — всё фиксируется.

12. **Cost, latency, quality — раздельно.** Не сворачиваются в один score без весов.

13. **Infrastructure errors ≠ system errors.** Таймаут адаптера не снижает score памяти.

14. **Datasets versioned.** Изменение dataset = новый version, не перезапись.

15. **Result = coverage + confidence.** Каждый результат сопровождается coverage percentage.

16. **Aggregate decomposable.** Любой агрегированный показатель раскладывается до сырых прогонов.
