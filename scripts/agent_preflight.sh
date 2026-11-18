#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --help ]]; then
  echo 'Usage: agent_preflight.sh [--dry-run] [workstream-search]'
  echo 'Inspect state and open PRs; fetch metadata unless --dry-run. Never switches branches.'
  exit 0
fi
dry=0
if [[ ${1:-} == --dry-run ]]; then dry=1; shift; fi
query=${1:-}
git rev-parse --show-toplevel >/dev/null || { echo 'Not a Git repository.' >&2; exit 2; }
echo "Repository root: $(git rev-parse --show-toplevel)"
echo "Branch: $(git branch --show-current)"
echo "HEAD: $(git rev-parse HEAD)"
echo "Upstream: $(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo none)"
echo 'Working tree (including untracked paths):'
git status --short
if ! git remote get-url origin >/dev/null 2>&1; then echo 'Missing origin remote.' >&2; exit 2; fi
if ((dry)); then echo 'Dry run: would fetch origin --prune.'; else
  if ! GIT_TERMINAL_PROMPT=0 git fetch --quiet origin --prune 2>/dev/null; then
    echo 'Fetch failed; check connectivity and authorization; local files were preserved.' >&2; exit 3
  fi
fi
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  echo 'Open PRs (inspect details, comments and checks before choosing one):'
  if ! GH_PROMPT_DISABLED=1 gh pr list --state open --search "$query" --json number,title,headRefName,baseRefName,isDraft,url; then
    echo 'Could not inspect PRs. Do not assume no PR exists.' >&2; exit 3
  fi
else
  echo 'GitHub CLI authentication unavailable; use an authorized integration to inspect PRs.' >&2
fi
echo 'Read AGENTS.md, docs/engineering/{AGENT_GITHUB_WORKFLOW,MASTER_TASK_PLAN,AGENT_SESSION_LOG,IMPLEMENTATION_STATUS}.md.'
echo 'Confirm repository identity, PR ownership and remote divergence before editing.'
