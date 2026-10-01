"""LODESTAR 2.0's studio in a real browser (ADR-0543): what the operator does, measured where it
happens.

* **A whole session is one page load.** Load a list, name the slide, scope the dates, set the
  data date, pick and link two items, undo, switch the marking, visit the other page and come
  back: every change is a studio call, never a navigation.
* **Linking.** Clicking a predecessor then a successor on the slide fills the From / To lists,
  rings and tags them FROM / TO, and Add draws the link with the chosen type; DRAGGING one item
  onto another adds the link too (a dashed lead follows the pointer).
* **The keyboard.** Ctrl+Z / Ctrl+Shift+Z undo and redo (never while typing in a field); Ctrl+K
  opens the command palette, typing filters it, Enter runs the first match, Esc closes it.
* **The tour** starts by itself once, after the first list is loaded, at STEP 2 OF 7 — Back,
  Next, Finish and Esc work, and it never starts by itself again.
* **The scrubber** moves the red line while it is dragged and commits ONE data date on release.
* **Full screen** opens and closes; a **Show me** demo runs on a preview and changes neither the
  session nor its log.
* **Print** shows the slide zone alone — both marking bars, a white ground, no credit — and a
  page prints on ONE sheet, Letter or A4 (the lead's 2026-10-01 fix: the frame had made a
  second sheet that repeated the slide).
* **Reduced motion** stills the slide's reveal.
* **The slide's ink order** — every link shaft under every item, every arrowhead over them — and
  every outside label carries a halo in the panel colour (``paint-order: stroke``, 0.42 x its
  size), while a label inside its bar carries none.
* **Contrast** — every visible text on the launch page, the empty studio, a loaded Timeline and
  a loaded Compare, and in the palette, the tour, the DATA drawer, the open handling drawer and a
  toast, reaches WCAG AA (4.5:1; 3:1 for large text) in all four views; every text on the slide
  reaches 4.5:1 against its halo (or the slide's ground). The lead's sweep found 93 failures
  before the 2026-10-01 token fix and none after; its JavaScript is reused here.

Each load-bearing check has a ``test_mutation_*`` twin that breaks the product (a style injected
into the page, or the studio's script rewritten in the server's asset table in memory — never on
disk) and asserts the SAME check goes red by name.
"""

from __future__ import annotations

import datetime as dt
import re
import socketserver
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from lodestar_probe import ROWS, upload

from schedule_forensics.lodestar import server as server_mod
from schedule_forensics.lodestar.server import LodestarServer, LodestarState
from schedule_forensics.web.htmlkit import CUI_MARKING, UNCLASSIFIED_MARKING
from web.browser_chrome import chrome_kwargs
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2026, 9, 30)
VIEWS = ("dark", "bright", "contrast", "console")
#: The example list's items (the template's own rows) the tests link by name.
ITEM_A, ITEM_B, ITEM_C = "Boots 1", "Uncrewed Lander Campaign", "CDR"


@dataclass
class Studio:
    """One LODESTAR server and one browser page on it."""

    server: LodestarServer
    state: LodestarState
    page: Any

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


@contextmanager
def _studio(
    browser: Any,
    *,
    view: str = "dark",
    height: int = 900,
    reduced: bool = True,
    tour_seen: bool = True,
    patch: dict[str, tuple[str, str]] | None = None,
) -> Iterator[Studio]:
    """A fresh server (an empty session, its clock fixed) and a fresh page in ``view``.
    ``patch`` rewrites a served asset IN MEMORY (``name -> (old, new)``) — a mutation of the
    product the browser runs, never of the file on disk."""
    state = LodestarState()
    srv = LodestarServer(0, state, TODAY)
    for name, (old, new) in (patch or {}).items():
        data, ct = srv.assets[name]
        assert old.encode() in data, f"the mutation's anchor moved in {name}: {old!r}"
        srv.assets[name] = (data.replace(old.encode(), new.encode()), ct)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    ctx = browser.new_context(
        viewport={"width": 1440, "height": height},
        reduced_motion="reduce" if reduced else "no-preference",
    )
    seed = f"localStorage.setItem('lodestar-view', '{view}');"
    if tour_seen:
        seed += " sessionStorage.setItem('lodestar-tour-seen', '1');"
    ctx.add_init_script(f"try {{ {seed} }} catch (e) {{}}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        yield Studio(srv, state, page)
        assert errors == [], errors
    finally:
        ctx.close()
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)


def _state(page: Any) -> dict[str, Any]:
    return dict(page.evaluate("() => LSStudio.state()"))


def _load_example(page: Any, base: str, path: str = "/onepager") -> None:
    page.goto(base + path)
    page.click("main [data-ls-example]")
    page.wait_for_function("() => window.LSStudio && LSStudio.state().layout !== null")


def _key(page: Any, name: str) -> str:
    keys = [x["key"] for x in _state(page)["linkable"] if f"· {name} (" in x["label"]]
    assert len(keys) == 1, name
    return str(keys[0])


def _centre(page: Any, key: str) -> tuple[float, float]:
    """The screen centre of an item's bar or diamond on the slide."""
    box = page.evaluate(
        """(k) => { const g = document.querySelector('#lsSlide [data-key="' + k + '"] .lss-glyph');
          g.scrollIntoView({block: 'center'}); const r = g.getBoundingClientRect();
          return [r.x + r.width / 2, r.y + r.height / 2]; }""",
        key,
    )
    return float(box[0]), float(box[1])


def _act(page: Any, verb: str, fields: dict[str, Any]) -> str | None:
    """Run one studio call in the page (``LSStudio.act``) and wait for its answer."""
    return page.evaluate(  # type: ignore[no-any-return]
        "async ([v, f]) => { const s = await LSStudio.act(v, f); return s ? s.label : null; }",
        [verb, fields],
    )


def _list_file(tmp_path: Path) -> str:
    path = tmp_path / "Program list.xlsx"
    path.write_bytes(twin_xlsx(ROWS, omit_blank=True))
    return str(path)


# ── a whole session, one page load ────────────────────────────────────────────────────────────


