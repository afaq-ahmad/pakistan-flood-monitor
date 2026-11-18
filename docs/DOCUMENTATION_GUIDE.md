# Documentation guide

Open [the documentation homepage](INDEX.md) first. The checked-in `docs/`
folder is the shared Obsidian vault. In Obsidian's vault switcher, select
**Open folder as vault**, choose the checkout's `docs/` folder, then open
`INDEX.md`. Edit these same files when contributing documentation, and keep
personal `.obsidian/` settings, plugin caches and private notes out of commits.
See [Obsidian's vault instructions](https://obsidian.md/help/vault).

## Choose the document by reader need

| Reader need | Form | Existing home |
|---|---|---|
| Complete a first working example | Tutorial | [Local setup](setup.md) |
| Do a particular task | How-to | [Development](development.md), [deployment](deployment.md), [testing](testing.md) and [troubleshooting](troubleshooting.md) |
| Check a contract, option or interface | Reference | [API](api.md), [configuration](configuration.md), task state or QA matrix |
| Understand why the system works this way | Explanation | [Architecture](architecture.md), ADRs or product research |

Update the document that already answers the question. Add a page when it
supports a distinct task or audience and link it from its nearest topic in
the [index](INDEX.md). Preserve paths when consolidating. Label historical
material with its cutoff and link to the current authority. The
[inventory](engineering/DOCUMENTATION_INVENTORY.md) records classifications
and baseline evidence. See [Diátaxis](https://diataxis.fr/).

## Ownership

| Information | Authoritative location |
|---|---|
| Operating requirements for agents | Repository-root `AGENTS.md` and [agent GitHub workflow](engineering/AGENT_GITHUB_WORKFLOW.md) |
| Engineering and code review standards | [Engineering standards](engineering/ENGINEERING_STANDARDS.md) |
| Open, blocked and completed task state | [Master task plan](engineering/MASTER_TASK_PLAN.md) |
| Checkpoint and recovery context | [Session handoff log](engineering/AGENT_SESSION_LOG.md) |
| Actual implementation coverage and validation gaps | [Implementation ledger](engineering/IMPLEMENTATION_STATUS.md), verified against code and test evidence |
| Accepted architectural decisions | [ADR index](adr/README.md). Supersede a decision through a new ADR. |
| Pakistan feature specifications | [Product roadmap](product/PAKISTAN_FEATURE_ROADMAP.md) |
| Acceptance scenarios and dated QA evidence | [UX acceptance matrix](product/UI_UX_ACCEPTANCE_MATRIX.md) and [rural journey QA](product/FARMER_LIVESTOCK_QA_MATRIX.md) |

## Author, link and verify

1. Give each authored page one H1, focused headings, short paragraphs and
   language names on code fences. Use a table when it helps readers compare
   equivalent information.
2. Use relative Markdown links for notes inside `docs/`. Use descriptive
   labels and forward slashes. For paths with spaces, use URL encoding or
   enclose the link destination in angle brackets. Link to a file if the heading
   fragment renders differently between readers. For a target outside the
   vault, give its repository path or a GitHub URL that also works from
   Obsidian. Pin links to a commit when citing historical code.
3. Put Mermaid in a fenced `mermaid` block. Use simple labels and a short
   diagram per flow. Put evidence and caveats in surrounding prose. Check
   syntax and open previews in GitHub and Obsidian when available. Keep a
   prose explanation for readers who cannot see the diagram.
4. Use simple optional YAML properties such as `title`, `doc_type`,
   `status`, `owner`, `verified_at` and `tags`. Set a verification date
   only after checking the stated scope. Qualify drafts, proposals, missing
   measurements and historical observations in prose too.
5. Verify paths and heading anchors from the document's directory. Validate
   navigation from the index and check cited code at the stated revision.
   Spot-check external references that support changed claims. Record what
   you ran, the result, and any rendering or environment limits in the PR.
6. Run the [offline documentation checks](testing.md#documentation-checks).
   Verify the preview in GitHub and Obsidian for changes that affect layout
   or diagrams. Record manual checks that were unavailable.

## Keep documentation current

Update the owning documentation in the same PR whenever a change affects
public behavior, API contracts, runtime configuration, architecture,
database schema, scientific semantics, data-provider assumptions,
publication or authorization, user workflows, deployment, or completion
evidence. Update the relevant diagrams and examples along with prose.
Record the test environment and exact evidence under the task and handoff.
If the change needs no documentation update, give the reason in the PR.
Use the affected reference, tutorial or QA record rather than editing an
unrelated landing page.

The [master plan](engineering/MASTER_TASK_PLAN.md#pending-work) owns task
priority, status, acceptance and next action. Remaining Work links to it.
The implementation ledger and product QA documents preserve dated
evidence. The roadmap keeps specifications and dependencies. Append
verified handoffs and supersede accepted ADRs through a new ADR.

References for [Obsidian Markdown links](https://obsidian.md/help/links) and
[GitHub Mermaid diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).
