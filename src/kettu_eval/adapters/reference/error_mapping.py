"""Adapter error mapping — standardized error taxonomy.

All adapters must map their errors to this taxonomy.
Raw exceptions must never be returned as the sole result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AdapterErrorCode(str, Enum):
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    ADAPTER_TIMEOUT = "adapter_timeout"
    ADAPTER_AUTH_ERROR = "adapter_auth_error"
    ADAPTER_INVALID_RESPONSE = "adapter_invalid_response"
    ADAPTER_NOT_SUPPORTED = "adapter_not_supported"
    ADAPTER_STATE_ERROR = "adapter_state_error"
    ADAPTER_RESET_FAILED = "adapter_reset_failed"
    ADAPTER_ISOLATION_FAILURE = "adapter_isolation_failure"
    ADAPTER_INTERNAL_ERROR = "adapter_internal_error"


@dataclass
class AdapterError:
    """Standardized error from any adapter."""
    code: AdapterErrorCode
    message: str
    retriable: bool = False
    original_exception: str | None = None
    transport_status: int | None = None  # HTTP status code
    adapter_name: str = ""
    adapter_version: str = ""
    detail: dict | None = None

    def to_dict(self) -> dict:
        return {
            "error": self.code.value,
            "message": self.message,
            "retriable": self.retriable,
            "original_exception": self.original_exception,
            "transport_status": self.transport_status,
            "adapter": f"{self.adapter_name}@{self.adapter_version}",
        }


def not_supported(operation: str, adapter_name: str = "", version: str = "") -> AdapterError:
    """Standard 'not supported' response."""
    return AdapterError(
        code=AdapterErrorCode.ADAPTER_NOT_SUPPORTED,
        message=f"Operation '{operation}' is not supported by this adapter",
        retriable=False,
        adapter_name=adapter_name,
        adapter_version=version,
    )


def timeout_error(operation: str, timeout_s: int, adapter_name: str = "") -> AdapterError:
    return AdapterError(
        code=AdapterErrorCode.ADAPTER_TIMEOUT,
        message=f"Operation '{operation}' timed out after {timeout_s}s",
        retriable=True,
        adapter_name=adapter_name,
    )


def unavailable_error(detail: str = "", adapter_name: str = "") -> AdapterError:
    return AdapterError(
        code=AdapterErrorCode.ADAPTER_UNAVAILABLE,
        message=f"Adapter unavailable: {detail}" if detail else "Adapter unavailable",
        retriable=True,
        adapter_name=adapter_name,
    )
