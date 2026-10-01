"""LODESTAR 2.0's studio API and its session log, driven over real HTTP (ADR-0543).

The studio is server-rendered and works with scripting off (plain forms → the v1 routes → 303);
with scripting on, ``lodestar_studio.js`` posts the SAME changes as JSON to ``/api/<action>`` and
repaints from the answer. Pinned here, each against the live server:

* **The state** — ``GET /api/state?page=…`` answers the design handoff's shape (the layout, the
  takeaway, the sub-sentence, the provenance chip, the banner, the notices, the links and what can
  be linked, the session log, undo / redo, the marking, the data date, the window, the title) plus
  the two regions the script swaps in — the SAME HTML the page itself renders.
* **Every action** changes what it says and is logged under the label the session log shows; a
  REFUSAL (a window that ends before it starts, a date that does not read, a link already drawn,
  a loop, an item linked to itself) and a no-op change nothing, log nothing, and say why in a
  ``warn`` toast.
* **Undo / redo** restore exactly the content they took away (the marking included), a new change
  clears the redo list, and the log keeps the newest 60 steps.
* **Preview** (``/api/preview``) lays out a PROPOSED change — a data date, a window, a link, the
  example list — and commits none of it: the session, its layout cache and its log are the same
  objects, unchanged, afterwards.
* **One door** — the same edits made through the form routes and through ``/api`` leave the two
  sessions in the same state, with the same log.
* **The JSON gates** — a studio call must be ``application/json`` (415), one object (400) of
  short plain values (400), within the form cap (413) — and still passes the SAME Host (400) and
  cross-site (403) gates every POST does; a refused call changes nothing.
* **Uploads with ``Accept: application/json``** answer the state, not a redirect.
* **Scripting off** — the served page's own forms, read out of its HTML and posted as a browser
  with no script would post them, take a list through upload → title → window → link → undo.

The oracle values (labels, sentences, item names) are typed here from the handoff and the
template's rows, never read out of the modules under test. Each load-bearing check has a
``test_mutation_*`` twin that breaks the product in memory and asserts the SAME checker goes red.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode

import pytest
from lodestar_probe import PRIOR_ROWS, ROWS, Reply, multipart, request, upload

from schedule_forensics.lodestar import server as server_mod
from schedule_forensics.lodestar.server import MAX_FORM_BYTES, LodestarServer, LodestarState
from schedule_forensics.web import lodestar_actions, lodestar_history, onepager_actions
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2026, 9, 1)
JSON_CT = ("Content-Type", "application/json")
#: The handoff's /api/state keys (ADR-0543), typed here.
STATE_KEYS = frozenset(
    {
        "layout",
        "takeaway",
        "sub",
        "prov",
        "banner",
        "notices",
        "links",
        "linkable",
        "history",
        "canUndo",
        "canRedo",
        "marking",
        "dataDate",
        "window",
        "title",
        "regions",
    }
)
#: What the operator owns — the session's content an undo must restore (typed here, not read off
#: ``lodestar_history.CONTENT``: a field that module forgot would be forgotten by both).
OWNED = (
    "onepager",
    "onepager_title",
    "onepager_window",
    "onepager_links",
    "onepager_today",
    "onepager_prior",
    "onepager_current",
    "onepager_compare_title",
    "onepager_compare_window",
    "onepager_compare_links",
    "unclassified",
)


@dataclass
class Live:
    server: LodestarServer
    state: LodestarState
    thread: threading.Thread

    @property
    def port(self) -> int:
        return int(self.server.server_port)


def _start(state: LodestarState | None = None) -> Live:
    st = state or LodestarState(onepager_today=None)
    srv = LodestarServer(0, st, TODAY)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    return Live(srv, st, thread)


def _stop(live: Live) -> None:
    socketserver.BaseServer.shutdown(live.server)
    live.server.server_close()
    live.thread.join(timeout=10)


@pytest.fixture
def live() -> Iterator[Live]:
    """A LODESTAR server on a free loopback port, its clock fixed at :data:`TODAY`."""
    one = _start()
    try:
        yield one
    finally:
        _stop(one)


# ── helpers ───────────────────────────────────────────────────────────────────────────────────


def _call(live: Live, verb: str, /, **fields: Any) -> dict[str, Any]:
    """``POST /api/<verb>`` (the studio's call) with ``fields`` as its JSON object (a field may
    itself be called ``action``) — the answer's JSON; it must be a 200."""
    got = request(
        live.port, "POST", f"/api/{verb}", body=json.dumps(fields).encode(), headers=[JSON_CT]
    )
    assert got.status == 200, (verb, got.status, got.body[:200])
    return dict(json.loads(got.body))


def _state(live: Live, page: str = "timeline") -> dict[str, Any]:
    got = request(live.port, "GET", f"/api/state?page={page}")
    assert got.status == 200 and got.headers["content-type"].startswith("application/json")
    return dict(json.loads(got.body))


def _owned(st: LodestarState) -> tuple[Any, ...]:
    return tuple(getattr(st, name) for name in OWNED)


def _key(state: dict[str, Any], name: str) -> str:
    """The link key of the item called ``name`` (its label is ``swimlane · name (dates)``)."""
    found = [x["key"] for x in state["linkable"] if f"· {name} (" in x["label"]]
    assert len(found) == 1, (name, [x["label"] for x in state["linkable"]])
    return str(found[0])


