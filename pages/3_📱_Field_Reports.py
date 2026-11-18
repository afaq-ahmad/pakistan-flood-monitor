import hashlib
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
from backend_service import DEMO_WATERMARK, data_service
from pakistan_flood_monitor.config import settings
from pakistan_flood_monitor.models.report_categories import CATEGORY_REGISTRY

st.set_page_config(page_title="Field Reports", page_icon="📱", layout="wide")
st.title("📱 Field Reports Moderation")
if not data_service.is_demo_mode:
    st.info("Field report moderation is unavailable in this mode.")
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

reports = data_service.get_field_reports()
if reports.empty:
    st.info("Demo field reports are unavailable.")
    st.stop()

with st.expander("🌾 Community & Agricultural Report Submission (Demo Intake)"):
    st.markdown(
        "Residents and community observers can report flood impacts on agricultural assets, "
        "livestock, roads, and drinking water. Submissions require explicit consent and undergo moderation."
    )
    cat_options = {f"{m.icon} {m.label_en}": m for m in CATEGORY_REGISTRY}
    selected_label = st.selectbox("Report Category", list(cat_options.keys()), key="sub_cat")
    selected_meta = cat_options[selected_label]
    st.caption(selected_meta.description_en)

    if selected_meta.sensitive_location:
        st.info(
            "🔒 **Location Privacy:** This category covers private farm or household assets. "
            "Exact coordinates are minimized and not exposed publicly; reports are coarsened to corridor or district level."
        )

    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        corridor_choices = [c.name for c in settings.pilot_corridors] if settings.pilot_corridors else ["Indus-Lower", "Chenab-Middle"]
        sub_corridor = st.selectbox("Corridor / General Area", corridor_choices, key="sub_corridor")
    with sub_col2:
        sub_obs_date = st.date_input("Observed Date", value=datetime.now(timezone.utc).date(), key="sub_date")

    sub_notes = st.text_area(
        "Observed Conditions / Description",
        key="sub_notes",
        placeholder="Describe observed water depth, crop damage, road blockages, or animal needs. Do not include personal identification or phone numbers.",
    )

    sub_consent = st.checkbox(
        "I consent to submitting this observation for community flood monitoring. "
        "I understand this is a self-reported observation that requires moderation and cross-signal "
        "corroboration. It does NOT constitute an official emergency call or compensation claim.",
        key="sub_consent",
    )

    if st.button("Submit Report (Demo)", key="sub_submit_btn"):
        if not sub_consent:
            st.error("Consent is required to submit a community report.")
        elif not sub_notes.strip():
            st.error("Please provide a description of the observed conditions.")
        else:
            receipt_seed = f"{sub_corridor}:{sub_obs_date}:{sub_notes.strip()}"
            receipt_id = f"REC-{hashlib.sha256(receipt_seed.encode('utf-8')).hexdigest()[:8].upper()}"
            st.success(f"✅ Report received. Your submission receipt ID is **{receipt_id}**.")
            st.info(
                f"Status: **Submitted / Pending Moderation** · Category: **{selected_meta.label_en}** · "
                f"Area: **{sub_corridor}**. Reports require independent cross-signal corroboration before any research use."
            )

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
