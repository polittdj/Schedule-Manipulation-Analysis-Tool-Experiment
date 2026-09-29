"""Executable reproducers for the AUDIT-2026-09-23 findings in the WEB lane (A0923-WEB-001..002).

Campaign: AUDIT-2026-09-23, a read-only audit of base 8c71c639 (v1.0.289). AUDIT + PLAN ONLY:
the audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Everything runs in-process through FastAPI's TestClient (no server, no browser): the browser half
of A0923-WEB-001 was measured in Chromium by the verifier and is pinned here on the SERVED
``home.js``. Inputs are built inline; no fixture file is added and nothing is CUI; an autouse
fixture refuses every non-loopback connect and name lookup. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_web.py -rxX``.
"""

from __future__ import annotations

import asyncio
import json
import re
import socket
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


_PLAN = json.dumps(
    {
        "name": "Folder plan",
        "project_start": "2026-01-05T08:00:00",
        "calendars": [{"name": "Standard", "hours_per_day": 8}],
        "tasks": [
            {"unique_id": 1, "name": "Design", "duration_minutes": 2400},
            {"unique_id": 2, "name": "Build", "duration_minutes": 4800},
        ],
        "relationships": [{"predecessor_id": 1, "successor_id": 2, "type": "FS"}],
    }
).encode("utf-8")


def _folder_parts(others: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    """One schedule plus ``others`` non-schedule files — a picked folder, as home.js posts it."""
    parts = [("files", ("plan.json", _PLAN, "application/json"))]
    parts += [
        ("files", (f"notes-{i:04d}.pdf", b"%PDF-1.4 not a schedule", "application/pdf"))
        for i in range(others)
    ]
    return parts


# --------------------------------------------------------------------------------------------
# A0923-WEB-001 (T4): a >1000-file upload is refused 400 and home.js navigates away silently
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-WEB-001: POST /upload with more than 1000 file parts answers 400 'Too many "
    "files. Maximum number of files is 1000.' (Starlette's multipart default) and home.js never "
    "reads resp.ok before navigating to '/', so the refused ingest is silent",
)
def test_a0923_web_001_a_large_folder_upload_loads_or_fails_loudly() -> None:
    """Claim: at 8c71c639 POST /upload with 1001 file parts (here one schedule plus 1000
    non-schedule files, a picked folder) answers 400 {"detail": "Too many files. Maximum number of
    files is 1000."} with nothing loaded, and home.js's upload() navigates to '/' without reading
    the response status, so the operator sees the unchanged dashboard and no message (Chromium:
    pick and drop, verifier); a 1000-part batch loads.

    Authority: docs/adr/0225-grouped-ingestion-and-portfolio.md:21-24 "Operator rules
    (confirmed): loose files group by document Title; **a folder — any nesting depth — is exactly
    one Project named by its top folder**, every schedule beneath it a version (sub-folders are
    just filing and are ignored); **no file-count cap**." and README.md:69-70 "the dashboard
    tells you exactly what loaded and what failed (no silent failures)."

    Tier: T4 (not LAW-1). Correct = the batch loads (no cap), or the refusal reaches the operator
    (home.js reads the status before it navigates); the browser half is pinned on the served JS.
    """
    control_state = SessionState()
    control = TestClient(create_app(control_state))
    ok = control.post(
        "/upload", files=_folder_parts(999), data={"file_meta": "[]"}, headers={"X-SF-Ajax": "1"}
    )
    if ok.status_code != 200 or len(control_state.schedules) != 1:
        pytest.fail(f"precondition: a 1000-part folder batch loads its schedule ({ok.status_code})")
    state = SessionState()
    client = TestClient(create_app(state))
    resp = client.post(
        "/upload", files=_folder_parts(1000), data={"file_meta": "[]"}, headers={"X-SF-Ajax": "1"}
    )
    js = client.get("/static/home.js").text
    start = js.find("fetch('/upload'")
    navigate = js.find("window.location", start)
    if start < 0 or navigate < 0:
        pytest.fail("precondition: the served home.js POSTs /upload by fetch, then navigates")
    reads_status = re.search(r"\bresp\.(?:ok|status)\b", js[start:navigate]) is not None
    loaded = resp.status_code == 200 and len(state.schedules) == 1
    problems = []
    if not loaded and not reads_status:
        problems.append(
            f"/upload answered {resp.status_code} {resp.text[:80]!r} with "
            f"{len(state.schedules)} loaded, and home.js navigates without reading resp.ok/status"
        )
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-WEB-002 (T4): a malformed AI endpoint 500s two routes and makes the launch fail
# --------------------------------------------------------------------------------------------
_DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
_MALFORMED = ("http://[", "http://a\uff20127.0.0.1:11434", "http://[::1:11434")


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="A0923-WEB-002: net_guard.is_local_http_endpoint lets urlparse's ValueError escape "
    "('Invalid IPv6 URL', NFKC netloc), so a settings file carrying 'http://[' makes create_app() "
    "raise, and POST /settings and GET /api/ai/models answer 500",
)
def test_a0923_web_002_a_malformed_endpoint_falls_back_instead_of_raising(
    tmp_path: Path,
) -> None:
    """Claim: at 8c71c639 an endpoint urllib.parse cannot split ('http://[', a fullwidth-@
    netloc, the typo 'http://[::1:11434') makes net_guard.is_local_http_endpoint RAISE ValueError
    instead of returning False: a hand-edited ai-settings.json carrying it makes create_app() (the
    desktop-launch path) raise, and POST /settings and GET /api/ai/models?kind=ollama answer 500.

    Authority: docs/adr/0404-persistent-ai-settings.md:37-42 "3. **Loading is a trust boundary.**
    The file is operator-editable state, so loading re-applies the POST sanitizers: ...
    non-loopback local endpoints fall back to defaults, ... Missing or corrupt files yield pure
    defaults — a launch never fails on settings."

    Tier: T4 (not LAW-1: every raising path fails closed). Sibling not asserted: POST /language
    500s on a malformed Referer (web/app.py:7941).
    """
    settings = tmp_path / "SF_SETTINGS_DIR" / "ai-settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    for bad in _MALFORMED:
        settings.write_text(
            json.dumps({"schema": 1, "backend": "ollama", "endpoint": bad}), encoding="utf-8"
        )
        endpoint = create_app().state.session.ai_config.endpoint  # the launch path
        if endpoint != _DEFAULT_ENDPOINT:
            problems.append(f"launch with {bad!r} kept endpoint {endpoint!r}")
    client = TestClient(create_app(SessionState()))
    for bad in _MALFORMED:
        saved = client.post("/settings", data={"endpoint": bad}, follow_redirects=False)
        if saved.status_code != 303:
            problems.append(f"POST /settings endpoint={bad!r} -> {saved.status_code}")
        probe = client.get("/api/ai/models", params={"kind": "ollama", "endpoint": bad})
        if probe.status_code != 200 or probe.json().get("reachable") is not False:
            problems.append(f"GET /api/ai/models endpoint={bad!r} -> {probe.status_code}")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-WEB-004 (T4): 'Save .json' answers 500 when the file name carries a code point > U+00FF
