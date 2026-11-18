# Project overview

Pakistan Flood Monitor explores flood situational awareness using public
Earth observation and meteorological sources. The current application
provides a corridor reference catalogue, an eligible published event view,
official information links and general preparedness guides. Use official
agencies and local authorities for warnings and emergency instructions.

## Public experience

- **My Area** lets users choose a configured river corridor. Published events
  without a confirmed configured association stay in the all-events view.
  Administrative district, tehsil, village and farm coverage remain unverified.
- **Official flood information** links to government sources. Check the
  bulletin's issue date and applicable area at the source.
- **Preparedness** provides English farm and livestock checklists with sources,
  optional details and a view for printing. Reviewed Urdu guidance and browser
  accessibility verification remain open.
- **Community reporting** offers a standalone demo practice preview.
  Operational resident intake and private durable acknowledgements are pending.

The configured corridor names are Indus-Lower, Indus-Upper, Chenab-Middle,
Jhelum-Lower, Sutlej-Lower and Kabul-Nowshera. They are static references from
`Settings.pilot_corridors` in the canonical configuration. Catalogue membership,
an available service, or an empty event list does not establish conditions
on the ground.

## Research and limitations

Forecasting and dam-risk pages are restricted to standalone demo or test
contexts. The LSTM is untrained for operational use, and the dam surface
extent is a proxy. Advanced SAR uses simulation, water detection includes
RGB proxies, and replay scenarios exercise software behavior. Independent
validation is required for operational use of these outputs.

For current capabilities and blockers see [implementation status](engineering/IMPLEMENTATION_STATUS.md).
For feature requirements see the [Pakistan product roadmap](product/PAKISTAN_FEATURE_ROADMAP.md).
