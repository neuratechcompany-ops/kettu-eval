# Contract Audit — Kettu Eval v0.1.0

**Date:** 2026-07-12
**Scope:** Adapter interfaces, capability model, metric model, hard gates, coverage, extensibility

## Findings

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| F1 | MEDIUM | No capability dependency validation (compression→process, recoverable_refs→expand) | ✅ FIXED |
| F2 | LOW | 'process' capability not distinct from 'compression' | 📋 Documented |
| F3 | MEDIUM | No method→capability mapping — impossible to validate adapter implements declared caps | ✅ FIXED |
| F4 | LOW | update_fact/delete_fact raised NotImplementedError instead of returning False | ✅ FIXED |
| F5 | LOW | ContextAdapter.process() returns untyped dict — no spec for return format | 📋 Documented |
| F6 | INFO | reset() semantics not documented | 📋 Documented |

## Fixes Applied

### F1 + F3: Capability dependency validation + method mapping

Added:
- `CAPABILITY_METHODS` — maps each capability to required adapter methods
- `CAPABILITY_DEPENDENCIES` — maps capabilities to their prerequisites
- `validate_capability_dependencies()` — checks that declared caps have satisfied deps
- `validate_adapter_methods()` — checks that adapter implements methods for declared caps

Example: declaring `compression=True` without `process=True` → validation error.

### F4: Optional methods

`MemoryAdapter.update_fact()` and `MemoryAdapter.delete_fact()` now return `False` instead of raising `NotImplementedError`. These are optional capabilities — adapters that don't support them simply return False.

## Documented Limitations

### F2: process vs compression

`process()` is the general method for content transformation. `compression` is a specific capability that uses `process()`. An adapter could implement `process()` for other purposes (logging, monitoring) without doing compression. The capability system handles this — declare only what you support.

### F5: Return format

`ContextAdapter.process()` returns `dict` with expected keys: `content`, `artifact_id`, `mode`, `lossy`, `original_tokens`, `compressed_tokens`, `refs`. Full spec in `ADAPTER_SPEC.md`.

### F6: reset() semantics

`reset()` clears all adapter state for the current evaluation context. After reset, the adapter must behave as if freshly initialized. No cross-run state leakage permitted.

## Kettu Independence

Verified: zero imports from Kettu Mem, Kettu Squeeze, or any external project in all adapter base classes. All interfaces use only standard Python types (str, dict, list, int, bool).

## Extensibility Check

Mental implementation walkthrough for 5 external systems:

| System | Adapter Type | Feasible? | Notes |
|--------|-------------|-----------|-------|
| Mem0 | Memory | ✅ | Implements add_event, add_fact, search |
| Letta | Memory + Agent | ✅ | Multi-adapter (MemoryAdapter + AgentAdapter) |
| LangGraph memory | Memory | ✅ | Implements get_context, add_event |
| Simple SQLite | Memory + Retrieval | ✅ | Minimal implementation, no semantic search |
| Arbitrary RAG | Retrieval | ✅ | Implements index, query |

No core Kettu Eval changes required for any of these.

## Contract Freeze Decision

**Adapter contract CAN be frozen for v0.1.x.**

All interfaces are:
- Minimal (5–8 methods each)
- Independent of Kettu projects
- Extensible by third parties
- Capability-negotiable
- Transport-agnostic
- Validated (manifest + dependencies + methods)

Breaking changes to public interfaces are prohibited until v1.0 without a new major version.
