from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol

from app.services.observability import log_failure, log_structured, metrics_registry

TASK_PREPROCESS_S1 = "preprocess_s1_scene"
TASK_PREPROCESS_OPTICAL = "preprocess_optical_scene"
TASK_RUN_FLOOD_DETECTION = "run_flood_detection"
TASK_RUN_BREACH_SCORING = "run_breach_scoring"
TASK_COMPUTE_EXPOSURE = "compute_exposure"
TASK_REFRESH_DASHBOARD_CACHE = "refresh_dashboard_cache"

TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_SKIPPED = "skipped"
TASK_STATUS_STALE = "stale"
TASK_STATUS_MANUAL_RETRY_REQUESTED = "manual_retry_requested"


@dataclass(slots=True)
class CandidateScene:
    scene_id: str
    corridor_id: str
    sensor: str
    acquisition_time: datetime
    discovered_at: datetime


@dataclass(slots=True)
class HydrometSummary:
    corridor_id: str
    observed_at: datetime
    stress_score: float
    warning_exceedance: bool


@dataclass(slots=True)
class CorridorState:
    corridor_id: str
    operational_priority: int
    is_active: bool = True


@dataclass(slots=True)
class RetryTask:
    task_type: str
    corridor_id: str
    scene_id: str | None = None
    requested_at: datetime | None = None


@dataclass(slots=True)
class PlannedTask:
    task_type: str
    corridor_id: str
    scene_id: str | None
    priority_score: float
    rank_reason: str
    status: str = TASK_STATUS_QUEUED
    payload: dict = field(default_factory=dict)


class TaskQueueRepository(Protocol):
    def insert(self, task: PlannedTask) -> int:
        ...


class TaskPlannerJob:
    """Generates concrete, ranked workflow tasks from corridor, scene, and hydromet state."""

    def __init__(self, task_repository: TaskQueueRepository) -> None:
        self._task_repository = task_repository

    def plan(
        self,
        *,
        scenes: list[CandidateScene],
        hydromet_summaries: list[HydrometSummary],
        active_corridors: list[CorridorState],
        analyst_followup_waiting: set[str] | None = None,
        retry_backlog: list[RetryTask] | None = None,
        now: datetime | None = None,
    ) -> list[PlannedTask]:
        now = now or datetime.utcnow()
        analyst_followup_waiting = analyst_followup_waiting or set()
        retry_backlog = retry_backlog or []

        corridor_lookup = {c.corridor_id: c for c in active_corridors if c.is_active}
        hydromet_lookup = {h.corridor_id: h for h in hydromet_summaries}

        planned: list[PlannedTask] = []

        for retry in retry_backlog:
            planned.append(
                PlannedTask(
                    task_type=retry.task_type,
                    corridor_id=retry.corridor_id,
                    scene_id=retry.scene_id,
                    priority_score=1_000.0,
                    rank_reason="manual retry backlog",
                    status=TASK_STATUS_MANUAL_RETRY_REQUESTED,
                    payload={"retry_requested_at": (retry.requested_at or now).isoformat()},
                )
            )

        for scene in scenes:
            corridor = corridor_lookup.get(scene.corridor_id)
            if corridor is None:
                continue
            hydromet = hydromet_lookup.get(scene.corridor_id)
            priority, reason = self._rank_task(
                corridor=corridor,
                scene=scene,
                hydromet=hydromet,
                followup_waiting=scene.corridor_id in analyst_followup_waiting,
                now=now,
            )
            planned.extend(self._scene_tasks(scene=scene, priority_score=priority, rank_reason=reason))

        for corridor in active_corridors:
            if not corridor.is_active:
                continue
            hydromet = hydromet_lookup.get(corridor.corridor_id)
            summary_priority = float(corridor.operational_priority * 10)
            if hydromet:
                summary_priority += hydromet.stress_score * 100
            planned.append(
                PlannedTask(
                    task_type=TASK_REFRESH_DASHBOARD_CACHE,
                    corridor_id=corridor.corridor_id,
                    scene_id=None,
                    priority_score=summary_priority,
                    rank_reason="corridor summary refresh",
                )
            )

        for task in sorted(planned, key=lambda item: item.priority_score, reverse=True):
            self._task_repository.insert(task)
        return planned

    def _scene_tasks(self, *, scene: CandidateScene, priority_score: float, rank_reason: str) -> list[PlannedTask]:
        preprocess_type = TASK_PREPROCESS_S1 if "sentinel-1" in scene.sensor.lower() else TASK_PREPROCESS_OPTICAL
        return [
            PlannedTask(
                task_type=preprocess_type,
                corridor_id=scene.corridor_id,
                scene_id=scene.scene_id,
                priority_score=priority_score,
                rank_reason=rank_reason,
            ),
            PlannedTask(
                task_type=TASK_RUN_FLOOD_DETECTION,
                corridor_id=scene.corridor_id,
                scene_id=scene.scene_id,
                priority_score=priority_score - 0.1,
                rank_reason=rank_reason,
            ),
            PlannedTask(
                task_type=TASK_RUN_BREACH_SCORING,
                corridor_id=scene.corridor_id,
                scene_id=scene.scene_id,
                priority_score=priority_score - 0.2,
                rank_reason=rank_reason,
            ),
            PlannedTask(
                task_type=TASK_COMPUTE_EXPOSURE,
                corridor_id=scene.corridor_id,
                scene_id=scene.scene_id,
                priority_score=priority_score - 0.3,
                rank_reason=rank_reason,
            ),
        ]

    @staticmethod
    def _rank_task(
        *, corridor: CorridorState, scene: CandidateScene, hydromet: HydrometSummary | None, followup_waiting: bool, now: datetime
    ) -> tuple[float, str]:
        score = float(corridor.operational_priority * 25)
        reasons = [f"corridor_priority={corridor.operational_priority}"]

        if hydromet:
            stress_boost = hydromet.stress_score * 100
            score += stress_boost
            reasons.append(f"hydromet_stress={hydromet.stress_score:.2f}")
            if hydromet.warning_exceedance:
                score += 35
                reasons.append("warning_exceedance")
            if scene.acquisition_time >= hydromet.observed_at - timedelta(hours=12):
                score += 30
                reasons.append("first_observation_after_spike")

        scene_age_hours = max(0.0, (now - scene.acquisition_time).total_seconds() / 3600)
        freshness_bonus = max(0.0, 72 - scene_age_hours) / 72 * 40
        score += freshness_bonus
        reasons.append(f"freshness_bonus={freshness_bonus:.1f}")

        if followup_waiting:
            score += 45
            reasons.append("analyst_followup_waiting")

        return score, ";".join(reasons)


