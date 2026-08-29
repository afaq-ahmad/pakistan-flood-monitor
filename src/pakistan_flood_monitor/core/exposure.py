from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.pipeline.demo_fixtures import DemoFloodProductSimulator
from pakistan_flood_monitor.models.observations import OperationalDataIntegrityError
from pakistan_flood_monitor.models.schemas import ExposureStats


class ExposureAnalyzer:
    """Compatibility facade for the explicit test/demo exposure simulator.

    A real population and asset-overlay processor must replace this facade before
    operational exposure is enabled.
    """

    def __init__(self, app_mode: AppMode = AppMode.DEMO) -> None:
        self._app_mode = app_mode
        self._simulator = DemoFloodProductSimulator()

    def estimate_demo(self, flood_area_km2: float) -> ExposureStats:
        if self._app_mode is AppMode.OPERATIONAL:
            raise OperationalDataIntegrityError(
                "Operational exposure requires real hazard geometry and asset overlays; "
                "fixed area multipliers are demo-only."
            )
        return self._simulator.estimate_exposure(flood_area_km2)
