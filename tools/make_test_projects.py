"""Generate the synthetic MSPDI verification battery (TP1-TP4) — docs/TEST-PROJECTS.md.

Four fictional, non-CUI test programs that exercise the surfaces the curated goldens
(Project2-Project5) cannot: ragged real-world actual times (TP1), a non-standard 4x10
calendar with holidays (TP2), hand-seeded DCMA violations with known counts (TP3), and
a five-snapshot version series with a deliberate manipulation (TP4 v1-v5).

Dates are computed with an MS-Project-faithful block calendar (e.g. 8:00-12:00 /
13:00-17:00), NOT the engine's single-block approximation, so MS Project re-derives the
same dates on import and never reflows the files. The committed copies live in
``tests/fixtures/test_projects/`` (the only schedule-format path allowed in git) and are
pinned to this generator by ``tests/test_projects/``.

Run:  python tools/make_test_projects.py [outdir]
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "test_projects"

# --- MSP-faithful block calendar ----------------------------------------------------


@dataclass(frozen=True)
class BlockCalendar:
    """Working time as MS Project models it: per-weekday minute-of-day blocks."""

    name: str
    blocks_by_weekday: dict[int, tuple[tuple[int, int], ...]]  # Mon=0..Sun=6
    holidays: tuple[dt.date, ...] = ()

    def is_workday(self, day: dt.date) -> bool:
        return day.weekday() in self.blocks_by_weekday and day not in self.holidays

    def blocks(self, day: dt.date) -> tuple[tuple[int, int], ...]:
        return self.blocks_by_weekday[day.weekday()] if self.is_workday(day) else ()

    def minutes_per_day(self) -> int:
        per = {sum(e - s for s, e in b) for b in self.blocks_by_weekday.values()}
        if len(per) != 1:
            raise ValueError("blocks must total the same minutes on every working day")
        return per.pop()

    def snap_start(self, moment: dt.datetime) -> dt.datetime:
        """The first working instant >= moment with working time remaining after it."""
        day, tod = moment.date(), moment.hour * 60 + moment.minute
        while True:
            for s, e in self.blocks(day):
                if tod < e:
                    return dt.datetime.combine(day, _tod(max(tod, s)))
            day, tod = day + dt.timedelta(days=1), 0

    def snap_finish(self, moment: dt.datetime) -> dt.datetime:
        """The last working instant <= moment with working time before it."""
        day, tod = moment.date(), moment.hour * 60 + moment.minute
        while True:
            for s, e in reversed(self.blocks(day)):
                if tod > s:
                    return dt.datetime.combine(day, _tod(min(tod, e)))
            day, tod = day - dt.timedelta(days=1), 24 * 60

    def add_work(self, moment: dt.datetime, minutes: int) -> dt.datetime:
        """The instant after consuming ``minutes`` of working time from ``moment``."""
        if minutes == 0:
            return moment
        cur = self.snap_start(moment)
        remaining = minutes
        while True:
            day, tod = cur.date(), cur.hour * 60 + cur.minute
            for s, e in self.blocks(day):
                if tod < e:
                    take = min(e - max(tod, s), remaining)
                    remaining -= take
                    cur = dt.datetime.combine(day, _tod(max(tod, s) + take))
                    if remaining == 0:
                        return cur
                    tod = cur.hour * 60 + cur.minute
            cur = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(0, 0))

    def sub_work(self, moment: dt.datetime, minutes: int) -> dt.datetime:
        """The instant ``minutes`` of working time before ``moment``."""
        if minutes == 0:
            return moment
        cur = self.snap_finish(moment)
        remaining = minutes
        while True:
            day, tod = cur.date(), cur.hour * 60 + cur.minute
            for s, e in reversed(self.blocks(day)):
                if tod > s:
                    take = min(min(tod, e) - s, remaining)
                    remaining -= take
                    cur = dt.datetime.combine(day, _tod(min(tod, e) - take))
                    if remaining == 0:
                        return cur
                    tod = cur.hour * 60 + cur.minute
            cur = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(23, 59))

    def work_between(self, start: dt.datetime, finish: dt.datetime) -> int:
        """Working minutes in [start, finish] — the actual duration of a ragged span."""
        total = 0
        day = start.date()
        while day <= finish.date():
            for s, e in self.blocks(day):
                lo = max(s, start.hour * 60 + start.minute) if day == start.date() else s
                hi = min(e, finish.hour * 60 + finish.minute) if day == finish.date() else e
                total += max(0, hi - lo)
            day += dt.timedelta(days=1)
        return total


def _tod(minutes: int) -> dt.time:
    return dt.time(minutes // 60, minutes % 60)


def _last_block_end(cal: BlockCalendar) -> int:
    """The latest end-of-working-time minute across the week (DefaultFinishTime)."""
    return max(e for blocks in cal.blocks_by_weekday.values() for _, e in blocks)


STANDARD = BlockCalendar(
    "Standard",
    {d: ((8 * 60, 12 * 60), (13 * 60, 17 * 60)) for d in range(5)},
)

# --- task / link / status specs ------------------------------------------------------

# MSPDI codes (importer-verified): link Type 0=FF 1=FS 2=SF 3=SS; ConstraintType
# 0=ASAP 2=MSO 3=MFO 4=SNET. Lags are working minutes here; emitted as tenths.
FS, SS, FF, SF = 1, 3, 0, 2
ASAP, MSO, MFO, SNET = 0, 2, 3, 4
DAY = 480  # standard-calendar working minutes (TP2 overrides per its calendar)


@dataclass
class T:
    uid: int
    name: str
    days: float = 0.0
    wbs: str = ""
    outline: int = 2
    summary: bool = False
    milestone: bool = False
    constraint: int = ASAP
    constraint_date: dt.datetime | None = None
    mso_at_logic: bool = False  # pin MSO exactly at the logic-derived start
    mfo_logic_offset_days: int | None = None  # pin MFO this many days before logic finish
    no_baseline: bool = False
    bl_finish_shift_days: int = 0  # deliberate baseline slip (TP4 manipulation cover-up)
    resources: tuple[int, ...] = ()
    # filled by the scheduler:
    start: dt.datetime = field(default=dt.datetime.min)
    finish: dt.datetime = field(default=dt.datetime.min)
    bl_start: dt.datetime | None = None
    bl_finish: dt.datetime | None = None
    bl_minutes: int = 0
    actual_start: dt.datetime | None = None
    actual_finish: dt.datetime | None = None
    percent: int = 0
    duration_minutes: int = 0


@dataclass(frozen=True)
class L:
    pred: int
    succ: int
    type: int = FS
    lag: int = 0  # working minutes (negative = lead)


@dataclass(frozen=True)
class St:
    """One task's actual history (replayed up to a data date for TP4)."""

    uid: int
    started: dt.datetime
    finished: dt.datetime | None = None
    percent: int = 100  # used while in progress (finished=None at the data date)


