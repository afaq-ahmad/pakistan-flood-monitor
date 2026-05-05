import streamlit as st
import yaml
from backend_service import data_service

st.set_page_config(page_title="Settings & API Keys", page_icon="🔑", layout="wide")
st.title("🔑 API Keys, Thresholds & System Configuration")
st.markdown("Configure credentials, detection thresholds, and breach weighting parameters.")

tab1, tab2, tab3, tab4 = st.tabs(["🔐 API Keys", "📏 Flood Thresholds", "⚖️ Breach Weights", "🌐 Environment"])

with tab1:
    st.subheader("External API Credentials")
    st.caption("Reference: `docs/notification_channels_runbook.md`, `.env.local`")
    st.text_input("STAC_TOKEN (Satellite Imagery)", type="password", value="sk-stac-xxxxx", key="stac")
    st.text_input("HYDROMET_TOKEN (Rainfall/Forecast)", type="password", value="sk-hydro-xxxxx", key="hydro")
    st.text_input("SMS_API_KEY", type="password", value="", key="sms")
    st.text_input("EMAIL_API_KEY", type="password", value="", key="email")
    st.text_input("WHATSAPP_API_KEY", type="password", value="", key="wa")
    st.markdown("---")
    st.subheader("Auth Tokens")
    st.text_input("FLOOD_MONITOR_ADMIN_TOKEN", type="password", value="admin-local-dev-token", key="admin_tok")
    st.text_input("FLOOD_MONITOR_ANALYST_TOKEN", type="password", value="analyst-local-dev-token", key="analyst_tok")
    if st.button("💾 Save API Keys"):
        st.success("API keys would be saved to `.env.local` in production.")

with tab2:
    st.subheader("Flood Detection Thresholds")
    st.caption("Source: `config/thresholds/flood_thresholds.yaml`")
    thresholds = data_service.get_flood_thresholds()
    st.json(thresholds)

    st.markdown("#### Edit Thresholds")
    corridor_thresholds = thresholds.get("corridor_thresholds", {})
    for corridor, vals in corridor_thresholds.items():
        st.markdown(f"**{corridor}**")
        c1, c2 = st.columns(2)
        vals["sar_drop_db"] = c1.number_input(f"SAR Drop dB ({corridor})", value=float(vals.get("sar_drop_db",2.5)), step=0.1, key=f"sar_{corridor}")
        vals["ndwi_min"] = c2.number_input(f"NDWI Min ({corridor})", value=float(vals.get("ndwi_min",0.2)), step=0.01, key=f"ndwi_{corridor}")

    review_thresh = thresholds.get("review_thresholds", {})
    st.markdown("**Review Thresholds**")
    c1, c2 = st.columns(2)
    review_thresh["analyst_review_min_confidence"] = c1.number_input("Min Confidence for Review", value=float(review_thresh.get("analyst_review_min_confidence",0.45)), step=0.05, key="rev_min")
    review_thresh["publish_min_confidence"] = c2.number_input("Min Confidence for Publish", value=float(review_thresh.get("publish_min_confidence",0.72)), step=0.05, key="pub_min")

    if st.button("💾 Save Flood Thresholds"):
        thresholds["corridor_thresholds"] = corridor_thresholds
        thresholds["review_thresholds"] = review_thresh
        data_service.save_flood_thresholds(thresholds)
        st.success("Flood thresholds saved to `config/thresholds/flood_thresholds.yaml`!")

with tab3:
    st.subheader("Breach Suspicion Weights")
    st.caption("Source: `config/thresholds/breach_weights.yaml`")
    bw = data_service.get_breach_weights()
    st.json(bw)

    weights = bw.get("breach_weights", {})
    st.markdown("#### Edit Weights (must sum to ~1.0)")
    for key, val in weights.items():
        weights[key] = st.slider(key.replace("_"," ").title(), 0.0, 0.5, float(val), 0.01, key=f"bw_{key}")

    total = sum(weights.values())
    st.write(f"**Total weight:** {total:.2f} {'✅' if abs(total-1.0)<0.05 else '⚠️ Should be ~1.0'}")

    bw_thresh = bw.get("review_thresholds", {})
    bw_thresh["breach_alert_min_score"] = st.number_input("Breach Alert Min Score", value=float(bw_thresh.get("breach_alert_min_score",0.68)), step=0.05, key="breach_min")

    if st.button("💾 Save Breach Weights"):
        bw["breach_weights"] = weights
        bw["review_thresholds"] = bw_thresh
        data_service.save_breach_weights(bw)
        st.success("Breach weights saved!")

with tab4:
    st.subheader("Environment Configuration")
    st.caption("Reference: `docs/local_setup_and_deployment.md`")
    st.text_input("DATABASE_DSN", value="postgresql+psycopg://postgres:postgres@localhost:5432/flood_monitor", key="dsn")
    st.text_input("STAC_ENDPOINT", value="https://earth-search.aws.element84.com/v1", key="stac_ep")
    st.text_input("HYDROMET_ENDPOINT", value="https://api.glofas.ecmwf.int/v1", key="hydro_ep")
    st.text_input("API_BASE_URL", value="http://localhost:8000", key="api_base")
    st.selectbox("APP_ENV", ["local","staging","prod"], key="app_env")
    st.selectbox("LOG_LEVEL", ["DEBUG","INFO","WARNING","ERROR"], index=1, key="log_level")
    st.text_input("DEFAULT_CRS", value="EPSG:4326", key="crs")
    st.number_input("CORRIDOR_BUFFER_METERS", value=5000, step=500, key="buffer")
    if st.button("💾 Save Environment Config"):
        st.success("Environment config saved. Restart required for changes to take effect.")
