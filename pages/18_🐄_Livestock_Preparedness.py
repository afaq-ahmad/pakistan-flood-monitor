"""
Livestock Preparedness — sourced guidance for animal owners during floods.

This page provides attributed, text-first preparedness information for
livestock owners (cattle, buffalo, goats, poultry and other animals).
Content is derived from published guidance by FAO, livestock departments
and veterinary authorities.

This page does NOT:
- Imply that shelters, veterinary services or fodder supplies are currently
  available without verification.
- Provide veterinary medical advice or treatment protocols.
- Fabricate environmental observations or flood predictions.
- Issue evacuation instructions or emergency warnings.

Urdu translation is a required subtask (PK-003) and is not included here.
"""
from __future__ import annotations

import streamlit as st

from backend_service import DEMO_WATERMARK, DataService

st.set_page_config(page_title="Livestock Preparedness", page_icon="🐄", layout="wide")
st.title("🐄 Livestock Preparedness Guide")
st.page_link("pages/16_📚_Official_Information.py", label="Official flood information")

data_service = DataService()
if data_service.is_demo_mode:
    st.warning(DEMO_WATERMARK)

st.info(
    "This page provides general preparedness guidance for livestock owners, "
    "compiled from published sources.  It is **not a substitute for "
    "veterinary advice** or official instructions from NDMA, PDMA, or "
    "district livestock departments.  Always follow official guidance."
)

# ── Before the Flood ────────────────────────────────────────────────────────
st.header("🔵 Before the Flood Season")

with st.expander("🐄 Animal Identification and Records", expanded=True):
    st.markdown("""
**Preparedness actions:**

- **Identify your animals.** Maintain a written list of all livestock
  including species, breed, sex, approximate age and any identifying marks or
  tags.
- **Vaccination records.** Keep copies of vaccination and treatment records
  in a waterproof container at an elevated or separate location.
- **Registration.** If your district has a livestock registration system,
  ensure your animals are registered.  This may assist with post-flood
  verification and assistance.
- **Photographs.** Take clear photographs of your animals for identification
  purposes.

*Source: FAO emergency livestock guidelines; district livestock department
registration guidance.*
""")

with st.expander("🌿 Fodder and Water Preparation"):
    st.markdown("""
**Preparedness actions:**

- **Fodder stockpile.** Store at least 2–4 weeks of feed at an elevated
  location, using waterproof containers or sealed bags where possible.
- **Alternative feed.** Identify alternative feed sources (crop residues, tree
  fodder) in case primary supply is disrupted.
- **Water storage.** Prepare clean water containers.  Floodwater is not safe
  for animal consumption due to contamination risk.
- **Salt and mineral licks.** Include mineral supplements in your stored
  supplies.

*Sources: FAO Pakistan flood-impact assessments (2025); livestock department
monsoon advisories.  Specific fodder requirements vary by species, breed and
local conditions — consult your district livestock office.*
""")

with st.expander("🏠 Shelter and Movement Planning"):
    st.markdown("""
**Preparedness actions:**

- **Evacuation route.** Identify safe higher ground and routes to move animals
  before flooding.  Practice moving animals to reduce stress during
  emergencies.
- **Temporary shelter.** Identify potential temporary shelter locations on
  higher ground.  Confirm access and suitability in advance.
- **Tethering and restraint.** Have ropes, halters and restraint equipment
  ready.  Animals may panic in floodwater.
- **Species separation.** Plan to keep different species and aggressive
  animals separate during movement and temporary sheltering.

*Source: NDMA monsoon preparedness guidelines; FAO livestock emergency
guidance.*

> ⚠️ **This system cannot verify** whether any specific shelter, camp or
> fodder supply point is currently open or accessible.  Confirm with local
> authorities before travelling.
""")

# ── During the Flood ────────────────────────────────────────────────────────
st.header("🟡 During the Flood")

with st.expander("⚠️ Immediate Actions", expanded=True):
    st.markdown("""
**Follow official instructions from NDMA, PDMA and local authorities.**

- **Human safety first.** Do not risk human life to save animals.
- **Move animals early.** If authorities issue warnings, move animals to
  higher ground as early as possible.  Do not wait until floodwater arrives.
- **Avoid floodwater.** Do not let animals drink or wade through floodwater.
  It may contain sewage, chemicals, debris and disease organisms.
- **Keep animals together.** Try to keep herd or flock groups together to
  reduce stress and facilitate counting.
- **Monitor health.** Watch for signs of injury, illness or distress.

*Source: NDMA safety advisories; WHO/FAO flood safety guidance.*
""")

