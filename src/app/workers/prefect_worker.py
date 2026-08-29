"""Deprecated Prefect bridge; no longer imports legacy workflow placeholders."""
from pakistan_flood_monitor.workers import run_daily_worker


def run_prefect_wrapper() -> dict:
    return run_daily_worker("Indus-Lower")
