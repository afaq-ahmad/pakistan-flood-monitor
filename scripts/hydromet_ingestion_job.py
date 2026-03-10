from __future__ import annotations

from datetime import datetime

from app.services.hydromet import (
    GloFASFetcher,
    HydrometIngestionJob,
    IMERGRainfallFetcher,
    InMemoryHydrometRepository,
    SequenceRainfallProvider,
    StaticGloFASProvider,
)


if __name__ == "__main__":
    rainfall_provider = SequenceRainfallProvider(
        {
            24: [3.0] * 24,
            72: [2.0] * 72,
            168: [1.5] * 168,
        }
    )
    repo = InMemoryHydrometRepository()
    job = HydrometIngestionJob(
        rainfall_fetcher=IMERGRainfallFetcher(rainfall_provider),
        glofas_fetcher=GloFASFetcher(StaticGloFASProvider(percentile=0.92)),
        repository=repo,
    )
    summary = job.run(
        corridor_id="indus-lower",
        corridor_geometry={"type": "Polygon", "coordinates": []},
        timestamp=datetime.utcnow(),
        baseline_7d_mm=150.0,
    )
    print(summary)