def _session_of_edits(s: Studio, tmp_path: Path) -> int:
    """Upload → title → window → data date → link → undo → marking → Compare and back; the
    number of documents the page loaded after its first (counted from the browser's own
    ``load`` events — a document's ``performance`` entries cannot count it: each new document
    starts its own list at one; and a tab switch's ``pushState`` is not a load), plus one if the
    first document's marker is gone."""
    page = s.page
    page.goto(s.base + "/onepager")
    navigations = _watch_loads(page)
    page.set_input_files("#lsFile", _list_file(tmp_path))
    page.wait_for_function("() => LSStudio.state().layout !== null")
    page.fill("#lsTitle", "Program review")
    page.press("#lsTitle", "Enter")
    page.wait_for_function("() => LSStudio.state().title === 'Program review'")
    page.fill("#lsWinFrom", "2027-01-01")
    page.fill("#lsWinTo", "2027-12-31")
    page.click("#lsWindowForm button[value=apply]")
    page.wait_for_function("() => (LSStudio.state().window || [])[1] === '2027-12-31'")
    page.fill("#lsToday", "2027-03-01")
    page.wait_for_function("() => LSStudio.state().dataDate === '2027-03-01'")
    keys = {x["label"]: x["key"] for x in _state(page)["linkable"]}
    page.select_option("#lsFrom", keys["Alpha · Design Review (1/15/27)"])
    page.select_option("#lsTo", keys["Alpha · Build (2/1/27 to 4/15/27)"])
    page.click("#lsAddLink")
    page.wait_for_function("() => LSStudio.state().links.length === 1")
    page.click("#lsUndo")
    page.wait_for_function("() => LSStudio.state().links.length === 0")
    page.click("#lsMarking")
    page.wait_for_function("() => LSStudio.state().marking.cls === 'unclassified'")
    page.click("header a[data-ls-tab=compare]")
    page.wait_for_function("() => LSStudio.state().page === 'compare'")
    page.click("header a[data-ls-tab=timeline]")
    page.wait_for_function("() => LSStudio.state().page === 'timeline'")
    return _loads(page, navigations)


def _watch_loads(page: Any) -> list[str]:
    """Start counting the documents ``page`` loads from now on, and mark this one."""
    loads: list[str] = []
    page.on("load", lambda p: loads.append(p.url))
    page.evaluate("() => { window.lsSameDocument = true; }")
    return loads


def _loads(page: Any, loads: list[str]) -> int:
    """How many documents loaded since :func:`_watch_loads` — at least one if its mark is gone."""
    gone = not page.evaluate("() => window.lsSameDocument === true")
    return max(len(loads), int(gone))


def test_a_whole_session_of_edits_is_one_page_load(browser: Any, tmp_path: Path) -> None:
    """Every change above is a studio call: ONE navigation for the whole session; the server
    holds every change, the log names each, and the bars follow the marking at once."""
    with _studio(browser) as s:
        assert _session_of_edits(s, tmp_path) == 0  # not one new document
        assert s.page.url.endswith("/onepager")
        bars = s.page.eval_on_selector_all(".cui-banner", "ns => ns.map(n => n.textContent.trim())")
        assert bars == [UNCLASSIFIED_MARKING] * 2
        assert s.state.onepager_title == "Program review" and s.state.unclassified is True
        assert s.state.onepager_today == dt.date(2027, 3, 1) and s.state.onepager_links == ()
        assert [st.label for st in reversed(s.state.history.past)] == [
            "Marking switched to Unclassified",
            "Data date 2027-03-01",
            "Date window 2027-01-01 → 2027-12-31",
            "Slide title changed",
            "List loaded: Program list.xlsx",
        ]


def test_mutation_a_studio_that_lets_forms_post_navigates(browser: Any, tmp_path: Path) -> None:
    """MUTATION: the studio's script with no studio actions (every form posts as it is) — the
    title edit alone now loads a new document, and the same count sees it."""
    patch = {
        "lodestar_studio.js": (
            "var API = { title: 1, window: 1, today: 1, clear: 1, links: 1, swap: 1, "
            "example: 1, risks: 1 };",
            "var API = {};",
        )
    }
    with _studio(browser, patch=patch) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        page.set_input_files("#lsFile", _list_file(tmp_path))
        page.wait_for_function("() => LSStudio.state().layout !== null")
        loads = _watch_loads(page)
        with page.expect_navigation():
            page.fill("#lsTitle", "Program review")
            page.press("#lsTitle", "Enter")
        page.wait_for_load_state()
        assert _loads(page, loads) >= 1
        assert s.state.onepager_title == "Program review"


# ── linking: click-pick, then Add; drag one item onto another ────────────────────────────────


def test_click_pick_two_items_then_add_draws_the_link(browser: Any) -> None:
    with _studio(browser, height=1400) as s:
        page = s.page
        _load_example(page, s.base)
        a, c = _key(page, ITEM_A), _key(page, ITEM_C)
        assert page.is_disabled("#lsAddLink")
        page.mouse.click(*_centre(page, a))
        assert page.input_value("#lsFrom") == a and page.input_value("#lsTo") == ""
        assert "now pick the successor" in page.text_content("#lsHintText")
        page.mouse.click(*_centre(page, c))
        assert page.input_value("#lsTo") == c
        rings = page.eval_on_selector_all(
            "#lsSlide .lss-ring-tag",
            "ns => ns.map(n => n.getAttribute('class') + ':' + n.textContent)",
        )
        assert rings == ["lss-ring-tag is-from:FROM", "lss-ring-tag is-to:TO"], rings
        hint = page.text_content("#lsHintText")
        assert hint.startswith("From ") and hint.endswith(
            "choose the type and press Add logic link."
        )
        page.click("#lsKind label:has-text('SS')")
        page.click("#lsAddLink")
        page.wait_for_function("() => LSStudio.state().links.length === 1")
        links = [(x["pred"], x["succ"], x["kind"], x["drawn"]) for x in _state(page)["links"]]
        assert links == [(a, c, "SS", True)]
        assert page.input_value("#lsFrom") == "" and page.locator("#lsSlide .lss-ring").count() == 0
        assert page.locator("#lsSlide .lss-shaft").count() == 1


def _drag(page: Any, a: str, b: str) -> dict[str, Any]:
    """Press on ``a``, drag in steps onto ``b`` and release; what the lead showed mid-drag."""
    x0, y0 = _centre(page, a)
    x1, y1 = _centre(page, b)
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x0 + 12, y0 + 4, steps=4)
    page.mouse.move(x1, y1, steps=12)
    mid = page.evaluate(
        """() => ({lead: document.querySelectorAll('#lsSlide .lss-drag line').length,
                   text: (document.querySelector('#lsSlide .lss-drag text') || {}).textContent})"""
    )
    page.mouse.up()
    return dict(mid)


def test_dragging_one_item_onto_another_adds_the_link(browser: Any) -> None:
    """A tall viewport, so the drop target is on screen (a 900-px one put it off-screen)."""
    with _studio(browser, height=1600) as s:
        page = s.page
        _load_example(page, s.base)
        a, b = _key(page, ITEM_A), _key(page, ITEM_B)
        mid = _drag(page, a, b)
        assert mid == {"lead": 1, "text": "release to link (FS)"}, mid
        page.wait_for_function("() => LSStudio.state().links.length === 1")
        assert [(x["pred"], x["succ"], x["kind"]) for x in _state(page)["links"]] == [(a, b, "FS")]
        assert page.locator("#lsSlide .lss-drag line").count() == 0  # the lead is gone
        assert _state(page)["history"][0] == f"Add link {ITEM_A} → {ITEM_B} (FS)"


def test_mutation_a_drop_that_adds_nothing_is_named(browser: Any) -> None:
    """MUTATION: the studio's script with the drop's add removed — the same drag leaves no link."""
    patch = {"lodestar_studio.js": ("if (d.over && d.target) addLink(", "if (false) addLink(")}
    with _studio(browser, height=1600, patch=patch) as s:
        page = s.page
        _load_example(page, s.base)
        _drag(page, _key(page, ITEM_A), _key(page, ITEM_B))
        page.wait_for_timeout(400)  # time for a call that should never be made
        assert _state(page)["links"] == [] and s.state.onepager_links == ()


