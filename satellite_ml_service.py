"""
Satellite Image Downloader & ML Water Detection Pipeline
=========================================================
Downloads real satellite thumbnails/previews from Earth Search and NASA CMR,
saves them locally for training, and runs ML clustering for water region detection.

Storage layout (all images kept permanently for training):
  storage/satellite/sentinel2_thumbnails/  — Sentinel-2 preview JPGs
  storage/satellite/hls_thumbnails/        — HLS browse images
  storage/satellite/historical_floods/     — Historical flood event images
  storage/ml/water_masks/                  — Generated water masks
  storage/ml/clusters/                     — Cluster analysis outputs
  storage/ml/models/                       — Trained model artifacts
  storage/flood_memory/                    — Flood/river path memory records
"""
from __future__ import annotations

import io
import json
import hashlib
import os
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from PIL import Image

# ── Storage paths ─────────────────────────────────────────────────────────────
STORAGE      = Path("storage")
SAT_DIR      = STORAGE / "satellite"
S2_THUMBS    = SAT_DIR / "sentinel2_thumbnails"
HLS_THUMBS   = SAT_DIR / "hls_thumbnails"
HIST_FLOODS  = SAT_DIR / "historical_floods"
ML_DIR       = STORAGE / "ml"
WATER_MASKS  = ML_DIR  / "water_masks"
CLUSTER_DIR  = ML_DIR  / "clusters"
MODEL_DIR    = ML_DIR  / "models"
MEMORY_DIR   = STORAGE / "flood_memory"