# --------------------------------------------------------------------------------------------
_WEB_004_MSPDI = b"""<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>Bridge</Name>
<StartDate>2026-03-02T08:00:00</StartDate>
<Tasks>
 <Task><UID>1</UID><ID>1</ID><Name>Design</Name><Duration>PT40H0M0S</Duration></Task>
 <Task><UID>2</UID><ID>2</ID><Name>Build</Name><Duration>PT80H0M0S</Duration>
  <PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>
</Tasks></Project>"""

# File names as Windows Explorer, Word's autocorrect or a non-English desktop write them; every
# one carries a code point above U+00FF, outside ISO-8859-1 (the glyphs on purpose: they ARE the
# input; ruff RUF001 reads the two Latin-lookalikes as typos).
_WEB_004_NAMES = (
    "Bridge – Rev 3.xml",  # noqa: RUF001 — U+2013 EN DASH
    "Owner’s Update 3.xml",  # noqa: RUF001 — U+2019 RIGHT SINGLE QUOTATION MARK (Word / Windows)
    "Plan — v2.xml",  # U+2014 EM DASH
    "График.xml",  # Cyrillic 'Grafik'
    "计划.xml",  # CJK 'jihua' (plan)
)
# The boundary is ISO-8859-1, not ASCII: both of these answer 200 on the audited tree (verifier).
_WEB_004_CONTROLS = ("Plain Plan.xml", "Café Plan.xml")


