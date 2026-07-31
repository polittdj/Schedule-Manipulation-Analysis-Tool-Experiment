"""PR-6 of the approved queue (ADR-0320): the /evolution exports honor the page state.

The trace-options banner promises that "every date and path on this page (including the
Excel exports) comes from the re-solved pure-logic network" — but ``export_evolution``
ignored every page parameter (and even the page's own ``?target=`` focus, using only the
session-wide target). This suite pins the closure:

1. the ⤓ export bar carries the LIVE query string (focus / tier / trace options), bare by
   default;
2. ``/export/{fmt}/evolution`` honors ``ignore_constraints`` / ``ignore_leveling`` through
   ``_optioned_versions`` (same fixture oracle as the ADR-0265 family-B suite: a leveled
   schedule whose stored dates vanish under the re-solve);
3. the export honors the focused UID with the page's exact URL-first / session-fallback rule;
4. export headings state the APPLIED scope — and a chosen tier, which never filters these
   tables, is disclosed as not applied rather than silently implied;
5. the two /evolution forms (Focus, Run what-if) and the clear-focus link carry the rest of
   the page's state instead of dropping it; default pages render byte-identically.
"""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _leveled_mspdi(title: str, status: str, shift_days: int) -> bytes:
    """Tasks A→B whose STORED dates sit ``shift_days`` later than pure logic would place
    them (a leveled schedule), plus a standalone off-path task C (UID 3) so a focused
    driving path can differ from the critical set."""
    d0 = 6 + shift_days  # logic would start A on Jan 6; stored dates start later
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>"
        "<Tasks>"
        f"<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        f"<Start>2025-01-{d0:02d}T08:00:00</Start><Finish>2025-01-{d0:02d}T17:00:00</Finish>"
        "</Task>"
        f"<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration>"
        f"<Start>2025-01-{d0 + 1:02d}T08:00:00</Start>"
        f"<Finish>2025-01-{d0 + 2:02d}T17:00:00</Finish>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
        "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00</Start><Finish>2025-01-06T17:00:00</Finish>"
        "</Task>"
        "</Tasks></Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    client = TestClient(create_app(st))
    client.post(
        "/upload",
        files=[
            ("files", ("v1.xml", _leveled_mspdi("Alpha", "2025-01-10T00:00:00", 10), "text/xml")),
            ("files", ("v2.xml", _leveled_mspdi("Alpha", "2025-02-10T00:00:00", 12), "text/xml")),
            ("files", ("v3.xml", _leveled_mspdi("Alpha", "2025-03-10T00:00:00", 14), "text/xml")),
        ],
    )
    return st, client


def _export(client: TestClient, qs: str = "", fmt: str = "xlsx") -> bytes:
    r = client.get(f"/export/{fmt}/evolution{qs}")
    assert r.status_code == 200, r.text
    return r.content


def _pkg_text(content: bytes) -> str:
    """Every XML part of an OOXML package (xlsx/docx are both zips) as one string."""
    with ZipFile(BytesIO(content)) as z:
        return " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())


# ── 1. the export bar carries the live page state ─────────────────────────────────────────────────