def _schedule(
    tasks: list[T],
    links: list[L],
    cal: BlockCalendar,
    project_start: dt.datetime,
    statuses: dict[int, St],
    *,
    minutes_per_day: int,
    baseline_pass: bool,
) -> None:
    """Forward-pass the network in spec order (specs are topologically ordered).

    The baseline pass ignores all statusing (the as-planned network); the current pass
    pins started tasks at their actual dates exactly as MS Project would."""
    by_uid = {t.uid: t for t in tasks}
    preds: dict[int, list[L]] = {t.uid: [] for t in tasks}
    for link in links:
        preds[link.succ].append(link)
    for t in tasks:
        if t.summary:
            continue
        dur = round(t.days * minutes_per_day)
        st = None if baseline_pass else statuses.get(t.uid)
        if st is not None:
            t.actual_start, t.actual_finish = st.started, st.finished
            t.percent = 100 if st.finished else st.percent
            t.start = st.started
            if st.finished is not None:
                t.finish = st.finished
                dur = cal.work_between(st.started, st.finished)
            else:
                t.finish = cal.add_work(cal.snap_start(st.started), dur)
        else:
            cands = [cal.snap_start(project_start)]
            for link in preds[t.uid]:
                p = by_uid[link.pred]
                lagged = (
                    cal.add_work(_anchor(p, link), link.lag)
                    if link.lag >= 0
                    else cal.sub_work(_anchor(p, link), -link.lag)
                )
                if link.type in (FS, SS):
                    cands.append(lagged if t.milestone else cal.snap_start(lagged))
                else:  # FF / SF constrain the finish; derive the start
                    cands.append(cal.sub_work(lagged, dur) if dur else lagged)
            if t.constraint == SNET and t.constraint_date is not None:
                cands.append(cal.snap_start(t.constraint_date))
            t.start = max(cands)
            if t.constraint == MSO:
                if t.mso_at_logic:
                    t.constraint_date = t.start
                assert t.constraint_date is not None
                t.start = t.constraint_date
            t.finish = cal.add_work(t.start, dur) if dur else t.start
            if t.constraint == MFO:
                if t.mfo_logic_offset_days is not None:
                    t.constraint_date = cal.sub_work(
                        t.finish, t.mfo_logic_offset_days * minutes_per_day
                    )
                assert t.constraint_date is not None
                t.finish = t.constraint_date
                t.start = cal.sub_work(t.finish, dur) if dur else t.finish
        if baseline_pass:
            t.bl_start, t.bl_finish, t.bl_minutes = t.start, t.finish, dur
        else:
            t.duration_minutes = dur
    _rollup(tasks, cal, baseline_pass=baseline_pass)


def _anchor(p: T, link: L) -> dt.datetime:
    """The predecessor instant a link measures from (FS/FF: finish; SS/SF: start)."""
    return p.finish if link.type in (FS, FF) else p.start


