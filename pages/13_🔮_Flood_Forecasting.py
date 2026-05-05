import streamlit as st
import pandas as pd
import sys
import os
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pakistan_flood_monitor.services.forecast_service import fetch_weather_forecast, predict_future_water_level
from satellite_ml_service import CORRIDOR_BBOXES

st.set_page_config(page_title="Flood Forecasting", page_icon="🔮", layout="wide")
st.title("🔮 Predictive Flood Forecasting")
st.markdown("Transitioning from reactive monitoring to **predictive early warnings**. This module leverages the Open-Meteo API (GFS) for 14-day precipitation forecasts and an LSTM Spatio-Temporal Neural Network to predict river water level trajectories.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Forecast Parameters")
    selected_corridor = st.selectbox("Select River Corridor", list(CORRIDOR_BBOXES.keys()))
    
    # Get center coords for the corridor
    bbox = CORRIDOR_BBOXES[selected_corridor]
    lat = (bbox[1] + bbox[3]) / 2.0
    lon = (bbox[0] + bbox[2]) / 2.0
    
    st.write(f"**Target Coordinates:** {lat:.2f}, {lon:.2f}")
    
    if st.button("Generate 14-Day Forecast", type="primary"):
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
        fig1 = px.bar(forecast_df, x='date', y='precipitation_mm', 
                     labels={'precipitation_mm': 'Rainfall (mm)', 'date': 'Date'},
                     title=f"Forecasted Rainfall - {selected_corridor}")
        fig1.update_traces(marker_color='#2196F3')
        st.plotly_chart(fig1, use_container_width=True)
        
        st.subheader("LSTM Predicted Water Level Trajectory")
        pred_df = pd.DataFrame(preds)
        
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
        
        # Alerts
        critical_days = pred_df[pred_df['risk_status'] == 'CRITICAL']
        if not critical_days.empty:
            st.error(f"🚨 **EARLY WARNING ALERT:** The LSTM model predicts critical flood levels on {critical_days.iloc[0]['date']}. Prepare evacuation notices for {selected_corridor}.")
        elif not pred_df[pred_df['risk_status'] == 'WARNING'].empty:
            st.warning(f"⚠️ **WATCH:** Water levels are predicted to rise to warning thresholds. Monitor the situation closely.")
        else:
            st.success("✅ Water levels are predicted to remain stable over the next 14 days.")
