import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

def render_home() -> None:
    st.set_page_config(page_title="Pakistan Flood Monitor", page_icon="🌊", layout="centered")

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


st.navigation(
    {
        "": [st.Page(render_home, title="Home", default=True)],
        "Public information": [
            st.Page("pages/1_🌍_Public_Dashboard.py", title="My Area"),
            st.Page("pages/17_🌾_Farmer_Preparedness.py", title="Prepare my farm"),
            st.Page("pages/18_🐄_Livestock_Preparedness.py", title="Prepare my livestock"),
            st.Page("pages/16_📚_Official_Information.py", title="Official flood information"),
            st.Page("pages/3_📱_Field_Reports.py", title="Community Reporting"),
        ],
        "Research": [
            "pages/9_🛰️_Satellite_Viewer.py",
            "pages/10_🌧️_NASA_Hydromet.py",
            "pages/11_🤖_ML_Water_Detection.py",
            "pages/12_🗺️_Historical_Flood_Map.py",
            "pages/13_🔮_Flood_Forecasting.py",
            "pages/14_🧠_Advanced_ML_SAR.py",
            "pages/15_🏗️_Dam_Flood_Risk.py",
        ],
        "Operations": [
            "pages/2_👨‍💻_Analyst_Review.py",
            "pages/4_🤝_Partner_Mode.py",
            "pages/5_📤_Export_Center.py",
            "pages/6_🧠_ML_Training.py",
            "pages/7_⚙️_Operations.py",
            "pages/8_🔑_Settings.py",
        ],
    },
    position="top",
).run()
