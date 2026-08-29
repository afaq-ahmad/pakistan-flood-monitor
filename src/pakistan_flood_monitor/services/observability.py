"""Canonical lightweight structured logging and in-process metrics facade."""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


LOGGER = logging.getLogger("pakistan_flood_monitor")


def log_structured(event: str, **fields: Any) -> None:
    LOGGER.info(json.dumps({"event": event, "timestamp": datetime.now(UTC).isoformat(), **fields}, default=str, sort_keys=True))


def log_failure(event: str, *, error: Exception, **fields: Any) -> None:
    log_structured(event, success=False, error_type=type(error).__name__, error_message=str(error), **fields)


@dataclass(slots=True)
class MetricsSnapshot:
    counters: dict[str, float]
    gauges: dict[str, float]
    latencies_ms: dict[str, dict[str, float]]


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._latency_samples: defaultdict[str, list[float]] = defaultdict(list)

    def increment(self, key: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, key: str, value: float) -> None:
        with self._lock:
            self._gauges[key] = value

    def observe_latency_ms(self, key: str, value_ms: float) -> None:
        with self._lock:
            self._latency_samples[key].append(value_ms)

    def time_block(self, key: str):
        start = time.perf_counter()

        def finish() -> float:
            elapsed = (time.perf_counter() - start) * 1000
            self.observe_latency_ms(key, elapsed)
            return elapsed

        return finish

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            latencies = {
                metric: {
                    "count": float(len(samples)),
                    "avg_ms": sum(samples) / len(samples),
                    "p95_ms": sorted(samples)[min(len(samples) - 1, int(len(samples) * 0.95))],
                    "max_ms": max(samples),
                }
                for metric, samples in self._latency_samples.items()
                if samples
            }
            return MetricsSnapshot(counters=dict(self._counters), gauges=dict(self._gauges), latencies_ms=latencies)


metrics_registry = MetricsRegistry()