def _rollup(tasks: list[T], cal: BlockCalendar, *, baseline_pass: bool) -> None:
    """Summary rows span their children (MS Project recomputes these on import).

    Deepest-first (reverse file order): a parent summary's children include OTHER
    summaries — computing top-down read their placeholder dates and gave the UID-0
    project row a year-0001 baseline that MS Project rejected on import."""
    for i, t in reversed(list(enumerate(tasks))):
        if not t.summary:
            continue
        kids = []
        for k in tasks[i + 1 :]:
            if k.outline <= t.outline:
                break
            kids.append(k)
        if not kids:
            continue
        if baseline_pass:
            # summary children carry their baseline-pass dates in bl_* (their start/finish
            # fields are only filled by the current pass) — read the right axis
            starts = [k.bl_start for k in kids if k.bl_start is not None]
            finishes = [k.bl_finish for k in kids if k.bl_finish is not None]
            s, f = min(starts), max(finishes)
            t.bl_start, t.bl_finish = s, f
            t.bl_minutes = cal.work_between(s, f)
        else:
            s, f = min(k.start for k in kids), max(k.finish for k in kids)
            t.start, t.finish = s, f
            t.duration_minutes = cal.work_between(s, f)
            if any(k.actual_start for k in kids):
                t.actual_start = min(k.actual_start for k in kids if k.actual_start)
            if all(k.actual_finish or k.summary for k in kids):
                fins = [k.actual_finish for k in kids if k.actual_finish]
                if fins:
                    t.actual_finish = max(fins)
                    t.percent = 100


# --- MSPDI emission -------------------------------------------------------------------


