"""
Farmer Preparedness — sourced guidance for crop and farm protection.

This page provides attributed, text-first preparedness information for farmers.
Content is derived from published guidance by FAO, NDMA and agricultural
extension services.  No unverified Urdu translations are included; Urdu
content is marked as a required subtask (PK-003).

This page does NOT:
- Fabricate environmental observations or flood predictions.
- Provide parcel-level risk assessments or crop insurance guidance.
- Issue evacuation instructions or emergency warnings.
- Claim availability of government services without verification.
"""
from __future__ import annotations

import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Farmer Preparedness", page_icon="🌾", layout="wide")
st.title("🌾 Farmer Preparedness Guide")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information")

data_service = DataService()
if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)

st.info(
    "This page provides general preparedness guidance compiled from published "
    "sources.  It is **not a substitute for official instructions** from NDMA, "
    "PDMA, or local agricultural extension services.  Always follow official "
    "guidance for your specific area."
)

# ── Before the Flood ────────────────────────────────────────────────────────
st.header("🔵 Before the Flood Season")

with st.expander("🌱 Crops and Planting Materials", expanded=True):
    st.markdown("""
**Preparedness actions (general guidance):**

- **Know your area's flood history.** Check official sources for historical
  flood information relevant to your district or tehsil.  Past extent does not
  predict future flooding.
- **Seed and planting material.** Store seeds, seedlings and planting stock in
  sealed, waterproof containers at an elevated location.
- **Harvesting schedule.** Where possible, adjust planting and harvesting
  timing based on official seasonal advisories.
- **Crop documentation.** Keep records of crop type, planting date, estimated
  area and variety.  These may be needed for damage assessment.

*Sources: FAO Pakistan flood-impact assessments; NDMA monsoon preparedness
guidelines.  Specific planting calendars should be obtained from your district
agricultural extension office.*
""")

with st.expander("🏠 Stored Grain and Feed"):
    st.markdown("""
**Preparedness actions:**

- **Elevate grain storage.** Move stored grain, animal feed and agricultural
  chemicals above expected flood levels where possible.
- **Waterproof storage.** Use sealed containers or waterproof coverings for
  stored grain and seed stock.
- **Inventory.** Maintain a written list of stored quantities by type and
  location before the flood season.
- **Backup copies.** Keep copies of farm records, land documents and financial
  records in a separate, protected location.

*Source: FAO post-disaster needs assessment guidelines.*
""")

with st.expander("🔧 Equipment and Infrastructure"):
    st.markdown("""
**Preparedness actions:**

- **Irrigation equipment.** Disconnect and move portable pumps, pipes and
  motors to higher ground.  Fixed infrastructure should be documented for
  insurance or damage assessment.
- **Agricultural chemicals.** Store pesticides, herbicides and fertilizers in
  secure, elevated and sealed containers to prevent contamination of
  floodwater.
- **Tools and machinery.** Relocate or elevate portable tools and machinery
  where practical.
- **Fuel and power.** Store fuel safely at elevation.  Know how to safely shut
  off electrical connections before evacuating.

*Source: NDMA monsoon preparedness guidance; FAO emergency preparedness for
agriculture.*
""")

# ── During the Flood ────────────────────────────────────────────────────────
st.header("🟡 During the Flood")

with st.expander("⚠️ Immediate Actions", expanded=True):
    st.markdown("""
**Follow official instructions from NDMA, PDMA and local authorities.**

- **Safety first.** People and animals take priority over crops and equipment.
- **Avoid floodwater.** Do not attempt to save crops or equipment by entering
  floodwater.  Floodwater may carry debris, contaminants and disease.
- **Monitor official channels.** Continue checking official sources (FFD, NDMA,
  PDMA) for updated flood bulletins and instructions.
- **Document conditions.** If safe to do so, note the date, approximate water
  level and affected areas for later assessment.  Do not enter dangerous areas
  to take photographs.

*Source: NDMA safety advisories; WHO flood safety guidance.*
""")

# ── After the Flood ─────────────────────────────────────────────────────────
st.header("🟢 After the Flood — Recovery")

with st.expander("🌾 Crop and Soil Recovery", expanded=True):
    st.markdown("""
**Post-flood assessment actions:**

- **Wait for official clearance.** Do not return to flooded areas until
  authorities confirm it is safe.
- **Assess damage.** Document crop losses with dates, estimated area and
  photographs where safe.  Report through official damage-assessment channels.
- **Soil assessment.** Floodwater may deposit silt, contaminants or salts.
  Contact your local agricultural extension office for soil testing before
  replanting.
- **Replanting guidance.** Consult agricultural extension services for
  recommended varieties and timing for replanting after flooding.
- **Contaminated produce.** Do not consume or sell crops that were submerged
  in floodwater without guidance from health authorities.

*Sources: FAO post-flood agricultural recovery guidance; Pakistan Agricultural
Research Council guidelines.*
""")

with st.expander("📋 Damage Reporting"):
    st.markdown("""
**Reporting actions:**

- **Official channels.** Report crop and farm damage through your district's
  official damage-assessment process (revenue department, agricultural extension
  office, or PDMA).
- **Keep records.** Maintain copies of all damage reports and receipts.
- **Distinguish types.** Report crop loss, stored grain loss, equipment damage,
  irrigation damage and soil contamination as separate items.
- **Privacy.** You are not required to share exact farm locations publicly.
  Official assessments have their own confidentiality procedures.

*Note: This system does not currently accept damage reports.  Use official
channels for all damage reporting.*
""")

# ── Authoritative Resources ─────────────────────────────────────────────────
st.header("📚 Authoritative Resources")

st.markdown("""
| Organisation | Resource | Notes |
|---|---|---|
| [FAO Pakistan](https://www.fao.org/pakistan/en/) | Agricultural emergency and recovery guidance | National and provincial scope; check publication dates |
| [NDMA](https://www.ndma.gov.pk/) | National disaster preparedness and response | Official guidelines and situation reports |
| [Pakistan Agricultural Research Council](https://www.parc.gov.pk/) | Crop and soil science guidance | Research-based recommendations |
| [FFD / PMD](https://ffd.weather.gov.pk/) | Flood forecasts and advisories | Official flood bulletins |

*Links verified: November 2026.  Link availability does not confirm current
service status.  Check each source for publication date and geographic scope.*
""")

# ── Limitations ──────────────────────────────────────────────────────────────
with st.expander("⚠️ Limitations"):
    st.markdown("""
- This page provides **general preparedness guidance**, not area-specific
  instructions.
- **No crop insurance or compensation guidance** is provided.  Contact your
  local revenue department or agricultural extension office.
- **Urdu translation** is a required subtask and is not yet available.
- **No real-time flood data** is shown on this page.  See the Public Dashboard
  for current event information, and official sources for authoritative notices.
- Guidance is compiled from published sources and may not reflect the most
  recent updates.  Always verify with official channels.
""")