# ── the keyboard: undo / redo, the palette ────────────────────────────────────────────────────


def test_ctrl_z_undoes_and_ctrl_shift_z_redoes_but_never_while_typing(browser: Any) -> None:
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        _act(
            page, "links", {"action": "add", "pred": _key(page, ITEM_A), "succ": _key(page, ITEM_C)}
        )
        page.focus("#lsTitle")
        page.keyboard.press("Control+z")  # the field's own undo, never the studio's
        page.wait_for_timeout(300)
        assert len(_state(page)["links"]) == 1
        page.click("#lsPanel h1")  # off the field
        page.keyboard.press("Control+z")
        page.wait_for_function("() => LSStudio.state().links.length === 0")
        assert _state(page)["canRedo"] is True
        page.keyboard.press("Control+Shift+z")
        page.wait_for_function("() => LSStudio.state().links.length === 1")
        assert s.state.onepager_links != ()


def test_the_command_palette_filters_runs_the_first_match_and_closes(browser: Any) -> None:
    with _studio(browser) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        page.keyboard.press("Control+k")
        page.wait_for_selector("#lsPalette:not([hidden])")
        page.wait_for_function("() => document.activeElement.id === 'lsPaletteQ'")
        everything = page.locator("#lsPalette .ls-palette-item").count()
        page.keyboard.type("example list")
        labels = page.eval_on_selector_all(
            "#lsPalette .ls-palette-item span:first-child", "ns => ns.map(n => n.textContent)"
        )
        assert 0 < len(labels) < everything and labels[0] == "Load the example list", labels
        assert all("example" in x.lower() for x in labels), labels
        page.keyboard.press("Enter")
        page.wait_for_function("() => LSStudio.state().layout !== null")
        assert page.is_hidden("#lsPalette") and s.state.onepager is not None
        page.keyboard.press("Control+k")
        page.wait_for_function("() => document.activeElement.id === 'lsPaletteQ'")
        page.keyboard.type("zzz no such command")
        assert page.text_content("#lsPaletteList") == "No command matches."
        page.keyboard.press("Escape")
        assert page.is_hidden("#lsPalette")


# ── the guided tour ──────────────────────────────────────────────────────────────────────────


def _tour(page: Any) -> tuple[str, str, str, bool]:
    return (
        page.text_content("#lsTourStep") or "",
        page.text_content("#lsTourTitle") or "",
        page.text_content("#lsTourNext") or "",
        page.is_disabled("[data-ls-tour-back]"),
    )


def test_the_tour_starts_once_after_the_first_list_and_steps(browser: Any) -> None:
    with _studio(browser, tour_seen=False) as s:
        page = s.page
        _load_example(page, s.base)
        page.wait_for_selector("#lsTour:not([hidden])", timeout=5000)
        assert _tour(page) == ("STEP 2 OF 7", "Name the slide", "Next", False)
        page.click("[data-ls-tour-next]")
        assert _tour(page)[:2] == ("STEP 3 OF 7", "Set the data date")
        page.click("[data-ls-tour-back]")
        page.click("[data-ls-tour-back]")
        assert _tour(page) == ("STEP 1 OF 7", "Start with your list", "Next", True)
        for _ in range(6):
            page.click("[data-ls-tour-next]")
        assert _tour(page) == ("STEP 7 OF 7", "Mark it right", "Finish", False)
        page.click("[data-ls-tour-next]")  # Finish
        assert page.is_hidden("#lsTour")
        page.click("[data-ls-tour]")  # the header's Tour starts it at step 1
        assert _tour(page)[0] == "STEP 1 OF 7"
        page.keyboard.press("Escape")
        assert page.is_hidden("#lsTour")
        # a second list load, the same way (the rail's example button): never by itself again
        steps = len(s.state.history.past)
        page.click("#lsRail [data-ls-example]")
        page.wait_for_function(f"() => LSStudio.state().history.length === {steps + 1}")
        page.wait_for_timeout(1200)  # past the 650-ms start the first load had
        assert page.is_hidden("#lsTour")


# ── the scrubber ─────────────────────────────────────────────────────────────────────────────


def test_the_scrubber_moves_the_red_line_and_commits_once_on_release(browser: Any) -> None:
    """A pointer drag: the red line and the date box follow the slider while it moves, nothing
    is committed until the release, and the release commits ONE step at the date shown."""
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        page.locator("#lsScrub").scroll_into_view_if_needed()
        line = "() => document.querySelector('#lsSlide .lss-dd line').getAttribute('x1')"
        x_before, steps_before = page.evaluate(line), len(s.state.history.past)
        box = page.locator("#lsScrubRange").bounding_box()
        value, span = (int(page.get_attribute("#lsScrubRange", a) or 0) for a in ("value", "max"))
        y = box["y"] + box["height"] / 2
        x = box["x"] + 8 + (box["width"] - 16) * value / span  # the thumb
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 120, y, steps=10)
        dragged = page.evaluate(line)
        shown = page.input_value("#lsToday")
        assert dragged != x_before and shown != TODAY.isoformat()
        assert len(s.state.history.past) == steps_before  # nothing committed while dragging
        page.mouse.up()
        page.wait_for_function(f"() => LSStudio.state().history.length === {steps_before + 1}")
        assert _state(page)["history"][0] == f"Data date {shown}"
        assert s.state.onepager_today == dt.date.fromisoformat(shown)


def _keyboard_scrub(s: Studio, *, then: str, keys: int = 12) -> tuple[dt.date, int, str]:
    """Focus the slider, press ArrowRight ``keys`` times, then either wait past the 700-ms
    gathering (``then="wait"``) or Tab away inside it (``then="tab"``). Returns ``(the data date
    the SERVER holds, the new log steps, the date the page shows)`` — once the page is quiet."""
    page = s.page
    _load_example(page, s.base)
    steps = len(s.state.history.past)
    page.focus("#lsScrubRange")
    for _ in range(keys):
        page.keyboard.press("ArrowRight")
    if then == "tab":
        page.keyboard.press("Tab")
    page.wait_for_function(
        f"() => LSStudio.state().history.length > {steps} && !LSStudio.view.busy"
        " && LSStudio.view.pendingToday === null",
        timeout=10_000,
    )
    page.wait_for_timeout(900)  # past a second (wrong) commit the old script would have made
    assert s.state.onepager_today is not None
    return s.state.onepager_today, len(s.state.history.past) - steps, _state(page)["dataDate"]


@pytest.mark.parametrize("then", ["wait", "tab"])
def test_keyboard_nudges_of_the_scrubber_commit_once(browser: Any, then: str) -> None:
    """Twelve ArrowRight presses move the data date twelve days — ONE step in the log, the page
    and the server agreeing — whether the operator waits or Tabs away at once (the lead's fix,
    2026-10-01: the old script committed a step per key and lost the keys pressed while a call was
    in flight: +2 / +5 / +3 days, 2 / 5 / 3 steps, measured)."""
    with _studio(browser) as s:
        got, steps, shown = _keyboard_scrub(s, then=then)
    assert (got, steps, shown) == (TODAY + dt.timedelta(days=12), 1, got.isoformat())


