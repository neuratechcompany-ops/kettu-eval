"""Kettu Eval — core data models.

All Pydantic/dataclass models for runs, metrics, hard gates, coverage, and results.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class AdapterType(str, Enum):
    MEMORY = "memory"
    CONTEXT = "context"
    AGENT = "agent"
    RETRIEVAL = "retrieval"


class EvalStatus(str, Enum):
    OFFICIAL = "official"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    FAIL = "fail"


class RunStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class FailureClass(str, Enum):
    SYSTEM_ERROR = "system_error"
    ADAPTER_ERROR = "adapter_error"
    MODEL_ERROR = "model_error"
    DATASET_ERROR = "dataset_error"
    EVALUATOR_ERROR = "evaluator_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_OUTPUT = "invalid_output"
    TASK_FAILURE = "task_failure"
    HARD_GATE_FAILURE = "hard_gate_failure"


# ═══════════════════════════════════════════════════════════════════════════════
# Metric Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetricResult:
    name: str
    value: float | None = None       # null if not measured
    unit: str = "ratio"
    measured: bool = True
    sample_count: int = 0
    confidence_interval: tuple[float, float] | None = None
    threshold: float | None = None
    passed: bool | None = None       # null if no threshold
    detail: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.measured:
            self.value = None
        if self.measured and self.threshold is not None and self.value is not None:
            self.passed = self.value >= self.threshold


@dataclass
class HardGate:
    name: str
    description: str
    condition: str
    actual: float | int
    passed: bool
    severity: str = "blocking"  # "blocking" | "warning"


@dataclass
class Coverage:
    total_groups: int
    measured_groups: int
    skipped_groups: int
    unsupported_groups: int
    details: dict[str, str] = field(default_factory=dict)

    @property
    def percentage(self) -> float:
        if self.total_groups == 0:
            return 0.0
        return self.measured_groups / self.total_groups * 100


# ═══════════════════════════════════════════════════════════════════════════════
# Run Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RunConfig:
    repeat: int = 1
    concurrency: int = 1
    timeout_seconds: int = 300
    seed: int | None = None

    model_provider: str = ""
    model_name: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096

    dataset_id: str = ""
    dataset_version: str = ""

    adapter_name: str = ""
    adapter_version: str = ""
    adapter_type: AdapterType = AdapterType.MEMORY


@dataclass
class RunRecord:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    suite_id: str = ""
    scenario_id: str = ""
    adapter: str = ""
    adapter_version: str = ""
    model: str = ""
    runtime: str = ""
    seed: int | None = None
    repeat: int = 1
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    status: RunStatus = RunStatus.PASS
    metrics: list[MetricResult] = field(default_factory=list)
    hard_gates: list[HardGate] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    failure_class: FailureClass | None = None
    failure_detail: str | None = None
    coverage: Coverage | None = None
    config_hash: str = ""
    git_commit: str = ""
    os_info: str = ""
    python_version: str = ""

    def finish(self, status: RunStatus = RunStatus.PASS):
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.status = status

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "scenario_id": self.scenario_id,
            "adapter": self.adapter,
            "adapter_version": self.adapter_version,
            "model": self.model,
            "runtime": self.runtime,
            "seed": self.seed,
            "repeat": self.repeat,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status.value,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "measured": m.measured,
                    "sample_count": m.sample_count,
                    "threshold": m.threshold,
                    "passed": m.passed,
                    "detail": m.detail,
                }
                for m in self.metrics
            ],
            "hard_gates": [
                {"name": h.name, "passed": h.passed, "actual": h.actual, "condition": h.condition}
                for h in self.hard_gates
            ],
            "artifacts": self.artifacts,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "failure_detail": self.failure_detail,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset Model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DatasetInfo:
    dataset_id: str
    version: str
    language: str = "multilingual"
    license: str = "MIT"
    scenario_count: int = 0
    checksum: str = ""
    created_at: str = ""
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Composite Scores
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompositeScore:
    name: str                      # "MES", "COS", "RES", "AES"
    total: float
    components: dict[str, float]   # component_name → weighted_score
    weights: dict[str, float]      # component_name → weight
    status: EvalStatus
    hard_gate_violations: list[str] = field(default_factory=list)
    coverage: Coverage | None = None

    @staticmethod
    def compute(name: str, components: dict[str, float], weights: dict[str, float],
                hard_gates: list[HardGate], coverage: Coverage | None = None) -> CompositeScore:
        total = sum(
            components.get(c, 0.0) * weights.get(c, 0.0)
            for c in weights
        )
        violations = [h.name for h in hard_gates if not h.passed]
        if violations:
            status = EvalStatus.FAIL
        elif coverage and coverage.percentage < 100:
            status = EvalStatus.PARTIAL
        else:
            status = EvalStatus.OFFICIAL

        return CompositeScore(
            name=name, total=round(total, 4),
            components=components, weights=weights,
            status=status, hard_gate_violations=violations,
            coverage=coverage,
        )
