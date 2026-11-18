"""Text-first, sourced guidance for farm preparedness and recovery."""

import streamlit as st

from preparedness_ui import NDMA_FLOOD_GUIDE, begin_guide, show_checklist, show_detail

FAO_GRAIN = "https://www.fao.org/pakistan/news/detail-events/en/c/1709335/"
FARM_PREPARATION = (
    "https://www.uvm.edu/extension/newfarmerproject/resources/sites/default/files/"
    "resource-files/preparing-farms-for-potential-flooding-071024.pdf"
)
FARM_FOOD_SAFETY = (
    "https://extension.illinois.edu/blogs/commercial-fruit-and-vegetable-growers/"
    "2025-07-30-flooding-and-food-safety-farms"
)

show_all = begin_guide(
    "Farmer Preparedness Guide", "🌾",
    "General guidance for crops, stored grain, equipment and farm records. "
    "Follow NDMA, PDMA and local agricultural extension instructions for your area.",
)

show_checklist("Before flooding", (
    "Protect seed and stored grain and keep farm records somewhere dry.",
    "Plan where to move portable pumps, tools and farm supplies before flooding.",
    "Check official advisories and ask your district agricultural extension office about crop timing.",
))
show_detail("Seed, stored grain and farm records", f"""
- Use sealed storage for seed and stored grain. Move stock and feed out of low-lying storage before flooding where possible.
- Keep a list of stored quantities and locations. Record crop type, variety, planting date and estimated area.
- Keep a protected copy of crop, land, inventory and financial records away from your main records.

Sources: [FAO Pakistan's seed and grain storage work in Dadu]({FAO_GRAIN}) and
[NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)
show_detail("Crops, equipment and chemicals", f"""
- Check official seasonal notices and ask your district agricultural extension office about planting and harvesting dates. Past floods do not predict the next flood.
- Move portable pumps, pipes, motors and tools out of low-lying areas in advance, when safe. Record fixed equipment and irrigation infrastructure for later assessment.
- Keep pesticides, herbicides, fertilizer and fuel secure and away from likely floodwater. Leave electrical work to qualified personnel and follow official safety advice.

References: [University of Vermont Extension farm preparedness]({FARM_PREPARATION} "PDF")
and [Illinois Extension flood and farm food safety]({FARM_FOOD_SAFETY}).
Use local agricultural extension guidance for local practice.
""", show_all=show_all)

show_checklist("During flooding", (
    "Follow official instructions and put people and animals first.",
    "Stay out of floodwater. Leave crops and equipment if reaching them puts anyone at risk.",
))
show_detail("Official updates and safe documentation", f"""
- Follow FFD, NDMA, PDMA and local authorities for bulletins and instructions.
- Record the date, affected area and observed water level only from a safe place. Keep photographs for later assessment if you can take them safely.

Source: [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)

show_checklist("After flooding", (
    "Wait for official clearance before returning to affected areas.",
    "Record losses when it is safe. Ask agricultural extension staff about soil and replanting.",
    "Keep crops that touched floodwater out of the food supply and seek local food safety advice.",
))
show_detail("Crop and soil recovery", f"""
- Contact agricultural extension staff about soil testing, crop varieties and timing before replanting. Floodwater can leave silt, salts and contamination.
- Separate produce that touched floodwater. Seek local food safety guidance before using or selling flood-affected produce.

Reference: [Illinois Extension flood and farm food safety]({FARM_FOOD_SAFETY}).
""", show_all=show_all)
show_detail("Damage reporting", f"""
- Use your district's official damage assessment channels. Ask the revenue department, agriculture office or PDMA where to report.
- Record crop losses, damaged seed or stored grain, machinery and irrigation damage separately. Keep a copy of your report and any official receipt.
- Keep precise farm locations private. Use the channel's own instructions for supplying supporting details.

Reference: [NDMA flash flood preparedness and damage assessment]({NDMA_FLOOD_GUIDE} "PDF").
""", show_all=show_all)

st.header("Official and Technical Resources")
st.markdown(f"""
- [NDMA flash flood preparedness]({NDMA_FLOOD_GUIDE} "PDF") · General safety before, during and after a flood.
- [FAO Pakistan seed and grain storage in Dadu]({FAO_GRAIN}) · Published in 2024. Local agricultural preparedness example.
- District agricultural extension office · Local questions about soil tests and replanting.
- [FFD / Pakistan Meteorological Department](https://ffd.weather.gov.pk/flood-ews) · Official flood bulletins. Check the date and area on the bulletin.
""")
show_detail("Limitations", """
- This guide provides general preparedness information. Use official instructions for your area and your district's channels for damage reporting.
- The source links point to guidance and bulletins. Check each source for its date and geographic scope.
- This guide is available in English. Reviewed Urdu guidance is pending.
""", show_all=show_all)
