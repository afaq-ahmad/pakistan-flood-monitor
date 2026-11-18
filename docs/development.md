# Local development workflow

Start with [local setup](setup.md) for editable installation, or
[deployment](deployment.md) for the Compose commands. From the repository
root, use the canonical FastAPI command and the Streamlit entry point
shown in setup. The [runtime architecture](architecture.md) maps their
storage and provider boundaries.

Use the package extras declared in `pyproject.toml`. The `dev` extra
adds pytest and `dashboard` supplies Streamlit, Folium, the Streamlit
Folium integration and Plotly. Use both for local CI parity. Install
`ml`, `dl` or `workflow` only when the affected feature requires it.
[Testing](testing.md) owns the separate offline test guard.

For a clean install or packaging check, use a disposable checkout and
environment. Editable installs can rewrite the currently tracked
`src/pakistan_flood_monitor.egg-info/` files. Inspect that diff and
exclude generated metadata from ordinary changes. Packaging follow-up
is tracked in [OPS-001](engineering/MASTER_TASK_PLAN.md#ops-001--deployment-and-operational-verification).

## Change a Streamlit page

1. Read the existing page and its AppTest. Keep public routes usable when a
   source is unavailable or no eligible events are published.
2. For a new route, register its file with `st.navigation` in
   `streamlit_app.py` under the appropriate group. Preserve existing URL paths
   when changing menu labels. The registry determines the routes.
3. Use the shared public status presentation for Home and My Area where the
   same contract applies. Keep authentication in the handler and API.
4. Add deterministic component tests for the affected mode, data and empty or
   failure paths. See the [UX acceptance matrix](product/UI_UX_ACCEPTANCE_MATRIX.md).

## Change the canonical backend

Use the [engineering standards](engineering/ENGINEERING_STANDARDS.md) to
identify the canonical owner and interfaces before editing. Check
[ADR-001](adr/ADR-001-canonical-runtime.md) for applicable architecture
and safety constraints. Use the [canonical migration chain](deployment.md#migrate-the-canonical-database)
for schema changes and the [API reference](api.md) for contracts.

## Validate and document

Use the [offline checks](testing.md) for the affected layer. Update the owning
contract or how-to as described in the [documentation guide](DOCUMENTATION_GUIDE.md).
For PR and agent checkpoint expectations, see [contributing](contributing.md)
and the [agent workflow](engineering/AGENT_GITHUB_WORKFLOW.md).