def _iso(moment: dt.datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def _dur(minutes: int) -> str:
    return f"PT{minutes // 60}H{minutes % 60}M0S"


def _calendar_xml(cal: BlockCalendar) -> str:
    """One base calendar, UID 1, in MSPDI WeekDays + Exceptions form."""
    out = ["  <Calendars>", "    <Calendar>", "      <UID>1</UID>"]
    out += [f"      <Name>{escape(cal.name)}</Name>", "      <IsBaseCalendar>1</IsBaseCalendar>"]
    out += [
        "      <IsBaselineCalendar>0</IsBaselineCalendar>",
        "      <BaseCalendarUID>-1</BaseCalendarUID>",
    ]
    out.append("      <WeekDays>")
    for day_type in range(1, 8):  # MSPDI: 1=Sunday .. 7=Saturday
        weekday = (day_type + 5) % 7  # -> Python Mon=0..Sun=6
        blocks = cal.blocks_by_weekday.get(weekday, ())
        out.append("        <WeekDay>")
        out.append(f"          <DayType>{day_type}</DayType>")
        out.append(f"          <DayWorking>{1 if blocks else 0}</DayWorking>")
        if blocks:
            out.append("          <WorkingTimes>")
            for s, e in blocks:
                out.append("            <WorkingTime>")
                out.append(f"              <FromTime>{_tod(s).strftime('%H:%M:%S')}</FromTime>")
                out.append(f"              <ToTime>{_tod(e).strftime('%H:%M:%S')}</ToTime>")
                out.append("            </WorkingTime>")
            out.append("          </WorkingTimes>")
        out.append("        </WeekDay>")
    out.append("      </WeekDays>")
    if cal.holidays:
        out.append("      <Exceptions>")
        for holiday in cal.holidays:
            out.append("        <Exception>")
            out.append("          <EnteredByOccurrences>0</EnteredByOccurrences>")
            out.append("          <TimePeriod>")
            out.append(f"            <FromDate>{holiday.isoformat()}T00:00:00</FromDate>")
            out.append(f"            <ToDate>{holiday.isoformat()}T23:59:00</ToDate>")
            out.append("          </TimePeriod>")
            out.append("          <Occurrences>1</Occurrences>")
            out.append(f"          <Name>Holiday {holiday.isoformat()}</Name>")
            out.append("          <DayWorking>0</DayWorking>")
            out.append("        </Exception>")
        out.append("      </Exceptions>")
    out += ["    </Calendar>", "  </Calendars>"]
    return "\n".join(out)


def _task_xml(t: T, tid: int, links: list[L]) -> str:
    """One <Task> in MSPDI schema element order (MS Project's import is order-aware)."""
    rem = (
        0
        if t.percent == 100
        else round(t.duration_minutes * (100 - t.percent) / 100)
        if t.actual_start
        else None
    )
    out = ["    <Task>", f"      <UID>{t.uid}</UID>", f"      <ID>{tid}</ID>"]
    out.append(f"      <Name>{escape(t.name)}</Name>")
    # Active/Manual sit directly after Name in genuine MS Project exports — emitted at
    # the tail they are IGNORED and the user's "New Tasks: Manually Scheduled" default
    # takes over (the operator's TP1.mpp imported manual with dropped links).
    out += ["      <Active>1</Active>", "      <Manual>0</Manual>"]
    out += ["      <Type>0</Type>", "      <IsNull>0</IsNull>"]
    if t.wbs:
        out.append(f"      <WBS>{escape(t.wbs)}</WBS>")
        out.append(f"      <OutlineNumber>{escape(t.wbs)}</OutlineNumber>")
    out.append(f"      <OutlineLevel>{t.outline}</OutlineLevel>")
    out.append("      <Priority>500</Priority>")
    out.append(f"      <Start>{_iso(t.start)}</Start>")
    out.append(f"      <Finish>{_iso(t.finish)}</Finish>")
    out.append(f"      <Duration>{_dur(t.duration_minutes)}</Duration>")
    out.append("      <DurationFormat>7</DurationFormat>")
    out.append(f"      <Milestone>{1 if t.milestone else 0}</Milestone>")
    out.append(f"      <Summary>{1 if t.summary else 0}</Summary>")
    out.append(f"      <PercentComplete>{t.percent}</PercentComplete>")
    if t.actual_start is not None:
        out.append(f"      <ActualStart>{_iso(t.actual_start)}</ActualStart>")
    if t.actual_finish is not None:
        out.append(f"      <ActualFinish>{_iso(t.actual_finish)}</ActualFinish>")
    if rem is not None:
        out.append(f"      <RemainingDuration>{_dur(rem)}</RemainingDuration>")
    out.append(f"      <ConstraintType>{t.constraint}</ConstraintType>")
    if t.constraint_date is not None:
        out.append(f"      <ConstraintDate>{_iso(t.constraint_date)}</ConstraintDate>")
    for link in links:
        out.append("      <PredecessorLink>")
        out.append(f"        <PredecessorUID>{link.pred}</PredecessorUID>")
        out.append(f"        <Type>{link.type}</Type>")
        out.append("        <CrossProject>0</CrossProject>")
        out.append(f"        <LinkLag>{link.lag * 10}</LinkLag>")
        out.append("        <LagFormat>7</LagFormat>")
        out.append("      </PredecessorLink>")
    if not t.no_baseline and t.bl_start is not None and t.bl_finish is not None:
        shift = t.bl_finish_shift_days * DAY
        bl_finish = STANDARD.add_work(t.bl_finish, shift) if shift else t.bl_finish
        out.append("      <Baseline>")
        out.append("        <Number>0</Number>")
        out.append(f"        <Start>{_iso(t.bl_start)}</Start>")
        out.append(f"        <Finish>{_iso(bl_finish)}</Finish>")
        out.append(f"        <Duration>{_dur(t.bl_minutes)}</Duration>")
        out.append("        <DurationFormat>7</DurationFormat>")
        out.append("      </Baseline>")
    out.append("    </Task>")
    return "\n".join(out)


def _project_xml(
    *,
    name: str,
    title: str,
    cal: BlockCalendar,
    project_start: dt.datetime,
    status_date: dt.datetime | None,
    tasks: list[T],
    links: list[L],
    resources: dict[int, str] | None = None,
    assignments: list[tuple[int, int]] | None = None,  # (task UID, resource UID)
) -> str:
    links_by_succ: dict[int, list[L]] = {}
    for link in links:
        links_by_succ.setdefault(link.succ, []).append(link)
    per_day = cal.minutes_per_day()
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        "<!-- SYNTHETIC, NON-CUI VERIFICATION FIXTURE - generated by",
        "     tools/make_test_projects.py (see docs/TEST-PROJECTS.md). Fictional content;",
        "     contains no real schedule data. Do not hand-edit: regenerate instead. -->",
        '<Project xmlns="http://schemas.microsoft.com/project">',
        f"  <Name>{escape(name)}</Name>",
        f"  <Title>{escape(title)}</Title>",
        "  <ScheduleFromStart>1</ScheduleFromStart>",
        f"  <StartDate>{_iso(project_start)}</StartDate>",
        "  <CalendarUID>1</CalendarUID>",
        f"  <DefaultStartTime>{project_start.strftime('%H:%M:%S')}</DefaultStartTime>",
        "  <DefaultFinishTime>"
        + _tod(_last_block_end(cal)).strftime("%H:%M:%S")
        + "</DefaultFinishTime>",
        "  <MinutesPerDay>" + str(per_day) + "</MinutesPerDay>",
        f"  <MinutesPerWeek>{per_day * len(cal.blocks_by_weekday)}</MinutesPerWeek>",
        "  <DaysPerMonth>20</DaysPerMonth>",
        "  <HonorConstraints>1</HonorConstraints>",
    ]
    if status_date is not None:
        out.append(f"  <StatusDate>{_iso(status_date)}</StatusDate>")
    # imported tasks must never inherit a user's "New Tasks: Manually Scheduled" default
    out.append("  <NewTasksAreManual>0</NewTasksAreManual>")
    out.append(_calendar_xml(cal))
    out.append("  <Tasks>")
    for tid, t in enumerate(tasks):
        out.append(_task_xml(t, tid, links_by_succ.get(t.uid, [])))
    out.append("  </Tasks>")
    if resources:
        out.append("  <Resources>")
        for uid, rname in sorted(resources.items()):
            out.append("    <Resource>")
            out.append(f"      <UID>{uid}</UID>")
            out.append(f"      <ID>{uid}</ID>")
            out.append(f"      <Name>{escape(rname)}</Name>")
            out.append("      <Type>1</Type>")
            out.append("    </Resource>")
        out.append("  </Resources>")
    if assignments:
        out.append("  <Assignments>")
        for i, (task_uid, res_uid) in enumerate(assignments, start=1):
            out.append("    <Assignment>")
            out.append(f"      <UID>{i}</UID>")
            out.append(f"      <TaskUID>{task_uid}</TaskUID>")
            out.append(f"      <ResourceUID>{res_uid}</ResourceUID>")
            out.append("      <Units>1</Units>")
            out.append("    </Assignment>")
        out.append("  </Assignments>")
    out.append("</Project>")
    return "\n".join(out) + "\n"


