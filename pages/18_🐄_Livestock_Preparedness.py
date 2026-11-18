"""Text-first flood preparedness and recovery information for livestock owners."""

import streamlit as st

from preparedness_ui import NDMA_FLOOD_GUIDE, begin_guide, show_checklist, show_detail

LEGS_HANDBOOK = "https://www.livestock-emergency.net/download-legs/"
SINDH_CONTACTS = "https://livestock.sindh.gov.pk/contact-us"
PUNJAB_DIRECTORY = "https://lahoredivision.punjab.gov.pk/provincial"

show_all = begin_guide(
    "Livestock Preparedness Guide", "🐄",
    "General guidance for owners of cattle, buffalo, goats, sheep and poultry. "
    "Follow official flood instructions and ask a veterinary professional about animal health.",
)

show_checklist("Before flooding", (
    "Keep a list of your animals, identifying marks and health records.",
    "Prepare protected fodder and clean water supplies. Ask your district livestock office how much to plan for.",
    "Discuss shelter plans with local authorities before flooding and check access and suitability.",
))
show_detail("Animal identification and records", f"""
- Record species, breed, sex, approximate age, tags or identifying marks. Keep clear photos if possible.
- Store copies of vaccination and treatment records somewhere protected. Ask your district livestock office about local registration.

References: [Livestock Emergency Guidelines and Standards (LEGS), 3rd edition]({LEGS_HANDBOOK})
and [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)
show_detail("Feed and water before flooding", f"""
- Plan feed and clean-water needs with your district livestock office. Needs vary by animal, weather and local supply.
- Keep fodder and feed dry and protected. Prepare clean water containers and identify a backup source of feed and water.
- Ask your livestock office about locally suitable alternatives if supplies are disrupted.

Source: [LEGS, feed and water chapters]({LEGS_HANDBOOK}).
""", show_all=show_all)
show_detail("Shelter and movement planning", f"""
- Ask local authorities about shelter suitability and official movement instructions. Confirm access before relying on any location.
- Prepare suitable handling equipment and plan space to separate animals when needed.

References: [LEGS, livestock shelter chapter]({LEGS_HANDBOOK})
and [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)

show_checklist("During flooding", (
    "Put people first and follow NDMA, PDMA and local instructions for any movement.",
    "Keep animals away from floodwater where you can do so safely.",
    "Watch for injury, illness or distress. Contact a veterinary professional for advice.",
))
show_detail("Animal welfare and official instructions", f"""
- Avoid trying to reach or move animals through floodwater. Follow official guidance when movement is safe.
- Keep track of animals by herd or flock if safe to do so. Ask a veterinary professional about injured, distressed or vulnerable animals.
- Report unusual illness or deaths to your local veterinary or livestock office.

References: [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF")
and [LEGS, veterinary support chapter]({LEGS_HANDBOOK}).
""", show_all=show_all)

show_checklist("After flooding", (
    "Keep suspect feed and water separate and ask local officers about safe supplies.",
    "Ask your district livestock office about veterinary assessment and recovery.",
    "Record losses and keep copies of official reports and receipts.",
))
show_detail("Feed and water recovery", f"""
- Keep floodwater and suspected contaminated water away from animals. Ask local authorities about safe water sources.
- Keep water-damaged or mouldy feed separate and ask the livestock office about safe disposal and replacement feed.
- Ask extension staff about affected pasture before using it again.

Source: [LEGS, feed and water chapters]({LEGS_HANDBOOK}).
""", show_all=show_all)
show_detail("Veterinary recovery and reporting", f"""
- Contact a veterinary professional for assessment and follow local guidance about vaccination and disease reporting.
- Ask local authorities how to dispose of dead animals safely. Keep carcasses out of waterways.
- Use district livestock or revenue department channels for loss assessment. Record animal deaths, injuries, missing animals and damage to shelters or equipment separately.
- Keep supporting records private and follow the district process for providing them.

References: [LEGS, veterinary support chapter]({LEGS_HANDBOOK})
and [NDMA flash flood preparedness and damage assessment]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)

st.header("Veterinary Information and Official Resources")
st.markdown(f"""
- Your district livestock office or a licensed veterinarian can advise on animal health, feed and recovery.
- [Sindh Livestock and Fisheries Department contacts]({SINDH_CONTACTS}) · Provincial contact information.
- [Punjab Livestock and Dairy Development Department contact listing]({PUNJAB_DIRECTORY}) · Lahore Division government directory.
- [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF") · General flood preparedness and official safety guidance.
- [LEGS handbook]({LEGS_HANDBOOK}) · Technical reference for feed, water, shelter and veterinary support.

This site cannot verify whether a veterinary clinic, shelter, fodder point or water supply is open or accessible.
Confirm arrangements with the relevant local office.
""")
show_detail("Limitations", """
- This guide provides general preparedness information. Seek veterinary advice for your own animals.
- Use your district's official channels for reporting animal losses. Check each source's date and coverage.
- This guide is available in English. Reviewed Urdu guidance is pending.
""", show_all=show_all)
