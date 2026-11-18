"""Configuration guidance for operators."""

import streamlit as st

st.set_page_config(page_title="Settings", page_icon="🔑", layout="centered")
st.title("Settings")
st.info("Web settings are unavailable. Configuration is managed on the server by authorized operators.")
st.write(
    "Use the server environment for credentials and deployment settings. "
    "Manage detection thresholds and breach weights through the project's configuration files."
)
