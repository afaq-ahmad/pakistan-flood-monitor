"""Presentation shared by the public Home and My Area pages."""

import streamlit as st

from backend_service import DEMO_WATERMARK, DataService


def show_official_information_link() -> None:
    st.page_link("pages/16_📚_Official_Information.py", label="View official flood information")


def show_demo_notice(service: DataService) -> None:
    if service.is_demo_mode:
        st.warning(DEMO_WATERMARK)


def show_event_feed_status(service: DataService, *, empty: bool, corridor: str | None = None) -> None:
    if service.event_api_error:
        if service.has_api:
            st.error("Flood information is unavailable. The publication service did not return usable information.")
        else:
            st.error("Flood information source is unavailable. This site has no connected publication source.")
        return

    if empty:
        message = (
            f"No published events are linked to {corridor} in this feed."
            if corridor else "No published events in this feed."
        )
        st.info(f"{message} Local conditions may still be unknown.")

    if service.is_demo_mode:
        freshness = service.freshness_status()
        if freshness["status"] == "stale":
            st.warning(f"Demo processing is stale. {freshness['message']}.")
        else:
            st.caption(f"Demo processing status · {freshness['message']}")
    elif not empty:
        st.caption("The update time for this feed is unavailable. Individual events may show publication dates.")
