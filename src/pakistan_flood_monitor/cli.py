"""Command-line interface for the canonical API/worker runtime."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Sequence

from pakistan_flood_monitor.config import AppMode, settings
from pakistan_flood_monitor.models.observations import OperationalDataIntegrityError
from pakistan_flood_monitor.workflow.flood_daily import run_flood_daily_workflow
from pakistan_flood_monitor.workflow.repository import WorkflowRepository


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="flood-monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Execute the canonical daily flood workflow")
    run_parser.add_argument("--aoi", required=True)
    run_parser.add_argument("--retry", action="store_true", help="Retry a degraded/failed run with the same signature")
    status_parser = subparsers.add_parser("run-status", help="Read a durable canonical workflow run")
    status_parser.add_argument("run_id")
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            execution = run_flood_daily_workflow(args.aoi, retry=args.retry)
        except OperationalDataIntegrityError as exc:
            print(json.dumps(exc.as_dict(), indent=2, sort_keys=True))
            return 2
        print(json.dumps(execution.as_dict(), indent=2, sort_keys=True, default=str))
        return 0

    repository = WorkflowRepository(auto_create_for_non_operational=settings.app_mode is not AppMode.OPERATIONAL)
    run = repository.get_run(args.run_id)
    if run is None:
        parser.error(f"Workflow run '{args.run_id}' was not found")
    tasks = repository.list_tasks(args.run_id)
    print(json.dumps({"run_id": run.id, "status": run.status.value, "metadata": run.metadata, "tasks": [asdict(task) for task in tasks]}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
