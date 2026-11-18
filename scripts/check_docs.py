"""Check the repository's Markdown conventions and an optional Git diff offline."""

import argparse
from collections import Counter
from datetime import date
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


PLAN = Path("docs/engineering/MASTER_TASK_PLAN.md")
PENDING = f"{PLAN}#pending-work"
INDEX = Path("docs/INDEX.md")
ENTRIES = {
    INDEX: {
        PENDING, "docs/setup.md", "docs/architecture.md", "docs/adr/README.md",
        "docs/engineering/AGENT_GITHUB_WORKFLOW.md", "docs/engineering/AGENT_SESSION_LOG.md",
        "docs/engineering/IMPLEMENTATION_STATUS.md", "docs/testing.md",
    },
    Path("AGENTS.md"): {
        f"{PLAN}", "docs/engineering/AGENT_GITHUB_WORKFLOW.md#start-or-resume",
        "docs/adr/README.md",
    },
    Path("docs/engineering/REMAINING_WORK.md"): {PENDING},
    Path("docs/adr/README.md"): {"docs/adr/ADR-001-canonical-runtime.md"},
}
REQUIRED = {PLAN, *ENTRIES, Path("docs/DOCUMENTATION_GUIDE.md")} | {
    Path(destination.split("#", 1)[0])
    for destinations in ENTRIES.values()
    for destination in destinations
}
METADATA_VALUES = {
    "doc_type": {"tutorial", "how-to", "reference", "explanation"},
    "status": {"current", "baseline", "draft", "historical", "superseded"},
}
STATUSES = {"NOT_STARTED", "IN_PROGRESS", "PARTIAL", "BLOCKED", "COMPLETE"}
TASK_ID = r"[A-Z][A-Z0-9]*-\d{3}"
TASK = re.compile(rf"^#{{2,3}} ({TASK_ID}) — .+$", re.M)
TASK_FIELDS = {"Impact and requirement", "Current behavior", "Code", "Dependencies and blockers",
               "Acceptance", "Evidence", "Next action"}
STATUS = re.compile(r"^- \*\*Priority\*\* .+? · \*\*Status\*\* `([^`]+)` · \*\*Workstream\*\* .+$", re.M)
HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)\s*#*\s*$", re.M)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*(.*)$")
LINK = re.compile(r'(?<!\\)\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s()]+))(?=\s|\))')
REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|([^\s()]+))", re.M)
DIAGRAM_HEADER = re.compile(
    r"(?:(?:flowchart|graph)\s+(?:TB|TD|BT|RL|LR)|sequenceDiagram|stateDiagram(?:-v2)?)"
)
PROTECTED_PATH = re.compile(
    r"(^|/)(?:\.env(?:\.[^/]+)?|credentials(?:\.[^/]+)?|id_(?:rsa|ed25519))$"
    r"|(^|/)\.(?:ssh|aws|gnupg)/|\.(?:db|sqlite3?|pem|key|p12|pfx)$", re.I,
)
SECRET = re.compile(
    r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY|\bgh[pousr]_[A-Za-z0-9_]{20,}"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}|\bAKIA[A-Z0-9]{16}\b",
)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8")


def split_markdown(text):
    """Return prose outside fenced code, Mermaid bodies, and open-fence flag."""
    prose, diagrams = [], []
    marker = None
    diagram = None
    for line in text.splitlines():
        fence = FENCE.match(line)
        if marker is None:
            if not fence:
                prose.append(line)
                continue
            marker, info = fence.groups()
            if info == "mermaid":
                diagram = []
            prose.append("")
        elif fence and fence[1][0] == marker[0] and len(fence[1]) >= len(marker) and not fence[2].strip():
            if diagram is not None:
                diagrams.append(diagram)
            marker = diagram = None
        elif diagram is not None:
            diagram.append(line)
    return "\n".join(prose), diagrams, marker is not None


def read_frontmatter(text, *, required):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, ["required YAML frontmatter is missing"] if required else []
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return text, ["YAML frontmatter is missing its closing delimiter"]
    body = "".join(lines[end + 1:])
    try:
        fields = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError:
        return body, ["invalid YAML frontmatter"]
    if not isinstance(fields, dict):
        return body, ["YAML frontmatter must be a mapping"]
    errors = []
    for key, allowed in METADATA_VALUES.items():
        value = fields.get(key)
        if (required or key in fields) and (not isinstance(value, str) or value not in allowed):
            errors.append(f"invalid or missing frontmatter field {key}")
    for key in ("title", "owner"):
        value = fields.get(key)
        if (required or key in fields) and (not isinstance(value, str) or not value.strip()):
            errors.append(f"invalid or missing frontmatter field {key}")
    if (required or "verified_at" in fields) and type(fields.get("verified_at")) is not date:
        errors.append("verified_at must be an ISO date")
    return body, errors


def heading_anchor(title):
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title).replace("**", "").replace("__", "")
    return "".join(
        char for char in plain.lower()
        if char in " _-" or unicodedata.category(char)[0] in "LMN"
    ).replace(" ", "-")


def markdown_anchors(body):
    used = set()
    for heading in HEADING.findall(body):
        anchor = heading_anchor(heading)
        unique, suffix = anchor, 0
        while unique in used:
            suffix += 1
            unique = f"{anchor}-{suffix}"
        used.add(unique)
    return used


