"""
🛰️ Satellite Scene Viewer — Pakistan Flood Monitor
Real-time queries to the free Earth Search STAC API.
No API key required.
"""
import sys
import os
from datetime import datetime, timedelta, date

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Allow import from src/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pakistan_flood_monitor.data.sources import (
    DataCatalog,
    CORRIDOR_BBOXES,
    STAC_ENDPOINT,
)

st.set_page_config(page_title="Satellite Scene Viewer", page_icon="🛰️", layout="wide")

catalog = DataCatalog()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛰️ Satellite Scene Viewer")
st.markdown(
    "Queries **real satellite imagery** from the free "
    "[Earth Search STAC API](https://earth-search.aws.element84.com/v1) "
    "(Element 84). **No API key required.**"
)

# ── Data Source Reference ──────────────────────────────────────────────────────
with st.expander("📡 Available Data Sources & Access Info", expanded=False):
    info = catalog.collection_info()
    df_info = pd.DataFrame(info)
    st.dataframe(
        df_info[["sensor", "provider", "auth", "resolution", "revisit", "description"]],
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "All satellite data is free and open. Earth Search (Sentinel/Landsat) "
        "requires no registration. GloFAS requires a free CDS account. "
        "NASA IMERG requires a free Earthdata account."
    )

st.markdown("---")

# ── Query Controls ─────────────────────────────────────────────────────────────
st.subheader("🔎 Scene Search")

col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    sensor_label = st.selectbox(
        "Sensor",
        ["Sentinel-1 (SAR — Flood Detection)", "Sentinel-2 (Optical — NDWI / Analyst)", "Landsat (Optical — Long Archive)"],
        key="sensor_sel",
    )
    sensor_map = {
        "Sentinel-1 (SAR — Flood Detection)": "sentinel-1",
        "Sentinel-2 (Optical — NDWI / Analyst)": "sentinel-2",
        "Landsat (Optical — Long Archive)": "landsat",
    }
    sensor = sensor_map[sensor_label]

with col2:
    corridor_opts = ["All Corridors"] + list(CORRIDOR_BBOXES.keys())
    corridor = st.selectbox("Corridor / AOI", corridor_opts, key="corr_sel")

with col3:
    days_back = st.number_input("Days to search back", min_value=1, max_value=60, value=14, step=1, key="days_sel")

with col4:
    cloud_max = st.number_input(
        "Max cloud cover %",
        min_value=0, max_value=100, value=60, step=5, key="cloud_sel",
        help="Only applies to Sentinel-2 and Landsat. SAR ignores cloud.",
    )

max_items = st.slider("Max scenes per corridor", 1, 20, 5, key="max_items")

run_search = st.button("🚀 Search for Real Scenes", type="primary")

# ── Cache state ───────────────────────────────────────────────────────────────
if "stac_results" not in st.session_state:
    st.session_state["stac_results"] = None

if run_search:
    end_dt   = datetime.utcnow().date()
    start_dt = end_dt - timedelta(days=int(days_back))

    corridors_to_search = (
        list(CORRIDOR_BBOXES.keys()) if corridor == "All Corridors" else [corridor]
    )

    all_scenes: dict = {}
    progress = st.progress(0, text="Querying Earth Search STAC API…")
    for i, corr in enumerate(corridors_to_search):
        progress.progress(
            (i + 1) / len(corridors_to_search),
            text=f"Fetching {sensor} scenes for {corr}…",
        )
        scenes = catalog.fetch_scenes(
            sensor=sensor,
            aoi_name=corr,
            start=start_dt,
            end=end_dt,
            max_items=max_items,
            cloud_cover_max=float(cloud_max),
        )
        all_scenes[corr] = scenes

    progress.empty()
    st.session_state["stac_results"] = {
        "scenes":    all_scenes,
        "sensor":    sensor,
        "start":     start_dt,
        "end":       end_dt,
        "queried_at": datetime.utcnow().isoformat(),
    }
    st.success(
        f"Query complete: {sum(len(v) for v in all_scenes.values())} scenes "
        f"found across {len(corridors_to_search)} corridor(s)"
    )

# ── Results ───────────────────────────────────────────────────────────────────
results = st.session_state.get("stac_results")

