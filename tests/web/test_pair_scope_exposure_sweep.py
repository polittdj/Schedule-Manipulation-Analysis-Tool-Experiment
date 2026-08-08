"""The ADR-0370 exposure sweep (ADR-0371): every remaining version-PAIR forensic surface.

ADR-0370 fixed /integrity: a session Target UID truncates every version to the target's own
ancestor cone (``scope()``), and diffing two DIFFERENTLY-truncated cones as if they were the
files fabricates changes (cone membership reads as a file change), zeroes real revert effects
(a restored link dangles into a missing task) and hides edits outside the cone. The same
truncated pairs still fed /compare, /trend's pairwise signals, /evolution (per-step signals +
the counterfactual), the whatif/evolution/compare/mission exports, the Diagnostic Brief's
version-pair questions and the Executive Briefing's section 3.1.

On the ADR-0370 control pair the truncated pipeline literally fabricates the tool's worst
accusation — a HIGH "2 activities deleted since the prior version" — while hiding the real
duration cut (the positive control below demonstrates it). This module pins the fix: those
surfaces run on the PAIR scope (``_pair_versions`` / ``build_brief``'s / ``build_briefing``'s
``pair_*`` populations) — the reduce-FILTER still applies, the Target UID only anchors.

Every web test POSTs /target and asserts the 303 — a setup that can 405 silently tests
nothing (the ADR-0370 trap).
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile

from fastapi.testclient import TestClient

from schedule_forensics.ai.brief import build_brief
from schedule_forensics.ai.briefing import build_briefing
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.path_counterfactual import compute_path_counterfactual
from schedule_forensics.engine.path_evolution import compute_path_evolution
from schedule_forensics.engine.path_trace import subschedule_to_target
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

FS = RelationshipType.FS
START = dt.datetime(2026, 1, 7)  # a Wednesday — a working day on the default calendar

#: The fabricated HIGH accusation the truncated pair invents (and the fix removes).
FABRICATED = "activities deleted since the prior version"
#: The real MEDIUM finding the truncated pair hides (Dig's cut is outside the comparison cone).
REAL_CUT = "incomplete activities had their duration shortened"


def _rel(pred: int, succ: int) -> Relationship:
    return Relationship(predecessor_id=pred, successor_id=succ, type=FS)


def _pair(dig_prior: int = 2400, dig_cur: int = 1440) -> tuple[Schedule, Schedule]:
    """The ADR-0370 control pair: A = Dig→Pour→Roof with Wire→Roof; B removes Pour→Roof and
    cuts Dig. With the target on Roof (UID 3), B's cone is {Wire, Roof} — Dig/Pour leave it,
    so the truncated diff invents deletions and cannot see Dig's cut. ``dig_*`` let the brief
    test widen the cut (25d→1d) so the remaining-cut question triggers on the REAL pair."""
    cal = Calendar(name="Std")
    prior_tasks = (
        Task(unique_id=1, name="Dig", duration_minutes=dig_prior),
        Task(unique_id=2, name="Pour", duration_minutes=2400),
        Task(unique_id=3, name="Roof", duration_minutes=480),
        Task(unique_id=4, name="Wire", duration_minutes=480),
    )
    prior = Schedule(
        name="Job",
        source_file="A.mpp",
        project_start=START,
        status_date=dt.datetime(2026, 1, 7),
        calendar=cal,
        tasks=prior_tasks,
        relationships=(_rel(1, 2), _rel(2, 3), _rel(4, 3)),
    )
    cur_tasks = tuple(
        t.model_copy(update={"duration_minutes": dig_cur}) if t.unique_id == 1 else t
        for t in prior_tasks
    )
    current = Schedule(
        name="Job",
        source_file="B.mpp",
        project_start=START,
        status_date=dt.datetime(2026, 2, 4),
        calendar=cal,
        tasks=cur_tasks,
        relationships=(_rel(1, 2), _rel(4, 3)),
    )
    return prior, current


def _client(prior: Schedule, current: Schedule) -> TestClient:
    c = TestClient(create_app(SessionState()), raise_server_exceptions=True)
    st = c.app.state.session  # type: ignore[attr-defined]
    st.schedules["A.mpp"] = prior
    st.schedules["B.mpp"] = current
    return c


def _client_with_target(prior: Schedule, current: Schedule) -> TestClient:
    c = _client(prior, current)
    r = c.post("/target", data={"uid": "3", "next_url": "/"}, follow_redirects=False)
    assert r.status_code == 303  # the POST really took the target (GET /target is a 405)
    return c


def _sheets(content: bytes) -> str:
    zf = zipfile.ZipFile(io.BytesIO(content))
    return "".join(zf.read(n).decode() for n in zf.namelist() if n.startswith("xl/worksheets/"))


# ── the defect, demonstrated (positive control): what the truncated pair feeds every engine ─


def test_truncated_pair_control_fabricates_on_every_engine() -> None:
    """The OLD pipeline's inputs produce the lies on all three engines this sweep re-bases —
    the control proving the surface tests below measure the real defect."""
    prior, current = _pair()
    p_t, c_t = subschedule_to_target(prior, 3), subschedule_to_target(current, 3)
    # detect_manipulation: a fabricated HIGH deleted-task accusation; the real cut invisible
    truncated = {f.metric_id: f for f in detect_manipulation(c_t, p_t)}
    assert "MANIP_DELETED_TASK" in truncated
    assert str(truncated["MANIP_DELETED_TASK"].severity) == "HIGH"
    assert "MANIP_SHORTENED_DURATION" not in truncated
    raw = {f.metric_id: f for f in detect_manipulation(current, prior)}
    assert "MANIP_DELETED_TASK" not in raw  # no activity was deleted between the real files
    assert "MANIP_SHORTENED_DURATION" in raw  # Dig's cut is visible on the real pair
    # path evolution (unanchored, the briefing/mission basis): entered/left near-inverted
    snap_t = compute_path_evolution([p_t, c_t], [compute_cpm(p_t), compute_cpm(c_t)]).snapshots[-1]
    assert (snap_t.entered, snap_t.left) == ((4,), (1, 2))  # Wire "entered", Dig/Pour "left"
    snap = compute_path_evolution(
        [prior, current], [compute_cpm(prior), compute_cpm(current)]
    ).snapshots[-1]
    assert (snap.entered, snap.left) == ((), (3,))  # the truth: only Roof left the path
    # the counterfactual: starved to None by the dangling restore
    assert (
        compute_path_counterfactual(p_t, c_t, compute_cpm(p_t), compute_cpm(c_t), target_uid=3)
        is None
    )
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None and [(r.uid, r.name) for r in pc.reverted] == [(3, "Roof")]


# ── /compare and its export ───────────────────────────────────────────────────────────────


def test_compare_with_target_diffs_the_real_files() -> None:
    c = _client_with_target(*_pair())
    page = c.get("/compare").text
    # the header KPI takeaway counts the real diff — not cone membership
    assert (
        "Between the two versions, 1 activity changed, 0 added and 0 removed, "
        "with 0 logic links added and 1 removed" in page
    )
    # the signals are the real pair's findings: the cut visible, no fabricated deletion
    assert REAL_CUT in page
    assert FABRICATED not in page


def test_compare_export_matches_the_page() -> None:
    c = _client_with_target(*_pair())
    sheets = _sheets(c.get("/export/xlsx/compare").content)
    assert "logic links removed since the prior version" in sheets
    assert REAL_CUT in sheets
    assert FABRICATED not in sheets


# ── /trend's pairwise signal roll-up ──────────────────────────────────────────────────────


def test_trend_signals_with_target_are_real_file_findings() -> None:
    c = _client_with_target(*_pair())
    page = c.get("/trend").text
    assert f"1 {REAL_CUT}" in page
    assert FABRICATED not in page


# ── /evolution: the counterfactual un-starved, the per-step signals un-fabricated ─────────


def test_evolution_counterfactual_with_target_measures_the_real_revert() -> None:
    c = _client_with_target(*_pair())
    page = c.get("/evolution").text
    # the whatif rows carry the real revert (the truncated pair starved this to None)
    assert '"name": "Roof"' in page
    assert '"change_reverted": "logic 1 link(s) restored"' in page
    # and no per-step signal fabricates a deletion
    assert FABRICATED not in page


def test_whatif_export_with_target_carries_the_real_revert() -> None:
    c = _client_with_target(*_pair())
    sheets = _sheets(c.get("/export/xlsx/whatif?a=A.mpp&b=B.mpp").content)
    assert "Roof" in sheets and "logic 1 link(s) restored" in sheets
    assert "Wire" not in sheets  # nothing fabricated into the revert list


# ── the mission export's evolution tables (unanchored path_evolution) ─────────────────────


def test_mission_export_evolution_rows_diff_the_real_pair() -> None:
    c = _client_with_target(*_pair())
    sheets = _sheets(c.get("/export/xlsx/mission").content)
    # the truth: Roof left the path (its inbound link was removed); nothing entered
    assert ">Roof<" in sheets and ">left<" in sheets
    assert ">Wire<" not in sheets and ">entered<" not in sheets  # the cone fabrications


# ── the Executive Briefing's section 3.1 and the Diagnostic Brief's pair questions ────────


def test_briefing_section31_diffs_the_real_pair() -> None:
    c = _client_with_target(*_pair())
    page = c.get("/briefing").text
    assert "0 moved onto the critical path and 1 moved off" in page
    assert "No Longer Critical" in page  # Roof's table renders…
    assert "Newly Critical" not in page  # …and nothing fabricated an entry


def test_brief_questions_see_outside_the_cone() -> None:
    """The remaining-cut question names Dig (24 wd cut vs 20 wd elapsed) even though Dig is
    outside the comparison cone — and no fabricated deleted-activities question appears."""
    c = _client_with_target(*_pair(dig_prior=12000, dig_cur=480))
    page = c.get("/brief").text
    assert "(UID 1) had its remaining duration cut by 24 working days" in page
    assert "activities deleted" not in page


# ── the plumbing, pinned at the function tier (independent of the web wiring) ─────────────


def test_build_brief_pair_populations_feed_the_pair_questions() -> None:
    prior, current = _pair(dig_prior=12000, dig_cur=480)
    p_t, c_t = subschedule_to_target(prior, 3), subschedule_to_target(current, 3)
    trunc_s, trunc_c = [p_t, c_t], [compute_cpm(p_t), compute_cpm(c_t)]
    brief = build_brief(
        trunc_s,
        trunc_c,
        pair_schedules=[prior, current],
        pair_cpms=[compute_cpm(prior), compute_cpm(current)],
    )
    text = " ".join(p.text for s in brief.sections for p in s.paragraphs)
    assert "had its remaining duration cut by 24 working days" in text
    assert "activities deleted" not in text
    # without the pair populations the truncated primaries fabricate and hide — the control
    control = build_brief(trunc_s, trunc_c)
    ctl_text = " ".join(p.text for s in control.sections for p in s.paragraphs)
    assert "activities deleted" in ctl_text
    assert "remaining duration cut" not in ctl_text


def test_build_briefing_section31_uses_pair_populations() -> None:
    prior, current = _pair()
    p_t, c_t = subschedule_to_target(prior, 3), subschedule_to_target(current, 3)
    trunc_s, trunc_c = [p_t, c_t], [compute_cpm(p_t), compute_cpm(c_t)]
    briefing = build_briefing(
        trunc_s,
        cpms=trunc_c,
        pair_schedules=[prior, current],
        pair_cpms=[compute_cpm(prior), compute_cpm(current)],
    )
    text = " ".join(s.text for sec in briefing.sections for s in sec.statements)
    assert "0 moved onto the critical path and 1 moved off" in text
    # the control: truncated primaries alone report the cone fabrication
    control = build_briefing(trunc_s, cpms=trunc_c)
    ctl_text = " ".join(s.text for sec in control.sections for s in sec.statements)
    assert "1 moved onto the critical path and 2 moved off" in ctl_text
