"""ADR-0539 (resume): the review's route and page-text findings on the One-Pager pages, pinned.

* ROUTES-1 — the two PowerPoint exports' ASCII ``filename=`` is byte-identical to 0b45eb28's for
  every title 0b45eb28 could export (the ADR-0539 build trimmed underscores off its ends);
* ROUTES-2 — Polaris²'s Word template is headed "POLARIS² — One-Pager list" again;
* ROUTES-3 — the One-Pager reads columns A to E only, so a cover sheet whose only text sits right
  of column E is passed over and the list loads from the next sheet (accepted, recorded here);
* ROUTES-4 — a list with no usable rows AND nothing skipped no longer says "0 row(s) skipped;
  see the list below" over no list, on either page or either Compare slot;
* DOCS-1 / DOCS-3 / DOCS-4 — the page help names as "complete" only values the reader really
  reads as complete (a typed 100% is the NUMBER 1 and is not), states the lone-month exception to
  "one date is a milestone", and states the 200-link cap.

ROUTES-1/2/4 and DOCS-1/3/4 were each seen RED on the ADR-0539 build before the fix; ROUTES-3 (a
record of accepted behaviour) goes RED under 0b45eb28's every-column reader. Each load-bearing pin
was also mutated back RED by name, in a sandbox copy of ``src/``.
"""

from __future__ import annotations

import datetime as dt
import html
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_links import MAX_LINKS
from schedule_forensics.web import onepager_actions
from schedule_forensics.web.app import SessionState, create_app
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2027, 1, 10)
HEADER = ("Swimlane", "Task", "Start", "Finish", "Complete")
ROWS: tuple[tuple[object, ...], ...] = (
    HEADER,
    ("Eng", "PDR", "3/15/2027", "3/15/2027", "Complete"),
    ("Eng", "CDR", "6/1/2027", "7/15/2027", ""),
)