# --- TP1: progressed schedule with ragged actual times --------------------------------


def tp1() -> tuple[str, str]:
    start = dt.datetime(2026, 1, 5, 8, 0)
    dd = dt.datetime(2026, 3, 31, 17, 0)
    tasks = [
        T(0, "TP1 - Riverside Community Library", outline=0, summary=True),
        T(1, "Design", wbs="1", outline=1, summary=True),
        T(11, "Notice to proceed", wbs="1.1", milestone=True),
        T(12, "Schematic design", days=10, wbs="1.2"),
        T(15, "Geotechnical survey", days=5, wbs="1.3"),
        T(13, "Design development", days=15, wbs="1.4"),
        T(16, "Interior design package", days=8, wbs="1.5"),
        T(14, "Permitting & approvals", days=35, wbs="1.6"),
        T(2, "Procurement", wbs="2", outline=1, summary=True),
        T(21, "Long-lead equipment procurement", days=45, wbs="2.1"),
        T(22, "Steel package fabrication", days=30, wbs="2.2"),
        T(3, "Construction", wbs="3", outline=1, summary=True),
        T(31, "Mobilization", days=5, wbs="3.1"),
        T(32, "Foundations", days=20, wbs="3.2", resources=(1,)),
        T(33, "Steel erection", days=15, wbs="3.3"),
        T(34, "Building envelope", days=25, wbs="3.4", resources=(1,)),
        T(35, "MEP rough-in", days=30, wbs="3.5", resources=(2,)),
        T(36, "Interior finishes", days=25, wbs="3.6"),
        T(39, "Elevator install & inspection", days=18, wbs="3.7"),
        T(37, "FF&E installation", days=10, wbs="3.8"),
        T(38, "Commissioning", days=10, wbs="3.9", resources=(3,)),
        T(4, "Closeout", wbs="4", outline=1, summary=True),
        T(41, "Punch list", days=10, wbs="4.1"),
        T(42, "Final inspections", days=5, wbs="4.2"),
        T(43, "Substantial completion", wbs="4.3", milestone=True),
        T(44, "Owner training", days=5, wbs="4.4"),
        T(45, "Closeout documentation", days=5, wbs="4.5"),
        T(46, "Occupancy", wbs="4.6", milestone=True),
    ]
    links = [
        L(11, 12),
        L(11, 15),
        L(12, 13),
        L(12, 16),
        L(13, 14),
        L(13, 21),
        L(13, 22, lag=5 * DAY),
        L(14, 31),
        L(31, 32),
        L(32, 33),
        L(22, 33),
        L(33, 34),
        L(33, 35, SS, lag=5 * DAY),
        L(34, 36),
        L(35, 36, FF, lag=10 * DAY),
        L(34, 39),
        L(21, 37),
        L(34, 37),
        L(35, 38),
        L(36, 38),
        L(37, 38),
        L(39, 38),
        L(38, 41),
        L(41, 42),
        L(42, 43),
        L(38, 44),
        L(44, 45),
        L(42, 45),
        L(43, 46),
        L(45, 46),
    ]
    # Ragged actual times are the point: 16:30/15:00/14:00 finishes and 9:30/10:00 starts
    # put minutes of "slack" on chains SSI displays at 0 days (the 4-vs-66 class).
    statuses = {
        11: St(11, dt.datetime(2026, 1, 5, 8, 0), dt.datetime(2026, 1, 5, 8, 0)),
        12: St(12, dt.datetime(2026, 1, 5, 8, 0), dt.datetime(2026, 1, 15, 16, 30)),
        15: St(15, dt.datetime(2026, 1, 5, 8, 0), dt.datetime(2026, 1, 9, 17, 0)),
        13: St(13, dt.datetime(2026, 1, 16, 9, 30), dt.datetime(2026, 2, 11, 15, 0)),
        16: St(16, dt.datetime(2026, 1, 16, 10, 0), dt.datetime(2026, 1, 26, 14, 0)),
        14: St(14, dt.datetime(2026, 2, 12, 9, 0), None, percent=60),
        21: St(21, dt.datetime(2026, 2, 12, 7, 0), None, percent=40),
        22: St(22, dt.datetime(2026, 2, 19, 10, 0), None, percent=30),
    }
    _schedule(tasks, links, STANDARD, start, {}, minutes_per_day=DAY, baseline_pass=True)
    _schedule(tasks, links, STANDARD, start, statuses, minutes_per_day=DAY, baseline_pass=False)
    return "TP1_Library_Progressed.xml", _project_xml(
        name="TP1_Library_Progressed.xml",
        title="TP1 - Riverside Community Library (progressed, ragged actuals)",
        cal=STANDARD,
        project_start=start,
        status_date=dd,
        tasks=tasks,
        links=links,
        resources={1: "GC Crew A", 2: "Electrical Sub", 3: "Commissioning Agent"},
        assignments=[(32, 1), (34, 1), (35, 2), (38, 3)],
    )


