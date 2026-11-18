# Local development workflow

Start with [local setup](setup.md). Find the supported entry points and
storage boundaries in [runtime architecture](architecture.md).

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

Extend `src/pakistan_flood_monitor/`. Treat `src/app/` as a migration source.
Check [ADR-001](adr/ADR-001-canonical-runtime.md), existing contracts and
callers before changing data or persistence. Apply schema changes through the
canonical Alembic chain. Add tests that preserve published-data eligibility,
role checks, provenance, scientific units and failure states as applicable.

## Validate and document

Use the [offline checks](testing.md) for the affected layer. Update the owning
contract or how-to as described in the [documentation guide](DOCUMENTATION_GUIDE.md).
For PR and agent checkpoint expectations, see [contributing](contributing.md)
and the [agent workflow](engineering/AGENT_GITHUB_WORKFLOW.md).
