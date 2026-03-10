from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Polygon, mapping

from app.services.review import review_service


@dataclass
class DashboardEvent:
    event_id: str
    corridor_id: str
    event_type: str
    confidence: float
    status: str
    detected_at: datetime
    geometry: MultiPolygon


class DashboardService:
    """Provides API-ready dashboard and map payloads from preprocessed event state."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._events: list[DashboardEvent] = [
            DashboardEvent(
                event_id="evt-indus-001",
                corridor_id="Indus-Lower",
                event_type="flood",
                confidence=0.82,
                status="published",
                detected_at=now - timedelta(hours=8),
                geometry=MultiPolygon([
                    Polygon([(68.30, 25.45), (68.48, 25.45), (68.48, 25.58), (68.30, 25.58), (68.30, 25.45)]),
                ]),
            ),
            DashboardEvent(
                event_id="evt-indus-002",
                corridor_id="Indus-Lower",
                event_type="flood",
                confidence=0.67,
                status="active",
                detected_at=now - timedelta(hours=4),
                geometry=MultiPolygon([
                    Polygon([(68.52, 25.54), (68.63, 25.54), (68.63, 25.66), (68.52, 25.66), (68.52, 25.54)]),
                ]),
            ),
            DashboardEvent(
                event_id="evt-chenab-001",
                corridor_id="Chenab-Middle",
                event_type="possible_breach",
                confidence=0.74,
                status="active",
                detected_at=now - timedelta(hours=5),
                geometry=MultiPolygon([
                    Polygon([(72.54, 31.13), (72.62, 31.13), (72.62, 31.21), (72.54, 31.21), (72.54, 31.13)]),
                ]),
            ),
        ]
        self._corridor_centerlines: dict[str, LineString] = {
            "Indus-Lower": LineString([(68.24, 25.30), (68.70, 25.82)]),
            "Chenab-Middle": LineString([(72.40, 31.00), (72.70, 31.33)]),
        }
        self._snapshot_dir = Path(".cache/dashboard_snapshots")
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _confidence_band(confidence: float) -> str:
        if confidence < 0.5:
            return "low"
        if confidence < 0.75:
            return "medium"
        return "high"

    def list_events(self, corridor_id: str | None = None) -> list[DashboardEvent]:
        if corridor_id is None:
            return list(self._events)
        return [event for event in self._events if event.corridor_id == corridor_id]

    def dashboard_view(self, corridor_id: str) -> dict:
        events = self.list_events(corridor_id)
        active_events = [event for event in events if event.status == "active"]
        published_events = [event for event in events if event.status == "published"]
        avg_confidence = round(sum(event.confidence for event in events) / len(events), 3) if events else 0.0

        recent_events = sorted(events, key=lambda item: item.detected_at, reverse=True)[:5]
        return {
            "corridor_id": corridor_id,
            "generated_at": datetime.now(UTC),
            "active_events": len(active_events),
            "published_events": len(published_events),
            "average_confidence": avg_confidence,
            "recent_events": [
                {
                    "event_id": event.event_id,
                    "corridor_id": event.corridor_id,
                    "event_type": event.event_type,
                    "confidence": event.confidence,
                    "status": event.status,
                    "detected_at": event.detected_at,
                }
                for event in recent_events
            ],
        }

    def review_dashboard(
        self,
        *,
        corridor_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_class: str | None = None,
        review_status: str | None = None,
        breach_suspicion_min: float | None = None,
        confidence_band: str | None = None,
    ) -> dict:
        items = review_service.list_queue(
            corridor_id=corridor_id,
            candidate_class=event_class,
            review_status=review_status,
            detected_after=date_from,
            detected_before=date_to,
            breach_suspicion_min=breach_suspicion_min,
            confidence_band=confidence_band,
        )

        queue = [
            {
                "candidate_id": item.candidate.candidate_id,
                "corridor_id": item.candidate.corridor_id,
                "district": item.candidate.district,
                "detected_at": item.candidate.detected_at,
                "review_status": item.status,
                "event_class": item.candidate_class,
                "confidence": round(item.candidate.confidence, 3),
                "confidence_band": self._confidence_band(item.candidate.confidence),
                "breach_suspicion": round(item.candidate.breach_suspicion, 3),
                "analyst_confidence": item.analyst_confidence,
                "context_links": {
                    "before_sar": item.candidate.before_sar_url,
                    "after_sar": item.candidate.after_sar_url,
                    "anomaly_mask": f"/analytics/map/events?corridor_id={item.candidate.corridor_id}",
                    "flood_candidates": f"/admin/review/{item.candidate.candidate_id}",
                    "embankments": f"/analytics/map/corridors?corridor_id={item.candidate.corridor_id}",
                    "seasonal_permanent_water": item.candidate.baseline_overlay_url,
                    "districts": f"/analytics/map/events?corridor_id={item.candidate.corridor_id}",
                    "optical_support": item.candidate.optical_support_url,
                },
            }
            for item in items
        ]

        return {
            "generated_at": datetime.now(UTC),
            "layer_toggles": {
                "previous_sar": True,
                "current_sar": True,
                "anomaly_mask": True,
                "flood_candidate_polygons": True,
                "embankments": True,
                "seasonal_permanent_water": True,
                "districts": True,
                "optical_support": False,
            },
            "action_controls": {
                "accept_reject": True,
                "class_selection": ["flood", "breach", "ponding", "artifact"],
                "note_entry": True,
                "confidence_adjustment": {"min": 0.0, "max": 1.0, "step": 0.05},
                "publish_action": True,
            },
            "applied_filters": {
                "corridor": corridor_id,
                "date_from": date_from,
                "date_to": date_to,
                "event_class": event_class,
                "review_status": review_status,
                "breach_suspicion_min": breach_suspicion_min,
                "confidence_band": confidence_band,
            },
            "queue_size": len(queue),
            "queue": queue,
        }

    def map_ready_event_layer(self, corridor_id: str | None = None, simplify_tolerance: float = 0.005) -> dict:
        events = self.list_events(corridor_id)
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": event.event_id,
                    "geometry": mapping(event.geometry.simplify(simplify_tolerance, preserve_topology=True)),
                    "properties": {
                        "event_id": event.event_id,
                        "corridor_id": event.corridor_id,
                        "event_type": event.event_type,
                        "confidence": round(event.confidence, 3),
                        "status": event.status,
                        "detected_at": event.detected_at.isoformat(),
                    },
                }
                for event in events
            ],
        }

    def map_ready_corridor_layer(self, corridor_id: str | None = None) -> dict:
        items = self._corridor_centerlines.items() if corridor_id is None else [(corridor_id, self._corridor_centerlines[corridor_id])]
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": key,
                    "geometry": mapping(line),
                    "properties": {"corridor_id": key, "layer": "centerline"},
                }
                for key, line in items
            ],
        }

    def precompute_snapshots(self, event_ids: list[str] | None = None) -> list[dict]:
        selected_events = self._events if not event_ids else [event for event in self._events if event.event_id in event_ids]
        records: list[dict] = []
        for event in selected_events:
            output_path = self._snapshot_dir / f"{event.event_id}.png"
            self._write_snapshot_png(output_path, event)
            records.append(
                {
                    "event_id": event.event_id,
                    "corridor_id": event.corridor_id,
                    "generated_at": datetime.now(UTC),
                    "snapshot_path": str(output_path),
                    "snapshot_url": f"/analytics/snapshots/{event.event_id}",
                    "width": 512,
                    "height": 512,
                }
            )
        return records

    def snapshot_path(self, event_id: str) -> Path:
        return self._snapshot_dir / f"{event_id}.png"

    def _write_snapshot_png(self, output_path: Path, event: DashboardEvent) -> None:
        width, height = 512, 512
        pixels = bytearray(width * height * 3)

        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 3
                pixels[idx : idx + 3] = b"\xf3\xf6\xfb"

        minx, miny, maxx, maxy = event.geometry.bounds

        def to_pixel(x: float, y: float) -> tuple[int, int]:
            px = int(((x - minx) / max(maxx - minx, 1e-6)) * (width - 1))
            py = int((1.0 - ((y - miny) / max(maxy - miny, 1e-6))) * (height - 1))
            return max(0, min(width - 1, px)), max(0, min(height - 1, py))

        for poly in event.geometry.geoms:
            for x, y in poly.exterior.coords:
                px, py = to_pixel(x, y)
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            idx = (ny * width + nx) * 3
                            pixels[idx : idx + 3] = b"\xdb\x3f\x3f"

        self._save_png(output_path, width, height, bytes(pixels))

    @staticmethod
    def _save_png(path: Path, width: int, height: int, rgb_data: bytes) -> None:
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        raw = bytearray()
        stride = width * 3
        for row in range(height):
            raw.append(0)
            start = row * stride
            raw.extend(rgb_data[start : start + stride])

        png = bytearray(b"\x89PNG\r\n\x1a\n")
        png.extend(chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)))
        png.extend(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        png.extend(chunk(b"IEND", b""))
        path.write_bytes(png)


dashboard_service = DashboardService()