for d in [S2_THUMBS, HLS_THUMBS, HIST_FLOODS, WATER_MASKS, CLUSTER_DIR, MODEL_DIR, MEMORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Catalog of major Pakistan flood events (past 10 years) ───────────────────
HISTORICAL_FLOODS = [
    {"year": 2022, "name": "Pakistan Mega Flood 2022", "months": [7, 8, 9],
     "corridors": ["Indus-Lower", "Indus-Upper", "Chenab-Middle", "Jhelum-Lower", "Sutlej-Lower"],
     "peak_date": "2022-08-27", "severity": "catastrophic",
     "affected_area_sqkm": 75000, "deaths": 1739, "displaced": 33000000,
     "notes": "Worst flood in Pakistan history. 1/3 of country submerged."},
    {"year": 2020, "name": "Sindh Flood 2020", "months": [8, 9],
     "corridors": ["Indus-Lower"],
     "peak_date": "2020-08-25", "severity": "major",
     "affected_area_sqkm": 8500, "deaths": 410, "displaced": 660000,
     "notes": "Heavy monsoon flooding in Sindh and southern Punjab."},
    {"year": 2019, "name": "AJK Flash Flood 2019", "months": [7],
     "corridors": ["Jhelum-Lower"],
     "peak_date": "2019-07-15", "severity": "moderate",
     "affected_area_sqkm": 3200, "deaths": 85, "displaced": 120000,
     "notes": "Flash floods in Azad Jammu & Kashmir due to cloudbursts."},
    {"year": 2018, "name": "Balochistan Flood 2018", "months": [7, 8],
     "corridors": ["Indus-Lower"],
     "peak_date": "2018-07-20", "severity": "moderate",
     "affected_area_sqkm": 4100, "deaths": 164, "displaced": 300000,
     "notes": "Monsoon flooding in Balochistan and Sindh."},
    {"year": 2017, "name": "Punjab Flood 2017", "months": [8],
     "corridors": ["Chenab-Middle", "Sutlej-Lower"],
     "peak_date": "2017-08-05", "severity": "moderate",
     "affected_area_sqkm": 5200, "deaths": 160, "displaced": 450000,
     "notes": "River flooding in Punjab along Chenab and Sutlej."},
    {"year": 2016, "name": "KP Flood 2016", "months": [4],
     "corridors": ["Kabul-Nowshera"],
     "peak_date": "2016-04-03", "severity": "moderate",
     "affected_area_sqkm": 2800, "deaths": 138, "displaced": 280000,
     "notes": "Spring floods in Khyber Pakhtunkhwa."},
    {"year": 2015, "name": "Chitral Flood 2015", "months": [7],
     "corridors": ["Kabul-Nowshera", "Indus-Upper"],
     "peak_date": "2015-07-15", "severity": "major",
     "affected_area_sqkm": 6100, "deaths": 238, "displaced": 1500000,
     "notes": "Severe flooding in Chitral, Peshawar, Nowshera."},
    {"year": 2014, "name": "India-Pakistan Flood 2014", "months": [9],
     "corridors": ["Chenab-Middle", "Jhelum-Lower"],
     "peak_date": "2014-09-06", "severity": "catastrophic",
     "affected_area_sqkm": 13000, "deaths": 367, "displaced": 2500000,
     "notes": "Devastating Jhelum/Chenab flooding. Srinagar-Lahore corridor."},
]

# Corridor bounding boxes
CORRIDOR_BBOXES = {
    "Indus-Lower":    [66.8, 25.2, 69.5, 27.8],
    "Indus-Upper":    [70.5, 33.0, 74.0, 34.5],
    "Chenab-Middle":  [71.5, 30.5, 73.5, 32.2],
    "Jhelum-Lower":   [72.8, 32.0, 74.2, 33.2],
    "Sutlej-Lower":   [70.2, 28.5, 72.5, 30.5],
    "Kabul-Nowshera": [71.5, 33.8, 72.8, 34.6],
}

# Known major river paths (lat/lon waypoints)
RIVER_PATHS = {
    "Indus": [
        (35.50, 74.50), (34.80, 73.50), (34.00, 72.40), (33.50, 71.80),
        (32.50, 71.20), (31.50, 70.70), (30.00, 70.00), (28.50, 69.00),
        (27.50, 68.50), (26.50, 67.80), (25.40, 68.30), (24.80, 67.70),
    ],
    "Jhelum": [
        (34.30, 73.80), (33.90, 73.60), (33.40, 73.50), (32.90, 73.40),
        (32.50, 73.10), (32.10, 72.40), (31.70, 72.00),
    ],
    "Chenab": [
        (33.20, 74.80), (32.80, 74.20), (32.30, 73.50), (31.70, 72.90),
        (31.30, 72.40), (30.80, 71.80), (30.30, 71.50),
    ],
    "Ravi": [
        (32.50, 74.90), (32.10, 74.50), (31.50, 74.30), (31.10, 73.70),
        (30.60, 73.10), (30.20, 72.50),
    ],
    "Sutlej": [
        (31.30, 75.30), (30.80, 74.50), (30.30, 73.50), (29.80, 72.50),
        (29.30, 71.50), (28.90, 71.00),
    ],
    "Kabul": [
        (34.50, 71.50), (34.30, 71.80), (34.10, 72.00), (34.00, 72.30),
    ],
}


# ── Image Download Functions ──────────────────────────────────────────────────

def download_image(url: str, save_path: Path, timeout: int = 30) -> bool:
    """Download an image from URL and save locally. Returns True on success."""
    if save_path.exists():
        return True  # Already cached
    try:
        r = requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "image" not in ct and "octet" not in ct:
            return False
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(r.content)
        return True
    except Exception:
        return False


def download_sentinel2_thumbnails(
    corridor: str, days_back: int = 14, max_items: int = 5, cloud_max: float = 40.0
) -> list[dict]:
    """Download Sentinel-2 thumbnails from Earth Search and save locally."""
    try:
        import pystac_client
        client = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
    except Exception:
        return []

    bbox = CORRIDOR_BBOXES.get(corridor, [60, 24, 77, 37])
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days_back)

    try:
        results = client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}",
            query={"eo:cloud_cover": {"lt": cloud_max}},
            max_items=max_items,
        )
        items = list(results.items())
    except Exception:
        return []

    downloaded = []
    for item in items:
        thumb_url = item.assets.get("thumbnail", None)
        if thumb_url is None:
            continue
        href = thumb_url.href
        if not href.startswith("https://"):
            continue
        filename = f"{item.id}.jpg"
        save_path = S2_THUMBS / corridor / filename
        if download_image(href, save_path):
            downloaded.append({
                "scene_id": item.id,
                "corridor": corridor,
                "date": item.datetime.date().isoformat() if item.datetime else "",
                "cloud_cover": item.properties.get("eo:cloud_cover", None),
                "local_path": str(save_path),
                "source_url": href,
                "bbox": list(item.bbox) if item.bbox else bbox,
            })
    return downloaded


