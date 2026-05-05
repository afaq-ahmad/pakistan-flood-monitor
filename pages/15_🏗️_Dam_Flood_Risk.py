"""Page 15 — Dam-Aware Flood Risk Analysis Dashboard."""
import streamlit as st
import sys, os, json, time
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pakistan_flood_monitor.services.dam_service import (
    get_upstream_dams, get_all_dams, compute_dam_aware_risk,
    detect_reservoir_fill, load_fill_history, CORRIDOR_RIVER_MAP,
    RIVER_FLOW_GRAPH, DAMS_DATABASE,
)
from satellite_ml_service import CORRIDOR_BBOXES, RIVER_PATHS

st.set_page_config(page_title="Dam-Aware Flood Risk", page_icon="🏗️", layout="wide")
st.title("🏗️ Dam-Aware Flood Risk Analysis")
st.markdown(
    "Analyze how upstream dam fill levels affect downstream flood probability. "
    "Includes cross-border dams in India and Afghanistan."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
corridor = st.sidebar.selectbox("Select Downstream Corridor", list(CORRIDOR_BBOXES.keys()))

tabs = st.tabs([
    "1. Dam Map & Connections",
    "2. Reservoir Fill Status",
    "3. Flood Risk Score",
    "4. Fill History",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Map showing dams, river paths, and downstream region
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Upstream Dam Network")
    dams = get_upstream_dams(corridor)

    if not dams:
        st.warning("No upstream dams mapped for this corridor yet.")
    else:
        # Build map
        bbox = CORRIDOR_BBOXES[corridor]
        center_lat = (bbox[1] + bbox[3]) / 2
        center_lon = (bbox[0] + bbox[2]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6,
                       tiles="CartoDB positron")

        # Draw downstream region
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color="#2196F3", weight=3, fill=True, fillOpacity=0.15,
            tooltip=f"Downstream: {corridor}",
        ).add_to(m)

        # Draw river paths
        rivers = CORRIDOR_RIVER_MAP.get(corridor, [])
        for river in rivers:
            waypoints = RIVER_PATHS.get(river, [])
            if waypoints:
                folium.PolyLine(
                    waypoints, color="#1565C0", weight=3,
                    opacity=0.7, tooltip=f"{river} River",
                ).add_to(m)

        # Draw dams with flow-order labels
        for dam in dams:
            color = "#F44336" if dam["is_cross_border"] else "#FF9800"
            icon_color = "red" if dam["is_cross_border"] else "orange"
            popup_html = (
                f"<b>{dam['name']}</b><br>"
                f"Country: {dam['country']}<br>"
                f"River: {dam['river']}<br>"
                f"Capacity: {dam['capacity_mcm']} MCM<br>"
                f"Height: {dam['height_m']}m<br>"
                f"Distance: {dam['distance_km']} km<br>"
                f"Flow Order: #{dam['river_connection_order']}"
            )
            folium.Marker(
                [dam["lat"], dam["lon"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"#{dam['river_connection_order']} {dam['name']} ({dam['country']})",
                icon=folium.Icon(color=icon_color, icon="tint", prefix="fa"),
            ).add_to(m)

            # Draw dam→downstream flow line
            folium.PolyLine(
                [[dam["lat"], dam["lon"]], [center_lat, center_lon]],
                color=color, weight=1, dash_array="5",
                opacity=0.4, tooltip=f"{dam['name']} → {corridor}",
            ).add_to(m)

        st_folium(m, width=900, height=500)

        # Table
        st.subheader("Connected Dams")
        df = pd.DataFrame(dams)
        display_cols = ["river_connection_order", "name", "country", "river",
                        "capacity_mcm", "distance_km", "relationship_confidence"]
        st.dataframe(df[display_cols].rename(columns={
            "river_connection_order": "Flow #",
            "name": "Dam Name",
            "country": "Country",
            "river": "River",
            "capacity_mcm": "Capacity (MCM)",
            "distance_km": "Distance (km)",
            "relationship_confidence": "Confidence",
        }), hide_index=True, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Reservoir Fill Status
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Reservoir Fill Detection")
    st.info("Uses the existing satellite ML pipeline (K-Means water clustering) "
            "on Sentinel-2 imagery of each dam's reservoir bounding box.")

    dams = get_upstream_dams(corridor)
    if not dams:
        st.warning("No upstream dams for this corridor.")
    else:
        if st.button("🔍 Analyze All Upstream Dams", type="primary"):
            fills = []
            progress = st.progress(0)
            for i, dam in enumerate(dams):
                with st.spinner(f"Analyzing {dam['name']}..."):
                    fill = detect_reservoir_fill(dam)
                    fills.append(fill)
                progress.progress((i + 1) / len(dams))
            st.session_state["dam_fills"] = fills

        if "dam_fills" in st.session_state:
            fills = st.session_state["dam_fills"]
            cols = st.columns(min(4, len(fills)))
            for i, fill in enumerate(fills):
                col = cols[i % len(cols)]
                level = fill["fill_level"]
                emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}[level]
                trend_icon = {"rising": "📈", "stable": "➡️", "falling": "📉"}[fill["trend"]]
                col.metric(
                    label=f"{emoji} {fill['dam_name']}",
                    value=f"{fill['water_pct']:.1f}%",
                    delta=f"{fill['trend']} {trend_icon}",
                )
            # Detailed table
            df_fills = pd.DataFrame(fills)
            st.dataframe(df_fills[["dam_name", "water_pct", "fill_level",
                                    "trend", "confidence", "capacity_mcm"]],
                         hide_index=True, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Dam-Aware Flood Risk Score
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Dam-Enhanced Flood Risk Score")
    st.markdown("Combines upstream dam fill intelligence with existing rainfall "
                "data to produce an enhanced, explainable flood probability.")

    if st.button("⚡ Compute Dam-Aware Risk", type="primary"):
        with st.spinner("Analyzing all upstream dams and computing risk..."):
            risk = compute_dam_aware_risk(corridor)
            st.session_state["dam_risk"] = risk

    if "dam_risk" in st.session_state:
        risk = st.session_state["dam_risk"]

        c1, c2, c3 = st.columns(3)
        prob = risk["flood_probability"]
        level = risk["risk_level"]
        color = {"low": "green", "medium": "orange", "high": "red", "critical": "darkred"}[level]

        c1.metric("Flood Probability", f"{prob}%")
        c2.metric("Risk Level", level.upper())
        c3.metric("Upstream Dams", risk["dam_count"])

        # Alert
        if level in ("high", "critical"):
            st.error(
                f"🚨 **DAM-AWARE ALERT — {corridor}**: Flood probability is "
                f"**{prob}%** ({level.upper()}). Immediate monitoring recommended."
            )
        elif level == "medium":
            st.warning(f"⚠️ Moderate flood risk ({prob}%) on {corridor}.")
        else:
            st.success(f"✅ Low flood risk ({prob}%) on {corridor}.")

        # Explanations
        st.subheader("Why this risk level?")
        for i, reason in enumerate(risk["main_reasons"], 1):
            st.markdown(f"**{i}.** {reason}")

        # Scoring breakdown
        if risk.get("dam_scores"):
            st.subheader("Scoring Breakdown")
            df_scores = pd.DataFrame(risk["dam_scores"])
            st.dataframe(df_scores, hide_index=True, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: Historical Fill Trend
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Dam Fill Level History")
    dams = get_upstream_dams(corridor)
    if not dams:
        st.warning("No upstream dams for this corridor.")
    else:
        selected_dam = st.selectbox("Select Dam", [d["name"] for d in dams])
        dam_id = next(d["dam_id"] for d in dams if d["name"] == selected_dam)
        history = load_fill_history(dam_id)

        if history:
            df_hist = pd.DataFrame(history)
            df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
            st.line_chart(df_hist.set_index("timestamp")["water_pct"])
            st.dataframe(df_hist[["timestamp", "water_pct", "fill_level", "trend"]],
                         hide_index=True)
        else:
            st.info("No fill history yet. Run the fill detection first to start recording.")
