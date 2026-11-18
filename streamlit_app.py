import streamlit as st

from backend_service import DataService
from public_information import show_demo_notice, show_event_feed_status, show_official_information_link


def render_home() -> None:
    st.set_page_config(page_title="Pakistan Flood Monitor", page_icon="🌊", layout="centered")

    st.title("Pakistan Flood Monitor")
    st.write("Find published flood information for monitored river corridors in Pakistan and prepare for flooding.")

    st.header("Available flood information")
    data_service = DataService()
    show_demo_notice(data_service)
    availability = st.container()

    st.header("Check information for my area")
    st.page_link("pages/1_🌍_Public_Dashboard.py", label="Open My Area")
    st.write("Choose a monitored river corridor to see the flood information published for it.")

    st.header("Prepare for flooding")
    st.page_link("pages/17_🌾_Farmer_Preparedness.py", label="Prepare my farm")
    st.write("Find guidance for crops, stored grain, equipment and farm records.")
    st.page_link("pages/18_🐄_Livestock_Preparedness.py", label="Prepare my livestock")
    st.write("Find guidance on animal care, fodder, water and veterinary resources.")

    st.header("Official information")
    show_official_information_link()
    st.write("Follow official agencies and local authorities for flood bulletins and emergency instructions.")

    st.header("Coverage and limits")
    st.write(
        "The site covers selected river corridors. Information for individual villages, farms and "
        "properties is unverified. Local conditions may be unknown even when the feed has no events."
    )

    st.page_link("pages/3_📱_Field_Reports.py", label="Community Reporting")
    st.write("Practice with a fictional example in demo mode. Real report submission is unavailable.")

    # Keep links usable while the publication service responds.
    with availability:
        with st.spinner("Checking published flood information…"):
            events = data_service.get_public_events()
        show_event_feed_status(data_service, empty=events.empty)
        if not data_service.event_api_error and not events.empty:
            st.write(f"Published events in this feed: {len(events)}.")


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
