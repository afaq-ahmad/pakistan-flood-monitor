import streamlit as st

st.set_page_config(page_title="Pakistan Flood Monitor", page_icon="🌊", layout="wide")

st.sidebar.title("🌊 Pakistan Flood Monitor")
st.sidebar.markdown("---")
st.sidebar.caption("Satellite-driven flood monitoring system")

st.title("Welcome to Pakistan Flood Monitor")
st.markdown("Use the sidebar to navigate between pages.")

from backend_service import data_service
stats = data_service.summary_stats()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active Events", stats.get("active_events", 0))
c2.metric("Critical Zones", stats.get("critical_zones", 0))
c3.metric("Population at Risk", f"{stats.get('total_population', 0):,}")
c4.metric("Pending Review", stats.get("pending_review", 0))

fresh = data_service.freshness_status()
color = {"fresh": "🟢", "watch": "🟡", "stale": "🔴"}.get(fresh["status"], "⚪")
st.info(f"{color} **Data Freshness:** {fresh['message']} — Status: **{fresh['status'].upper()}**")

st.markdown("""
> **Limitations:** This system is for situational awareness only. Confidence scores are model-derived and may be delayed.
> Do not use as the sole evacuation trigger. Follow official NDMA/PDMA instructions.
""")