def download_historical_flood_images(
    corridor: str, year: int, month: int, max_items: int = 5
) -> list[dict]:
    """Download Sentinel-2 images from historical flood dates."""
    try:
        import pystac_client
        client = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
    except Exception:
        return []

    bbox = CORRIDOR_BBOXES.get(corridor, [60, 24, 77, 37])
    start_dt = date(year, month, 1)
    end_dt = date(year, month, 28)

    try:
        results = client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_dt.isoformat()}/{end_dt.isoformat()}",
            query={"eo:cloud_cover": {"lt": 60}},
            max_items=max_items,
        )
        items = list(results.items())
    except Exception:
        return []

    downloaded = []
    for item in items:
        thumb_url = item.assets.get("thumbnail", None)
        if thumb_url is None:
            continue
        href = thumb_url.href
        if not href.startswith("https://"):
            continue
        save_dir = HIST_FLOODS / corridor / f"{year}_{month:02d}"
        filename = f"{item.id}.jpg"
        save_path = save_dir / filename
        if download_image(href, save_path):
            downloaded.append({
                "scene_id": item.id,
                "corridor": corridor,
                "year": year,
                "month": month,
                "date": item.datetime.date().isoformat() if item.datetime else "",
                "cloud_cover": item.properties.get("eo:cloud_cover", None),
                "local_path": str(save_path),
                "source_url": href,
                "event_type": "historical_flood",
            })
    return downloaded


# ── ML Water Detection ────────────────────────────────────────────────────────


