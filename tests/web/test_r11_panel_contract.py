"""Ultracode round 11 — /path, /driving-path, /evolution and /volatility wear the panel contract.

**This module exists because round 10 rotted silently.** ``test_portfolio_panelkit.py:105`` and
``test_integrity_panelkit.py:105`` assert that a ⛶ click lands ``.is-big`` on the panel — and that
assertion passed for months while the control moved *nothing*: ``.is-big`` is only
``grid-column:1/-1`` (base.css), so on a BLOCK-layout panel it is inert (ADR-0304). A class
read-back is not a proof. Every ⛶ assertion below reads ``getBoundingClientRect()`` on both sides
of a real click and requires the box to have CHANGED.

What this pins, per hazard:

* **the effect, in real chromium** — one BLOCK-layout panel (/driving-path's "Driving tiers")
  measurably lifts into the fixed focus overlay, and one /volatility MOSAIC tile measurably grows
  *in the flow* (``position`` stays ``static``). The two enlarge layouts are structurally
  different and the test proves each takes its own path, so a future edit cannot quietly convert
  the Mission wall into modals;
* **the include** — ``panelkit.js`` is a per-page ``<script src>``; two of them register two
  delegated listeners and every click would toggle ``.is-big`` twice and net to nothing. Matched
  as a SUBSTRING because ``_page`` cache-busts static URLs to ``?v=<version>``. It must be ABSENT
  on the two /driving-path branches that render no contract control at all (bare, and a target no
  loaded version carries) — a script with nothing to drive is a promise the page cannot keep;
* **every ⤓ destination is live** — each ``data-export`` on the four routes is fetched and must
  answer 200 with the ``PK`` zip magic. A dead ⤓ is worse than no ⤓ in a testimony context;
* **the ⤓ that must NOT exist** — /driving-path's "All driving-tier activities" panel and BOTH
  /evolution what-if panels carry NO ``data-export``, because ``driving_tiers.js`` and
  ``whatif.js`` rebuild ``&cols=<live selection>`` on every render while ``panelkit.js`` reads a
  STATIC attribute. Pinning a URL there hands the operator the DEFAULT columns while they are
  looking at theirs — the round-10 /performance defect. /path carries none either: its export
  route declares ``target`` REQUIRED and answers 422 without one;
* **the promotion census** — the conversion decorates panels that were already ``.panel``, so the
  per-route ``.panel`` count is unchanged and nothing NEW joins jarvis's broad
  ``html[data-theme=jarvis] .panel`` fight. The frozen counts were derived from a live render on
  BOTH trees (patched, then ``git stash`` to pristine, then re-run) and cross-checked against
  ``document.querySelectorAll('.panel').length`` in real chromium: 5 / 13 / 9 / 14;
* **these pages' own HAZARDS (standing requirement 4)** — all four carry GET ``<form>`` elements
  and three carry an embedded CSP JSON payload (``#volData``, ``#drivingTiersData``, ``#dpData``,
  ``#whatifAddedData``). Round 11 is a markup round, so both must be byte-identical; they are
  frozen here by md5 + length, and were verified equal to the pre-round render;
* **the axis-caption freeze (standing requirement 5)** — the seven page-owned chart scripts and
  all **16** ``SFChartFrame.axisTitles(`` call sites are frozen. The call site is hashed together
  with its argument object (the captions live on the FOLLOWING lines — hashing the opening line
  alone collides nine ways and would pass while a caption moved);
* **the loaded-terms gate WITH ITS CONTROL** — every visible string round 11 added is harvested
  from the RENDER (never retyped) and run through ``introduces_loaded_terms``; the same test first
  asserts the gate is alive on ``deliberate concealed fraud``;
* **the CSS the whole round rests on** — the overlay rule's two structural exclusions
  (``:not(.tile)``, ``:not(:has(.sf-tilebox))``) and the ``@media print`` reset. Deleting the
  first converts the Mission wall to modals; deleting the second nests a fixed box inside a fixed
  box; deleting the third prints the overlay as a floating card over a testimony report.

The browser halves skip cleanly where the python ``playwright`` package is absent (the runtime
stays std-lib only); the markup, export, freeze and gate halves always run.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.citations import introduces_loaded_terms
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "test_projects"
STATIC = REPO / "src" / "schedule_forensics" / "web" / "static"

#: the five TP4 DataCenter snapshots, uploaded as ONE five-version project (``file_meta`` groups
#: them by folder — without it each file is its own one-version project and /evolution,
#: /volatility and /driving-path render their "load at least two analyzable versions" fallback).
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]

#: "Substantial completion", the project finish milestone — the session focus the four pages open
#: on. /path renders its workspace take only with a target set; /driving-path needs one to trace.
TARGET_UID = 26

#: the four converted routes, in the order the round landed them.
VOL = "/volatility"
DP = f"/driving-path?source=11&target={TARGET_UID}"
EVO = "/evolution"
PATH = "/path"
ROUTES = (PATH, DP, EVO, VOL)

#: panelkit.js's exact strings — these pages may only ever render these.
EXCEL_LABEL = "⤓ EXCEL"
ENLARGE_LABEL = "⛶ ENLARGE"
SHRINK_LABEL = "⛶ SHRINK"


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────


def _load(client: TestClient) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    assert (
        client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False).status_code
        == 303
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    _load(c)
    return c


@pytest.fixture(scope="module")
def pages(client: TestClient) -> dict[str, str]:
    """Each converted route rendered once — every markup assertion reads the SAME bytes."""
    return {r: client.get(r).text for r in ROUTES}


# ── html helpers ──────────────────────────────────────────────────────────────────────────────

#: a panel OPEN tag. The negative lookahead is load-bearing: without it ``class=panel-head``
#: matches too and every panel is split in half (it also inflates the census — /path counts 6).
_PANEL_OPEN = re.compile(r'<(?:div|section)[^>]*\bclass="?[^">]*\bpanel(?![-\w])[^">]*"?[^>]*>')
_H = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.S)
_TAKE = re.compile(r"<p class=sf-take[^>]*>(.*?)</p>", re.S)
_CTRL = re.compile(r"<button[^>]*\bdata-sf-(?:big|excel|data)\b[^>]*>(.*?)</button>", re.S)
_CTRL_TAG = re.compile(r"<button[^>]*\bdata-sf-(?:big|excel|data)\b[^>]*>")
_ATTR = re.compile(r'(?:title|aria-label)="([^"]*)"')
_CHIP = re.compile(r"<span class=prov-chip[^>]*>(.*?)</span>", re.S)
_FORM = re.compile(r"<form\b.*?</form>", re.S)
_JSON_BLOB = re.compile(r'<script type="application/json" id=(\w+)>(.*?)</script>', re.S)
_EXPORT = re.compile(r'data-export="([^"]+)"')


def _panels(page: str) -> list[str]:
    """The page split into its panel chunks (open tag + body). These pages never nest a panel."""
    starts = [m.start() for m in _PANEL_OPEN.finditer(page)]
    bounds = [*starts, len(page)]
    return [page[bounds[i] : bounds[i + 1]] for i in range(len(starts))]


def _panel_titled(page: str, needle: str) -> str:
    """The one panel chunk whose own h2/h3 contains ``needle`` (asserted unique)."""
    hits = [c for c in _panels(page) if any(needle in h for h in _H.findall(c))]
    assert len(hits) == 1, f"{needle!r}: expected 1 panel, found {len(hits)}"
    return hits[0]


def _visible(fragment: str) -> str:
    """A rendered fragment as the analyst reads it: tags stripped, entities resolved."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ── (b) the include ───────────────────────────────────────────────────────────────────────────


