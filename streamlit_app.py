import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Pakistan Flood Monitor", page_icon="🌊", layout="centered")

st.sidebar.title("Pakistan Flood Monitor")

st.title("Pakistan Flood Monitor")
st.write(
    "Check published flood information for monitored river corridors in Pakistan "
    "and find preparedness guidance for farms and livestock."
)
st.caption("Local conditions may still be unknown. For emergency guidance, follow official authorities.")

st.header("Flood information and preparedness")

st.page_link("pages/1_🌍_Public_Dashboard.py", label="My Area")
st.write("Choose a monitored river corridor and see whether flood information is published for it.")

st.page_link("pages/16_📚_Official_Information.py", label="Official Information")
st.write("Find agencies that publish flood bulletins and emergency guidance.")

st.page_link("pages/17_🌾_Farmer_Preparedness.py", label="Farmer Safety")
st.write("Prepare for flooding and find recovery guidance for crops, stored grain, equipment and farm records.")

st.page_link("pages/18_🐄_Livestock_Preparedness.py", label="Livestock Safety")
st.write("Find guidance on animal care, fodder, water and veterinary resources.")

st.page_link("pages/3_📱_Field_Reports.py", label="Community Reporting")
st.write("Practice with a fictional example in demo mode. Real report submission is unavailable.")

st.header("Published events")
data_service = DataService()
if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)

with st.spinner("Checking published events…"):
    events = data_service.get_public_events()

if data_service.event_api_error:
    st.error(f"Event information is unavailable. {data_service.event_api_error}")
elif events.empty:
    st.info("No published events were returned. Conditions may still be unknown.")
else:
    st.write(f"Events in this feed: {len(events)}.")
