import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Pakistan Flood Monitor", page_icon="🌊", layout="wide")

st.sidebar.title("🌊 Pakistan Flood Monitor")
st.sidebar.caption("Satellite-driven flood monitoring system")

st.title("Pakistan Flood Monitor")
data_service = DataService()
events = data_service.get_public_events()

if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)
if data_service.event_api_error:
    st.error(f"Event information is unavailable. {data_service.event_api_error}")
else:
    st.metric("Published events", len(events))
    if events.empty:
        st.info("No published events were returned. Conditions may still be unknown.")

st.markdown("For emergency guidance, follow the relevant official authorities.")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information")
