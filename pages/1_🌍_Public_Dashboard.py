from html import escape

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from backend_service import DEMO_WATERMARK, DataService
from pakistan_flood_monitor.config import settings

st.set_page_config(page_title="Public Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 Public Flood Dashboard")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information")
data_service = DataService()
if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)
    fresh = data_service.freshness_status()
    st.caption(f"Demo run freshness: {fresh['message']}")

st.subheader("Reference river corridors")
if settings.pilot_corridors:
    st.write(", ".join(corridor.name for corridor in settings.pilot_corridors))
else:
    st.info("No reference river corridors are configured.")
st.caption(
    "These are configured reference names. District, tehsil, village and farm coverage is unverified. "
    "Check official sources for current notices."
)

events = data_service.get_public_events()
if data_service.event_api_error:
    st.error(f"Event information is unavailable. {data_service.event_api_error}")
    st.stop()

if not data_service.is_demo_mode:
    st.caption("Event feed freshness is unavailable.")

if events.empty:
    st.info("No published events were returned. Conditions may still be unknown.")
    st.stop()

st.subheader("🔍 Search My Area")
districts = sorted(events["district"].dropna().unique())
search = st.selectbox("Search by district", ["All"] + districts)
if search != "All":
    events = events[events["district"] == search]

st.metric("Published events", len(events))

# Map
st.subheader("🗺️ Flood Map Overview")
sev_colors = {"critical": "red", "warning": "orange", "watch": "gold", "low": "blue"}

m = folium.Map(location=[30.37, 69.34], zoom_start=5, tiles="OpenStreetMap")
for _, row in events.iterrows():
    if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
        color = sev_colors.get(row.get("severity"), "blue") if data_service.is_demo_mode else "blue"
        event_id = escape(str(row["event_id"]))
        district = escape(str(row["district"])) if pd.notna(row["district"]) else "District unavailable"
        popup = f"<b>{event_id}</b><br>District: {district}"
        folium.CircleMarker([row["latitude"], row["longitude"]], radius=10, color=color,
                            fill=True, fill_opacity=0.7, popup=popup,
                            tooltip=f"{event_id} — {district}").add_to(m)

# Corridors
corridors = data_service.get_corridors()
for _, c in corridors.iterrows():
    folium.PolyLine([[c["start_lat"], c["start_lon"]], [c["end_lat"], c["end_lon"]]],
                    color="cyan", weight=2, opacity=0.6, tooltip=c["corridor_name"]).add_to(m)

st_folium(m, width=1200, height=500)

st.subheader("Published events")
for _, event in events.iterrows():
    district = event["district"] if pd.notna(event["district"]) else "District unavailable"
    with st.expander(f"{event['event_id']} · {district}"):
        updated_at = event.get("updated_at")
        st.write(f"Event timestamp: {updated_at}" if pd.notna(updated_at) else "Event timestamp unavailable.")
        if data_service.is_demo_mode:
            for label, field in (
                ("Severity", "severity"),
                ("What changed", "what_changed"),
                ("What this means", "what_this_means_en"),
                ("اردو", "what_this_means_ur"),
            ):
                if pd.notna(event.get(field)):
                    st.write(f"**{label}** {event[field]}")

# Impact summary
st.subheader("📊 Impact Summary")
exposure = data_service.get_exposure()
if not exposure.empty:
    exposure = exposure[exposure["event_id"].isin(events["event_id"])]
if not exposure.empty:
    if data_service.exposure_data_source == "local_csv":
        st.caption(
            f"ℹ️ {DEMO_WATERMARK} — Exposure figures below are from prototype "
            "CSV data and are not derived from the current live event feed."
        )
    st.dataframe(exposure[["event_id","district","flooded_area_sqkm","population_exposed",
                           "roads_exposed_km","health_facilities_exposed","schools_exposed",
                           "cropland_sqkm","housing_damage_class","infrastructure_damage_class"]],
                 width="stretch", hide_index=True)
else:
    st.info("Exposure data is unavailable for the selected events.")

# How to read this map
with st.expander("ℹ️ How to Read This Map"):
    st.markdown("""
    - Circles show mapped published events. Demo marker colours reflect fixture severity.
    - Cyan lines show reference corridors.
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
