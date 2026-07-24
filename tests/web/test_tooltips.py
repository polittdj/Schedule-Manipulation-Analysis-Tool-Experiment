"""One tooltip per hover + a 1.5s hover-intent delay (ADR-0286).

The operator reported two overlapping tooltips on the /analysis DCMA-14 table: the rich
``.dcma-tip`` callout AND the browser's own native tooltip, because the trigger carried a
``title=`` as a no-CSS fallback. These pins lock the fix:

* every page loads ``tooltips.js``, which retires a native ``title`` wherever a custom tooltip
  already covers the trigger and promotes the remaining plain titles to the shared styled callout;
* both CSS tooltip families reveal on a ``transition-delay`` of ``--sf-tip-delay`` (1.5s) rather
  than appearing instantly, so a tooltip only shows once the pointer RESTS on the target;
* the JS-positioned floating tip waits the same interval via ``window.SF_TIP_DELAY_MS``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

STATIC = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static"
GOLD = Path(__file__).resolve().parents[2] / "tests/fixtures/golden/project2_5"


ANALYSIS = "/analysis/Project5"


def _client_loaded() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLD / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_tooltips_js_is_loaded_on_every_page() -> None:
    """The de-duplication must be global — a page that misses it shows doubled tooltips."""
    c = _client_loaded()
    for page in ("/", ANALYSIS, "/trend", "/settings", "/help", "/sra", "/risks"):
        assert "/static/tooltips.js" in c.get(page).text, page


def test_tooltips_js_retires_the_native_title_when_a_custom_tip_exists() -> None:
    js = (STATIC / "tooltips.js").read_text(encoding="utf-8")
    # the trigger families that already own a styled tooltip
    assert "data-sf-hint" in js and "dcma-metric" in js and "dcma-tip" in js
    # the native tooltip is removed, and its text preserved rather than discarded
    assert 'removeAttribute("title")' in js
    assert 'setAttribute("data-sf-title"' in js
    # replaced elements cannot host ::after, so they must keep their native title
    assert "NO_PSEUDO" in js and "INPUT" in js and "SELECT" in js
    # late-rendered charts/tables are normalised too
    assert "MutationObserver" in js


def test_shared_delay_is_1500ms_and_1_5s() -> None:
    """One source of truth per layer, and the two must agree."""
    assert "window.SF_TIP_DELAY_MS = 1500" in (STATIC / "tooltips.js").read_text(encoding="utf-8")
    assert "--sf-tip-delay:1.5s" in (STATIC / "hud.css").read_text(encoding="utf-8")


def test_css_tooltips_reveal_on_a_delay_not_instantly() -> None:
    """A ``transition-delay`` reveal is what makes the tooltip cancellable: moving the cursor away
    before it elapses means it never paints. An instant ``display``/``content`` flip could not."""
    hud = (STATIC / "hud.css").read_text(encoding="utf-8")
    # the callout is always in the box tree but hidden, and the hover rule delays the reveal
    assert "[data-sf-hint]::after{" in hud
    assert "visibility:hidden" in hud
    assert "transition:opacity .12s linear var(--sf-tip-delay)" in hud

    app_css = (STATIC / "app.css").read_text(encoding="utf-8")
    # the .dcma-tip family moved off `display` (which cannot transition) onto opacity/visibility
    assert "transition: opacity .12s linear var(--sf-tip-delay)" in app_css
    assert ".dcma-metric:hover + .dcma-tip" in app_css
    dcma_rule = app_css.split(".dcma-tip {", 1)[1].split("}", 1)[0]
    # `display` cannot be transitioned — leaving it would make the reveal instant
    assert "display: none" not in dcma_rule


def test_floating_tip_waits_for_hover_intent_and_cancels_on_leave() -> None:
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "window.SF_TIP_DELAY_MS" in js  # shares the one delay constant
    assert "setTimeout(show, delay)" in js  # reveal is deferred
    assert "clearTimeout(timer)" in js  # leaving early cancels it
    assert 'row.addEventListener("mouseenter", showLater)' in js
    # keyboard focus is already deliberate — it should not be delayed
    assert 'row.addEventListener("focus", show)' in js


def test_dcma_check_cell_no_longer_ships_a_duplicate_native_title() -> None:
    """The reported case: the DCMA-14 check name rendered a rich tip AND a plain-text title.

    The server still emits ``title=`` (it is the no-JS/export fallback), so the guarantee is that
    the client-side normaliser can find and retire it — i.e. the trigger is one of the recognised
    custom-tooltip families.
    """
    c = _client_loaded()
    html = c.get(ANALYSIS).text
    assert "dcma-metric" in html and "dcma-tip" in html
    # the trigger carries the class tooltips.js keys off, on the same element as the title
    marker = "class=dcma-metric"
    assert marker in html
    frag = html.split(marker, 1)[1][:400]
    assert "title=" in frag, "the fallback title must still be present for tooltips.js to retire"
