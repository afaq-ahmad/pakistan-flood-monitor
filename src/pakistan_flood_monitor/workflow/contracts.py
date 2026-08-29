"""Small, durable workflow contracts for canonical processors."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping, Protocol

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.observations import SourceAvailabilityStatus


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"


TERMINAL_WORKFLOW_STATUSES = {
    WorkflowStatus.SUCCESS,
    WorkflowStatus.FAILED,
    WorkflowStatus.SKIPPED,
    WorkflowStatus.DEGRADED,
}


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    run_id: str
    workflow_name: str
    aoi_name: str
    app_mode: AppMode
    input_versions: Mapping[str, str]
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProcessorResult:
    status: WorkflowStatus
    output: Mapping[str, Any] = field(default_factory=dict)
    data_availability: SourceAvailabilityStatus = SourceAvailabilityStatus.AVAILABLE
    reason_code: str | None = None
    message: str | None = None

    @classmethod
    def unavailable(cls, *, reason_code: str, message: str) -> "ProcessorResult":
        return cls(
            status=WorkflowStatus.DEGRADED,
            data_availability=SourceAvailabilityStatus.UNAVAILABLE,
            reason_code=reason_code,
            message=message,
        )


class WorkflowProcessor(Protocol):
    """Interface future EO and hydromet processors must implement."""

    processor_version: str

    def execute(self, context: WorkflowContext) -> ProcessorResult:
        ...


@dataclass(frozen=True, slots=True)
class WorkflowTaskSpec:
    name: str
    processor: WorkflowProcessor
    dependencies: tuple[str, ...] = ()
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    name: str
    tasks: tuple[WorkflowTaskSpec, ...]

    def ordered_tasks(self) -> tuple[WorkflowTaskSpec, ...]:
        """Return a validated topological order, preserving declaration order."""

        by_name = {task.name: task for task in self.tasks}
        if len(by_name) != len(self.tasks):
            raise ValueError(f"Workflow '{self.name}' has duplicate task names")
        ordered: list[WorkflowTaskSpec] = []
        resolved: set[str] = set()
        remaining = list(self.tasks)
        while remaining:
            ready = [task for task in remaining if set(task.dependencies).issubset(resolved)]
            if not ready:
                unknown = sorted({dependency for task in remaining for dependency in task.dependencies if dependency not in by_name})
                if unknown:
                    raise ValueError(f"Workflow '{self.name}' references unknown dependencies: {', '.join(unknown)}")
                raise ValueError(f"Workflow '{self.name}' has a cyclic task dependency")
            for task in ready:
                ordered.append(task)
                resolved.add(task.name)
                remaining.remove(task)
        return tuple(ordered)


def workflow_signature(context: WorkflowContext) -> str:
    """Stable idempotency key for all important inputs and configuration versions."""

    payload = {
        "workflow": context.workflow_name,
        "aoi": context.aoi_name,
        "app_mode": context.app_mode.value,
        "input_versions": dict(sorted(context.input_versions.items())),
        "metadata": context.metadata,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
