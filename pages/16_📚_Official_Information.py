"""Static links to official sources, not an automatic warning feed."""
import streamlit as st

from official_sources import OFFICIAL_SOURCES, SOURCE_REVIEWED_ON

st.set_page_config(page_title="Official flood information", page_icon="📚", layout="wide")
st.title("Official flood information")
st.warning(
    "This page links to official sources; it does not monitor them or tell you whether a warning is active. "
    "Open the source and check its issue date, area and latest instructions. "
    "An empty dashboard does not mean an area is safe."
)
st.caption(f"Links reviewed on {SOURCE_REVIEWED_ON}. Links may change or be unavailable.")
for source in OFFICIAL_SOURCES:
    st.subheader(source["name"])
    st.write(source["purpose"])
    st.caption(source["coverage"])
    st.markdown(f"[Visit the official source]({source['url']})")
st.info("For immediate assistance, contact the relevant local emergency authorities directly using their verified contact information.")
