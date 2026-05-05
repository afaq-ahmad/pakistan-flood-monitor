"""
🌧️ NASA Hydromet Dashboard — Pakistan Flood Monitor
Real data from NASA POWER API + NASA CMR (HLS scenes).
Uses NASA Earthdata credentials from .env.local
"""
import sys, os
from datetime import date, timedelta, datetime

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Load .env.local
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nasa_service import (
    fetch_corridor_rainfall,
    fetch_all_corridors_rainfall,
    fetch_hls_scenes,
    fetch_imerg_info,
    compute_flood_risk_score,
    CORRIDOR_POINTS,
    CORRIDOR_BBOXES,
    FLOOD_RISK_THRESHOLDS,
    NASA_USERNAME,
    NASA_BEARER,
)

st.set_page_config(page_title="NASA Hydromet Dashboard", page_icon="🌧️", layout="wide")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌧️ NASA Hydromet & Satellite Dashboard")
st.markdown(
    "Live data from **NASA POWER** (rainfall/climate) and **NASA CMR** (HLS satellite scenes). "
    "Authenticated with your NASA Earthdata account."
)

# Auth status
with st.expander("🔐 NASA Authentication Status"):
    c1, c2 = st.columns(2)
    c1.markdown(f"**Username:** `{NASA_USERNAME or 'Not set'}`")
    c1.markdown(f"**Bearer Token:** `{'✅ Set (' + str(len(NASA_BEARER)) + ' chars)' if NASA_BEARER else '❌ Not set'}`")
    c2.markdown("**APIs in use:**")
    c2.write("- NASA POWER v2.3 (no auth needed — open)")
    c2.write("- NASA CMR STAC / LPCLOUD (bearer token)")
    c2.write("- NASA CMR Collections search (bearer token)")
    if not NASA_BEARER:
        st.warning("Bearer token not found. Set NASA_BEARER_TOKEN in .env.local")
    else:
        st.success("NASA credentials loaded from .env.local")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🌧️ Rainfall Monitor",
    "📊 Flood Risk Scores",
    "🛰️ HLS Satellite Scenes",
    "📡 IMERG Products",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1 — RAINFALL MONITOR