@pytest.fixture
def state() -> SessionState:
    st = SessionState()
    st.onepager_today = TODAY
    return st


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _put(client: TestClient, url: str, name: str, data: bytes, slot: str = "") -> None:
    r = client.post(
        url,
        files={"file": (name, data, "application/octet-stream")},
        data={"slot": slot} if slot else {},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.status_code


def _load_all(client: TestClient, names: tuple[str, str, str]) -> None:
    """The One-Pager list and both Compare slots, each from ``ROWS`` under its own file name."""
    _put(client, "/onepager/upload", names[0], twin_xlsx(ROWS))
    _put(client, "/onepager-compare/upload", names[1], twin_xlsx(ROWS), "prior")
    _put(client, "/onepager-compare/upload", names[2], twin_xlsx(ROWS), "current")


def _text(page: str) -> str:
    """The page as a reader sees it: tags gone, entities decoded, whitespace collapsed."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


def _notices(page: str) -> list[str]:
    """Every notice block's text, in page order."""
    blocks = re.findall(r'<div class="notice[^"]*"[^>]*>(.*?)</div>', page, re.S)
    return [_text(b) for b in blocks]


class _Pct(float):
    """A number in a PERCENT cell format — how Excel stores "100%" typed into a cell: the number
    1 with ``numFmtId`` 9, never the text "100%"."""


def _book(sheets: list[tuple[str, dict[str, object]]]) -> bytes:
    """A minimal .xlsx in Excel's shape: ``[(sheet name, {"A1": value})]``; a ``str`` is an inline
    string, an ``int`` a bare number (an Excel date serial), a :class:`_Pct` a number in the
    percent format (a styles part with ``numFmtId`` 9 is written)."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg = "http://schemas.openxmlformats.org/package/2006/relationships"

    def cell(ref: str, v: object) -> str:
        if isinstance(v, _Pct):
            return f'<c r="{ref}" s="1"><v>{float(v):g}</v></c>'
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v}</v></c>'
        text = str(v).replace("&", "&amp;").replace("<", "&lt;")
        return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/'
            'vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/></Types>'
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{pkg}"><Relationship Id="rId1" '
            f'Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
            + "".join(
                f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>'
                for i, (n, _c) in enumerate(sheets, 1)
            )
            + "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{pkg}">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="{rel}/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + f'<Relationship Id="rIdS" Type="{rel}/styles" Target="styles.xml"/>'
            + "</Relationships>"
        ),
        "xl/styles.xml": (
            f'<styleSheet xmlns="{main}"><cellXfs count="2"><xf numFmtId="0"/>'
            '<xf numFmtId="9" applyNumberFormat="1"/></cellXfs></styleSheet>'
        ),
    }
    for i, (_name, cells) in enumerate(sheets, 1):
        rows: dict[int, list[str]] = {}
        for ref, v in cells.items():
            col = "".join(ch for ch in ref if ch.isalpha())
            rows.setdefault(int(ref[len(col) :]), []).append(cell(ref, v))
        data = "".join(f'<row r="{r}">{"".join(rows[r])}</row>' for r in sorted(rows))
        parts[f"xl/worksheets/sheet{i}.xml"] = (
            f'<worksheet xmlns="{main}"><sheetData>{data}</sheetData></worksheet>'
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in parts.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ── ROUTES-1: the PowerPoint exports' ASCII file name ─────────────────────────────────────────

PAGES = ("onepager", "onepager-compare")

#: MEASURED on 0b45eb28 (the tree before ADR-0539) through these very routes, 2026-09-29: the
#: ``filename=`` it sent for each slide title — the same on both exports. Every ASCII character
#: that is not a letter, a digit, ".", "_" or "-" became "_", and nothing was trimmed. (A fuzz of
#: 816 titles on both trees: every title 0b45eb28 answered, the fixed tree answers identically.)
PRISTINE_FILENAME = {
    "!!!": "___.pptx",
    "_x_": "_x_.pptx",
    "Q3 status!": "Q3_status_.pptx",
    "Program Review FY27": "Program_Review_FY27.pptx",
    "Program Review (FY27)": "Program_Review__FY27_.pptx",
    "FY27 - Rev B.": "FY27_-_Rev_B..pptx",
    "Status: [DRAFT]": "Status___DRAFT_.pptx",
    "__": "__.pptx",
    "-._": "-._.pptx",
    # a character outside ASCII that is no letter or digit: 0b45eb28 sent "_" for it, too
    "→ x →": "__x__.pptx",
}


def _disposition(client: TestClient, page: str, title: str) -> str:
    assert client.post(f"/{page}/title", data={"title": title}).status_code == 200
    r = client.get(f"/export/pptx/{page}")
    assert r.status_code == 200, (page, title, r.status_code)
    cd = r.headers["content-disposition"]
    assert cd.isascii(), cd
    return cd


def _filename(cd: str) -> str:
    m = re.search(r'filename="([^"]*)"', cd)
    assert m, cd
    return m.group(1)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("title", list(PRISTINE_FILENAME))
def test_a_title_0b45eb28_could_export_keeps_its_exact_file_name(
    client: TestClient, page: str, title: str
) -> None:
    """ROUTES-1: the ASCII ``filename=`` is 0b45eb28's, byte for byte — and the real title rides
    as RFC 5987 ``filename*`` (ADR-0539's addition, kept)."""
    _load_all(client, ("Plan.xlsx", "P.xlsx", "C.xlsx"))
    cd = _disposition(client, page, title)
    assert _filename(cd) == PRISTINE_FILENAME[title]
    assert unquote(cd.split("; filename*=UTF-8''", 1)[1]) == f"{title}.pptx"


#: MEASURED on 0b45eb28: with no title typed, the slide is titled by the source file names
#: (``Plan`` / ``P → C``; ``(Draft)`` / ``(Draft) → Plan!``) and the file name follows it.
PRISTINE_DEFAULT = {
    ("Plan.xlsx", "P.xlsx", "C.xlsx"): ("Plan.pptx", "P___C.pptx"),
    ("(Draft).xlsx", "(Draft).xlsx", "Plan!.xlsx"): ("_Draft_.pptx", "_Draft____Plan_.pptx"),
}


@pytest.mark.parametrize("names", list(PRISTINE_DEFAULT))
def test_the_default_title_exports_under_0b45eb28s_exact_file_name(
    client: TestClient, names: tuple[str, str, str]
) -> None:
    """ROUTES-1: most decks are exported under the default title — the arrow in the Compare
    title is outside ASCII but no letter, so it must NOT switch the trimming on."""
    _load_all(client, names)
    got = tuple(_filename(_disposition(client, page, "")) for page in PAGES)
    assert got == PRISTINE_DEFAULT[names]


#: 0b45eb28 answered HTTP 500 for a title holding a letter or digit outside ASCII (measured: the
#: exact set it could not export). Now: 200, the ASCII letters kept, the underscores standing for
#: the rest trimmed from the ends, and the page's fallback name when nothing is left.
NON_ASCII = {
    "Ωmega": ("mega.pptx", "mega.pptx"),
    "日程": ("one-pager.pptx", "one-pager-compare.pptx"),
    "Café": ("Caf.pptx", "Caf.pptx"),
}


@pytest.mark.parametrize("title", list(NON_ASCII))
def test_a_title_with_a_non_ascii_letter_exports_under_a_safe_ascii_name(
    client: TestClient, title: str
) -> None:
    _load_all(client, ("Plan.xlsx", "P.xlsx", "C.xlsx"))
    for page, want in zip(PAGES, NON_ASCII[title], strict=True):
        cd = _disposition(client, page, title)
        assert _filename(cd) == want
        assert unquote(cd.split("; filename*=UTF-8''", 1)[1]) == f"{title}.pptx"


def test_lodestars_shared_attachment_keeps_the_same_names() -> None:
    """LODESTAR's server calls the same ``attachment`` — the rule at the function itself."""
    got = onepager_actions.attachment("Program Review (FY27)", "one-pager", "pptx")
    assert got == (
        'attachment; filename="Program_Review__FY27_.pptx"; '
        "filename*=UTF-8''Program%20Review%20%28FY27%29.pptx"
    )
    assert onepager_actions.attachment("", "one-pager", "pptx").startswith(
        'attachment; filename="one-pager.pptx"'
    )


# ── ROUTES-2: Polaris²'s Word template heading ────────────────────────────────────────────────


def test_polaris_word_template_keeps_0b45eb28s_heading(client: TestClient) -> None:
    """ROUTES-2: the heading 0b45eb28's GET /export/docx/onepager-template carried (measured);
    the Excel template — the one LODESTAR serves too — never carries that heading."""
    r = client.get("/export/docx/onepager-template")
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        body = ET.fromstring(zf.read("word/document.xml"))
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    texts = [t.text or "" for t in body.iter(f"{w}t")]
    assert texts[0] == "POLARIS² — One-Pager list"
    x = client.get("/export/xlsx/onepager-template")
    with zipfile.ZipFile(io.BytesIO(x.content)) as zf:
        named = [n for n in zf.namelist() if re.search(rb"(?i)polaris", zf.read(n))]
    assert named == []


# ── ROUTES-3: a cover sheet whose text is right of column E ───────────────────────────────────

COVER_BOOK = [
    ("Cover", {"G1": "Instructions: the list is on the next sheet"}),
    (
        "List",
        {
            **dict(zip(("A1", "B1", "C1", "D1", "E1"), HEADER, strict=True)),
            **{"A2": "Eng", "B2": "PDR", "C2": 46461, "D2": 46461, "E2": "Complete"},
            **{"A3": "Eng", "B3": "CDR", "C3": 46539, "D3": 46583},
        },
    ),
]


def test_a_cover_sheet_right_of_column_e_is_passed_over(
    client: TestClient, state: SessionState
) -> None:
    """ROUTES-3 (accepted): the One-Pager reads A to E only, so a first sheet whose only text is
    in G1 is EMPTY to it and the list loads from sheet 2 (0b45eb28 picked the cover sheet and
    refused the file). On both pages — the one reader serves both."""
    data = _book(COVER_BOOK)
    _put(client, "/onepager/upload", "Book.xlsx", data)
    doc = state.onepager
    assert doc is not None and doc.sheet == "List"
    assert [it.name for it in doc.items] == ["PDR", "CDR"] and doc.problems == ()
    assert "Loaded 2 item(s) from Book.xlsx." in _notices(client.get("/onepager").text)
    _put(client, "/onepager-compare/upload", "Book.xlsx", data, "prior")
    prior = state.onepager_prior
    assert prior is not None and prior.sheet == "List" and len(prior.items) == 2


# ── ROUTES-4: no usable rows and nothing skipped ──────────────────────────────────────────────

#: Every shape that yields no item AND no skipped row: the header alone (either layout), a
#: header over rows holding only a status, and status-only rows with no header at all.
EMPTY_LISTS = {
    "header only": (HEADER,),
    "older header only": (("Swimlane", "Task", "Date", "Status"),),
    "status-only rows": (HEADER, ("", "", "", "", "Complete")),
    "status-only rows, no header": (("", "", "", "", "Complete"), ("", "", "", "", "Done")),
}
NO_ROWS = "the sheet has no task or milestone rows."


@pytest.mark.parametrize("case", list(EMPTY_LISTS))
@pytest.mark.parametrize("where", ["onepager", "prior", "current"])
def test_a_list_with_no_rows_says_so_and_points_at_no_list(
    client: TestClient, case: str, where: str
) -> None:
    """ROUTES-4: the message is TRUE — no "0 row(s) skipped", no "see the list below" when no
    list is drawn — and still a failure (role=alert)."""
    data = twin_xlsx(EMPTY_LISTS[case])
    if where == "onepager":
        _put(client, "/onepager/upload", "H.xlsx", data)
        page, slot = client.get("/onepager").text, ""
    else:
        _put(client, "/onepager-compare/upload", "H.xlsx", data, where)
        page, slot = client.get("/onepager-compare").text, f" ({where.upper()})"
    assert f"No usable rows in H.xlsx{slot} — {NO_ROWS}" in _notices(page)
    assert f"role=alert>No usable rows in H.xlsx{slot} — {NO_ROWS}</div>" in page
    assert "see the list below" not in page and "0 row(s) skipped" not in page


@pytest.mark.parametrize("where", ["onepager", "prior"])
def test_a_list_whose_rows_were_all_skipped_still_points_at_the_list(
    client: TestClient, where: str
) -> None:
    """ROUTES-4's other half: when rows WERE skipped, the list of them is drawn below the
    message, so "see the list below" stays — and it is there."""
    data = twin_xlsx((HEADER, ("Eng", "PDR", "soon", "", "")))
    if where == "onepager":
        _put(client, "/onepager/upload", "B.xlsx", data)
        page, slot = client.get("/onepager").text, ""
    else:
        _put(client, "/onepager-compare/upload", "B.xlsx", data, where)
        page, slot = client.get("/onepager-compare").text, f" ({where.upper()})"
    notices = _notices(page)
    msg = f"No usable rows in B.xlsx{slot} — 1 row(s) skipped; see the list below."
    assert msg in notices
    below = notices[notices.index(msg) + 1 :]
    assert any("row 2 (Eng · PDR): unreadable start date “soon” — skipped" in n for n in below)


# ── DOCS-1 / DOCS-3 / DOCS-4: the page help ───────────────────────────────────────────────────


def _help_pages(client: TestClient) -> dict[str, str]:
    return {p: _text(client.get(f"/{p}").text) for p in PAGES}


def _claimed_complete(text: str) -> list[str]:
    """Every value the help NAMES as drawing a check, as the help words it: the list between
    "status word" and "draws a check" / "marks the item complete". An aside between dashes is
    no value; "a check mark (✓ ✔)" names the characters in its brackets."""
    found = re.findall(r"status word[:.](.*?)(?:draws a check|marks the item complete)", text)
    assert found, "the help names no status values at all"
    values: list[str] = []
    for seg in found:
        seg = re.sub(r"—[^—]*—", ",", seg)
        seg = re.sub(r"a check mark \(([^)]*)\)", lambda m: ", ".join(m.group(1).split()), seg)
        values += [v.strip() for v in re.split(r",|\bor\b|\(|\)", seg) if v.strip()]
    return values


def test_every_value_the_help_names_as_complete_is_read_as_complete(client: TestClient) -> None:
    """DOCS-1: each value the rendered help (both pages) names as drawing a check, typed as TEXT
    in column E, goes through the real upload reader — and every one reads complete. A number is
    named only as TEXT: the help never claims a bare 100% draws a check."""
    for page, text in _help_pages(client).items():
        claimed = _claimed_complete(text)
        bare = [v for v in claimed if v[:1].isdigit() and not v.endswith(" stored as text")]
        assert bare == [], f"{page}: names a bare number as complete: {bare}"
        values = [v.removesuffix(" stored as text") for v in claimed]
        assert "100%" in values and "✓" in values, (page, values)
        rows = [HEADER] + [("L", f"v{i}", 46400 + i, 46400 + i, v) for i, v in enumerate(values)]
        doc = onepager_actions.read_list(twin_xlsx(rows), "v.xlsx", max_bytes=1 << 20)
        assert isinstance(doc, OnePagerDoc) and doc.status_column == "E"
        got = {values[int(it.name[1:])]: it.complete for it in doc.items}
        assert got == dict.fromkeys(values, True), f"{page}: {got}"


def test_the_help_says_a_typed_100_percent_is_a_number_the_page_names(
    client: TestClient, state: SessionState
) -> None:
    """DOCS-1: the help says it, and it is so — "100%" typed in Excel is stored as the number 1
    in a percent format; the reader draws no check and the page names that cell, on both pages."""
    for page, text in _help_pages(client).items():
        assert "Excel keeps a typed 100% as the number 1" in text, page
    rows = {**dict(zip(("A1", "B1", "C1", "D1", "E1"), HEADER, strict=True))}
    rows |= {"A2": "Eng", "B2": "PDR", "C2": 46461, "D2": 46461, "E2": _Pct(1)}
    data = _book([("Sheet1", rows)])
    _put(client, "/onepager/upload", "Pct.xlsx", data)
    assert state.onepager is not None and [it.complete for it in state.onepager.items] == [False]
    named = "column E “1” (row 2): not a status read as complete — drawn as not complete"
    assert named in _text(client.get("/onepager").text)
    _put(client, "/onepager-compare/upload", "Pct.xlsx", data, "prior")
    _put(client, "/onepager-compare/upload", "Pct.xlsx", data, "current")
    assert named in _text(client.get("/onepager-compare").text)


def test_the_help_states_the_lone_month_exception_and_it_is_true(
    client: TestClient, state: SessionState
) -> None:
    """DOCS-3: one date is a milestone — EXCEPT a lone month, drawn across the whole month. The
    help states it on both pages; the reader does it in BOTH layouts (the help claims no note:
    the current layout notes it, the older one does not)."""
    for page, text in _help_pages(client).items():
        assert "or that has only one date — is a milestone" in text, page
        assert "a lone month such as Jan 2027 is drawn across the whole month;" in text, page
        assert "has only one of them" not in text, page
    want = {"Day": ("2027-01-15", "2027-01-15", True), "Month": ("2027-01-01", "2027-01-31", False)}
    for head, pad in ((HEADER, ("", "")), (("Swimlane", "Task", "Date", "Status"), ("",))):
        rows = (head, ("L", "Day", "1/15/2027", *pad), ("L", "Month", "Jan 2027", *pad))
        _put(client, "/onepager/upload", "M.xlsx", twin_xlsx(rows))
        doc = state.onepager
        assert doc is not None
        got = {i.name: (i.start.isoformat(), i.finish.isoformat(), i.milestone) for i in doc.items}
        assert got == want, head
    # the current layout also SAYS so, beside the slide
    _put(client, "/onepager/upload", "M.xlsx", twin_xlsx((HEADER, ("L", "Month", "Jan 2027"))))
    assert "“Jan 2027” names a month, not a day — drawn across the whole month" in _text(
        client.get("/onepager").text
    )


def test_the_links_help_states_the_cap(client: TestClient) -> None:
    """DOCS-4: "as many pairs as you need" has a cap — the one ``check_link`` enforces."""
    _load_all(client, ("Plan.xlsx", "P.xlsx", "C.xlsx"))
    for page in PAGES:
        text = _text(client.get(f"/{page}").text)
        assert f"Add as many pairs as you need (up to {MAX_LINKS})" in text, page
    assert MAX_LINKS == 200
