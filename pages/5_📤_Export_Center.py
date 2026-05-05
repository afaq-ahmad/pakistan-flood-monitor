import streamlit as st
from backend_service import data_service

st.set_page_config(page_title="Export Center", page_icon="📤", layout="wide")
st.title("📤 Export Center")
st.markdown("Generate validated GIS exports — GeoJSON, COG, GeoParquet — with manifests and QGIS guidance.")

events = data_service.get_events()
if events.empty:
    st.info("No events to export.")
    st.stop()

c1, c2 = st.columns(2)
selected = c1.selectbox("Select Event", events["event_id"].tolist())
fmt = c2.selectbox("Export Format", ["geojson", "cog", "geoparquet"])

st.markdown("""
| Format | Extension | Description |
|--------|-----------|-------------|
| GeoJSON | `.geojson` | FeatureCollection vector — universal GIS compatibility |
| COG | `.tif` | Cloud Optimized GeoTIFF — tiled raster with overviews |
| GeoParquet | `.parquet` | Columnar geospatial — fast analytics with CRS metadata |
""")

if st.button("🚀 Generate Export", type="primary"):
    with st.spinner("Generating export..."):
        result = data_service.generate_export(selected, fmt)
    if "error" in result:
        st.error(result["error"])
    else:
        st.success(f"Export generated: `{result['export_id']}`")
        st.json(result)

# QGIS Integration Guide
st.subheader("🗺️ QGIS Integration Guide")
with st.expander("GeoJSON Import"):
    st.markdown("1. Open QGIS → Layer → Add Layer → Add Vector Layer\n2. Source: File → Browse to `.geojson`\n3. Click Add\n4. Verify CRS is EPSG:4326")
with st.expander("COG Import"):
    st.markdown("1. Layer → Add Layer → Add Raster Layer\n2. Browse to `.tif`\n3. Check Layer Properties → CRS and overviews")
with st.expander("GeoParquet Import"):
    st.markdown("1. Requires QGIS with GDAL Parquet support\n2. Layer → Add Layer → Add Vector Layer → `.parquet`\n3. Validate feature count matches GeoJSON")
with st.expander("Manifest-Assisted QA"):
    st.markdown("""
    Use `manifest.json` alongside imported layers:
    - `export_id`: tie map products to exact export run
    - `generated_at`: timestamp for reproducibility
    - `lineage.source_endpoint`: confirms event geometry source
    - `lineage.processing_version`: confirms processing version
    """)
