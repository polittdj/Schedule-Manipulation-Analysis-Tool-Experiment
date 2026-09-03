"""``tools/ci_cui_guard.sh`` — the pre-commit CUI blocklist, run by CI over a push/PR diff.

WP4 · ADR-0455. The local hook guards only a clone that activated it, and a GitHub web upload
never runs it (2026-09-03: four ``.docx`` and a Save-format ``.json`` landed under
``00_REFERENCE_INTAKE/src/``, seen only by the manifest guard one PR later). The script runs the
SAME hook — one blocklist in the tree — over everything ``base..HEAD`` adds or changes.

Each test runs the real script and the real hook inside a scratch repo (the pattern
``test_precommit_blocklist.py`` established): the guard must refuse a new schedule file on a PR,
must NOT fire on ordinary source, must restore HEAD whatever it decides, must treat an operator
web-upload under ``00_REFERENCE_INTAKE/`` on a push as disclosure (warning) while a schedule
file elsewhere on that same push is still an error, and its ``--self-test`` must prove the hook
can fail.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "ci_cui_guard.sh"
HOOK = ROOT / ".githooks" / "pre-commit"


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _commit(repo: Path, message: str, **files: bytes) -> str:
    for rel, body in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        _git(repo, "add", "-f", "--", rel)
    _git(repo, "commit", "-q", "--no-verify", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A scratch repository carrying the REAL hook at the path the script expects."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / ".githooks").mkdir()
    shutil.copy(HOOK, repo / ".githooks" / "pre-commit")
    _commit(
        repo, "base", **{"src/ok.py": b"print('hi')\n", ".githooks/pre-commit": HOOK.read_bytes()}
    )
    return repo


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=repo, capture_output=True, text=True, check=False
    )


def test_a_new_schedule_file_on_a_pull_request_fails_by_name(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "leak", **{"data/leak.mpp": b"new-schedule"})
    proc = _run(repo, base, "pull_request")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "::error file=data/leak.mpp::" in proc.stdout
    assert _git(repo, "rev-parse", "HEAD") == head  # HEAD restored after the verdict


def test_ordinary_source_passes_and_head_is_restored(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "feature", **{"src/more.py": b"x = 1\n", "docs/note.md": b"# hi\n"})
    proc = _run(repo, base, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "found nothing" in proc.stdout
    assert _git(repo, "rev-parse", "HEAD") == head


def test_a_push_discloses_intake_uploads_but_still_fails_a_schedule_elsewhere(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "web upload", **{"00_REFERENCE_INTAKE/src/x.docx": b"PK-not-really"})
    proc = _run(repo, base, "push")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "::warning file=00_REFERENCE_INTAKE/src/x.docx::" in proc.stdout
    assert "::error" not in proc.stdout
    # the same push carrying a schedule OUTSIDE the intake tree is an error, warning or not
    base2 = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "stray", **{"notes/plan.xer": b"ERMHDR\t7"})
    proc = _run(repo, base2, "push")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "::error file=notes/plan.xer::" in proc.stdout


def test_the_same_intake_upload_is_a_hard_failure_on_a_pull_request(repo: Path) -> None:
    """The warning is the push-to-main disclosure only; a PR from a build session gets the gate."""
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "pr upload", **{"00_REFERENCE_INTAKE/src/x.docx": b"PK-not-really"})
    proc = _run(repo, base, "pull_request")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "::error file=00_REFERENCE_INTAKE/src/x.docx::" in proc.stdout


def test_a_blob_the_base_already_had_is_inherited_not_blocked(repo: Path) -> None:
    """The hook's inherited-blob exception, aimed at the BASE: a PR that merely carries a
    blocked-extension file main already holds, byte for byte, is not accused of adding it."""
    _commit(repo, "upstream intake", **{"00_REFERENCE_INTAKE/ref.xlsx": b"upstream-bytes"})
    base = _git(repo, "rev-parse", "HEAD")
    # a PR head that touches other files while the intake blob rides along unchanged
    _commit(repo, "pr", **{"src/feature.py": b"y = 2\n"})
    proc = _run(repo, base, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # ...and a TAMPERED copy of that same path is blocked, base or no base
    base2 = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "tamper", **{"00_REFERENCE_INTAKE/ref.xlsx": b"TAMPERED"})
    proc = _run(repo, base2, "pull_request")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "::error file=00_REFERENCE_INTAKE/ref.xlsx::" in proc.stdout


def test_an_unknown_base_is_refused_not_ignored(repo: Path) -> None:
    proc = _run(repo, "0" * 40, "pull_request")
    assert proc.returncode == 2
    assert "not a commit" in proc.stderr


def test_the_self_test_proves_the_hook_can_fail(repo: Path) -> None:
    proc = _run(repo, "--self-test")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "the guard can fail" in proc.stdout
    assert not (repo / "__ci_cui_guard_probe.mpp").exists()
    assert _git(repo, "status", "--porcelain") == ""  # the probe left no trace, staged or not


def test_the_self_test_reddens_when_the_hook_is_dead(repo: Path) -> None:
    """Mutation: a hook that allows everything must be caught by the self-test itself."""
    dead = repo / ".githooks" / "pre-commit"
    dead.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    proc = _run(repo, "--self-test")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "ALLOWED a staged .mpp" in proc.stderr
    assert not (repo / "__ci_cui_guard_probe.mpp").exists()
