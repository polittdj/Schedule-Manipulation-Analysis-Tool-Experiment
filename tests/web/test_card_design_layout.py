"""/card wears the Claude Design "Library Schedule ID Card" layout (ADR-0470), functionality
unchanged — the seventh page on the design.

The artboard (the v2 canvas's ``section[data-screen-label="Library Schedule ID Card"]``, read
verbatim from the canvas markup): kicker · headline · lede · a row of VERSION CHIPS ("Pick a
version to read its card") · ONE card with the file line (``file · data date``) and a grid of KPI
tiles · a ⤓ EXCEL button · a footnote. The page keeps both of its panels and every figure
VERBATIM; what it gains is the family's cursor strip — here a row of LINK chips, one per loaded
version of the active project, the open version on, and the ``vN · file · DD`` pill — because a
per-file drill's "cursor" is navigation, not a stepper. Named omissions (ADR-0470): the mock's
⤓ EXCEL (no export covers the card — the r12 rule, ADR-0327), its verdict word (no engine
verdict behind it), and its "nothing leaves this machine" footnote (an assurance that must derive
from the measured backend locality, never a static sentence — ADR-0396).

Red-first (2026-09-06): the pristine page served no strip, no chips and no pill.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
CHIP = re.compile(r'<a class="cd-chip( on)?" data-idx="(\d+)" href="([^"]+)"[^>]*>v(\d+)</a>')
PANEL = re.compile(r'<div class="?panel"?[ >]')


def _client(*names: str) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in names:
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    return client


@pytest.fixture(scope="module")
def pair() -> TestClient:
    return _client("Project2", "Project5")


def test_the_cursor_strip_serves_one_link_chip_per_version_with_the_open_one_on(
    pair: TestClient,
) -> None:
    page = pair.get("/card/Project5").text
    assert page.count("id=cardCursor") == 1
    chips = CHIP.findall(page)
    assert [(idx, href, lab) for _on, idx, href, lab in chips] == [
        ("0", "/card/Project2", "1"),
        ("1", "/card/Project5", "2"),
    ]
    assert [on for on, *_rest in chips] == ["", " on"]  # oldest first; the open version on
    pill = re.search(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>', page)
    assert pill and pill.group(1).startswith("v2 &middot; Project5.mspdi.xml &middot; DD ")


def test_a_chip_opens_that_versions_card_with_its_own_chip_on(pair: TestClient) -> None:
    page = pair.get("/card/Project2").text
    chips = CHIP.findall(page)
    assert [on for on, *_rest in chips] == [" on", ""]
    pill = re.search(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>', page)
    assert pill and pill.group(1).startswith("v1 &middot; Project2.mspdi.xml")


def test_one_loaded_version_serves_no_strip() -> None:
    page = _client("Project5").get("/card/Project5").text
    assert "id=cardCursor" not in page and "cd-chip" not in page


def test_chips_carry_no_id_and_no_family_word(pair: TestClient) -> None:
    page = pair.get("/card/Project5").text
    tags = re.findall(r"<a class=\"cd-chip[^>]*>", page)
    assert len(tags) == 2
    for tag in tags:
        assert " id=" not in tag and not re.search(_FAMILY, tag)
    assert not re.search(_FAMILY, "cardCursor")


def test_both_panels_and_every_figure_survive_the_layout(pair: TestClient) -> None:
    page = pair.get("/card/Project5").text
    assert (
        len(PANEL.findall(page)) == 3
    )  # the card, the pivots, the chrome's Ask panel — never a chip
    for text in (
        "Schedule card &mdash; ",
        "Makeup, status &amp; performance pivots",
        "stat-grid",
        "<td>Normal</td><td>126</td>",
        "<td>ASAP</td><td>120</td>",
        "% elapsed since last finish",
    ):
        assert text in page
    assert "data-export" not in page.split("<h1", 1)[-1]  # still no ⤓ EXCEL on the card (r12)
