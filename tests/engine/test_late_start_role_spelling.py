"""A late START is a start-role instant on the WALL path too (R-69, ADR-XXXX).

``_retreat_wall`` lands a block-exact retreat on the END of a working block, because
:func:`_tod_at_worked` does. MS Project writes a late start at the START of the NEXT block:
Hard_File UID 178's stored LateStart is 08-04 **13:00** where the engine read **12:00** -- the
same working minute on the task's own axis, spelled the other way.

This is ADR-0348's day-boundary rule and ADR-0523's segment-boundary rule applied to the one
direction that never got it. The offset path already carries both spellings
(:func:`offset_to_datetime` vs :func:`offset_to_start_datetime`); the backward wall path carried
only the finish one (:func:`_snap_back_to_working` is explicitly documented as the FINISH role).

**The blocker the register recorded is gone.** R-69 was priced as "NOT a one-line fix" because
"the contiguous projection of the 13:00 form reads 300 where 12:00 reads 240, so every
project-calendar predecessor would inherit the lunch hour as float". ADR-0523 made
``datetime_to_offset`` -- and with it ``_wall_to_offset`` -- segment-aware, so both spellings now
project to the SAME offset and no predecessor inherits anything. That claim is pinned below, so
the day it stops being true this file goes red rather than the arithmetic going quietly wrong.

**The rule is role-based, and it has NO duration exception** -- a claim that cost a refuted
plan to establish. Measured from the files' own stored values over the 44-file corpus (an oracle
independent of this engine): MS Project spells an internal-boundary late start with the LATER form
on 754 of 780 NON-MILESTONE instants (96.7 %) and a late finish with the EARLIER form on 880 of 911
(96.6 %), while a MILESTONE's single late instant splits 58 / 54 between the two. That split looked
like a reason to exclude zero-duration tasks, and a mutation test refuted it: the 58 / 54 population
is instants the FAST path carries (``_carried_late_instant``), which this seam never reaches. Of the
zero-duration instants it does reach, 5 of 5 with a determinate stored answer take the later form,
and the guard broke all five to save none. The general milestone ambiguity remains a NAMED residual
of ADR-0523, not a rule invented here.

Measured pristine -> this tree over the 44-file corpus (22,105 activities): wall late-start
instants exact 1,628 -> 1,698, wall late-finish instants exact 1,728 -> 1,755, stored Total Slack
exact 10,568 -> 10,572. Per activity, 70 late starts and 27 late finishes moved TOWARD MS Project's
stored instant and **none moved away**; no early instant and no Critical flag moved at all.
UID 379's total float 17,521 -> 17,581 lands exactly on the stored 175,810 tenths -- the lunch hour
had been float. Hard_File UID 147's carried Saturday instant (ADR-0510's named residual, registered
to this row) comes right for free: it is 178's late start less 72 ELAPSED hours, so re-spelling 178
carries it to the stored Saturday 13:00 without the milestone itself being re-spelled.
"""

from __future__ import annotations

import collections
import datetime as dt
import gzip
import pathlib
import xml.etree.ElementTree as ET

from schedule_forensics.engine import cpm
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule

#: 08:00-12:00 + 13:00-17:00 -- the MS Project Standard day, with a 12:00-13:00 lunch.
GAPPED = Calendar(day_segments=((480, 720), (780, 1020)))
#: the same 480-minute day with NO declared segments (one contiguous block).
PLAIN = Calendar()
MON = dt.date(2025, 1, 6)  # a Monday
SAT = dt.date(2025, 1, 11)  # a Saturday -- non-working on both calendars above

NS = "{http://schemas.microsoft.com/project}"
_GOLDEN_ROOT = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "golden"
#: ELEVEN of the fifteen goldens are gzipped, so a plain ``*.xml`` glob sees four and looks
#: exhaustive. Every population below is asserted non-empty for the same reason.
_GOLDENS = tuple(
    sorted(list(_GOLDEN_ROOT.rglob("*.mspdi.xml")) + list(_GOLDEN_ROOT.rglob("*.mspdi.xml.gz")))
)