def test_panelkit_is_included_exactly_once_on_every_converted_route(
    pages: dict[str, str],
) -> None:
    """Two ``<script src>`` elements register two delegated listeners: every ⛶ click would toggle
    ``.is-big`` twice and net to a no-op. Matched as a SUBSTRING — ``_page`` rewrites static URLs
    to ``?v=<version>``, so an equality match on the bare path would silently pass at zero."""
    for route, page in pages.items():
        assert page.count("/static/panelkit.js") == 1, route
        # and the include is real markup, not a mention inside a comment or a JSON blob. The src
        # is the cache-busted form ``/static/panelkit.js?v=<version>`` — matched as a pattern, so
        # a version bump does not turn this pin into a false failure.
        tags = re.findall(r'<script src="/static/panelkit\.js\?v=[^"]+"></script>', page)
        assert len(tags) == 1, (route, tags)


def test_panelkit_is_absent_where_no_control_is_rendered(client: TestClient) -> None:
    """/driving-path has two branches that build NO tier panel: no target at all, and a target no
    loaded version carries. Shipping the driver for controls that do not exist is a dead promise
    (and the conditional is on the RENDERED html, not on ``target is not None`` — this is the
    assertion that keeps it that way)."""
    for route in ("/driving-path", "/driving-path?target=999999"):
        page = client.get(route).text
        assert "/static/panelkit.js" not in page, route
        for token in ("panel-head", "sf-take", "sf-tools", "data-sf-big", "prov-chip"):
            assert token not in page, (route, token)


# ── (c) every ⤓ destination is live ───────────────────────────────────────────────────────────


