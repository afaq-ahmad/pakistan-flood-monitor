from __future__ import annotations

from pathlib import Path

from app.services.reference_sync import ReferenceSyncJob, ReferenceSyncSuite


if __name__ == "__main__":
    root = Path("./tmp/reference_layers")
    source = Path("./README.md")
    suite = ReferenceSyncSuite(ReferenceSyncJob(root))

    print(suite.run_dem_sync(source, version="v1", source_date="2026-01-01"))
    print(suite.run_water_mask_sync(source, version="v1", source_date="2026-01-01"))
    print(suite.run_exposure_sync(source, version="v1", source_date="2026-01-01"))
