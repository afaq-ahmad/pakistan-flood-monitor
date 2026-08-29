from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.database import Base
from pakistan_flood_monitor.models.observations import SourceAvailabilityStatus
from pakistan_flood_monitor.workflow.contracts import (
    ProcessorResult,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowTaskSpec,
)
from pakistan_flood_monitor.workflow.engine import WorkflowEngine
from pakistan_flood_monitor.workflow.repository import WorkflowRepository


class RecordingProcessor:
    processor_version = "test-v1"

    def __init__(self, calls: list[str], name: str) -> None:
        self.calls = calls
        self.name = name

    def execute(self, _context: WorkflowContext) -> ProcessorResult:
        self.calls.append(self.name)
        return ProcessorResult(status=WorkflowStatus.SUCCESS, output={"processor": self.name})


class UnavailableProcessor:
    processor_version = "test-unavailable-v1"

    def execute(self, _context: WorkflowContext) -> ProcessorResult:
        return ProcessorResult.unavailable(reason_code="missing_imerg", message="IMERG is unavailable")


def _repository(tmp_path) -> WorkflowRepository:
    engine = create_engine(f"sqlite:///{tmp_path / 'workflow.db'}")
    Base.metadata.create_all(bind=engine)
    return WorkflowRepository(sessionmaker(bind=engine))


def _context() -> WorkflowContext:
    return WorkflowContext(
        run_id="workflow-run-1",
        workflow_name="test_workflow",
        aoi_name="Indus-Lower",
        app_mode=AppMode.TEST,
        input_versions={"scene": "S1-A", "thresholds": "v1"},
    )


def test_workflow_persists_dependency_order_and_idempotently_reuses_success(tmp_path) -> None:
    calls: list[str] = []
    definition = WorkflowDefinition(
        name="test_workflow",
        tasks=(
            WorkflowTaskSpec("discover", RecordingProcessor(calls, "discover")),
            WorkflowTaskSpec("detect", RecordingProcessor(calls, "detect"), dependencies=("discover",)),
        ),
    )
    engine = WorkflowEngine(_repository(tmp_path))

    first = engine.execute(definition, _context())
    second = engine.execute(definition, _context())

    assert first.run.status is WorkflowStatus.SUCCESS
    assert [task.status for task in first.tasks] == [WorkflowStatus.SUCCESS, WorkflowStatus.SUCCESS]
    assert calls == ["discover", "detect"]
    assert second.reused is True
    assert calls == ["discover", "detect"]


def test_unavailable_processor_is_durable_degraded_and_blocks_dependents(tmp_path) -> None:
    calls: list[str] = []
    definition = WorkflowDefinition(
        name="test_workflow",
        tasks=(
            WorkflowTaskSpec("fetch_hydromet", UnavailableProcessor()),
            WorkflowTaskSpec("detect", RecordingProcessor(calls, "detect"), dependencies=("fetch_hydromet",)),
        ),
    )
    repository = _repository(tmp_path)
    execution = WorkflowEngine(repository).execute(definition, _context())

    assert execution.run.status is WorkflowStatus.DEGRADED
    assert execution.tasks[0].status is WorkflowStatus.DEGRADED
    assert execution.tasks[0].data_availability == SourceAvailabilityStatus.UNAVAILABLE.value
    assert execution.tasks[1].status is WorkflowStatus.SKIPPED
    assert execution.tasks[0].attempt_count == 1
    assert calls == []
