"""WP5 — the folder ask (operator, 2026-08-27: BOTH builds): labels that state the three measured
folder-gesture facts, and the parent-folder question that is ASKED, never guessed.

The three facts were MEASURED on 2026-08-21 and govern this build (never re-derived here):

1. the folder-picker DIALOG cannot multi-select — ``webkitdirectory`` overrides ``multiple``
   (Chromium's file-chooser modes are exclusive, WICG entries-api #24);
2. DROPPING several folders at once WORKS — each dropped folder lands as its own Project
   (ADR-0437, proven with real Chrome entries via CDP);
3. Ctrl/Shift multi-select of FILES already works through *choose files…*.

Build A (labels): the dropzone says each of the three plainly, in the operator's terms, and the
folder button says what the dialog can do (ONE folder per pick). Build B (the question): the
server groups every file by its TOP folder (``_parse_upload_meta``), so an operator whose
projects sit side by side under a parent — ``Programs/Apollo/…``, ``Programs/Artemis/…`` — could
only ever pick the parent and got ONE Project with every schedule a version. That is correct for
year sub-folders (``Project/2024/x.mpp`` IS one Project) and wrong for sibling programs, and the
paths alone can never say which (ADR-0258: a folder is one Project by the operator's rule;
guessing is forbidden). So when ONE folder root's schedule files span two or more immediate
sub-folders, ``home.js`` asks — one Project, or one per sub-folder — and the per-sub-folder answer
re-roots each file's companion ``rel`` at its sub-folder before the upload. The server changes
nothing; this module pins BOTH server facts the client relies on, the served shell, and the
client-side plan's shape. ``test_folder_ask_browser.py`` drives the real thing in Chromium.

Observed RED on the pristine tree (2026-09-04): every build-A/B pin below failed by name; the two
server pins were green (they pin behaviour that pre-dates the build and MUST stay true).
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.test_ui_control_effect_census import _FAMILY

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><Title>{title}</Title><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate>{_TASK}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def _post(client: TestClient, rels: list[str]) -> None:
    files = [
        (
            "files",
            (r.rsplit("/", 1)[-1], _mspdi("ignored", f"2025-0{i + 1}-10T00:00:00"), "text/xml"),
        )
        for i, r in enumerate(rels)
    ]
    meta = json.dumps([{"rel": r, "mtime": 1000 + i} for i, r in enumerate(rels)])
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200


# ── build A: the three gestures, stated plainly ─────────────────────────────────────────────


def test_dropzone_states_the_three_gestures_plainly(sc: tuple[SessionState, TestClient]) -> None:
    """The copy names each measured gesture: several FILES via Ctrl/Shift, ONE folder per pick,
    several folders (several Projects) by dropping them together. The two phrases the 2026-08-21
    build pinned survive verbatim, and both buttons keep the ids home.js binds."""
    _st, client = sc
    home = client.get("/").text
    assert "id=pickBtn" in home and "id=pickFolderBtn" in home
    assert "choose one folder" in home  # the button says what the dialog can do (fact 1)
    assert "one folder per pick" in home
    assert "Ctrl-click" in home and "Shift-click" in home  # fact 3, in the operator's terms
    assert "drop several folders at once" in home  # fact 2 — the 2026-08-21 phrase, kept
    assert "each folder is its own Project" in home  # ADR-0437's contract, kept
    # the parent-folder question is announced where the operator reads how to load
    assert "parent folder" in home and "asks you how to load it" in home


# ── build B: the served shell + the client-side plan ───────────────────────────────────────


def test_home_serves_the_parent_folder_ask_shell_hidden(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The question is a server-rendered, hidden dialog shell the script fills with textContent:
    a title, the per-sub-folder list, the never-guess rule, and three controls — one Project,
    one per sub-folder, Cancel. Rendering it hidden keeps the empty page byte-identical in
    behaviour until a gesture is actually ambiguous."""
    _st, client = sc
    home = client.get("/").text
    shell = re.search(r"<div id=dzAsk\b[^>]*>", home)
    assert shell, "the #dzAsk shell is not served"
    assert "hidden" in shell.group(0) and "role=dialog" in shell.group(0)
    assert "aria-labelledby=dzAskTitle" in shell.group(0)
    for cid in ("dzAskTitle", "dzAskList", "dzAskNote", "dzAskSplit", "dzAskOne", "dzAskCancel"):
        assert f"id={cid}" in home, cid
    assert "The tool never guesses" in home


def test_ask_controls_stay_outside_the_control_census_families() -> None:
    """The sitewide control-effect census (M1) recognises stepper/zoom families by id+class; a
    new home-page control whose id or class matched one would enter that census as an undriven
    control. The ask's ids and classes are chosen outside every family word — asserted with the
    census module's OWN regex so the two can never drift apart."""
    family = re.compile(_FAMILY, re.IGNORECASE)
    for token in (
        "dzAsk",
        "dzAskTitle",
        "dzAskList",
        "dzAskNote",
        "dzAskSplit",
        "dzAskOne",
        "dzAskCancel",
        "dz-ask",
        "dz-ask-title",
        "dz-ask-list",
        "dz-how",
    ):
        assert not family.search(token), f"{token!r} collides with a census family word"


def test_home_js_plans_the_split_client_side_without_a_new_html_sink(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The plan and the re-rooting live in home.js (the server is untouched — see the two
    server pins below), the ask is built with createElement/textContent (folder names are
    operator content, ADR-0439 — no new ``innerHTML`` sink beyond the pre-existing notice), the
    ask asks only when ONE root spans two or more sub-folders holding schedules, and the
    buttons never prime the audio context (the four genuine gesture handlers already did —
    ``test_launch_sequence`` pins that count at exactly four)."""
    _st, client = sc
    js = client.get("/static/home.js").text
    assert "function subfolderPlan(" in js and "function reroot(" in js
    assert "function askSubfolders(" in js and "function ingest(" in js
    assert js.count("innerHTML") == 1, "a new innerHTML sink entered home.js"
    assert "textContent" in js
    # every entry point funnels through ingest(): picked files, the picked folder, the drop
    assert js.count("ingest(") >= 4
    assert js.count("hum('prime')") == 4


# ── the two SERVER facts the client relies on (pre-existing behaviour, pinned) ─────────────


def test_server_groups_a_parent_folder_pick_as_one_project(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The fact that makes the question necessary: the companion ``rel`` is grouped by its FIRST
    segment, so a parent folder holding two project folders is ONE Project with every schedule a
    version — exactly what an un-asked pick would silently produce."""
    st, client = sc
    _post(client, ["Programs/Apollo/a1.xml", "Programs/Artemis/b1.xml"])
    projects = {p.title: p for p in st.projects()}
    assert set(projects) == {"Programs"}
    assert projects["Programs"].origin == "folder"
    assert len(projects["Programs"].versions) == 2


def test_server_groups_rerooted_rels_one_project_per_subfolder(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The fact the per-sub-folder answer relies on: rels re-rooted at their sub-folder land as
    separate folder Projects, and a file that sat directly under the parent keeps the parent as
    its Project (the client leaves a two-segment rel untouched)."""
    st, client = sc
    _post(client, ["Apollo/a1.xml", "Apollo/2024/a2.xml", "Artemis/b1.xml", "Programs/top.xml"])
    projects = {p.title: p for p in st.projects()}
    assert set(projects) == {"Apollo", "Artemis", "Programs"}
    assert all(p.origin == "folder" for p in projects.values())
    assert len(projects["Apollo"].versions) == 2
    assert len(projects["Artemis"].versions) == 1
    assert len(projects["Programs"].versions) == 1
    assert len(st.populations()) == 3
