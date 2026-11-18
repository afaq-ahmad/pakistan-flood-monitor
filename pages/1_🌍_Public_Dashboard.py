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

st.subheader("My Area")
corridor_names = tuple(corridor.name for corridor in settings.pilot_corridors)
selected_corridor = None
if corridor_names:
    selected_corridor = st.selectbox(
        "River corridor",
        [None, *corridor_names],
        format_func=lambda name: name if name is not None else "All published events",
        key="my_area_corridor",
    )
else:
    st.info("No reference river corridors are configured.")
st.caption(
    "The list comes from the pilot corridor configuration. District, tehsil, village and "
    "farm coverage is unverified. Check official sources for current notices."
)

events = data_service.get_public_events()
if data_service.event_api_error:
    st.error(f"Event information is unavailable. {data_service.event_api_error}")
    st.stop()

if not data_service.is_demo_mode:
    st.caption("Event feed freshness is unavailable.")

if selected_corridor is not None and not events.empty:
    if not events["corridor_id"].isin(corridor_names).all():
        st.caption("Events without a configured corridor are available in the all-events view.")
    events = events[events["corridor_id"] == selected_corridor]

if events.empty:
    message = (
        f"No published events are linked to {selected_corridor} in this feed."
        if selected_corridor is not None else "No published events were returned."
    )
    st.info(f"{message} Conditions may still be unknown.")
    st.stop()

if data_service.is_demo_mode:
    districts = sorted(events["district"].dropna().unique())
    district = st.selectbox("Filter demo events by district", ["All", *districts], key="demo_district")
    if district in districts:
        events = events[events["district"] == district]

st.metric("Published events", len(events))


def event_area_label(event: pd.Series) -> str:
    if data_service.is_demo_mode and pd.notna(event["district"]):
        return str(event["district"])
    if event["corridor_id"] in corridor_names:
        return str(event["corridor_id"])
    return "Corridor unavailable"


st.subheader("Published events")
for _, event in events.iterrows():
    with st.expander(f"{event['event_id']} · {event_area_label(event)}"):
        for label, field in (("Published", "published_at"), ("Detected", "detected_at")):
            date = event.get(field)
            st.write(f"{label}: {date}" if pd.notna(date) else f"{label} time unavailable.")
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

if st.checkbox("Show map", key="my_area_map"):
    st.subheader("Flood Map Overview")
    sev_colors = {"critical": "red", "warning": "orange", "watch": "gold", "low": "blue"}
    m = folium.Map(location=[30.37, 69.34], zoom_start=5, tiles="OpenStreetMap")
    for _, row in events.iterrows():
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            color = sev_colors.get(row.get("severity"), "blue") if data_service.is_demo_mode else "blue"
            event_id = escape(str(row["event_id"]))
            area = escape(event_area_label(row))
            folium.CircleMarker(
                [row["latitude"], row["longitude"]], radius=10, color=color, fill=True,
                fill_opacity=0.7, popup=f"<b>{event_id}</b><br>{area}", tooltip=f"{event_id} — {area}",
            ).add_to(m)

    corridors = data_service.get_corridors()
    if selected_corridor is not None and not corridors.empty:
        corridors = corridors[corridors["corridor_id"] == selected_corridor]
    for _, corridor in corridors.iterrows():
        folium.PolyLine(
            [[corridor["start_lat"], corridor["start_lon"]], [corridor["end_lat"], corridor["end_lon"]]],
            color="cyan", weight=2, opacity=0.6, tooltip=corridor["corridor_name"],
        ).add_to(m)

    st.caption("Circles show published events with a mapped location. Cyan lines are reference lines.")
    st_folium(m, use_container_width=True, height=420, returned_objects=[])

# Limitations
with st.expander("⚠️ Limitations and Official Guidance"):
    st.markdown("""
    - This system is for **situational awareness only** and is not a replacement for official emergency instructions.
    - Confidence scores are model-derived and can be delayed, incomplete, or incorrect.
    - Flood extents are based on satellite imagery which may have cloud interference or timing gaps.
    - Population and infrastructure exposure estimates use baseline data which may not reflect current conditions.
    - **Always follow instructions from NDMA, PDMA, and local authorities.**
    """)
