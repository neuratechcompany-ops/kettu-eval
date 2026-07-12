"""Kettu Eval — Adapter base classes and manifest validation."""

from __future__ import annotations

import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kettu_eval.core.models import AdapterType


# ═══════════════════════════════════════════════════════════════════════════════
# Adapter Manifest
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AdapterManifest:
    name: str
    version: str
    adapter_type: AdapterType
    transport: str = "stdio"
    endpoint: str = ""
    capabilities: dict[str, bool] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    timeout_seconds: int = 30

    @classmethod
    def from_yaml(cls, path: str | Path) -> AdapterManifest:
        data = yaml.safe_load(Path(path).read_text())
        return cls(
            name=data["name"],
            version=data["version"],
            adapter_type=AdapterType(data["adapter_type"]),
            transport=data.get("transport", "stdio"),
            endpoint=data.get("endpoint", ""),
            capabilities=data.get("capabilities", {}),
            limitations=data.get("limitations", []),
            timeout_seconds=data.get("timeout_seconds", 30),
        )

    def has_capability(self, name: str) -> bool:
        return self.capabilities.get(name, False)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "adapter_type": self.adapter_type.value,
            "transport": self.transport,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "limitations": self.limitations,
            "timeout_seconds": self.timeout_seconds,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Base Adapter Classes
# ═══════════════════════════════════════════════════════════════════════════════

class BaseAdapter(ABC):
    """All adapters inherit from this."""

    adapter_type: AdapterType
    manifest: AdapterManifest | None = None

    @abstractmethod
    async def health(self) -> dict:
        """Return {'status': 'ok'} or error info."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset all state for this adapter."""
        ...

    def check_capability(self, name: str) -> bool:
        if self.manifest is None:
            return True  # no manifest → assume all supported
        return self.manifest.has_capability(name)


class MemoryAdapter(BaseAdapter):
    adapter_type = AdapterType.MEMORY

    @abstractmethod
    async def start_session(self, session_id: str, user_id: str, metadata: dict) -> None: ...
    @abstractmethod
    async def add_event(self, session_id: str, event: dict) -> str: ...
    @abstractmethod
    async def add_fact(self, session_id: str, fact: dict) -> str: ...
    @abstractmethod
    async def search(self, session_id: str, query: str, top_k: int = 10) -> list[dict]: ...
    @abstractmethod
    async def get_context(self, session_id: str) -> dict: ...
    @abstractmethod
    async def end_session(self, session_id: str) -> None: ...

    async def update_fact(self, fact_id: str, updates: dict) -> bool:
        raise NotImplementedError

    async def delete_fact(self, fact_id: str) -> bool:
        raise NotImplementedError


class ContextAdapter(BaseAdapter):
    adapter_type = AdapterType.CONTEXT

    @abstractmethod
    async def process(self, content: str, session_id: str,
                      source_type: str, source_path: str | None = None) -> dict: ...
    @abstractmethod
    async def expand(self, ref: str, session_id: str) -> dict: ...
    @abstractmethod
    async def inspect(self, artifact_id: str) -> dict: ...
    @abstractmethod
    async def get_context_status(self, session_id: str) -> dict: ...


class AgentAdapter(BaseAdapter):
    adapter_type = AdapterType.AGENT

    @abstractmethod
    async def run_task(self, task: dict, session_id: str) -> dict: ...
    @abstractmethod
    async def reset_session(self, session_id: str) -> None: ...
    @abstractmethod
    async def get_usage(self, session_id: str) -> dict: ...


class RetrievalAdapter(BaseAdapter):
    adapter_type = AdapterType.RETRIEVAL

    @abstractmethod
    async def index(self, documents: list[dict]) -> list[str]: ...
    @abstractmethod
    async def query(self, query: str, top_k: int = 10,
                    filters: dict | None = None) -> list[dict]: ...
    @abstractmethod
    async def delete(self, doc_ids: list[str]) -> int: ...


# ═══════════════════════════════════════════════════════════════════════════════
# Manifest Validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_manifest(manifest: AdapterManifest) -> list[str]:
    """Validate an adapter manifest. Returns list of issues (empty = valid)."""
    issues: list[str] = []

    if not manifest.name:
        issues.append("name is required")
    if not manifest.version:
        issues.append("version is required")
    if not manifest.adapter_type:
        issues.append("adapter_type is required")

    # Check known adapter types
    try:
        AdapterType(manifest.adapter_type)
    except ValueError:
        issues.append(f"unknown adapter_type: {manifest.adapter_type}")

    # Validate capabilities are boolean
    for cap, val in manifest.capabilities.items():
        if not isinstance(val, bool):
            issues.append(f"capability '{cap}' must be boolean, got {type(val).__name__}")

    return issues


def validate_adapter_against_manifest(adapter: BaseAdapter, manifest: AdapterManifest) -> list[str]:
    """Check that adapter implements methods declared as supported in manifest."""
    issues: list[str] = []

    if manifest.adapter_type == AdapterType.MEMORY:
        if manifest.has_capability("add_event") and not _has_method(adapter, "add_event"):
            issues.append("manifest claims add_event but adapter does not implement it")
        if manifest.has_capability("fact_update") and not _has_method(adapter, "update_fact"):
            issues.append("manifest claims fact_update but adapter does not implement update_fact")
        if manifest.has_capability("fact_delete") and not _has_method(adapter, "delete_fact"):
            issues.append("manifest claims fact_delete but adapter does not implement delete_fact")

    return issues


def _has_method(obj: Any, method_name: str) -> bool:
    """Check if method is concretely implemented (not just abstract)."""
    meth = getattr(obj, method_name, None)
    if meth is None:
        return False
    return not getattr(meth, "__isabstractmethod__", False)
