"""Every GitHub Action must be pinned to a commit SHA (audit §7, ADR-0347).

A mutable major tag — ``actions/checkout@v5`` — is a standing supply-chain hole: whoever can move
that tag can run arbitrary code inside a job that has already checked out this repository. The
2026-08-03 external audit found all nine action references on ``@v4``/``@v5``/``@v6``, including
the two ADR-0346's ``floor`` job had just added.

Pinning is only half the fix. Without this test the next workflow edit reintroduces a tag and
nobody notices, so the finding reopens silently — the same shape as ADR-0346's lesson that a
declared range nobody runs is decoration. The readability the tag provided is preserved by the
``# vX.Y.Z`` comment each pin carries, which this test also requires: a bare 40-hex SHA with no
version note is unmaintainable, and an unmaintainable pin gets reverted.

Scope note: this deliberately does NOT assert *which* SHA. Pinning is hygiene, not a version
policy; asserting a specific commit would turn every routine action upgrade into a test edit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parents[2] / ".github" / "workflows").glob("*.yml"))

# `- uses: owner/repo@ref  # comment`  (also the `uses:` form nested under a step key)
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)(?:\s+#\s*(?P<note>.*))?$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_VERSION_NOTE = re.compile(r"^v\d+\.\d+\.\d+")


def _uses() -> list[tuple[Path, int, str, str]]:
    found: list[tuple[Path, int, str, str]] = []
    for wf in WORKFLOWS:
        for lineno, line in enumerate(wf.read_text(encoding="utf-8").split("\n"), start=1):
            match = _USES.match(line)
            if match:
                found.append((wf, lineno, match.group("ref"), match.group("note") or ""))
    return found


def test_there_are_workflows_with_action_references() -> None:
    """Guard the guard: an empty sweep would make every assertion below vacuously true."""
    assert WORKFLOWS, ".github/workflows/ holds no yml files"
    assert len(_uses()) >= 9, "expected at least the nine known action references"


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit_sha(wf: Path) -> None:
    unpinned = [
        f"{wf.name}:{lineno}  {ref}"
        for path, lineno, ref, _ in _uses()
        if path == wf and not _SHA.match(ref.partition("@")[2])
    ]
    assert unpinned == [], (
        "mutable action refs — pin to a commit SHA:\n  "
        + "\n  ".join(unpinned)
        + "\nResolve with: git ls-remote --tags https://github.com/<owner>/<repo> 'refs/tags/<tag>'"
    )


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_pin_records_the_release_it_pins(wf: Path) -> None:
    """A bare SHA is unmaintainable; the `# vX.Y.Z` note is what makes the pin upgradable."""
    undocumented = [
        f"{wf.name}:{lineno}  {ref}"
        for path, lineno, ref, note in _uses()
        if path == wf and not _VERSION_NOTE.match(note.strip())
    ]
    assert undocumented == [], (
        "each pin needs a trailing `# vX.Y.Z` naming the release it pins:\n  "
        + "\n  ".join(undocumented)
    )
