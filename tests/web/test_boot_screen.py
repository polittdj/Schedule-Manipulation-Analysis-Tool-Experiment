"""ADR-0426 — the Boot Screen at ``/launch``: the startup lightshow, served-content half.

The Mission Ops v2 prototype opens on a full-bleed particle scene with a BEGIN LAUNCH SEQUENCE
control; the repo shipped ADR-0328's Boot Audio Hum and no boot sequence for it to ride. This
module asserts the SERVED artifact — markup, the JS/CSS text, the launcher's URL. The behavioural
half (does the canvas paint, does BEGIN reach the deck, does reduced-motion stop) is
``test_boot_screen_chromium.py``; a source-level assertion cannot answer any of those.

The four claims worth guarding, in the order they would hurt if they broke:

1. **Compliance chrome survives leaving the shell.** ``/launch`` is the only route that does not
   return through ``_page``, which is exactly where a CUI marking silently stops rendering. The
   bars AND the drawer must be there, and the drawer must be the SAME BYTES the shell serves —
   two copies of a regulatory notice is how one of them stops matching the other.
2. **No fabricated number.** The prototype counts "225.4 M km" down to zero. The design system
   forbids that. Every figure here traces to the session, and an empty session shows the em dash.
3. **Every quick action points at a real route.** ADR-0425's rule, one screen earlier.
4. **The lightshow is assetless and token-driven** — Law 1 and design law 1 respectively.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.launch import _EMPTY_ACTION, _QUICK_ACTIONS

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"
GOLD = ROOT / "tests" / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


@pytest.fixture
def loaded() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLD / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def _drawer(html: str) -> str | None:
    m = re.search(r"<details class=compliance-drawer.*?</details>", html, re.S)
    return m.group(0) if m else None


# ── 1. compliance chrome outside the shell ────────────────────────────────────────────────────


def test_the_boot_screen_marks_top_and_bottom_like_every_other_page(client: TestClient) -> None:
    html = client.get("/launch").text
    assert html.count("cui-banner") == 2, "the boot screen must carry BOTH marking bars"
    assert "cui-banner bottom" in html, "the bottom bar must carry its .bottom modifier"


def test_the_drawer_on_the_boot_screen_is_byte_identical_to_the_shell(
    client: TestClient,
) -> None:
    """Not merely "a drawer is present" — the SAME one.

    ``_page`` renders the drawer through ``_LAYOUT``; ``/launch`` renders it directly. Both call
    ``_compliance_drawer``, and this is the assertion that keeps that true: a second hand-written
    copy would pass a presence check forever while drifting from the notice the rest of the app
    shows.
    """
    boot = _drawer(client.get("/launch").text)
    shell = _drawer(client.get("/").text)
    assert boot is not None, "no compliance drawer on the boot screen"
    assert shell is not None, "no compliance drawer on the home page"
    assert boot == shell, "the boot screen's drawer has drifted from the shell's"


def test_the_boot_screen_keeps_the_sessions_classification(client: TestClient) -> None:
    """An UNCLASSIFIED-asserted session must not still be told it is handling CUI here."""
    html = client.get("/launch").text
    assert "Controlled Unclassified Information • CUI" in html
    assert 'class="cui-banner cui"' in html


# ── 2. the numbers rule ───────────────────────────────────────────────────────────────────────


def test_an_empty_session_shows_the_em_dash_and_never_a_zero_dressed_as_a_fact(
    client: TestClient,
) -> None:
    """ "Nothing loaded" is unknown, not zero. The prototype's counters would print 0 / 0 / 0."""
    html = client.get("/launch").text
    # Scope to the telemetry block: the shared compliance drawer legitimately uses the &mdash;
    # ENTITY in its prose, and that prose is not a sentinel value. Asserting over the whole
    # document would either fail on the drawer or force the drawer's wording to change to suit
    # a test — both wrong.
    tiles = html[html.index("<div class=boot-tel>") : html.index("<div class=boot-parked>")]
    assert "— nothing aboard" in tiles, "the empty aboard tile must read the em dash"
    assert "&mdash;" not in tiles, "the sentinel is the literal character, never the entity"
    assert ">0<" not in tiles and "0 files" not in tiles, "unknown must not render as zero"
    assert "225.4" not in html and "14 PRE-FLIGHT" not in html.upper(), (
        "a figure from the prototype's demo telemetry reached the served page"
    )


def test_a_loaded_session_shows_its_own_real_counts(loaded: TestClient) -> None:
    """The tiles are read from the session, so they must move when the session does."""
    from schedule_forensics.web.launch import _boot_facts

    app = loaded.app
    state = app.state.session  # type: ignore[union-attr]
    facts = _boot_facts(state)
    html = loaded.get("/launch").text

    assert facts.files == 1, facts
    assert facts.activities > 0, facts
    assert f"{facts.activities:,} activit" in html, "the activity count is not the session's"
    assert facts.data_date is not None, "the golden file carries a status date"
    assert facts.data_date.isoformat() in html, "the data-date tile is not the session's"


def test_the_boot_json_block_is_non_executable_and_escaped(client: TestClient) -> None:
    """The strict script-src CSP (ADR-0268) forbids an inline assignment; the payload is data."""
    html = client.get("/launch").text
    assert '<script id=sfBootData type="application/json">' in html
    assert "window.SF_BOOT" not in html, "a boot payload must never be an executable assignment"