def detect_water_spectral(image_path: str) -> dict:
    """
    Production-grade water detection using spectral water indices.
    Computes NDWI-proxy, MNDWI-proxy, and AWEI-proxy from available RGB
    channels, combines them into an ensemble water probability, and produces
    a confidence-graded water mask.

    Limitations:
    - Without true NIR/SWIR bands this is a proxy using RGB heuristics.
    - Should be replaced with full Sentinel-2 L2A band access when available.
    """
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    eps = 1e-6

    brightness = arr.mean(axis=2)

    # Proxy water indices from RGB (approximating NIR≈R, SWIR≈brightness)
    ndwi_proxy = (G - R) / (G + R + eps)          # green-NIR proxy
    mndwi_proxy = (G - brightness) / (G + brightness + eps)  # green-SWIR proxy
    # AWEI shadow-resistant: 4*(Green-SWIR) - (0.25*NIR + 2.75*SWIR)
    awei_proxy = 4 * (G - brightness) - (0.25 * R + 2.75 * brightness)

    # Normalize AWEI to [-1, 1] range
    awei_min, awei_max = awei_proxy.min(), awei_proxy.max()
    if awei_max - awei_min > eps:
        awei_norm = 2 * (awei_proxy - awei_min) / (awei_max - awei_min) - 1
    else:
        awei_norm = np.zeros_like(awei_proxy)

    # Ensemble water probability (0-1)
    water_prob = np.clip(
        0.4 * np.clip(ndwi_proxy, 0, 1)
        + 0.35 * np.clip(mndwi_proxy, 0, 1)
        + 0.25 * np.clip(awei_norm, 0, 1),
        0, 1,
    )

    # Confidence grading
    # High: all 3 indices agree; Medium: 2 agree; Low: only 1
    agree_count = (
        (ndwi_proxy > 0.05).astype(int)
        + (mndwi_proxy > 0.05).astype(int)
        + (awei_norm > 0.05).astype(int)
    )
    confidence = np.where(agree_count >= 3, "high",
                 np.where(agree_count >= 2, "medium", "low"))

    # Binary water mask at probability > 0.3
    water_mask = water_prob > 0.3
    water_pct = 100.0 * water_mask.sum() / (h * w)

    # Save outputs
    scene_name = Path(image_path).stem
    prob_vis = (water_prob * 255).astype(np.uint8)
    mask_vis = np.zeros((h, w, 3), dtype=np.uint8)
    mask_vis[water_mask] = [0, 100, 255]
    mask_vis[~water_mask] = [180, 180, 180]

    prob_path = WATER_MASKS / f"{scene_name}_water_prob.png"
    mask_path = WATER_MASKS / f"{scene_name}_spectral_mask.png"
    Image.fromarray(prob_vis).save(prob_path)
    Image.fromarray(mask_vis).save(mask_path)

    high_conf_pct = 100.0 * ((water_mask) & (agree_count >= 3)).sum() / (h * w)

    return {
        "image_path": image_path,
        "method": "spectral_indices",
        "water_pct": round(water_pct, 2),
        "high_confidence_water_pct": round(high_conf_pct, 2),
        "indices": {
            "ndwi_proxy_mean": round(float(ndwi_proxy[water_mask].mean()) if water_mask.any() else 0, 4),
            "mndwi_proxy_mean": round(float(mndwi_proxy[water_mask].mean()) if water_mask.any() else 0, 4),
            "awei_proxy_mean": round(float(awei_norm[water_mask].mean()) if water_mask.any() else 0, 4),
        },
        "water_probability_path": str(prob_path),
        "water_mask_path": str(mask_path),
        "image_size": {"width": w, "height": h},
        "limitations": [
            "Uses RGB proxy indices, not true NIR/SWIR bands.",
            "Cloud/shadow/haze can produce false positives.",
            "Sediment-laden water may be missed.",
        ],
    }


