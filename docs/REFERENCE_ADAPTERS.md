# Reference Adapters — Kettu Eval v0.1.0

## Overview

Reference adapters prove the adapter contract works with real implementations.

| Adapter | Type | Status | Tests |
|---------|------|--------|-------|
| NullBaselineAdapter | memory, context, agent, retrieval | ✅ Complete | 8 |
| SimpleSQLiteMemoryAdapter | memory | ✅ Complete | 13 |
| KettuSqueezeAdapter | context | ✅ Complete | 11 |
| KettuMemAdapter | memory | ⚠️ Requires server | 0 (integration skipped) |

## SimpleSQLiteMemoryAdapter

Minimal SQLite-backed memory. No embeddings, no semantic search, no ML.

**Capabilities:** add_event, add_fact, search (exact substring), get_context, session_isolation, fact_update, fact_delete, restart_recovery.

**Not supported:** semantic_search, context_builder, compression, ttl, project_isolation.

**Storage:** SQLite WAL, `:memory:` or file path.

## KettuSqueezeAdapter

In-process adapter for Kettu Squeeze context optimization.

**Capabilities:** process (compress), expand, inspect, context_status, source_code_safe, recoverable_refs, session_isolation.

**Not supported:** delta, dedup, lossy (by default — opt-in).

**Transport:** Direct Python import (same process).

## KettuMemAdapter

HTTP adapter for Kettu Mem server.

**Capabilities:** start_session, add_event, add_fact, search, semantic_search, get_context, context_builder, session_isolation, project_isolation.

**Not supported:** fact_delete, ttl.

**Transport:** HTTP to `KETTU_MEM_ENDPOINT` (default: `http://127.0.0.1:8765`).

**Requires:** Kettu Mem server running.

## Conformance

All adapters pass the same conformance suite:
- Manifest validation
- Lifecycle (start → use → end → reset)
- Session isolation
- Optional methods
- Restart/persistence
- Capability truthfulness
- Unicode safety
- Error mapping