# ── 3. the quick actions ──────────────────────────────────────────────────────────────────────


def test_every_quick_action_points_at_a_route_that_exists(client: TestClient) -> None:
    """ADR-0425's rule, one screen earlier: a button pointing at a route that does not exist is a
    dead link wearing a label. The population is READ from the module, never re-typed here — a
    hand-copied list is a stale list waiting to happen."""
    served = {
        getattr(r, "path", None)
        for r in client.app.routes  # type: ignore[union-attr]
    }
    for _kicker, title, _sub, route in (*_QUICK_ACTIONS, _EMPTY_ACTION):
        assert route in served, f"quick action {title!r} points at missing route {route}"


def test_the_empty_session_offers_import_and_a_loaded_one_offers_the_deck(
    client: TestClient, loaded: TestClient
) -> None:
    empty_html = client.get("/launch").text
    assert "GO TO IMPORT" in empty_html
    assert "ENTER THE DECK" not in empty_html, "nothing is aboard — there is no deck to enter yet"

    full_html = loaded.get("/launch").text
    assert "ENTER THE DECK" in full_html
    assert "Schedule Integrity" in full_html, "the forensics quick action is missing"


# ── 4. assetless, token-driven, and outside the story ─────────────────────────────────────────


def test_the_lightshow_ships_no_asset_and_reaches_no_remote_host() -> None:
    """Law 1 stays trivially true: the scene is COMPUTED, so the wheel carries zero media bytes."""
    js = (STATIC / "launch.js").read_text(encoding="utf-8")
    assert "http://" not in js and "https://" not in js
    assert ".png" not in js and ".jpg" not in js and ".webp" not in js and ".mp3" not in js
    assert "fetch(" not in js and "XMLHttpRequest" not in js


def test_the_palette_is_read_from_theme_tokens_not_hard_coded() -> None:
    """Design law 1 — nothing styles itself. The prototype hard-codes its cyan ramp; this reads
    ``--accent``/``--warn``, so apollo's amber CRT gets a lightshow that belongs to it."""
    js = (STATIC / "launch.js").read_text(encoding="utf-8")
    assert 'themeColor("--boot-accent"' in js
    assert 'themeColor("--boot-warm"' in js
    assert "getPropertyValue" in js
    # and the indirection must actually resolve to the theme for the dark views — a boot palette
    # that ignored the theme entirely would satisfy the two assertions above.
    css = (STATIC / "launch.css").read_text(encoding="utf-8")
    assert "--boot-accent: var(--accent);" in css
    assert "--boot-warm: var(--warn);" in css


def test_the_boot_screen_renders_none_of_the_story_chrome(client: TestClient) -> None:
    """It is deliberately not a chapter: no nav rail, no kicker, no Continue segue. If it ever
    starts rendering through ``_page`` this goes red rather than the screen quietly growing a
    left rail."""
    html = client.get("/launch").text
    assert "nav-chapter" not in html, "the boot screen must not render the story nav"
    assert "chapter-kicker" not in html
    assert "story-foot" not in html
    assert "continue-btn" not in html


def test_reduced_motion_is_honoured_by_the_module() -> None:
    """The screen is decorative motion end to end, so the query is not optional. The behavioural
    proof (no rAF is ever scheduled) is in the chromium module; this pins the mechanism."""
    js = (STATIC / "launch.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in js
    assert "raf = reduced ? null : requestAnimationFrame(frame);" in js, (
        "the frame loop must not re-arm under reduced motion"
    )


def test_the_audio_is_adr_0328s_module_and_is_gesture_primed() -> None:
    """One sound, one set of controls, one persisted preference — the boot screen must not
    synthesize a second hum. And the context is created inside the click handler, nowhere else."""
    js = (STATIC / "launch.js").read_text(encoding="utf-8")
    assert "window.SFLaunchAudio" in js
    # Constructors and graph nodes, not the WORD — "AudioContext" appears in this module's own
    # comment explaining that it never builds one, and a guard that cannot tell prose from code
    # would force the comment out to stay green.
    for built in ("new AudioContext", "webkitAudioContext", "createOscillator", "createGain"):
        assert built not in js, f"the boot screen must not build its own audio graph ({built})"
    assert "SFLaunchAudio.prime()" in js
    begin = js[js.index("function begin()") : js.index("function leave(")]
    assert "prime()" in begin, "priming must happen inside the click handler"


def test_the_launcher_opens_the_boot_screen() -> None:
    """The boot screen is the program's front door or it is a page nobody ever sees."""
    src = (ROOT / "src" / "schedule_forensics" / "launcher.py").read_text(encoding="utf-8")
    assert 'args=(f"{url}/launch",)' in src, "the launcher no longer opens the boot screen"


def test_the_skip_preference_short_circuits_before_anything_is_painted() -> None:
    """A boot screen the operator dismissed must never FLASH. The check runs at parse time, in
    the head-loaded module, before the canvas is laid out."""
    js = (STATIC / "launch.js").read_text(encoding="utf-8")
    head = js[: js.index("var boot = null;")]
    assert 'stored(SKIP_KEY) === "1"' in head
    assert 'location.replace("/")' in head
