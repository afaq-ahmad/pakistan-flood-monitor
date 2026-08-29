"""SQLAlchemy persistence for canonical workflow runs and tasks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.database import Base, SessionLocal, engine
from pakistan_flood_monitor.models.db_models import PipelineRun, PipelineTask
from pakistan_flood_monitor.workflow.contracts import WorkflowContext, WorkflowDefinition, WorkflowStatus


@dataclass(frozen=True, slots=True)
class PersistentRun:
    id: str
    aoi_name: str
    status: WorkflowStatus
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PersistentTask:
    id: str
    run_id: str
    name: str
    order: int
    status: WorkflowStatus
    dependencies: tuple[str, ...]
    attempt_count: int
    max_attempts: int
    result: dict[str, Any]
    data_availability: str | None
    error_code: str | None
    error_message: str | None


class WorkflowRepository:
    def __init__(
        self,
        session_factory: Callable[[], Any] = SessionLocal,
        *,
        auto_create_for_non_operational: bool = False,
    ) -> None:
        self._session_factory = session_factory
        if auto_create_for_non_operational:
            # Demo/test fixtures have no deployment migration step.  Production
            # deployments must use Alembic; this only creates the new table when
            # the existing local development schema is already present.
            Base.metadata.create_all(bind=engine)

    @staticmethod
    def _run(model: PipelineRun) -> PersistentRun:
        return PersistentRun(
            id=model.id,
            aoi_name=model.corridor_aoi,
            status=WorkflowStatus(model.status),
            metadata=dict(model.run_metadata or {}),
        )

    @staticmethod
    def _task(model: PipelineTask) -> PersistentTask:
        return PersistentTask(
            id=model.id,
            run_id=model.run_id,
            name=model.task_name,
            order=model.task_order,
            status=WorkflowStatus(model.status),
            dependencies=tuple(model.dependencies or []),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            result=dict(model.result_metadata or {}),
            data_availability=model.data_availability,
            error_code=model.error_code,
            error_message=model.error_message,
        )

    def find_by_signature(self, signature: str) -> PersistentRun | None:
        with self._session_factory() as session:
            task = session.scalar(select(PipelineTask).where(PipelineTask.run_signature == signature).limit(1))
            return self._run(task.pipeline_run) if task else None

    def create_or_get(
        self,
        *,
        definition: WorkflowDefinition,
        context: WorkflowContext,
        signature: str,
    ) -> tuple[PersistentRun, bool]:
        existing = self.find_by_signature(signature)
        if existing:
            return existing, False

        with self._session_factory() as session:
            run = PipelineRun(
                id=context.run_id,
                corridor_aoi=context.aoi_name,
                status=WorkflowStatus.QUEUED.value,
                run_metadata={
                    "workflow_name": definition.name,
                    "run_signature": signature,
                    "app_mode": context.app_mode.value,
                    "input_versions": dict(context.input_versions),
                    "requested_at": context.requested_at.isoformat(),
                    "metadata": dict(context.metadata),
                },
            )
            session.add(run)
            for order, task in enumerate(definition.ordered_tasks()):
                session.add(
                    PipelineTask(
                        id=str(uuid4()),
                        run_id=context.run_id,
                        task_name=task.name,
                        task_order=order,
                        run_signature=signature,
                        status=WorkflowStatus.QUEUED.value,
                        dependencies=list(task.dependencies),
                        max_attempts=task.max_attempts,
                        input_metadata={
                            "processor_version": task.processor.processor_version,
                            "input_versions": dict(context.input_versions),
                        },
                    )
                )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = self.find_by_signature(signature)
                if existing:
                    return existing, False
                raise
            return self._run(run), True

    def get_run(self, run_id: str) -> PersistentRun | None:
        with self._session_factory() as session:
            model = session.get(PipelineRun, run_id)
            return self._run(model) if model else None

    def list_tasks(self, run_id: str) -> list[PersistentTask]:
        with self._session_factory() as session:
            models = session.scalars(select(PipelineTask).where(PipelineTask.run_id == run_id).order_by(PipelineTask.task_order)).all()
            return [self._task(model) for model in models]

    def update_task(
        self,
        task_id: str,
        *,
        status: WorkflowStatus,
        attempt_count: int | None = None,
        result: dict[str, Any] | None = None,
        data_availability: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> PersistentTask:
        with self._session_factory() as session:
            task = session.get(PipelineTask, task_id)
            if task is None:
                raise KeyError(f"Pipeline task '{task_id}' does not exist")
            task.status = status.value
            if attempt_count is not None:
                task.attempt_count = attempt_count
            if result is not None:
                task.result_metadata = result
            if data_availability is not None:
                task.data_availability = data_availability
            task.error_code = error_code
            task.error_message = error_message
            if started_at is not None:
                task.started_at = started_at
            if completed_at is not None:
                task.completed_at = completed_at
            session.commit()
            return self._task(task)

    def update_run(self, run_id: str, *, status: WorkflowStatus, metadata: dict[str, Any]) -> PersistentRun:
        with self._session_factory() as session:
            run = session.get(PipelineRun, run_id)
            if run is None:
                raise KeyError(f"Pipeline run '{run_id}' does not exist")
            run.status = status.value
            run.run_metadata = metadata
            if status in {WorkflowStatus.SUCCESS, WorkflowStatus.FAILED, WorkflowStatus.DEGRADED, WorkflowStatus.SKIPPED}:
                run.completed_at = datetime.now(UTC)
            session.commit()
            return self._run(run)

    def prepare_retry(self, run_id: str, *, force: bool = False) -> PersistentRun:
        with self._session_factory() as session:
            run = session.get(PipelineRun, run_id)
            if run is None:
                raise KeyError(f"Pipeline run '{run_id}' does not exist")
            tasks = session.scalars(select(PipelineTask).where(PipelineTask.run_id == run_id)).all()
            for task in tasks:
                if task.status == WorkflowStatus.SUCCESS.value and not force:
                    continue
                if task.attempt_count >= task.max_attempts:
                    continue
                task.status = WorkflowStatus.QUEUED.value
                task.error_code = None
                task.error_message = None
                task.completed_at = None
            run.status = WorkflowStatus.QUEUED.value
            run.completed_at = None
            session.commit()
            return self._run(run)
