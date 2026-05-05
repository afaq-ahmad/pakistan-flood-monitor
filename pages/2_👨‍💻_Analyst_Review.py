import streamlit as st
import pandas as pd
from backend_service import data_service

st.set_page_config(page_title="Analyst Review", page_icon="👨‍💻", layout="wide")
st.title("👨‍💻 Analyst Review Queue")
st.markdown("Validate machine detections, review evidence, and manage lifecycle transitions.")

# Filters
st.subheader("🔎 Queue Filters")
fc1, fc2, fc3, fc4 = st.columns(4)
events = data_service.get_events()
corridors_list = ["All"] + sorted(events["corridor_id"].dropna().unique().tolist()) if not events.empty else ["All"]
statuses_list = ["All","draft","queued","review","active","approved"]
classes_list = ["All","flood","possible_breach"]
bands = ["All","low","medium","high"]

f_corridor = fc1.selectbox("Corridor", corridors_list, key="rq_corr")
f_status = fc2.selectbox("Status", statuses_list, key="rq_stat")
f_class = fc3.selectbox("Event Class", classes_list, key="rq_cls")
f_band = fc4.selectbox("Confidence Band", bands, key="rq_band")

queue = data_service.get_review_queue()
if f_corridor != "All" and not queue.empty:
    queue = queue[queue["corridor_id"] == f_corridor]
if f_status != "All" and not queue.empty:
    queue = queue[queue["status"] == f_status]
if f_class != "All" and not queue.empty:
    queue = queue[queue["event_class"] == f_class]
if f_band != "All" and not queue.empty:
    queue = queue[queue["confidence_band"] == f_band]

st.markdown(f"**Queue size:** {len(queue)} candidates")

# Queue table
if queue.empty:
    st.info("No candidates match the current filters.")
else:
    for idx, row in queue.iterrows():
        eid = row["event_id"]
        conf = row.get("confidence", 0)
        breach = row.get("breach_suspicion", 0)
        status = row.get("status", "")

        # QA flags
        qa_flags = []
        if conf < 0.65: qa_flags.append("⚠️ low_confidence")
        if breach >= 0.7: qa_flags.append("🔴 high_breach_suspicion")
        if pd.isna(row.get("source_scenes")): qa_flags.append("❌ missing_imagery")
        if status == "review": qa_flags.append("📝 needs_revision")

        # Priority reasons
        reasons = []
        if breach >= 0.7: reasons.append("Possible breach suspicion: high")
        pop = row.get("population_exposed", 0)
        if pop > 10000: reasons.append(f"Population exposure: {pop:,}")
        if conf < 0.65: reasons.append("Confidence: low — needs verification")

        with st.expander(f"{'🔴' if breach>=0.7 else '🟠' if conf<0.7 else '🟢'} **{eid}** — {row.get('district','')} | {row.get('event_class','')} | Conf: {conf:.0%} | Status: {status}"):
            # Three-panel layout
            lc, mc, rc = st.columns([1, 1, 1])

            with lc:
                st.markdown("#### 📋 Event Details")
                st.write(f"**Corridor:** {row.get('corridor_id','')}")
                st.write(f"**District/Tehsil:** {row.get('district','')}/{row.get('tehsil','')}")
                st.write(f"**Detected:** {row.get('detected_at','')}")
                st.write(f"**Severity:** {row.get('severity','')}")
                st.write(f"**Affected Area:** {row.get('affected_area_sqkm',0)} sq km")
                st.write(f"**Source Scenes:** {row.get('source_scenes','N/A')}")
                if qa_flags:
                    st.markdown("**QA Flags:** " + " | ".join(qa_flags))
                if reasons:
                    st.markdown("**Priority Reasons:**")
                    for r in reasons: st.write(f"  - {r}")

            with mc:
                st.markdown("#### 📊 Evidence Scorecard")
                sar_strength = "Strong" if conf >= 0.7 else "Moderate" if conf >= 0.5 else "Weak"
                st.write(f"**SAR Anomaly:** {sar_strength}")
                st.write(f"**Optical Support:** {'Available' if pd.notna(row.get('source_scenes')) else 'Missing'}")
                hydro = "Supports" if conf > 0.6 else "Neutral"
                st.write(f"**Hydromet Context:** {hydro}")
                st.write(f"**Breach Suspicion:** {breach:.0%}")
                exp_sig = "High" if pop > 20000 else "Medium" if pop > 5000 else "Low"
                st.write(f"**Exposure Significance:** {exp_sig}")

                st.markdown("#### 🔍 Confidence Breakdown")
                st.write(f"**Machine Confidence:** {conf:.0%}")
                st.write(f"**Confidence Band:** {row.get('confidence_band','')}")
                st.progress(min(conf, 1.0))

                # Field report fusion
                fr_summary = data_service.field_report_summary(eid)
                if fr_summary["total"] > 0:
                    st.markdown("#### 📱 Field Report Fusion")
                    st.write(f"Trusted reports: {fr_summary['trusted']}")
                    st.write(f"Unmoderated: {fr_summary['unmoderated']}")
                    st.write(f"Conflicting: {fr_summary['conflicting']}")

            with rc:
                st.markdown("#### ✅ Review Checklist")
                st.checkbox("Candidate geometry inspected", value=True, key=f"chk1_{eid}")
                st.checkbox("Confidence available", value=True, key=f"chk2_{eid}")
                st.checkbox("Exposure summary checked", value=pop > 0, key=f"chk3_{eid}")
                st.checkbox("Public limitations present", value=True, key=f"chk4_{eid}")
                st.checkbox("Public copy previewed", key=f"chk5_{eid}")
                st.checkbox("Urdu copy present", value=pd.notna(row.get("what_this_means_ur")), key=f"chk6_{eid}")
                st.checkbox("Notes added", key=f"chk7_{eid}")

                st.markdown("#### ⚡ Actions")
                analyst = st.text_input("Analyst ID", value="analyst-local", key=f"analyst_{eid}")
                notes = st.text_area("Notes", key=f"notes_{eid}", height=68)

                ac1, ac2, ac3 = st.columns(3)
                if ac1.button("✅ Approve", key=f"approve_{eid}", type="primary"):
                    data_service.update_event_status(eid, "approved", analyst, notes)
                    st.success(f"Event {eid} approved!")
                    st.rerun()
                if ac2.button("📢 Publish", key=f"publish_{eid}"):
                    data_service.update_event_status(eid, "published", analyst, notes)
                    st.success(f"Event {eid} published! Public alerts updated.")
                    st.rerun()
                if ac3.button("❌ Reject", key=f"reject_{eid}"):
                    data_service.update_event_status(eid, "rejected", analyst, notes)
                    st.warning(f"Event {eid} rejected.")
                    st.rerun()

# Audit Timeline
st.subheader("📜 Audit Timeline")
audit = data_service.get_audit_log()
if not audit.empty:
    st.dataframe(audit.sort_values("timestamp", ascending=False), width="stretch", hide_index=True)
else:
    st.info("No audit records yet.")