if results:
    all_scenes = results["scenes"]
    sensor_r   = results["sensor"]
    total      = sum(len(v) for v in all_scenes.values())

    # Summary metrics
    st.subheader("📊 Search Results Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Scenes", total)
    m2.metric("Corridors Searched", len(all_scenes))
    m3.metric("Sensor", sensor_r.title())
    m4.metric("Date Range", f"{results['start']} → {results['end']}")

    # ── Map showing scene footprints ─────────────────────────────────────────
    st.subheader("🗺️ Scene Footprint Map")
    m = folium.Map(location=[30.0, 70.0], zoom_start=5, tiles="CartoDB dark_matter")

    corridor_colors = {
        "Indus-Lower":    "#FF6B6B",
        "Indus-Upper":    "#FF8E53",
        "Chenab-Middle":  "#FFC93C",
        "Jhelum-Lower":   "#4FC3F7",
        "Sutlej-Lower":   "#81C784",
        "Kabul-Nowshera": "#CE93D8",
    }

    for corr, scenes in all_scenes.items():
        bbox = CORRIDOR_BBOXES.get(corr, [60, 24, 77, 37])
        color = corridor_colors.get(corr, "#FFFFFF")

        # Draw corridor bounding box
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color=color,
            weight=2,
            fill=True,
            fill_opacity=0.08,
            tooltip=f"{corr}: {len(scenes)} scenes",
        ).add_to(m)

        # Draw each scene footprint
        for sc in scenes:
            sc_bbox = sc.bbox or bbox
            cloud_str = f"{sc.cloud_cover:.1f}%" if sc.cloud_cover is not None else "N/A (SAR)"
            popup_html = f"""
            <b>{sc.scene_id}</b><br>
            Sensor: {sc.sensor}<br>
            Date: {sc.acquisition_date}<br>
            Cloud: {cloud_str}<br>
            """
            if sc.thumbnail_url and sc.thumbnail_url.startswith("https://"):
                popup_html += f'<img src="{sc.thumbnail_url}" width="200"><br>'

            folium.Rectangle(
                bounds=[[sc_bbox[1], sc_bbox[0]], [sc_bbox[3], sc_bbox[2]]],
                color=color,
                weight=1,
                fill=True,
                fill_opacity=0.15,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{sc.scene_id} ({sc.acquisition_date})",
            ).add_to(m)

    # Flood events overlay
    try:
        from backend_service import data_service
        events = data_service.get_events_by_status(["published", "active", "critical"])
        for _, ev in events.iterrows():
            if pd.notna(ev.get("latitude")):
                folium.CircleMarker(
                    [ev["latitude"], ev["longitude"]],
                    radius=10, color="red", fill=True, fill_opacity=0.8,
                    tooltip=f"⚠️ {ev['event_id']} — {ev['district']}",
                ).add_to(m)
    except Exception:
        pass

    # Legend
    legend_html = """
    <div style='position:fixed;bottom:20px;right:20px;background:rgba(0,0,0,0.8);
                 color:white;padding:10px;border-radius:5px;font-size:12px;z-index:9999'>
    <b>Legend</b><br>
    🔲 Corridor AOI<br>
    🔲 Scene footprint<br>
    🔴 Active flood event<br>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=1200, height=520)

    # ── Per-corridor scene list ───────────────────────────────────────────────
    st.subheader("📋 Scene Details by Corridor")

    all_rows = []
    for corr, scenes in all_scenes.items():
        for sc in scenes:
            all_rows.append({
                "Corridor":   corr,
                "Scene ID":   sc.scene_id,
                "Sensor":     sc.sensor,
                "Date":       str(sc.acquisition_date),
                "Cloud%":     round(sc.cloud_cover, 1) if sc.cloud_cover is not None else "N/A",
                "Has Thumbnail": "✅" if sc.thumbnail_url and sc.thumbnail_url.startswith("https://") else "❌ S3",
                "Stub":       sc.properties.get("stub", False),
            })

    if all_rows:
        df_scenes = pd.DataFrame(all_rows)
        st.dataframe(df_scenes, width="stretch", hide_index=True)

    # ── Thumbnail gallery (Sentinel-2 only — has HTTPS thumbnails) ───────────
    st.subheader("🖼️ Scene Thumbnails")
    thumb_count = 0
    for corr, scenes in all_scenes.items():
        http_scenes = [s for s in scenes if s.thumbnail_url and s.thumbnail_url.startswith("https://")]
        if not http_scenes:
            continue
        st.markdown(f"**{corr}**")
        cols = st.columns(min(len(http_scenes), 4))
        for i, sc in enumerate(http_scenes[:4]):
            with cols[i]:
                st.image(
                    sc.thumbnail_url,
                    caption=f"{sc.scene_id}\n{sc.acquisition_date}  ☁️{sc.cloud_cover:.1f}%",
                    use_container_width=True,
                )
                thumb_count += 1

    if thumb_count == 0:
        st.info(
            "Sentinel-1 thumbnails are on S3 (not publicly browsable as HTTPS). "
            "Try **Sentinel-2** to see visual previews of the area."
        )

    # ── Scene properties deep-dive ────────────────────────────────────────────
    st.subheader("🔬 Scene Properties Deep Dive")
    all_scene_ids = [
        f"{corr} / {sc.scene_id}"
        for corr, scenes in all_scenes.items()
        for sc in scenes
    ]
    if all_scene_ids:
        selected_id = st.selectbox("Select scene to inspect", all_scene_ids, key="inspect_scene")
        sel_corr, sel_sid = selected_id.split(" / ", 1)
        sel_scene = next(
            (s for s in all_scenes.get(sel_corr, []) if s.scene_id == sel_sid), None
        )
        if sel_scene:
            lc, rc = st.columns(2)
            with lc:
                st.markdown(f"**Scene ID:** `{sel_scene.scene_id}`")
                st.markdown(f"**Sensor:** {sel_scene.sensor}")
                st.markdown(f"**Date:** {sel_scene.acquisition_date}")
                st.markdown(f"**Cloud Cover:** {sel_scene.cloud_cover}%")
                st.markdown(f"**Bounding Box:** `{sel_scene.bbox}`")
                if sel_scene.stac_item_url:
                    st.markdown(f"**STAC Item:** [{sel_scene.stac_item_url}]({sel_scene.stac_item_url})")
                st.markdown("**Available Assets:**")
                if sel_scene.assets:
                    for k, v in sel_scene.assets.items():
                        st.write(f"  `{k}`: {v[:80]}…" if len(v) > 80 else f"  `{k}`: {v}")
            with rc:
                if sel_scene.thumbnail_url and sel_scene.thumbnail_url.startswith("https://"):
                    st.image(sel_scene.thumbnail_url, caption="Scene thumbnail", use_container_width=True)
                st.markdown("**STAC Properties:**")
                st.json(sel_scene.properties)

else:
    # Show info panel before any search
    st.info(
        "👆 Configure your search and click **Search for Real Scenes** to query live satellite data."
    )

    st.subheader("🌐 About the Data Sources")
    st.markdown("""
    | Source | Type | Auth | Use in Flood Detection |
    |--------|------|------|----------------------|
    | **Sentinel-1 GRD** | SAR (radar) | ❌ None | Primary flood detection — backscatter anomaly |
    | **Sentinel-2 L2A** | Optical | ❌ None | NDWI water index, analyst visual check |
    | **Landsat C2 L2** | Optical | ❌ None | Long-archive NDWI backup |
    | **Copernicus DEM** | Elevation | ❌ None | Floodplain distance feature |
    | **GPM IMERG** | Rainfall | 🔑 Free Earthdata | Hydromet trigger (72h rainfall) |
    | **GloFAS** | River discharge | 🔑 Free CDS | Return period, seasonal anomaly |
    | **JRC-GSW** | Surface water baseline | ❌ None | Permanent water mask |

    ### How Sentinel-1 SAR detects floods
    - Floods appear as **dark areas** in SAR backscatter — smooth water reflects radar away from sensor
    - Compare a **recent scene** against a **baseline scene** from non-flood period
    - A drop > **2.5 dB** in the VV/VH polarisation bands triggers a flood candidate
    - The pipeline calls `detection.rule_based_probability()` using this SAR drop feature

    ### How Sentinel-2 Optical supports analysts
    - **NDWI** = (Green − NIR) / (Green + NIR)  → values > 0.2 indicate open water
    - Analysts use the **True Color Image (TCI)** to visually confirm flood extent
    - Cloud-free scenes required — SAR is used when clouds are present
    """)

# ── Supporting layers info ────────────────────────────────────────────────────
st.subheader("🌧️ Supporting Science Layers (Hydromet)")
corr_select = st.selectbox("Select corridor for layer info", list(CORRIDOR_BBOXES.keys()), key="supp_corr")
layers = catalog.fetch_supporting_layers(corr_select)
for name, url in layers.items():
    if name != "bbox":
        st.markdown(f"- **{name.upper()}**: [{url}]({url})")
    else:
        st.markdown(f"- **AOI bbox**: `{url}`")

# ── STAC endpoint status ──────────────────────────────────────────────────────
with st.expander("🔌 STAC API Connection Status"):
    try:
        import pystac_client
        client = pystac_client.Client.open(STAC_ENDPOINT)
        colls = [c.id for c in client.get_collections()]
        st.success(f"✅ Connected to **{client.title}**")
        st.write(f"Available collections: {', '.join(colls)}")
        st.write(f"Endpoint: `{STAC_ENDPOINT}`")
        st.write("**Authentication required:** None — fully public")
    except Exception as e:
        st.error(f"❌ Cannot connect to STAC endpoint: {e}")
        st.write(f"Endpoint: `{STAC_ENDPOINT}`")