def test_mutation_a_scrubber_that_commits_every_key_is_named(browser: Any) -> None:
    """MUTATION: the keyboard's gathering removed (every nudge commits at once) — the same
    measurement sees more than one step, or a date short of twelve days."""
    patch = {"lodestar_studio.js": ("commitTimer = setTimeout(flushScrub, 700);", "flushScrub();")}
    with _studio(browser, patch=patch) as s:
        got, steps, _shown = _keyboard_scrub(s, then="wait")
    assert (got, steps) != (TODAY + dt.timedelta(days=12), 1), (got, steps)


def _slow_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server answers a studio title call 0.8 s late — the delay is the SERVER's (its body
    read, before the session lock), so the browser really has a call in flight meanwhile. (A
    Playwright route that sleeps would block the test's own thread instead, and the two calls
    would never overlap.)"""
    real = server_mod._Handler._json_body

    def late(self: Any, **kw: Any) -> dict[str, Any]:
        if self.path == "/api/title":
            time.sleep(0.8)
        return real(self, **kw)  # type: ignore[no-any-return]

    monkeypatch.setattr(server_mod._Handler, "_json_body", late)


def _scrub_during_a_slow_title(s: Studio) -> int:
    """Commit a title (answered late), then nudge the slider three days and Tab away while that
    call is still in flight; wait until the page is quiet. The log steps added."""
    page = s.page
    _load_example(page, s.base)
    steps = len(s.state.history.past)
    page.fill("#lsTitle", "Late title")
    page.press("#lsTitle", "Enter")  # the title call is in flight from here …
    assert page.evaluate("() => LSStudio.view.busy") is True
    page.focus("#lsScrubRange")
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    page.keyboard.press("Tab")  # … and the data date is committed while it still is
    assert page.evaluate("() => LSStudio.view.busy") is True, "the two calls did not overlap"
    page.wait_for_function("() => LSStudio.state().title === 'Late title'", timeout=10_000)
    page.wait_for_function(
        "() => !LSStudio.view.busy && LSStudio.view.pendingToday === null", timeout=10_000
    )
    page.wait_for_timeout(300)
    return len(s.state.history.past) - steps


def test_a_data_date_committed_while_a_call_is_in_flight_is_never_dropped(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A title change still on its way when the slider is nudged and left: the data date waits
    its turn and lands after it — both changes, two steps, in that order."""
    _slow_titles(monkeypatch)
    with _studio(browser) as s:
        assert _scrub_during_a_slow_title(s) == 2
        assert s.state.onepager_title == "Late title"
        assert s.state.onepager_today == TODAY + dt.timedelta(days=3)
        assert [x.label for x in s.state.history.past[-2:]] == [
            "Slide title changed",
            f"Data date {(TODAY + dt.timedelta(days=3)).isoformat()}",
        ]
        assert _state(s.page)["dataDate"] == (TODAY + dt.timedelta(days=3)).isoformat()


def test_mutation_a_commit_dropped_while_busy_is_named(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the waiting commit thrown away instead of kept — the same run lands the title
    alone, and the data date never."""
    _slow_titles(monkeypatch)
    patch = {
        "lodestar_studio.js": (
            "if (view.busy) { view.pendingToday = iso; return; }",
            "if (view.busy) return;",
        )
    }
    with _studio(browser, patch=patch) as s:
        assert _scrub_during_a_slow_title(s) == 1
        assert s.state.onepager_title == "Late title" and s.state.onepager_today is None


# ── the DATA drawer, the completion check, files dropped on the page ───────────────────────


def test_the_data_drawer_opens_shows_the_rows_and_survives_a_change(browser: Any) -> None:
    """v1's ▦ DATA: the panel's DATA button shows the parsed rows (pressed), keeps them open
    across a change (the region the script swaps in is re-rendered), and hides them again."""
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        assert page.is_hidden("#lsData")
        page.click("[data-ls-data]")
        assert page.is_visible("#lsData")
        assert page.get_attribute("[data-ls-data]", "aria-pressed") == "true"
        assert page.locator("#lsData tbody tr").count() == 6
        _act(page, "title", {"title": "Still open"})
        assert page.is_visible("#lsData") and page.locator("#lsData tbody tr").count() == 6
        page.click("[data-ls-data]")
        assert page.is_hidden("#lsData")
        assert page.get_attribute("[data-ls-data]", "aria-pressed") == "false"


_DROP = """async ([b64, name, selector]) => {
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const file = new File([bytes], name, {type: 'application/octet-stream'});
  const data = new DataTransfer();
  data.items.add(file);
  const target = document.querySelector(selector);
  target.dispatchEvent(new DragEvent('drop',
    {dataTransfer: data, bubbles: true, cancelable: true}));
}"""


def _drop(page: Any, rows: Any, name: str, selector: str) -> None:
    """Drop ``rows`` as a workbook called ``name`` onto ``selector`` (a real DataTransfer)."""
    import base64

    data = base64.b64encode(twin_xlsx(rows, omit_blank=True)).decode("ascii")
    page.evaluate(_DROP, [data, name, selector])


def test_a_list_dropped_anywhere_on_the_timeline_loads(browser: Any) -> None:
    with _studio(browser) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        _drop(page, ROWS, "Dropped list.xlsx", "#lsMain")
        page.wait_for_function("() => LSStudio.state().layout !== null")
        assert s.state.onepager is not None and s.state.onepager.source == "Dropped list.xlsx"


def test_compare_never_guesses_which_list_a_drop_is(browser: Any) -> None:
    """Dropped beside the slots, the workbook is refused by name — the page never guesses PRIOR
    or CURRENT — and nothing is sent; dropped ON a slot, it loads into that slot."""
    with _studio(browser) as s:
        page = s.page
        page.goto(s.base + "/onepager-compare")
        sent: list[str] = []
        page.on("request", lambda r: sent.append(r.url) if r.method == "POST" else None)
        _drop(page, ROWS, "Which one.xlsx", "#lsMain")
        page.wait_for_selector("#lsDropHint:not([hidden])")
        assert "never guesses" in (page.text_content("#lsDropHint") or "")
        page.wait_for_timeout(300)
        assert sent == [] and s.state.onepager_prior is None and s.state.onepager_current is None
        _drop(page, ROWS, "Prior list.xlsx", "#lsSlotPrior")
        page.wait_for_function("() => LSStudio.state().loaded.prior === true")
        assert s.state.onepager_prior is not None and s.state.onepager_current is None
        assert s.state.onepager_prior.source == "Prior list.xlsx"


# ── full screen, a demo ──────────────────────────────────────────────────────────────────────


def test_full_screen_opens_and_closes(browser: Any) -> None:
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        page.click("[data-ls-full]")
        page.wait_for_selector("#lsFull:not([hidden])")
        assert page.locator("#lsFullBox svg").count() == 1
        page.keyboard.press("Escape")
        assert page.is_hidden("#lsFull")
        page.click("[data-ls-full]")
        page.mouse.click(4, 450)  # the backdrop, beside the slide
        assert page.is_hidden("#lsFull")


@pytest.mark.parametrize("path,demo", [("/onepager", "links"), ("/onepager-compare", "compare")])
def test_a_show_me_demo_runs_and_changes_neither_the_session_nor_its_log(
    browser: Any, path: str, demo: str
) -> None:
    """The links demo on a loaded Timeline, the compare demo on an EMPTY Compare (shown on the
    example pair, never loaded): the caption shows, the demo rings an item, and afterwards the
    session's content and log are what they were."""
    with _studio(browser) as s:
        page = s.page
        if demo == "links":
            _load_example(page, s.base, path)
        else:
            page.goto(s.base + path)
        before = (s.state.onepager_links, s.state.onepager_prior, len(s.state.history.past))
        page.click(f"[data-ls-demo={demo}]")
        page.wait_for_selector("#lsDemoNote:not([hidden])")
        page.wait_for_selector("#lsSlide .lss-ring.is-demo", timeout=8000)
        assert page.text_content("#lsDemoText")
        page.wait_for_selector("#lsDemoNote", state="hidden", timeout=15000)
        after = (s.state.onepager_links, s.state.onepager_prior, len(s.state.history.past))
        assert after == before
        if demo == "compare":  # an empty page: the demo loaded nothing, logged nothing
            assert _state(page)["history"] == [] and _state(page)["layout"] is None


# ── print: the slide alone, one sheet ────────────────────────────────────────────────────────

_PRINT_PROBE = r"""() => {
  const visible = (el) => getComputedStyle(el).visibility === 'visible'
    && getComputedStyle(el).display !== 'none' && el.getClientRects().length > 0;
  const zone = document.querySelector('.ls-print-zone');
  const marks = [...zone.querySelectorAll('.ls-print-mark')];
  const stray = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const el = walker.currentNode.parentElement;
    if (!walker.currentNode.textContent.trim() || !el || zone.contains(el)) continue;
    if (visible(el)) stray.push(el.tagName + '.' + el.className + ': '
      + walker.currentNode.textContent.trim().slice(0, 30));
  }
  return {marks: marks.map(m => [visible(m), m.textContent.trim()]),
          ground: getComputedStyle(zone).backgroundColor,
          credit: [...document.querySelectorAll('a[href^="mailto:"]')].filter(visible).length,
          slide: visible(zone.querySelector('svg')), stray: stray.slice(0, 5)};
}"""


def _pdf_pages(page: Any, fmt: str) -> int:
    pdf = page.pdf(landscape=True, format=fmt, print_background=True, prefer_css_page_size=True)
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


@pytest.mark.parametrize("path", ["/onepager", "/onepager-compare"])
def test_print_is_the_slide_alone_marked_on_white_on_one_sheet(browser: Any, path: str) -> None:
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base, path)
        page.emulate_media(media="print")
        got = page.evaluate(_PRINT_PROBE)
        assert got["marks"] == [[True, CUI_MARKING], [True, CUI_MARKING]], got
        assert got["ground"] == "rgb(255, 255, 255)" and got["slide"], got
        assert got["credit"] == 0 and got["stray"] == [], got
        assert {fmt: _pdf_pages(page, fmt) for fmt in ("Letter", "A4")} == {"Letter": 1, "A4": 1}