# --- TP2: 4x10 calendar + holidays, unprogressed --------------------------------------


def tp2() -> tuple[str, str]:
    cal = BlockCalendar(
        "4x10 Crew",
        {d: ((7 * 60, 12 * 60), (12 * 60 + 30, 17 * 60 + 30)) for d in range(4)},  # Mon-Thu
        holidays=(
            dt.date(2026, 5, 25),
            dt.date(2026, 6, 15),
            dt.date(2026, 7, 2),
            dt.date(2026, 9, 7),
        ),
    )
    day = cal.minutes_per_day()  # 600
    start = dt.datetime(2026, 4, 6, 7, 0)
    tasks = [
        T(0, "TP2 - Bridge Deck Rehabilitation", outline=0, summary=True),
        T(1, "Stage 1 - Eastbound", wbs="1", outline=1, summary=True),
        T(11, "Notice to proceed", wbs="1.1", milestone=True),
        T(12, "Demolition - EB deck", days=20, wbs="1.2"),
        T(13, "Deck repairs - EB", days=44, wbs="1.3"),  # exactly 44 days: NOT high duration
        T(14, "Overlay & cure - EB", days=45, wbs="1.4"),  # 45 days: the high-duration hit
        T(15, "Striping - EB", days=5, wbs="1.5"),
        T(16, "Expansion joint seals - EB", days=2, wbs="1.6"),
        T(2, "Stage 2 - Westbound", wbs="2", outline=1, summary=True),
        T(21, "Demolition - WB deck", days=17, wbs="2.1"),
        T(22, "Deck repairs - WB", days=36, wbs="2.2"),
        T(23, "Overlay & cure - WB", days=33, wbs="2.3"),
        T(24, "Striping - WB", days=5, wbs="2.4"),
        T(3, "Ancillary", wbs="3", outline=1, summary=True),
        T(31, "Barrier replacement", days=25, wbs="3.1"),
        T(32, "Drainage upgrades", days=18, wbs="3.2"),
        T(33, "Permanent signage", days=10, wbs="3.3"),
        T(34, "Work-zone traffic control (continuous)", days=86, wbs="3.4"),
        T(41, "Final inspection", days=5, wbs="3.5"),
        T(42, "Reopen to traffic", wbs="3.6", milestone=True),
    ]
    links = [
        L(11, 12),
        L(12, 13),
        L(13, 14),
        L(14, 15),
        L(14, 16),
        L(12, 21),
        L(21, 22),
        L(22, 23),
        L(23, 24),
        L(12, 31),
        L(12, 32),
        L(12, 33),
        L(12, 34),
        L(15, 41),
        L(16, 41),
        L(24, 41),
        L(31, 41),
        L(32, 41),
        L(33, 41),
        L(34, 41),
        L(41, 42),
    ]
    _schedule(tasks, links, cal, start, {}, minutes_per_day=day, baseline_pass=True)
    _schedule(tasks, links, cal, start, {}, minutes_per_day=day, baseline_pass=False)
    return "TP2_Bridge_4x10_Calendar.xml", _project_xml(
        name="TP2_Bridge_4x10_Calendar.xml",
        title="TP2 - Bridge Deck Rehabilitation (4x10 calendar + holidays)",
        cal=cal,
        project_start=start,
        status_date=start,
        tasks=tasks,
        links=links,
    )


# --- TP3: hand-seeded DCMA violations with known counts --------------------------------