def local_links(body):
    prose = re.sub(r"`+[^`\n]*`+", "", body)
    for links in (LINK, REFERENCE):
        for angle, bare in links.findall(prose):
            href = angle or bare
            try:
                destination = urlsplit(href)
            except ValueError:
                yield "<invalid URL>", ""
                continue
            if not (destination.scheme or destination.netloc):
                yield unquote(destination.path), unquote(destination.fragment)


def check_tasks(body, anchors, errors):
    records = list(TASK.finditer(body))
    if not records or "pending-work" not in anchors:
        errors.append(f"{PLAN}: missing task records or Pending Work section")
    counts = Counter(record[1] for record in records)
    pending = re.split(r"^## Pending Work[^\S\n]*$", body, maxsplit=1, flags=re.M)[-1]
    pending = re.split(r"^## ", pending, maxsplit=1, flags=re.M)[0]
    indexed = {anchor for target, anchor in local_links(pending) if not target}
    for index, record in enumerate(records):
        end = records[index + 1].start() if index + 1 < len(records) else len(body)
        section = body[record.end():end]
        statuses = STATUS.findall(section)
        if len(statuses) != 1 or statuses[0] not in STATUSES:
            errors.append(f"{PLAN}: {record[1]} needs exactly one valid task status")
        elif statuses[0] != "COMPLETE" and heading_anchor(record[0].split(" ", 1)[1]) not in indexed:
            errors.append(f"{PLAN}: {record[1]} is absent from Pending Work")
        fields = set(re.findall(r"^- \*\*([^*]+)\*\* .+", section, re.M))
        for field in sorted(TASK_FIELDS - fields):
            errors.append(f"{PLAN}: {record[1]} is missing the {field} field")
    for task, count in counts.items():
        if count > 1:
            errors.append(f"{PLAN}: duplicate authoritative task ID {task}")
    return len(counts)


def check_documents(root, paths):
    errors = [f"{path}: required document is missing" for path in sorted(REQUIRED - set(paths))]
    documents, anchors = {}, {}
    diagrams = 0
    for path in paths:
        if not (root / path).is_file():
            errors.append(f"{path}: tracked document is missing")
            continue
        text = (root / path).read_text(encoding="utf-8")
        body, metadata_errors = read_frontmatter(text, required=path == INDEX)
        body, blocks, unclosed = split_markdown(body)
        documents[path] = body
        anchors[path] = markdown_anchors(body)
        errors.extend(f"{path}: {error}" for error in metadata_errors)
        if unclosed:
            errors.append(f"{path}: unclosed code fence")
        for index, lines in enumerate(blocks, 1):
            meaningful = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("%%")]
            if len(meaningful) < 2 or not DIAGRAM_HEADER.fullmatch(meaningful[0]):
                errors.append(f"{path}: Mermaid block {index} needs a supported header and body")
            diagrams += 1

    links = 0
    for path, body in documents.items():
        destinations = set()
        for target, anchor in local_links(body):
            if SECRET.search(f"{target}#{anchor}"):
                errors.append(f"{path}: possible secret in a local link")
                continue
            resolved = (root / path.parent / target if target else root / path).resolve()
            links += 1
            if not resolved.is_relative_to(root) or not resolved.exists():
                errors.append(f"{path}: unresolved local link {target}")
                continue
            destination = resolved.relative_to(root)
            if anchor and resolved.suffix.lower() == ".md" and anchor not in anchors.get(destination, set()):
                errors.append(f"{path}: missing anchor {destination}#{anchor}")
            destinations.add(f"{destination}#{anchor}" if anchor else str(destination))
        for destination in sorted(ENTRIES.get(path, set()) - destinations):
            errors.append(f"{path}: missing required entry link to {destination}")
    tasks = check_tasks(documents.get(PLAN, ""), anchors.get(PLAN, set()), errors)
    return errors, links, tasks, diagrams


def check_diff(root, revision):
    errors = []
    paths = git(root, "diff", "--name-only", "-z", "--diff-filter=ACMRT", *revision, "--").split("\0")
    for path in filter(None, paths):
        if PROTECTED_PATH.search(path) and Path(path).name != ".env.example":
            errors.append(f"{path}: protected path changed")
    diff = git(root, "diff", "--no-ext-diff", "--no-color", "--unified=0", *revision, "--")
    # Never print a matched value, which could be a real credential.
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++ ") and SECRET.search(line[1:]):
            errors.append("Git diff: possible secret in an added line")
            break
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--base", help="Check the committed changes from this revision through HEAD")
    scope.add_argument("--staged", action="store_true", help="Check the staged paths and added lines")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    paths = {Path(path) for path in git(root, "ls-files", "-z", "--", "*.md").split("\0") if path}
    errors, links, tasks, diagrams = check_documents(root, sorted(paths))
    if args.base:
        base = git(root, "rev-parse", "--verify", "--end-of-options", f"{args.base}^{{commit}}").strip()
        errors.extend(check_diff(root, [f"{base}..HEAD"]))
    elif args.staged:
        errors.extend(check_diff(root, ["--cached"]))
    for error in errors:
        print(error)
    print(f"Checked {len(paths)} Markdown files, {links} local links, {tasks} task IDs "
          f"and {diagrams} Mermaid fences. {len(errors)} errors.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
