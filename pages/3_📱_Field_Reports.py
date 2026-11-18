from datetime import datetime, timezone

import streamlit as st
import pandas as pd
from backend_service import DEMO_WATERMARK, data_service
from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.models.report_categories import CATEGORY_REGISTRY

st.set_page_config(page_title="Field Reports", page_icon="📱", layout="wide")
st.title("📱 Field Reports Moderation")
if not data_service.is_demo_mode:
    st.info("Field report moderation is unavailable in this mode. Resident report submission is unavailable here.")
    st.stop()

st.warning(DEMO_WATERMARK)
st.caption("Review decisions apply to demo reports. Reports require independent corroboration to support observations.")

def save_moderation(report_id: str, status: str) -> None:
    reason = st.session_state.get(f"mod_reason_{report_id}", "")
    st.session_state["field_report_save_result"] = data_service.moderate_report(report_id, status, reason)


result = st.session_state.pop("field_report_save_result", None)
if result is True:
    st.success("Demo report updated.")
elif result is False:
    st.error("The demo report could not be saved. Check its current status and try again.")

with st.expander("Practice a community report (demo)"):
    st.write(
        "Try a fictional example using a category, pilot corridor and date. "
        "Real report submission is unavailable here. This preview stays outside the moderation queue."
    )
    corridors = [corridor.name for corridor in settings.pilot_corridors]
    if not corridors:
        st.info("No pilot corridors are configured. The practice preview is unavailable.")
    else:
        categories = {f"{item.icon} {item.label_en}": item for item in CATEGORY_REGISTRY}
        category = st.selectbox("Report category", list(categories), key="sub_cat")
        st.caption(categories[category].description_en)
        if categories[category].sensitive_location:
            st.caption("Use only the general corridor for this example. Keep farm and household locations private.")
        corridor = st.selectbox("Pilot corridor", corridors, key="sub_corridor")
        today = datetime.now(timezone.utc).date()
        observed = st.date_input("Example observation date", value=today, max_value=today, key="sub_date")
        acknowledged = st.checkbox("I understand this is a practice example.", key="sub_consent")
        if st.button("Preview example", key="sub_submit_btn"):
            if not acknowledged:
                st.error("Confirm that this is a practice example to see the preview.")
            elif observed is None:
                st.error("Choose a date for the practice example.")
            else:
                st.info(f"Practice preview · {category} · {corridor} · {observed.isoformat()}. Nothing was submitted.")

reports = data_service.get_field_reports()
if reports.empty:
    st.info("Demo field reports are unavailable.")
    st.stop()

# Summary stats
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Reports", len(reports))
c2.metric("Approved", len(reports[reports["status"] == "approved"]))
c3.metric("Pending", len(reports[reports["status"].isin(["submitted","needs_more_info"])]))
c4.metric("Spam Flagged", len(reports[reports["status"] == "flagged_spam"]))

# Filter
filt = st.selectbox("Filter by status", ["All","submitted","approved","needs_more_info","rejected","flagged_spam"])
filtered = reports if filt == "All" else reports[reports["status"] == filt]

for _, rep in filtered.iterrows():
    rid = rep["report_id"]
    status_icon = {"submitted":"🟡","approved":"🟢","needs_more_info":"🔵","rejected":"🔴","flagged_spam":"⛔"}.get(rep["status"],"⚪")

    with st.expander(f"{status_icon} **{rid}** — Event: {rep['event_id']} | {rep['reporter_channel']} | Status: {rep['status']}"):
        lc, rc = st.columns(2)
        with lc:
            st.write(f"**Reported observation time:** {rep.get('observed_at','')}")
            st.write(f"**Location:** ({rep.get('latitude','')}, {rep.get('longitude','')})")
            st.write(f"**Channel:** {rep.get('reporter_channel','')}")
            st.write(f"**Notes:** {rep.get('notes','')}")
            if pd.notna(rep.get("evidence_urls")) and rep["evidence_urls"]:
                st.write(f"**Evidence:** {rep['evidence_urls']}")
            st.write(f"**Demo trust flag:** {'✅ Yes' if rep.get('trusted') else '❌ No'}")
            if pd.notna(rep.get("moderation_reason")) and rep["moderation_reason"]:
                st.write(f"**Moderation Reason:** {rep['moderation_reason']}")

        with rc:
            if rep["status"] in ["submitted", "needs_more_info"]:
                st.markdown("**Moderation Actions:**")
                st.text_input("Reason", key=f"mod_reason_{rid}")
                mc1, mc2, mc3 = st.columns(3)
                mc1.button("Approve", key=f"mod_approve_{rid}", on_click=save_moderation, args=(rid, "approved"))
                mc2.button("Reject", key=f"mod_reject_{rid}", on_click=save_moderation, args=(rid, "rejected"))
                mc3.button("Flag spam", key=f"mod_spam_{rid}", on_click=save_moderation, args=(rid, "flagged_spam"))

st.caption("⚠️ Reports can be malicious, spoofed, stale, or inaccurate. Moderation and cross-signal corroboration are required before any report is treated as trusted.")