def tp3() -> tuple[str, str]:
    start = dt.datetime(2026, 2, 2, 8, 0)
    dd = dt.datetime(2026, 4, 30, 17, 0)
    tasks = [
        T(0, "TP3 - Coastal Plant Outage Turnaround", outline=0, summary=True),
        T(1, "Pre-outage", wbs="1", outline=1, summary=True),
        T(11, "Outage readiness review", wbs="1.1", milestone=True),
        T(12, "Scaffolding & insulation removal", days=10, wbs="1.2"),
        T(13, "Permits & isolation plans", days=15, wbs="1.3"),
        T(14, "Pre-fabricate spool pieces", days=20, wbs="1.4"),  # missing predecessor
        T(15, "Rental equipment staging", days=5, wbs="1.5"),  # missing predecessor
        T(16, "Welder qualification", days=5, wbs="1.6"),  # missing predecessor
        T(34, "Craft onboarding & badging", days=8, wbs="1.7", no_baseline=True),
        T(2, "Execution", wbs="2", outline=1, summary=True),
        T(21, "Unit shutdown & cooldown", days=5, wbs="2.1"),
        T(22, "Exchanger bundle pulls", days=10, wbs="2.2"),
        T(23, "Tube bundle retube", days=50, wbs="2.3"),  # high duration #1
        T(24, "Tower internals replacement", days=60, wbs="2.4", constraint=MSO, mso_at_logic=True),
        T(25, "Piping demolition & replacement", days=40, wbs="2.5"),
        T(26, "Valve overhaul program", days=25, wbs="2.6"),
        T(27, "Instrumentation & controls upgrade", days=30, wbs="2.7"),
        T(28, "Hydrotest & reinstatement", days=10, wbs="2.8"),
        T(29, "Reinstate insulation & scaffolding", days=15, wbs="2.9"),
        T(31, "Spent catalyst disposal", days=5, wbs="2.10"),  # missing successor
        T(32, "Warehouse inventory reconciliation", days=10, wbs="2.11"),  # missing successor
        T(3, "Closeout", wbs="3", outline=1, summary=True),
        T(
            41,
            "Startup & performance test",
            days=10,
            wbs="3.1",
            constraint=MFO,
            mfo_logic_offset_days=3,
        ),
        T(33, "Demobilize rental equipment", days=3, wbs="3.2"),
        T(42, "Outage complete", wbs="3.3", milestone=True),
    ]
    links = [
        L(11, 12),
        L(11, 13),
        L(11, 34),
        L(12, 21),
        L(13, 21),
        L(21, 22),
        L(34, 22),
        L(22, 23),
        L(16, 23),
        L(21, 24, lag=2 * DAY),  # lag #1
        L(21, 25, SS, lag=3 * DAY),  # SS #1, lag #2
        L(14, 25),
        L(25, 26, SS, lag=5 * DAY),  # SS #2, lag #3
        L(23, 27, SS),  # SS #3
        L(25, 28, FF),  # FF #1
        L(24, 28, FF),  # FF #2
        L(22, 28),
        L(26, 29, lag=-1 * DAY),  # lead #1
        L(27, 29, lag=-2 * DAY),  # lead #2
        L(28, 29),
        L(29, 41),
        L(41, 33, SF),  # SF #1
        L(41, 42),
        L(21, 31),
        L(15, 32),
    ]
    statuses = {
        11: St(11, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 2, 8, 0)),
        12: St(12, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 13, 17, 0)),
        13: St(13, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 20, 17, 0)),
        # in progress so the missing-predecessor seed registers (DCMA logic counts
        # incomplete work only — a completed dangling task falls out of the population):
        14: St(14, dt.datetime(2026, 2, 2, 8, 0), None, percent=85),
        15: St(15, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 6, 17, 0)),
        16: St(16, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 6, 17, 0)),
        34: St(34, dt.datetime(2026, 2, 2, 8, 0), dt.datetime(2026, 2, 11, 17, 0)),
        21: St(21, dt.datetime(2026, 2, 23, 8, 0), dt.datetime(2026, 2, 27, 17, 0)),
        # finished two working days late vs its baseline (completion-performance seed):
        22: St(22, dt.datetime(2026, 3, 2, 8, 0), dt.datetime(2026, 3, 17, 17, 0)),
        # actual finish AFTER the data date: the invalid-actual-date seed (DCMA9):
        31: St(31, dt.datetime(2026, 3, 2, 8, 0), dt.datetime(2026, 5, 5, 17, 0)),
        23: St(23, dt.datetime(2026, 3, 18, 8, 0), None, percent=30),
        24: St(24, dt.datetime(2026, 3, 4, 8, 0), None, percent=25),
        27: St(27, dt.datetime(2026, 4, 6, 8, 0), None, percent=20),
        # 32 stays unstarted with a forecast wholly before the data date (DCMA9 forecast).
    }
    _schedule(tasks, links, STANDARD, start, {}, minutes_per_day=DAY, baseline_pass=True)
    _schedule(tasks, links, STANDARD, start, statuses, minutes_per_day=DAY, baseline_pass=False)
    return "TP3_Outage_DCMA_Seeded.xml", _project_xml(
        name="TP3_Outage_DCMA_Seeded.xml",
        title="TP3 - Coastal Plant Outage Turnaround (seeded DCMA violations)",
        cal=STANDARD,
        project_start=start,
        status_date=dd,
        tasks=tasks,
        links=links,
    )


# --- TP4: five-snapshot version series with a deliberate manipulation ------------------


def _tp4_tasks() -> list[T]:
    return [
        T(0, "TP4 - Data Center Fit-Out", outline=0, summary=True),
        T(11, "Notice to proceed", wbs="1", outline=1, milestone=True),
        T(12, "Design & permits", days=15, wbs="2", outline=1),
        T(13, "Demolition & shell prep", days=10, wbs="3", outline=1),
        T(14, "Electrical rough-in", days=20, wbs="4", outline=1),
        T(15, "Mechanical / HVAC rough-in", days=25, wbs="5", outline=1),
        T(16, "Fire suppression", days=15, wbs="6", outline=1),
        T(19, "Generator & switchgear procurement", days=20, wbs="7", outline=1),
        T(17, "Raised floor & containment", days=15, wbs="8", outline=1),
        T(18, "Power distribution units", days=10, wbs="9", outline=1),
        T(21, "UPS & battery installation", days=15, wbs="10", outline=1),
        T(22, "Network cabling", days=20, wbs="11", outline=1),
        T(23, "CRAC units set & pipe", days=20, wbs="12", outline=1),
        T(24, "Commissioning L1-L3", days=15, wbs="13", outline=1),
        T(25, "Integrated systems test", days=10, wbs="14", outline=1),
        T(26, "Substantial completion", wbs="15", outline=1, milestone=True),
    ]


