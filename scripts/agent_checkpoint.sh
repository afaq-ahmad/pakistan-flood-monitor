#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --help || $# -eq 0 ]]; then
  echo 'Usage: agent_checkpoint.sh [--dry-run] <expected-branch> <commit-message>'
  echo 'Review and explicitly stage intended files first. No files are staged by this script.'
  exit 0
fi
dry=0
if [[ $1 == --dry-run ]]; then dry=1; shift; fi
[[ $# == 2 && -n $2 ]] || { echo 'Expected a branch and descriptive commit message.' >&2; exit 2; }
branch=$1; message=$2
[[ $(git branch --show-current) == "$branch" && $branch != main && $branch != master && -n $branch ]] || { echo 'Unexpected or protected branch; no changes made.' >&2; exit 2; }
git remote get-url origin >/dev/null 2>&1 || { echo 'Missing origin remote.' >&2; exit 2; }
if git diff --cached --quiet; then echo 'No staged changes; no commit created.'; exit 0; fi
# Path screening is a conservative guard, not a substitute for reviewing staged content.
while IFS= read -r -d '' path; do
  lower=${path,,}
  case "/$lower" in
    */.env|*/.env.*|*/.ssh/*|*/.aws/*|*/.gnupg/*|*/credentials|*/credentials.*|*/id_rsa|*/id_ed25519|*.pem|*.key|*.p12|*.pfx|*.sqlite|*.sqlite3|*.db)
      echo 'Protected or potentially sensitive staged path detected; unstage and review it.' >&2; exit 2;;
  esac
done < <(git diff --cached --name-only -z --diff-filter=ACMR)
if git diff --cached --no-ext-diff --no-color | LC_ALL=C grep -Eiq 'BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}'; then
  echo 'Potential credential material detected; unstage and review privately.' >&2; exit 2
fi
git diff --cached --check
if ((dry)); then echo "Dry run: staged changes passed basic checks; would commit and push branch $branch."; exit 0; fi
# The caller must inspect the staged diff, including content, before invoking this helper.
git commit -m "$message"
sha=$(git rev-parse HEAD)
if ! GIT_TERMINAL_PROMPT=0 git push -u origin "HEAD:refs/heads/$branch" 2>/dev/null; then
  echo "Push failed; local commit $sha is intact. Fetch and reconcile remote history; do not force push." >&2; exit 3
fi
if ! remote=$(GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code origin "refs/heads/$branch" 2>/dev/null); then
  echo "Push returned success but remote verification failed; local commit $sha is intact." >&2; exit 3
fi
remote_sha=${remote%%$'\t'*}
[[ $sha == "$remote_sha" ]] || { echo "Remote head differs from local commit $sha; inspect concurrent updates." >&2; exit 3; }
echo "Verified remote checkpoint: $sha"
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then GH_PROMPT_DISABLED=1 gh pr view "$branch" --json number,state,isDraft,headRefName,baseRefName,url || echo 'PR lookup unavailable; verify separately.' >&2; else echo 'Verify PR status using an authorized GitHub integration.' >&2; fi