def _text(path: pathlib.Path) -> str:
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode("utf-8")
    return path.read_text(encoding="utf-8")


def _stored(path: pathlib.Path) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for node in ET.fromstring(_text(path)).iter(NS + "Task"):
        uid = node.findtext(NS + "UID")
        if uid is None:
            continue
        rec = {}
        for f in ("LateStart", "LateFinish", "TotalSlack", "Milestone", "Start"):
            v = node.findtext(NS + f)
            if v:
                rec[f] = v
        out[int(uid)] = rec
    return out


def _hard_file() -> tuple[Schedule, object, dict[int, dict[str, str]]]:
    path = next(p for p in _GOLDENS if p.name == "Hard_File.mspdi.xml.gz")
    sch = parse_mspdi_text(_text(path))
    return sch, compute_cpm(sch), _stored(path)


def _boundary_forms(sch: Schedule, tod0: int, task) -> dict[int, str]:
    """Minute-of-day -> which spelling it is, for the task's own calendar's INTERNAL
    boundaries. The day's first start and last end are not internal boundaries."""
    by_uid = {c.uid: c for c in [sch.calendar, *sch.calendars]}
    cal = by_uid.get(task.calendar_uid) or sch.calendar
    segs = cpm._ruler(cal).segments(tod0)
    forms: dict[int, str] = {}
    for i in range(len(segs) - 1):
        forms[segs[i][1]] = "earlier"
        forms[segs[i + 1][0]] = "later"
    return forms


# --------------------------------------------------------------------------- the helper


def test_the_start_role_respells_an_internal_block_boundary() -> None:
    """12:00 and 13:00 are both 240 minutes worked; a START takes the later spelling."""
    snap = cpm._snap_start_role
    got = snap(dt.datetime.combine(MON, dt.time(12, 0)), GAPPED, 480)
    assert got == dt.datetime.combine(MON, dt.time(13, 0))


def test_the_start_role_leaves_an_instant_away_from_a_boundary_alone() -> None:
    """CONTROL: only the block-exact case differs; away from it the spellings agree."""
    snap = cpm._snap_start_role
    for hh, mm in ((10, 0), (11, 59), (13, 1), (15, 30)):
        at = dt.datetime.combine(MON, dt.time(hh, mm))
        assert snap(at, GAPPED, 480) == at, (hh, mm)


def test_the_start_role_leaves_the_day_edges_alone() -> None:
    """CONTROL: the day's first start and last end are NOT internal boundaries -- re-spelling
    them would move the instant to another DAY, which is ADR-0348's rule, not this one."""
    snap = cpm._snap_start_role
    for hh in (8, 17):
        at = dt.datetime.combine(MON, dt.time(hh, 0))
        assert snap(at, GAPPED, 480) == at, hh


def test_an_undeclared_calendar_has_no_internal_boundary_to_respell() -> None:
    """CONTROL: the segment-aware family fires only when the file DECLARED segments
    (ADR-0523's first rule) -- a single contiguous block has no internal boundary at all."""
    snap = cpm._snap_start_role
    at = dt.datetime.combine(MON, dt.time(12, 0))
    assert snap(at, PLAIN, 480) == at


def test_a_non_working_day_is_not_respelled() -> None:
    """CONTROL: an instant the calendar does not work has no block to be on the end of.
    Hard_File UID 147's stored LateStart is a SATURDAY 13:00 (ADR-0510) -- it is carried by
    its driver, never manufactured here."""
    snap = cpm._snap_start_role
    at = dt.datetime.combine(SAT, dt.time(12, 0))
    assert snap(at, GAPPED, 480) == at


