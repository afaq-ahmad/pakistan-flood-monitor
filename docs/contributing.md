# Contributing to Pakistan Flood Monitor

1. Use [local setup](setup.md) for the tested Python environment and install
   steps. Check the [master task plan](engineering/MASTER_TASK_PLAN.md) and
   active PRs for ownership. Resume a suitable workstream or branch from
   current `main`. Agents start with root `AGENTS.md` and follow the
   [agent GitHub workflow](engineering/AGENT_GITHUB_WORKFLOW.md).
2. Follow the [engineering standards](engineering/ENGINEERING_STANDARDS.md)
   for code placement, failure handling and self-review. Keep the diff
   focused. Add deterministic checks for changed behavior and record
   exact commands and results from [offline testing](testing.md).
3. Open a focused draft PR with the repository template. Request human
   review when the acceptance checks are met.
4. Update the owning page according to the [documentation guide](DOCUMENTATION_GUIDE.md).
   If the PR changes an architecture
   contract, API boundary, workflow transition, scientific-data semantics
   or storage responsibility, review the affected documentation and
   Mermaid diagrams. Link any updated sections in the PR.

When contributing corridor or dam data, cite the authoritative source and
verification date. Distinguish the canonical corridor catalogue in
`src/pakistan_flood_monitor/config.py` from research geometry in
`satellite_ml_service.py` and the prototype dam data in
`src/pakistan_flood_monitor/services/dam_service.py`. See
[architecture](architecture.md) for scope and decision boundaries.
