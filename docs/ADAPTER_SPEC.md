# Adapter Specification — Kettu Eval v0.1.0

## Concept

Adapter — единственная точка связи между Kettu Eval и тестируемой системой. Вся логика оценки находится в Kettu Eval, адаптер только предоставляет данные через стандартизированный интерфейс.

## Adapter Types

| Type | Interface | Used By |
|------|-----------|---------|
| `memory` | `MemoryAdapter` | Memory Eval Suite |
| `context` | `ContextAdapter` | Context Eval Suite |
| `agent` | `AgentAdapter` | Agent Eval Suite |
| `retrieval` | `RetrievalAdapter` | Retrieval Eval Suite |

## Base Interfaces

### MemoryAdapter

```python
class MemoryAdapter(ABC):
    adapter_type = "memory"

    async def start_session(self, session_id: str, user_id: str, metadata: dict) -> None
    async def add_event(self, session_id: str, event: dict) -> str  # → event_id
    async def add_fact(self, session_id: str, fact: dict) -> str    # → fact_id
    async def search(self, session_id: str, query: str, top_k: int = 10) -> list[dict]
    async def get_context(self, session_id: str) -> dict
    async def update_fact(self, fact_id: str, updates: dict) -> bool
    async def delete_fact(self, fact_id: str) -> bool
    async def end_session(self, session_id: str) -> None
    async def reset(self) -> None
    async def health(self) -> dict
```

### ContextAdapter

```python
class ContextAdapter(ABC):
    adapter_type = "context"

    async def process(self, content: str, session_id: str, source_type: str,
                      source_path: str | None = None) -> dict
    async def expand(self, ref: str, session_id: str) -> dict
    async def inspect(self, artifact_id: str) -> dict
    async def get_context_status(self, session_id: str) -> dict
    async def reset(self) -> None
    async def health(self) -> dict
```

### AgentAdapter

```python
class AgentAdapter(ABC):
    adapter_type = "agent"

    async def run_task(self, task: dict, session_id: str) -> dict
    async def reset_session(self, session_id: str) -> None
    async def get_usage(self, session_id: str) -> dict
    async def health(self) -> dict
```

### RetrievalAdapter

```python
class RetrievalAdapter(ABC):
    adapter_type = "retrieval"

    async def index(self, documents: list[dict]) -> list[str]
    async def query(self, query: str, top_k: int = 10,
                    filters: dict | None = None) -> list[dict]
    async def delete(self, doc_ids: list[str]) -> int
    async def reset(self) -> None
    async def health(self) -> dict
```

## Adapter Manifest

Каждый адаптер предоставляет YAML-manifest:

```yaml
name: kettu-mem
version: 0.2.1
adapter_type: memory
transport: http
endpoint: http://127.0.0.1:8765
capabilities:
  add_event: true
  add_fact: true
  semantic_search: true
  context_builder: true
  compression: true
  session_isolation: true
  fact_update: true
  fact_delete: false
  ttl: false
limitations:
  - "No TTL/expiry support"
  - "Max 1000 facts per session"
timeout_seconds: 30
```

## Capability Declaration

Каждый метод в интерфейсе имеет capability flag. Если capability = false, Kettu Eval не вызывает метод и помечает соответствующие тесты как NOT_SUPPORTED (не FAIL).

## Adapter Validation

При загрузке адаптера:

1. Проверить наличие manifest
2. Проверить соответствие adapter_type
3. Проверить health endpoint
4. Проверить заявленные capabilities против реализованных методов
5. Зафиксировать неподдерживаемые операции

## Error Handling

- Адаптер возвращает ошибки в стандартном формате: `{"error": "message", "code": "ERROR_CODE"}`
- Timeout → `SYSTEM_ERROR`, не снижает score
- Adapter unavailable → run помечается как `error`, не `fail`
- Invalid response → `ADAPTER_ERROR`

## Namespace Isolation

- Каждый run получает изолированное пространство (session_id prefix)
- После run → `reset()` очищает все данные этого run
- Между параллельными run данные не пересекаются