def test_every_data_export_on_the_four_routes_is_a_real_workbook(
    client: TestClient, pages: dict[str, str]
) -> None:
    """A ⤓ that 404s / 422s / hands back HTML is worse than no ⤓. Fetched, not assumed."""
    seen = 0
    for route, page in pages.items():
        for url in sorted(set(_EXPORT.findall(page))):
            resp = client.get(html.unescape(url))
            assert resp.status_code == 200, (route, url, resp.status_code)
            assert resp.content[:4] == b"PK\x03\x04", (route, url, resp.content[:8])
            assert "spreadsheetml" in resp.headers.get("content-type", ""), (route, url)
            seen += 1
    # the round ships exactly two DISTINCT destinations: the driving-tiers workbook on the tiers
    # panel and the volatility membership matrix shared by the ten mosaic tiles.
    assert seen == 2, seen


def test_the_tiers_export_carries_the_trace_basis_the_panel_was_solved_with(
    pages: dict[str, str],
) -> None:
    """/driving-path's ⤓ is only honest if the URL pins the SAME target and trace options the
    panel beside it was computed from — every one of them lives in the page's single GET form,
    so a change to any of them is a full navigation and the attribute is regenerated."""
    urls = _EXPORT.findall(pages[DP])
    assert urls == [
        "/export/xlsx/driving-tiers/TP4_DataCenter_v5.xml"
        f"?target={TARGET_UID}&ignore_constraints=0&ignore_leveling=0"
    ], urls


# ── (d) the ⤓ that must NOT exist ─────────────────────────────────────────────────────────────


def test_the_live_column_panels_pin_no_export_url(pages: dict[str, str]) -> None:
    """``driving_tiers.js`` and ``whatif.js`` rebuild ``&cols=<live selection>`` on every render
    (and persist.js remembers the selection across visits), while ``panelkit.js`` follows a STATIC
    ``data-export``. A pinned URL there exports the DEFAULT columns while the operator looks at
    theirs — the round-10 /performance defect. These three panels own their own Excel control."""
    for page, needle in (
        (pages[DP], "All driving-tier activities"),
        (pages[EVO], "What-if: work added to the critical path"),
        (pages[EVO], "What-if: work removed from the critical path"),
    ):
        chunk = _panel_titled(page, needle)
        assert "data-export" not in chunk, needle
        assert "data-sf-excel" not in chunk, needle


def test_path_pins_no_export_url_anywhere(pages: dict[str, str]) -> None:
    """``/export/xlsx/path/{name}`` declares ``target: int = Query(...)`` — REQUIRED — so with no
    session target it answers 422 application/json, and ``st.target_uid`` is legitimately None on
    this page. path.js's own ``updateExportLinks()`` owns a live, correct export bar."""
    assert "data-export" not in pages[PATH]
    assert "data-sf-excel" not in pages[PATH]
    assert "id=pathXlsx" in pages[PATH]  # the page's OWN, live export control still there


def test_the_corridor_and_the_path_header_ship_no_tool_strip(pages: dict[str, str]) -> None:
    """Two deliberate refusals, both structural. The corridor panel already owns Zoom -/+ /
    "View entire project" / Timescale and ``driving_path.js`` never re-fits after a Fit, so ⛶
    would be right before a Fit and wrong after it; the "Driving path:" header holds zero tables
    and zero charts. Both wear a head + chip + take and no controls."""
    for needle in ("Corridor over time", "Driving path:"):
        chunk = _panel_titled(pages[DP], needle)
        assert "panel-head" in chunk and "prov-chip" in chunk and "sf-take" in chunk, needle
        assert "sf-tools" not in chunk, needle
        assert "data-sf-big" not in chunk, needle


# ── (e) the promotion census ──────────────────────────────────────────────────────────────────

#: ``.panel`` per route BEFORE and AFTER the round — measured on both trees (patched, then
#: ``git stash`` to pristine, then re-run) and cross-checked against
#: ``document.querySelectorAll('.panel').length`` in real chromium at 1440x900.
PANEL_CENSUS = {PATH: 5, DP: 13, EVO: 9, VOL: 14}

#: the contract vocabulary each route NEWLY carries — heads / tool strips / ⛶ / takes / chips.
#: All five were ZERO on all four routes before this round (verified by ``curl | grep -c``).
CONTRACT_CENSUS = {
    #        heads, tools, ⛶,  takes, chips
    PATH: (1, 1, 1, 1, 0),
    DP: (5, 3, 3, 5, 5),
    EVO: (4, 2, 2, 4, 4),
    VOL: (2, 10, 10, 12, 12),
}