def _web_004_raw_get(app: Any, href: str) -> tuple[int | None, bytes | None, bytes, str | None]:
    """GET ``href`` by calling the ASGI app directly: the raw ``http.response.start`` status and
    Content-Disposition bytes, the body, and the exception the app re-raised (or None).

    The TestClient cannot measure the control: its httpx transport decodes response headers as
    UTF-8, so the server's valid ISO-8859-1 ``filename="Caf\\xe9 Plan.json"`` surfaces as a 500 of
    the client's own making (the finder's and the verifier's instrument note). This reads the
    status Starlette actually sends, with no client decoding in the way.
    """
    sent: list[dict[str, Any]] = []
    raw_path, _, query = href.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": unquote(raw_path),
        "raw_path": raw_path.encode("ascii"),
        "query_string": query.encode("ascii"),
        "root_path": "",
        "headers": [(b"host", b"127.0.0.1")],
        "client": ("127.0.0.1", 1),
        "server": ("127.0.0.1", 80),
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def call() -> str | None:
        try:
            await app(scope, receive, send)
        except Exception as exc:  # ServerErrorMiddleware re-raises after it has sent its 500
            return f"{type(exc).__name__}: {exc}"
        return None

    raised = asyncio.run(call())
    start = next((m for m in sent if m["type"] == "http.response.start"), None)
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    disposition = dict(start["headers"]).get(b"content-disposition") if start else None
    return (start["status"] if start else None), disposition, body, raised


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-WEB-004: GET /download/{key}.json puts the raw key in Content-Disposition "
    "(_safe_filename strips only quotes, backslash and CRLF; Starlette encodes header values as "
    "latin-1), so a schedule whose file name carries any code point above U+00FF -- an en dash, "
    "a Word apostrophe, an em dash, Cyrillic, CJK -- loads and gets a 'Save .json' link that "
    "answers 500 UnicodeEncodeError",
)
def test_a0923_web_004_a_save_json_link_answers_for_a_file_name_outside_latin_1() -> None:
    """Claim (as verified, P2 -- the boundary is ISO-8859-1, not ASCII): at 0b45eb28 a schedule
    uploaded under a file name carrying any code point above U+00FF -- 'Bridge <U+2013> Rev
    3.xml' (en dash), 'Owner<U+2019>s Update 3.xml' (the Word / Windows apostrophe), 'Plan
    <U+2014> v2.xml' (em dash), a Cyrillic name, a CJK name -- loads (POST /upload 303) and gets
    a 'Save .json' link on the dashboard, but GET /download/{key}.json answers 500 'Internal
    Server Error': Starlette raises UnicodeEncodeError building the Content-Disposition header
    (starlette/responses.py:61 ``v.encode("latin-1")``) from the key that download_json
    (web/app.py:1972-1977) passes through _safe_filename (web/app.py:8125-8127), which strips
    only quotes, backslash and CRLF. Measured in-process by raw ASGI and over the wire (uvicorn,
    verifier). An ASCII name and an ISO-8859-1 name ('Café Plan.xml') answer 200 with the
    re-openable JSON.

    Authority: docs/USER-GUIDE.md:75-76 "with **Open report**, **Card**, and **Save .json**
    (exports the normalised schedule as a / re-openable `.json`, calendar and holidays
    included)." and README.md:70 "Each schedule lists **Open report** and **Save .json**."; the
    link is rendered for EVERY loaded key (web/app.py:1811).

    Tier: T4 (not LAW-1: a documented control fails as an unnamed 500; no figure is wrong).
    Correct = the dashboard's own 'Save .json' href answers 200 for every loaded schedule, with a
    body that re-opens model-equal to the upload (source_file aside).
    """
    reference = parse_mspdi_text(_WEB_004_MSPDI.decode("utf-8")).model_dump(exclude={"source_file"})
    problems: list[str] = []
    for name in (*_WEB_004_CONTROLS, *_WEB_004_NAMES):
        state = SessionState()
        client = TestClient(create_app(state), raise_server_exceptions=False)
        up = client.post(
            "/upload", files={"files": (name, _WEB_004_MSPDI, "text/xml")}, follow_redirects=False
        )
        hrefs = re.findall(r'href="(/download/[^"]+\.json)"', client.get("/").text)
        if up.status_code != 303 or len(state.schedules) != 1 or len(hrefs) != 1:
            pytest.fail(
                f"precondition: {name!r} loads and the dashboard renders one 'Save .json' link "
                f"(upload {up.status_code}, {len(state.schedules)} loaded, hrefs {hrefs})"
            )
        status, _disposition, body, raised = _web_004_raw_get(client.app, hrefs[0])
        if status == 200:
            reopens = parse_json_text(body.decode("utf-8")).model_dump(exclude={"source_file"})
            outcome = "" if reopens == reference else "200, but the body does not re-open equal"
        else:
            outcome = f"{status} {raised or body[:40]!r}"
        if name in _WEB_004_CONTROLS:
            if outcome:
                pytest.fail(
                    f"precondition (control): {name!r} GET {hrefs[0]} -> {outcome}: an ASCII / "
                    "ISO-8859-1 name no longer saves and re-opens (the boundary moved)"
                )
            continue
        if outcome:
            problems.append(f"{name!r}: GET {hrefs[0]} -> {outcome}")
    assert problems == [], (
        "the dashboard's own 'Save .json' link fails for a file name outside ISO-8859-1 "
        "(USER-GUIDE.md:75-76 / README.md:70 promise it for every loaded schedule):\n"
        + "\n".join(problems)
    )


