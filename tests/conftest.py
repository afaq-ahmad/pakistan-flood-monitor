import os
import sys
import tempfile
from pathlib import Path

import pytest

# Unit and integration tests may use deterministic fixtures, but the runtime
# still labels them. Individual integrity tests explicitly exercise demo and
# operational modes.
# Never point the standard suite at a caller's database or enable operational
# mode accidentally. Integration tests needing another database create it explicitly.
_TEST_DATABASE_DIR = tempfile.TemporaryDirectory(prefix="flood-monitor-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TEST_DATABASE_DIR.name) / 'tests.db'}"
os.environ["APP_MODE"] = "test"

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# Deterministic fixtures for test-mode provider outages and prototype dam data.
# Individual tests can override these mocks when exercising provider behavior.
@pytest.fixture(autouse=True)
def _offline_prototype_fixtures(request, tmp_path):
    from pakistan_flood_monitor.data.sources import DataCatalog

    saved_env = {key: value for key, value in os.environ.items() if key.startswith("FLOOD_MONITOR_")}
    for key in saved_env:
        del os.environ[key]
    api_module = sys.modules.get("pakistan_flood_monitor.api.main")
    if api_module is not None:
        api_module.rate_limiter.reset()
    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(DataCatalog, "_get_client", lambda self: None)
        if request.path.name in {"test_backtesting.py", "test_dam_service.py"}:
            from src.pakistan_flood_monitor.services import dam_service

            patch.setattr(dam_service, "DAM_HISTORY", tmp_path)
            patch.setattr(dam_service, "_fetch_dam_thumbnail", lambda _dam: None)
            patch.setattr(dam_service.np.random, "normal", lambda *_args, **_kwargs: 0.0)
        yield
    finally:
        patch.undo()
        for key in list(os.environ):
            if key.startswith("FLOOD_MONITOR_"):
                del os.environ[key]
        os.environ.update(saved_env)