def test_the_projection_cannot_tell_the_two_spellings_apart() -> None:
    """The blocker R-69 was priced on. ADR-0523 made the wall->int projection segment-aware,
    so re-spelling a late start moves NO offset and no predecessor inherits the gap as float.
    The register predicted 240 vs 300; both now read the same working minute."""
    ps = dt.datetime.combine(MON, dt.time(8, 0))
    noon = dt.datetime.combine(MON, dt.time(12, 0))
    one = dt.datetime.combine(MON, dt.time(13, 0))
    assert cpm._wall_to_offset(ps, noon, GAPPED) == cpm._wall_to_offset(ps, one, GAPPED) == 240
    assert cpm.datetime_to_offset(ps, noon, GAPPED) == cpm.datetime_to_offset(ps, one, GAPPED)


# ------------------------------------------------------- MS Project's own convention


def test_ms_project_spells_a_non_milestone_late_date_by_its_ROLE() -> None:
    """The rule's oracle, read from the files' own stored values -- independent of this
    engine, which is the point: a fixture generated by the rule under test cannot validate it.

    A late START takes the later spelling, a late FINISH the earlier one."""
    counts: collections.Counter[str] = collections.Counter()
    for path in _GOLDENS:
        sch = parse_mspdi_text(_text(path))
        stored = _stored(path)
        tod0 = sch.project_start.hour * 60 + sch.project_start.minute
        for task in sch.tasks:
            if task.is_summary or not task.is_active:
                continue
            forms = _boundary_forms(sch, tod0, task)
            if not forms:
                continue
            rec = stored.get(task.unique_id, {})
            kind = "milestone" if rec.get("Milestone") == "1" else "task"
            by_uid = {c.uid: c for c in [sch.calendar, *sch.calendars]}
            cal = by_uid.get(task.calendar_uid) or sch.calendar
            for field in ("LateStart", "LateFinish"):
                raw = rec.get(field)
                if not raw:
                    continue
                at = dt.datetime.fromisoformat(raw)
                if not cpm._ruler(cal).is_worked(at.date()):
                    continue
                form = forms.get(at.hour * 60 + at.minute)
                if form is not None:
                    counts[f"{field}:{kind}:{form}"] += 1
    # population guard -- a vacuous census passes forever
    assert counts["LateStart:task:later"] + counts["LateStart:task:earlier"] == 382
    assert counts["LateFinish:task:later"] + counts["LateFinish:task:earlier"] == 440
    assert counts["LateStart:task:later"] == 366  # 95.8 % take the START spelling
    assert counts["LateStart:task:earlier"] == 16
    assert counts["LateFinish:task:earlier"] == 426  # 96.8 % take the FINISH spelling
    assert counts["LateFinish:task:later"] == 14
    # ...and a MILESTONE's single instant has no dominant spelling at all, which is why the
    # rule below is scoped to duration > 0. This is a RESIDUAL, pinned so it cannot drift
    # into an invented rule.
    assert counts["LateStart:milestone:earlier"] == 29
    assert counts["LateStart:milestone:later"] == 25


# ------------------------------------------------------------------ the engine's answer


def test_the_late_start_chain_agrees_with_the_stored_instant() -> None:
    """R-69's named witness and its chain. Pristine reads 12:00 for every one of these."""
    _sch, res, stored = _hard_file()
    for uid in (178, 179, 180, 188, 200, 321, 403, 36, 144):
        got = res.timing(uid).late_start_wall
        want = dt.datetime.fromisoformat(stored[uid]["LateStart"])
        assert got == want, f"UID {uid}: {got} != stored {want}"


def test_the_carried_milestone_instant_follows_its_re_spelled_driver() -> None:
    """ADR-0510 named UID 147's carried Saturday instant as R-69's residual: it is 178's late
    start less 72 ELAPSED hours, so it inherited 178's spelling. The milestone itself is NOT
    re-spelled -- its driver is."""
    _sch, res, stored = _hard_file()
    got = res.timing(147).late_start_wall
    assert (
        got == dt.datetime(2026, 8, 1, 13, 0) == dt.datetime.fromisoformat(stored[147]["LateStart"])
    )
    assert got.weekday() == 5, "the carried instant is a Saturday -- off the axis entirely"