def test_the_panel_count_is_unchanged_by_the_conversion(pages: dict[str, str]) -> None:
    """The conversion DECORATES panels that were already ``.panel``. If a count moves, the round
    minted a new box — and every new ``.panel`` inherits jarvis's broad
    ``html[data-theme=jarvis] .panel`` rules, i.e. a promotion nobody designed."""
    for route, page in pages.items():
        assert len(_panels(page)) == PANEL_CENSUS[route], route


def test_the_contract_vocabulary_lands_where_it_was_planned(pages: dict[str, str]) -> None:
    """Counted, not eyeballed: a head that silently stopped rendering is exactly the failure this
    file exists to catch, and a ⛶ count that drifts from the tool-strip count means a strip lost
    its button (or grew a second glyph nobody wired)."""
    for route, page in pages.items():
        got = (
            page.count("<div class=panel-head>"),
            page.count("sf-tools"),
            page.count("data-sf-big"),
            page.count("<p class=sf-take"),
            page.count("<span class=prov-chip"),
        )
        assert got == CONTRACT_CENSUS[route], (route, got)
        # every tool strip carries exactly one ⛶, and no strip ever ships ▦ DATA (none of these
        # panels renders an .sf-drawer, so the glyph would reveal nothing)
        assert page.count("sf-tools") == page.count("data-sf-big"), route
        assert "data-sf-data" not in page, route
        assert page.count(SHRINK_LABEL) == 0, route  # the label flips in JS, never server-side


def test_the_headings_the_round_wrapped_still_read_the_same(pages: dict[str, str]) -> None:
    """``_panel_head`` preserves the heading TEXT (the uppercase treatment is CSS). Every existing
    content assertion in test_driving_path_view / test_evolution_view / test_volatility is a plain
    substring on these strings — this pins that they survived the wrap."""
    for route, needles in (
        (PATH, ("Path analysis &mdash; driving / secondary / tertiary to a target",)),
        (
            DP,
            (
                f"Driving tiers to {TARGET_UID}",
                "All driving-tier activities",
                "Driving-slack degradation trend",
                "Driving path:",
                "Corridor over time",
            ),
        ),
        (
            EVO,
            (
                "Critical-Path Evolution",
                "Completed on the path &mdash; version to version",
                "What-if: work added to the critical path",
                "What-if: work removed from the critical path",
            ),
        ),
        (
            VOL,
            (
                "Critical-Path Volatility &mdash; membership churn across versions",
                "Volatility scoreboard",
            ),
        ),
    ):
        for needle in needles:
            assert f"<h2>{needle}" in pages[route], (route, needle)


def test_the_volatility_tile_explainers_are_untouched(pages: dict[str, str]) -> None:
    """The ten ``<h3 class=viz-hint data-sf-hint=…>`` are deliberately NOT routed through
    ``_panel_head`` (it emits an ``<h2>`` and would drop the explainer the tiles are built
    around). The toolbar is injected AFTER the ``</h3>``, inside the existing ``.tile-head``."""
    hints = re.findall(r"<h3 class=viz-hint data-sf-hint=", pages[VOL])
    assert len(hints) == 10, len(hints)
    assert pages[VOL].count("<h3 class=viz-hint") == 10
    assert pages[VOL].count('<span class="tile-actions sf-tools" data-noprint=1>') == 10


# ── (f) this page's own hazard: forms + embedded CSP JSON ──────────────────────────────────────

#: the five GLOBAL chrome forms every page renders, byte-frozen and IDENTICAL on all four routes.
#: (action, md5 of the whole <form>…</form>, length)
GLOBAL_FORMS = [
    ("/session/wipe", "b6865b61ecf8d256992f66a1e5a8fa4f", 162),
    ("/target", "03f588005cb81489f95f0bf540f88414", 638),
    ("/target", "6f7248497e541120c16c6da3b098b605", 599),
    ("/language", "c3b117dc6b8fdabc36bd6043ac60d085", 391),
    ("/target", "3e9a44eae1ed506b4a430e8421100d96", 213),
]

#: each route's PAGE-OWNED forms (everything after the global chrome), byte-frozen. Round 11 is a
#: markup round on panel heads — it must not have moved one character of a control that drives a
#: re-solve. /path and /volatility own no form of their own.
PAGE_FORMS = {
    PATH: [],
    DP: [("/driving-path", "bee3c73c2d22828fe6be36f703313ad6", 1905)],
    EVO: [
        ("/evolution", "12bf0d795832e2c344d1ee0a147b6295", 802),
        ("/evolution", "848cd08e4bab7156a0aa5af217475162", 743),
        ("/evolution", "25dd6f16300d15519223ee9df9738355", 803),
    ],
    VOL: [],
}

