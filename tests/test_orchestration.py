from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.orchestration import (
    CandidateScene,
    CorridorState,
    HydrometSummary,
    IdempotentTaskWorker,
    InMemoryOutputStore,
    InMemoryRunStateRepository,
    InMemoryTaskQueueRepository,
    RetryTask,
    RunSignature,
    TaskPlannerJob,
    TASK_PREPROCESS_S1,
    TASK_REFRESH_DASHBOARD_CACHE,
    TASK_STATUS_FAILED,
    TASK_STATUS_MANUAL_RETRY_REQUESTED,
    TASK_STATUS_SKIPPED,
    TASK_STATUS_SUCCESS,
)


def test_task_planner_ranks_retry_backlog_highest_and_persists_statuses() -> None:
    queue_repo = InMemoryTaskQueueRepository()
    planner = TaskPlannerJob(queue_repo)
    now = datetime(2026, 1, 10, tzinfo=UTC)

    tasks = planner.plan(
        scenes=[
            CandidateScene(
                scene_id="S1-A",
                corridor_id="indus-lower",
                sensor="sentinel-1",
                acquisition_time=now - timedelta(hours=6),
                discovered_at=now - timedelta(hours=5),
            )
        ],
        hydromet_summaries=[
            HydrometSummary(
                corridor_id="indus-lower",
                observed_at=now - timedelta(hours=4),
                stress_score=0.93,
                warning_exceedance=True,
            )
        ],
        active_corridors=[CorridorState(corridor_id="indus-lower", operational_priority=5)],
        analyst_followup_waiting={"indus-lower"},
        retry_backlog=[RetryTask(task_type="run_flood_detection", corridor_id="indus-lower", scene_id="S1-X")],
        now=now,
    )

    assert tasks
    assert queue_repo.rows[0]["status"] == TASK_STATUS_MANUAL_RETRY_REQUESTED
    assert queue_repo.rows[0]["task_type"] == "run_flood_detection"
    assert any(row["task_type"] == TASK_PREPROCESS_S1 for row in queue_repo.rows)
    assert any(row["task_type"] == TASK_REFRESH_DASHBOARD_CACHE for row in queue_repo.rows)


def test_idempotent_worker_skips_when_run_hash_success_exists() -> None:
    run_state = InMemoryRunStateRepository()
    outputs = InMemoryOutputStore()
    worker = IdempotentTaskWorker(run_state, outputs)

    signature = RunSignature(
        scene_id="S1-A",
        corridor_id="indus-lower",
        pipeline_version="1.0.0",
        threshold_config_version="2026.01",
    )
    output_files = ["s3://derived/indus-lower/S1-A/flood.tif"]
    outputs.outputs.update(output_files)
    run_state.save(signature.run_hash, {"status": TASK_STATUS_SUCCESS, "outputs": output_files})

    status = worker.execute(signature=signature, expected_outputs=output_files, processor=lambda: None)

    assert status == TASK_STATUS_SKIPPED


def test_idempotent_worker_cleans_partial_outputs_after_failure() -> None:
    run_state = InMemoryRunStateRepository()
    outputs = InMemoryOutputStore()
    worker = IdempotentTaskWorker(run_state, outputs)

    signature = RunSignature(
        scene_id="S1-B",
        corridor_id="indus-mid",
        pipeline_version="1.0.0",
        threshold_config_version="2026.01",
    )
    output_files = ["s3://derived/indus-mid/S1-B/flood.tif"]
    outputs.outputs.update(output_files)

    try:
        worker.execute(signature=signature, expected_outputs=output_files, processor=lambda: (_ for _ in ()).throw(RuntimeError))
    except RuntimeError:
        pass

    assert output_files[0] not in outputs.outputs
    assert run_state.states[signature.run_hash]["status"] == TASK_STATUS_FAILED

    status = worker.execute(
        signature=signature,
        expected_outputs=output_files,
        processor=lambda: outputs.outputs.update(output_files),
    )
    assert status == TASK_STATUS_SUCCESS
