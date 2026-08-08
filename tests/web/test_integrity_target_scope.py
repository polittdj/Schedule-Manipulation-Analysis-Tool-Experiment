"""/integrity with a Target UID set measures change effects on the REAL pair (2026-08-08).

The operator's report: "When you select a target UID it is not correctly calculating the change
effects if reversed to that UID." Root cause: ``SessionState.scope()`` truncates every version to
``subschedule_to_target`` — the target plus its ancestors under THAT VERSION'S OWN logic — and
/integrity diffed the two differently-truncated cones as if they were the files. Three distinct
lies followed on one synthetic pair (all demonstrated by the positive control below):

1. **False "no effect"** — restoring the genuinely-removed link 2→3 dangles: predecessor 2 left
   the comparison's cone, CPM drops the edge (cpm.py keeps only edges with BOTH endpoints), and
   the true +7 wd effect on the target reads 0.
2. **Fabricated change** — link 1→2 exists in BOTH files, but its endpoints leave the comparison
   cone, so the truncated diff reports it "removed".
3. **Missed change** — the duration cut on UID 1 is invisible (the task is absent from the
   comparison cone entirely).

The fix: the page, its export and the AI manipulation facts run on ``_pair_versions()`` /
``SessionState.cpm_pair_for`` — the active FILTER still applies, the Target UID never truncates;
it anchors the measurement (``compute_change_effects(..., target_uid=)``) instead.

Why no earlier test caught it: the only "target set" /integrity test called GET /target, a
POST-only route — the 405 left the session target unset, so the pin exercised the no-target
path where the auto-chosen last-critical task made the numbers coincide (the handoff's queued
"3 web tests calling GET /target" item; fixed alongside this file).
"""

from __future__ import annotations

import datetime as dt
import io
import re
import zipfile

from fastapi.testclient import TestClient

from schedule_forensics.engine.change_effects import compute_change_effects
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.path_trace import subschedule_to_target
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

FS = RelationshipType.FS
START = dt.datetime(2026, 1, 7)  # a Wednesday — a working day on the default calendar


def _rel(pred: int, succ: int) -> Relationship:
    return Relationship(predecessor_id=pred, successor_id=succ, type=FS)