def test_mutation_a_frame_left_in_the_print_flow_prints_two_sheets(browser: Any) -> None:
    """MUTATION: the frame back in the flow (the pre-fix ``position:static``) — the same count
    sees more than one sheet (the lead measured 2 per format; 3 here at this page's length)."""
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        page.add_style_tag(content="@media print{body.ls-app .ls-root{position:static!important}}")
        assert _pdf_pages(page, "Letter") >= 2  # measured 2-3 by viewport: the slide repeated


def test_mutation_a_credit_left_visible_in_print_is_named(browser: Any) -> None:
    """MUTATION: the status bar kept visible in print — the same probe counts its credit."""
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        page.add_style_tag(content="@media print{body.ls-app .ls-status *{visibility:visible}}")
        page.emulate_media(media="print")
        got = page.evaluate(_PRINT_PROBE)
        assert got["credit"] == 1 and got["stray"], got


# ── motion ───────────────────────────────────────────────────────────────────────────────────

_REVEAL = r"""() => {
  const svg = document.querySelector('#lsSlide svg');
  const moving = document.getAnimations().filter(a => a.effect && a.effect.target
    && a.effect.target.closest && a.effect.target.closest('#lsSlide'));
  return {reveal: svg.classList.contains('is-reveal'), moving: moving.length};
}"""


@pytest.mark.parametrize("reduced", [False, True], ids=["motion", "reduced-motion"])
def test_reduced_motion_stills_the_slides_reveal(browser: Any, reduced: bool) -> None:
    """A list loaded: the slide reveals itself (lanes fade, bars grow, shafts draw) — unless the
    operator asked for reduced motion, when it is simply there (nothing animates on it)."""
    with _studio(browser, reduced=reduced) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        page.click("main [data-ls-example]")
        page.wait_for_function("() => document.querySelector('#lsSlide svg') !== null")
        got = page.evaluate(_REVEAL)
    if reduced:
        assert got == {"reveal": False, "moving": 0}, got
    else:
        assert got["reveal"] is True and got["moving"] > 0, got


# ── the slide's ink order and its halos ───────────────────────────────────────────────────────

_ORDER = r"""() => {
  const svg = document.querySelector('#lsSlide svg');
  const after = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  const shafts = [...svg.querySelectorAll('.lss-shaft')];
  const items = [...svg.querySelectorAll('g.lss-item')];
  const heads = [...svg.querySelectorAll('g.lss-heads .lss-head')];
  const layers = [...svg.children].map(n => n.getAttribute('class') || n.tagName);
  return {shafts: shafts.length, items: items.length, heads: heads.length, layers: layers,
    shaftsUnder: shafts.every(s => items.every(i => after(s, i))),
    headsOver: heads.every(h => items.every(i => after(i, h)))};
}"""


def _order_problems(got: dict[str, Any]) -> list[str]:
    problems = []
    if not (got["shafts"] and got["heads"] and got["items"]):
        problems.append(f"counts: {got['shafts']} shafts, {got['heads']} heads")
    if not got["shaftsUnder"]:
        problems.append("shafts: a link shaft is painted over an item")
    if not got["headsOver"]:
        problems.append("heads: an arrowhead is painted under an item")
    layers = [c for c in got["layers"] if c.startswith("lss-") and c.split()[0] in _LAYERS]
    if [c.split()[0] for c in layers] != list(_LAYERS):
        problems.append(f"layers: {layers}")
    return problems


#: The design's z-order of the slide's layers (lodestar_slide.js's header), bottom to top.
_LAYERS = ("lss-shafts", "lss-items", "lss-heads", "lss-dd-layer", "lss-rings", "lss-drag")


