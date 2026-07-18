"""Family-B option-plumbing unification (ADR-0265 — the behavior work ADR-0251 queued).

ADR-0251 froze the taxonomy: family B (/driving-path, /evolution) is a deliberate
COUNTERFACTUAL re-solve, and four of its surfaces were disclosed as mixed-basis. This PR
unifies them so every element of a counterfactual page shares ONE basis:

1. `/api/evolution` (the stepper's feed) accepts the trace options and serves the SAME
   re-solved network the server-rendered panels use; the page embeds the active options for
   the chart script to forward. The /mission wall embeds none — byte-identical behavior.
2. `/export/{fmt}/path/{name}` gains `basis=resolve`: the /driving-path full-trace export
   runs on the page's re-solved network (default `stored` stays the SSI-parity stored-date
   trace, byte-identical — the /path page's basis).
3. The driving-tiers drill + its Excel no longer mix bases: solve-dependent columns
   (start / finish / total float / critical — stored-network figures) are dropped while the
   trace options are active; basis-independent input columns (durations, %, WBS, resources,
   baselines, custom fields) remain.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _leveled_mspdi(title: str, status: str, shift_days: int) -> bytes:
    """Two linked tasks whose STORED dates sit ``shift_days`` later than pure logic would
    place them (a leveled/progressed schedule): under ``ignore_leveling`` the re-solve
    clears the stored dates and the pure-logic CPM pulls everything back."""
    d0 = 6 + shift_days  # logic start would be Jan 6; stored dates start later
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
        "</Task></Tasks></Project>"
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
        ],
    )
    return st, client


# ── 1. /api/evolution honors the trace options ────────────────────────────────────────────────────


def test_api_evolution_default_serves_the_stored_schedule(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    data = client.get("/api/evolution").json()
    # the stored (leveled) finish of v2's task 2 — Jan 6 + 12 shift + chain = Jan 20
    text = str(data)
    assert "2025-01-20" in text  # stored dates govern the default feed (family-A view)


def test_api_evolution_applies_the_trace_options(sc) -> None:  # type: ignore[no-untyped-def]
    """With ignore_leveling the feed serves the SAME re-solved pure-logic network the
    server-rendered panels show — the ADR-0251 stepper/panels split is closed."""
    _st, client = sc
    stored = client.get("/api/evolution").json()
    resolved = client.get("/api/evolution?ignore_leveling=1").json()
    assert resolved != stored
    text = str(resolved)
    assert "2025-01-08" in text  # pure logic: A Jan 6, B Jan 7-8 — the leveling shift is gone
    assert "2025-01-20" not in text  # the stored leveled dates no longer appear
    # both flags parse (ignore_constraints strips constraints — a no-op on this fixture,
    # but the parameter must be accepted and the payload stay well-formed)
    both = client.get("/api/evolution?ignore_leveling=1&ignore_constraints=1").json()
    assert both.get("versions") or both.get("frames") or both  # well-formed payload


def test_evolution_page_embeds_the_options_for_the_stepper(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/evolution?ignore_leveling=1").text
    assert 'data-ignore-leveling="1"' in html
    assert 'data-ignore-constraints="0"' in html
    default = client.get("/evolution").text
    assert 'data-ignore-leveling="0"' in default
    # the chart script forwards them to the feed
    js = client.get("/static/path_evolution.js").text
    assert "ignore_leveling" in js and "ignore_constraints" in js


def test_mission_wall_stepper_stays_on_the_stored_basis(sc) -> None:  # type: ignore[no-untyped-def]
    """The wall has no trace options — its evolution tile must not grow option attributes."""
    _st, client = sc
    html = client.get("/mission").text
    assert "data-ignore-leveling" not in html


# ── 2. the full-trace export can run on the page's re-solved basis ────────────────────────────────


def _export_path(client: TestClient, key: str, extra: str = "") -> bytes:
    r = client.get(f"/export/xlsx/path/{key}?target=2{extra}")
    assert r.status_code == 200, r.text
    return r.content


def test_full_trace_export_default_basis_is_unchanged(sc) -> None:  # type: ignore[no-untyped-def]
    """No basis param, explicit basis=stored, and basis=resolve with NO options are all
    byte-identical — the family-A stored-date trace (goldens hold)."""
    st, client = sc
    key = next(iter(st.schedules))
    default = _export_path(client, key)
    assert default == _export_path(client, key, "&basis=stored")
    assert default == _export_path(client, key, "&basis=resolve")  # no options -> no transform


def test_full_trace_export_resolve_basis_matches_the_page(sc) -> None:  # type: ignore[no-untyped-def]
    """basis=resolve + the page's options exports the COUNTERFACTUAL network's trace — it
    must differ from the stored-date trace on a leveled schedule (the whole point), while
    the stored basis with the same flags keeps the SSI-parity semantics (a stored-date
    trace, dated tasks governed by stored dates)."""
    st, client = sc
    key = next(iter(st.schedules))
    stored = _export_path(client, key, "&ignore_leveling=1")  # family A: SSI option semantics
    resolved = _export_path(client, key, "&ignore_leveling=1&basis=resolve")
    assert resolved != stored


# ── 3. the tiers drill + Excel share the page's basis ─────────────────────────────────────────────


def test_tiers_export_drops_solve_dependent_columns_under_options(sc) -> None:  # type: ignore[no-untyped-def]
    st, client = sc
    key = next(iter(st.schedules))
    cols = "Start,Finish,Total float (d),Critical,WBS,Duration (d)"
    plain = client.get(f"/export/xlsx/driving-tiers/{key}?target=2&cols={cols}")
    assert plain.status_code == 200
    optioned = client.get(
        f"/export/xlsx/driving-tiers/{key}?target=2&cols={cols}&ignore_leveling=1"
    )
    assert optioned.status_code == 200
    from io import BytesIO
    from zipfile import ZipFile

    def sheet_xml(content: bytes) -> str:
        with ZipFile(BytesIO(content)) as z:
            return " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())

    plain_xml = sheet_xml(plain.content)
    optioned_xml = sheet_xml(optioned.content)
    # exact header CELLS ("<t>Start</t>"), so data cells like the "Critical / driving" tier
    # label can never satisfy (or spoil) the assertion
    for kept in ("<t>WBS</t>", "<t>Duration (d)</t>"):
        assert kept in plain_xml and kept in optioned_xml
    for dropped in ("<t>Start</t>", "<t>Finish</t>", "<t>Total float (d)</t>", "<t>Critical</t>"):
        assert dropped in plain_xml  # served on the stored basis…
        assert dropped not in optioned_xml  # …but never mixed into the re-solved basis


def test_tiers_drill_js_hides_solve_dependent_columns_under_options(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    js = client.get("/static/driving_tiers.js").text
    assert "SOLVE_DEPENDENT" in js  # the hide list exists…
    for key in ("start", "finish", "total_float_days", "is_critical"):
        assert f'"{key}"' in js  # …and names exactly the stored-basis fields