with st.expander("🩺 Animal Health During Flooding"):
    st.markdown("""
**Health monitoring:**

- **Injuries.** Treat visible wounds with clean water and basic first aid.
  Contact a veterinary professional as soon as possible.
- **Disease risk.** Floodwater increases risk of waterborne diseases (e.g.,
  anthrax spore release from soil, leptospirosis, foot-and-mouth disease).
  Report unusual illness or death to your local veterinary office.
- **Stress and exposure.** Provide shade or shelter where possible.  Animals
  exposed to cold floodwater are at risk of hypothermia.
- **Pregnant animals.** Pregnant animals are particularly vulnerable.  Avoid
  unnecessary movement and stress.

*Source: FAO livestock disease surveillance guidance; veterinary department
monsoon health advisories.*

> ⚠️ **This page does not provide veterinary treatment advice.**  Contact a
> licensed veterinarian or your district livestock department for medical
> guidance.
""")

# ── After the Flood ─────────────────────────────────────────────────────────
st.header("🟢 After the Flood — Recovery")

with st.expander("🌿 Fodder and Water Recovery", expanded=True):
    st.markdown("""
**Recovery actions:**

- **Water safety.** Do not use floodwater or water from contaminated sources
  for animals.  Wait for official guidance on water safety.
- **Fodder assessment.** Inspect stored fodder for water damage, mould and
  contamination before feeding.  Discard contaminated feed.
- **Pasture recovery.** Flood-deposited silt may benefit or harm pasture
  depending on contaminants.  Consult your agricultural extension office.
- **Emergency feed.** Contact your district livestock department or FAO for
  information about emergency feed distribution, if available.

*Source: FAO post-flood livestock recovery; Dawn reporting on fodder
disruption (October 2025).*
""")

with st.expander("🩺 Post-Flood Animal Health"):
    st.markdown("""
**Health recovery actions:**

- **Veterinary inspection.** Have animals examined by a veterinary
  professional as soon as services are accessible.
- **Vaccination.** Follow official guidance on post-flood vaccination
  campaigns.  Your district livestock department coordinates these.
- **Disease surveillance.** Report any unusual illness, deaths or reproductive
  problems to veterinary authorities.
- **Carcass disposal.** Dead animals must be disposed of safely following
  official guidelines to prevent disease spread.  Do not dump carcasses in
  waterways.

*Source: FAO disease surveillance guidance; provincial livestock department
post-flood protocols.*
""")

with st.expander("📋 Damage Reporting"):
    st.markdown("""
**Reporting actions:**

- **Official channels.** Report animal losses through your district livestock
  department and revenue department.
- **Document losses.** Record species, number, approximate value and
  circumstances of each loss.
- **Distinguish types.** Report animal death, injury, missing animals and
  property damage (sheds, equipment) as separate items.
- **Privacy.** Official damage assessments have their own confidentiality
  procedures.

*Note: This system does not currently accept livestock damage reports.
Use official channels for all damage reporting.*
""")

# ── Authoritative Resources ─────────────────────────────────────────────────
st.header("📚 Authoritative Resources")

st.markdown("""
| Organisation | Resource | Notes |
|---|---|---|
| [FAO Pakistan](https://www.fao.org/pakistan/en/) | Livestock emergency and recovery guidance | National; check publication dates |
| [NDMA](https://www.ndma.gov.pk/) | National disaster preparedness and response | Official guidelines and situation reports |
| [FFD / PMD](https://ffd.weather.gov.pk/) | Flood forecasts and advisories | Official flood bulletins |
| District Livestock Department | Local veterinary services and vaccination | Contact your district office directly |

*Links verified: November 2026.  Link availability does not confirm current
service status or that veterinary services are operational.  Check each source
for publication date and geographic scope.*
""")

# ── Limitations ──────────────────────────────────────────────────────────────
with st.expander("⚠️ Limitations"):
    st.markdown("""
- This page provides **general preparedness guidance**, not area-specific or
  species-specific veterinary instructions.
- **No verified service directory** is available.  This system cannot confirm
  whether any shelter, veterinary clinic, fodder point or water supply is
  currently open or accessible.
- **Urdu translation** is a required subtask and is not yet available.
- **No real-time flood data** is shown on this page.  See the Public Dashboard
  for current event information, and official sources for authoritative notices.
- Guidance is compiled from published sources and may not reflect the most
  recent updates.  Always verify with official channels.
""")
