import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from backend_service import data_service

st.set_page_config(page_title="Public Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 Public Flood Dashboard")
st.markdown("Live situational awareness for monitored river corridors in Pakistan.")

# Emergency banner
fresh = data_service.freshness_status()
if fresh["status"] == "stale":
    st.error(f"⚠️ DATA MAY BE STALE — Last update: {fresh.get('last_completed','unknown')}. Follow official NDMA/PDMA channels.")
elif fresh["status"] == "watch":
    st.warning(f"🟡 Data freshness watch — {fresh['message']}")
else:
    st.success(f"🟢 System active — {fresh['message']}")

# Search my area
st.subheader("🔍 Search My Area")
events = data_service.get_events()
districts = sorted(events["district"].dropna().unique().tolist()) if not events.empty else []
search = st.selectbox("Search by district", ["All"] + districts)
if search != "All":
    events = events[events["district"] == search]

# Stats
stats = data_service.summary_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Active Alerts", stats.get("active_events", 0))
c2.metric("Critical Zones", stats.get("critical_zones", 0))
c3.metric("Population at Risk", f"{stats.get('total_population',0):,}")
c4.metric("Avg Confidence", f"{stats.get('avg_confidence',0)*100:.0f}%")

# Map
st.subheader("🗺️ Flood Map Overview")
pub_events = data_service.get_events() if search == "All" else events
sev_colors = {"critical": "red", "warning": "orange", "watch": "gold", "low": "blue"}

m = folium.Map(location=[30.37, 69.34], zoom_start=5, tiles="CartoDB dark_matter")
for _, row in pub_events.iterrows():
    if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
        color = sev_colors.get(str(row.get("severity","")), "blue")
        popup = f"<b>{row['event_id']}</b><br>District: {row['district']}<br>Severity: {row['severity']}<br>Confidence: {row['confidence']}<br>Status: {row['status']}"
        folium.CircleMarker([row["latitude"], row["longitude"]], radius=10, color=color,
                            fill=True, fill_opacity=0.7, popup=popup,
                            tooltip=f"{row['event_id']} — {row['district']}").add_to(m)

# Corridors
corridors = data_service.get_corridors()
for _, c in corridors.iterrows():
    folium.PolyLine([[c["start_lat"], c["start_lon"]], [c["end_lat"], c["end_lon"]]],
                    color="cyan", weight=2, opacity=0.6, tooltip=c["corridor_name"]).add_to(m)

st_folium(m, width=1200, height=500)

# Public alert cards
st.subheader("🚨 Active Alert Cards")
published = data_service.get_events_by_status(["published", "active", "approved"])
if published.empty:
    st.info("No active alerts at this time.")
else:
    for _, ev in published.iterrows():
        sev = str(ev.get("severity","")).upper()
        band = str(ev.get("confidence_band",""))
        with st.expander(f"{'🔴' if sev=='CRITICAL' else '🟠' if sev=='WARNING' else '🟡'} **{sev}** — {ev.get('corridor_id','')} near {ev.get('district','')} | Confidence: {band} | Updated: {ev.get('updated_at','')}"):
            st.markdown(f"**Event ID:** {ev['event_id']}")
            st.markdown(f"**What changed:** {ev.get('what_changed','N/A')}")
            st.markdown(f"**What this means:** {ev.get('what_this_means_en','N/A')}")
            st.markdown(f"**اردو:** {ev.get('what_this_means_ur','N/A')}")
            st.caption(f"⚠️ {ev.get('limitations','This alert may be delayed, incomplete, or incorrect. Follow official instructions.')}")

# Impact summary
st.subheader("📊 Impact Summary")
exposure = data_service.get_exposure()
if not exposure.empty:
    st.dataframe(exposure[["event_id","district","flooded_area_sqkm","population_exposed",
                           "roads_exposed_km","health_facilities_exposed","schools_exposed",
                           "cropland_sqkm","housing_damage_class","infrastructure_damage_class"]],
                 width="stretch", hide_index=True)

# How to read this map
with st.expander("ℹ️ How to Read This Map"):
    st.markdown("""
    - **Red circles**: Critical severity events — high confidence, large impact
    - **Orange circles**: Warning level events — confirmed flooding
    - **Yellow circles**: Watch level — lower confidence, monitoring needed
    - **Cyan lines**: Monitored river corridors
    - **Confidence bands**: Low (<50%), Medium (50-75%), High (>75%)
    - Map data is updated after each pipeline run (target: every 30 minutes)
    """)

# Limitations
with st.expander("⚠️ Limitations and Official Guidance"):
    st.markdown("""
    - This system is for **situational awareness only** and is not a replacement for official emergency instructions.
    - Confidence scores are model-derived and can be delayed, incomplete, or incorrect.
    - Flood extents are based on satellite imagery which may have cloud interference or timing gaps.
    - Population and infrastructure exposure estimates use baseline data which may not reflect current conditions.
    - **Always follow instructions from NDMA, PDMA, and local authorities.**
    """)
