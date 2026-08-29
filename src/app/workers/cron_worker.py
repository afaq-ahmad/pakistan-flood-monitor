"""Deprecated cron entrypoint; delegates to the canonical worker."""
from pakistan_flood_monitor.workers import run_daily_worker


if __name__ == "__main__":
    print(run_daily_worker("Indus-Lower"))