def test_the_export_bar_carries_the_live_query_string(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution?target=2&tier=secondary&ignore_leveling=1").text
    live = "/export/xlsx/evolution?target=2&tier=secondary&ignore_leveling=1"
    assert live in html
    assert live.replace("xlsx", "docx") in html


def test_the_default_export_bar_stays_bare(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution").text
    assert 'href="/export/xlsx/evolution"' in html  # closing quote pins "no query string"
    assert 'href="/export/docx/evolution"' in html


# ── 2. the export honors the trace options ────────────────────────────────────────────────────────


def test_export_default_serves_the_stored_schedule(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    text = _pkg_text(_export(client))
    assert "2025-01-22" in text  # v3's stored (leveled) finish of B governs the default rows


def test_export_applies_the_trace_options(sc) -> None:  # type: ignore[no-untyped-def]
    """With ignore_leveling the workbook rows come from the SAME re-solved pure-logic
    network the page shows — the banner's "including the Excel exports" line is now true."""
    _st, client = sc
    stored = _export(client)
    resolved = _export(client, "?ignore_leveling=1")
    assert resolved != stored
    text = _pkg_text(resolved)
    assert "2025-01-08" in text  # pure logic: A Jan 6, B Jan 7-8 — the leveling shift is gone
    assert "2025-01-20" not in text and "2025-01-22" not in text  # stored leveled finishes gone
    # both flags parse together (constraint stripping is a no-op on this fixture, but the
    # parameter must be accepted and the workbook stay well-formed)
    assert _export(client, "?ignore_leveling=1&ignore_constraints=1")


def test_export_defaults_are_byte_identical_to_explicit_defaults(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    assert _export(client) == _export(client, "?tier=off&ignore_constraints=0&ignore_leveling=0")


# ── 3. the export honors the focused UID (URL first, session fallback — the page's rule) ─────────


def test_export_honors_the_url_focus(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    focused = _export(client, "?target=3")
    assert focused != _export(client)  # driving path to off-path C != the critical set
    assert "driving path to UID 3" in _pkg_text(focused)


def test_export_session_focus_applies_the_sessions_own_rule(sc) -> None:  # type: ignore[no-untyped-def]
    """A session-wide Target UID truncates the POPULATION (``SessionState.scope`` runs
    ``subschedule_to_target`` inside ``_solvable_versions``), while a URL ``?target=`` is a
    view focus on the FULL population — the page renders those two states differently, and
    the export mirrors the page in both (it used to read only the session target). Both are
    focused on UID 3 and say so; only the session-scoped rows lose the full network's
    finish."""
    st, client = sc
    by_url = _pkg_text(_export(client, "?target=3"))
    st.target_uid = 3
    by_session = _pkg_text(_export(client))
    assert "driving path to UID 3" in by_url and "driving path to UID 3" in by_session
    assert "2025-01-20" in by_url  # full population: v1's leveled project finish stays
    assert "2025-01-20" not in by_session  # truncated to C + its drivers: it's gone
    assert "2025-01-06" in by_session  # the truncated network finishes at C's own finish


# ── 4. export headings state the applied scope ────────────────────────────────────────────────────


def test_export_headings_state_the_applied_scope(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    text = _pkg_text(_export(client, "?target=2&ignore_leveling=1&ignore_constraints=1"))
    assert "Applied scope" in text  # the workbook's own scope sheet
    assert "driving path to UID 2" in text
    assert "constraints ignored" in text
    assert "leveling delay ignored (pure-logic dates)" in text
    # the Word heading carries the same applied list (TableSet title only reaches docx)
    doc = _pkg_text(_export(client, "?ignore_leveling=1", fmt="docx"))
    assert "Critical-path evolution - leveling delay ignored (pure-logic dates)" in doc


def test_default_export_carries_no_scope_sheet(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    assert "Applied scope" not in _pkg_text(_export(client))


def test_a_chosen_tier_is_disclosed_not_applied(sc) -> None:  # type: ignore[no-untyped-def]
    """The tier stepper is an on-screen lens; these tables keep the path basis. The heading
    must say so instead of silently implying a tier filter (a wrong scope line is worse
    than none) — and must never CLAIM the tier was applied."""
    _st, client = sc
    text = _pkg_text(_export(client, "?tier=secondary"))
    assert "the on-screen tier view (secondary) is not applied" in text
    assert "these tables keep the path basis" in text
    # tier alone applies no transform: the title gains no suffix and the rows are unchanged
    doc = _pkg_text(_export(client, "?tier=secondary", fmt="docx"))
    assert "Critical-path evolution -" not in doc
    # an unknown tier value is not a tier view — no disclosure, no scope sheet
    assert "Applied scope" not in _pkg_text(_export(client, "?tier=zzz"))


# ── 5. the two forms + the clear-focus link stop dropping state ───────────────────────────────────


def test_the_focus_form_keeps_the_trace_options(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution?ignore_constraints=1&ignore_leveling=1").text
    focus_form = html.split("Focus a specific activity")[0].rsplit("<form", 1)[1]
    assert '<input type=hidden name="ignore_constraints" value="1">' in focus_form
    assert '<input type=hidden name="ignore_leveling" value="1">' in focus_form


def test_the_whatif_form_keeps_focus_tier_and_options(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution?target=2&tier=secondary&ignore_leveling=1").text
    picker = html.split("Compare any two of the")[0].rsplit("<form", 1)[1]
    assert '<input type=hidden name="target" value="2">' in picker
    assert '<input type=hidden name="tier" value="secondary">' in picker
    assert '<input type=hidden name="ignore_leveling" value="1">' in picker
    assert 'name="ignore_constraints"' not in picker  # off — defaults are not echoed


def test_the_clear_focus_link_keeps_the_rest_of_the_state(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution?target=2&tier=secondary&ignore_leveling=1").text
    assert 'href="/evolution?target=&tier=secondary&ignore_leveling=1"' in html
    # with nothing else set the link keeps its historical shape (explicit empty target,
    # which must override a session-wide focus — an absent parameter would not)
    bare = client.get("/evolution?target=2").text
    assert 'href="/evolution?target="' in bare


def test_the_default_page_emits_no_hidden_state(sc) -> None:  # type: ignore[no-untyped-def]
    """Default option state stays out of the forms entirely (byte-identical default render):
    the quoted hidden-input shape never appears for the ignore flags — the trace-option
    CHECKBOXES use unquoted attributes, so this discriminates cleanly. (The trace-options
    form's own ``tier=off`` keep predates this change and is deliberately untouched.)"""
    _st, client = sc
    html = client.get("/evolution").text
    assert 'type=hidden name="ignore_constraints"' not in html
    assert 'type=hidden name="ignore_leveling"' not in html
