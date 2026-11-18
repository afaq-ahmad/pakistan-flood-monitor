# Resumable GitHub workflow for coding agents

Status: IN PROGRESS. This guide governs repository-connected agents alongside AGENTS.md.
The master task plan is the authoritative checklist; the session log is the handoff.
User instructions and repository safety rules take precedence. Do not merge automatically.

## Start or resume

1. Verify repository identity, branch, HEAD, status, untracked files, upstream and remote
   without printing URLs that might contain credentials. Never discard a dirty workspace.
2. Fetch remote metadata. Inspect open PRs for the assigned workstream; read the PR description,
   branch, base, commits, changes, reviews and checks. Reuse its branch only if appropriate.
   Closed or merged PRs are not automatically reused. If access is unavailable, report the
   limitation; do not assume there is no PR. Never expose authentication values.
3. Recover the latest PR branch with a clean workspace and fast-forward only. Stop on divergence,
   ambiguous ownership, conflicts, or uncommitted changes; preserve work and coordinate.
4. Read AGENTS.md, this guide, MASTER_TASK_PLAN.md, AGENT_SESSION_LOG.md,
   IMPLEMENTATION_STATUS.md and relevant ADRs. Reconcile the claims against code, remote
   commits and tests. Run an appropriate baseline smoke check.
5. Select one eligible task by ID, checking dependencies, ownership and prior changes. Agree an
   integration owner before multiple agents touch a shared branch. Markdown ownership is advisory,
   not a distributed lock. Other agents use isolated branches/worktrees and avoid conflicting files.

## Small, durable checkpoints

Break the approved workstream into small reviewable units. After approximately 60–120 seconds of
meaningful editing, or a coherent subtask, whichever comes first: inspect the diff, run an appropriate
lightweight check, record the actual status and exact next action in the existing handoff, stage
only intended files, inspect the staged diff and `git diff --cached --check`, commit and push.
Aim to avoid five minutes of unpushed useful work. Do not interrupt an atomic change to meet a
timer; do not create artificial or empty commits. Tests or syntax checks may fail on a necessary
WIP checkpoint; clearly record the failure and keep the PR draft. Never mark unverified work done.

Before staging, review paths and contents for secrets, credentials, private data, generated
databases and unrelated changes. Never use indiscriminate staging in a shared workspace. A script
cannot guarantee secret detection; manual review and approved scanners remain necessary. Use only
authorized credentials and never print them.

After every checkpoint, push a normal fast-forward to the assigned branch and compare local HEAD to
the actual remote branch head (for example `git ls-remote origin refs/heads/<branch>`). A local
commit or attempted push alone is not a durable checkpoint. Check the open PR head/base and draft
state; inspect CI and review feedback at milestones. Never force-push or rewrite published commits.
If the push or authentication fails, preserve the commit, report the exact failure without secrets,
and reconcile remote history before retrying. If remote history has diverged, stop and coordinate.

Create one draft PR to main immediately after the first meaningful pushed checkpoint if no suitable
PR exists. Use the existing template; summarize task ID, scope, milestones, tests, limitations and
next action. Continue pushing the same branch; do not create a duplicate PR after a reset. Update
the PR description at milestones. If a user or higher-priority instruction prohibits a PR, honor it.
If the PR is closed or merged, reassess the workstream before opening another.

## Failures, completion and handoff

Investigate test failures and distinguish pre-existing, environmental, WIP and new regressions.
Never claim a test passed without running it. Run full applicable checks before human review.
Mark a subtask complete only with evidence, preserving all other backlog items. Keep the PR draft
until acceptance criteria are met. Report blockers and unverified scenarios rather than inventing
requirements. Do not change production data, deploy or merge unless separately authorized.

Append compact entries to AGENT_SESSION_LOG.md: UTC time, repository, workstream, branch and PR,
base and last verified remote SHA, task ID/status, completed and pending work, changed files, exact
test results, failures/blockers, worktree/unpushed status and next action. A commit cannot contain
its own SHA; record the preceding verified remote SHA and verify the new SHA after pushing. On
interruption recover from GitHub commits, PR and tracked plan even if a handoff is missing.

At completion inspect the cumulative diff, run applicable tests and security checks, document
limitations and rollback, and request human review. Close a workstream only after its agreed
acceptance; select a new one only when authorized, following AGENTS.md.

References: [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow),
[GitHub draft PRs](https://docs.github.com/en/pull-requests/reference/pull-requests),
and [OpenAI's multi-hour execution plans](https://developers.openai.com/cookbook/articles/codex_exec_plans).
