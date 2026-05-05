"""
NASA Data Service — Pakistan Flood Monitor
Uses authenticated NASA Earthdata APIs:
  1. NASA POWER  — daily rainfall, temperature, humidity (no auth needed, but we use it)
  2. NASA CMR    — IMERG precipitation collections, HLS scenes
  3. NASA FIRMS  — Fire/thermal anomaly data (bonus)

Bearer token from .env.local is used for CMR authenticated requests.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

# ── Credentials from env ──────────────────────────────────────────────────────
NASA_BEARER    = os.getenv("NASA_BEARER_TOKEN", "")
NASA_USERNAME  = os.getenv("NASA_EARTHDATA_USERNAME", "")
NASA_PASSWORD  = os.getenv("NASA_EARTHDATA_PASSWORD", "")

POWER_BASE = "https://power.larc.nasa.gov/api/temporal"
CMR_STAC   = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"
CMR_SEARCH = "https://cmr.earthdata.nasa.gov/search"

# Corridor coordinates (lon, lat) for point queries
CORRIDOR_POINTS = {
    "Indus-Lower":   (67.78, 26.73),
    "Indus-Upper":   (72.50, 34.00),
    "Chenab-Middle": (72.98, 31.72),
    "Jhelum-Lower":  (73.04, 32.59),
    "Sutlej-Lower":  (71.05, 29.22),
    "Kabul-Nowshera":(71.99, 34.01),
}

# Corridor bboxes for area searches
CORRIDOR_BBOXES = {
    "Indus-Lower":   [66.8, 25.2, 69.5, 27.8],
    "Indus-Upper":   [70.5, 33.0, 74.0, 34.5],
    "Chenab-Middle": [71.5, 30.5, 73.5, 32.2],
    "Jhelum-Lower":  [72.8, 32.0, 74.2, 33.2],
    "Sutlej-Lower":  [70.2, 28.5, 72.5, 30.5],
    "Kabul-Nowshera":[71.5, 33.8, 72.8, 34.6],
}

FLOOD_RISK_THRESHOLDS = {
    "rain_72h_warning_mm": 50.0,
    "rain_72h_critical_mm": 100.0,
    "rain_7d_warning_mm": 120.0,
    "rain_7d_critical_mm": 200.0,
}


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {NASA_BEARER}"} if NASA_BEARER else {}


# ── POWER API ─────────────────────────────────────────────────────────────────

def fetch_power_daily(
    lon: float, lat: float,
    start: date, end: date,
    parameters: str = "PRECTOTCORR,T2M,RH2M,WS2M,ALLSKY_SFC_SW_DWN",
) -> dict:
    """
    Fetch NASA POWER daily climate data for a point.
    Returns dict of parameter → {date_str: value}.
    -999.0 means missing data.
    """
    url = (
        f"{POWER_BASE}/daily/point"
        f"?parameters={parameters}&community=RE"
        f"&longitude={lon}&latitude={lat}"
        f"&start={start.strftime('%Y%m%d')}&end={end.strftime('%Y%m%d')}"
        f"&format=JSON"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json().get("properties", {}).get("parameter", {})
    except Exception as exc:
        return {"error": str(exc)}


def fetch_corridor_rainfall(
    corridor: str, days_back: int = 30
) -> dict:
    """
    Fetch rainfall time series for a corridor plus computed metrics.
    Returns a structured dict ready for the dashboard.
    """
    lon, lat = CORRIDOR_POINTS.get(corridor, (70.0, 30.0))
    end_dt   = date.today()
    start_dt = end_dt - timedelta(days=days_back)

    raw = fetch_power_daily(lon, lat, start_dt, end_dt)
    if "error" in raw:
        return {"corridor": corridor, "error": raw["error"]}

    prec_raw  = raw.get("PRECTOTCORR", {})
    temp_raw  = raw.get("T2M", {})
    humid_raw = raw.get("RH2M", {})
    wind_raw  = raw.get("WS2M", {})

    # Filter missing
    prec  = {k: v for k, v in prec_raw.items()  if v != -999.0}
    temp  = {k: v for k, v in temp_raw.items()  if v != -999.0}
    humid = {k: v for k, v in humid_raw.items() if v != -999.0}
    wind  = {k: v for k, v in wind_raw.items()  if v != -999.0}

    vals = list(prec.values())
    dates = sorted(prec.keys())

    # 72h and 7d rainfall totals
    rain_72h = sum(vals[-3:]) if len(vals) >= 3 else sum(vals)
    rain_7d  = sum(vals[-7:]) if len(vals) >= 7 else sum(vals)
    rain_30d = sum(vals)

    # Risk assessment
    if rain_72h >= FLOOD_RISK_THRESHOLDS["rain_72h_critical_mm"]:
        risk_level = "critical"
    elif rain_72h >= FLOOD_RISK_THRESHOLDS["rain_72h_warning_mm"]:
        risk_level = "warning"
    elif rain_7d >= FLOOD_RISK_THRESHOLDS["rain_7d_warning_mm"]:
        risk_level = "watch"
    else:
        risk_level = "normal"

    return {
        "corridor": corridor,
        "lon": lon, "lat": lat,
        "period": {"start": str(start_dt), "end": str(end_dt), "days": days_back},
        "rainfall_mm": {
            "72h": round(rain_72h, 2),
            "7d":  round(rain_7d, 2),
            "30d": round(rain_30d, 2),
        },
        "risk_level": risk_level,
        "daily_series": {
            "dates":    dates,
            "rainfall": vals,
            "temp_c":   [temp.get(d, None) for d in dates],
            "humidity": [humid.get(d, None) for d in dates],
            "wind_ms":  [wind.get(d, None) for d in dates],
        },
        "thresholds": FLOOD_RISK_THRESHOLDS,
        "source": "NASA POWER v2.3",
        "fetched_at": datetime.utcnow().isoformat(),
    }


def fetch_all_corridors_rainfall(days_back: int = 30) -> dict[str, dict]:
    """Fetch rainfall for every corridor in one call."""
    return {
        corridor: fetch_corridor_rainfall(corridor, days_back)
        for corridor in CORRIDOR_POINTS
    }


# ── CMR STAC — HLS Scenes ─────────────────────────────────────────────────────

def fetch_hls_scenes(
    corridor: str,
    days_back: int = 14,
    max_items: int = 10,
    cloud_max: float = 60.0,
    sensor: str = "both",  # "landsat", "sentinel", "both"
) -> list[dict]:
    """
    Query NASA CMR for HLS (Harmonized Landsat Sentinel-2) scenes.
    Returns parsed scene list with thumbnail URLs.
    Sensor: landsat=HLSL30, sentinel=HLSS30, both=combined.
    """
    bbox = CORRIDOR_BBOXES.get(corridor, [60, 24, 77, 37])
    end_dt   = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days_back)

    collections = []
    if sensor in ("landsat", "both"):
        collections.append("HLSL30.v2.0")
    if sensor in ("sentinel", "both"):
        collections.append("HLSS30.v2.0")

    all_scenes = []
    for coll in collections:
        url = (
            f"{CMR_STAC}/search"
            f"?collections={coll}"
            f"&bbox={','.join(str(x) for x in bbox)}"
            f"&datetime={start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"&limit={max_items}"
        )
        try:
            r = requests.get(url, headers=_auth_headers(), timeout=20)
            r.raise_for_status()
            features = r.json().get("features", [])
            for item in features:
                props   = item.get("properties", {})
                cloud   = props.get("eo:cloud_cover", None)
                if cloud is not None and cloud > cloud_max:
                    continue
                assets  = item.get("assets", {})
                thumb   = (assets.get("thumbnail", {}) or assets.get("browse", {})).get("href", "")
                # HLS sensor type from collection
                s_type  = "Landsat-8/9" if "L30" in coll else "Sentinel-2"
                all_scenes.append({
                    "scene_id":   item.get("id", ""),
                    "collection": coll,
                    "sensor":     s_type,
                    "corridor":   corridor,
                    "date":       props.get("datetime", "")[:10],
                    "cloud_pct":  cloud,
                    "bbox":       item.get("bbox", bbox),
                    "thumbnail":  thumb,
                    "assets":     {k: v.get("href", "") for k, v in assets.items()},
                    "stac_url":   item.get("links", [{}])[0].get("href", "") if item.get("links") else "",
                })
        except Exception as exc:
            all_scenes.append({"scene_id": f"ERROR-{coll}", "error": str(exc)})

    return sorted(all_scenes, key=lambda x: x.get("date", ""), reverse=True)


# ── CMR — IMERG Rainfall ──────────────────────────────────────────────────────

def fetch_imerg_info() -> list[dict]:
    """
    Return available IMERG product info from CMR.
    (Actual IMERG data download requires OPeNDAP/wget — this returns metadata.)
    """
    url = f"{CMR_SEARCH}/collections.json?keyword=IMERG&page_size=6&sort_key=start_date"
    try:
        r = requests.get(url, headers=_auth_headers(), timeout=15)
        r.raise_for_status()
        entries = r.json().get("feed", {}).get("entry", [])
        return [
            {
                "short_name": e.get("short_name", ""),
                "title":      e.get("dataset_id", "")[:100],
                "version":    e.get("version_id", ""),
                "temporal":   e.get("time_start", "")[:10],
            }
            for e in entries
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


# ── Flood Risk Score (hydromet fusion) ────────────────────────────────────────

def compute_flood_risk_score(rainfall_data: dict) -> dict:
    """
    Fuse rainfall metrics into a single flood risk score for each corridor.
    Mirrors the logic in pipeline/runner.py TriggerInputs.
    """
    results = {}
    for corridor, data in rainfall_data.items():
        if "error" in data:
            results[corridor] = {"risk_score": 0.0, "risk_level": "unknown", "error": data["error"]}
            continue

        r72h = data["rainfall_mm"]["72h"]
        r7d  = data["rainfall_mm"]["7d"]
        r30d = data["rainfall_mm"]["30d"]

        # Weighted score 0..1
        score = min(1.0, (
            0.50 * min(r72h / FLOOD_RISK_THRESHOLDS["rain_72h_critical_mm"], 1.0) +
            0.30 * min(r7d  / FLOOD_RISK_THRESHOLDS["rain_7d_critical_mm"],  1.0) +
            0.20 * min(r30d / 300.0, 1.0)
        ))

        level = data.get("risk_level", "normal")
        results[corridor] = {
            "corridor":   corridor,
            "risk_score": round(score, 3),
            "risk_level": level,
            "rain_72h":   r72h,
            "rain_7d":    r7d,
            "rain_30d":   r30d,
        }
    return results