#: the embedded CSP JSON payloads the page-owned scripts read, byte-frozen: (md5, length).
#: These are ENGINE OUTPUT rendered into the page — a byte change here is a Law-2 event, not a
#: styling one. Verified identical to the pre-round render.
JSON_BLOBS = {
    DP: {
        "drivingTiersData": ("558abbe2ec446a340ffb710591390389", 624),
        "dpData": ("2bde4ed12211f191120e6cfbe1e1dcd2", 7360),
    },
    EVO: {"whatifAddedData": ("05b0b79b8e18b4e41957d591597d7c08", 702)},
    VOL: {"volData": ("e7ebbdd72e837aae35807d3c33893b27", 2026)},
    PATH: {},
}


def test_every_form_on_the_four_routes_is_byte_frozen(pages: dict[str, str]) -> None:
    for route, page in pages.items():
        forms = _FORM.findall(page)
        expected = GLOBAL_FORMS + PAGE_FORMS[route]
        assert len(forms) == len(expected), (route, len(forms))
        for form, (action, digest, length) in zip(forms, expected, strict=True):
            assert action in form, (route, action)
            assert len(form) == length, (route, action, len(form))
            assert _md5(form) == digest, (route, action)


def test_the_embedded_json_payloads_are_byte_frozen(pages: dict[str, str]) -> None:
    """Requirement 4, shaped to these pages: three of the four carry an engine payload inside a
    ``<script type="application/json">`` (the CSP-safe embed). A markup round may not move a
    single byte of one, and the ``<`` escaping that keeps it from breaking the parser must hold."""
    for route, page in pages.items():
        blobs = dict(_JSON_BLOB.findall(page))
        assert set(blobs) == set(JSON_BLOBS[route]), (route, sorted(blobs))
        for blob_id, (digest, length) in JSON_BLOBS[route].items():
            body = blobs[blob_id]
            assert len(body) == length, (route, blob_id, len(body))
            assert _md5(body) == digest, (route, blob_id)
            # every "<" is escaped to the \\u003c JSON escape, so no payload can close the
            # <script> element early and inject markup (the reason the embed is safe under CSP)
            assert "<" not in body, (route, blob_id)
            json.loads(body)  # and it is still parseable JSON


# ── (g) the axis-caption / page-script freeze (standing requirement 5) ─────────────────────────

#: the seven page-owned chart scripts of the four converted routes. Round 11 touched NO JS on
#: these pages (the only JS edit in the round is panelkit.js, which contains zero axisTitles).
PAGE_SCRIPTS = {
    "path.js": "f04f15d478b9f1181e28f963c8181745",
    "driving_path.js": "027a0d438a9337e408e7fb1997a24d44",
    "driving_tiers.js": "f44f6d35ce10798aafb7ed298dcd7570",
    "path_evolution.js": "f901da4e52b223174f5d3fed6ebbdeda",
    "whatif.js": "b1b911b3cb0c2c87f02aa8e7f4f6d533",
    "volatility.js": "0d38b34ee6d2824125b498b196473a4c",
    "gantt.js": "2a4ccb612899cf141bbf30af3b64286e",
}

#: all 16 ``SFChartFrame.axisTitles(`` call sites, frozen with their ARGUMENT OBJECT — the caption
#: strings live on the lines that FOLLOW the call, so hashing the opening line alone collides nine
#: ways (b1c0ee5f…) and would pass while a caption changed. Recipe (reproducible, and the reason
#: this list is re-derivable rather than a retyped number): for each ``static/*.js`` line
#: containing the call, take that line plus following lines up to and including the first line
#: whose strip starts ``});`` (a one-line call is taken alone), join with ``\n``, md5.
AXIS_CALL_SITES = [
    ("cei.js", 226, "fbf047e07c947cda865470118fcf4bcd"),
    ("curves.js", 385, "be3566a1f0c0feb3319053688753b574"),
    ("drift.js", 133, "d7cd43e8092e02ef82449a52592578d6"),
    ("histogram.js", 243, "5dccee80ef65513a4e5775abc5604271"),
    ("margin.js", 224, "0bead85c7a9f61cbc9175a125bafe2c0"),
    ("performance.js", 472, "db8ae0464072322438172fe30f85fb71"),
    ("resources.js", 243, "251b7d09fffcc7a9f8adaf5f88ab94eb"),
    ("scatter.js", 102, "ab0a7516adc3ba20cfb65107aaf4f244"),
    ("scurve.js", 168, "537fc87d2d19ccc2af0802ebd5dbf58f"),
    ("trend.js", 479, "8bf757af762c9343299f4770bf086f1a"),
    ("trend.js", 583, "82a858e0da47d00e87cb6feffc9dac7d"),
    ("trend.js", 708, "7cff421ad9b3b74b5f8907093822f67f"),
    ("trend.js", 826, "389cb5d55cdb709d1a8e5b86950de32a"),
    ("trend.js", 916, "d85c285c5166c824a0a44425e134b581"),
    ("trend_drill.js", 110, "a1c40e6c60bfb1261bb35bf2ef062930"),
    ("wbs.js", 133, "7b0515f0ff194d2abf03d21133f627b7"),
]


