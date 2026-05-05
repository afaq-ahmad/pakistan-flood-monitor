import streamlit as st
import pandas as pd
from backend_service import data_service

st.set_page_config(page_title="Field Reports", page_icon="📱", layout="wide")
st.title("📱 Field Reports Moderation")
st.markdown("Verify ground observations. Unmoderated reports are never treated as truth.")

reports = data_service.get_field_reports()
if reports.empty:
    st.info("No field reports available.")
    st.stop()

# Summary stats
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Reports", len(reports))
c2.metric("Approved/Trusted", len(reports[reports["status"] == "approved"]))
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
            st.write(f"**Observed:** {rep.get('observed_at','')}")
            st.write(f"**Location:** ({rep.get('latitude','')}, {rep.get('longitude','')})")
            st.write(f"**Channel:** {rep.get('reporter_channel','')}")
            st.write(f"**Notes:** {rep.get('notes','')}")
            if pd.notna(rep.get("evidence_urls")) and rep["evidence_urls"]:
                st.write(f"**Evidence:** {rep['evidence_urls']}")
            st.write(f"**Trusted:** {'✅ Yes' if rep.get('trusted') else '❌ No'}")
            if pd.notna(rep.get("moderation_reason")) and rep["moderation_reason"]:
                st.write(f"**Moderation Reason:** {rep['moderation_reason']}")

        with rc:
            if rep["status"] in ["submitted", "needs_more_info"]:
                st.markdown("**Moderation Actions:**")
                reason = st.text_input("Reason", key=f"mod_reason_{rid}")
                mc1, mc2, mc3 = st.columns(3)
                if mc1.button("✅ Approve", key=f"mod_approve_{rid}"):
                    data_service.moderate_report(rid, "approved", reason)
                    st.success("Report approved and marked trusted.")
                    st.rerun()
                if mc2.button("❌ Reject", key=f"mod_reject_{rid}"):
                    data_service.moderate_report(rid, "rejected", reason)
                    st.rerun()
                if mc3.button("⛔ Flag Spam", key=f"mod_spam_{rid}"):
                    data_service.moderate_report(rid, "flagged_spam", reason)
                    st.rerun()

st.caption("⚠️ Reports can be malicious, spoofed, stale, or inaccurate. Moderation and cross-signal corroboration are required before any report is treated as trusted.")
