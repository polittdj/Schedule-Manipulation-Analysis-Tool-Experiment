"""Session-wide target UID, the four-view theme system (ADR-0195), and the 20-file batch cap."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import MAX_FILES
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "schedule_forensics"
    / "web"
    / "examples"
    / "house_build.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


# ---- light / dark theme ----


def test_every_page_carries_theme_controls_and_script(client: TestClient) -> None:
    page = client.get("/").text
    assert 'src="/static/theme.js?v=' in page  # cache-busted (ADR-0148)
    assert 'href="/static/sf-themes.css?v=' in page  # the four-view tokens (ADR-0195)
    assert "id=themeToggle" in page
    assert "id=themeSelect" in page  # the View dropdown
    for view in ("console", "daylight", "apollo", "jarvis"):
        assert f"<option value={view}>" in page, view


def test_theme_js_persists_and_applies_data_theme(client: TestClient) -> None:
    js = client.get("/static/theme.js").text
    assert "localStorage" in js and "sf-theme" in js
    assert 'setAttribute("data-theme"' in js


def test_console_is_the_default_view_and_legacy_saves_migrate(client: TestClient) -> None:
    """ADR-0195: the tool opens in the CONSOLE view (dark mission control) by default.
    Legacy saves migrate — "light" becomes "daylight", "dark" becomes "console" — and the
    view NEVER follows the OS setting (an explicit operator choice, identical everywhere)."""
    js = client.get("/static/theme.js").text
    assert 'saved === "light"' in js and '"daylight"' in js  # light -> daylight
    assert 'saved === "dark"' in js and '"console"' in js  # dark -> console
    assert "prefers-color-scheme" not in js


def test_sf_themes_css_defines_all_four_views(client: TestClient) -> None:
    """ADR-0195: sf-themes.css carries the complete token set for every view, including the
    header chrome tokens the command banner reads (base.css keeps :root as no-JS fallback)."""
    css = client.get("/static/sf-themes.css").text
    for view in ("console", "daylight", "apollo", "jarvis"):
        assert f"html[data-theme={view}]" in css, view
    assert css.count("--header-bg:") >= 4
    assert css.count("--header-ink:") >= 4
    assert css.count("--header-line:") >= 4
    assert css.count("--grid-dot:") >= 4  # the dotted chart reading grid re-themes too


def test_base_css_defines_the_light_palette(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "html[data-theme=light]" in css  # legacy fallback block (superseded by daylight)
    # no hard-coded page colors left outside the variable blocks: spot-check the
    # surfaces that used to be fixed-dark
    assert "background:var(--header-bg)" in css
    assert "color:var(--btn-ink)" in css


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_theme_switcher_migration_and_toggle_execute_under_node() -> None:
    """ADR-0195: EXECUTE theme.js (not just substring-pin it) — the legacy-save migration,
    the four-view select, and the daylight<->last-dark toggle round-trip."""
    harness = Path(__file__).parent / "js" / "theme_switch_harness.mjs"
    proc = subprocess.run(
        [str(shutil.which("node")), str(harness)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"


def test_svg_charts_route_theme_variables_via_style(client: TestClient) -> None:
    for asset in ("cei.js", "trend.js"):
        js = client.get(f"/static/{asset}").text
        assert 'indexOf("var(")' in js  # the svgEl helper themes fill/stroke live
        assert "var(--ink)" in js


# ---- session-wide target UID ----


def test_set_target_redirects_back_and_prefills_everywhere(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    r = client.post("/target", data={"uid": "143", "next_url": "/trend"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/trend"
    # the report page shows the target panel and pre-fills the trace box
    page = client.get("/analysis/Project2").text
    assert "Target activity" in page and 'value="143"' in page
    # the trend page focuses automatically (no ?target= needed)
    page = client.get("/trend").text
    assert "Focus activity UID 143" in page
    # compare shows the target's movement between the two versions
    page = client.get("/compare").text
    assert "Focus activity UID 143" in page and "Computed finish moved" in page


def test_measure_to_uid_box_focuses_any_activity(client: TestClient) -> None:
    """Operator item 3: the header 'Measure to' control keeps the milestone dropdown and adds a
    UID box that measures to ANY activity by UniqueID (a non-milestone, or a UID only in an older
    version). The dropdown unions milestones across versions; the box covers everything else."""
    _upload(client, "Project5")
    home = client.get("/").text
    # the UID box + Set button render on every page (via the header)
    assert "sf-uid-form" in home and 'placeholder="any UID' in home and ">Set<" in home
    # any UID absent from the milestone dropdown is still accepted, shown as a custom target
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    assert 'value="999999" selected>UID 999999 (custom)' in client.get("/").text
    # the milestone dropdown remains available (Project finish = the whole schedule)
    assert "Project finish (whole schedule)" in home


def test_target_form_returns_to_current_page_and_reaches_card_and_wbs(client: TestClient) -> None:
    """The header Target-UID form shipped next_url hardcoded to '/', so setting a target always
    bounced to the dashboard — looking like nothing changed. target.js now keeps you on the
    current page, and the target is reflected on the card + WBS pages (they ignored it before)."""
    _upload(client, "Project5")
    tjs = client.get("/static/target.js")
    assert tjs.status_code == 200
    assert "next_url" in tjs.text and "location.pathname" in tjs.text  # rewrites to current page
    assert 'src="/static/target.js?v=' in client.get("/").text  # every page (cache-busted)
    assert "name=next_url" in client.get("/analysis/Project5").text  # the field target.js drives
    # with a target set, the card and WBS pages now show its focus panel
    client.post("/target", data={"uid": "143", "next_url": "/"})
    assert "Target activity" in client.get("/card/Project5").text
    assert "Target activity" in client.get("/wbs/Project5").text


def test_explicit_blank_target_overrides_the_session_target(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    # the Focus form submitted blank (the old 422 crash) clears focus for that view only
    r = client.get("/trend?target=")
    assert r.status_code == 200
    assert "Focus activity UID" not in r.text


def test_blank_or_invalid_uid_clears_the_target(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/target", data={"uid": "  ", "next_url": "/"})
    assert "Target activity" not in client.get("/analysis/Project2").text
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/target", data={"uid": "abc", "next_url": "/"})
    assert "Target activity" not in client.get("/analysis/Project2").text


def test_target_absent_from_a_version_degrades_gently(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    page = client.get("/analysis/Project2").text
    assert "does not contain UniqueID 999999" in page


def test_target_endpoint_truncates_the_analyzed_population() -> None:
    """Setting a Target UID makes it the analysis ENDPOINT: every metric/visual is restricted to
    that activity + its drivers (work beyond it is omitted), and a banner says so on every page."""
    st = SessionState()
    c = TestClient(create_app(st))
    data = (GOLDEN / "project2_5" / "Project2.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project2.mspdi.xml", data, "text/xml")})
    raw = next(iter(st.schedules.values()))
    full = sum(1 for t in raw.tasks if not t.is_summary)

    c.post("/target", data={"uid": "143", "next_url": "/"})
    scoped = st.scope(raw)
    kept = sum(1 for t in scoped.tasks if not t.is_summary)
    assert 1 <= kept < full  # truncated to UID 143 + its drivers
    assert any(t.unique_id == 143 for t in scoped.tasks)  # the target itself is retained
    page = c.get("/analysis/Project2").text
    assert "Analysis endpoint: UID 143" in page and "omitted" in page  # banner on the page

    # clearing the target restores the full population and drops the banner everywhere
    c.post("/target", data={"uid": "", "next_url": "/"})
    assert sum(1 for t in st.scope(raw).tasks if not t.is_summary) == full
    assert "Analysis endpoint:" not in c.get("/analysis/Project2").text


def test_endpoint_banner_warns_when_target_missing(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    page = client.get("/analysis/Project2").text
    assert "Endpoint UID 999999 not found" in page  # nothing truncated; the UID is flagged


def test_target_redirect_never_leaves_the_app(client: TestClient) -> None:
    for evil in ("//evil.example", "http://evil.example/x", "javascript:alert(1)"):
        r = client.post("/target", data={"uid": "1", "next_url": evil}, follow_redirects=False)
        assert r.headers["location"] == "/"


def test_wipe_clears_the_target(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/session/wipe")
    _upload(client, "Project2")
    assert "Target activity" not in client.get("/analysis/Project2").text


# ---- no file-count cap (v4 grouped ingestion: a whole folder of versions loads at once) ----


def test_upload_has_no_file_count_cap(client: TestClient) -> None:
    """The old 100-file batch cap is removed (v4): a project's whole version history — or a
    recursive folder of them — loads in one go, never truncated or refused. Each file gets
    byte-unique content (trailing newlines): identical bytes would (correctly, ADR-0259)
    collapse to one loaded file, and this test needs n real files."""
    data = EXAMPLE.read_bytes()
    n = MAX_FILES + 25  # comfortably past the old cap
    files = [("files", (f"v{i}.json", data + b"\n" * i, "application/json")) for i in range(n)]
    page = client.post("/upload", files=files).text
    assert "batch cap" not in page  # the cap message is gone
    assert f"Loaded {n}:" in page  # every file accepted


def test_every_off_spine_rail_entry_carries_a_takeaway() -> None:
    """ADR-0311: the DoD requires a nav entry WITH a takeaway.

    A numbered chapter surfaces its takeaway through the Continue segue. An off-spine page has no
    segue by design, so its takeaway had nowhere to go — and all six Setup entries shipped with
    ``""``. They now carry real text, rendered as the nav link's ``title``. Pinned because a
    half-filled rail is exactly the silent-omission class this round was cleaning up: four of six
    would have looked deliberate.

    ADR-0425 split that one mixed rail into FORENSICS / LIBRARY / CONTROL / SETUP, so this walks
    EVERY off-spine rail rather than the one named "SETUP" — a hand-named rail is a stale list
    waiting to happen, and a new rail added with blank takeaways would have passed unseen.
    """
    from schedule_forensics.web.app import _OFF_SPINE, _SPINE

    rails = [(label, chapters) for label, chapters in _SPINE if label in _OFF_SPINE]
    assert {label for label, _ in rails} == _OFF_SPINE, "an off-spine rail is declared but absent"
    for label, chapters in rails:
        missing = [c.label for c in chapters if not c.takeaway.strip()]
        assert not missing, f"{label} entries with no takeaway: {missing}"
        # and a takeaway is a sentence, not a label echo
        for c in chapters:
            assert c.takeaway != c.label
            assert c.takeaway.endswith("."), f"{c.label}: takeaway should read as a sentence"


def test_off_spine_rails_are_navigable_and_stay_out_of_the_story(client: TestClient) -> None:
    """ADR-0425: the prototype's FORENSICS / LIBRARY / CONTROL rails, and the invariant that
    promoting a page to one is a NAV move only.

    Three properties, each of which failed before the split:
      1. Every off-spine rail renders with its label and its entries' links.
      2. No off-spine entry enters ``_STORY_ORDER`` — the Continue segue and the progress dashes
         still walk Import → Mission Control → 01…12 and nothing else.
      3. Chapter membership is untouched: /integrity and /scorecards still resolve to Chapter 02
         and /evm to Chapter 07 through ``_TITLE_TO_CHAPTER``, so their kickers do not move.
    """
    from schedule_forensics.web.app import _OFF_SPINE, _SPINE, _STORY_ORDER, _TITLE_TO_CHAPTER

    page = client.get("/").text
    for label in ("FORENSICS", "LIBRARY", "CONTROL", "SETUP"):
        assert f">{label}</span>" in page, f"{label} rail missing from the nav"
    for route in ("/integrity", "/workbench", "/evm", "/margin", "/standards", "/scorecards"):
        assert f'href="{route}"' in page, f"{route} unreachable from the nav"

    # Partition the rails EXHAUSTIVELY. Asserting only "no off-spine page is in the story order"
    # is circular — both sides read `_OFF_SPINE`, so dropping a rail from it moves the page and
    # the expectation together and the check stays green (this mutant survived until it didn't).
    # The story rails are therefore named independently, and every _SPINE section must land in
    # exactly one of the two sets.
    story_rails = {
        "LOAD",
        "OVERVIEW",
        "ACT I · SITUATION",
        "ACT II · DIAGNOSIS",
        "ACT III · OUTLOOK",
    }
    assert {label for label, _ in _SPINE} == story_rails | _OFF_SPINE
    assert not (story_rails & _OFF_SPINE)
    assert [c.label for c in _STORY_ORDER] == [
        c.label for label, chs in _SPINE if label in story_rails for c in chs
    ]
    assert [c.num for c in _STORY_ORDER if c.num] == [f"{n:02d}" for n in range(0, 13)]

    assert _TITLE_TO_CHAPTER["Schedule Integrity"].num == "02"
    assert _TITLE_TO_CHAPTER["Assessment Scorecards"].num == "02"
    assert _TITLE_TO_CHAPTER["EVM"].num == "07"


def test_per_file_rail_entries_are_skipped_until_a_file_is_loaded(client: TestClient) -> None:
    """ADR-0425: `@wbs` / `@card` have no URL before an import, so the LIBRARY rail must DROP
    them rather than render them pointing at "/" — the "skipped, not broken" rule the folded beats
    and the role Start-here cards already follow (ADR-0255). A dead link that silently lands on the
    dropzone is the failure this guards."""
    from schedule_forensics.web.app import _SPINE

    empty = client.get("/").text
    assert ">LIBRARY</span>" in empty  # the rail still renders — Workbench and EVM resolve
    assert "WBS Rollup" not in empty
    assert "Schedule ID Card" not in empty

    _upload(client, "Project5")

    loaded = client.get("/").text
    assert "WBS Rollup" in loaded and "Schedule ID Card" in loaded
    assert 'href="/wbs/Project5"' in loaded and 'href="/card/Project5"' in loaded
    # and the promoted entries are the ONLY place those routes appear in the nav now
    library = next(chs for label, chs in _SPINE if label == "LIBRARY")
    assert {c.route for c in library} == {"/workbench", "@wbs", "@card", "/evm"}


def test_rank12_pages_all_carry_a_takeaway_and_a_context_line() -> None:
    """ADR-0311 rank 12: the DoD's takeaway h1 + context line, on all six Library/Setup pages.

    Five of the six had neither and `/margin` had an h1 with no lede. The headline must state a
    FINDING, not a topic (`DESIGN-SYSTEM.md` §5), and every figure in it must already be rendered
    further down the same page — so this asserts the elements exist AND that the headline is not
    merely the page's own title echoed back.
    """
    import re

    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    golden = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
    client = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (golden / f"{name}.mspdi.xml").read_bytes()
        assert (
            client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        ).status_code == 200

    topics = {"metric workbench", "groups & filters", "standards & execution", "margin dashboard"}
    for url in (
        "/workbench",
        "/groups",
        "/standards",
        "/margin",
        "/card/Project5",
        "/wbs/Project5",
    ):
        page = client.get(url).text
        h1 = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page, re.S)
        lede = re.search(r'<p class="page-lede"[^>]*>(.*?)</p>', page, re.S)
        assert h1 is not None, f"{url}: no takeaway h1"
        assert lede is not None, f"{url}: no context line"
        text = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
        assert len(text) > 20, f"{url}: takeaway too short to be a finding: {text!r}"
        assert text.lower() not in topics, f"{url}: takeaway is a topic, not a finding: {text!r}"
        assert re.sub(r"<[^>]+>", "", lede.group(1)).strip(), f"{url}: context line is empty"