def _axis_call_sites() -> list[tuple[str, int, str]]:
    """Re-derive the 16 frozen call sites from disk (see AXIS_CALL_SITES for the recipe)."""
    out: list[tuple[str, int, str]] = []
    for js in sorted(STATIC.glob("*.js")):
        lines = js.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "SFChartFrame.axisTitles(" not in line:
                continue
            chunk = [line]
            if not line.rstrip().endswith(");"):
                for follow in lines[i + 1 :]:
                    chunk.append(follow)
                    if follow.strip().startswith("});"):
                        break
            out.append((js.name, i + 1, _md5("\n".join(chunk))))
    return out


def test_the_seven_page_owned_scripts_are_byte_frozen() -> None:
    """These pages' charts are drawn by JS this round never opened. If one of them moves, a
    caption / axis / tick can move with it — and the whole point of the round is that only the
    FRAME changed."""
    for name, digest in PAGE_SCRIPTS.items():
        path = STATIC / name
        assert path.exists(), name
        assert hashlib.md5(path.read_bytes()).hexdigest() == digest, name


def test_all_sixteen_axis_title_call_sites_are_frozen() -> None:
    """Standing requirement 5: the axis captions are finished — nothing may move one. 16 is the
    real count (``grep -c 'SFChartFrame.axisTitles(' static/*.js``); chartframe.js's definition
    and export are not call sites."""
    sites = _axis_call_sites()
    assert len(sites) == 16, len(sites)
    assert len({d for _n, _l, d in sites}) == 16, "a hash collided — the freeze is not selective"
    # THE LOAD-BEARING HALF: same files, same caption bytes. A failure here means a caption moved
    # — STOP AND REPORT, do not refresh the constant.
    assert [(n, d) for n, _l, d in sites] == [(n, d) for n, _l, d in AXIS_CALL_SITES], (
        "an axis caption changed"
    )
    # the locator half: a pure line-number shift is benign (an edit ABOVE a call site), but it
    # must be refreshed deliberately rather than drift unnoticed.
    assert [ln for _n, ln, _d in sites] == [ln for _n, ln, _d in AXIS_CALL_SITES], (
        "call sites moved lines; captions are intact — refresh AXIS_CALL_SITES"
    )
    # and the one JS file this round DID edit contains no caption call at all
    assert "axisTitles" not in (STATIC / "panelkit.js").read_text(encoding="utf-8")


# ── (h) the loaded-terms gate, with its control ───────────────────────────────────────────────


def _new_visible_strings(page: str) -> set[str]:
    """Every string round 11 added to a rendered page, HARVESTED FROM THE RENDER: the takeaways,
    the control labels, their hover/aria text, and the provenance chips."""
    out = {_visible(t) for t in _TAKE.findall(page)}
    out |= {_visible(b) for b in _CTRL.findall(page)}
    for tag in _CTRL_TAG.findall(page):
        out |= {_visible(a) for a in _ATTR.findall(tag)}
    out |= {_visible(c) for c in _CHIP.findall(page)}
    return {s for s in out if s}


def test_no_new_string_introduces_an_accusatory_term(pages: dict[str, str]) -> None:
    """ADR-0132: the tool reports what the engine computed and never asserts intent. THE CONTROL
    RUNS FIRST — a gate that answers False to everything would pass this test vacuously."""
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True, "the gate is dead"

    checked = 0
    for route, page in pages.items():
        strings = _new_visible_strings(page)
        assert strings, route
        for text in sorted(strings):
            assert introduces_loaded_terms("", text) is False, (route, text)
            checked += 1
    assert checked >= 40, checked  # 42 at the time of writing — a floor, not a pin


def test_the_control_strip_speaks_only_panelkits_own_glyphs(pages: dict[str, str]) -> None:
    """One vocabulary per glyph. A page that invents "Expand" or "Download" beside ⛶/⤓ is a second
    convention the operator has to learn, and panelkit.js would not drive it."""
    for route, page in pages.items():
        labels = {_visible(b) for b in _CTRL.findall(page)}
        assert labels <= {EXCEL_LABEL, ENLARGE_LABEL}, (route, labels)
        assert ENLARGE_LABEL in labels, route