# --- A0923-WEB-003 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_web.py and adds NOTHING at module
# level:
#   imports    re, pytest, Path (pathlib), TestClient (fastapi.testclient),
#              SessionState / create_app (web.app)
#   fixture    the module-level autouse _air_gapped
# The two engine names the preconditions need (parse_mspdi_text; compute_cpm / CPMError) are
# imported inside their helpers, so the fragment appends below the existing tests without an E402
# and the module header stays as it is.
# Input: the committed, non-CUI goldens evm/EVM1.mspdi.xml and evm/EVM2.mspdi.xml (plain XML) with
# one link inserted in memory, and an inline summary-only MSPDI. No new fixture file.

_WEB_003_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "evm"
#: the resolver's notice (web/app.py:2665-2672): its class, the 'Skipped (...):' prefix and the
#: names it lists; the parenthetical is not pinned (its wording moved at dee28ab3, ADR-0467)
_WEB_003_NOTICE = re.compile(r'<div class="notice err">Skipped \([^)]*\): ([^<]*)</div>')
#: the six sibling HTML routes that resolve through _solvable_versions and render that notice
_WEB_003_SIBLINGS = ("/trend", "/volatility", "/performance", "/forecast", "/brief", "/briefing")
#: ADR-0467 row CPM-04's own case: a FILE with no schedulable activity
_WEB_003_SUMMARY_ONLY = (
    '<?xml version="1.0" encoding="UTF-8"?><Project xmlns="http://schemas.microsoft.com/project">'
    "<Name>SummaryOnly</Name><StartDate>2012-08-14T08:00:00</StartDate>"
    "<StatusDate>2012-09-20T17:00:00</StatusDate><Tasks>"
    "<Task><UID>0</UID><ID>0</ID><Name>SummaryOnly</Name><Summary>1</Summary>"
    "<OutlineLevel>0</OutlineLevel></Task>"
    "<Task><UID>1</UID><ID>1</ID><Name>Phase</Name><Summary>1</Summary>"
    "<OutlineLevel>1</OutlineLevel><Start>2012-08-14T08:00:00</Start>"
    "<Finish>2012-09-20T17:00:00</Finish></Task></Tasks></Project>"
)


def _web_003_cyclic(name: str) -> str:
    """The committed golden ``evm/<name>.mspdi.xml`` with one extra FS link 23 -> 18 (UID 18 is an
    activity that already reaches 23 through 19..22), inserted before UID 18's ``</Task>``."""
    raw = (_WEB_003_GOLDEN / f"{name}.mspdi.xml").read_text(encoding="utf-8-sig")
    task = re.search(r"(<Task>\s*<UID>18</UID>.*?)(</Task>)", raw, re.S)
    if task is None or "<Summary>0</Summary>" not in task.group(1):
        pytest.fail(f"precondition: {name} no longer carries an activity <Task> with UID 18")
    link = (
        "<PredecessorLink><PredecessorUID>23</PredecessorUID><Type>1</Type>"
        "<CrossProject>0</CrossProject><LinkLag>0</LinkLag><LagFormat>7</LagFormat>"
        "</PredecessorLink>"
    )
    return raw.replace(task.group(0), task.group(1) + link + task.group(2), 1)