@dataclass(slots=True)
class RunSignature:
    scene_id: str
    corridor_id: str
    pipeline_version: str
    threshold_config_version: str

    @property
    def run_hash(self) -> str:
        digest_input = "|".join(
            [self.scene_id, self.corridor_id, self.pipeline_version, self.threshold_config_version]
        )
        return sha256(digest_input.encode("utf-8")).hexdigest()


class RunStateRepository(Protocol):
    def get_successful(self, run_hash: str) -> dict | None:
        ...

    def save(self, run_hash: str, state: dict) -> None:
        ...


class OutputStore(Protocol):
    def outputs_exist(self, output_uris: list[str]) -> bool:
        ...

    def remove_partial_outputs(self, output_uris: list[str]) -> None:
        ...


class IdempotentTaskWorker:
    def __init__(self, run_state_repository: RunStateRepository, output_store: OutputStore) -> None:
        self._run_state_repository = run_state_repository
        self._output_store = output_store

    def execute(self, *, signature: RunSignature, expected_outputs: list[str], processor) -> str:
        run_hash = signature.run_hash
        start = datetime.now(UTC)
        checkpoint = "load_previous_state"
        previous_success = self._run_state_repository.get_successful(run_hash)
        if previous_success and self._output_store.outputs_exist(expected_outputs):
            metrics_registry.increment("ops.jobs_skipped")
            log_structured(
                "idempotent_worker",
                run_id=run_hash,
                corridor_id=signature.corridor_id,
                scene_id=signature.scene_id,
                task_type="idempotent_execute",
                duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
                success=True,
                status=TASK_STATUS_SKIPPED,
                output_paths=expected_outputs,
            )
            return TASK_STATUS_SKIPPED

        checkpoint = "cleanup_partial_outputs"
        if not previous_success and self._output_store.outputs_exist(expected_outputs):
            self._output_store.remove_partial_outputs(expected_outputs)

        checkpoint = "execute_processor"
        self._run_state_repository.save(run_hash, {"status": TASK_STATUS_RUNNING, "outputs": expected_outputs})
        try:
            processor()
        except Exception as exc:
            self._output_store.remove_partial_outputs(expected_outputs)
            self._run_state_repository.save(run_hash, {"status": TASK_STATUS_FAILED, "outputs": expected_outputs})
            metrics_registry.increment("ops.job_failures")
            log_failure(
                "idempotent_worker",
                error=exc,
                run_id=run_hash,
                corridor_id=signature.corridor_id,
                scene_id=signature.scene_id,
                task_type="idempotent_execute",
                pipeline_stage="task_worker",
                input_identifiers={"scene_id": signature.scene_id, "corridor_id": signature.corridor_id},
                last_completed_checkpoint=checkpoint,
                duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
                output_paths=expected_outputs,
            )
            raise

        self._run_state_repository.save(run_hash, {"status": TASK_STATUS_SUCCESS, "outputs": expected_outputs})
        metrics_registry.increment("ops.jobs_succeeded")
        log_structured(
            "idempotent_worker",
            run_id=run_hash,
            corridor_id=signature.corridor_id,
            scene_id=signature.scene_id,
            task_type="idempotent_execute",
            duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
            success=True,
            status=TASK_STATUS_SUCCESS,
            output_paths=expected_outputs,
        )
        return TASK_STATUS_SUCCESS


class InMemoryTaskQueueRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def insert(self, task: PlannedTask) -> int:
        row = {
            "id": len(self.rows) + 1,
            "task_type": task.task_type,
            "corridor_id": task.corridor_id,
            "scene_id": task.scene_id,
            "priority_score": task.priority_score,
            "rank_reason": task.rank_reason,
            "status": task.status,
            "payload": task.payload,
        }
        self.rows.append(row)
        return int(row["id"])


class InMemoryRunStateRepository:
    def __init__(self) -> None:
        self.states: dict[str, dict] = {}

    def get_successful(self, run_hash: str) -> dict | None:
        state = self.states.get(run_hash)
        if state and state.get("status") == TASK_STATUS_SUCCESS:
            return state
        return None

    def save(self, run_hash: str, state: dict) -> None:
        self.states[run_hash] = state


class InMemoryOutputStore:
    def __init__(self) -> None:
        self.outputs: set[str] = set()

    def outputs_exist(self, output_uris: list[str]) -> bool:
        return all(uri in self.outputs for uri in output_uris)

    def remove_partial_outputs(self, output_uris: list[str]) -> None:
        for uri in output_uris:
            self.outputs.discard(uri)