def _pair() -> tuple[Schedule, Schedule]:
    """Baseline A: Dig(5d)→Pour(5d)→Roof(1d) with Wire(1d)→Roof. Comparison B removes the
    Pour→Roof link AND cuts Dig 5d→3d. With the target on Roof (UID 3):

    * restoring 2→3 alone moves Roof 2d→9d = **+7 wd on the target**, +1 wd on the project;
    * restoring Dig's duration alone moves the project +2 wd but Roof **0** (a TRUE no-effect);
    * both together: **+9 wd on the target**, +3 wd on the project.

    Dig and Pour are NOT ancestors of Roof in B (the removal disconnected them) — exactly the
    cone change that broke the truncated pipeline."""
    cal = Calendar(name="Std")
    prior_tasks = (
        Task(unique_id=1, name="Dig", duration_minutes=2400),
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
        t.model_copy(update={"duration_minutes": 1440}) if t.unique_id == 1 else t
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


def _client_with_pair() -> TestClient:
    c = TestClient(create_app(SessionState()), raise_server_exceptions=True)
    st = c.app.state.session  # type: ignore[attr-defined]
    prior, current = _pair()
    st.schedules["A.mpp"] = prior
    st.schedules["B.mpp"] = current
    return c


# ── the defect, demonstrated (positive control): the truncated pair measures wrongly ──────


def test_truncated_pair_fabricates_and_zeroes_the_control() -> None:
    """The OLD pipeline's inputs (each version truncated to the target's own cone) produce all
    three lies — this is the control proving the page test below measures the real defect (a
    pipeline regression re-feeding truncated pairs would resurrect exactly these)."""
    prior, current = _pair()
    p_trunc = subschedule_to_target(prior, 3)
    c_trunc = subschedule_to_target(current, 3)
    # the comparison cone lost Dig and Pour — the truncation the fix removes
    assert {t.unique_id for t in c_trunc.tasks} == {3, 4}
    eff = compute_change_effects(p_trunc, c_trunc, compute_cpm(c_trunc), target_uid=3)
    assert eff is not None
    by_label = {e.label: e for e in eff.per_change}
    # lie 1: the real removed link 2→3 dangles (no task 2) and measures a false ZERO
    real = by_label["restore removed FS link 2→3"]
    assert real.target_finish_delta_days == 0 and real.target_finish_delta_minutes == 0
    # lie 2: link 1→2 exists in BOTH files, yet the truncated diff reports it "removed"
    assert "restore removed FS link 1→2" in by_label
    # lie 3: the duration cut on Dig is invisible (the task left the cone)
    assert not [e for e in eff.per_change if e.kind == "duration_restored"]


# ── the fix, at the engine boundary the routes now feed (raw pair, target as anchor) ──────


def test_raw_pair_measures_the_true_target_effects() -> None:
    prior, current = _pair()
    eff = compute_change_effects(prior, current, compute_cpm(current), target_uid=3)
    assert eff is not None and not eff.target_unavailable
    by_label = {e.label: e for e in eff.per_change}
    link = by_label["restore removed FS link 2→3"]
    assert link.target_finish_delta_days == 7  # the effect the truncation zeroed
    assert link.project_finish_delta_days == 1  # ≠ target effect: really measured ON the target
    assert link.link_type == "FS" and link.citation_uids == (2, 3)
    dur = by_label["restore UID 1 duration (cut 3→5 wd)"]
    assert dur.target_finish_delta_days == 0  # a TRUE zero on the target…
    assert dur.project_finish_delta_days == 2  # …while the project moves
    assert dur.prior_duration_minutes == 2400 and dur.current_duration_minutes == 1440
    assert dur.percent_complete == 0.0
    # no fabricated rows: exactly the two real changes
    assert set(by_label) == {"restore removed FS link 2→3", "restore UID 1 duration (cut 3→5 wd)"}
    assert eff.aggregate_target_finish_delta_days == 9
    assert eff.aggregate_project_finish_delta_days == 3


# ── the state machinery: the pair scope ignores the target, and re-serves resident solves ──


def test_cpm_pair_for_ignores_the_target_truncation() -> None:
    c = _client_with_pair()
    st = c.app.state.session  # type: ignore[attr-defined]
    _prior, current = st.schedules["A.mpp"], st.schedules["B.mpp"]
    st.set_target(3)
    scoped, _cpm = st.cpm_scoped_for("B.mpp", current)
    pair, _cpm2 = st.cpm_pair_for("B.mpp", current)
    assert {t.unique_id for t in scoped.tasks} == {3, 4}  # the target truncation, still real…
    assert pair is current  # …while the pair scope hands the RAW schedule through (no filter)


# ── the page: target set via the REAL (POST) route → true figures, no fabrications ────────


def test_integrity_with_target_set_shows_true_effects_and_no_fabrications() -> None:
    c = _client_with_pair()
    r = c.post("/target", data={"uid": "3", "next_url": "/integrity"}, follow_redirects=False)
    assert r.status_code == 303  # the POST route really took the target (GET /target is a 405)
    page = c.get("/integrity?a=0&b=1").text
    assert "Effect of each change on UID 3 (Roof)" in page
    # the true effect the truncation used to zero — and the distinct project column
    assert "restore removed FS link 2→3" in page
    assert "+7 wd" in page and "+1 wd" in page
    # the duration cut is present (was invisible), with its true no-effect-on-target
    assert "restore UID 1 duration (cut 3→5 wd)" in page
    assert "no effect" in page
    # no fabricated change rows from cone membership
    assert "restore removed FS link 1→2" not in page
    # the aggregate line measures the target, not the cone endpoint
    assert "+9 working day" in page


def test_integrity_target_absent_from_comparison_still_disclosed() -> None:
    """A target UID absent from the comparison version renders the ADR-0369 banner (sentinel),
    never a silent omission — unchanged by the pair-scope fix."""
    c = _client_with_pair()
    c.post("/target", data={"uid": "999", "next_url": "/"}, follow_redirects=False)
    page = c.get("/integrity?a=0&b=1").text
    assert "target unavailable" in page
    assert "UID 999" in page


# ── the operator's detail asks: was→now column, finding magnitudes, the logic diagram ─────


def test_was_now_column_states_duration_and_link_specifics() -> None:
    c = _client_with_pair()
    c.post("/target", data={"uid": "3", "next_url": "/"}, follow_redirects=False)
    page = c.get("/integrity?a=0&b=1").text
    assert "Was &rarr; is now" in page  # the column exists
    assert "was 5 wd → now 3 wd (-2 wd removed; 0% complete)" in page
    assert "link FS 2→3 — was present, now removed" in page


def test_shortened_duration_finding_names_was_now_and_days_removed() -> None:
    prior, current = _pair()
    findings = detect_manipulation(current, prior)
    cut = next(f for f in findings if f.metric_id == "MANIP_SHORTENED_DURATION")
    assert "UID 1 'Dig' was 5 wd → now 3 wd (2 wd removed; 0% complete)" in cut.detail
    logic = next(f for f in findings if f.metric_id == "MANIP_DELETED_LOGIC")
    assert "Removed: FS 2→3." in logic.detail


def test_logic_diagram_draws_the_removed_link_with_names_and_effect() -> None:
    c = _client_with_pair()
    c.post("/target", data={"uid": "3", "next_url": "/"}, follow_redirects=False)
    page = c.get("/integrity?a=0&b=1").text
    assert "Logic changes &mdash; before &rarr; after" in page
    assert '<div class="logic-row removed">' in page
    assert "UID 2 &middot; Pour" in page and "UID 3 &middot; Roof" in page
    assert "removed in B" in page
    m = re.search(r'<div class="logic-row removed">.*?</div>', page, re.S)
    assert m is not None and "+7 wd" in m.group(0)  # the measured effect rides the diagram row


# ── the export: the underlying change ledger (operator 2026-08-08) ────────────────────────


def _sheets(content: bytes) -> str:
    zf = zipfile.ZipFile(io.BytesIO(content))
    return "".join(zf.read(n).decode() for n in zf.namelist() if n.startswith("xl/worksheets/"))


def test_integrity_export_carries_the_change_ledger_and_logic_sheets() -> None:
    c = _client_with_pair()
    c.post("/target", data={"uid": "3", "next_url": "/"}, follow_redirects=False)
    r = c.get("/export/xlsx/integrity?a=0&b=1")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    workbook = zf.read("xl/workbook.xml").decode()
    assert "Change ledger" in workbook and "Logic changes" in workbook
    sheets = _sheets(r.content)
    # the ledger row for the duration cut: was / is-now / delta / % complete as columns
    assert "restore UID 1 duration (cut 3→5 wd)" in sheets
    assert ">5 wd<" in sheets and ">3 wd<" in sheets and ">-2 wd<" in sheets
    # the target effect columns carry the true figures (7 on target, 1 on project)
    assert "Effect on target UID 3 (Roof)" in sheets
    # the aggregate row and the logic sheet's named endpoints
    assert "ALL 2 MEASURED CHANGE(S) REVERTED TOGETHER" in sheets
    assert "removed in comparison" in sheets
    assert ">Pour<" in sheets and ">Roof<" in sheets


def test_integrity_export_without_pair_keeps_the_findings_only_shape() -> None:
    """A legacy call (no a/b) keeps the findings-only workbook byte-shape — one sheet."""
    c = _client_with_pair()
    r = c.get("/export/xlsx/integrity")
    assert r.status_code == 200
    workbook = zipfile.ZipFile(io.BytesIO(r.content)).read("xl/workbook.xml").decode()
    assert "Change ledger" not in workbook and "Logic changes" not in workbook
