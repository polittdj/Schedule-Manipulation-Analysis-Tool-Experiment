"""A dashboard card's drill resolves THAT card's file — never a substituted one (ADR-0295).

The dashboard is the session MANIFEST: one card per loaded file, **every Project**, excluded
versions included (ADR-0258). Each card's status bar marks its segments with the card's own key so
a click lists the activities behind it. But the drill endpoint used to resolve the version through
``_pick_scorecard_version``, which searches the **ACTIVE Project only** and silently falls back to
``versions[-1]`` when the requested key is not found.

So with two Projects loaded, clicking the non-active Project's card rendered the ACTIVE Project's
schedule instead. Measured on the golden pair (Alpha/Project2 + Bravo/Project5, Bravo active):

    card Project2  card.complete=20  drill rows=20  but resolved file=Project5

Those 20 rows are Project5 activities that happen to share UIDs with Project2's complete set —
wrong data presented under the right label, which is precisely the failure Law 2 exists to
prevent. The lazy-segment form (ADR-0288) made it worse, not better: ``segment=complete`` against
the substituted file returned 27 rows — Project5's own complete set — a fully self-consistent,
entirely wrong answer. That is why this fix lands BEFORE the dashboard ``status_mix_uids`` trim.

5 of the 7 tests fail on the pre-fix tree (verified by stashing the resolver change); the two
that pass pre-fix are the anti-regression pins on behaviour the fix must NOT change (the unnamed
``file=""`` fallback and active-population resolution).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _two_projects() -> TestClient:
    """Two DISTINCT Projects (different top folders) — the newest-loaded becomes active."""
    client = TestClient(create_app(SessionState()))
    for name, folder in (("Project2.mspdi.xml", "Alpha"), ("Project5.mspdi.xml", "Bravo")):
        client.post(
            "/upload",
            files={"files": (name, (GOLD / name).read_bytes(), "text/xml")},
            data={"file_meta": json.dumps([{"rel": f"{folder}/{name}", "mtime": 1}])},
        )
    return client


def test_every_dashboard_card_drills_against_its_own_file() -> None:
    client = _two_projects()
    cards = client.get("/api/dashboard").json()["cards"]
    assert len(cards) == 2, "the dashboard is the manifest — both Projects must appear"

    for card in cards:
        key = card["key"]
        uids = (card.get("status_mix_uids") or {}).get("complete") or []
        drill = client.get(
            f"/api/activities/drill?file={key}&uids=" + ",".join(str(u) for u in uids)
        ).json()
        # the endpoint echoes the version it actually resolved — it must be the one asked for
        assert drill["file"] == key, (
            f"card {key} drilled against {drill['file']!r} — another Project's schedule"
        )
        assert len(drill["rows"]) == card["status_mix"]["complete"], (
            f"card {key} says {card['status_mix']['complete']} complete but the drill listed "
            f"{len(drill['rows'])}"
        )


def test_a_named_file_that_does_not_exist_is_an_error_not_a_substitution() -> None:
    """The silent fallback was the defect: a named-but-unknown version must error loudly."""
    client = _two_projects()
    missing = client.get("/api/activities/drill?file=NoSuchVersion&segment=complete")
    assert missing.status_code == 400
    assert "NoSuchVersion" in missing.json()["error"]

    export = client.get("/export/xlsx/activities-drill?file=NoSuchVersion&segment=complete")
    assert export.status_code == 422
    assert "NoSuchVersion" in export.json()["error"]


def test_an_unnamed_request_still_means_latest_solvable() -> None:
    """``file=""`` keeps its historical meaning — that is how the UID-only triggers (sra.js's
    per-activity bars) have always worked; the error path is only for a NAMED miss."""
    client = _two_projects()
    unnamed = client.get("/api/activities/drill?file=&segment=complete").json()
    assert unnamed["file"] in {"Project2", "Project5"}  # a real loaded version, not an error


@pytest.mark.parametrize("segment", ["complete", "in_progress", "planned"])
def test_the_lazy_segment_form_agrees_with_the_card_it_came_from(segment: str) -> None:
    """Guards the follow-on ``status_mix_uids`` trim: once the card ships a segment NAME instead
    of an id list, the server-resolved set must still equal that card's own count — for BOTH
    cards, not just the active Project's."""
    client = _two_projects()
    for card in client.get("/api/dashboard").json()["cards"]:
        rows = client.get(f"/api/activities/drill?file={card['key']}&segment={segment}").json()[
            "rows"
        ]
        assert len(rows) == card["status_mix"][segment], f"{card['key']}/{segment}"


def test_active_population_triggers_resolve_exactly_as_before() -> None:
    """The widened resolver may only ADD resolution, never change an existing one: a trigger
    naming an active-population version (by key or by label) must return the same version the
    old resolver picked."""
    client = _two_projects()
    by_key = client.get("/api/activities/drill?file=Project5&segment=complete").json()
    assert by_key["file"] == "Project5"
    by_label = client.get("/api/activities/drill?file=Project5.mspdi.xml&segment=complete").json()
    assert by_label["file"] == "Project5"
    assert len(by_key["rows"]) == len(by_label["rows"])
