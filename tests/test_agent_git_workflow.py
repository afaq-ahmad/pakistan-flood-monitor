"""Offline integration checks for agent Git helpers, using temporary repositories only."""
import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args, cwd, check=True):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=check)


@pytest.fixture
def repos(tmp_path):
    remote, local = tmp_path / "remote.git", tmp_path / "local"
    run("git", "init", "--bare", str(remote), cwd=tmp_path)
    run("git", "clone", str(remote), str(local), cwd=tmp_path)
    run("git", "config", "user.email", "agent@example.invalid", cwd=local)
    run("git", "config", "user.name", "Test Agent", cwd=local)
    run("git", "config", "core.autocrlf", "false", cwd=local)
    run("git", "config", "core.whitespace", "cr-at-eol", cwd=local)
    run("git", "switch", "-c", "work", cwd=local)
    (local / "base").write_text("base\n")
    run("git", "add", "base", cwd=local)
    run("git", "commit", "-m", "base", cwd=local)
    run("git", "push", "-u", "origin", "work", cwd=local)
    return local, remote


def helper(name, *args, cwd, check=True):
    return run("bash", str(SCRIPTS / name), *args, cwd=cwd, check=check)


def sha(repo, ref="HEAD"):
    return run("git", "rev-parse", ref, cwd=repo).stdout.strip()


def test_checkpoint_and_recovery_preserve_unrelated_changes(repos, tmp_path):
    local, remote = repos
    (local / "intended").write_text("checkpoint\n")
    (local / "unrelated").write_text("leave me\n")
    run("git", "add", "intended", cwd=local)
    helper("agent_checkpoint.sh", "work", "feat: checkpoint", cwd=local)
    assert sha(local) == sha(remote, "refs/heads/work")
    assert (local / "unrelated").read_text() == "leave me\n"
    assert "unrelated" not in run("git", "show", "--name-only", "--format=", "HEAD", cwd=local).stdout
    before = sha(local)
    assert "No staged changes" in helper("agent_checkpoint.sh", "work", "unused", cwd=local).stdout
    assert sha(local) == before
    clone = tmp_path / "fresh"
    run("git", "clone", str(remote), str(clone), cwd=tmp_path)
    helper("agent_resume.sh", "work", cwd=clone)
    assert sha(clone) == before
    assert (clone / "intended").read_text() == "checkpoint\n"


def test_dirty_resume_and_protected_files_stop(repos):
    local, remote = repos
    (local / ".env").write_text("SECRET=example\n")
    run("git", "add", ".env", cwd=local)
    before = sha(local)
    result = helper("agent_checkpoint.sh", "work", "bad", cwd=local, check=False)
    assert result.returncode == 2 and "SECRET=example" not in result.stderr
    assert sha(local) == before
    assert helper("agent_resume.sh", "work", cwd=local, check=False).returncode == 2
    assert (local / ".env").exists()


def test_failed_push_keeps_commit(repos):
    local, remote = repos
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    (local / "change").write_text("data\n")
    run("git", "add", "change", cwd=local)
    before = sha(remote, "refs/heads/work")
    result = helper("agent_checkpoint.sh", "work", "feat: retained", cwd=local, check=False)
    assert result.returncode == 3 and "local commit" in result.stderr
    assert sha(local) != before and sha(remote, "refs/heads/work") == before
    assert (local / "change").read_text() == "data\n"


def test_diverged_resume_refuses_to_overwrite(repos, tmp_path):
    local, remote = repos
    other = tmp_path / "other"
    run("git", "clone", "--branch", "work", str(remote), str(other), cwd=tmp_path)
    run("git", "config", "user.email", "other@example.invalid", cwd=other)
    run("git", "config", "user.name", "Other", cwd=other)
    (local / "local").write_text("local\n")
    run("git", "add", "local", cwd=local)
    run("git", "commit", "-m", "local", cwd=local)
    before = sha(local)
    (other / "other").write_text("other\n")
    run("git", "add", "other", cwd=other)
    run("git", "commit", "-m", "other", cwd=other)
    run("git", "push", cwd=other)
    result = helper("agent_resume.sh", "work", cwd=local, check=False)
    assert result.returncode == 2 and "diverged" in result.stderr
    assert sha(local) == before and (local / "local").exists()


def test_dry_run_and_branch_guard(repos):
    local, remote = repos
    (local / "change").write_text("data\n")
    run("git", "add", "change", cwd=local)
    before = sha(local)
    assert helper("agent_checkpoint.sh", "wrong", "message", cwd=local, check=False).returncode == 2
    helper("agent_checkpoint.sh", "--dry-run", "work", "message", cwd=local)
    assert sha(local) == before == sha(remote, "refs/heads/work")


def test_preflight_lists_existing_pr_without_creating_one(repos, tmp_path, monkeypatch):
    local, _ = repos
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "gh-calls"
    gh = fake_bin / "gh"
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\ncase "$1 $2" in\n  "auth status") exit 0;;\n  "pr list") printf "[{\\"number\\":83,\\"headRefName\\":\\"work\\"}]\\n";;\n  *) exit 1;;\nesac\n')
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("CALL_LOG", str(calls))
    result = helper("agent_preflight.sh", "--dry-run", "workflow", cwd=local)
    assert '"number":83' in result.stdout
    assert "pr list" in calls.read_text() and "pr create" not in calls.read_text()


def test_remote_advance_rejects_checkpoint_without_force(repos, tmp_path):
    local, remote = repos
    other = tmp_path / "other"
    run("git", "clone", "--branch", "work", str(remote), str(other), cwd=tmp_path)
    run("git", "config", "user.email", "other@example.invalid", cwd=other)
    run("git", "config", "user.name", "Other", cwd=other)
    (other / "upstream").write_text("upstream\n")
    run("git", "add", "upstream", cwd=other)
    run("git", "commit", "-m", "upstream", cwd=other)
    run("git", "push", cwd=other)
    remote_before = sha(remote, "refs/heads/work")
    (local / "local").write_text("local\n")
    run("git", "add", "local", cwd=local)
    result = helper("agent_checkpoint.sh", "work", "feat: local", cwd=local, check=False)
    assert result.returncode == 3 and "do not force push" in result.stderr
    assert sha(remote, "refs/heads/work") == remote_before and sha(local) != remote_before
