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


# ── every workflow can be dispatched by hand (WP4, ADR-0455) ───────────────────────────────
# On 2026-08-26 a GitHub-side anomaly gave one push run `startup_failure` and delayed the next
# push's run by 21 minutes; the session on duty fell back to `workflow_dispatch` for ci.yml — and
# could not for installer-smoke.yml, which had no manual trigger. A workflow that can only be
# reached by an event it does not control cannot be re-proven on demand.

_ON_BLOCK = re.compile(r"^on:\n((?:[ \t]+.*\n|\n)+)", re.MULTILINE)


def _dispatchable(wf: Path) -> bool:
    match = _ON_BLOCK.search(wf.read_text(encoding="utf-8"))
    return bool(match) and re.search(r"^\s+workflow_dispatch:", match.group(1), re.M) is not None


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_offers_a_manual_trigger(wf: Path) -> None:
    assert _dispatchable(wf), f"{wf.name}: add `workflow_dispatch:` under `on:`"


def test_the_dispatch_check_can_fail(tmp_path: Path) -> None:
    """Guard the guard: an `on:` block without the trigger — and a trigger hiding OUTSIDE the
    `on:` block — must both be refused."""
    absent = tmp_path / "absent.yml"
    absent.write_text("name: x\non:\n  push:\n    branches: [main]\n\njobs: {}\n", encoding="utf-8")
    assert not _dispatchable(absent)
    elsewhere = tmp_path / "elsewhere.yml"
    elsewhere.write_text(
        "name: x\non:\n  push:\n\njobs:\n  a:\n    steps:\n      - run: echo workflow_dispatch:\n",
        encoding="utf-8",
    )
    assert not _dispatchable(elsewhere)
    present = tmp_path / "present.yml"
    present.write_text(
        "name: x\non:\n  push:\n  workflow_dispatch:\n\njobs: {}\n", encoding="utf-8"
    )
    assert _dispatchable(present)