def _shape_problems(state: dict[str, Any]) -> list[str]:
    """What the state answer lacks or mistypes, each named by its key."""
    problems = [f"missing {k}" for k in sorted(STATE_KEYS - set(state))]
    checks: dict[str, Any] = {
        "takeaway": str,
        "sub": str,
        "prov": str,
        "title": str,
        "notices": list,
        "links": list,
        "linkable": list,
        "history": list,
        "canUndo": bool,
        "canRedo": bool,
        "marking": dict,
        "dataDate": str,
        "regions": dict,
    }
    for key, kind in checks.items():
        if key in state and not isinstance(state[key], kind):
            problems.append(f"{key}: {type(state[key]).__name__}, not {kind.__name__}")
    if not isinstance(state.get("layout"), dict | None):
        problems.append("layout: neither an object nor null")
    if state.get("banner") is not None and set(state["banner"]) != {"text", "status"}:
        problems.append(f"banner: {state['banner']}")
    window = state.get("window")
    if window is not None and not (isinstance(window, list) and len(window) == 2):
        problems.append(f"window: {window}")
    if isinstance(state.get("dataDate"), str):
        try:
            dt.date.fromisoformat(state["dataDate"])
        except ValueError:
            problems.append(f"dataDate: {state['dataDate']!r}")
    marking = state.get("marking") or {}
    if not {"cls", "text", "bg", "fg", "flip", "flipLabel"} <= set(marking):
        problems.append(f"marking: {sorted(marking)}")
    regions = state.get("regions") or {}
    if not (isinstance(regions.get("main"), str) and isinstance(regions.get("rail"), str)):
        problems.append("regions: no main / rail HTML")
    for n in state.get("notices") or []:
        if set(n) != {"key", "status", "title", "text", "items"}:
            problems.append(f"notice: {sorted(n)}")
    for ln in state.get("links") or []:
        if not {"pred", "succ", "kind", "pred_label", "succ_label", "drawn"} <= set(ln):
            problems.append(f"link: {sorted(ln)}")
    for x in state.get("linkable") or []:
        if set(x) != {"key", "label", "row"}:
            problems.append(f"linkable: {sorted(x)}")
    return problems


# ── the state ─────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("page", ["timeline", "compare"])
def test_the_state_api_answers_the_design_handoffs_shape(live: Live, page: str) -> None:
    """Empty, then loaded: every key the handoff names, each its own type — the layout ``null``
    with nothing to draw and the slide's geometry once a list is loaded; the regions as HTML."""
    empty = _state(live, page)
    assert _shape_problems(empty) == []
    assert empty["page"] == page and empty["layout"] is None and empty["history"] == []
    assert (empty["canUndo"], empty["canRedo"], empty["window"]) == (False, False, None)
    assert empty["marking"]["cls"] == "cui" and empty["dataDate"] == TODAY.isoformat()
    _call(live, "example", page=page)
    full = _state(live, page)
    assert _shape_problems(full) == []
    assert isinstance(full["layout"], dict) and full["layout"]["items"], "no slide geometry"
    assert full["linkable"] and full["prov"].startswith(("SOURCE:", "PRIOR:"))
    assert full["takeaway"] and full["canUndo"] is True
    assert "lsLinkForm" in full["regions"]["rail"] and "lsPanel" in full["regions"]["main"]
    # an unknown page name is the Timeline, never an error
    assert _state(live, "no-such-page")["page"] == "timeline"


def test_mutation_a_state_missing_a_key_or_mistyped_is_named(live: Live) -> None:
    """MUTATION: ``linkable`` dropped and ``canUndo`` sent as a string — both named."""
    broken = _state(live)
    del broken["linkable"]
    broken["canUndo"] = "no"
    assert _shape_problems(broken) == ["missing linkable", "canUndo: str, not bool"]


def _region(page: str, ident: str, tag: str) -> str:
    """The inner HTML of ``<tag … id=ident …>`` in a served page (no nested same tag inside)."""
    start = page.index(f"id={ident}")
    open_end = page.index(">", start) + 1
    return page[open_end : page.index(f"</{tag}>", open_end)]


@pytest.mark.parametrize("page,path", [("timeline", "/onepager"), ("compare", "/onepager-compare")])
def test_the_regions_the_script_swaps_in_are_the_pages_own(
    live: Live, page: str, path: str
) -> None:
    """One renderer: the MAIN and RAIL HTML ``/api/state`` hands the script are exactly what the
    page itself serves (so a sentence exists once, in Python)."""
    _call(live, "example", page=page)
    _state(live, page)  # consume the one-shot banner, so both reads see the same session
    served = request(live.port, "GET", path).text
    regions = _state(live, page)["regions"]
    assert regions["main"] == _region(served, "lsMain", "main")
    assert regions["rail"] == _region(served, "lsRail", "aside")


# ── every action, its label, and the refusals ─────────────────────────────────────────────────

#: Each step: ``(action, fields, the label the log shows, a check on the answer)``.
_ITEM_A, _ITEM_B, _ITEM_C = "Boots 1", "Uncrewed Lander Campaign", "CDR"


