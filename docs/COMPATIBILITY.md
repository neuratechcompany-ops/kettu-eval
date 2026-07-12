# Compatibility — Kettu Eval v0.1.x

## Adapter Contract Stability

Public adapter interfaces (`MemoryAdapter`, `ContextAdapter`, `AgentAdapter`, `RetrievalAdapter`) are frozen for v0.1.x. No breaking changes without a major version bump.

## What CAN change without breaking

- Adding new optional methods with default implementations (returning False/None)
- Adding new capabilities to the manifest (backward-compatible)
- Adding new validation rules (more checks, not fewer)
- Internal implementation changes in evaluators/runners
- CLI flag additions
- Report format additions (new fields, not removal)

## What CANNOT change without v0.2.0

- Removing or renaming abstract methods
- Changing method signatures (parameter names, types, order)
- Changing return types
- Making optional methods required
- Removing capabilities from the dependency map
- Changing hard gate semantics
- Changing `measured=false → value=null` invariant

## Capability Matrix v0.1

| Adapter Type | Required Methods | Optional Methods | Capabilities |
|-------------|-----------------|------------------|--------------|
| Memory | start_session, add_event, add_fact, search, get_context, end_session, health, reset | update_fact, delete_fact | semantic_search, context_builder, session_isolation, ttl, compression |
| Context | process, expand, inspect, get_context_status, health, reset | — | compression, recoverable_refs, source_code_safe, session_isolation, dedup, delta, lossy |
| Agent | run_task, reset_session, get_usage, health, reset | — | tool_use, planning, multi_step, error_recovery |
| Retrieval | index, query, delete, health, reset | — | semantic_search, metadata_filter, temporal, multi_hop, ranking |

## Transport Compatibility

Adapters are transport-agnostic. Supported transports:
- Direct Python import (in-process)
- HTTP (REST)
- stdio (MCP)

Transport is declared in the manifest, not in the adapter class. Same adapter class can be used with different transports.

## Version Compatibility

Adapters declare their version in the manifest. Kettu Eval checks:
- Major version mismatch → warning (may still work)
- Minor version mismatch → info only
- No version → accepted with warning
