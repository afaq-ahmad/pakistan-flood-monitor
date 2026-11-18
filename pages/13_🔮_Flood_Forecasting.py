import streamlit as st
import pandas as pd
import sys
import os
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.pakistan_flood_monitor.services.forecast_service import fetch_weather_forecast, predict_future_water_level
    HAS_FORECAST_SERVICE = True
except ImportError as e:
    HAS_FORECAST_SERVICE = False
    FORECAST_IMPORT_ERROR = str(e)

from backend_service import DEMO_WATERMARK, DataService
from satellite_ml_service import CORRIDOR_BBOXES

st.set_page_config(page_title="Flood Forecasting", page_icon="🔮", layout="wide")
st.title("🔮 Predictive Flood Forecasting")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information and bulletins")

data_service = DataService()
if not data_service.is_demo_mode:
    st.error(
        "Predictive flood forecasting is unavailable in operational mode pending "
        "independent model validation, historical hindcasting, and official authorization."
    )
    st.caption(
        "Per ADR-001 and PK-011, unvalidated machine learning models must not generate "
        "operational flood warnings or evacuation directives. Consult official FFD/NDMA sources."
    )
    st.stop()

st.warning(DEMO_WATERMARK)
st.caption(
    "SIMULATED / RESEARCH PROTOTYPE — This module demonstrates an experimental "
    "14-day precipitation forecast and LSTM water level model for research purposes only. "
    "Model weights are uncalibrated. Never use these outputs for evacuation or operational decisions."
)

if not HAS_FORECAST_SERVICE:
    st.warning(f"⚠️ **Optional ML dependencies not found** (`{FORECAST_IMPORT_ERROR}`).\n\nTo enable full predictive LSTM forecasting, install optional packages: `pip install openmeteo-requests requests_cache retry_requests torch`.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Forecast Parameters")
    selected_corridor = st.selectbox("Select River Corridor", list(CORRIDOR_BBOXES.keys()))

    # Get center coords for the corridor
    bbox = CORRIDOR_BBOXES[selected_corridor]
    lat = (bbox[1] + bbox[3]) / 2.0
    lon = (bbox[0] + bbox[2]) / 2.0

    st.write(f"**Target Coordinates:** {lat:.2f}, {lon:.2f}")

    if st.button("Generate 14-Day Forecast", type="primary", disabled=not HAS_FORECAST_SERVICE):
        with st.spinner("Fetching GFS meteorological forecast..."):
            forecast_df = fetch_weather_forecast(lat, lon, 14)
            st.session_state['forecast_df'] = forecast_df

        if not forecast_df.empty:
            with st.spinner("Running LSTM predictive model..."):
                predictions = predict_future_water_level(forecast_df)
                st.session_state['lstm_preds'] = predictions
                st.success("Prediction complete!")

with col2:
    if 'forecast_df' in st.session_state and not st.session_state['forecast_df'].empty:
        forecast_df = st.session_state['forecast_df']
        preds = st.session_state['lstm_preds']

        st.subheader("14-Day Precipitation Forecast (GFS)")
        if HAS_PLOTLY:
            fig1 = px.bar(forecast_df, x='date', y='precipitation_mm',
                         labels={'precipitation_mm': 'Rainfall (mm)', 'date': 'Date'},
                         title=f"Forecasted Rainfall - {selected_corridor}")
            fig1.update_traces(marker_color='#2196F3')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.bar_chart(forecast_df.set_index("date")["precipitation_mm"])

        st.subheader("LSTM Predicted Water Level Trajectory")
        pred_df = pd.DataFrame(preds)

        if HAS_PLOTLY:
            # Color code based on risk status
            color_map = {'NORMAL': 'green', 'WARNING': 'orange', 'CRITICAL': 'red'}
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=pred_df['date'], y=pred_df['predicted_water_level_m'],
                                     mode='lines+markers', name='Predicted Level',
                                     line=dict(color='blue', width=3),
                                     marker=dict(size=8, color=[color_map[status] for status in pred_df['risk_status']])))

            # Add threshold lines
            fig2.add_hline(y=5.0, line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
            fig2.add_hline(y=8.0, line_dash="dash", line_color="red", annotation_text="Critical / Flood Breach Threshold")

            fig2.update_layout(title="Predicted River Water Level (LSTM Output)",
                              xaxis_title="Date", yaxis_title="Water Level (meters)",
                              yaxis=dict(range=[0, 10]))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.line_chart(pred_df.set_index("date")["predicted_water_level_m"])

        # Simulated risk indications — NEVER issue evacuation notices
        critical_days = pred_df[pred_df['risk_status'] == 'CRITICAL']
        if not critical_days.empty:
            st.error(
                f"⚠️ **SIMULATED THRESHOLD EXCEEDANCE:** Experimental model indicates potential threshold "
                f"exceedance on {critical_days.iloc[0]['date']} for {selected_corridor}. This is research "
                f"prototype output; consult official NDMA/PDMA bulletins for official warnings and evacuation instructions."
            )
        elif not pred_df[pred_df['risk_status'] == 'WARNING'].empty:
            st.warning(
                f"⚠️ **SIMULATED WATCH:** Experimental model indicates water levels approaching warning "
                f"thresholds for {selected_corridor}. Consult official sources."
            )
        else:
            st.info(f"ℹ️ Simulated water levels remain within normal thresholds for {selected_corridor}.")
    else:
        st.info("ℹ️ Select a river corridor on the left and click **Generate 14-Day Forecast** to fetch meteorological data and predict water levels.")

with st.expander("⚠️ Limitations & Scientific Assumptions"):
    st.markdown("""
    - **Experimental Model:** The LSTM model is an unvalidated research prototype with synthetic/initial weights.
    - **No Operational Authority:** Machine scores do not constitute official flood warnings, emergency alerts, or evacuation directives.
    - **Meteorological Uncertainties:** 14-day precipitation forecasts from GFS contain increasing uncertainty beyond 3-5 days.
    - **Hydrological Assumptions:** Soil moisture, upstream dam releases, and terrain friction are simplified or proxied.
    - **Official Bulletins:** Always follow flood warnings and advisories issued by the **Flood Forecasting Division (FFD/PMD)** and **NDMA/PDMA**.
    """)