def detect_water_regions(image_path: str, n_clusters: int = 4) -> dict:
    """
    [PROTOTYPE/DEMO] K-Means clustering on a satellite RGB thumbnail.

    Limitations:
    - Uses RGB thumbnails, not radiometrically calibrated bands.
    - Fragile under clouds, haze, shadows, sediment, and vegetation.
    - Not validated against ground truth flood extents.
    - For operational use, prefer detect_water_spectral() or full
      Sentinel-2 band-based NDWI/MNDWI/AWEI processing.
    """
    from sklearn.cluster import KMeans, MiniBatchKMeans

    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    h, w, c = arr.shape
    pixels = arr.reshape(-1, 3).astype(np.float32)

    # Normalise
    pixels_norm = pixels / 255.0

    # Add derived features: brightness, blue-ratio, green-ratio
    brightness = pixels_norm.mean(axis=1, keepdims=True)
    blue_ratio = (pixels_norm[:, 2:3]) / (brightness + 1e-6)
    green_ratio = (pixels_norm[:, 1:2]) / (brightness + 1e-6)
    ndwi_proxy = (pixels_norm[:, 1:2] - pixels_norm[:, 2:3]) / (pixels_norm[:, 1:2] + pixels_norm[:, 2:3] + 1e-6)

    features = np.hstack([pixels_norm, brightness, blue_ratio, green_ratio, ndwi_proxy])

    model = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=1024, n_init=3)
    labels = model.fit_predict(features)

    # Identify water cluster — lowest brightness + highest blue ratio
    cluster_stats = []
    for ci in range(n_clusters):
        mask = labels == ci
        count = mask.sum()
        if count == 0:
            cluster_stats.append({"id": ci, "brightness": 1.0, "blue_ratio": 0.0, "count": 0})
            continue
        cluster_stats.append({
            "id": ci,
            "brightness": float(brightness[mask].mean()),
            "blue_ratio": float(blue_ratio[mask].mean()),
            "green_ratio": float(green_ratio[mask].mean()),
            "ndwi_proxy": float(ndwi_proxy[mask].mean()),
            "count": int(count),
            "pct": round(100.0 * count / len(labels), 2),
            "mean_rgb": [int(x) for x in pixels[mask].mean(axis=0)],
        })

    # Water cluster: highest (blue_ratio - brightness) score
    water_scores = [
        (cs["id"], cs["blue_ratio"] * 1.5 - cs["brightness"] + cs.get("ndwi_proxy", 0) * 0.5)
        for cs in cluster_stats if cs["count"] > 0
    ]
    water_cluster_id = max(water_scores, key=lambda x: x[1])[0]

    water_mask = (labels == water_cluster_id).reshape(h, w)
    water_pct = 100.0 * water_mask.sum() / (h * w)

    # Save cluster map and water mask
    label_img = labels.reshape(h, w)
    cluster_colors = np.array([[0,0,255], [0,255,0], [255,255,0], [255,0,0],
                                [0,255,255], [255,0,255], [128,128,128], [255,128,0]])[:n_clusters]
    cluster_vis = cluster_colors[label_img].astype(np.uint8)

    mask_vis = np.zeros((h, w, 3), dtype=np.uint8)
    mask_vis[water_mask] = [0, 100, 255]  # Blue for water
    mask_vis[~water_mask] = [180, 180, 180]

    scene_name = Path(image_path).stem
    cluster_path = CLUSTER_DIR / f"{scene_name}_clusters.png"
    mask_path    = WATER_MASKS / f"{scene_name}_water_mask.png"

    Image.fromarray(cluster_vis).save(cluster_path)
    Image.fromarray(mask_vis).save(mask_path)

    return {
        "image_path": image_path,
        "n_clusters": n_clusters,
        "water_cluster_id": water_cluster_id,
        "water_pct": round(water_pct, 2),
        "cluster_stats": cluster_stats,
        "cluster_map_path": str(cluster_path),
        "water_mask_path": str(mask_path),
        "image_size": {"width": w, "height": h},
    }


# ── Flood Memory ──────────────────────────────────────────────────────────────

def save_flood_memory(corridor: str, data: dict):
    """Save flood/water detection results to the memory store."""
    path = MEMORY_DIR / f"{corridor}_memory.json"
    existing = []
    if path.exists():
        existing = json.loads(path.read_text())
    data["saved_at"] = datetime.utcnow().isoformat()
    existing.append(data)
    path.write_text(json.dumps(existing, indent=2, default=str))


def load_flood_memory(corridor: str = None) -> list[dict]:
    """Load flood memory records."""
    records = []
    pattern = f"{corridor}_memory.json" if corridor else "*_memory.json"
    for f in MEMORY_DIR.glob(pattern):
        records.extend(json.loads(f.read_text()))
    return sorted(records, key=lambda x: x.get("saved_at", ""), reverse=True)


def get_local_image_inventory() -> dict:
    """Count all locally saved satellite images."""
    inv = {}
    for subdir in [S2_THUMBS, HLS_THUMBS, HIST_FLOODS]:
        count = sum(1 for _ in subdir.rglob("*.jpg")) + sum(1 for _ in subdir.rglob("*.png"))
        inv[subdir.name] = count
    inv["water_masks"] = sum(1 for _ in WATER_MASKS.rglob("*.png"))
    inv["cluster_maps"] = sum(1 for _ in CLUSTER_DIR.rglob("*.png"))
    inv["total"] = sum(inv.values())
    return inv


def get_historical_flood_catalog() -> list[dict]:
    """Return the historical flood event catalog."""
    return HISTORICAL_FLOODS


def get_river_paths() -> dict:
    """Return known river path waypoints."""
    return RIVER_PATHS