def test_every_shaft_is_under_every_item_and_every_head_over_them(browser: Any) -> None:
    with _studio(browser) as s:
        page = s.page
        _load_example(page, s.base)
        _act(
            page, "links", {"action": "add", "pred": _key(page, ITEM_A), "succ": _key(page, ITEM_C)}
        )
        _act(
            page,
            "links",
            {"action": "add", "pred": _key(page, ITEM_B), "succ": _key(page, ITEM_A), "kind": "SS"},
        )
        page.wait_for_function(
            "() => document.querySelectorAll('#lsSlide .lss-shaft').length === 2"
        )
        assert _order_problems(page.evaluate(_ORDER)) == []


def test_mutation_shafts_painted_last_are_named(browser: Any) -> None:
    """MUTATION: the painter appends the shafts' layer AFTER the items — named by the same check."""
    # appending the (already placed) shafts' layer again MOVES it to after the items
    patch = {}
    patch["lodestar_slide.js"] = (
        "    svg.appendChild(items);\n",
        "    svg.appendChild(items);\n    svg.appendChild(shafts);\n",
    )
    with _studio(browser, patch=patch) as s:
        page = s.page
        _load_example(page, s.base)
        _act(
            page, "links", {"action": "add", "pred": _key(page, ITEM_A), "succ": _key(page, ITEM_C)}
        )
        page.wait_for_function(
            "() => document.querySelectorAll('#lsSlide .lss-shaft').length === 1"
        )
        problems = _order_problems(page.evaluate(_ORDER))
    assert any(p.startswith("shafts:") for p in problems), problems


_HALO = r"""() => {
  const probe = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  probe.setAttribute('fill', 'var(--bg-panel)');
  const svg = document.querySelector('#lsSlide svg'); svg.appendChild(probe);
  const panel = getComputedStyle(probe).fill; probe.remove();
  const L = LSStudio.state().layout;
  return [...svg.querySelectorAll('text.lss-label')].map(t => {
    const cs = getComputedStyle(t);
    return {inside: t.classList.contains('is-in'), stroke: cs.stroke,
            width: t.getAttribute('stroke-width'), order: cs.paintOrder, panel: panel,
            want: (0.42 * L.label_pt).toFixed(3), text: t.textContent};
  });
}"""


def _halo_problems(labels: list[dict[str, Any]]) -> list[str]:
    problems = []
    inside = [x for x in labels if x["inside"]]
    outside = [x for x in labels if not x["inside"]]
    if not inside or not outside:
        problems.append(f"sample: {len(inside)} inside and {len(outside)} outside labels")
    for x in outside:
        if (
            x["stroke"] != x["panel"]
            or x["width"] != x["want"]
            or not x["order"].startswith("stroke")
        ):
            problems.append(f"halo: {x['text']!r} stroke {x['stroke']} {x['width']} {x['order']}")
    for x in inside:
        if x["stroke"] != "none" or x["width"] is not None:
            problems.append(f"inside: {x['text']!r} carries a halo ({x['stroke']} {x['width']})")
    return problems


def test_outside_labels_carry_a_halo_and_inside_labels_none(browser: Any, tmp_path: Path) -> None:
    """The probe's list puts Build and Test INSIDE their bars and the two milestones outside."""
    with _studio(browser) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        page.set_input_files("#lsFile", _list_file(tmp_path))
        page.wait_for_function("() => LSStudio.state().layout !== null")
        assert _halo_problems(page.evaluate(_HALO)) == []
        # v1's completion check: the one row marked Complete carries the check, and the legend
        # names it
        done = page.evaluate(
            "() => [document.querySelectorAll('#lsSlide g.lss-items .lss-done').length,"
            " document.querySelectorAll('#lsSlide g.lss-legend[data-kind=done]').length]"
        )
        assert done == [1, 1], done


@pytest.mark.parametrize(
    "css,named",
    [
        (".lss-label{paint-order:normal}", "halo:"),
        (".lss-label.is-in{stroke:var(--bg-panel)}", "inside:"),
    ],
)
def test_mutation_a_lost_halo_or_a_haloed_inside_label_is_named(
    browser: Any, tmp_path: Path, css: str, named: str
) -> None:
    with _studio(browser) as s:
        page = s.page
        page.goto(s.base + "/onepager")
        page.set_input_files("#lsFile", _list_file(tmp_path))
        page.wait_for_function("() => LSStudio.state().layout !== null")
        page.add_style_tag(content=css)
        problems = _halo_problems(page.evaluate(_HALO))
    assert any(p.startswith(named) for p in problems), problems


# ── contrast: every visible text, every view (the lead's sweep, reused) ──────────────────────

#: Every visible, non-aria-hidden, enabled HTML text's contrast against the composited stack of
#: its ancestors' backgrounds (its own opacity applied) — 4.5:1, or 3:1 for >= 24 px or
#: >= 18.66 px bold. The slide's own text is judged by _SVG_SWEEP.
_TEXT_SWEEP = r"""() => {
 const parse = c => { const m = c.match(/[\d.]+/g); if (!m) return [0,0,0,0];
   return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1]; };
 const over = (top, bot) => { const a = top[3];
   return [top[0]*a + bot[0]*(1-a), top[1]*a + bot[1]*(1-a), top[2]*a + bot[2]*(1-a), 1]; };
 const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v/12.92
   : Math.pow((v+0.055)/1.055, 2.4); }; return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2]); };
 const ground = el => { const stack = [];
   for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
     const b = parse(getComputedStyle(n).backgroundColor);
     if (b[3] > 0) { stack.push(b); if (b[3] >= 1) break; } }
   let g = [255,255,255,1];
   if (!stack.length || stack[stack.length-1][3] < 1)
     g = parse(getComputedStyle(document.documentElement).backgroundColor);
   if (g[3] < 1) g = [255,255,255,1];
   for (let i = stack.length - 1; i >= 0; i--) g = over(stack[i], g); return g; };
 const out = [], seen = new Set();
 const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
 while (walker.nextNode()) {
   const t = walker.currentNode; if (!t.textContent.trim()) continue;
   const el = t.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
   if (el.closest('svg') || el.closest('[aria-hidden=true]')) continue;
   if (!el.getClientRects().length) continue;
   const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
   if (el.closest('[disabled]') || el.closest('.is-disabled')) continue;
   let op = 1; for (let n = el; n && n.nodeType === 1; n = n.parentElement)
     op *= +getComputedStyle(n).opacity;
   const fg0 = parse(cs.color), g = ground(el), fg = over([fg0[0], fg0[1], fg0[2], fg0[3]*op], g);
   const L1 = lum(fg), L2 = lum(g), ratio = (Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
   const px = parseFloat(cs.fontSize), w = +cs.fontWeight;
   const need = (px >= 24 || (px >= 18.66 && w >= 700)) ? 3 : 4.5;
   if (ratio < need) out.push((el.id ? '#' + el.id : el.tagName.toLowerCase()
     + (typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\s+/).join('.') : ''))
     + ' ' + ratio.toFixed(2) + '<' + need + ' '
     + JSON.stringify(t.textContent.trim().slice(0, 30)));
 }
 return out; }"""