def _web_003_cpm_refusal(text: str) -> str | None:
    """What the CPM says when it refuses the MSPDI ``text`` (None when the network solves)."""
    from schedule_forensics.engine.cpm import CPMError, compute_cpm
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    try:
        compute_cpm(parse_mspdi_text(text))
    except CPMError as exc:
        return str(exc)
    return None


def _web_003_has_no_activity(text: str) -> bool:
    """True when every task of the MSPDI ``text`` is a summary (nothing schedulable)."""
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    return all(t.is_summary for t in parse_mspdi_text(text).tasks)


def _web_003_client(files: dict[str, str]) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name, text in files.items():
        up = client.post("/upload", files={"files": (name, text.encode("utf-8"), "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    return client


def _web_003_named(html: str) -> str:
    """The names the resolver's skipped notice lists on a page ('' when there is no notice)."""
    notice = _WEB_003_NOTICE.search(html)
    return notice.group(1) if notice else ""


# --------------------------------------------------------------------------------------------
# A0923-WEB-003 (T4): /evm never discloses a refused version -- alone, or a newer one beside an
# older solvable one -- while its chrome lists the refused file as a data source
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-WEB-003: GET /evm never discloses a refused version -- web/app.py:3372 computes the "
        "resolver's skipped list and discards it, and _evm_body resolves through _latest_solvable "
        "(web/evm.py:234), which returns no skipped list -- so a refused file alone (EVM1 plus a "
        "23 -> 18 back-link; a summary-only file) gets 'Load an analyzable schedule ...' and a "
        "refused NEWER version beside an older solvable one (EVM1 + EVM2_cycle) silently shifts "
        "the page to EVM1's figures, with no 'Skipped (...): <name>' notice in either case, while "
        "the six sibling pages print one and the chrome lists the refused file as a data source"
    ),
)
def test_a0923_web_003_evm_names_a_refused_version_instead_of_hiding_it() -> None:
    """A0923-WEB-003 (finder id F-FAMB-006) · WEB · T4 (latent on the committed corpus, live on
    any refused upload).

    Claim (as VERIFIED -- verifier P2's narrowing and broadening adopted): at 0b45eb28 ``GET
    /evm`` never DISCLOSES a refused version -- no "Skipped (...)" notice, no reason -- in either
    of two cases. (1) The loaded population is one refused file: the committed EVM1 golden plus
    one back-link 23 -> 18 (``compute_cpm`` raises ``CPMError: schedule logic contains a cycle``),
    or a summary-only file (ADR-0467's own case); the body says "Load an analyzable schedule to
    see its earned-value metrics ..." (truthful wording, no file name). (2) An older solvable EVM1
    sits beside a NEWER refused copy of EVM2, and the page silently falls back to EVM1's figures
    (its chips read "SOURCE: EVM1.mspdi.xml · DD 2012-09-01", so the figures are attributed, not
    mislabelled). In both cases the page chrome lists the refused file as a data source ("All
    data on this page is computed from: EVM1_cycle.mspdi.xml"; "computed from the 2 loaded files
    (oldest first): EVM1.mspdi.xml -> EVM2_cycle.mspdi.xml") -- false for the refused file --
    while the six sibling pages on the same session (/trend, /volatility, /performance,
    /forecast, /brief, /briefing) print "Skipped (network cannot be solved, or holds no
    schedulable activity -- see each report for the reason): <name>". Mechanism:
    ``web/app.py:3372`` ``schedules, _cpms, _skipped = _solvable_versions()`` -- the route
    computes the skipped list and never references it again; ``_evm_body`` (``web/evm.py:234``)
    resolves through ``_latest_solvable`` (``web/components.py:344-361``), which returns only the
    chosen version and no skipped list, so none of its callers can name a refused file.

    Authority: A2 -- ``docs/adr/0467-wp6b-the-ledger-tail-verified-by-execution-eleven-fixed-
    red-first-six-refuted.md:23`` (row CPM-04): "every multi-version resolver (...) skips a
    FILE with no schedulable activity by name (the skipped notice names it)" -- ``_latest_solvable``
    is one of the resolvers that line names; the notice, ``src/schedule_forensics/web/app.py:
    2670-2671``: "Skipped (network cannot be solved, or holds no schedulable activity — see each
    report for the reason): {names}"; the page's own chrome, ``web/chrome.py:696`` and ``:699``.
    (Read at 0b45eb28, 2026-09-29.) Deliberate-decision screen: no ADR exempts /evm; not HELD;
    not a duplicate of A0923-CPM-025 (/driving-path's empty-population early return, whose census
    names /evm as a weaker sibling it does not assert; CPM-025's sketch does not reach this
    route) -- the lead ruled a new class (LEAD-VALIDATION, session 7).

    Control (precondition): on the same sessions the six siblings name the refused file, and with
    EVM1 beside the UNMODIFIED EVM2 /evm carries no notice and shows EVM2 -- nothing to skip, so
    the check does not fire spuriously. Census (verifier): ``_latest_solvable`` has 7 callers and
    returns no skipped list; the committed corpus solves 44/44, so this is latent on committed
    files and live on any refused upload.
    """
    evm1 = (_WEB_003_GOLDEN / "EVM1.mspdi.xml").read_text(encoding="utf-8-sig")
    evm2 = (_WEB_003_GOLDEN / "EVM2.mspdi.xml").read_text(encoding="utf-8-sig")
    evm1_cycle, evm2_cycle = _web_003_cyclic("EVM1"), _web_003_cyclic("EVM2")
    for name, text in (("EVM1_cycle", evm1_cycle), ("EVM2_cycle", evm2_cycle)):
        reason = _web_003_cpm_refusal(text)
        if reason is None or "cycle" not in reason:
            pytest.fail(f"precondition: the CPM no longer refuses {name} as a cycle ({reason!r})")
    if _web_003_cpm_refusal(evm1) is not None or _web_003_cpm_refusal(evm2) is not None:
        pytest.fail("precondition: the committed EVM1 / EVM2 goldens no longer solve")
    if not _web_003_has_no_activity(_WEB_003_SUMMARY_ONLY):
        pytest.fail("precondition: the summary-only file now carries a schedulable activity")

    # -- control: EVM1 beside a solvable EVM2 -> the newest version, nothing to skip -----------
    both = _web_003_client({"EVM1.mspdi.xml": evm1, "EVM2.mspdi.xml": evm2}).get("/evm").text
    if _web_003_named(both) or "SOURCE: EVM2.mspdi.xml" not in both:
        pytest.fail("precondition (control): beside a solvable EVM2, /evm no longer shows EVM2")

    wrong: dict[str, dict[str, object]] = {}
    cases = (
        (
            "EVM1_cycle",
            {"EVM1_cycle.mspdi.xml": evm1_cycle},
            "All data on this page is computed from: <b>EVM1_cycle.mspdi.xml</b>",
        ),
        (
            "SummaryOnly",
            {"SummaryOnly.mspdi.xml": _WEB_003_SUMMARY_ONLY},
            "All data on this page is computed from: <b>SummaryOnly.mspdi.xml</b>",
        ),
        (
            "EVM2_cycle",
            {"EVM1.mspdi.xml": evm1, "EVM2_cycle.mspdi.xml": evm2_cycle},
            "computed from the 2 loaded files (oldest first): <b>EVM1.mspdi.xml</b> &rarr; "
            "<b>EVM2_cycle.mspdi.xml</b>",
        ),
    )
    for key, files, source_line in cases:
        client = _web_003_client(files)
        page = client.get("/evm").text
        if source_line not in page:
            pytest.fail(f"precondition: /evm's chrome no longer lists {key} as a data source")
        for route in _WEB_003_SIBLINGS:
            if key not in _web_003_named(client.get(route).text):
                pytest.fail(f"precondition: {route} no longer names the refused {key}")
        mixed = key == "EVM2_cycle"
        if mixed and "SOURCE: EVM1.mspdi.xml" not in page:
            pytest.fail("precondition: beside the refused EVM2_cycle, /evm no longer shows EVM1")
        named = _web_003_named(page)
        if key not in named:
            loads = "Load an analyzable schedule" in page
            shown = "EVM1's (SOURCE: EVM1.mspdi.xml)" if mixed else f"none (asks to load: {loads})"
            wrong[key] = {
                "skipped notice names": named or None,
                "chrome lists it as a data source": True,
                "figures shown": shown,
            }

    assert not wrong, (
        f"GET /evm does not name the refused version its chrome lists as a data source (the six "
        f"siblings do; a refused newer version silently shifts the page to the older one's "
        f"figures): {wrong}"
    )
