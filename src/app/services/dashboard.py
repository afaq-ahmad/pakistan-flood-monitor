from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Polygon, mapping


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
