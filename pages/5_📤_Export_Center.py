from pathlib import Path

import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Export Center", page_icon="📤", layout="wide")
st.title("📤 Export Center")

data_service = DataService()
if not data_service.is_demo_mode:
    st.info("GIS export is unavailable for API-backed or operational events.")
    st.stop()

st.warning(DEMO_WATERMARK)
st.write("Download a demo event location as a GeoJSON point and its provenance manifest.")

events = data_service.get_events()
if events.empty:
    st.info("No demo events are available to export.")
    st.stop()

selected = st.selectbox("Select demo event", events["event_id"].tolist())
if st.button("Generate demo export", type="primary"):
    st.session_state["demo_export"] = (selected, data_service.generate_export(selected, "geojson"))

selected_export = st.session_state.get("demo_export")
if selected_export and selected_export[0] == selected:
    result = selected_export[1]
    if "error" in result:
        st.error(result["error"])
    else:
        try:
            geojson = Path(result["output_path"]).read_bytes()
            manifest = Path(result["manifest_path"]).read_bytes()
        except OSError:
            st.error("Demo export is unavailable. Generate it again to retry.")
        else:
            st.download_button("Download GeoJSON", geojson, file_name="demo-event.geojson",
                               mime="application/geo+json")
            st.download_button("Download manifest", manifest, file_name="manifest.json",
                               mime="application/json")
