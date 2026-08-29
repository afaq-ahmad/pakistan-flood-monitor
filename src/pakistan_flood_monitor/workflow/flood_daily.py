"""Canonical daily flood workflow adapter around the existing flood module."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.models.observations import OperationalDataIntegrityError, ScientificObservation
from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline
from pakistan_flood_monitor.workflow.contracts import ProcessorResult, WorkflowContext, WorkflowDefinition, WorkflowTaskSpec, WorkflowStatus
from pakistan_flood_monitor.workflow.engine import WorkflowEngine, WorkflowExecution
from pakistan_flood_monitor.workflow.repository import WorkflowRepository


class FloodDailyProcessor:
    processor_version = "flood-daily-adapter-v1"

    def __init__(self, pipeline: FloodMonitoringPipeline) -> None:
        self._pipeline = pipeline

    def execute(self, context: WorkflowContext) -> ProcessorResult:
        if isinstance(self._pipeline, FloodMonitoringPipeline):
            report = self._pipeline.run_daily(context.aoi_name, run_id=context.run_id)
        else:  # Compatibility with focused test/adaptor doubles during migration.
            report = self._pipeline.run_daily(context.aoi_name)
        return ProcessorResult(
            status=WorkflowStatus.SUCCESS,
            output={"report": report.model_dump(mode="json")},
            data_availability=report.data_availability,
        )


class UnavailableProcessor:
    """Explicit placeholder for a future processor; it never reports success."""

    processor_version = "unavailable-processor-v1"

    def __init__(self, *, reason_code: str, message: str) -> None:
        self._reason_code = reason_code
        self._message = message

    def execute(self, context: WorkflowContext) -> ProcessorResult:
        return ProcessorResult.unavailable(reason_code=self._reason_code, message=self._message)


def run_flood_daily_workflow(
    aoi_name: str,
    *,
    pipeline: FloodMonitoringPipeline | None = None,
    retry: bool = False,
    repository: WorkflowRepository | None = None,
) -> WorkflowExecution:
    resolved_pipeline = pipeline or FloodMonitoringPipeline()
    app_mode = getattr(resolved_pipeline, "app_mode", settings.app_mode)
    context = WorkflowContext(
        run_id=str(uuid4()),
        workflow_name="flood_daily",
        aoi_name=aoi_name,
        app_mode=app_mode,
        input_versions={
            "processing_version": "sar-preprocess-v1",
            "threshold_version": "alert-thresholds-v1",
            "runtime_date": datetime.now(UTC).date().isoformat(),
            "thresholds": settings.thresholds.model_dump_json(),
        },
    )
    definition = WorkflowDefinition(
        name="flood_daily",
        tasks=(
            WorkflowTaskSpec(
                name="flood_daily_processing",
                processor=FloodDailyProcessor(resolved_pipeline),
                max_attempts=settings.workflow_max_attempts,
            ),
        ),
    )
    resolved_repository = repository or WorkflowRepository(
        auto_create_for_non_operational=app_mode is not AppMode.OPERATIONAL,
    )
    execution = WorkflowEngine(resolved_repository).execute(definition, context, retry=retry)
    if execution.run.status.value == "degraded":
        for task in execution.tasks:
            payload = task.result.get("integrity_error")
            if isinstance(payload, dict):
                observations = {
                    name: ScientificObservation.model_validate(observation)
                    for name, observation in (payload.get("observations") or {}).items()
                }
                raise OperationalDataIntegrityError(str(payload.get("message") or task.error_message), observations=observations)
    return execution


def run_unavailable_workflow_task(
    task_name: str,
    *,
    aoi_name: str = "Indus-Lower",
    app_mode: AppMode | None = None,
    repository: WorkflowRepository | None = None,
) -> WorkflowExecution:
    """Compatibility bridge for former string-only workflow entrypoints."""

    resolved_mode = app_mode or settings.app_mode
    context = WorkflowContext(
        run_id=str(uuid4()),
        workflow_name=f"legacy_{task_name}",
        aoi_name=aoi_name,
        app_mode=resolved_mode,
        input_versions={"runtime_date": datetime.now(UTC).date().isoformat(), "adapter": "legacy-workflow-shim-v1"},
    )
    definition = WorkflowDefinition(
        name=context.workflow_name,
        tasks=(
            WorkflowTaskSpec(
                name=task_name,
                processor=UnavailableProcessor(
                    reason_code="processor_not_implemented",
                    message=f"The '{task_name}' processor is not implemented in the canonical runtime.",
                ),
                max_attempts=settings.workflow_max_attempts,
            ),
        ),
    )
    resolved_repository = repository or WorkflowRepository(
        auto_create_for_non_operational=resolved_mode is not AppMode.OPERATIONAL,
    )
    return WorkflowEngine(resolved_repository).execute(definition, context)