def test_every_action_changes_the_state_and_logs_its_label(live: Live) -> None:
    """Each studio action, through ``/api``: the answer carries its label, the log's newest entry
    is that label, and the state shows the change. Labels typed from the handoff."""
    seen: list[str] = []

    def step(verb: str, label: str, /, page: str = "timeline", **fields: Any) -> dict[str, Any]:
        got = _call(live, verb, page=page, **fields)
        assert got["label"] == label, (verb, fields, got["label"], got.get("toast"))
        assert got["history"][0] == label and got["canUndo"] is True
        seen.append(label)
        return got

    got = step("example", "List loaded: example-list.xlsx")
    assert got["layout"] is not None and len(got["linkable"]) == 6
    a, b, c = (_key(got, n) for n in (_ITEM_A, _ITEM_B, _ITEM_C))
    assert step("title", "Slide title changed", title="Program review")["title"] == (
        "Program review"
    )
    assert step("today", "Data date 2027-03-01", today="2027-03-01")["dataDate"] == "2027-03-01"
    assert step("today", "Data date cleared", action="clear")["dataDateChosen"] is False
    got = step(
        "window", "Date window 2027-01-01 → 2027-12-31", start="2027-01-01", end="2027-12-31"
    )
    assert got["window"] == ["2027-01-01", "2027-12-31"]
    assert step("window", "Date window cleared", action="clear")["window"] is None
    add = f"Add link {_ITEM_A} → {_ITEM_B} (FS)"
    got = step("links", add, action="add", pred=a, succ=b, kind="FS")
    assert [(x["pred"], x["succ"], x["kind"]) for x in got["links"]] == [(a, b, "FS")]
    got = step(
        "links", f"Add link {_ITEM_B} → {_ITEM_C} (SS)", action="add", pred=b, succ=c, kind="SS"
    )
    assert len(got["links"]) == 2
    got = step(
        "links",
        f"Remove link {_ITEM_A} → {_ITEM_B} (FS)",
        action="remove",
        pred=a,
        succ=b,
        kind="FS",
    )
    assert [(x["pred"], x["succ"]) for x in got["links"]] == [(b, c)]
    assert step("links", "Remove all links", action="clear")["links"] == []
    got = step("marking", "Marking switched to Unclassified", marking="unclassified")
    assert got["marking"]["cls"] == "unclassified"
    assert step("marking", "Marking switched to CUI", marking="cui")["marking"]["cls"] == "cui"
    got = step("example", "Both lists loaded", page="compare")
    assert got["loaded"] == {"timeline": True, "prior": True, "current": True}
    got = step("swap", "Prior and current swapped", page="compare")
    assert got["prov"].startswith("PRIOR: example-current.xlsx · CURRENT: example-prior.xlsx")
    got = step("clear", "Both lists cleared", page="compare")
    assert (got["loaded"]["prior"], got["loaded"]["current"]) == (False, False)
    got = step("clear", "List cleared")
    assert got["loaded"]["timeline"] is False and got["layout"] is None
    assert _state(live)["history"] == seen[::-1]  # the log, newest first


def test_uploads_with_accept_json_answer_the_state_and_are_logged(live: Live) -> None:
    """The studio posts a file with ``Accept: application/json``: the answer is the page's state
    (labelled, toasted), never a redirect; a PRIOR and a CURRENT are logged by slot; a file that
    is not a list is refused by name — logged as nothing."""

    def post(path: str, rows: Any, name: str, **fields: str) -> dict[str, Any]:
        body, ctype = multipart(fields, name, twin_xlsx(rows, omit_blank=True))
        got = request(
            live.port,
            "POST",
            path,
            body=body,
            headers=[("Content-Type", ctype), ("Accept", "application/json")],
        )
        assert got.status == 200 and got.headers["content-type"].startswith("application/json")
        return dict(json.loads(got.body))

    got = post("/onepager/upload", ROWS, "Program list.xlsx")
    assert (got["label"], got["toast"]["status"]) == ("List loaded: Program list.xlsx", "pass")
    assert got["page"] == "timeline" and got["layout"] is not None and "regions" in got
    got = post("/onepager-compare/upload", PRIOR_ROWS, "March.xlsx", slot="prior")
    assert got["label"] == "PRIOR list loaded" and got["page"] == "compare"
    got = post("/onepager-compare/upload", ROWS, "April.xlsx", slot="current")
    assert got["label"] == "CURRENT list loaded" and got["layout"] is not None
    before, log = _owned(live.state), _state(live)["history"]
    body, ctype = multipart({}, "notes.xlsx", b"this is not a workbook")
    bad = request(
        live.port,
        "POST",
        "/onepager/upload",
        body=body,
        headers=[("Content-Type", ctype), ("Accept", "application/json")],
    )
    refused = json.loads(bad.body)
    assert bad.status == 200 and refused["label"] is None and refused["toast"]["status"] == "warn"
    assert refused["toast"]["text"].startswith("Could not read that file")
    assert _owned(live.state) == before and _state(live)["history"] == log
    assert log == ["CURRENT list loaded", "PRIOR list loaded", "List loaded: Program list.xlsx"]


#: Each refusal: ``(name, action, fields)`` on a loaded Timeline (items by name; ``None`` → key).
_REFUSALS = [
    ("window ends before it starts", "window", {"start": "2027-12-31", "end": "2027-01-01"}),
    ("a data date that does not read", "today", {"today": "the thirty-first"}),
    ("a link already drawn", "links", {"action": "add", "pred": _ITEM_A, "succ": _ITEM_B}),
    ("a loop", "links", {"action": "add", "pred": _ITEM_B, "succ": _ITEM_A}),
    ("an item linked to itself", "links", {"action": "add", "pred": _ITEM_A, "succ": _ITEM_A}),
    ("a link no longer there", "links", {"action": "remove", "pred": _ITEM_C, "succ": _ITEM_A}),
]


def _refusal_outcomes(live: Live) -> dict[str, tuple[Any, ...]]:
    """For each refusal, on a list with one link A → B: ``(label, toast status, whether the
    session's content changed, whether the log grew)``."""
    first = _call(live, "example", page="timeline")
    keys = {n: _key(first, n) for n in (_ITEM_A, _ITEM_B, _ITEM_C)}
    _call(live, "links", page="timeline", action="add", pred=keys[_ITEM_A], succ=keys[_ITEM_B])
    out: dict[str, tuple[Any, ...]] = {}
    for name, action, fields in _REFUSALS:
        sent = {k: keys.get(v, v) if k in ("pred", "succ") else v for k, v in fields.items()}
        before, log = _owned(live.state), _state(live)["history"]
        got = _call(live, action, page="timeline", **sent)
        toast = got.get("toast") or {}
        out[name] = (
            got["label"],
            toast.get("status"),
            bool(toast.get("text")),
            _owned(live.state) != before,
            got["history"] != log,
        )
    return out


