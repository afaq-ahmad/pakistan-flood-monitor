import streamlit as st
import pandas as pd
from backend_service import DEMO_WATERMARK, DataService, ReviewQueueUnavailable
from pakistan_flood_monitor.config import AppMode
from pakistan_flood_monitor.models.review_queue import REVIEW_QUEUE_PAGE_SIZE

st.set_page_config(page_title="Analyst Review", page_icon="👨‍💻", layout="wide")
st.title("👨‍💻 Analyst Review Queue")
data_service = DataService()


def set_queue_offset(offset: int) -> None:
    st.session_state["review_queue_offset"] = offset


def render_api_queue() -> None:
    st.caption(
        "Read-only candidate list from the current API process. Review transitions and audit "
        "history are available through the internal API."
    )
    token = st.text_input(
        "Review API token", type="password", key="review_queue_token",
        on_change=set_queue_offset, args=(0,),
    ).strip()
    if not token:
        st.info("Enter a review credential to load candidates.")
        return

    col_status, col_refresh = st.columns([3, 1])
    status = col_status.selectbox(
        "Lifecycle status", [None, "draft", "review", "approved"],
        format_func=lambda value: value or "All",
        key="api_review_status", on_change=set_queue_offset, args=(0,),
    )
    col_refresh.button("Refresh queue")
    offset = st.session_state.get("review_queue_offset", 0)
    try:
        with st.spinner("Loading analyst queue…"):
            queue = data_service.fetch_review_queue(token, offset=offset, status=status)
    except ReviewQueueUnavailable as error:
        st.error(str(error))
        return

    if queue.app_mode in (AppMode.DEMO, AppMode.TEST) or any(
        item.product_label == "SIMULATED" for item in queue.items
    ):
        st.warning(DEMO_WATERMARK)
    if not queue.items:
        st.info("No candidates match this page and filter in the current API process.")
    else:
        st.dataframe([
            {
                "Event": item.event_id,
                "Corridor": item.corridor_id or "Unavailable",
                "Class": item.event_class or "Unavailable",
                "Status": item.status,
                "Recorded detection (UTC)": item.detected_at.isoformat() if item.detected_at else "Unavailable",
                "Model confidence (%)": item.machine_confidence_pct,
                "Product label": item.product_label or "Unavailable",
            }
            for item in queue.items
        ], hide_index=True)

    previous, following = st.columns(2)
    previous.button(
        "Previous page", disabled=offset == 0, on_click=set_queue_offset,
        args=(max(0, offset - REVIEW_QUEUE_PAGE_SIZE),),
    )
    following.button(
        "Next page", disabled=queue.next_offset is None, on_click=set_queue_offset,
        args=(queue.next_offset or offset,),
    )


if data_service.has_api:
    render_api_queue()
    st.stop()
if not data_service.is_demo_mode:
    st.error("The analyst queue is unavailable. No API endpoint is configured.")
    st.stop()

st.warning(
    f"**{DEMO_WATERMARK}** — Review actions update local demo records."
)

# Filters
st.subheader("🔎 Queue Filters")
fc1, fc2, fc3, fc4 = st.columns(4)
queue = data_service.get_review_queue()
corridors_list = ["All"] + sorted(queue["corridor_id"].dropna().unique().tolist()) if not queue.empty else ["All"]
statuses_list = ["All","draft","queued","review","active","approved"]
classes_list = ["All","flood","possible_breach"]
bands = ["All","low","medium","high"]

f_corridor = fc1.selectbox("Corridor", corridors_list, key="rq_corr")
f_status = fc2.selectbox("Status", statuses_list, key="rq_stat")
f_class = fc3.selectbox("Event Class", classes_list, key="rq_cls")
f_band = fc4.selectbox("Confidence Band", bands, key="rq_band")

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
                st.markdown("#### Demo review checklist")
                st.checkbox("Candidate geometry inspected", key=f"chk1_{eid}")
                st.checkbox("Confidence available", key=f"chk2_{eid}")
                st.checkbox("Exposure summary checked", key=f"chk3_{eid}")
                st.checkbox("Public limitations present", key=f"chk4_{eid}")
                st.checkbox("Public copy previewed", key=f"chk5_{eid}")
                st.checkbox("Urdu copy present", key=f"chk6_{eid}")
                st.checkbox("Notes added", key=f"chk7_{eid}")

                st.markdown("#### ⚡ Actions")
                analyst = st.text_input("Analyst ID", value="analyst-local", key=f"analyst_{eid}")
                notes = st.text_area("Notes", key=f"notes_{eid}", height=68)

                ac1, ac2, ac3 = st.columns(3)
                if ac1.button("✅ Approve", key=f"approve_{eid}", type="primary"):
                    if data_service.update_event_status(eid, "approved", analyst, notes):
                        st.success(f"Event {eid} approved!")
                        st.rerun()
                    else:
                        st.error(f"Failed to approve event {eid}. Check backend service and permissions.")
                if ac2.button("📢 Publish", key=f"publish_{eid}"):
                    if data_service.update_event_status(eid, "published", analyst, notes):
                        st.success(f"Event {eid} published! Public alerts updated.")
                        st.rerun()
                    else:
                        st.error(f"Failed to publish event {eid}. Check backend service and permissions.")
                if ac3.button("❌ Reject", key=f"reject_{eid}"):
                    if data_service.update_event_status(eid, "rejected", analyst, notes):
                        st.warning(f"Event {eid} rejected.")
                        st.rerun()
                    else:
                        st.error(f"Failed to reject event {eid}. Check backend service and permissions.")

# Audit Timeline
st.subheader("📜 Demo Audit Timeline")
audit = data_service.get_audit_log()
if not audit.empty:
    st.dataframe(audit.sort_values("timestamp", ascending=False), width="stretch", hide_index=True)
else:
    st.info("No audit records yet.")