def test_every_takeaway_figure_is_a_figure_the_page_already_prints(pages: dict[str, str]) -> None:
    """Law 2 at the presentation boundary: a take FRAMES numbers, it never introduces one. Every
    integer a takeaway quotes must appear somewhere else on the same page, OUTSIDE every take."""
    for route, page in pages.items():
        takes = _TAKE.findall(page)
        rest = page
        for t in takes:
            rest = rest.replace(t, " ")
        elsewhere = set(re.findall(r"\d+", _visible(rest)))
        for take in takes:
            for token in re.findall(r"\d+", _visible(take)):
                assert token in elsewhere, (route, token, _visible(take))


# ── (i) the CSS the whole round rests on ──────────────────────────────────────────────────────


def test_the_overlay_rule_keeps_both_structural_exclusions() -> None:
    """``.is-big`` alone is ``grid-column:1/-1`` — inert on a block panel (ADR-0304). The round's
    remedy is a fixed focus overlay, and its two exclusions are structural, not taste:

    * dropping ``:not(.tile)`` converts the whole /performance + /volatility Mission wall from
      the working round-10 grid mechanism into modals;
    * dropping ``:not(:has(.sf-tilebox))`` puts a fixed box inside the fixed box /curves and
      /analysis's scatter panel already own.
    """
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert ".is-big{grid-column:1/-1}" in css  # the round-10 rule, kept byte-unchanged
    rule = re.search(
        r"\.panel\.is-big:not\(\.tile\):not\(:has\(\.sf-tilebox\)\)\{(.*?)\}", css, re.S
    )
    assert rule is not None, "the block-layout overlay rule is gone"
    body = " ".join(rule.group(1).split())
    for decl in ("position:fixed", "inset:3vh 12px", "z-index:220", "overflow:auto"):
        assert decl in body, decl
    # 3vw-class insets are structurally unsafe: daylight has no 236px rail (main is x=0 w=1440),
    # so a vw inset yields a box NARROWER than a daylight panel — ⛶ would shrink the chart.
    assert "3vw" not in body


def test_the_enlarged_panel_is_put_back_in_the_flow_for_print() -> None:
    """Without this, a toggled panel stays ``position:fixed`` under print media (measured
    1416x846 in all four themes) and prints as a floating card over a testimony report."""
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    block = re.search(r"@media print\{(.*?)\n\}", css, re.S)
    assert block is not None
    reset = re.search(r"\.panel\.is-big\{([^}]*)\}", block.group(1))
    assert reset is not None, "the @media print reset for .panel.is-big is gone"
    for decl in (
        "position:static!important",
        "inset:auto!important",
        "overflow:visible!important",
    ):
        assert decl in reset.group(1), decl


def test_panelkit_closes_overlays_without_an_inline_handler() -> None:
    """The single-open invariant and Escape-to-close are the round's two new behaviors. Both must
    be DELEGATED listeners — a strict script-src CSP (ADR-0268) forbids inline handlers — and the
    invariant must key off the COMPUTED position, i.e. ask the browser for base.css's own answer
    rather than re-deriving the selector in JS (one owner for the rule)."""
    js = (STATIC / "panelkit.js").read_text(encoding="utf-8")
    assert 'getComputedStyle(panel).position === "fixed"' in js
    assert 'document.addEventListener("keydown"' in js
    assert 'ev.key !== "Escape"' in js
    assert "closeOverlays(panel)" in js  # single-open, on the open path
    assert "onclick=" not in js and "onkeydown=" not in js


# ── (a) the effect, in real chromium ──────────────────────────────────────────────────────────

CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

