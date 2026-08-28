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
        "no fabricated observations": "never fabricate an environmental observation in operational code",
        "synthetic fixture boundary": "synthetic data may exist only in explicit automated-test or demo fixtures",
        "typed unavailable state": "typed `unavailable` or `degraded` states",
        "EPSG:4326 metric prohibition": "never interpret degrees or epsg:4326 planar results as metres",
        "provenance source": "source/provider and stable source uri",
        "provenance acquisition time": "acquisition/valid time",
        "provenance processing time": "processing time, expressed as timezone-aware utc",
        "provenance versions": "configuration, model, threshold, and reference-dataset versions",
        "quality and uncertainty": "quality/availability status, validation result, known limitations, and uncertainty",
        "concept separation": "public observation, forecast, exposure, estimated impact, and verified damage",
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
