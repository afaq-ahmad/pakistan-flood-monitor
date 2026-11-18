import streamlit as st
import pandas as pd
from backend_service import data_service, DEMO_WATERMARK

st.set_page_config(page_title="Partner Mode", page_icon="🤝", layout="wide")
st.title("🤝 Partner Mode — Event Briefs & Sharing")
st.markdown("Generate exportable briefs, shareable advisory cards, and printable maps for emergency partners.")

# ── Demo / data-mode watermark (ADR-001 / P0-003) ────────────────────────────
if data_service.is_demo_mode:
    st.warning(
        f"**{DEMO_WATERMARK}**  \n"
        "Operating with prototype data. Generated briefs and advisory cards are simulated "
        "and MUST NOT be shared as real disaster advisories. Follow official NDMA/PDMA channels."
    )
elif not data_service.is_demo_mode and not __import__("os").getenv("API_BASE_URL"):
    st.error("⛔ Operational data unavailable. No live API configured.")

events = data_service.get_events_by_status(["published", "approved", "active"])
if events.empty:
    st.info("No published events available for partner exports.")
    st.stop()

selected = st.selectbox("Select Event", events["event_id"].tolist())
ev = data_service.get_event(selected)
exposure = data_service.get_exposure_for_event(selected)

st.subheader("📄 Event Brief")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Event:** {ev['event_id']}")
    st.markdown(f"**Corridor:** {ev['corridor_id']}")
    st.markdown(f"**District/Tehsil:** {ev['district']}/{ev.get('tehsil','')}")
    st.markdown(f"**Severity:** {ev['severity']}")
    st.markdown(f"**Confidence:** {ev['confidence']} ({ev.get('confidence_band','')})")
    st.markdown(f"**Status:** {ev.get('status','N/A')}")
    st.markdown(f"**Detected:** {ev.get('detected_at','N/A')}")
    st.markdown(f"**Published:** {ev.get('published_at','Not yet')}")

with col2:
    st.markdown(f"**Population Exposed:** {ev.get('population_exposed',0):,}")
    st.markdown(f"**Area Flooded:** {ev.get('affected_area_sqkm',0)} sq km")
    st.markdown(f"**Roads Exposed:** {ev.get('roads_exposed_km',0)} km")
    st.markdown(f"**Health Facilities:** {ev.get('health_facilities_exposed',0)}")
    st.markdown(f"**Schools:** {ev.get('schools_exposed',0)}")
    st.markdown(f"**Cropland:** {ev.get('cropland_exposed_sqkm',0)} sq km")

# Exposure table
if not exposure.empty:
    st.subheader("📊 District Exposure Breakdown")
    st.dataframe(exposure, width="stretch", hide_index=True)

# Shareable advisory card
st.subheader("📋 Shareable Advisory Card")
watermark_header = f"[{DEMO_WATERMARK}]\n" if data_service.is_demo_mode else ""
advisory = f"""{watermark_header}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOOD ADVISORY — {ev['severity'].upper()}
{ev['corridor_id']} near {ev['district']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Updated: {ev.get('updated_at','')}
Confidence: {ev.get('confidence_band','')}

What this means:
{ev.get('what_this_means_en','Potential flooding detected.')}

اردو:
{ev.get('what_this_means_ur','')}

What changed:
{ev.get('what_changed','')}

⚠️ LIMITATIONS: {ev.get('limitations','This alert may be delayed, incomplete, or incorrect.')}
Follow official NDMA/PDMA instructions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
st.code(advisory, language="text")
st.download_button("📥 Download Advisory Text", advisory, file_name=f"advisory_{selected}.txt")

# SitRep sections
st.subheader("📑 SitRep Sections (PDF Preview)")
with st.expander("Event Summary"):
    st.write(ev.get("what_this_means_en",""))
with st.expander("District/Tehsil Priorities"):
    if not exposure.empty:
        for _, r in exposure.iterrows():
            st.write(f"- **{r['district']}/{r.get('tehsil','')}**: Pop={r['population_exposed']:,}, Housing={r['housing_damage_class']}")
with st.expander("Recommended Actions"):
    st.write("- Monitor official NDMA/PDMA communications")
    st.write("- Prepare evacuation routes in high-impact districts")
    st.write("- Pre-position relief supplies")
with st.expander("Confidence and Limitations"):
    st.write(f"Confidence: {ev['confidence']} ({ev.get('confidence_band','')})")
    st.write(f"Limitations: {ev.get('limitations','')}")
with st.expander("Contacts"):
    st.write("- NDMA Control Room: +92-51-9205037")
    st.write("- Local EOC: [To be filled by operator]")
