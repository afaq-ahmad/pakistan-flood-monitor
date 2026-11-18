"""Native text-first components for the public preparedness guides."""

import streamlit as st

from backend_service import DataService
from public_information import show_demo_notice, show_official_information_link

NDMA_FLOOD_GUIDE = "https://ndma.gov.pk/public/storage/guidelines/July2024/687CQaWTVMvbiFxuxk0f.pdf"


def begin_guide(title: str, icon: str, scope: str) -> bool:
    st.set_page_config(page_title=title, page_icon=icon, layout="centered")
    st.title(title)
    st.write(scope)
    show_official_information_link()
    show_demo_notice(DataService())
    return st.checkbox(
        "Show all details for printing",
        help="Show all sections, then use your browser's Print option.",
    )


def show_checklist(heading: str, items: tuple[str, ...]) -> None:
    st.header(heading)
    st.markdown("\n".join(f"- {item}" for item in items))


def show_detail(topic: str, body: str, *, show_all: bool) -> None:
    if show_all:
        st.subheader(topic)
        st.markdown(body)
    else:
        with st.expander(topic):
            st.markdown(body)
