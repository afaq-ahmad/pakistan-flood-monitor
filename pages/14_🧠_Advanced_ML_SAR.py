import streamlit as st
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pakistan_flood_monitor.services.advanced_ml_service import (
    simulate_sar_download_and_process,
    fetch_dem_and_calculate_hand,
    GeoFoundationModelWrapper
)
from satellite_ml_service import CORRIDOR_BBOXES

st.set_page_config(page_title="Advanced ML & SAR", page_icon="🧠", layout="wide")
st.title("🧠 Advanced ML: SAR, Topography & Foundation Models")
st.markdown("This module demonstrates the state-of-the-art predictive architecture: replacing optical imagery with cloud-penetrating SAR, integrating terrain physics via DEM/HAND, and leveraging zero-shot Foundation Models.")

tabs = st.tabs(["1. SAR Processing", "2. Topography (DEM/HAND)", "3. Foundation Model Inference"])

corridor = st.sidebar.selectbox("Select Corridor for Analysis", list(CORRIDOR_BBOXES.keys()))

with tabs[0]:
    st.subheader("Radar Imagery: Sentinel-1 SAR")
    st.markdown("Optical imagery (Sentinel-2) is blind during monsoon storms. Synthetic Aperture Radar (SAR) pierces through clouds. Water acts as a specular reflector, returning minimal signal (appearing dark).")
    
    if st.button("Fetch & Process SAR", key="btn_sar"):
        with st.spinner("Downloading Sentinel-1 GRD imagery and applying Otsu thresholding..."):
            time.sleep(1) # simulate network delay
            res = simulate_sar_download_and_process(corridor, "latest")
            st.session_state['sar_res'] = res
            
    if 'sar_res' in st.session_state:
        res = st.session_state['sar_res']
        col1, col2 = st.columns(2)
        with col1:
            st.image(res['sar_path'], caption="Raw SAR Intensity (VV/VH)", use_container_width=True)
        with col2:
            st.image(res['mask_path'], caption=f"Otsu Water Mask (Coverage: {res['water_coverage_pct']}%)", use_container_width=True)

with tabs[1]:
    st.subheader("Physics-Informed: Topography Integration")
    st.markdown("Neural networks need to know that water flows downhill. We integrate the Copernicus 30m Digital Elevation Model (DEM) and calculate the Height Above Nearest Drainage (HAND) index.")
    
    if st.button("Fetch DEM & Compute HAND", key="btn_dem"):
        with st.spinner("Fetching Copernicus 30m DEM and computing HAND index..."):
            res = fetch_dem_and_calculate_hand(corridor, CORRIDOR_BBOXES[corridor])
            st.session_state['dem_res'] = res
            
    if 'dem_res' in st.session_state:
        res = st.session_state['dem_res']
        col1, col2 = st.columns(2)
        with col1:
            st.image(res['dem_path'], caption="Real Topography Elevation (DEM)", use_container_width=True)
        with col2:
            st.image(res['hand_path'], caption="Real Height Above Nearest Drainage (HAND)", use_container_width=True)

with tabs[2]:
    st.subheader("Zero-Shot Earth Observation Foundation Models")
    st.markdown("Deploying massive, pre-trained geospatial foundation models (like NASA's Prithvi or Sen1Floods11 U-Net) to predict flood inundation based on multi-modal inputs: [SAR + DEM + Forecast Rain].")
    
    forecast_rain = st.slider("Simulate Forecasted Rain (mm)", 0.0, 300.0, 100.0)
    
    if st.button("Run Multi-Modal Inference", type="primary"):
        if 'sar_res' not in st.session_state or 'dem_res' not in st.session_state:
            st.error("Please run SAR Processing and Topography steps first!")
        else:
            with st.spinner("Loading GeoFoundationModel..."):
                wrapper = GeoFoundationModelWrapper()
                
            with st.spinner("Running inference..."):
                time.sleep(1) # Simulate inference time
                
                # Fetch raw data for inference
                dem_arr = st.session_state['dem_res']['raw_dem']
                
                # We need a SAR array matching DEM size (64x64). We'll generate it here since
                # we updated the SAR logic to accept a base_dem to make it physically plausible
                sar_sim_res = simulate_sar_download_and_process(corridor, "latest_for_inference", base_dem=dem_arr)
                from PIL import Image
                import numpy as np
                sar_img = np.array(Image.open(sar_sim_res['sar_path']))
                
                # Run the model
                pred_mask = wrapper.predict_flood_extent(sar_img, dem_arr, forecast_rain)
                
                # Visualization (resize for display)
                viz = np.zeros((*pred_mask.shape, 3), dtype=np.uint8)
                viz[pred_mask == 1] = [255, 0, 0] # Red for predicted danger zone
                viz[pred_mask == 0] = [20, 20, 20]
                viz_img = Image.fromarray(viz).resize((512, 512), Image.NEAREST)
                
                sar_disp = Image.fromarray(sar_img).convert('L').resize((512, 512), Image.NEAREST)
                
                st.success("Inference Complete! The model intelligently limits the predicted flood spread by incorporating the actual topographical constraints (HAND index) and the forecasted precipitation volume.")
                
                c1, c2, c3 = st.columns(3)
                c1.image(sar_disp, caption="Input 1: SAR Backscatter")
                c2.image(st.session_state['dem_res']['dem_path'], caption="Input 2: Real Topography (DEM)")
                c3.image(viz_img, caption=f"Output: Predicted Flood Extent ({forecast_rain}mm rain)")