def test_a_zero_duration_wall_path_task_takes_the_start_form_too() -> None:
    """There is NO duration exception, and this test is why.

    The rule was first written with a ``duration > 0`` guard, on the reading that a milestone's
    one instant carries both roles and the corpus splits 58 / 54 between the spellings. A
    mutation test refuted it: the 58 / 54 population is instants carried by the FAST path
    (``_carried_late_instant``), which this seam never reaches. Of the zero-duration instants
    it DOES reach, every one with a determinate stored answer takes the later form -- 5 of 5,
    UID 5288 across the Large_Test_File2 family -- and the guard broke all five to save none."""
    path = next(p for p in _GOLDENS if p.name == "Large_Test_File2.mspdi.xml.gz")
    sch = parse_mspdi_text(_text(path))
    res = compute_cpm(sch)
    stored = _stored(path)
    task = next(t for t in sch.tasks if t.unique_id == 5288)
    assert task.duration_minutes == 0, "the witness must be zero-duration or it proves nothing"
    got = res.timing(5288).late_start_wall
    assert got == dt.datetime(2026, 5, 20, 13, 0)
    assert got == dt.datetime.fromisoformat(stored[5288]["LateStart"])


def test_a_carried_fast_path_milestone_is_not_reached_by_this_seam() -> None:
    """CONTROL: these seven Hard_File milestones are stored at 12:00 and take their instant
    from the fast path's carried-late rule (ADR-0510), not from the wall retreat. They must be
    exactly where they were -- if this seam ever starts moving them, the 58 / 54 residual
    becomes live and this rule needs re-deciding."""
    _sch, res, stored = _hard_file()
    for uid in (155, 388, 404, 405, 406, 407, 411):
        got = res.timing(uid).late_start_wall
        want = dt.datetime.fromisoformat(stored[uid]["LateStart"])
        assert got == want == dt.datetime(2026, 11, 5, 12, 0), f"UID {uid}: {got}"


def test_the_late_finish_keeps_the_finish_form() -> None:
    """The ROLE half of the rule: only the START is re-spelled. MS Project writes a
    non-milestone late finish with the EARLIER form on 426 of 440 golden instants, and
    ``_snap_back_to_working`` is already documented as the finish role. Applying the start
    form to ``lf_w`` as well breaks 52 already-exact late finishes across the corpus --
    Hard_File UID 189 is one of them."""
    _sch, res, stored = _hard_file()
    got = res.timing(189).late_finish_wall
    assert got == dt.datetime(2026, 8, 5, 12, 0)
    assert got == dt.datetime.fromisoformat(stored[189]["LateFinish"])


def test_the_lunch_hour_is_not_counted_as_float() -> None:
    """The register's mechanism, measured where it actually bites: UID 379's total float was
    one lunch hour long, and lands on MS Project's stored figure once the spelling is right."""
    _sch, res, stored = _hard_file()
    assert res.timing(379).total_float == 17581
    assert int(stored[379]["TotalSlack"]) == 175810  # tenths of a minute


def test_no_early_instant_moves() -> None:
    """CONTROL: this is a BACKWARD-pass spelling. The forward pass must be untouched -- across
    the 44-file corpus not one early instant changed."""
    _sch, res, stored = _hard_file()
    assert res.timing(178).early_start_wall == dt.datetime(2026, 8, 3, 17, 0)
    assert res.timing(379).early_start_wall == dt.datetime(2026, 8, 18, 13, 0)
    for uid in (178, 379):
        assert res.timing(uid).early_start_wall == dt.datetime.fromisoformat(stored[uid]["Start"])
