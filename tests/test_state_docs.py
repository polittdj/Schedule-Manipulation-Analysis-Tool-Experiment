"""Guard against the durable-state doc silently drifting behind the ADR record.

The build process makes ``docs/STATE/HANDOFF.md`` the single source of truth a
fresh session resumes from ("READ THIS FILE FIRST"), paired with ``docs/adr/``
as the decision record. When a PR ships an ADR but the handoff is not refreshed,
the next session resumes from a stale map: it can re-attempt already-merged work
or recreate a consumed branch. That is exactly what happened once -- the handoff
stopped at ADR-0046 / PR #102 while ``main`` had merged through ADR-0057 / #113 --
and this test exists so it fails loudly the next time instead of silently.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "adr"
HANDOFF = REPO_ROOT / "docs" / "STATE" / "HANDOFF.md"
SESSION_LOG = REPO_ROOT / "docs" / "STATE" / "SESSION-LOG.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"

_ADR_FILE = re.compile(r"^(\d{4})-.*\.md$")


def _latest_adr_number() -> int:
    """Highest ADR sequence number among ``docs/adr/NNNN-*.md`` files."""
    numbers = []
    for path in ADR_DIR.iterdir():
        match = _ADR_FILE.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    assert numbers, f"no ADR files found in {ADR_DIR}"
    return max(numbers)


def test_handoff_references_latest_adr() -> None:
    """HANDOFF.md must mention the most recent ADR on disk.

    This pins the durable state to the decision record: a session that adds an
    ADR must refresh the handoff in the same change.
    """
    latest = _latest_adr_number()
    token = f"ADR-{latest:04d}"
    text = HANDOFF.read_text(encoding="utf-8")
    assert token in text, (
        f"docs/STATE/HANDOFF.md does not mention {token}, the latest ADR on disk. "
        "Refresh the handoff so a new session resumes from current state "
        "(see HANDOFF.md 'READ THIS FILE FIRST to resume')."
    )


def test_session_log_references_latest_adr() -> None:
    """A11: the append-only SESSION-LOG must also record the latest ADR.

    The earlier drift (HANDOFF stale behind the merged PR) slipped past because only the
    *latest ADR token* was checked in one doc. Anchoring on the ADR files (local ground truth,
    no network) and requiring the latest to appear in BOTH durable docs catches an ADR that
    shipped without its session being logged.
    """
    latest = _latest_adr_number()
    token = f"ADR-{latest:04d}"
    text = SESSION_LOG.read_text(encoding="utf-8")
    assert token in text, (
        f"docs/STATE/SESSION-LOG.md does not mention {token}, the latest ADR on disk. "
        "Append the session entry so the per-session history stays complete."
    )


def test_handoff_top_section_pins_the_current_pyproject_version() -> None:
    """The shipped version must appear in HANDOFF's CURRENT (top) status section.

    The ADR-token check alone once let a version ship past the guard: 1.0.18 was a
    bugfix with no ADR, so nothing forced a HANDOFF refresh and the "read first" doc
    presented 1.0.17 as current (audit M11). Pinning ``pyproject.toml``'s version
    string into the section ABOVE the first ``# (prior)`` marker means any version
    bump must refresh the top of the handoff in the same change — an old version
    string lingering in the history sections can never satisfy this.
    """
    with PYPROJECT.open("rb") as fh:
        version = tomllib.load(fh)["project"]["version"]
    top_section = HANDOFF.read_text(encoding="utf-8").split("# (prior)", 1)[0]
    # Boundary-anchored: "1.0.5" must not silently satisfy a handoff that says "1.0.52".
    pinned = re.search(rf"(?<![\d.]){re.escape(version)}(?![\d.])", top_section)
    assert pinned, (
        f"docs/STATE/HANDOFF.md's top (current) section does not mention {version}, the "
        "version pyproject.toml ships. Refresh the handoff's STATUS block in the same "
        "change as the version bump so a new session resumes from the shipped state."
    )
