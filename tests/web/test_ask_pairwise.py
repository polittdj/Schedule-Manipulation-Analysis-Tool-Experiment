"""Ask-the-AI compares EVERY consecutive version pair, on every page (ADR-0424).

Operator report (2026-08-18): with more than two schedules loaded, an Ask-the-AI question got a
comparative analysis of the last two only — reported against the Schedule Integrity page, but the
Ask panel is one shared component (``chrome._ask_panel_html``) rendered by ``_page`` on every
page, so the defect was every page's.

Two routes serve that one panel: ``/api/ask`` (the "Workbook — all N versions" scope, which
``/integrity`` gets because it passes no ``ask_schedule``) and ``/api/ask/{name}`` (a single file
picked from the same select). Both are covered here.

The third test is the one that cost the most to find: the consecutive-pair sweep runs the
manipulation DIFF detector, and a diff must never see a Target-UID-truncated population (ADR-0371).
Measured on the Project2 → Project5 golden with a target set, the truncated diff invents a
HIGH-severity "13 activities deleted since the prior version" the untruncated diff does not report
— while the total signal COUNT is identical either way, so counting cannot detect it.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
_D0 = dt.datetime(2026, 4, 15)


def _session(n: int, *, cut_at: set[int] = frozenset()) -> SessionState:
    """``n`` monthly versions of the golden project; a duration halved going into each step."""
    st = SessionState()
    base = parse_mspdi(GOLDEN / "Project5.mspdi.xml")
    victims = [
        t.unique_id
        for t in base.tasks
        if not t.is_summary and t.percent_complete < 100.0 and t.duration_minutes >= 4800
    ]
    cur = base
    for i in range(n):
        if i in cut_at:
            uid = victims[i % len(victims)]
            cur = cur.model_copy(
                update={
                    "tasks": tuple(
                        t.model_copy(update={"duration_minutes": t.duration_minutes // 2})
                        if t.unique_id == uid
                        else t
                        for t in cur.tasks
                    )
                }
            )
        label = f"IPMR_v{i + 1:02d}.mpp"
        st.schedules[label] = cur.model_copy(
            update={
                "name": label,
                "source_file": label,
                "status_date": _D0 + dt.timedelta(days=30 * i),
            }
        )
    return st


def _fact_text(payload: dict) -> str:
    return "\n".join(f["text"] for f in payload["facts"])


# --- 1. the workbook scope (what /integrity's panel uses) -------------------------------------


def test_workbook_ask_compares_every_pair_not_just_the_newest_two() -> None:
    """THE operator regression: 5 versions, manipulation in step 1, newest pair clean."""
    client = TestClient(create_app(_session(5, cut_at={1})))
    r = client.post("/api/ask", data={"question": "is there a pattern of schedule manipulation?"})
    assert r.status_code == 200
    body = _fact_text(r.json())
    assert "PAIRWISE COMPARISON SERIES: all 5 loaded version(s)" in body
    assert "4 comparison(s)" in body
    assert "MANIPULATION-SIGNAL RECURRENCE" in body
    assert "Manipulation signal at step 1 of 4" in body, "the EARLIEST pair's signal must be here"


def test_workbook_ask_states_a_measured_absence_across_the_whole_series() -> None:
    client = TestClient(create_app(_session(6)))
    r = client.post("/api/ask", data={"question": "any manipulation?"})
    body = _fact_text(r.json())
    assert "none of the 5 consecutive-pair comparison(s) fired any manipulation signal" in body


def test_a_one_pair_absence_says_which_comparison_it_is_out_of_how_many() -> None:
    """The affirmative negative that read as a workbook verdict now carries its own scope."""
    client = TestClient(create_app(_session(5)))
    body = _fact_text(client.post("/api/ask", data={"question": "durations shortened?"}).json())
    # unconditional: a guarded assertion is one that cannot fail if the guard stops matching
    assert "No incomplete activity on the critical path had its duration shortened" in body
    assert "This is comparison 4 of 4 (the newest update) in a 5-version workbook" in body
    assert "See the PAIRWISE COMPARISON SERIES fact" in body


# --- 2. the single-file scope of the SAME panel ------------------------------------------------


def test_single_file_ask_also_carries_the_whole_comparison_series() -> None:
    """Scoping the panel to one file does not make the other versions stop existing."""
    client = TestClient(create_app(_session(5, cut_at={1})))
    r = client.post(
        "/api/ask/IPMR_v01.mpp", data={"question": "is there a pattern of manipulation?"}
    )
    assert r.status_code == 200
    body = _fact_text(r.json())
    assert "PAIRWISE COMPARISON SERIES: all 5 loaded version(s)" in body
    assert "Manipulation signal at step 1 of 4" in body


def test_a_lone_schedule_gets_no_comparison_facts() -> None:
    client = TestClient(create_app(_session(1)))
    body = _fact_text(client.post("/api/ask", data={"question": "manipulation?"}).json())
    assert "PAIRWISE COMPARISON SERIES" not in body


# --- 3. the population the diffs run on (ADR-0371 / ADR-0424) ---------------------------------


@pytest.mark.parametrize("route", ["/api/ask", "/api/ask/IPMR_v02.mpp"])
def test_the_pair_diffs_never_run_on_a_target_truncated_population(route: str) -> None:
    """With a Target UID set, ``_solvable_versions()`` truncates each version to the cone that
    drives the target. Diffing THOSE reads cone membership as file changes and invents deleted
    tasks. The sweep must take ``_pair_versions()`` — filter applied, target never applied.

    The oracle is the fabricated signal itself, not a count: the truncated and untruncated diffs
    of this golden pair both report 5 signals.
    """
    st = SessionState()
    for label, src in (("IPMR_v01.mpp", "Project2"), ("IPMR_v02.mpp", "Project5")):
        sch = parse_mspdi(GOLDEN / f"{src}.mspdi.xml")
        st.schedules[label] = sch.model_copy(
            update={
                "name": label,
                "source_file": label,
                "status_date": _D0 + dt.timedelta(days=30 * (label.endswith("2.mpp"))),
            }
        )
    client = TestClient(create_app(st))
    clean = _fact_text(client.post(route, data={"question": "what changed?"}).json())

    st.set_target(145)  # the last critical activity; its cone is ~109 of 145 tasks
    targeted = _fact_text(client.post(route, data={"question": "what changed?"}).json())

    # The probe is the COMPACT label, which rides the pinned series/recurrence facts: the route
    # returns only the 12 question-relevant facts, so the finding's own title ("13 activities
    # deleted since the prior version") can be trimmed out of the response and read as clean.
    fabricated = "task deleted from the critical path"
    for body, tag in ((clean, "no target"), (targeted, "target set")):
        assert "PAIRWISE COMPARISON SERIES" in body, f"series missing ({tag})"
        assert fabricated not in body, (
            f"the pair diff fabricated a deleted-task signal out of cone membership ({tag}) — "
            "it is running on the target-truncated population, not the pair population"
        )
    # CONTROL: the truncated populations really do produce that signal, so the assertion above
    # is measuring something. Without this the test passes on a build that fabricates nothing
    # because it compares nothing.
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.engine.pair_series import compute_pairwise_series

    truncated = [st.scope(v) for v in st.schedules.values()]
    control = compute_pairwise_series(truncated, [compute_cpm(v) for v in truncated])
    assert any("MANIP_DELETED_TASK" in step.signal_ids for step in control.steps), (
        "the control did not move: this golden pair no longer fabricates under truncation"
    )