#: Every slide text against its halo (or, with none, the slide's ground) — 4.5:1.
_SVG_SWEEP = r"""() => {
 const parse = c => { const m = (c||'').match(/[\d.]+/g); if (!m) return null;
   return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1]; };
 const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v/12.92
   : Math.pow((v+0.055)/1.055, 2.4); }; return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2]); };
 const svg = document.querySelector('#lsSlide svg'); if (!svg) return ['no slide'];
 const bg = parse(getComputedStyle(svg.querySelector('rect')).fill), out = [];
 let n = 0;
 svg.querySelectorAll('text').forEach(t => {
   if (!t.textContent.trim() || !t.getClientRects().length) return;
   if (t.closest('.lss-rings,.lss-drag,[aria-hidden=true]')) return;
   const cs = getComputedStyle(t), fg = parse(cs.fill); if (!fg) return; n++;
   const sw = parseFloat(cs.strokeWidth) || 0;
   const g = (sw > 0 && cs.stroke !== 'none' ? parse(cs.stroke) : null) || bg;
   const L1 = lum(fg), L2 = lum(g), r = (Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
   if (r < 4.5) out.push((t.getAttribute('class') || 'text') + ' ' + r.toFixed(2)
     + ' ' + JSON.stringify(t.textContent.trim().slice(0, 30)));
 });
 return n ? out : ['no slide text']; }"""


def _sweep(page: Any, where: str, *, slide: bool = False) -> list[str]:
    found = [f"{where}: {x}" for x in page.evaluate(_TEXT_SWEEP)]
    if slide:
        found += [f"{where} slide: {x}" for x in page.evaluate(_SVG_SWEEP)]
    return found


def _contrast_failures(browser: Any, view: str) -> list[str]:
    """Every failing text in ``view``: the launch page, the empty studio, a loaded Timeline (and
    its slide, the palette, the tour, the DATA drawer, the open handling drawer, a toast) and a
    loaded Compare (and its slide)."""
    found: list[str] = []
    with _studio(browser, view=view) as s:
        page = s.page
        page.goto(s.base + "/launch?replay=1")
        page.wait_for_selector("#lsHeroK:not(:empty)")
        found += _sweep(page, f"{view} launch")
        page.goto(s.base + "/onepager")
        found += _sweep(page, f"{view} empty")
        page.click("main [data-ls-example]")
        page.wait_for_function("() => LSStudio.state().layout !== null")
        found += _sweep(page, f"{view} timeline", slide=True)
        page.keyboard.press("Control+k")
        found += _sweep(page, f"{view} palette")
        page.keyboard.press("Escape")
        page.click("[data-ls-tour]")
        found += _sweep(page, f"{view} tour")
        page.keyboard.press("Escape")
        page.click("[data-ls-data]")
        found += _sweep(page, f"{view} data drawer")
        page.click("[data-ls-data]")
        page.click("#complianceDrawer summary")
        found += _sweep(page, f"{view} handling drawer")
        page.click("#complianceDrawer summary")
        page.fill("#lsTitle", f"Contrast {view}")
        page.press("#lsTitle", "Enter")
        page.wait_for_selector("#lsToasts .aismat-toast")
        found += _sweep(page, f"{view} toast")
        page.goto(s.base + "/onepager-compare")
        page.click("main [data-ls-example]")
        page.wait_for_function("() => LSStudio.state().layout !== null")
        found += _sweep(page, f"{view} compare", slide=True)
    return found


@pytest.mark.parametrize("view", VIEWS)
def test_every_text_reaches_wcag_aa_in_every_view(browser: Any, view: str) -> None:
    failures = _contrast_failures(browser, view)
    assert failures == [], "\n".join(failures)


@pytest.mark.parametrize(
    ("view", "path", "css", "named"),
    [
        # the Bright muted ink before the fix, on the launch page's --bg-void
        (
            "bright",
            "/launch?replay=1",
            ":root[data-theme=bright]{--text-muted:#5E6E83}",
            ".ls-launch-foot",
        ),
        # the faint token back on real text (the session log's count)
        ("dark", "/onepager", ".ls-count{color:var(--text-faint)}", ".ls-count"),
    ],
)
def test_mutation_the_pre_fix_inks_are_named(
    browser: Any, view: str, path: str, css: str, named: str
) -> None:
    with _studio(browser, view=view) as s:
        page = s.page
        page.goto(s.base + path)
        if path == "/onepager":
            page.click("main [data-ls-example]")
            page.wait_for_function("() => LSStudio.state().layout !== null")
        else:
            page.wait_for_selector("#lsHeroK:not(:empty)")
        page.add_style_tag(content=css)
        page.wait_for_timeout(250)  # past any colour transition
        failures = _sweep(page, view)
    assert any(named in f for f in failures), failures


# ── the CHANGE SUMMARY strip, the tags and the deltas fit their boxes (ADR-0544) ──────────────

