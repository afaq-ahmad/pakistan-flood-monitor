import streamlit as st
import json
import folium
from streamlit_folium import st_folium
from pathlib import Path
import pandas as pd

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Historical Flood Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Historical Flood Map (Past 20 Years)")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information and bulletins")

data_service = DataService()
if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)

st.markdown(
    "Explore approximate regions affected by major flood events in Pakistan over the last two decades. "
    "Data compiled from historical disaster reports (NDMA, OCHA, media reports) with approximate coordinates."
)
st.caption(
    "⚠️ Historical flood extents are approximate contextual reference data only. Past inundation does not predict "
    "future flood boundaries, and unhighlighted areas are not guaranteed safe. For current alerts, consult official sources."
)

@st.cache_data
def load_historical_data():
    data_path = Path("data/historical_flood_regions.json")
    if data_path.exists():
        with open(data_path, "r") as f:
            return json.load(f)
    return []

flood_data = load_historical_data()

if not flood_data:
    st.error("Historical flood dataset not found. Please run the generation script.")
    st.stop()

# Organize data for selection
event_options = {f"{event['year']} - {event['name']}": event for event in flood_data}

# Filters
col1, col2 = st.columns([1, 2])
with col1:
    selected_event_name = st.selectbox("Select Historical Flood Event", list(event_options.keys()))
    event = event_options[selected_event_name]
    
    st.subheader(f"Event Details: {event['name']}")
    st.write(f"**Year:** {event['year']}")
    st.write(f"**Total Affected Districts Logged:** {len(event['regions'])}")
    
    # Create a dataframe for the districts
    df_districts = pd.DataFrame(event['regions'])
    if not df_districts.empty:
        st.dataframe(df_districts[['name', 'lat', 'lon']], hide_index=True)

with col2:
    st.subheader("Affected Regions Map")
    
    # Base map centered on Pakistan
    m = folium.Map(location=[30.3753, 69.3451], zoom_start=5, tiles="CartoDB dark_matter")
    
    # Color coding
    colors = ['#ff4b4b', '#ff7f0e', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    color = colors[event['year'] % len(colors)]
    
    # Add regions to map
    for region in event['regions']:
        lat = region['lat']
        lon = region['lon']
        name = region['name']
        bbox = region.get('boundingbox')
        
        # Add a marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            popup=f"<b>{name}</b><br>Affected in {event['year']}",
            tooltip=name,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7
        ).add_to(m)
        
        # Add bounding box if available
        if bbox and len(bbox) == 4:
            try:
                # boundingbox format from Nominatim is usually [lat_min, lat_max, lon_min, lon_max]
                lat_min, lat_max, lon_min, lon_max = map(float, bbox)
                bounds = [[lat_min, lon_min], [lat_max, lon_max]]
                folium.Rectangle(
                    bounds=bounds,
                    color=color,
                    weight=2,
                    fill=True,
                    fillOpacity=0.1,
                    tooltip=f"{name} Boundary"
                ).add_to(m)
            except Exception as e:
                pass
                
    # Add a legend
    legend_html = f'''
     <div style="position: fixed; 
     bottom: 50px; right: 50px; width: 200px; height: 90px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:rgba(0, 0, 0, 0.7);
     color: white;
     padding: 10px;">
     &nbsp;<b>{event['year']} Affected Areas</b><br>
     &nbsp;<i class="fa fa-square fa-1x" style="color:{color}"></i> Highlighted District<br>
     &nbsp;<i class="fa fa-circle fa-1x" style="color:{color}"></i> District Center
      </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    st_folium(m, width=800, height=600)

st.markdown("---")
st.markdown("### Historical Context & Machine Learning")
st.info(
    "These approximate regions provide historical context and candidate bounding boxes for retrospective "
    "satellite imagery retrieval (`storage/satellite/historical_floods/`). They represent approximate "
    "disaster reporting extents and do not constitute ground-truth field boundaries or certified damage assessments."
)
