"""The operator's LOGIC LINKS through both One-Pager pages, end to end (ADR-0539).

A One-Pager list carries no logic, so the operator picks two items and the slide draws exactly
that arrow — "and only that logic" — then exports it to PowerPoint. This module drives the routes
the way the browser does (``TestClient``; the painted page is ``test_onepager_links_browser.py``)
and pins, for ``/onepager`` and ``/onepager-compare`` alike:

* **Add / remove / clear** — each POST returns 303 to the links block (``#opLinks`` /
  ``#opcLinks``) and its one-shot result is shown INSIDE that block, never in the banner above
  the slide (which the browser has scrolled away from); the layout JSON carries the link; the
  list below the slide names it with a Remove whose ``aria-label`` is unique.
* **Refusals** (a loop, the same item twice, a duplicate, an item not on the slide) are
  ``role=alert`` inside the block, and nothing changes.
* **The controls** opt out of ``persist.js`` (``data-sf-nopersist`` — else the pair just added is
  restored and re-submitted) and of translation (``data-no-i18n`` on the item selects); a long
  item is cut at 56 characters with an ellipsis, keeps ``— row N`` and carries its full text in
  ``title``.
* **Links outlive a list, never silently.** Re-uploading the same list keeps them; a list
  without one of the items lists the link under "Logic links not drawn" with the reason; a date
  window that hides an item says so; clearing the list clears its links and says how many.
* **Exports** — the .pptx carries one ``Logic link:`` group per drawn link and the .xlsx a
  "Logic links" sheet; a slide title of ``Ωmega 日程`` exports with an RFC 5987 ``filename*``.
* **The upload's layout choice** (auto / start-finish / date-status) is offered on every upload
  form and a forced layout is honoured through the route.
* **Compare** links join CURRENT positions; a REMOVED row is never offered and cannot be linked.

Red-first (2026-09-29): run against the pristine tree (HEAD 0b45eb2) every test here fails —
the ``/links`` routes 404, there is no links block, no layout select and no link export, and
the ``Ωmega 日程`` title 500s the PowerPoint export (``UnicodeEncodeError`` in the header). The
new modules (``web.onepager_actions``, ``reports.onepager_links``) are imported inside the tests
that need them so the pristine run fails test by test, not at collection. Every load-bearing
check has a ``test_mutation_*`` twin that breaks the thing in memory and asserts the SAME
checker goes red.
"""

from __future__ import annotations

import datetime as dt
import html
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import SessionState, create_app
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2026, 9, 1)

HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")
#: The CURRENT-layout list both pages load (the compare page as its CURRENT list).
ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "4/15/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Ship", "7/15/2027", "7/15/2027", ""),
)
#: The compare page's PRIOR list: Design Review five days earlier (so its ghost and its current
#: diamond sit apart), no Ship (NEW in the current list), and "Old Thing" (REMOVED from it).
PRIOR_ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/10/2027", "1/10/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "4/15/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Old Thing", "3/1/2027", "3/1/2027", ""),
)
#: The same list in the OLDER layout (C a date or range · D a status word).
OLDER_ROWS: tuple[tuple[object, ...], ...] = (
    ("Swimlane Name", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027 - 4/15/2027", ""),
)
DR = "Alpha · Design Review (1/15/27)"
BUILD = "Alpha · Build (2/1/27 to 4/15/27)"
TEST = "Beta · Test (5/1/27 to 6/30/27)"
SHIP = "Beta · Ship (7/15/27)"


@dataclass(frozen=True)
class Page:
    """One One-Pager page: where it lives, its element-id prefix and its clear sentence."""

    key: str
    path: str
    prefix: str
    cleared: str

    @property
    def links_url(self) -> str:
        return f"{self.path}/links"

    @property
    def pptx(self) -> str:
        return f"/export/pptx{self.path}"

    @property
    def xlsx(self) -> str:
        return f"/export/xlsx{self.path}"


ONEPAGER = Page("onepager", "/onepager", "op", "List cleared. Its {n} logic link(s) went with it.")
COMPARE = Page(
    "compare",
    "/onepager-compare",
    "opc",
    "Both lists cleared. Their {n} logic link(s) went with them.",
)
PAGES = pytest.mark.parametrize("pg", [ONEPAGER, COMPARE], ids=["onepager", "compare"])


@pytest.fixture
def state() -> SessionState:
    st = SessionState()
    st.onepager_today = TODAY
    return st


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


# ── helpers: drive the routes, read the page back ─────────────────────────────────────────────


def _post_file(client: TestClient, url: str, rows: Any, name: str, **form: str) -> None:
    r = client.post(
        url,
        files={"file": (name, twin_xlsx(rows), "application/octet-stream")},
        data=form,
        follow_redirects=False,
    )
    assert r.status_code == 303, (url, r.status_code)


def _load(client: TestClient, pg: Page, rows: Any = ROWS, *, layout: str | None = None) -> str:
    """Load ``rows`` as the page's list (the compare page: PRIOR_ROWS then ``rows`` as CURRENT)
    and return the page."""
    extra = {"layout": layout} if layout is not None else {}
    if pg is ONEPAGER:
        _post_file(client, "/onepager/upload", rows, "Logic list.xlsx", **extra)
    else:
        _post_file(
            client, "/onepager-compare/upload", PRIOR_ROWS, "March.xlsx", slot="prior", **extra
        )
        _post_file(client, "/onepager-compare/upload", rows, "April.xlsx", slot="current", **extra)
    return client.get(pg.path).text


def _link(
    client: TestClient, pg: Page, action: str, pred: str = "", succ: str = "", kind: str = "FS"
) -> str:
    """POST one link action; assert the 303 lands on the links block; return the page."""
    r = client.post(
        pg.links_url,
        data={"action": action, "pred": pred, "succ": succ, "kind": kind},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.status_code
    assert r.headers["location"] == f"{pg.path}#{pg.prefix}Links"
    return client.get(pg.path).text


_OPTION = re.compile(r'<option value="([^"]*)" title="([^"]*)">([^<]*)</option>')


def _options(page: str, pg: Page, which: str = "From") -> list[tuple[str, str, str]]:
    """``(value, title, text)`` of every item option in the From (or To) select."""
    m = re.search(rf"<select\b[^>]*\bid={pg.prefix}Link{which}\b[^>]*>(.*?)</select>", page, re.S)
    assert m, f"no {pg.prefix}Link{which} select on the page"
    return [
        (html.unescape(v), html.unescape(t), html.unescape(x))
        for v, t, x in _OPTION.findall(m.group(1))
    ]


def _keys(page: str, pg: Page) -> dict[str, str]:
    """Every linkable item's full label -> its key, read off the page's own select."""
    return {title: value for value, title, _text in _options(page, pg)}


def _block(page: str, element_id: str) -> str | None:
    m = re.search(rf"<section\b[^>]*\bid={element_id}\b[^>]*>(.*?)</section>", page, re.S)
    return m.group(1) if m else None


def _placement(page: str, pg: Page, text: str) -> str:
    """Where ``text`` shows: ``"block"`` (only inside the links block), ``"outside"`` (anywhere
    else on the page — the banner above the slide, say) or ``"absent"``."""
    block = _block(page, f"{pg.prefix}Links")
    rest = page.replace(block, "", 1) if block else page
    if text in html.unescape(rest):
        return "outside"
    return "block" if block is not None and text in html.unescape(block) else "absent"


def _notice_role(fragment: str, text: str) -> str | None:
    """The ``role`` of the notice in ``fragment`` whose text holds ``text``."""
    for role, body in re.findall(r'<div class="notice \w+" role=(\w+)>(.*?)</div>', fragment, re.S):
        if text in html.unescape(re.sub(r"<[^>]+>", "", body)):
            return str(role)
    return None


def _layout(page: str, pg: Page) -> dict[str, Any]:
    m = re.search(rf'<script id={pg.prefix}Data type="application/json">(.*?)</script>', page, re.S)
    assert m, "the layout JSON block is missing"
    return dict(json.loads(m.group(1)))


def _drawn(page: str, pg: Page) -> list[tuple[str, str, str]]:
    return [(ln["pred_name"], ln["succ_name"], ln["kind"]) for ln in _layout(page, pg)["links"]]


def _remove_labels(page: str, pg: Page) -> list[str]:
    listing = _block(page, f"{pg.prefix}LinkList") or ""
    return [
        html.unescape(x) for x in re.findall(r'aria-label="(Remove logic link [^"]*)"', listing)
    ]


class _Tags(HTMLParser):
    """Every start tag's attributes, and the tags carrying an id by that id."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.all: list[tuple[str, dict[str, str | None]]] = []
        self.by_id: dict[str, tuple[str, dict[str, str | None]]] = {}
        self.feed(page)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        self.all.append((tag, d))
        if d.get("id"):
            self.by_id[str(d["id"])] = (tag, d)


_PML = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _link_groups(pptx: bytes, prefix: str = "Logic link: ") -> list[tuple[str, list[str]]]:
    """``(group name, its children's names)`` for every group on the slide named ``prefix …`` —
    a link's SHAFT group (``Logic link: …``) or, since ADR-0543 paints the head over the items
    and the shaft under them, its HEAD group (``Logic link arrowhead: …``)."""
    with zipfile.ZipFile(io.BytesIO(pptx)) as zf:
        root = ET.fromstring(zf.read("ppt/slides/slide1.xml"))
    out = []
    for grp in root.iter(f"{_PML}grpSp"):
        own = grp.find(f"{_PML}nvGrpSpPr/{_PML}cNvPr")
        name = own.get("name", "") if own is not None else ""
        if name.startswith(prefix):
            kids = [str(c.get("name")) for c in grp.iter(f"{_PML}cNvPr") if c is not own]
            out.append((name, kids))
    return out


# ── add: the result lands where the browser does ──────────────────────────────────────────────


@PAGES
def test_an_added_link_is_announced_inside_the_links_block_drawn_and_listed(
    client: TestClient, pg: Page
) -> None:
    """POST add -> 303 to ``#<prefix>Links``; the success sentence shows ONCE, inside that block,
    as a status; the layout JSON carries the link; the list below the slide names it with its
    own Remove form (the link's keys and type) and a Remove label naming it; the message is
    one-shot."""
    keys = _keys(_load(client, pg), pg)
    page = _link(client, pg, "add", keys[DR], keys[BUILD], "FS")
    said = f"Logic link added: {DR} → {BUILD} (FS)."
    assert _placement(page, pg, said) == "block"
    assert _notice_role(_block(page, f"{pg.prefix}Links") or "", said) == "status"
    assert _drawn(page, pg) == [(DR, BUILD, "FS")]
    ln = _layout(page, pg)["links"][0]
    assert (ln["pred"], ln["succ"]) == (keys[DR], keys[BUILD]) and ln["tag"] == ""
    listing = _block(page, f"{pg.prefix}LinkList")
    assert listing is not None and f"<span data-no-i18n>{DR} → {BUILD}</span>" in listing
    assert _remove_labels(page, pg) == [f"Remove logic link {DR} → {BUILD} (FS)"]
    assert (
        f'<input type=hidden name=pred value="{keys[DR]}">'
        f'<input type=hidden name=succ value="{keys[BUILD]}">'
        '<input type=hidden name=kind value="FS">'
    ) in listing
    assert _placement(client.get(pg.path).text, pg, said) == "absent"  # one-shot


def test_mutation_a_link_message_in_the_banner_is_caught_by_the_placement_check(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: route the link action's sentence to the page BANNER (the pre-ADR-0539 place,
    above the slide) — the placement check the real test uses must say ``outside``."""
    from schedule_forensics.web import onepager_actions as op_actions

    real = op_actions.edit_links

    def to_banner(st: Any, page: str, *args: Any) -> None:
        real(st, page, *args)
        st.onepager_msg, st.onepager_links_msg = st.onepager_links_msg, None

    monkeypatch.setattr(op_actions, "edit_links", to_banner)
    keys = _keys(_load(client, ONEPAGER), ONEPAGER)
    page = _link(client, ONEPAGER, "add", keys[DR], keys[BUILD])
    assert _placement(page, ONEPAGER, f"Logic link added: {DR} → {BUILD} (FS).") == "outside"


@PAGES
def test_every_remove_button_names_its_own_link(client: TestClient, pg: Page) -> None:
    """Three links sharing an end — two of them the same pair, SS and FF — get three distinct
    Remove labels, each naming both ends and the type (a screen reader lists them by label)."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD], "SS")
    _link(client, pg, "add", keys[DR], keys[BUILD], "FF")
    page = _link(client, pg, "add", keys[DR], keys[TEST], "FS")
    labels = _remove_labels(page, pg)
    assert labels == [
        f"Remove logic link {DR} → {BUILD} (SS)",
        f"Remove logic link {DR} → {BUILD} (FF)",
        f"Remove logic link {DR} → {TEST} (FS)",
    ]
    assert len(set(labels)) == 3


@PAGES
def test_remove_and_clear_do_what_they_say_and_say_it(client: TestClient, pg: Page) -> None:
    """Remove takes exactly the link named and says so in the block; removing it again is an
    alert that nothing was removed; "Remove all links" empties the slide and counts them."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    _link(client, pg, "add", keys[BUILD], keys[TEST])
    page = _link(client, pg, "remove", keys[DR], keys[BUILD], "FS")
    said = f"Removed the logic link {DR} → {BUILD} (FS)."
    assert _placement(page, pg, said) == "block"
    assert _notice_role(_block(page, f"{pg.prefix}Links") or "", said) == "status"
    assert _drawn(page, pg) == [(BUILD, TEST, "FS")]
    page = _link(client, pg, "remove", keys[DR], keys[BUILD], "FS")
    gone = "That logic link is not on this page any more — nothing removed."
    assert _placement(page, pg, gone) == "block"
    assert _notice_role(_block(page, f"{pg.prefix}Links") or "", gone) == "alert"
    assert _drawn(page, pg) == [(BUILD, TEST, "FS")]
    page = _link(client, pg, "clear")
    assert _placement(page, pg, "All 1 logic link(s) removed.") == "block"
    assert _layout(page, pg)["links"] == [] and _block(page, f"{pg.prefix}LinkList") is None


# ── refusals: an alert, inside the block, and nothing changes ─────────────────────────────────


REFUSALS = pytest.mark.parametrize(
    "case",
    ["loop", "itself", "duplicate", "not-on-slide"],
)


def _refuse(client: TestClient, pg: Page, case: str) -> tuple[str, str]:
    """Build two links DR -> BUILD -> TEST, then POST the refused one; ``(page, sentence)``."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    _link(client, pg, "add", keys[BUILD], keys[TEST])
    if case == "loop":
        page = _link(client, pg, "add", keys[TEST], keys[DR])
        said = (
            f"Not added — {TEST} → {DR} would close a logic loop ({TEST} → {DR} → {BUILD} → "
            f"{TEST}). A loop has no start and no finish; remove one of its links first."
        )
    elif case == "itself":
        page = _link(client, pg, "add", keys[SHIP], keys[SHIP])
        said = f"“{SHIP}” cannot be linked to itself — pick two items."
    elif case == "duplicate":
        page = _link(client, pg, "add", keys[DR], keys[BUILD])
        said = f"{DR} → {BUILD} (FS) is already drawn."
    else:
        page = _link(client, pg, "add", "0123456789abcdef", keys[SHIP])
        said = "That item is no longer on the slide — pick it again from the list."
    return page, said


@PAGES
@REFUSALS
def test_a_refused_link_is_an_alert_inside_the_links_block(
    client: TestClient, pg: Page, case: str
) -> None:
    """A loop, the same item twice, an exact duplicate and an item no longer on the slide are each
    refused by name — an alert INSIDE the links block, never the banner — and the two links
    already made stay exactly as they were."""
    page, said = _refuse(client, pg, case)
    assert _placement(page, pg, said) == "block", case
    assert _notice_role(_block(page, f"{pg.prefix}Links") or "", said) == "alert", case
    assert _drawn(page, pg) == [(DR, BUILD, "FS"), (BUILD, TEST, "FS")], case


def test_mutation_without_loop_detection_the_loop_check_goes_red(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: blind the loop search — the closing link is then ADDED, and the same placement
    and link checks the real test uses see no alert and three links."""
    from schedule_forensics.reports import onepager_links

    monkeypatch.setattr(onepager_links, "_reaches", lambda *_a: None)
    page, said = _refuse(client, ONEPAGER, "loop")
    assert _placement(page, ONEPAGER, said) == "absent"
    assert len(_drawn(page, ONEPAGER)) == 3


# ── the controls ──────────────────────────────────────────────────────────────────────────────


@PAGES
def test_the_link_controls_opt_out_of_persist_and_the_item_selects_of_translation(
    client: TestClient, pg: Page
) -> None:
    """``persist.js`` restores any control without ``data-sf-nopersist`` — it would put the
    pair just added back and re-submit it (the browser test proves that); the translator must
    not rewrite a select's item names (``data-no-i18n``)."""
    keys = _keys(_load(client, pg), pg)
    page = _link(client, pg, "add", keys[DR], keys[BUILD])
    tags = _Tags(page)
    p = pg.prefix
    for el in (f"{p}Links", f"{p}LinkForm", f"{p}LinkFrom", f"{p}LinkTo", f"{p}LinkKind"):
        assert el in tags.by_id, el
        assert "data-sf-nopersist" in tags.by_id[el][1], el
    for el in (f"{p}LinkFrom", f"{p}LinkTo"):
        tag, attrs = tags.by_id[el]
        assert tag == "select" and "data-no-i18n" in attrs and "required" in attrs, el
    assert tags.by_id[f"{p}LinkForm"][1]["action"] == pg.links_url
    forms = [
        a
        for t, a in tags.all
        if t == "form" and a.get("class") in ("op-link-remove", "op-link-clear")
    ]
    assert len(forms) == 2 and all("data-sf-nopersist" in a for a in forms)
    assert all(a["action"] == pg.links_url for a in forms)


def _cut_right(text: str, title: str, row: int) -> bool:
    """An option's text is the title cut to 55 characters plus an ellipsis, then its row."""
    return len(title) > 56 and text == f"{title[:55]}… — row {row}"


@PAGES
def test_a_long_option_is_cut_with_an_ellipsis_keeps_its_row_and_titles_the_full_text(
    client: TestClient, pg: Page
) -> None:
    """An item label past 56 characters is cut to 55 plus an ellipsis, keeps ``— row N`` (two
    same-named items stay apart) and carries the whole label in ``title``; a short one is whole;
    the To select offers exactly what the From select does."""
    long = "Integrated vehicle stack qualification test campaign, acoustic and thermal"
    rows = (*ROWS[:2], ("Alpha", long, "2/1/2027", "4/15/2027", ""), *ROWS[3:])
    page = _load(client, pg, rows)
    by_title = {title: (text, value) for value, title, text in _options(page, pg)}
    full = f"Alpha · {long} (2/1/27 to 4/15/27)"
    assert full in by_title and len(full) > 56
    assert _cut_right(by_title[full][0], full, 3), by_title[full][0]
    assert by_title[DR][0] == f"{DR} — row 2"  # short: whole, no ellipsis
    assert _options(page, pg, "To") == _options(page, pg, "From")


def test_mutation_an_uncut_option_is_caught(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: lift the 56-character cut — the check the real test uses goes red."""
    from schedule_forensics.web import onepager as onepager_page

    monkeypatch.setattr(onepager_page, "_OPTION_NAME", 10_000)
    long = "Integrated vehicle stack qualification test campaign, acoustic and thermal"
    rows = (*ROWS[:2], ("Alpha", long, "2/1/2027", "4/15/2027", ""), *ROWS[3:])
    page = _load(client, ONEPAGER, rows)
    full = f"Alpha · {long} (2/1/27 to 4/15/27)"
    text = next(t for _v, title, t in _options(page, ONEPAGER) if title == full)
    assert not _cut_right(text, full, 3) and text == f"{full} — row 3"


def test_option_label_cuts_past_56_characters_exactly() -> None:
    """The cut's boundary: 56 characters stay whole, 57 are cut; no row, no suffix."""
    from schedule_forensics.web.onepager import option_label

    assert option_label("x" * 56, 7) == "x" * 56 + " — row 7"
    assert option_label("x" * 57, 7) == "x" * 55 + "… — row 7"
    assert len(option_label("y" * 300, None)) == 56 and option_label("abc", None) == "abc"


# ── links outlive a list — and are never silently dropped ─────────────────────────────────────


@PAGES
def test_links_survive_the_same_list_and_a_missing_item_is_named_not_dropped(
    client: TestClient, pg: Page
) -> None:
    """Links are keyed by item, not row: the same list re-uploaded draws them all again; a list
    without Build draws the other link, still LISTS the Build one (removable, marked not drawn)
    and names it in the "Logic links not drawn" alert with the reason; Build back, link back."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    _link(client, pg, "add", keys[TEST], keys[SHIP], "SS")
    both = [(DR, BUILD, "FS"), (TEST, SHIP, "SS")]
    page = _load(client, pg)  # the same list again: every link is drawn again
    assert _drawn(page, pg) == both and "Logic links not drawn" not in page
    without = tuple(r for r in ROWS if r[1] != "Build")
    page = _load(client, pg, without)
    assert _drawn(page, pg) == [(TEST, SHIP, "SS")]
    listing = _block(page, f"{pg.prefix}LinkList") or ""
    assert len(_remove_labels(page, pg)) == 2  # the undrawn link is still LISTED, removable
    assert listing.count("— not drawn (see below)") == 1
    head = "Logic links not drawn — 1 of 2"
    note = f"logic link “{DR}” → “{BUILD}” (FS) is not drawn — “{BUILD}” is no longer in the list."
    assert _notice_role(listing, head) == "alert" and _notice_role(listing, note) == "alert"
    assert _drawn(_load(client, pg), pg) == both  # the item is back: so is its link


@PAGES
def test_a_date_window_that_hides_an_item_names_its_link(client: TestClient, pg: Page) -> None:
    """A window that leaves Build off the slide names the link as not drawn because Build is
    outside the date window (not "no longer in the list"), offers only what it shows, and
    draws the link again once the window is cleared."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    r = client.post(
        f"{pg.path}/window",
        data={"start": "2027-01-01", "end": "2027-01-31", "action": "apply"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get(pg.path).text
    assert _drawn(page, pg) == []
    note = (
        f"logic link “{DR}” → “{BUILD}” (FS) is not drawn — “{BUILD}” is outside the date window."
    )
    assert _notice_role(_block(page, f"{pg.prefix}LinkList") or "", note) == "alert"
    assert [t for _v, t, _x in _options(page, pg)] == [DR]  # only what the window shows
    client.post(f"{pg.path}/window", data={"action": "clear"})
    assert _drawn(client.get(pg.path).text, pg) == [(DR, BUILD, "FS")]


@PAGES
def test_clearing_the_list_clears_its_links_and_says_how_many(
    client: TestClient, pg: Page, state: SessionState
) -> None:
    """Clearing the list (both lists, on Compare) takes its links with it and counts them; the
    session holds none, a fresh list starts with none, and a clear with no link says nothing
    about links."""
    keys = _keys(_load(client, pg), pg)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    _link(client, pg, "add", keys[BUILD], keys[TEST])
    assert client.post(f"{pg.path}/clear", follow_redirects=False).status_code == 303
    assert pg.cleared.format(n=2) in client.get(pg.path).text
    held = state.onepager_links if pg is ONEPAGER else state.onepager_compare_links
    assert held == ()
    page = _load(client, pg)
    assert _layout(page, pg)["links"] == [] and _block(page, f"{pg.prefix}LinkList") is None
    client.post(f"{pg.path}/clear")
    page = client.get(pg.path).text
    assert "logic link(s) went with" not in page  # none to count: no sentence about them


# ── exports ───────────────────────────────────────────────────────────────────────────────────


@PAGES
def test_the_exports_carry_every_link(client: TestClient, pg: Page) -> None:
    """The .pptx: one ``Logic link: A → B (T)`` shaft group and one ``Logic link arrowhead: A →
    B (T)`` head group per drawn link (an SS one's head group with its type tag); the .xlsx: a
    "Logic links" sheet — both ends, the type, whether the slide draws it, and the reason when it
    does not. With no link, neither."""
    keys = _keys(_load(client, pg), pg)
    deck = client.get(pg.pptx)
    assert deck.status_code == 200 and _link_groups(deck.content) == []
    assert "Logic links" not in read_xlsx(client.get(pg.xlsx).content)
    _link(client, pg, "add", keys[DR], keys[BUILD])
    _link(client, pg, "add", keys[TEST], keys[SHIP], "SS")
    deck = client.get(pg.pptx)
    groups = _link_groups(deck.content)
    assert [g for g, _kids in groups] == [
        f"Logic link: {DR} → {BUILD} (FS)",
        f"Logic link: {TEST} → {SHIP} (SS)",
    ]
    heads = _link_groups(deck.content, "Logic link arrowhead: ")
    assert [g for g, _kids in heads] == [
        f"Logic link arrowhead: {DR} → {BUILD} (FS)",
        f"Logic link arrowhead: {TEST} → {SHIP} (SS)",
    ]
    assert f"Logic link type: {TEST} → {SHIP} (SS)" in heads[1][1]
    assert not any(k.startswith("Logic link type:") for _g, kids in groups for k in kids)
    assert not any(k.startswith("Logic link type:") for k in heads[0][1])
    book = client.get(pg.xlsx)
    assert book.status_code == 200
    sheet = read_xlsx(book.content)["Logic links"]
    assert sheet == [
        ["From", "To", "Type", "On the slide"],
        [DR, BUILD, "Finish-to-Start (FS)", "yes"],
        [TEST, SHIP, "Start-to-Start (SS)", "yes"],
    ]
    client.post(f"{pg.path}/window", data={"start": "2027-05-01", "end": "2027-08-31"})
    sheet = read_xlsx(client.get(pg.xlsx).content)["Logic links"]
    assert sheet[1][3] == "no — see the note below" and sheet[2][3] == "yes"
    assert sheet[3][:3] == ["", "", "note"] and "is outside the date window" in sheet[3][3]
    assert len(_link_groups(client.get(pg.pptx).content)) == 1


@PAGES
def test_a_non_latin_slide_title_exports_with_an_rfc5987_filename(
    state: SessionState, pg: Page
) -> None:
    """A title of ``Ωmega 日程`` put a non-Latin-1 character in ``Content-Disposition`` and
    500'd the export (pristine: ``UnicodeEncodeError``). Now: 200, an ASCII ``filename`` and
    the real title as ``filename*=UTF-8''…``."""
    client = TestClient(create_app(state), raise_server_exceptions=False)
    _load(client, pg)
    assert client.post(f"{pg.path}/title", data={"title": "Ωmega 日程"}).status_code == 200
    r = client.get(pg.pptx)
    assert r.status_code == 200, r.status_code
    cd = r.headers["content-disposition"]
    assert cd.isascii()
    assert cd == (
        "attachment; filename=\"mega.pptx\"; filename*=UTF-8''%CE%A9mega%20%E6%97%A5%E7%A8%8B.pptx"
    )
    assert unquote(cd.split("filename*=UTF-8''", 1)[1]) == "Ωmega 日程.pptx"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert "Ωmega 日程" in zf.read("ppt/slides/slide1.xml").decode("utf-8")


def test_mutation_a_latin1_only_disposition_is_caught_as_a_500(
    state: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: the pristine header (the title kept whole wherever ``isalnum``) — the status
    check the real test makes goes red: the export 500s."""
    from schedule_forensics.web import onepager_actions as op_actions

    def pristine(title: str, fallback: str, ext: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in title) or fallback
        return f'attachment; filename="{safe}.{ext}"'

    monkeypatch.setattr(op_actions, "attachment", pristine)
    client = TestClient(create_app(state), raise_server_exceptions=False)
    _load(client, ONEPAGER)
    client.post("/onepager/title", data={"title": "Ωmega 日程"})
    assert client.get("/export/pptx/onepager").status_code == 500


# ── the upload's layout choice ────────────────────────────────────────────────────────────────


_LAYOUTS = ["auto", "start-finish", "date-status"]


def _layout_selects(page: str) -> dict[str, list[str]]:
    """Every ``name=layout`` select on the page -> its option values, by id."""
    return {
        sid: re.findall(r'<option value="([^"]*)"', body)
        for sid, body in re.findall(r"<select name=layout id=(\w+)>(.*?)</select>", page, re.S)
    }


@PAGES
def test_every_upload_form_offers_the_layout_choice(client: TestClient, pg: Page) -> None:
    """Every upload form — empty page and loaded page — carries a ``name=layout`` select offering
    auto / start-finish / date-status, INSIDE the form it is submitted with."""
    want = ["opLayout"] if pg is ONEPAGER else ["opcLayoutPrior", "opcLayoutCurrent"]
    for page in (client.get(pg.path).text, _load(client, pg)):
        got = _layout_selects(page)
        assert list(got) == want and all(v == _LAYOUTS for v in got.values()), got
        # each select sits INSIDE the upload form it is submitted with
        forms = re.findall(r'<form id=\w+ action="[^"]*/upload".*?</form>', page, re.S)
        assert len(forms) == len(want)
        assert all(
            f"<select name=layout id={sid}>" in f for sid, f in zip(want, forms, strict=True)
        )


def _item(page: str, pg: Page, name: str) -> dict[str, Any]:
    return dict(next(i for i in _layout(page, pg)["items"] if i["name"] == name))


def _finish(item: dict[str, Any]) -> str:
    """The drawn finish: a One-Pager item's own, a compared row's CURRENT one."""
    return str(item["finish"] if "finish" in item else item["current_finish"])


@PAGES
def test_a_forced_layout_is_honoured_through_the_route(client: TestClient, pg: Page) -> None:
    """Auto reads ROWS as C start · D finish (Build: an activity to 4/15); forcing the older
    layout reads C as the date and D as a status (Build: a milestone on 2/1) and says it was
    chosen."""
    auto = _load(client, pg, layout="auto")
    assert _item(auto, pg, "Build")["milestone"] is False and "chosen at upload" not in auto
    assert _finish(_item(auto, pg, "Build")) == "2027-04-15"
    forced = _load(client, pg, layout="date-status")
    build = _item(forced, pg, "Build")
    assert build["milestone"] is True and _finish(build) == "2027-02-01"
    if pg is ONEPAGER:
        assert "read as the older C date-or-range · D status — chosen at upload" in forced
    else:
        assert "· older layout" in forced


def test_forcing_the_current_layout_on_an_older_sheet_refuses_its_status_rows(
    client: TestClient,
) -> None:
    """The other direction: an older sheet reads by detection, and forcing C start · D finish
    on it refuses the row whose D holds a status word — by name."""
    older = _load(client, ONEPAGER, OLDER_ROWS, layout="auto")
    assert [i["name"] for i in _layout(older, ONEPAGER)["items"]] == ["Design Review", "Build"]
    assert _finish(_item(older, ONEPAGER, "Build")) == "2027-04-15"
    refused = _load(client, ONEPAGER, OLDER_ROWS, layout="start-finish")
    assert "column D holds “Complete”, a status word" in html.unescape(refused)
    assert [i["name"] for i in _layout(refused, ONEPAGER)["items"]] == ["Build"]


# ── compare: current positions only ───────────────────────────────────────────────────────────


def _offered(page: str) -> list[str]:
    return [t for _v, t, _x in _options(page, COMPARE)] + [
        t for _v, t, _x in _options(page, COMPARE, "To")
    ]


def test_a_removed_row_is_never_offered_and_cannot_be_linked(
    client: TestClient, state: SessionState
) -> None:
    """A REMOVED row is on the Compare slide (a ghost) but never in either select; posting its
    prior key anyway is refused as not on the slide, and nothing is drawn."""
    page = _load(client, COMPARE)
    assert _item(page, COMPARE, "Old Thing")["status"] == "removed"  # it IS on the slide…
    offered = _offered(page)
    assert offered == [DR, BUILD, TEST, SHIP] * 2  # …and never offered as a link end
    assert not any("Old Thing" in t for t in offered)
    assert state.onepager_prior is not None
    old_key = next(it.key for it in state.onepager_prior.items if it.name == "Old Thing")
    keys = _keys(page, COMPARE)
    page = _link(client, COMPARE, "add", old_key, keys[SHIP])
    said = "That item is no longer on the slide — pick it again from the list."
    assert _notice_role(_block(page, "opcLinks") or "", said) == "alert"
    assert _layout(page, COMPARE)["links"] == []


def test_mutation_a_removed_row_offered_is_caught(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: offer EVERY compared row (a REMOVED one under its prior row) — the check the
    real test uses sees "Old Thing" in the selects."""
    from schedule_forensics.reports.onepager_compare import row_label
    from schedule_forensics.web import onepager_compare as compare_page

    def every_row(st: Any) -> list[tuple[str, str, int | None]]:
        doc, _omitted = compare_page.onepager_compare_view(st)
        return [
            (r.key or f"removed{i}", row_label(r), r.current_row or r.prior_row)
            for i, r in enumerate(doc.rows if doc else ())
        ]

    monkeypatch.setattr(compare_page, "linkable_rows", every_row)
    assert any("Old Thing" in t for t in _offered(_load(client, COMPARE)))


def test_a_compare_link_joins_the_current_positions_never_the_ghost(client: TestClient) -> None:
    """Design Review slipped 1/10 -> 1/15: its ghost and its current diamond sit apart, and the
    link leaves the CURRENT diamond — FS out of a milestone's finish: its right vertex, at its
    centre line (ADR-0543) — and tips on Build's start, its shaft ending 4.2 pt before it."""
    keys = _keys(_load(client, COMPARE), COMPARE)
    page = _link(client, COMPARE, "add", keys[DR], keys[BUILD])
    dr = _item(page, COMPARE, "Design Review")
    assert dr["status"] == "slipped" and abs(dr["x0"] - dr["ghost_x0"]) > 5.0
    link = _layout(page, COMPARE)["links"][0]
    shaft = link["shaft"]
    assert shaft[0] == pytest.approx([dr["x0"] + dr["ms"] / 2, dr["y"]])
    assert abs(shaft[0][0] - dr["ghost_x0"]) > dr["ghost_ms"] / 2 + 1.0  # off the ghost
    build = _item(page, COMPARE, "Build")
    assert link["head"][0] == pytest.approx([build["x0"], build["y"]])  # FS: into its start
    assert shaft[-1] == pytest.approx([build["x0"] - 4.2, build["y"]])
