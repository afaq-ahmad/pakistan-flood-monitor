# Flood information for farmers, livestock owners, and communities

The walkthrough was recorded on 18 November 2026 against `main` at `d24fa22`, after PRs #85 and #86. It uses simulated personas and deterministic software checks. The research describes past events and identifies needs worth validating. The [QA matrix](FARMER_LIVESTOCK_QA_MATRIX.md) holds reproducible findings and the [master task plan](../engineering/MASTER_TASK_PLAN.md) owns delivery status.

## Research and implications

| Source | Historical evidence and product implication |
|---|---|
| [World Bank, lessons from the 2025 KP flash floods](https://www.worldbank.org/en/news/feature/2026/09/03/preparing-better-for-monsoons-lessons-from-the-2025-flash-floods-in-pakistan) | Among 1,207 households surveyed in Buner, Shangla and Swat, 85% received no warning and roughly half of warned households had under 30 minutes. Community networks mattered. Show concise source and issue time before maps, and retain those fields in forwarded messages. The sample describes those districts. |
| [FAO, 2025 geospatial assessment](https://www.fao.org/geospatial/news/news-detail/fao-releases-geospatial-flood-impact-assessment-for-pakistan--2025/en) | The study estimates agricultural and crop exposure from mapped extents for defined periods in Punjab, Sindh and KP. Show data windows, resolution and limits. Crop exposure alone cannot establish field loss, yield loss, or compensation eligibility. |
| [FAO GIEWS Pakistan brief, 6 February 2026](https://www.fao.org/giews/countrybrief/country.jsp?code=PAK&lang=en) | National crop and food-security summaries provide seasonal context. Their geography and reference date differ from an individual farm or today's flood conditions. |
| [Dawn, Punjab service and access gaps, 3 September 2025](https://www.dawn.com/news/1939265) | Communities reported severed rural road links and gaps in assistance. Distinguish reported access problems from a verified road closure or open relief site. |
| [Dawn, fodder and recovery, October 2025](https://www.dawn.com/news/1945551) | FAO findings reported disrupted fodder supplies and livestock health risks. A directory needs verified contacts, services, areas and review dates before it can show availability. |
| [IFRC, Pakistan Monsoon Floods 2025](https://www.ifrc.org/emergency/pakistan-monsoon-floods-2025) | Damage to roads, crops and livestock coincided with shortages of safe water and services. Keep those impact and assistance categories distinct. |
| [PMD Flood Forecasting Division](https://ffd.pmd.gov.pk/) and [Punjab PDMA](https://pdma.punjab.gov.pk/) | The FFD site served its public source page during review. Punjab PDMA's indexed official page was found, but a direct fetch timed out. Verify accessibility again before relying on the link. Confirm source issue time and geographic scope at the source. A directory link gives no evidence of service availability, partnership, or permission for ingestion. |

## Simulated personas

These are design scenarios. Device choices, literacy, languages, how messages are forwarded, and willingness to submit information are field research hypotheses for each persona.

### A. Small farmer near the Chenab

- **Objective and hazards.** Understand possible impact to planted crops, stored grain, animals and irrigation pumps during river flooding and road disruption.
- **Before / during / after.** Locate the relevant district or reach and dated official notice. During an event, check whether published information exists and where it came from. Afterward, compare a dated extent with separately labelled crop exposure and reported damage.
- **Access.** Hypothesis of a shared Android device with weak data, Urdu or Punjabi, and text alongside maps.
- **Journey and current limit.** Public Dashboard and Official Information first, then Historical Flood Map and exposure. The district filter depends on published event records. There is no validated mouza-to-corridor mapping, parcel exposure, crop stage, or storage-loss evidence.
- **Failure and acceptance.** An empty feed may be read as safety or a historical polygon as damage. Pass when a lightweight reference view, source links and distinct unknown states are visible, and acreage or loss appears only with its method, date, units and scope. See FL-01–03.

### B. Livestock owner

- **Objective and hazards.** Plan for buffalo, cattle, goats or poultry amid disrupted fodder, drinking-water and access, and find trustworthy veterinary information.
- **Before / during / after.** Find dated authority preparedness guidance. During a flood, check authoritative service and access information if available. Afterward, report animal loss or contaminated water separately and see the moderation state.
- **Access.** Hypothesis of intermittent phone data, a preference for Urdu or local-language text/audio, and occasional printed or forwarded messages.
- **Journey and current limit.** Official Information is a generic directory. No verified animal shelter, fodder, water or veterinary service roster, and no public reporting journey.
- **Failure and acceptance.** A guessed open camp can waste a trip. Pass when provider, supported species or service, area and verification time are visible for each confirmed listing, with stale or missing availability explicit. Keep treatment and transport decisions with authorized sources. See FL-04–05.

### C. Tenant or landless agricultural worker

- **Objective and hazards.** Find relevant alerts and assistance even with uncertain land records or limited money for transport.
- **Before / during / after.** Identify a coarse area without supplying property identity. During disruption, check source and access status. Afterward, submit a worker or tenant report without implying entitlement or requiring a land title.
- **Access.** Hypothesis of prepaid mobile data, shared access, Urdu/Punjabi or another regional language, and a need for short labels.
- **Journey and current limit.** Official links are available. There is no resident-facing assistance-status or report acknowledgement workflow. Role-protected API intake requires a linked event.
- **Failure and acceptance.** Requiring exact property data may exclude tenants and expose households. Pass when anonymous lookup is available and any future intake collects only justified data with a receipt, retention policy and a clear distinction between self-report and verification. See FL-04–05.

### D. Rural household with an inexpensive Android phone

- **Objective and hazards.** Read an area and source quickly despite intermittent mobile data, missing media or a small screen.
- **Before / during / after.** Bookmark official sources, read a plain-text status if tiles fail, then check updated or corrected records.
- **Access.** Low-cost Android, weak data and Urdu are hypotheses for testing. Include keyboard/assistive users, scaling, right-to-left layout and local-language needs.
- **Journey and current limit.** Official Information is text-first once Streamlit loads. A public event outage suppresses the area selector. Maps and imagery use heavier components, and offline first-load and reviewed Urdu strings have no acceptance evidence.
- **Failure and acceptance.** Slow loads can hide the only actionable source link. Pass when essential text renders without tiles or provider calls in an already loaded application. Separately test cold offline, 360 px reflow, keyboard order and reviewed Urdu. See FL-01, FL-06 and FL-12.

### E. Community volunteer

- **Objective and hazards.** Relay a dated, source-attributed message through local groups, mosques, or phone calls while avoiding stale guidance.
- **Before / during / after.** Save source references. During an event, confirm issuer, scope, issue and expiry. Afterward, relay corrections and retire expired messages.
- **Access.** Text copy and print alongside potential voice relays. Test Urdu and other languages with actual volunteers.
- **Journey and current limit.** Partner Mode demonstrates downloadable text with a demo marker and an update line. It lacks an issuer and expiry contract for official sharing, and the notification providers are stubs.
- **Failure and acceptance.** A forwarded message can lose its demo label or be read long after validity. Pass when an approved source, area, issue/expiry, uncertainty and demo status survive plain-text export. Unreviewed or expired products remain unavailable. See FL-07 and FL-11.

### F. District disaster analyst

- **Objective and hazards.** Assess evidence, separate reported impacts from observations, and maintain review continuity across restarts.
- **Before / during / after.** Check model, data and source limits, review draft candidates and reports privately, then preserve the decision trail and corrections.
- **Access.** Hypothesis of an office workstation and a tablet/phone in the field, with UTC/PKT awareness, structured evidence and plain-language summaries.
- **Journey and current limit.** PR #86 added the role-protected, read-only queue. It covers the current process. Field Reports and Partner Mode still have different evidence and presentation paths.
- **Failure and acceptance.** Loss of audit state or unsafe publication can mislead communities. Pass when event identity, reviewer authorization, duplicate/restart behavior and transactional review history are tested. Source, acquisition time, method, units and uncertainty must survive publication. See FL-05, FL-07 and FL-10.

## Application walkthrough

| Surface | User question and data path | Limits observed or requiring verification |
|---|---|---|
| Public Dashboard and My Area | Streamlit → `DataService.get_public_events` → canonical `/public/events` and its publication gate, or labelled demo fixtures. Exposure is suppressed in configured API mode. | Feed errors differ from empty results. The district selector depends on event rows, and the canonical collection omits area fields including district. A corridor in settings is a reference label rather than evidence of village coverage. Live freshness is unavailable. |
| Official Information | Streamlit → static `official_sources.py` → FFD and NDMA pages. | Source review date refers to links. Live status and provincial service availability remain external. Text can render with provider requests blocked once the application has loaded. |
| Satellite Viewer | Streamlit → STAC search → footprints and thumbnails; scene discovery. | A scene is evidence of imagery availability. It does not measure flood impact in a village. Search needs connectivity, provider credentials where applicable, and acquisition/scene QA. |
| NASA Hydromet | Streamlit → `nasa_service.py` → NASA POWER, HLS and IMERG discovery. | Offline auto-load can show both errors and a count marked successful. Rainfall, risk score and flood extent are different products. Network and satellite coverage can fail. |
| Water Detection | Streamlit → `satellite_ml_service.py` → thumbnails, clustering and local flood memory. | Prototype classifications lack accepted field-level validation. Image-derived water percentage cannot establish crop or animal loss. |
| Flood Forecasting | Streamlit → Open-Meteo GFS → prototype LSTM and hard-coded thresholds. | Optional dependencies may disable the button. The enabled path has untrained weights, substitutes rain for its soil-moisture feature, and can present an evacuation-style message. The selected plot title can also change without fetching a new forecast. |
| Dam Flood Risk | Streamlit → `dam_service.py` → STAC thumbnail or synthetic fallback → local history/risk score. | Missing imagery can yield a number tagged as a satellite proxy. Surface extent cannot establish reservoir volume or a downstream alert. |
| Historical Flood Map | Streamlit → bundled JSON → dated event outlines and local map. | Some text calls these ground truth. Treat the outlines as contextual unless source licensing and validation support stronger claims. |
| Field Reports | Streamlit → local CSV reads and moderation. Canonical internal report intake → process-local records → moderation/audit, separate from the page. | No resident submission or receipt UI. The page can show local reports in API mode. Approve feedback does not check the returned result. Keep precise locations and evidence out of public views. |
| Analyst Review | Streamlit → supplied role credential → canonical review queue. | Candidate lifecycle appears privately. The queue is process-local and read-only. The existing canonical review path does not provide the application a restart-safe dashboard workflow. |
| Partner Mode | Streamlit → public events or demo fixtures → local text advisory and optional exposure. | Demo marker survives the tested download payload. The payload lacks expiry and a verified issuer. Canonical operational mobile products require reviewed publication. |
| Export Centre | Streamlit → local demo GeoJSON point and manifest. | Operational GIS export is deliberately unavailable. A demo point is neither a field boundary nor a damage assessment. |
| Notifications | Dispatcher → SMS, email and WhatsApp provider stubs → constructed receipt. | A simulated receipt does not confirm delivery. Validate consent, verification and provider acceptance before enabling subscriptions. |
| Canonical API and persistence | Reviewed publication gate → public feeds. Role-protected routes → current review/report state and workflow DB. | The public list filters publication status and gate. Some operational products fail closed with HTTP 503. Durable review and evidence lineage remain separate requirements. |

## First implementation

PK-001 adds a text reference to the six configured pilot corridors before the event feed stop
conditions. It uses corridor names from canonical configuration only. The reference appears
when no events are published, the request fails, or the API is unconfigured. The official source
link remains visible. Event-based district filtering retains its existing behavior. Province labels
in the corridor model are not valid district boundaries. Later area work requires licensed and
validated district, tehsil and mouza identifiers plus explicit aliases, coverage, and missing-data
semantics. The [feature roadmap](PAKISTAN_FEATURE_ROADMAP.md) records remaining dependencies.

The walkthrough used AppTest and injected HTTP responses, plus code inspection. It did not
verify actual flood conditions, field needs, a fully offline first load, mobile rendering,
assistive technologies, source permissions, or scientific accuracy.
