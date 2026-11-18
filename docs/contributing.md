# Contributing to Pakistan Flood Monitor

1. Use [local setup](setup.md) for the tested Python environment and install
   steps. Create a focused branch from current `main`.
2. Check the [master task plan](engineering/MASTER_TASK_PLAN.md) for related
   work. Agents must also read the repository-root `AGENTS.md`, the
   [agent workflow](engineering/AGENT_GITHUB_WORKFLOW.md), [implementation status](engineering/IMPLEMENTATION_STATUS.md)
   and [accepted decisions](adr/README.md).
3. Keep changes focused and add deterministic checks for changed behavior.
   Use [offline testing](testing.md) and record exact commands and results.
4. Update the owning page according to the [documentation guide](DOCUMENTATION_GUIDE.md).
   Submit a PR describing scope, evidence, limitations and any follow-up.
   Use the repository PR template.

When contributing corridor or dam data, cite the authoritative source and
verification date. Distinguish the canonical corridor catalogue in
`src/pakistan_flood_monitor/config.py` from research geometry in
`satellite_ml_service.py` and the prototype dam data in
`src/pakistan_flood_monitor/services/dam_service.py`. See
[architecture](architecture.md) for scope and decision boundaries.