#: the probe both browser tests read — the panel's box and the computed properties that say WHICH
#: enlarge layout it took. A class read-back is deliberately not part of the verdict.
_RECT_PROBE = """
([sel, idx]) => {
  const btn = document.querySelectorAll(sel)[idx];
  const panel = btn.closest(".panel");
  const r = panel.getBoundingClientRect();
  const cs = getComputedStyle(panel);
  return {x: Math.round(r.x), y: Math.round(r.y),
          w: Math.round(r.width), h: Math.round(r.height),
          position: cs.position, label: btn.textContent.trim(),
          aria: btn.getAttribute("aria-pressed")};
}
"""


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    if not CHROME.exists():
        pytest.skip(f"bundled chromium not at {CHROME}")
    import uvicorn

    app = create_app(SessionState())
    with TestClient(app) as c:
        _load(c)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def _click_and_measure(page: Any, sel: str, idx: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """One REAL click on the nth control, with ``getBoundingClientRect()`` read either side."""
    page.wait_for_selector("[data-sf-big]", timeout=15000)
    page.wait_for_timeout(1200)  # let the page's own charts settle before the baseline rect
    before = page.evaluate(_RECT_PROBE, [sel, idx])
    button = page.locator(sel).nth(idx)
    button.scroll_into_view_if_needed()
    # the click must actually land ON the button — a sticky header can otherwise eat it and the
    # test would report a false NO-OP (measured on daylight, where the nav is 359px tall)
    assert page.evaluate(
        """([sel, idx]) => {
             const b = document.querySelectorAll(sel)[idx].getBoundingClientRect();
             const el = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
             return !!el && el.hasAttribute("data-sf-big");
        }""",
        [sel, idx],
    ), "the ⛶ control is occluded — the click would not reach it"
    button.click()
    page.wait_for_timeout(400)
    return before, page.evaluate(_RECT_PROBE, [sel, idx])


def test_a_real_click_moves_a_block_layout_panel(served: str) -> None:
    """THE assertion this whole module exists for (ADR-0304). /driving-path's "Driving tiers"
    panel is a plain block child of ``<main>``: pre-round its ⛶ flipped the class and the label
    while the box never moved. The verdict is the RECT, and the round-11 remedy is visible in the
    computed ``position`` — ``static`` before, ``fixed`` after."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + DP, wait_until="load")
        assert (
            page.evaluate(
                "()=>[...document.scripts].filter(s=>s.src.includes('/static/panelkit.js')).length"
            )
            == 1
        )
        before, after = _click_and_measure(page, ".panel[data-export] [data-sf-big]", 0)

        assert before["label"] == ENLARGE_LABEL and before["aria"] == "false"
        assert after["label"] == SHRINK_LABEL and after["aria"] == "true"
        # THE MEASUREMENT — not a class read-back
        assert (before["x"], before["y"], before["w"], before["h"]) != (
            after["x"],
            after["y"],
            after["w"],
            after["h"],
        ), f"the ⛶ moved nothing: {before} -> {after}"
        assert before["position"] != "fixed" and after["position"] == "fixed", (before, after)
        assert after["w"] > before["w"], (before["w"], after["w"])  # wider in every theme

        # Escape closes the focus overlay and restores the box, the label and aria-pressed
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        restored = page.evaluate(_RECT_PROBE, [".panel[data-export] [data-sf-big]", 0])
        assert restored["position"] != "fixed"
        assert restored["label"] == ENLARGE_LABEL and restored["aria"] == "false"
        assert (restored["w"], restored["h"]) == (before["w"], before["h"])
        browser.close()


def test_a_real_click_grows_a_volatility_mosaic_tile_in_the_flow(served: str) -> None:
    """The OTHER enlarge layout, asserted separately so nobody "simplifies" the two into one. A
    ``.mosaic .tile`` grows via ``grid-column:1/-1`` plus the round-10 matched pair
    ``.mosaic .tile.is-big .chart-host{height:74vh}`` — it stays IN THE FLOW. If this tile ever
    reports ``position:fixed`` the overlay rule lost its ``:not(.tile)`` exclusion and the whole
    Mission wall silently became modals."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + VOL, wait_until="load")
        assert page.evaluate("()=>document.querySelectorAll('.mosaic .tile.panel').length") == 10
        before, after = _click_and_measure(page, ".mosaic .tile [data-sf-big]", 0)

        assert after["label"] == SHRINK_LABEL and after["aria"] == "true"
        assert (before["w"], before["h"]) != (after["w"], after["h"]), (before, after)
        assert after["w"] > before["w"], (before["w"], after["w"])
        # in the flow, both sides — the grid path, NOT the block overlay
        assert before["position"] != "fixed" and after["position"] != "fixed", (before, after)
        # the CHART grows with the tile (the round-10 matched pair), not just the frame
        host = page.evaluate(
            """()=>{const h=document.querySelector('.mosaic .tile.is-big .chart-host');
                    const r=h.getBoundingClientRect();
                    return {w: Math.round(r.width), h: Math.round(r.height)};}"""
        )
        assert host["w"] > 1000 and host["h"] > 500, host

        # a second click puts it back exactly where it was
        page.locator(".mosaic .tile [data-sf-big]").nth(0).click()
        page.wait_for_timeout(300)
        restored = page.evaluate(_RECT_PROBE, [".mosaic .tile [data-sf-big]", 0])
        assert (restored["w"], restored["h"]) == (before["w"], before["h"])
        assert restored["label"] == ENLARGE_LABEL
        browser.close()
