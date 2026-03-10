from pakistan_flood_monitor.models.schemas import ExposureStats


class ExposureAnalyzer:
    """Stub exposure analytics using population/infrastructure overlays."""

    def estimate(self, flood_area_km2: float) -> ExposureStats:
        return ExposureStats(
            affected_population=int(flood_area_km2 * 3100),
            affected_cropland_km2=round(flood_area_km2 * 0.46, 2),
            affected_roads_km=round(flood_area_km2 * 3.2, 2),
            affected_schools=max(1, int(flood_area_km2 / 20)),
            affected_hospitals=max(1, int(flood_area_km2 / 45)),
        )
