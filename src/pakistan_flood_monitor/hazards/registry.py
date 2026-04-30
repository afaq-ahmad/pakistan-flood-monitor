from __future__ import annotations

from pakistan_flood_monitor.hazards.base import HazardModule


class HazardRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, HazardModule] = {}

    def register(self, module: HazardModule) -> None:
        self._modules[module.hazard_type] = module

    def get(self, hazard_type: str) -> HazardModule:
        try:
            return self._modules[hazard_type]
        except KeyError as exc:
            known = ", ".join(sorted(self._modules)) or "none"
            raise ValueError(f"Hazard '{hazard_type}' is not registered. Registered hazards: {known}") from exc

    def registered_hazards(self) -> list[str]:
        return sorted(self._modules)
