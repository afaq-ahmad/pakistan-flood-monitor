#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --help || $# -eq 0 ]]; then
  echo 'Usage: agent_resume.sh [--dry-run] <verified-PR-branch>'
  echo 'Inspect an explicitly verified PR branch; fast-forward only in a clean worktree.'
  exit 0
fi
dry=0
if [[ $1 == --dry-run ]]; then dry=1; shift; fi
[[ $# == 1 ]] || { echo 'Specify exactly one verified PR branch.' >&2; exit 2; }
branch=$1
git check-ref-format --branch "$branch" >/dev/null || exit 2
[[ $branch != main && $branch != master ]] || { echo 'Refusing to resume a base branch.' >&2; exit 2; }
[[ -z $(git status --porcelain) ]] || { echo 'Dirty worktree; preserve changes and use a clean worktree.' >&2; exit 2; }
if ((dry)); then echo "Dry run: would fetch origin and safely resume verified branch $branch; no changes made."; exit 0; fi
if ! GIT_TERMINAL_PROMPT=0 git fetch --quiet origin --prune 2>/dev/null; then echo 'Fetch failed; no branch changed.' >&2; exit 3; fi
remote="refs/remotes/origin/$branch"
git show-ref --verify --quiet "$remote" || { echo 'Remote branch not found.' >&2; exit 2; }
if git show-ref --verify --quiet "refs/heads/$branch"; then
  git merge-base --is-ancestor "refs/heads/$branch" "$remote" || { echo 'Local branch is ahead or diverged; reconcile manually.' >&2; exit 2; }
  git switch "$branch"
  git merge --ff-only "$remote"
else
  git switch --track -c "$branch" "origin/$branch"
fi
printf '\nLatest commits:\n'
git log -5 --oneline
printf '\nRead the master plan and latest handoff; confirm PR, CI, review and next task.\n'
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then GH_PROMPT_DISABLED=1 gh pr view "$branch" --json number,state,isDraft,headRefName,baseRefName,url || echo 'PR lookup failed; verify using an authorized integration.' >&2; else echo 'PR status unavailable via gh; verify using an authorized integration.' >&2; fi
