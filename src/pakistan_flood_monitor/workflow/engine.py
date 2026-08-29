"""Dependency-aware, idempotent execution for canonical processors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pakistan_flood_monitor.models.observations import OperationalDataIntegrityError
from pakistan_flood_monitor.workflow.contracts import (
    ProcessorResult,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowStatus,
    workflow_signature,
)
from pakistan_flood_monitor.workflow.repository import PersistentRun, PersistentTask, WorkflowRepository


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    run: PersistentRun
    tasks: tuple[PersistentTask, ...]
    reused: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run.id,
            "aoi_name": self.run.aoi_name,
            "status": self.run.status.value,
            "reused": self.reused,
            "metadata": self.run.metadata,
            "tasks": [
                {
                    "task_id": task.id,
                    "name": task.name,
                    "status": task.status.value,
                    "dependencies": list(task.dependencies),
                    "attempt_count": task.attempt_count,
                    "max_attempts": task.max_attempts,
                    "data_availability": task.data_availability,
                    "error_code": task.error_code,
                }
                for task in self.tasks
            ],
        }


class WorkflowEngine:
    def __init__(self, repository: WorkflowRepository) -> None:
        self._repository = repository

    def execute(
        self,
        definition: WorkflowDefinition,
        context: WorkflowContext,
        *,
        retry: bool = False,
    ) -> WorkflowExecution:
        signature = workflow_signature(context)
        run, created = self._repository.create_or_get(definition=definition, context=context, signature=signature)
        if not created:
            if run.status is WorkflowStatus.SUCCESS and not retry:
                return WorkflowExecution(run=run, tasks=tuple(self._repository.list_tasks(run.id)), reused=True)
            if not retry:
                return WorkflowExecution(run=run, tasks=tuple(self._repository.list_tasks(run.id)), reused=True)
            run = self._repository.prepare_retry(run.id, force=True)

        failure: OperationalDataIntegrityError | None = None
        tasks_by_name = {task.name: task for task in self._repository.list_tasks(run.id)}
        for spec in definition.ordered_tasks():
            task = tasks_by_name[spec.name]
            if task.status is WorkflowStatus.SUCCESS:
                continue
            dependency_states = [tasks_by_name[name].status for name in spec.dependencies]
            if any(state is not WorkflowStatus.SUCCESS for state in dependency_states):
                task = self._repository.update_task(
                    task.id,
                    status=WorkflowStatus.SKIPPED,
                    error_code="dependency_not_successful",
                    error_message="A required predecessor did not complete successfully.",
                    completed_at=datetime.now(UTC),
                )
                tasks_by_name[task.name] = task
                continue
            if task.attempt_count >= task.max_attempts:
                task = self._repository.update_task(
                    task.id,
                    status=WorkflowStatus.FAILED,
                    error_code="retry_limit_exhausted",
                    error_message="The task exhausted its configured retry limit.",
                    completed_at=datetime.now(UTC),
                )
                tasks_by_name[task.name] = task
                continue

            attempt = task.attempt_count + 1
            task = self._repository.update_task(task.id, status=WorkflowStatus.RUNNING, attempt_count=attempt, started_at=datetime.now(UTC))
            tasks_by_name[task.name] = task
            try:
                result = spec.processor.execute(context)
            except OperationalDataIntegrityError as exc:
                failure = exc
                task = self._repository.update_task(
                    task.id,
                    status=WorkflowStatus.DEGRADED,
                    data_availability=exc.as_dict()["data_availability"],
                    error_code="operational_data_integrity_error",
                    error_message=str(exc),
                    result={"integrity_error": exc.as_dict()},
                    completed_at=datetime.now(UTC),
                )
            except Exception as exc:
                task = self._repository.update_task(
                    task.id,
                    status=WorkflowStatus.FAILED,
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                    completed_at=datetime.now(UTC),
                )
                tasks_by_name[task.name] = task
                metadata = self._completed_metadata(run=run, signature=signature)
                self._repository.update_run(run.id, status=WorkflowStatus.FAILED, metadata=metadata)
                raise
            else:
                if result.status not in {WorkflowStatus.SUCCESS, WorkflowStatus.SKIPPED, WorkflowStatus.DEGRADED}:
                    raise ValueError(f"Processor '{spec.name}' returned unsupported terminal status '{result.status.value}'")
                task = self._repository.update_task(
                    task.id,
                    status=result.status,
                    result=dict(result.output),
                    data_availability=result.data_availability.value,
                    error_code=result.reason_code,
                    error_message=result.message,
                    completed_at=datetime.now(UTC),
                )
            tasks_by_name[task.name] = task

        tasks = tuple(self._repository.list_tasks(run.id))
        status = self._run_status(tasks)
        metadata = self._completed_metadata(run=run, signature=signature, tasks=tasks)
        run = self._repository.update_run(run.id, status=status, metadata=metadata)
        execution = WorkflowExecution(run=run, tasks=tasks, reused=False)
        if failure:
            raise failure
        return execution

    @staticmethod
    def _run_status(tasks: tuple[PersistentTask, ...]) -> WorkflowStatus:
        statuses = {task.status for task in tasks}
        if WorkflowStatus.FAILED in statuses:
            return WorkflowStatus.FAILED
        if WorkflowStatus.DEGRADED in statuses:
            return WorkflowStatus.DEGRADED
        if statuses and statuses.issubset({WorkflowStatus.SUCCESS, WorkflowStatus.SKIPPED}):
            return WorkflowStatus.SUCCESS
        return WorkflowStatus.QUEUED

    @staticmethod
    def _completed_metadata(
        *,
        run: PersistentRun,
        signature: str,
        tasks: tuple[PersistentTask, ...] = (),
    ) -> dict[str, Any]:
        metadata = dict(run.metadata)
        metadata["run_signature"] = signature
        metadata["completed_at"] = datetime.now(UTC).isoformat()
        metadata["task_results"] = {task.name: task.result for task in tasks}
        metadata["task_statuses"] = {task.name: task.status.value for task in tasks}
        return metadata
