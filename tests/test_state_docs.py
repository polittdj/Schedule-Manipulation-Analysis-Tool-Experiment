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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "adr"
HANDOFF = REPO_ROOT / "docs" / "STATE" / "HANDOFF.md"

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
