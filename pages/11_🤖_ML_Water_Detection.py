"""
🤖 ML Water Detection & Flood Analysis
Real satellite images + K-Means clustering for water region identification.
Downloads images locally, runs ML, saves results to flood memory.
"""
import sys, os, json
from datetime import datetime, timedelta, date
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from satellite_ml_service import (
    download_sentinel2_thumbnails,
    download_historical_flood_images,
    detect_water_regions,
    save_flood_memory,
    load_flood_memory,
    get_local_image_inventory,
    get_historical_flood_catalog,
    get_river_paths,
    CORRIDOR_BBOXES,
    S2_THUMBS, HLS_THUMBS, HIST_FLOODS, WATER_MASKS, CLUSTER_DIR,
)

st.set_page_config(page_title="ML Water Detection", page_icon="🤖", layout="wide")
st.title("🤖 ML Water Detection & Flood Analysis")
st.markdown("Download real satellite images, run K-Means clustering to detect water regions, and build flood memory.")

tabs = st.tabs([
    "📥 Download Images",
    "🧪 Water Detection ML",
    "📚 Historical Floods",
    "🗺️ River Paths & Memory",
    "📊 Image Inventory",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1 — IMAGE DOWNLOAD
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📥 Download Satellite Images (Saved Locally for Training)")
    st.caption("Images are saved permanently in `storage/satellite/` and never deleted.")

    dl_type = st.radio("Download type", ["Recent Sentinel-2", "Historical Flood Images"], key="dl_type")

    c1, c2, c3 = st.columns(3)
    dl_corridor = c1.selectbox("Corridor", list(CORRIDOR_BBOXES.keys()), key="dl_corr")

    if dl_type == "Recent Sentinel-2":
        dl_days = c2.number_input("Days back", 7, 60, 14, key="dl_days")
        dl_cloud = c3.number_input("Max cloud %", 0, 100, 30, key="dl_cloud")
        dl_max = st.slider("Max images", 1, 20, 5, key="dl_max")

        if st.button("📥 Download Recent Thumbnails", type="primary", key="dl_recent"):
            with st.spinner(f"Downloading Sentinel-2 from Earth Search for {dl_corridor}..."):
                results = download_sentinel2_thumbnails(
                    dl_corridor, days_back=int(dl_days), max_items=int(dl_max), cloud_max=float(dl_cloud)
                )
            st.session_state["dl_results"] = results
            st.success(f"Downloaded {len(results)} images to `storage/satellite/sentinel2_thumbnails/{dl_corridor}/`")

    else:
        catalog = get_historical_flood_catalog()
        events = {f"{e['year']} — {e['name']}": e for e in catalog}
        sel_event = c2.selectbox("Flood Event", list(events.keys()), key="dl_event")
        event = events[sel_event]
        dl_month = c3.selectbox("Month", event["months"], key="dl_month")
        dl_max_h = st.slider("Max images", 1, 15, 5, key="dl_max_h")

        st.info(f"**{event['name']}**: {event['notes']}")

        if st.button("📥 Download Historical Images", type="primary", key="dl_hist"):
            with st.spinner(f"Downloading {event['year']}/{dl_month} images for {dl_corridor}..."):
                results = download_historical_flood_images(
                    dl_corridor, event["year"], int(dl_month), max_items=int(dl_max_h)
                )
            st.session_state["dl_results"] = results
            st.success(f"Downloaded {len(results)} historical images")

    dl_results = st.session_state.get("dl_results", [])
    if dl_results:
        st.subheader("🖼️ Downloaded Images")
        cols = st.columns(min(len(dl_results), 4))
        for i, r in enumerate(dl_results):
            with cols[i % 4]:
                try:
                    st.image(r["local_path"], caption=f"{r['scene_id'][:25]}\n{r.get('date','')}", use_container_width=True)
                except Exception:
                    st.write(f"[{r['scene_id'][:25]}]")
        st.dataframe(pd.DataFrame(dl_results), width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 2 — WATER DETECTION ML
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🧪 K-Means Water Region Clustering")
    st.markdown("""
    Runs unsupervised ML clustering on satellite images to identify water regions:
    1. Extracts RGB + brightness + blue-ratio + NDWI-proxy features per pixel
    2. K-Means clustering (4 clusters)
    3. Water cluster identified by highest blue-ratio / lowest brightness
    4. Water mask and cluster map saved to `storage/ml/`
    """)

    # Find all local images
    all_imgs = []
    for d in [S2_THUMBS, HIST_FLOODS]:
        for f in d.rglob("*.jpg"):
            all_imgs.append({"path": str(f), "name": f.stem, "dir": f.parent.name})
        for f in d.rglob("*.png"):
            all_imgs.append({"path": str(f), "name": f.stem, "dir": f.parent.name})

    if not all_imgs:
        st.info("No local images found. Go to **Download Images** tab first.")
    else:
        st.write(f"**{len(all_imgs)} local images available for analysis**")

        ml_c1, ml_c2 = st.columns(2)
        sel_img = ml_c1.selectbox("Select image", [i["name"] for i in all_imgs], key="ml_img")
        n_clusters = ml_c2.slider("Number of clusters", 2, 8, 4, key="ml_clusters")

        sel_data = next((i for i in all_imgs if i["name"] == sel_img), None)

        if sel_data:
            st.image(sel_data["path"], caption="Original satellite image", width=400)

        if st.button("🔬 Run Water Detection", type="primary", key="ml_run"):
            if sel_data:
                with st.spinner("Running K-Means clustering..."):
                    result = detect_water_regions(sel_data["path"], n_clusters=n_clusters)
                st.session_state["ml_result"] = result

                # Save to flood memory
                save_flood_memory(sel_data.get("dir", "unknown"), {
                    "scene_id": sel_data["name"],
                    "water_pct": result["water_pct"],
                    "local_path": sel_data["path"],
                    "mask_path": result["water_mask_path"],
                    "analysis_type": "kmeans_clustering",
                })

        ml_result = st.session_state.get("ml_result")
        if ml_result:
            st.success(f"Water coverage detected: **{ml_result['water_pct']:.1f}%**")

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown("**Original Image**")
                st.image(ml_result["image_path"], use_container_width=True)
            with rc2:
                st.markdown("**Cluster Map**")
                st.image(ml_result["cluster_map_path"], use_container_width=True)
            with rc3:
                st.markdown("**Water Mask**")
                st.image(ml_result["water_mask_path"], use_container_width=True)

            st.subheader("📊 Cluster Statistics")
            df_cs = pd.DataFrame(ml_result["cluster_stats"])
            df_cs["is_water"] = df_cs["id"] == ml_result["water_cluster_id"]
            st.dataframe(df_cs, width="stretch", hide_index=True)

            # Pie chart of cluster distribution
            st.subheader("📈 Cluster Distribution")
            chart_data = pd.DataFrame({
                "Cluster": [f"Cluster {c['id']}" + (" (Water)" if c['id'] == ml_result["water_cluster_id"] else "") for c in ml_result["cluster_stats"] if c.get("pct",0)>0],
                "Coverage %": [c["pct"] for c in ml_result["cluster_stats"] if c.get("pct",0)>0],
            })
            st.bar_chart(chart_data.set_index("Cluster"))

            with st.expander("ℹ️ How it works"):
                st.markdown("""
                **Features per pixel:** RGB (normalized) + Brightness + Blue-ratio + Green-ratio + NDWI-proxy

                **NDWI proxy** = (Green - Blue) / (Green + Blue) — approximates water index from thumbnails

                **Water cluster selection:** Highest weighted score of `blue_ratio * 1.5 - brightness + ndwi_proxy * 0.5`

                This is a simplified proxy. Production water detection would use:
                - Full Sentinel-2 bands (B03 Green, B08 NIR)
                - True NDWI = (Green - NIR) / (Green + NIR)
                - Temporal change detection against baseline
                """)

# ═══════════════════════════════════════════════════════════════════
# TAB 3 — HISTORICAL FLOODS
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📚 Pakistan Historical Flood Catalog (2014–2022)")

    catalog = get_historical_flood_catalog()
    for event in catalog:
        icon = {"catastrophic":"🔴","major":"🟠","moderate":"🟡"}.get(event["severity"],"⚪")
        with st.expander(f"{icon} **{event['year']} — {event['name']}** | {event['severity'].upper()} | {event['affected_area_sqkm']:,} sq km"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Peak Date:** {event['peak_date']}")
                st.write(f"**Corridors Affected:** {', '.join(event['corridors'])}")
                st.write(f"**Deaths:** {event['deaths']:,}")
                st.write(f"**Displaced:** {event['displaced']:,}")
            with c2:
                st.write(f"**Flood Months:** {event['months']}")
                st.write(f"**Notes:** {event['notes']}")

            # Check if we have downloaded images for this event
            for corr in event["corridors"]:
                for m in event["months"]:
                    hist_dir = HIST_FLOODS / corr / f"{event['year']}_{m:02d}"
                    if hist_dir.exists():
                        imgs = list(hist_dir.glob("*.jpg")) + list(hist_dir.glob("*.png"))
                        if imgs:
                            st.write(f"**📸 {len(imgs)} images downloaded for {corr} ({event['year']}/{m:02d})**")
                            cols = st.columns(min(len(imgs), 4))
                            for i, img in enumerate(imgs[:4]):
                                with cols[i]:
                                    st.image(str(img), caption=img.stem[:20], use_container_width=True)

    # Summary table
    st.subheader("📊 Flood History Summary")
    df_hist = pd.DataFrame(catalog)
    st.dataframe(df_hist[["year","name","severity","peak_date","affected_area_sqkm","deaths","displaced"]], width="stretch", hide_index=True)

    st.bar_chart(
        pd.DataFrame(catalog).set_index("year")[["affected_area_sqkm", "deaths"]],
    )

# ═══════════════════════════════════════════════════════════════════
# TAB 4 — RIVER PATHS & FLOOD MEMORY
# ═══════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("🗺️ Pakistan River Paths & Flood Memory")

    rivers = get_river_paths()

    # River map
    m = folium.Map(location=[30.5, 70.0], zoom_start=5, tiles="CartoDB dark_matter")
    river_colors = {"Indus":"#2196F3", "Jhelum":"#4FC3F7", "Chenab":"#81D4FA",
                    "Ravi":"#B3E5FC", "Sutlej":"#E1F5FE", "Kabul":"#00BCD4"}

    for river, path in rivers.items():
        color = river_colors.get(river, "#FFFFFF")
        folium.PolyLine(path, color=color, weight=3, opacity=0.8, tooltip=f"River: {river}").add_to(m)
        # Start marker
        folium.CircleMarker(path[0], radius=5, color=color, fill=True, tooltip=f"{river} (upstream)").add_to(m)

    # Corridor boxes
    for corr, bbox in CORRIDOR_BBOXES.items():
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color="#FF9800", weight=1, fill=True, fill_opacity=0.05,
            tooltip=f"Corridor: {corr}",
        ).add_to(m)

    # Flood memory markers
    memory = load_flood_memory()
    for rec in memory[:20]:
        if rec.get("water_pct", 0) > 20:
            folium.CircleMarker(
                [30.0, 70.0],  # approximate
                radius=8, color="red", fill=True, fill_opacity=0.6,
                tooltip=f"Water: {rec['water_pct']:.1f}% | {rec.get('scene_id','')}",
            ).add_to(m)

    st_folium(m, width=1200, height=500)

    # Flood memory table
    st.subheader("📋 Flood Memory Records")
    if memory:
        df_mem = pd.DataFrame(memory)
        st.dataframe(df_mem, width="stretch", hide_index=True)
        st.metric("Total Water Detections", len(memory))
        avg_water = np.mean([r.get("water_pct", 0) for r in memory])
        st.metric("Avg Water Coverage", f"{avg_water:.1f}%")
    else:
        st.info("No flood memory records yet. Run water detection on downloaded images to build memory.")

# ═══════════════════════════════════════════════════════════════════
# TAB 5 — IMAGE INVENTORY
# ═══════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📊 Local Image Storage Inventory")

    inv = get_local_image_inventory()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sentinel-2 Thumbnails", inv.get("sentinel2_thumbnails", 0))
    c2.metric("Historical Flood Images", inv.get("historical_floods", 0))
    c3.metric("Water Masks", inv.get("water_masks", 0))
    c4.metric("Total Files", inv.get("total", 0))

    st.markdown("### 📁 Storage Layout")
    st.code("""
storage/
├── satellite/
│   ├── sentinel2_thumbnails/   ← Recent Sentinel-2 preview JPGs
│   │   ├── Indus-Lower/
│   │   ├── Chenab-Middle/
│   │   └── ...
│   ├── hls_thumbnails/         ← NASA HLS browse images
│   └── historical_floods/      ← Flood-period images by corridor/year
│       ├── Indus-Lower/
│       │   ├── 2022_08/        ← 2022 mega flood
│       │   └── 2020_08/
│       └── ...
├── ml/
│   ├── water_masks/            ← Generated water region masks (PNG)
│   ├── clusters/               ← K-Means cluster visualization maps
│   └── models/                 ← Trained model artifacts (future)
└── flood_memory/               ← JSON records of flood/water detections
    """, language="text")

    st.warning("⚠️ Images in `storage/` are kept permanently for ML training. Do NOT delete this directory.")
