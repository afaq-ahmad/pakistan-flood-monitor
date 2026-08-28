## Problem

<!-- What focused problem does this PR solve? Link the task/issue when available. -->

## Approach

<!-- Summarize the implementation and why it is appropriate. -->

## Changed components

<!-- List affected packages, services, APIs, data contracts, UI surfaces, tests, and docs. -->

## Migrations and configuration

<!-- Describe schema/data migrations, environment variables, config changes, and upgrade/downgrade behavior. Write "None" with a reason when not applicable. -->

## Tests run and results

<!-- Include exact commands and pass/fail counts. Identify pre-existing failures separately. -->

## Scientific assumptions and data limitations

<!-- State CRS/units, temporal assumptions, provenance, source limitations, uncertainty, validation coverage, and operational versus simulated status. Write "Not applicable" with a reason only for non-scientific changes. -->

## Screenshots

<!-- Required for UI changes. Otherwise write "Not applicable — no UI change." -->

## Backward compatibility and rollback

<!-- Describe API/data compatibility and a concrete safe rollback. -->

## Out of scope and follow-up

<!-- State what was intentionally not changed. Do not silently begin the next roadmap task. -->

## Self-review checklist

- [ ] Scope is limited to the requested task; no unrelated refactor is included.
- [ ] Canonical architecture and applicable ADRs are respected.
- [ ] Operational code does not invent environmental observations; unavailable/degraded states and provenance are preserved.
- [ ] CRS, units, timezones, uncertainty, and scientific terminology were reviewed where relevant.
- [ ] Observation, forecast, exposure, estimated impact, and verified damage remain distinct.
- [ ] No machine score automatically publishes an emergency warning or insurance payout decision.
- [ ] Tests and documentation cover every behavior change, and repository checks were run.
- [ ] Security/privacy, failure modes, performance, compatibility, and rollback were reviewed.