#: A pair shaped like the operator's August → September lists (typed here): a lane with eight
#: slips and long names, a lane with a pull-in, a removal, an addition and a repeated name whose
#: copies match no date (a DUPLICATE NAME tag), and a lane that stands still.
_FIT_HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")
_FIT_PRIOR: tuple[tuple[object, ...], ...] = (
    _FIT_HEAD,
    ("GRC-MET Testing", "Facility Prep - Process Water", "11/20/26", "11/20/26", ""),
    ("GRC-MET Testing", "Facility Prep - ISP Steam Ejector Systems", "11/6/26", "11/6/26", ""),
    (
        "GRC-MET Testing",
        "Facility Prep - LOX Integrated System Checkout Test",
        "12/28/26",
        "12/28/26",
        "",
    ),
    ("GRC-MET Testing", "Facility Prep - LH2 Checkout Testing", "10/26/26", "10/26/26", ""),
    ("GRC-MET Testing", "MET ATP for Hot-Fire", "2/1/27", "2/1/27", ""),
    ("GRC-MET Testing", "Exhaust Certification Test (ECT) ORR", "10/28/26", "10/28/26", ""),
    ("GRC-MET Testing", "ECT Test", "12/9/26", "1/4/27", ""),
    ("GRC-MET Testing", "MET Hot-Fire ORR/TRR", "2/1/27", "2/1/27", ""),
    ("GRC-MET Testing", "Cold Fire / WDR", "2/8/27", "2/8/27", ""),
    ("GRC-MET Testing", "Hotfire Test (Test Points #2-22)", "4/27/27", "4/27/27", ""),
    ("Blue Origin", "BOR Demo Mission IDR #2", "9/15/26", "9/15/26", ""),
    ("Blue Origin", "MET On-Dock", "11/13/26", "11/13/26", ""),
    ("Blue Origin", "MET Testing", "1/5/27", "4/16/27", ""),
    ("Blue Origin", "EOR FRR", "9/1/27", "9/1/27", ""),
    ("Blue Origin", "BOTM - Uncrewed Demo Lander Launch", "3/18/28", "3/18/28", ""),
    ("Blue Origin", "Monthly Review", "5/5/27", "5/5/27", ""),
    ("Blue Origin", "Monthly Review", "6/5/27", "6/5/27", ""),
    ("Flight Manifests", "Artemis III", "6/15/27", "6/15/27", ""),
    ("Flight Manifests", "Artemis IV", "3/31/28", "3/31/28", ""),
)
_FIT_CURRENT: tuple[tuple[object, ...], ...] = (
    _FIT_HEAD,
    ("GRC-MET Testing", "Facility Prep - Process Water", "12/11/26", "12/11/26", ""),
    (
        "GRC-MET Testing",
        "Facility Prep - ISP Steam Ejector Systems",
        "12/2/26",
        "12/2/26",
        "Complete",
    ),
    (
        "GRC-MET Testing",
        "Facility Prep - LOX Integrated System Checkout Test",
        "3/5/27",
        "3/5/27",
        "",
    ),
    ("GRC-MET Testing", "Facility Prep - LH2 Checkout Testing", "12/1/26", "12/1/26", ""),
    ("GRC-MET Testing", "MET ATP for Hot-Fire", "3/14/27", "3/14/27", ""),
    ("GRC-MET Testing", "Exhaust Certification Test (ECT) ORR", "12/13/26", "12/13/26", ""),
    ("GRC-MET Testing", "ECT Test", "1/29/27", "2/24/27", ""),
    ("GRC-MET Testing", "MET Hot-Fire ORR/TRR", "3/29/27", "3/29/27", ""),
    ("GRC-MET Testing", "Cold Fire / WDR", "4/20/27", "4/20/27", ""),
    ("GRC-MET Testing", "Hotfire Test (Test Points #2-22)", "4/27/27", "4/27/27", ""),
    ("Blue Origin", "BOR Demo Mission IDR #2", "10/6/26", "10/6/26", ""),
    ("Blue Origin", "MET On-Dock", "12/9/26", "12/9/26", "Complete"),
    ("Blue Origin", "MET Testing", "1/5/27", "4/7/27", ""),
    ("Blue Origin", "EOR FRR", "10/12/27", "10/12/27", ""),
    ("Blue Origin", "Monthly Review", "5/8/27", "5/8/27", ""),
    ("Blue Origin", "Monthly Review", "6/8/27", "6/8/27", ""),
    ("Blue Origin", "BOTM - Uncrewed Demo Lander Launch (Mk2-A-U)", "3/22/28", "3/22/28", ""),
    ("Flight Manifests", "Artemis III", "6/15/27", "6/15/27", ""),
    ("Flight Manifests", "Artemis IV", "3/31/28", "3/31/28", ""),
)
#: Each summary line's and tag's NATURAL width (its ``textLength`` fit lifted for the measure)
#: against the box the layout gave it — a strip line keeps 2.5 pt clear of the left edge, a tag 1.6.
_NATURAL_FIT = """() => {
  const nat = (t) => {
    const had = t.getAttribute('textLength'); t.removeAttribute('textLength');
    const w = t.getComputedTextLength(); if (had !== null) t.setAttribute('textLength', had);
    return w;
  };
  const over = [];
  document.querySelectorAll('g.lss-summary').forEach((g) => {
    const box = parseFloat(g.querySelector('.lss-sum-bg').getAttribute('width')) - 2.5;
    g.querySelectorAll('.lss-sum-text').forEach((t) => {
      const w = nat(t);
      if (w > box + 0.5) over.push(['summary', t.textContent, +w.toFixed(1), +box.toFixed(1)]);
    });
  });
  document.querySelectorAll('.lss-badge').forEach((t) => {
    const w = nat(t), box = parseFloat(t.previousSibling.getAttribute('width')) - 1.6;
    if (w > box + 0.5) over.push(['tag', t.textContent, +w.toFixed(1), +box.toFixed(1)]);
  });
  const first = document.querySelector('.lss-sum-text');
  const cs = first ? getComputedStyle(first) : null;
  return { over: over, lines: document.querySelectorAll('.lss-sum-text').length,
    tags: document.querySelectorAll('.lss-badge').length,
    rendering: cs ? cs.textRendering : '', face: cs ? cs.fontFamily : '' };
}"""


def _fit_pair(s: Studio) -> Any:
    """The operator-shaped pair on the Compare page, the fonts in, the strip measured."""
    for slot, rows, name in (
        ("prior", _FIT_PRIOR, "August.xlsx"),
        ("current", _FIT_CURRENT, "Sept.xlsx"),
    ):
        got = upload(s.server.server_port, "/onepager-compare/upload", rows, name, slot=slot)
        assert got.status == 303, (slot, got.status)
    page = s.page
    page.goto(s.base + "/onepager-compare")
    page.wait_for_function("() => window.LSStudio && LSStudio.state().layout !== null")
    page.wait_for_selector("svg[data-ls-slide] .lss-sum-text")
    page.evaluate("() => document.fonts.ready")
    return page.evaluate(_NATURAL_FIT)


@pytest.mark.parametrize("view", ["dark", "bright"])
def test_the_summary_strip_tags_and_deltas_fit_their_boxes_in_the_face_that_paints_them(
    browser: Any, view: str
) -> None:
    """Operator report 2026-10-01 (a screenshot): the CHANGE SUMMARY text ran outside its coloured
    boxes. The strip and the tags are set in IBM Plex Mono — 0.6 em per glyph — and the layout now
    wraps and sizes them for that face (ADR-0544); the slide renders with geometric precision so
    the browser's pixel-rounded advances at small sizes cannot widen them past the box."""
    with _studio(browser, view=view) as s:
        got = _fit_pair(s)
        assert got["lines"] >= 6 and got["tags"] >= 3, got
        assert "IBM Plex Mono" in got["face"] and got["rendering"] == "geometricprecision", got
        assert got["over"] == [], got["over"]


def test_mutation_the_calibri_width_model_on_the_strip_overflows_the_boxes(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the 0.52 model put back on the strip (in-process — the server runs here) and
    the SAME measurement reports summary lines AND tags past their boxes, by name."""
    from schedule_forensics.reports import onepager_compare as oc

    monkeypatch.setattr(oc, "MONO_CHAR_W", 0.52)
    with _studio(browser) as s:
        got = _fit_pair(s)
        kinds = {o[0] for o in got["over"]}
        assert kinds == {"summary", "tag"}, got["over"]


def test_mutation_without_geometric_precision_the_tags_overflow(browser: Any) -> None:
    """MUTATION: the one CSS declaration lifted from the served sheet — Chromium rounds each
    glyph advance to a device pixel at the tag's size and the pills no longer hold their word."""
    patch = {"lodestar_studio.css": ("text-rendering:geometricPrecision", "text-rendering:auto")}
    with _studio(browser, patch=patch) as s:
        got = _fit_pair(s)
        assert got["rendering"] == "auto" and any(o[0] == "tag" for o in got["over"]), got
