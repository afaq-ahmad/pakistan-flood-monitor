import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _normalized_markdown(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


def test_repository_agent_contract_covers_non_negotiable_safeguards() -> None:
    contract = _normalized_markdown(REPOSITORY_ROOT / "AGENTS.md")

    required_clauses = {
        "canonical package": "`src/pakistan_flood_monitor/` is the canonical",
        "legacy migration source": "treat `src/app/` as a migration source",
        "no third tree": "never create a third parallel implementation tree",
        "implementation ledger": "`docs/engineering/implementation_status.md`",
        "runtime modes": "exactly three safety modes: `test`, `demo`, and `operational`",
        "no fabricated observations": "never fabricate an environmental observation in operational code",
        "synthetic fixture boundary": "synthetic data may exist only in explicit automated-test or demo fixtures",
        "typed unavailable state": "typed `unavailable` or `degraded` states",
        "typed stale state": "typed `stale` state",
        "EPSG:4326 metric prohibition": "never interpret degrees or epsg:4326 planar results as metres",
        "provenance source": "source/provider and stable source uri",
        "provenance acquisition time": "acquisition/valid time",
        "provenance processing time": "processing time, expressed as timezone-aware utc",
        "provenance versions": "configuration, model, threshold, and reference-dataset versions",
        "quality and uncertainty": "quality/availability status, validation result, known limitations, and uncertainty",
        "concept separation": "public observation, forecast, model inference, exposure, estimated impact, verified damage, and warning",
        "ADR policy": "`docs/adr/adr-template.md`",
        "human warning gate": "never automatically publish an emergency warning",
        "human payout gate": "payout decision from a machine score",
        "free and open default": "prefer free/open data sources and open-source libraries",
        "no required paid API": "do not make a paid api",
        "tests for changes": "add or update tests for every behavior change",
        "scientific PR limitations": "scientific assumptions and data limitations",
        "rollback notes": "rollback notes",
        "stop at task boundary": "do not start the next task",
    }

    missing = [name for name, clause in required_clauses.items() if clause not in contract]
    assert not missing, f"AGENTS.md is missing required safeguards: {', '.join(missing)}"


def test_pull_request_template_requires_evidence_and_scientific_review() -> None:
    template = _normalized_markdown(REPOSITORY_ROOT / ".github" / "pull_request_template.md")

    required_sections = (
        "## problem",
        "## approach",
        "## changed components",
        "## migrations and configuration",
        "## tests run and results",
        "## scientific assumptions and data limitations",
        "## screenshots",
        "## backward compatibility and rollback",
        "## out of scope and follow-up",
        "## self-review checklist",
    )
    missing = [section for section in required_sections if section not in template]
    assert not missing, f"PR template is missing required sections: {', '.join(missing)}"


def test_implementation_ledger_tracks_repository_context_and_all_prompts() -> None:
    path = REPOSITORY_ROOT / "docs" / "engineering" / "IMPLEMENTATION_STATUS.md"
    ledger = _normalized_markdown(path)

    required_context = {
        "canonical package": "`src/pakistan_flood_monitor/`",
        "accepted ADR": "adr-001: canonical runtime and operational data integrity",
        "runtime modes": "`test`, `demo`, `operational`",
        "canonical schema head": "`f46f1d9e187b`",
        "legacy schema head": "`0005_add_lineage_metadata_to_provenance`",
        "limitations": "## current limitations and deprecated work",
        "defects": "## known p0/p1 defects",
        "test status": "## test and validation status",
        "next prompt": "## next recommended prompt",
    }
    missing = [name for name, clause in required_context.items() if clause not in ledger]
    assert not missing, f"Implementation ledger is missing context: {', '.join(missing)}"

    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*(\d{2})\s*\|\s*([A-Z_]+)\s*\|", line)
        if match:
            rows[match.group(1)] = match.group(2)

    assert rows.get("00") == "COMPLETE"
    assert set(rows) == {f"{number:02d}" for number in range(16)}
    allowed = {"NOT_STARTED", "IN_PROGRESS", "PARTIAL", "BLOCKED", "COMPLETE"}
    assert set(rows.values()) <= allowed


def test_adr_template_and_new_local_links_are_valid() -> None:
    template_path = REPOSITORY_ROOT / "docs" / "adr" / "ADR-TEMPLATE.md"
    template = _normalized_markdown(template_path)
    required_sections = (
        "**status:** proposed",
        "## context",
        "## decision drivers",
        "## considered options",
        "## decision",
        "## consequences",
        "## compatibility, migration, and rollback",
        "## validation and acceptance evidence",
        "## unresolved questions",
    )
    missing = [section for section in required_sections if section not in template]
    assert not missing, f"ADR template is missing required sections: {', '.join(missing)}"

    documents = (
        REPOSITORY_ROOT / "AGENTS.md",
        REPOSITORY_ROOT / "docs" / "adr" / "README.md",
        REPOSITORY_ROOT / "docs" / "engineering" / "IMPLEMENTATION_STATUS.md",
    )
    missing_links = []
    for document in documents:
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (document.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                missing_links.append(f"{document.relative_to(REPOSITORY_ROOT)} -> {target}")
    assert not missing_links, f"Broken local documentation links: {', '.join(missing_links)}"
