## Problem

<!-- What focused problem does this PR solve? Link the existing task or issue and its acceptance criteria. -->

## Approach

<!-- Summarize the implementation and why it is appropriate. -->

## Changed components

<!-- List affected packages, services, APIs, data contracts, UI surfaces, tests and docs. Link updated owning documentation, diagrams and task evidence, or explain why a documentation update does not apply. -->

## Migrations and configuration

<!-- Describe schema/data migrations, environment variables, config changes, and upgrade/downgrade behavior. Write "None" with a reason when not applicable. -->

## Tests run and results

<!-- Include the base used, exact commands, pass/fail counts and hosted check status. Record pre-existing failures and unverified boundaries separately. -->

## Scientific assumptions and data limitations

<!-- State CRS/units, temporal assumptions, provenance, source limitations, uncertainty, validation coverage, and operational versus simulated status. Write "Not applicable" with a reason only for non-scientific changes. -->

## Screenshots

<!-- For UI changes include before and after evidence, or describe why visual checks are unavailable. Record any unverified browser or accessibility scenarios. -->

## Backward compatibility and rollback

<!-- Describe API/data compatibility and a concrete safe rollback. -->

## Out of scope and follow-up

<!-- Record remaining acceptance work, blockers, rollout limits and the exact next task under the existing task ID. -->

## Self-review checklist

Use the [engineering standards](https://github.com/afaq-ahmad/pakistan-flood-monitor/blob/main/docs/engineering/ENGINEERING_STANDARDS.md#review-before-requesting-acceptance) for the evidence behind these checks.

- [ ] Scope is limited to the requested task; no unrelated refactor is included.
- [ ] Canonical architecture and applicable ADRs are respected.
- [ ] Operational code does not invent environmental observations; unavailable/degraded states and provenance are preserved.
- [ ] CRS, units, timezones, uncertainty, and scientific terminology were reviewed where relevant.
- [ ] Observation, forecast, exposure, estimated impact, and verified damage remain distinct.
- [ ] No machine score automatically publishes an emergency warning or insurance payout decision.
- [ ] Tests and documentation cover every behavior change, and repository checks were run.
- [ ] Security/privacy, failure modes, performance, compatibility, and rollback were reviewed.
- [ ] UI and API contracts agree, and affected architecture documentation and diagrams were reviewed.