_TP4_LINKS = [
    L(11, 12),
    L(12, 13),
    L(12, 19),
    L(13, 14),
    L(13, 15),
    L(13, 16),
    L(14, 17),
    L(15, 17),
    L(14, 18),
    L(18, 21),
    L(19, 21),
    L(17, 22),
    L(15, 23),
    L(17, 23),
    L(16, 24),
    L(21, 24),
    L(22, 24),
    L(23, 24),
    L(24, 25),
    L(25, 26),
]

#: The program's true actual history: (uid, actual start, actual finish). Each snapshot
#: replays the events known at its data date; in-progress percents are estimated linearly.
_TP4_HISTORY: list[tuple[int, dt.datetime, dt.datetime | None]] = [
    (11, dt.datetime(2026, 1, 5, 8, 0), dt.datetime(2026, 1, 5, 8, 0)),
    (12, dt.datetime(2026, 1, 5, 8, 0), dt.datetime(2026, 1, 23, 17, 0)),
    (13, dt.datetime(2026, 1, 26, 8, 0), dt.datetime(2026, 2, 6, 17, 0)),
    (14, dt.datetime(2026, 2, 9, 8, 0), dt.datetime(2026, 3, 10, 17, 0)),  # 2 days late
    (15, dt.datetime(2026, 2, 9, 8, 0), dt.datetime(2026, 4, 3, 17, 0)),  # 15 days late
    (16, dt.datetime(2026, 2, 9, 8, 0), dt.datetime(2026, 2, 27, 17, 0)),
    (19, dt.datetime(2026, 2, 2, 8, 0), None),  # stalled in-progress; erased in v4
    (18, dt.datetime(2026, 3, 11, 8, 0), dt.datetime(2026, 3, 24, 17, 0)),
    (17, dt.datetime(2026, 4, 6, 8, 0), dt.datetime(2026, 4, 24, 17, 0)),
    (22, dt.datetime(2026, 4, 27, 8, 0), None),
    (23, dt.datetime(2026, 4, 27, 8, 0), None),
]

#: Estimated percent complete for tasks in progress at each snapshot.
_TP4_PERCENTS: dict[int, dict[int, int]] = {
    2: {19: 25},
    3: {15: 50, 19: 25},
    4: {17: 40},
    5: {22: 50, 23: 30, 19: 40},
}


def tp4(version: int) -> tuple[str, str]:
    dds = {
        1: dt.datetime(2026, 1, 30, 17, 0),
        2: dt.datetime(2026, 2, 27, 17, 0),
        3: dt.datetime(2026, 3, 31, 17, 0),
        4: dt.datetime(2026, 4, 30, 17, 0),
        5: dt.datetime(2026, 5, 29, 17, 0),
    }
    dd = dds[version]
    start = dt.datetime(2026, 1, 5, 8, 0)
    tasks = _tp4_tasks()
    statuses: dict[int, St] = {}
    for uid, a_start, a_finish in _TP4_HISTORY:
        if a_start > dd:
            continue
        if uid == 19 and version == 4:
            continue  # THE MANIPULATION: 19's recorded actual start vanishes in v4
        if a_finish is not None and a_finish <= dd:
            statuses[uid] = St(uid, a_start, a_finish)
        else:
            pc = _TP4_PERCENTS.get(version, {}).get(uid, 10)
            statuses[uid] = St(uid, a_start, None, percent=pc)
    if version == 5:  # the honest restart after the v4 erasure
        statuses[19] = St(19, dt.datetime(2026, 4, 27, 8, 0), None, percent=40)
    for t in tasks:
        if t.uid == 19 and version >= 4:
            t.bl_finish_shift_days = 45  # the cover-up: 19's baseline quietly slips ~2 months
    _schedule(tasks, _TP4_LINKS, STANDARD, start, {}, minutes_per_day=DAY, baseline_pass=True)
    _schedule(
        tasks, _TP4_LINKS, STANDARD, start, statuses, minutes_per_day=DAY, baseline_pass=False
    )
    fname = f"TP4_DataCenter_v{version}.xml"
    return fname, _project_xml(
        name=fname,
        title=f"TP4 - Data Center Fit-Out (snapshot v{version})",
        cal=STANDARD,
        project_start=start,
        status_date=dd,
        tasks=tasks,
        links=_TP4_LINKS,
    )


# --- entry point -----------------------------------------------------------------------


def generate_all() -> dict[str, str]:
    """Every battery file as {filename: xml_text} (deterministic)."""
    files = dict([tp1(), tp2(), tp3()])
    for version in range(1, 6):
        name, xml = tp4(version)
        files[name] = xml
    return files


def main(argv: list[str]) -> int:
    outdir = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)
    for name, xml in generate_all().items():
        (outdir / name).write_text(xml, encoding="utf-8")
        print(f"wrote {outdir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
