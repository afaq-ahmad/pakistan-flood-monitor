"""Canonical worker entrypoints usable by cron or a future queue adapter."""
from __future__ import annotations

from typing import Any

from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline
from pakistan_flood_monitor.workflow.flood_daily import run_flood_daily_workflow


def run_daily_worker(aoi_name: str, *, retry: bool = False) -> dict[str, Any]:
    execution = run_flood_daily_workflow(aoi_name, pipeline=FloodMonitoringPipeline(), retry=retry)
    report = next((task.result.get("report") for task in execution.tasks if isinstance(task.result.get("report"), dict)), None)
    return {"workflow": execution.as_dict(), "report": report}