# ═══════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🌧️ NASA POWER — Real-Time Rainfall Monitor")
    st.caption("Source: NASA POWER v2.3 — Daily rainfall, temperature, humidity per corridor")

    rc1, rc2, rc3 = st.columns(3)
    days_back = rc1.selectbox("Time window", [7, 14, 30, 60], index=2, key="pw_days")
    selected_corr = rc2.selectbox(
        "Corridor", ["All Corridors"] + list(CORRIDOR_POINTS.keys()), key="pw_corr"
    )
    auto_refresh = rc3.checkbox("Auto-load on open", value=True, key="pw_auto")

    load_btn = st.button("🚀 Fetch Live Rainfall Data", type="primary", key="pw_fetch")

    if "power_data" not in st.session_state:
        st.session_state["power_data"] = None

    if load_btn or (auto_refresh and st.session_state["power_data"] is None):
        corridors = list(CORRIDOR_POINTS.keys()) if selected_corr == "All Corridors" else [selected_corr]
        prog = st.progress(0, "Fetching NASA POWER data…")
        data = {}
        for i, corr in enumerate(corridors):
            prog.progress((i + 1) / len(corridors), f"Fetching {corr}…")
            data[corr] = fetch_corridor_rainfall(corr, int(days_back))
        prog.empty()
        st.session_state["power_data"] = data
        st.success(f"✅ NASA POWER data loaded for {len(data)} corridors")

    power_data = st.session_state.get("power_data")

    if power_data:
        # ── Overview map with rainfall bubbles ─────────────────────────────
        st.subheader("🗺️ Rainfall Map")
        m = folium.Map(location=[30.0, 70.0], zoom_start=5, tiles="CartoDB dark_matter")
        risk_colors = {"critical": "#FF3333", "warning": "#FF8800", "watch": "#FFDD00", "normal": "#44CC44"}

        for corr, d in power_data.items():
            if "error" in d:
                continue
            lon, lat = d["lon"], d["lat"]
            r72h = d["rainfall_mm"]["72h"]
            r7d  = d["rainfall_mm"]["7d"]
            level = d["risk_level"]
            color = risk_colors.get(level, "#888888")

            popup = f"""
            <b>{corr}</b><br>
            <span style='color:{color}'>●</span> Risk: <b>{level.upper()}</b><br>
            Rainfall 72h: <b>{r72h:.1f} mm</b><br>
            Rainfall 7d: <b>{r7d:.1f} mm</b><br>
            Rainfall 30d: <b>{d['rainfall_mm']['30d']:.1f} mm</b>
            """
            radius = max(15, min(50, r72h / 2))
            folium.CircleMarker(
                [lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(popup, max_width=220),
                tooltip=f"{corr}: {r72h:.1f}mm / 72h",
            ).add_to(m)

            # Risk threshold annotation
            if r72h > FLOOD_RISK_THRESHOLDS["rain_72h_warning_mm"]:
                folium.Marker(
                    [lat + 0.3, lon],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size:12px;color:{color};font-weight:bold">⚠️{corr[:6]}</div>'
                    ),
                ).add_to(m)

        st_folium(m, width=1200, height=450)

        # ── Summary metrics ────────────────────────────────────────────────
        st.subheader("📊 Corridor Rainfall Summary")
        rows = []
        for corr, d in power_data.items():
            if "error" in d:
                rows.append({"Corridor": corr, "Error": d["error"]})
            else:
                level = d["risk_level"]
                icon = {"critical": "🔴", "warning": "🟠", "watch": "🟡", "normal": "🟢"}.get(level, "⚪")
                rows.append({
                    "Corridor":     corr,
                    "Risk Level":   f"{icon} {level.upper()}",
                    "Rain 72h (mm)": d["rainfall_mm"]["72h"],
                    "Rain 7d (mm)":  d["rainfall_mm"]["7d"],
                    "Rain 30d (mm)": d["rainfall_mm"]["30d"],
                    "Data Days":     d.get("daily_series", {}).get("dates", []) and len(d["daily_series"]["dates"]),
                })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        # Thresholds reference
        with st.expander("📏 Risk Thresholds"):
            st.markdown(f"""
            | Threshold | Value |
            |-----------|-------|
            | 72h Warning  | {FLOOD_RISK_THRESHOLDS['rain_72h_warning_mm']} mm |
            | 72h Critical | {FLOOD_RISK_THRESHOLDS['rain_72h_critical_mm']} mm |
            | 7d Warning   | {FLOOD_RISK_THRESHOLDS['rain_7d_warning_mm']} mm |
            | 7d Critical  | {FLOOD_RISK_THRESHOLDS['rain_7d_critical_mm']} mm |
            """)

        # ── Time series chart ──────────────────────────────────────────────
        st.subheader("📈 Daily Rainfall Time Series")
        chart_corr = st.selectbox("Select corridor", list(power_data.keys()), key="ts_corr")
        sel_data = power_data.get(chart_corr, {})

        if "daily_series" in sel_data and sel_data["daily_series"]["dates"]:
            ds = sel_data["daily_series"]
            df_ts = pd.DataFrame({
                "Date":         pd.to_datetime(ds["dates"], format="%Y%m%d"),
                "Rainfall mm":  ds["rainfall"],
                "Temp °C":      [t for t in ds["temp_c"]],
                "Humidity %":   [h for h in ds["humidity"]],
                "Wind m/s":     [w for w in ds["wind_ms"]],
            }).set_index("Date")

            metric_choice = st.multiselect(
                "Variables to plot",
                ["Rainfall mm", "Temp °C", "Humidity %", "Wind m/s"],
                default=["Rainfall mm"],
                key="ts_vars",
            )
            if metric_choice:
                st.line_chart(df_ts[metric_choice])

            # Show threshold lines
            r72h = sel_data["rainfall_mm"]["72h"]
            r7d  = sel_data["rainfall_mm"]["7d"]
            c1, c2, c3 = st.columns(3)
            c1.metric("72h Rainfall", f"{r72h:.1f} mm",
                      delta=f"{r72h - FLOOD_RISK_THRESHOLDS['rain_72h_warning_mm']:.1f} mm vs warning",
                      delta_color="inverse")
            c2.metric("7d Rainfall", f"{r7d:.1f} mm")
            c3.metric("Risk Level", sel_data["risk_level"].upper())

            with st.expander("📋 Raw Daily Table"):
                st.dataframe(df_ts.reset_index(), width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — FLOOD RISK SCORES
# ═══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 Hydromet Flood Risk Scores")
    st.caption("Fuses 72h / 7d / 30d NASA POWER rainfall into a composite flood risk score per corridor")

    power_data2 = st.session_state.get("power_data")
    if not power_data2:
        st.info("👈 First load data on the **Rainfall Monitor** tab.")
    else:
        risk_scores = compute_flood_risk_score(power_data2)

        # Risk scorecard
        cols = st.columns(3)
        for i, (corr, rs) in enumerate(risk_scores.items()):
            col = cols[i % 3]
            if "error" in rs:
                col.error(f"**{corr}**: {rs['error']}")
                continue
            level = rs["risk_level"]
            color = {"critical": "🔴", "warning": "🟠", "watch": "🟡", "normal": "🟢"}.get(level, "⚪")
            with col:
                st.markdown(f"### {color} {corr}")
                st.metric("Risk Score", f"{rs['risk_score']:.0%}")
                st.write(f"Level: **{level.upper()}**")
                st.write(f"72h: {rs['rain_72h']:.1f}mm | 7d: {rs['rain_7d']:.1f}mm")
                st.progress(float(rs["risk_score"]))

        # Combined bar chart
        st.subheader("📊 Risk Score Comparison")
        df_risk = pd.DataFrame([
            {"Corridor": k, "Risk Score": v["risk_score"], "72h Rain (mm)": v.get("rain_72h", 0)}
            for k, v in risk_scores.items() if "error" not in v
        ])
        if not df_risk.empty:
            st.bar_chart(df_risk.set_index("Corridor")[["Risk Score", "72h Rain (mm)"]])

        # Fusion explanation
        with st.expander("ℹ️ How is the risk score computed?"):
            st.markdown("""
            The composite flood risk score fuses three rainfall windows:
            ```
            score = 0.50 × min(rain_72h / 100, 1.0)
                  + 0.30 × min(rain_7d  / 200, 1.0)
                  + 0.20 × min(rain_30d / 300, 1.0)
            ```
            - **72h weight (50%)**: Most important — heavy short burst causes flash floods
            - **7d weight (30%)**: Cumulative basin saturation
            - **30d weight (20%)**: Seasonal background moisture

            This mirrors the `TriggerInputs.rainfall_mm_72h` used in `pipeline/runner.py`.
            """)


# ═══════════════════════════════════════════════════════════════════
# TAB 3 — HLS SATELLITE SCENES
# ═══════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🛰️ NASA HLS — Harmonized Landsat Sentinel-2 Scenes")
    st.caption("HLS provides cloud-masked, surface-reflectance scenes at 30m — used for NDWI water detection")

    hc1, hc2, hc3, hc4 = st.columns(4)
    hls_corr   = hc1.selectbox("Corridor", list(CORRIDOR_BBOXES.keys()), key="hls_corr")
    hls_days   = hc2.number_input("Days back", 7, 60, 14, key="hls_days")
    hls_cloud  = hc3.number_input("Max cloud %", 0, 100, 40, key="hls_cloud")
    hls_sensor = hc4.selectbox("Sensor", ["both", "landsat", "sentinel"], key="hls_sensor")

    if st.button("🛰️ Fetch HLS Scenes", type="primary", key="hls_fetch"):
        with st.spinner("Querying NASA CMR STAC for HLS scenes…"):
            scenes = fetch_hls_scenes(
                corridor=hls_corr,
                days_back=int(hls_days),
                max_items=15,
                cloud_max=float(hls_cloud),
                sensor=hls_sensor,
            )
        st.session_state["hls_scenes"] = {"scenes": scenes, "corridor": hls_corr}
        ok = [s for s in scenes if "error" not in s]
        st.success(f"Found {len(ok)} HLS scenes for {hls_corr}")

    hls_state = st.session_state.get("hls_scenes")
    if hls_state:
        scenes = hls_state["scenes"]
        ok_scenes = [s for s in scenes if "error" not in s]

        if ok_scenes:
            # Summary table
            df_hls = pd.DataFrame([{
                "Scene ID":    s["scene_id"],
                "Sensor":      s["sensor"],
                "Date":        s["date"],
                "Cloud %":     s.get("cloud_pct", "N/A"),
                "Collection":  s["collection"],
                "Has Thumb":   "✅" if s.get("thumbnail") else "❌",
            } for s in ok_scenes])
            st.dataframe(df_hls, width="stretch", hide_index=True)

            # Thumbnails
            st.subheader("🖼️ Scene Thumbnails")
            thumb_scenes = [s for s in ok_scenes if s.get("thumbnail", "").startswith("https://")]
            if thumb_scenes:
                cols = st.columns(min(len(thumb_scenes), 4))
                for i, sc in enumerate(thumb_scenes[:8]):
                    with cols[i % 4]:
                        st.image(
                            sc["thumbnail"],
                            caption=f"{sc['scene_id'][:20]}\n{sc['date']} ☁️{sc.get('cloud_pct','?')}%",
                            use_container_width=True,
                        )
            else:
                st.info("No HTTPS thumbnails available for this selection. HLS thumbnails may require authentication for direct access.")

            # Map of scene footprints
            st.subheader("🗺️ HLS Scene Footprints")
            m2 = folium.Map(location=[30.0, 70.0], zoom_start=5, tiles="CartoDB positron")
            colors_hls = {"Landsat-8/9": "#FFC107", "Sentinel-2": "#2196F3"}
            for sc in ok_scenes:
                b = sc.get("bbox", CORRIDOR_BBOXES.get(hls_corr, [60, 24, 77, 37]))
                c = colors_hls.get(sc.get("sensor", ""), "#888")
                folium.Rectangle(
                    bounds=[[b[1], b[0]], [b[3], b[2]]],
                    color=c, weight=2, fill=True, fill_opacity=0.15,
                    tooltip=f"{sc['scene_id']} | {sc['date']} | {sc.get('cloud_pct','?')}%",
                    popup=folium.Popup(
                        f"<b>{sc['scene_id']}</b><br>Sensor: {sc['sensor']}<br>"
                        f"Date: {sc['date']}<br>Cloud: {sc.get('cloud_pct','?')}%",
                        max_width=200
                    ),
                ).add_to(m2)
            st_folium(m2, width=1200, height=400)

            # Scene detail inspector
            st.subheader("🔬 Scene Inspector")
            scene_ids = [s["scene_id"] for s in ok_scenes]
            sel_sid   = st.selectbox("Select scene", scene_ids, key="hls_inspect")
            sel_sc    = next((s for s in ok_scenes if s["scene_id"] == sel_sid), None)
            if sel_sc:
                ic1, ic2 = st.columns(2)
                with ic1:
                    st.write(f"**Collection:** {sel_sc['collection']}")
                    st.write(f"**Sensor:** {sel_sc['sensor']}")
                    st.write(f"**Date:** {sel_sc['date']}")
                    st.write(f"**Cloud Cover:** {sel_sc.get('cloud_pct','?')}%")
                    st.write("**Available Bands/Assets:**")
                    for k, v in sel_sc.get("assets", {}).items():
                        st.write(f"  `{k}`: …{v[-40:]}" if len(v) > 40 else f"  `{k}`: {v}")
                with ic2:
                    st.write("**NDWI Water Detection (conceptual):**")
                    st.info(
                        "NDWI = (Green − NIR) / (Green + NIR)\n\n"
                        "HLS bands used:\n"
                        "- Band 3 (Green) — B03 / B3\n"
                        "- Band 5 (NIR) — B05 / B5\n\n"
                        "Threshold: NDWI > 0.2 indicates open water.\n"
                        "This is what `detection.py` computes for each scene."
                    )
        else:
            st.warning("No valid HLS scenes found. Try adjusting cloud cover threshold or date range.")
            if any("error" in s for s in scenes):
                for s in scenes:
                    if "error" in s:
                        st.error(f"{s.get('scene_id','?')}: {s['error']}")


# ═══════════════════════════════════════════════════════════════════
# TAB 4 — IMERG PRODUCTS
# ═══════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📡 NASA GPM IMERG Products")
    st.caption("IMERG = Integrated Multi-satellitE Retrievals for GPM — 30-min global precipitation")

    st.markdown("""
    IMERG provides the **most accurate near-real-time global rainfall** data.
    It is a core hydromet trigger in this system — confirming satellite SAR anomalies
    with actual measured precipitation.
    """)

    if st.button("📡 List Available IMERG Products", key="imerg_fetch"):
        with st.spinner("Querying NASA CMR…"):
            products = fetch_imerg_info()
        st.session_state["imerg_products"] = products

    imerg_prods = st.session_state.get("imerg_products")
    if imerg_prods:
        df_imerg = pd.DataFrame(imerg_prods)
        if "error" not in df_imerg.columns:
            st.dataframe(df_imerg, width="stretch", hide_index=True)

    st.markdown("---")
    st.subheader("🔗 IMERG Data Access Guide")
    st.markdown("""
    | Product | Latency | Resolution | Best for |
    |---------|---------|-----------|---------|
    | **IMERG Early** (3IMERGHHE) | ~4h | 30 min / 0.1° | Near-real-time alerts |
    | **IMERG Late** (3IMERGHHL) | ~14h | 30 min / 0.1° | Better calibrated |
    | **IMERG Final** (3IMERGHH) | ~3.5 months | 30 min / 0.1° | Validation, training |
    | **IMERG Daily** (3IMERGDF) | ~3.5 months | Daily / 0.1° | Event accumulation |
    """)

    with st.expander("📥 How to access IMERG data with your credentials"):
        st.code(f"""
# Option 1: GES DISC OPeNDAP (direct download)
import requests
url = "https://gpm.nasa.gov/data/imerg"
headers = {{"Authorization": "Bearer YOUR_TOKEN"}}

# Option 2: NASA Earthdata Search
# Go to: https://search.earthdata.nasa.gov/search?q=IMERG
# Use username: {NASA_USERNAME}

# Option 3: Python earthaccess library (recommended)
# pip install earthaccess
import earthaccess
auth = earthaccess.login(strategy="token", token="YOUR_TOKEN")
results = earthaccess.search_data(
    short_name="GPM_3IMERGDF",
    bounding_box=(66.8, 25.2, 74.0, 34.6),  # Pakistan
    temporal=("2026-04-01", "2026-05-01"),
)
earthaccess.download(results, "./imerg_data/")
        """, language="python")

    st.subheader("⚡ How IMERG fits in the pipeline")
    st.markdown("""
    ```
    Sentinel-1 SAR → backscatter_drop detected
           ↓
    IMERG 72h rainfall > 50mm threshold?  ← NASA POWER used as proxy
           ↓ YES
    Flood Candidate created → Analyst Review Queue
           ↓
    Sentinel-2 NDWI optical corroboration (HLS scenes)
           ↓
    Exposure estimation → Alert published
    ```
    Currently **NASA POWER** is used as an IMERG proxy (same variables, easier access).
    Upgrading to raw IMERG sub-daily data requires the `earthaccess` download step above.
    """)
