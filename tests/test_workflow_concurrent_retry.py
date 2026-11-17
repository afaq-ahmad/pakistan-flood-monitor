from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.database import Base
from pakistan_flood_monitor.workflow.contracts import ProcessorResult, WorkflowContext, WorkflowDefinition, WorkflowStatus, WorkflowTaskSpec
from pakistan_flood_monitor.workflow.engine import WorkflowEngine
from pakistan_flood_monitor.workflow.repository import WorkflowRepository


def test_retry_does_not_start_while_first_worker_is_active(tmp_path):
    db = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    Base.metadata.create_all(db)
    repository = WorkflowRepository(sessionmaker(bind=db))
    entered, release, second_started = Event(), Event(), Event()
    calls = []
    lock = Lock()

    class Processor:
        processor_version = "test"
        def execute(self, context):
            with lock:
                calls.append(context.run_id)
                if len(calls) > 1:
                    second_started.set()
            entered.set()
            assert release.wait(5)
            return ProcessorResult(status=WorkflowStatus.SUCCESS)

    context = WorkflowContext(run_id="first", workflow_name="test", aoi_name="aoi", app_mode=AppMode.TEST, input_versions={"v": "1"})
    definition = WorkflowDefinition(name="test", tasks=(WorkflowTaskSpec("work", Processor()),))
    engine = WorkflowEngine(repository)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(engine.execute, definition, context)
        assert entered.wait(5)
        retry = pool.submit(engine.execute, definition, replace(context, run_id="retry"), retry=True)
        try:
            assert not second_started.wait(1), "retry ran concurrently with the original processor"
        finally:
            release.set()
        first.result(timeout=5)
        retry.result(timeout=5)
    assert calls == ["first"]


def test_retry_uses_persisted_run_identity(tmp_path):
    db = create_engine(f"sqlite:///{tmp_path / 'identity.db'}")
    Base.metadata.create_all(db)
    repository = WorkflowRepository(sessionmaker(bind=db))
    calls = []

    class Processor:
        processor_version = "test"
        def execute(self, context):
            calls.append(context.run_id)
            if len(calls) == 1:
                raise RuntimeError("transient")
            return ProcessorResult(status=WorkflowStatus.SUCCESS)

    import pytest
    context = WorkflowContext(run_id="original", workflow_name="test", aoi_name="aoi", app_mode=AppMode.TEST, input_versions={"v": "1"})
    definition = WorkflowDefinition(name="test", tasks=(WorkflowTaskSpec("work", Processor()),))
    engine = WorkflowEngine(repository)
    with pytest.raises(RuntimeError):
        engine.execute(definition, context)
    execution = engine.execute(definition, replace(context, run_id="new-request"), retry=True)
    assert execution.run.id == "original"
    assert calls == ["original", "original"]


def test_only_one_concurrent_terminal_retry_is_executed(tmp_path):
    db = create_engine(f"sqlite:///{tmp_path / 'terminal.db'}")
    Base.metadata.create_all(db)
    repository = WorkflowRepository(sessionmaker(bind=db))
    entered, release, duplicate = Event(), Event(), Event()
    calls = []
    lock = Lock()

    class Processor:
        processor_version = "test"
        def execute(self, context):
            with lock:
                calls.append(context.run_id)
                count = len(calls)
            if count == 1:
                raise RuntimeError("transient")
            if count > 2:
                duplicate.set()
            entered.set()
            assert release.wait(5)
            return ProcessorResult(status=WorkflowStatus.SUCCESS)

    import pytest
    context = WorkflowContext(run_id="original", workflow_name="test", aoi_name="aoi", app_mode=AppMode.TEST, input_versions={"v": "1"})
    definition = WorkflowDefinition(name="test", tasks=(WorkflowTaskSpec("work", Processor()),))
    engine = WorkflowEngine(repository)
    with pytest.raises(RuntimeError):
        engine.execute(definition, context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(engine.execute, definition, replace(context, run_id="request-1"), retry=True)
        assert entered.wait(5)
        second = pool.submit(engine.execute, definition, replace(context, run_id="request-2"), retry=True)
        try:
            assert not duplicate.wait(1)
            other = second.result(timeout=5)
            assert other.run.status is WorkflowStatus.RUNNING
            assert other.reused
        finally:
            release.set()
        assert first.result(timeout=5).run.status is WorkflowStatus.SUCCESS
    assert calls == ["original", "original"]


def test_api_reports_active_run_without_claiming_completion(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from pakistan_flood_monitor.api import main

    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setattr(main, "run_flood_daily_workflow", lambda *_a, **_kw: SimpleNamespace(
        run=SimpleNamespace(id="active-run", status=WorkflowStatus.RUNNING),
        tasks=(SimpleNamespace(result={"report": {"run_id": "stale"}}),)))
    main.rate_limiter.reset()
    response = TestClient(main.app).get("/internal/run/aoi", headers={"Authorization": "Bearer admin-secret"})
    assert response.status_code == 409
    assert response.json()["detail"] == {"error": "workflow_in_progress", "run_id": "active-run", "status": "running"}


def test_api_does_not_return_stale_report_after_failed_retry(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from pakistan_flood_monitor.api import main

    monkeypatch.setenv("FLOOD_MONITOR_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setattr(main, "run_flood_daily_workflow", lambda *_a, **_kw: SimpleNamespace(
        run=SimpleNamespace(id="failed-run", status=WorkflowStatus.FAILED),
        tasks=(SimpleNamespace(result={"report": {"run_id": "stale"}}),)))
    main.rate_limiter.reset()
    response = TestClient(main.app).get("/internal/run/aoi", headers={"Authorization": "Bearer admin-secret"})
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "workflow_not_successful"
