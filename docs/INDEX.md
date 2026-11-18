---
title: Pakistan Flood Monitor Documentation
doc_type: reference
status: current
owner: engineering
verified_at: 2026-11-18
---

# Pakistan Flood Monitor documentation

Pakistan Flood Monitor is an open-source prototype for flood situational awareness
in Pakistan. It provides a pilot river corridor catalogue, an eligible published
event view, official source links, and general farm and livestock preparedness
guidance. See [the project overview](overview.md) for the scope and limitations.

## Start here

| If you are a… | Go to |
|---|---|
| Developer setting up a checkout | [Local setup and first smoke check](setup.md) |
| Coding agent resuming work | [Agent workflow](engineering/AGENT_GITHUB_WORKFLOW.md) → [current tasks](engineering/MASTER_TASK_PLAN.md) → [latest handoff](engineering/AGENT_SESSION_LOG.md) |
| Architect or reviewer | [Runtime architecture](architecture.md) and [accepted decisions](adr/README.md) |
| QA engineer | [Test commands and evidence boundaries](testing.md) and [UX acceptance matrix](product/UI_UX_ACCEPTANCE_MATRIX.md) |
| Contributor editing this vault | [Documentation guide](DOCUMENTATION_GUIDE.md) and [inventory and evidence audit](engineering/DOCUMENTATION_INVENTORY.md) |

Agents start with the [repository operating contract](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/main/AGENTS.md).
Inside a checkout it is at the repository root, beside the `docs/` folder.

## Architecture, API and data

- [Runtime architecture, entry points and persistence](architecture.md)
- [Environmental processing and data contracts](architecture-environmental-data.md)
- [Public reads, review, field reports and exports](architecture-user-and-review-flows.md)
- [API contracts and access roles](api.md)
- [Configuration, modes and credentials](configuration.md)
- [Risk-summary data contract in the repository](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/main/data_contracts/README.md)
- [ADR index and accepted decisions](adr/README.md)

## Product and community

- [Pakistan feature specifications](product/PAKISTAN_FEATURE_ROADMAP.md) and [user needs research](product/PAKISTAN_USER_NEEDS_AND_EVIDENCE.md)
- [Farmer and livestock journeys](product/FARMER_LIVESTOCK_USER_JOURNEYS.md) and [agricultural exposure prerequisites](product/AGRICULTURAL_EXPOSURE_SPECIFICATION.md)
- [UI design and language readiness](product/UI_UX_IMPROVEMENT_PLAN.md)
- [Farmer and livestock QA matrix](product/FARMER_LIVESTOCK_QA_MATRIX.md) and [cross-page acceptance evidence](product/UI_UX_ACCEPTANCE_MATRIX.md)

## Develop, test and operate

- [Local setup](setup.md), [development tasks](development.md), and [contributor guidance](contributing.md)
- [Engineering standards and review checks](engineering/ENGINEERING_STANDARDS.md)
- [Offline testing, workflow checks and validation limits](testing.md)
- [Deployment and database migrations](deployment.md)
- [Troubleshooting](troubleshooting.md)

## Task state, handoffs and known limits

- [Master task plan](engineering/MASTER_TASK_PLAN.md) owns pending, blocked and completed task state.
- [Agent session log](engineering/AGENT_SESSION_LOG.md) records handoffs and checkpoints.
- [Implementation status](engineering/IMPLEMENTATION_STATUS.md) owns the evidence ledger and current limitations.
- [Functionality gap audit](engineering/FUNCTIONALITY_GAP_AUDIT.md) records historical findings and decisions.

An empty event list leaves local conditions unknown. Use official agency
bulletins and local instructions for decisions. The forecasts, SAR demos and
dam estimates are research or prototype features. Independent scientific
validation, browser and accessibility checks, and reviewed Urdu guidance are
tracked in the [master plan](engineering/MASTER_TASK_PLAN.md).