def test_refusals_change_nothing_log_nothing_and_say_why(live: Live) -> None:
    """A refused change is never half-applied and never a step: no label, a ``warn`` toast that
    says why, the session's content unchanged, the log unchanged."""
    assert _refusal_outcomes(live) == {
        name: (None, "warn", True, False, False) for name, *_ in _REFUSALS
    }


def test_mutation_a_refusal_logged_or_half_applied_is_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: (1) a door that logs EVERY call, whatever happened — the same table names each
    refusal's log; (2) a data-date action that keeps a date it could not read — named by its
    content."""
    real = lodestar_actions.perform

    def logs_everything(st: Any, history: Any, action: str, params: Any, **kw: Any) -> Any:
        before = lodestar_history.capture(st)
        outcome = real(st, history, action, params, **kw)
        history.record(f"{action} (whatever happened)", before, st, always=True)
        return outcome

    monkeypatch.setattr(lodestar_actions, "perform", logs_everything)
    logged = _refusal_outcomes(live)
    assert sorted(n for n, o in logged.items() if o[4]) == sorted(n for n, *_ in _REFUSALS)
    monkeypatch.undo()

    keep = onepager_actions.set_today

    def sloppy(st: Any, page: str, value: str, action: str) -> None:
        keep(st, page, value, action)
        st.onepager_today = dt.date(2000, 1, 1)  # half-applied: refused, yet changed

    monkeypatch.setattr(onepager_actions, "set_today", sloppy)
    fresh = _start()
    try:
        changed = _refusal_outcomes(fresh)
    finally:
        _stop(fresh)
    assert changed["a data date that does not read"][3] is True, changed


def test_a_change_to_the_same_value_is_not_a_step(live: Live) -> None:
    """The title set to what it already is, a window cleared when none is set, the data date
    cleared when none is chosen: answered, unlogged (``label`` null)."""
    _call(live, "title", page="timeline", title="Same")
    log = _state(live)["history"]
    for action, fields in (
        ("title", {"title": "Same"}),
        ("window", {"action": "clear"}),
        ("today", {"action": "clear"}),
        ("links", {"action": "clear"}),
    ):
        got = _call(live, action, page="timeline", **fields)
        assert got["label"] is None and got["history"] == log, (action, got["label"])


# ── undo / redo ───────────────────────────────────────────────────────────────────────────────


def test_undo_and_redo_restore_exactly_what_they_took_the_marking_included(live: Live) -> None:
    """Each step back restores the session's content as it was before that step (compared
    attribute by attribute); redo puts the step back; the toasts name the step."""
    contents = [_owned(live.state)]
    _call(live, "example", page="timeline")
    contents.append(_owned(live.state))
    _call(live, "title", page="timeline", title="Review")
    contents.append(_owned(live.state))
    _call(live, "marking", page="timeline", marking="unclassified")
    contents.append(_owned(live.state))
    assert live.state.unclassified is True
    for want in reversed(contents[:-1]):
        got = _call(live, "undo", page="timeline")
        assert got["toast"]["text"].startswith("Undid: ") and got["label"]
        assert _owned(live.state) == want
    assert live.state.unclassified is False and _state(live)["canRedo"] is True
    nothing = _call(live, "undo", page="timeline")
    assert (nothing["label"], nothing["toast"]["text"]) == (None, "Nothing to undo.")
    for want in contents[1:]:
        got = _call(live, "redo", page="timeline")
        assert got["toast"]["text"].startswith("Redid: ")
        assert _owned(live.state) == want
    assert live.state.unclassified is True and live.state.onepager_title == "Review"
    assert _call(live, "redo", page="timeline")["toast"]["text"] == "Nothing to redo."
    # the marking is the PAGE's too: its bars follow an undo
    _call(live, "undo", page="timeline")
    page = request(live.port, "GET", "/onepager").text
    assert page.count('class="ls-mark-bar cui-banner cui ') == 2


def test_a_new_change_clears_the_redo_list(live: Live) -> None:
    _call(live, "title", page="timeline", title="One")
    _call(live, "title", page="timeline", title="Two")
    assert _call(live, "undo", page="timeline")["canRedo"] is True
    got = _call(live, "title", page="timeline", title="Three")
    assert got["canRedo"] is False and got["history"] == ["Slide title changed"] * 2
    assert _call(live, "redo", page="timeline")["toast"]["text"] == "Nothing to redo."
    assert live.state.onepager_title == "Three"


def test_the_form_routes_undo_and_redo_too(live: Live) -> None:
    """Scripting off, the header's two buttons post ``/undo`` and ``/redo`` — 303 back to the
    page named in ``next`` (only LODESTAR's own two)."""
    _call(live, "title", page="compare", title="Before")
    _call(live, "title", page="compare", title="After")
    got = _form(live, "/undo", {"next": "/onepager-compare"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager-compare")
    assert live.state.onepager_compare_title == "Before"
    got = _form(live, "/redo", {"next": "https://evil.example/"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager")
    assert live.state.onepager_compare_title == "After"


#: The handoff's figure, typed here.
MAX_STEPS = 60


def test_the_log_keeps_the_newest_sixty_steps(live: Live) -> None:
    """65 changes: the log holds the newest 60; sixty undos reach the content before the sixth
    change, and a sixty-first has nothing to undo."""
    for n in range(1, 66):
        _call(live, "title", page="timeline", title=f"T{n}")
    state = _state(live)
    assert len(state["history"]) == MAX_STEPS
    for _ in range(MAX_STEPS):
        assert _call(live, "undo", page="timeline")["label"] == "Slide title changed"
    assert live.state.onepager_title == "T5"
    assert _call(live, "undo", page="timeline")["label"] is None


def test_mutation_a_longer_log_is_named(live: Live, monkeypatch: pytest.MonkeyPatch) -> None:
    """MUTATION: the log's cap raised by one — the same count sees 61."""
    monkeypatch.setattr(lodestar_history, "MAX_STEPS", MAX_STEPS + 1)
    for n in range(1, 66):
        _call(live, "title", page="timeline", title=f"T{n}")
    assert len(_state(live)["history"]) == MAX_STEPS + 1


# ── preview: laid out, never committed ────────────────────────────────────────────────────────


def _preview(live: Live, **proposal: Any) -> dict[str, Any]:
    return _call(live, "preview", **proposal)


def _untouched_problems(live: Live, run: Any) -> list[str]:
    """Run ``run()`` (previews); what it changed in the session — its content, its layout
    cache (the very objects), its log — named."""
    st = live.state
    content = _owned(st)
    cache = dict(st.onepager_cache)
    past, future = list(st.history.past), list(st.history.future)
    run()
    problems = []
    if _owned(st) != content:
        problems.append("content")
    if set(st.onepager_cache) != set(cache) or any(
        st.onepager_cache[k] is not v for k, v in cache.items()
    ):
        problems.append("cache")
    if st.history.past != past or st.history.future != future:
        problems.append("log")
    return problems


def test_preview_lays_out_a_proposal_and_commits_none_of_it(live: Live) -> None:
    """Each proposal comes back as a layout that SHOWS it — the red line at the proposed date,
    the slide scoped to the proposed window, the proposed link routed, the example list on an
    empty page — while the session, its cache and its log are untouched."""
    empty: dict[str, Any] = {}

    def on_empty() -> None:
        got = _preview(live, page="timeline", example=True)
        empty.update(got)

    assert _untouched_problems(live, on_empty) == []
    assert empty["layout"] is not None and live.state.onepager is None

    base = _call(live, "example", page="timeline")
    a, b = _key(base, _ITEM_A), _key(base, _ITEM_C)
    _state(live)  # the layout cache now holds the committed slide
    seen: dict[str, Any] = {}

    def proposals() -> None:
        seen["today"] = _preview(live, page="timeline", today="2027-05-01")
        seen["window"] = _preview(live, page="timeline", window=["2027-01-01", "2027-06-30"])
        seen["all"] = _preview(live, page="timeline", window=None)
        seen["link"] = _preview(live, page="timeline", pred=a, succ=b, kind="SF")
        seen["compare"] = _preview(live, page="compare", example=True)

    assert _untouched_problems(live, proposals) == []
    assert seen["today"]["layout"]["today_iso"] == "2027-05-01"
    assert seen["today"]["dataDate"] == "2027-05-01"
    assert (
        seen["window"]["layout"]["t0"] >= "2027-01-01"
        and seen["window"]["layout"]["t1"] <= "2027-07-01"
    )
    assert seen["all"]["layout"]["t0"] == base["layout"]["t0"]
    assert [(ln["pred"], ln["succ"], ln["kind"]) for ln in seen["link"]["layout"]["links"]] == [
        (a, b, "SF")
    ]
    assert seen["compare"]["layout"] is not None and seen["compare"]["page"] == "compare"
    after = _state(live)
    assert (
        after["links"] == [] and after["window"] is None and after["dataDate"] == TODAY.isoformat()
    )
    assert after["history"] == ["List loaded: example-list.xlsx"]


def test_mutation_a_preview_on_the_session_itself_is_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a preview that works on the SESSION instead of a copy (``replace`` returning
    the session itself) — the same check names the content it committed."""
    base = _call(live, "example", page="timeline")
    a, b = _key(base, _ITEM_A), _key(base, _ITEM_C)
    monkeypatch.setattr(server_mod, "replace", lambda st, **_kw: st)

    def propose() -> None:
        _preview(live, page="timeline", pred=a, succ=b, kind="FS")

    assert "content" in _untouched_problems(live, propose)


# ── one door: the forms and the API make the same session ─────────────────────────────────────


def _form(live: Live, path: str, fields: dict[str, str]) -> Reply:
    return request(
        live.port,
        "POST",
        path,
        body=urlencode(fields).encode(),
        headers=[("Content-Type", "application/x-www-form-urlencoded")],
    )


def test_the_form_routes_and_the_api_make_the_same_session() -> None:
    """The same edits — a list, a title, a window, a data date, a link, the marking, a swap, an
    undo — made through the v1 form routes on one server and through ``/api`` on another leave
    the two in the same state: the same answer from ``/api/state`` on both pages (layout, links,
    log, marking …) and the same regions."""
    by_form, by_api = _start(), _start()
    try:
        assert upload(by_form.port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
        _call(by_api, "example", page="timeline")  # a different list first …
        _call(by_api, "clear", page="timeline")  # … and gone (two steps the form side lacks)
        body, ctype = multipart({}, "Program list.xlsx", twin_xlsx(ROWS, omit_blank=True))
        got = request(
            by_api.port,
            "POST",
            "/onepager/upload",
            body=body,
            headers=[("Content-Type", ctype), ("Accept", "application/json")],
        )
        assert got.status == 200
        keys = {x["label"]: x["key"] for x in _state(by_api)["linkable"]}
        dr, build = (
            keys["Alpha · Design Review (1/15/27)"],
            keys["Alpha · Build (2/1/27 to 4/15/27)"],
        )
        edits = [
            ("/onepager/title", "title", {"title": "Review"}),
            (
                "/onepager/window",
                "window",
                {"start": "2027-01-01", "end": "2027-12-31", "action": "apply"},
            ),
            ("/onepager/today", "today", {"today": "2027-02-01", "action": "apply"}),
            (
                "/onepager/links",
                "links",
                {"action": "add", "pred": dr, "succ": build, "kind": "SS"},
            ),
            ("/marking", "marking", {"marking": "unclassified"}),
            ("/onepager-compare/example", "example", {}),
            ("/onepager-compare/swap", "swap", {}),
            ("/onepager-compare/title", "title", {"title": "Moves"}),
        ]
        for path, action, fields in edits:
            assert _form(by_form, path, fields).status == 303, path
            page = "compare" if path.startswith("/onepager-compare") else "timeline"
            _call(by_api, action, page=page, **fields)
        assert _form(by_form, "/undo", {"next": "/onepager"}).status == 303
        _call(by_api, "undo", page="timeline")
        assert _owned(by_form.state) == _owned(by_api.state)  # by value: equal documents
        for page in ("timeline", "compare"):
            a, b = _state(by_form, page), _state(by_api, page)
            log_a, log_b = a.pop("history"), b.pop("history")
            assert log_b[: len(log_a)] == log_a  # the API side has its two extra steps at the end
            assert log_b[len(log_a) :] == ["List cleared", "List loaded: example-list.xlsx"]
            for one in (a, b):
                one["regions"] = {k: _without_log(v) for k, v in one["regions"].items()}
            assert a == b, page
    finally:
        _stop(by_form)
        _stop(by_api)


def _without_log(html: str) -> str:
    """A region without the session log and the change history (the one place two sessions
    whose logs differ in their oldest steps may differ)."""
    html = re.sub(_LOG_SECTION, "", html, flags=re.S)
    return re.sub(r"<section class=ls-history.*?</section>", "", html, flags=re.S)


_LOG_SECTION = (
    r"<section class=ls-sec><div class=ls-sec-head><div class=ls-kicker>Session log.*?</section>"
)


# ── the JSON gates ────────────────────────────────────────────────────────────────────────────


def _raw_api(
    live: Live, body: bytes, headers: list[tuple[str, str]], *, action: str = "title", **kw: Any
) -> Reply:
    return request(live.port, "POST", f"/api/{action}", body=body, headers=headers, **kw)


_OK_BODY = json.dumps({"page": "timeline", "title": "Landed"}).encode()
#: The title every gate case starts from — so a refused call that CLEARED it (a field read as
#: missing) is seen, not only one that set it.
_KEPT = "Kept"


def _bodies(live: Live) -> dict[str, Any]:
    """Each kind of bad studio call, ready to send."""
    port = live.port
    form_ct = [("Content-Type", "application/x-www-form-urlencoded")]

    def title(value: object) -> Any:
        body = json.dumps({"page": "timeline", "title": value}).encode()
        return lambda: _raw_api(live, body, [JSON_CT])

    return {
        "form-encoded": lambda: _raw_api(live, b"title=Landed", form_ct),
        "text/plain": lambda: _raw_api(live, _OK_BODY, [("Content-Type", "text/plain")]),
        "no type": lambda: _raw_api(live, _OK_BODY, []),
        "not json": lambda: _raw_api(live, b"{title: Landed", [JSON_CT]),
        "a list": lambda: _raw_api(live, b'["Landed"]', [JSON_CT]),
        "a string": lambda: _raw_api(live, b'"Landed"', [JSON_CT]),
        "a number": lambda: _raw_api(live, b"42", [JSON_CT]),
        "nested object": lambda: _raw_api(live, b'{"title": {"x": "Landed"}}', [JSON_CT]),
        "long list": lambda: _raw_api(live, b'{"title": ["a", "b", "c"]}', [JSON_CT]),
        "list of numbers": lambda: _raw_api(live, b'{"title": [1, 2]}', [JSON_CT]),
        # a studio ACTION's values are strings — a flag, a null, a pair or a number is refused,
        # never read as a missing field (lead's fix 2026-10-01: "title": true cleared the title)
        "title true": title(True),
        "title null": title(None),
        "title pair": title(["a", "b"]),
        "title number": title(5),
        "window flag": lambda: _raw_api(
            live,
            b'{"page": "timeline", "start": true, "end": "2027-01-01"}',
            [JSON_CT],
            action="window",
        ),
        "links pair": lambda: _raw_api(
            live,
            b'{"page": "timeline", "action": "clear", "pred": ["a", "b"]}',
            [JSON_CT],
            action="links",
        ),
        "long key": lambda: _raw_api(live, json.dumps({"k" * 33: "Landed"}).encode(), [JSON_CT]),
        "over the cap": lambda: _raw_api(
            live, b"{}", [JSON_CT, ("Content-Length", str(MAX_FORM_BYTES + 1))]
        ),
        "no length": lambda: request(port, "POST", "/api/title", headers=[JSON_CT]),
        "cross-site": lambda: _raw_api(live, _OK_BODY, [JSON_CT, ("Sec-Fetch-Site", "cross-site")]),
        "foreign origin": lambda: _raw_api(
            live, _OK_BODY, [JSON_CT, ("Origin", "http://127.0.0.1:1")]
        ),
        "bad host": lambda: _raw_api(live, _OK_BODY, [JSON_CT, ("Host", "evil.example")]),
        "chunked": lambda: _raw_api(
            live, b"0\r\n\r\n", [JSON_CT, ("Transfer-Encoding", "chunked")]
        ),
        "unknown action": lambda: _raw_api(live, _OK_BODY, [JSON_CT], action="nope"),
        "upload as json": lambda: _raw_api(live, _OK_BODY, [JSON_CT], action="upload"),
    }


def _gate_outcomes(live: Live) -> dict[str, tuple[int, bool]]:
    """Each kind of bad studio call → ``(its status, whether it changed the session)`` — the
    title (set to :data:`_KEPT` first), the links, the window and the log all watched."""
    _call(live, "title", page="timeline", title=_KEPT)
    out: dict[str, tuple[int, bool]] = {}
    for name, send in _bodies(live).items():
        before, steps = _owned(live.state), len(live.state.history.past)
        got = send()
        changed = _owned(live.state) != before or len(live.state.history.past) != steps
        out[name] = (got.status, changed)
        if got.status >= 400:
            assert "error" in json.loads(got.body), name
        if got.status >= 400 and name != "unknown action":  # refused at the gate, body unread
            assert got.headers.get("connection") == "close", name
    return out


_GATES = {
    "form-encoded": 415,
    "text/plain": 415,
    "no type": 415,
    "not json": 400,
    "a list": 400,
    "a string": 400,
    "a number": 400,
    "nested object": 400,
    "long list": 400,
    "list of numbers": 400,
    "title true": 400,
    "title null": 400,
    "title pair": 400,
    "title number": 400,
    "window flag": 400,
    "links pair": 400,
    "long key": 400,
    "over the cap": 413,
    "no length": 411,
    "cross-site": 403,
    "foreign origin": 403,
    "bad host": 400,
    "chunked": 400,
    "unknown action": 404,
    "upload as json": 400,
}


def _wrong(outcomes: dict[str, tuple[int, bool]]) -> list[str]:
    """The cases whose outcome is not the gate's: another status, or the session changed."""
    return sorted(
        n for n, (status, changed) in outcomes.items() if (status, changed) != (_GATES[n], False)
    )


def test_the_studios_json_calls_pass_every_gate(live: Live) -> None:
    """Every refused call is refused before the route runs — the title stays what it was, the
    log does not grow — answered as JSON naming why, its connection closed; and a good call
    lands."""
    outcomes = _gate_outcomes(live)
    assert {n: s for n, (s, _c) in outcomes.items()} == _GATES
    assert _wrong(outcomes) == []
    assert live.state.onepager_title == _KEPT and _state(live)["history"] == ["Slide title changed"]
    assert _raw_api(live, _OK_BODY, [JSON_CT]).status == 200
    assert live.state.onepager_title == "Landed"


def test_a_preview_still_takes_a_flag_and_a_pair_of_dates(live: Live) -> None:
    """The preview's own two non-string values stay allowed — ``example: true`` and a
    ``window`` of two dates — and commit nothing."""
    for proposal in ({"example": True}, {"example": True, "window": ["2026-10-01", "2027-12-31"]}):
        got = request(
            live.port,
            "POST",
            "/api/preview",
            body=json.dumps({"page": "timeline", **proposal}).encode(),
            headers=[JSON_CT],
        )
        assert got.status == 200, (proposal, got.body[:120])
        assert json.loads(got.body)["layout"] is not None, proposal
    assert live.state.onepager is None and live.state.history.past == []


#: The studio reader as ADR-0543's first draft shipped it (typed here as the mutation): flags,
#: nulls and short pairs taken for ANY call, numbers turned into strings.
def _first_draft_json_body(self: Any, *, preview: bool = False) -> dict[str, Any]:
    ctype = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if ctype != "application/json":
        raise server_mod._Refused(415, "a studio call must be application/json")
    raw = self._body(MAX_FORM_BYTES)
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, ValueError) as exc:
        raise server_mod._Refused(400, "the request body is not JSON") from exc
    if not isinstance(data, dict):
        raise server_mod._Refused(400, "the request body must be a JSON object")
    out: dict[str, Any] = {}
    for key, value in data.items():
        if not isinstance(key, str) or len(key) > 32:
            raise server_mod._Refused(400, "a request field name is not valid")
        if isinstance(value, bool) or value is None:
            out[key] = value
        elif isinstance(value, str | int | float):
            out[key] = str(value)[:256]
        elif (
            isinstance(value, list)
            and len(value) <= 2
            and all(isinstance(v, str) and len(v) <= 40 for v in value)
        ):
            out[key] = list(value)
        else:
            raise server_mod._Refused(400, "a request field is not a string")
    return out


_ACTION_VALUES = [
    "links pair",
    "title null",
    "title number",
    "title pair",
    "title true",
    "window flag",
]


def test_mutation_a_reader_that_takes_preview_values_everywhere_is_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (lead's twin): every call read as a preview — the flag, null and pair cases go
    through and are named; a number is still refused (a preview takes none either)."""
    real = server_mod._Handler._json_body

    def everywhere(self: Any, *, preview: bool = False) -> dict[str, Any]:
        return real(self, preview=True)  # type: ignore[no-any-return]

    monkeypatch.setattr(server_mod._Handler, "_json_body", everywhere)
    assert _wrong(_gate_outcomes(live)) == [n for n in _ACTION_VALUES if n != "title number"]


def test_mutation_the_first_draft_reader_is_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the first draft's reader back — all six action-value cases are named, the number
    one included (it was read as the string ``"5"``)."""
    monkeypatch.setattr(server_mod._Handler, "_json_body", _first_draft_json_body)
    wrong = _wrong(_gate_outcomes(live))
    assert wrong == _ACTION_VALUES, wrong


def test_mutation_a_gate_that_takes_any_body_is_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the JSON reader without its type and shape checks (any body read as an object of
    strings) — the same table names the cases it now lets through."""

    def lax(self: Any, **_kw: Any) -> dict[str, Any]:
        raw = self._body(MAX_FORM_BYTES)
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            data = {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    monkeypatch.setattr(server_mod._Handler, "_json_body", lax)
    wrong = _wrong(_gate_outcomes(live))
    assert {"text/plain", "no type", "form-encoded", "title true", "nested object"} <= set(wrong)


# ── scripting off: the page's own forms do the whole job ──────────────────────────────────────


class _Forms(HTMLParser):
    """Every ``<form>`` in a page: its action, method, enctype, its fields (hidden inputs and the
    rest, with their values), its selects' options and its submit buttons — and whether it, or
    anything around it, is hidden when scripting is off (``ls-js-only`` / ``data-ls-jsonly``)."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._stack: list[bool] = []  # per open element: hidden-without-script?
        self._form: dict[str, Any] | None = None
        self._select: str | None = None
        self.feed(page)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        js_only = "ls-js-only" in a.get("class", "").split() or "data-ls-jsonly" in a
        hidden = js_only or any(self._stack)
        if tag not in ("input", "meta", "link", "br", "img"):
            self._stack.append(hidden)
        if tag == "form":
            self._form = {**a, "fields": {}, "selects": {}, "buttons": [], "nojs_hidden": hidden}
            self.forms.append(self._form)
        elif self._form is not None:
            kind = a.get("type")
            named = tag == "input" and bool(a.get("name"))
            if named and (kind not in ("file", "radio") or (kind == "radio" and "checked" in a)):
                self._form["fields"][a["name"]] = a.get("value", "")
            if tag == "select":
                self._select = a.get("name")
                self._form["selects"][self._select] = []
            elif tag == "option" and self._select:
                self._form["selects"][self._select].append((a.get("value", ""), a.get("title", "")))
                if "selected" in a or self._select not in self._form["fields"]:
                    self._form["fields"][self._select] = a.get("value", "")  # what it submits
            elif tag == "button" and a.get("type") == "submit":
                unusable = hidden or "disabled" in a
                self._form["buttons"].append((a.get("name", ""), a.get("value", ""), unusable))

    def handle_endtag(self, tag: str) -> None:
        if tag in ("input", "meta", "link", "br", "img"):
            return
        if self._stack:
            self._stack.pop()
        if tag == "form":
            self._form = None
        elif tag == "select":
            self._select = None


def _form_for(page: str, action: str, *, want: str = "") -> dict[str, Any]:
    """The ONE visible-without-script form posting to ``action`` (whose fields include ``want``)."""
    found = [
        f
        for f in _Forms(page).forms
        if f.get("action") == action and (not want or want in f["fields"] or want in f["selects"])
    ]
    assert len(found) >= 1, f"no form posts to {action}"
    shown = [f for f in found if not f["nojs_hidden"]]
    assert shown, f"every form posting to {action} is hidden without scripting"
    return shown[0]


def _submit(live: Live, form_: dict[str, Any], **values: str) -> Reply:
    """Post ``form_`` as a browser with no script would: its own fields and a VISIBLE submit
    button (its name and value), with ``values`` typed into the named fields."""
    assert form_.get("method") == "post"
    fields = dict(form_["fields"])
    visible = [b for b in form_["buttons"] if not b[2]]
    assert visible, f"{form_.get('action')}: no submit button shows without scripting"
    name, value, _hidden = visible[0]
    if name:
        fields[name] = value
    for key, val in values.items():
        assert key in fields or key in form_["selects"], (form_.get("action"), key)
        fields[key] = val
    return _form(live, str(form_["action"]), fields)


def test_with_scripting_off_the_pages_own_forms_do_the_whole_job(live: Live) -> None:
    """A browser with no script: everything it needs is a plain form in the served HTML — upload
    a list (multipart, to the drop zone's own action), name the slide, scope the dates, link two
    items picked from the From / To lists, undo — each a 303 back to the page, which then shows
    the change. Nothing here is a studio call."""
    page = request(live.port, "GET", "/onepager").text
    drop = _form_for(page, "/onepager/upload")
    assert drop.get("enctype") == "multipart/form-data"
    body, ctype = multipart(drop["fields"], "Program list.xlsx", twin_xlsx(ROWS, omit_blank=True))
    sent = request(live.port, "POST", drop["action"], body=body, headers=[("Content-Type", ctype)])
    assert (sent.status, sent.headers.get("location")) == (303, "/onepager")
    page = request(live.port, "GET", "/onepager").text
    assert "Program list.xlsx" in page and live.state.onepager is not None

    got = _submit(live, _form_for(page, "/onepager/title"), title="Program review")
    assert got.status == 303 and live.state.onepager_title == "Program review"
    page = request(live.port, "GET", "/onepager").text
    assert 'value="Program review"' in page

    got = _submit(live, _form_for(page, "/onepager/window"), start="2027-01-01", end="2027-12-31")
    assert got.status == 303 and live.state.onepager_window == (
        dt.date(2027, 1, 1),
        dt.date(2027, 12, 31),
    )
    page = request(live.port, "GET", "/onepager").text

    links = _form_for(page, "/onepager/links", want="pred")
    options = {title: value for value, title in links["selects"]["pred"] if value}
    dr, build = (
        options["Alpha · Design Review (1/15/27)"],
        options["Alpha · Build (2/1/27 to 4/15/27)"],
    )
    got = _submit(live, links, pred=dr, succ=build)
    assert (got.status, got.headers.get("location")) == (303, "/onepager#lsLinks")
    assert [(ln.pred, ln.succ, ln.kind) for ln in live.state.onepager_links] == [(dr, build, "FS")]
    page = request(live.port, "GET", "/onepager").text
    assert "id=lsLinks" in page and "Design Review → Build" in page

    undo = _form_for(page, "/undo")
    assert undo["fields"].get("next") == "/onepager"
    got = _submit(live, undo)
    assert (got.status, got.headers.get("location")) == (303, "/onepager")
    assert live.state.onepager_links == () and live.state.onepager_title == "Program review"
    page = request(live.port, "GET", "/onepager").text
    assert "id=lsLinks" not in page  # the rail lists no link any more


def test_mutation_a_form_hidden_without_scripting_is_named() -> None:
    """MUTATION: the title form marked script-only — the no-script reader refuses it by name."""
    page = (
        '<div class=ls-js-only><form action="/onepager/title" method=post><input name=title>'
        "<button type=submit>Apply</button></form></div>"
    )
    with pytest.raises(AssertionError, match="hidden without scripting"):
        _form_for(page, "/onepager/title")
    shown = '<form action="/x" method=post><button type=submit data-ls-jsonly>Go</button></form>'
    with pytest.raises(AssertionError, match="no submit button shows"):
        _submit(Live(None, None, None), _form_for(shown, "/x"))  # type: ignore[arg-type]
