import subprocess

import pytest

from scripts.check_docs import (
    INDEX,
    PLAN,
    check_diff,
    check_documents,
    check_tasks,
    local_links,
    markdown_anchors,
    read_frontmatter,
    split_markdown,
)


def test_markdown_links_anchors_and_mermaid_fences():
    document = """# Linked heading
## A · date
## A · date
[Local](../setup.md#a%20date) and [external](https://example.test).
[With title](<local folder/start.md> "Start")
[Reference]: ../testing.md
`[Example](ignored-inline.md)`
````python
```
[Example](ignored-fence.md)
```
````
~~~mermaid
flowchart TD
    Start --> Finish
~~~
"""
    body, diagrams, open_fence = split_markdown(document)
    assert list(local_links(body)) == [
        ("../setup.md", "a date"), ("local folder/start.md", ""), ("../testing.md", ""),
    ]
    assert markdown_anchors(body) == {"linked-heading", "a--date", "a--date-1"}
    assert diagrams == [["flowchart TD", "    Start --> Finish"]]
    assert not open_fence
    assert split_markdown("```mermaid\nflowchart TD")[2]


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        ("", "required YAML frontmatter is missing"),
        ("---\nstatus: [unclosed\n---\n", "invalid YAML frontmatter"),
        ("---\nstatus: verified\n---\n", "invalid or missing frontmatter field status"),
        ("---\nverified_at: soon\n---\n", "verified_at must be an ISO date"),
    ],
)
def test_frontmatter_errors(frontmatter, expected):
    _, errors = read_frontmatter(frontmatter + "# Heading\n", required=True)
    assert expected in errors


def test_backlog_rejects_duplicate_status_and_missing_navigation():
    body = """# Plan
## Pending Work
[ENG-001](#eng-001--first)
## ENG-001 — First
- **Priority** P2 · **Status** `PARTIAL` · **Workstream** Docs
## ENG-001 — Second
- **Priority** P2 · **Status** `DONE` · **Workstream** Docs
## OPS-001 — Deployment
- **Priority** P1 · **Status** `BLOCKED` · **Workstream** Operations
"""
    errors = []
    assert check_tasks(body, markdown_anchors(body), errors) == 2
    assert f"{PLAN}: duplicate authoritative task ID ENG-001" in errors
    assert f"{PLAN}: ENG-001 needs exactly one valid task status" in errors
    assert f"{PLAN}: OPS-001 is absent from Pending Work" in errors
    assert f"{PLAN}: OPS-001 is missing the Next action field" in errors


def test_missing_documents_links_anchors_and_mermaid_headers(tmp_path):
    page = tmp_path / INDEX
    page.parent.mkdir()
    page.write_text(
        "# Entry\n[Gone](gone.md)\n[Anchor](#missing)\n"
        "```mermaid\ninvalid header\n    Start --> Finish\n```\n",
        encoding="utf-8",
    )

    errors, links, tasks, diagrams = check_documents(tmp_path, [INDEX])

    assert (links, tasks, diagrams) == (2, 0, 1)
    assert f"{PLAN}: required document is missing" in errors
    assert f"{INDEX}: unresolved local link gone.md" in errors
    assert f"{INDEX}: missing anchor {INDEX}#missing" in errors
    assert f"{INDEX}: missing required entry link to {PLAN}#pending-work" in errors
    assert f"{INDEX}: Mermaid block 1 needs a supported header and body" in errors


def test_staged_guard_reports_path_and_redacts_token(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    token = "ghp_" + "x" * 30
    (tmp_path / "notes.md").write_text(token, encoding="utf-8")
    (tmp_path / ".env").write_text("DUMMY=1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".env", "notes.md"], check=True)
    before = (tmp_path / "notes.md").read_bytes()
    errors = check_diff(tmp_path, ["--cached"])
    assert errors == [".env: protected path changed", "Git diff: possible secret in an added line"]
    assert token not in " ".join(errors)
    assert (tmp_path / "notes.md").read_bytes() == before
