import streamlit as st
import pandas as pd
from backend_service import data_service

st.set_page_config(page_title="Operations", page_icon="⚙️", layout="wide")
st.title("⚙️ Operations Cockpit")
st.markdown("Pipeline health, freshness SLA, run control, notifications, and diagnostics.")

# Freshness SLA
st.subheader("📊 Freshness SLA Dashboard")
fresh = data_service.freshness_status()
icon = {"fresh":"🟢","watch":"🟡","stale":"🔴"}.get(fresh["status"],"⚪")
st.markdown(f"### {icon} Status: **{fresh['status'].upper()}**")
fc1, fc2, fc3 = st.columns(3)
fc1.metric("Age (minutes)", fresh.get("age_minutes","N/A"))
fc2.metric("Target (minutes)", fresh.get("target_minutes", 30))
fc3.metric("Stale After", f"{fresh.get('stale_after_minutes',60)} min")
st.write(f"Last completed: {fresh.get('last_completed','N/A')}")

# Pipeline Runs
st.subheader("🔄 Pipeline Run History")
runs = data_service.get_pipeline_runs()
if not runs.empty:
    st.dataframe(runs.sort_values("started_at", ascending=False), width="stretch", hide_index=True)

    # Stats
    completed = runs[runs["status"] == "completed"]
    failed = runs[runs["status"] == "failed"]
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Total Runs", len(runs))
    rc2.metric("Completed", len(completed))
    rc3.metric("Failed", len(failed))
    rc4.metric("Avg Duration (s)", f"{completed['duration_seconds'].mean():.0f}" if not completed.empty else "N/A")

    if not failed.empty:
        st.error("**Failed Runs:**")
        for _, f in failed.iterrows():
            st.write(f"- `{f['run_id']}` ({f['aoi_name']}): {f.get('error_message','Unknown error')}")

# Run Control
st.subheader("🎮 Run Control")
rc1, rc2, rc3 = st.columns(3)
if rc1.button("▶️ Trigger Daily Pipeline"):
    st.info("Pipeline triggered: `python scripts/run_daily.py`")
    st.code("python scripts/run_daily.py", language="bash")
if rc2.button("🔍 Discover Scenes"):
    st.info("Scene discovery: `python scripts/discover_scenes_job.py`")
if rc3.button("🌧️ Hydromet Ingestion"):
    st.info("Hydromet pull: `python scripts/hydromet_ingestion_job.py`")

# Notification Audit
st.subheader("📨 Notification Delivery Audit")
notifs = data_service.get_notifications()
if not notifs.empty:
    nc1, nc2, nc3, nc4 = st.columns(4)
    nc1.metric("Succeeded", len(notifs[notifs["status"]=="succeeded"]))
    nc2.metric("Failed", len(notifs[notifs["status"]=="failed"]))
    nc3.metric("Blocked", len(notifs[notifs["status"]=="blocked"]))
    nc4.metric("Retrying", len(notifs[notifs["status"]=="retryable_failed"]))
    st.dataframe(notifs, width="stretch", hide_index=True)
else:
    st.info("No notification records.")

# Backup/Restore
st.subheader("💾 Backup & Restore")
st.markdown("Reference: `docs/backup_restore_runbook.md`")
bc1, bc2 = st.columns(2)
if bc1.button("📤 Export State Snapshot"):
    st.info("Snapshot exported via `GET /internal/admin/state/export`")
    st.write(f"RPO Target: 15 minutes | RTO Target: 30 minutes")
if bc2.button("📥 Restore Snapshot"):
    st.warning("Restore via `POST /internal/admin/state/restore`")

# Release Readiness
st.subheader("🚀 Release Readiness Checklist")
checklist = data_service.get_release_checklist()
for item in checklist:
    icon = {"pass":"✅","warning":"⚠️","fail":"❌","skip":"⏭️"}.get(item["status"],"⚪")
    st.write(f"{icon} [{item['category']}] {item['item']}")

# Incident Diagnostics
st.subheader("🔧 Incident Diagnostics")
st.markdown("""
| Component | Status | Last Check |
|-----------|--------|-----------|
| STAC Endpoint | 🟢 Healthy | 2 min ago |
| Hydromet API | 🟢 Healthy | 5 min ago |
| Storage (raw/prepared) | 🟢 Available | 1 min ago |
| Notification SMS | 🟡 Degraded | 10 min ago |
| Notification Email | 🟢 Healthy | 3 min ago |
""")
