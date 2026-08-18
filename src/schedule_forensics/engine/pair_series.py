"""The consecutive-pair comparison series — every version compared to the one before it.

**The defect this closes.** Manipulation is a *diff* signal: it only exists between two snapshots.
Every cross-version consumer therefore had to pick a pair, and each of them picked the same one —
the newest two. On a 32-version workbook that meant 1 of 31 available comparisons was ever made,
and the other 30 updates were never diffed at all. The Ask-the-AI fact base inherited that: asked
"across these 32 schedules, is there a pattern of manipulation?", the evidence held signals from
the final update only, plus — worse — an affirmative *negative* ("No incomplete activity on the
critical path had its duration shortened between v31 and v32") whose one-pair scope the reader
could not see. A duration cut in update 4 and another in update 9 left no trace anywhere.

:func:`compute_pairwise_series` walks the whole workbook the way a forensic scheduler does:
oldest to newest, **two at a time**, running the full manipulation detector on every consecutive
pair. The result is a series of :class:`PairStep` rows, one per update, each carrying that
update's cited signals and what the computed finish did across it.

**Recurrence is the forensic point, and it is arithmetic, not judgement.** One duration cut is an
event; the same signal in 24 of 31 updates is a pattern, and a pattern is what distinguishes
routine re-planning from a schedule being managed to a date. :attr:`PairwiseSeries.recurrence`
states, per signal type, how many steps carry it, how long its longest unbroken run is, and how
many findings it accounts for — mechanical counts a reader can re-derive from the step rows. It
draws no conclusion about intent; the tool never asserts one.

**Law 2 ("—" never 0).** A pair that cannot be compared — either version's network unsolvable —
is recorded in :attr:`PairwiseSeries.uncomparable` **by name** and is never counted as a step with
zero signals. "We could not look" and "we looked and found nothing" are different findings, and
collapsing them would be the same class of defect this module exists to close.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from schedule_forensics.engine.cpm import CPMError, CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.engine.trend import order_versions
from schedule_forensics.model.schedule import Schedule


def _label(schedule: Schedule) -> str:
    return schedule.source_file or schedule.name


@dataclass(frozen=True)
class PairStep:
    """One consecutive-version comparison — the unit of "two at a time"."""

    index: int  # 1-based, oldest step first
    prior_label: str
    current_label: str
    prior_date: dt.date | None  # the prior version's data date
    current_date: dt.date | None
    findings: tuple[Finding, ...]  # every manipulation signal this update fired
    prior_finish: dt.date | None  # each side's schedule-logic (CPM) finish
    current_finish: dt.date | None

    @property
    def label(self) -> str:
        return f"{self.prior_label} → {self.current_label}"

    @property
    def signals(self) -> int:
        return len(self.findings)

    @property
    def finish_movement_days(self) -> int | None:
        """Calendar days the computed finish moved across this one update. Positive = later.
        ``None`` when either side has no solved finish — never 0 (Law 2)."""
        if self.prior_finish is None or self.current_finish is None:
            return None
        return (self.current_finish - self.prior_finish).days

    @property
    def signal_ids(self) -> frozenset[str]:
        """The distinct manipulation ``metric_id``s this step fired."""
        return frozenset(f.metric_id for f in self.findings)


@dataclass(frozen=True)
class SignalRecurrence:
    """How persistently ONE manipulation signal recurs across the series."""

    metric_id: str
    title: str  # the signal's own wording, taken from a finding that carries it
    steps_present: int  # how many consecutive-pair steps fired it
    total_findings: int  # how many findings it accounts for across the whole series
    longest_run: int  # longest unbroken run of consecutive steps firing it
    first_step: int  # 1-based index of the first step firing it
    last_step: int


@dataclass(frozen=True)
class PairwiseSeries:
    """Every consecutive comparison in the workbook, oldest step first."""

    steps: tuple[PairStep, ...]
    #: Pairs that could NOT be compared, named — an unsolvable network is not "no signals".
    uncomparable: tuple[str, ...] = ()
    #: Versions the walk was given. NOT ``len(steps) + 1``: an uncomparable pair removes a step
    #: without removing the versions, and deriving the count from the steps made a 4-version
    #: workbook with one unsolvable file report "all 2 loaded version(s) were compared".
    versions: int = 0

    @property
    def total_signals(self) -> int:
        return sum(s.signals for s in self.steps)

    @property
    def steps_with_signals(self) -> int:
        return sum(1 for s in self.steps if s.findings)

    @property
    def recurrence(self) -> tuple[SignalRecurrence, ...]:
        """Per signal type, how widely it recurs — most-recurrent first, then most findings.

        This is the series' answer to "is this a pattern?": a metric present in 1 step of 31 and
        one present in 24 are different findings, and the difference is countable.
        """
        titles: dict[str, str] = {}
        present: dict[str, list[int]] = {}
        totals: dict[str, int] = {}
        for step in self.steps:
            for finding in step.findings:
                titles.setdefault(finding.metric_id, finding.title)
                totals[finding.metric_id] = totals.get(finding.metric_id, 0) + 1
            for mid in step.signal_ids:
                present.setdefault(mid, []).append(step.index)
        out = [
            SignalRecurrence(
                metric_id=mid,
                title=titles[mid],
                steps_present=len(indices),
                total_findings=totals[mid],
                longest_run=_longest_run(indices),
                first_step=indices[0],
                last_step=indices[-1],
            )
            for mid, indices in present.items()
        ]
        out.sort(key=lambda r: (-r.steps_present, -r.total_findings, r.metric_id))
        return tuple(out)

    @property
    def net_finish_movement_days(self) -> int | None:
        """Calendar days the computed finish moved from the first step's prior side to the last
        step's current side. ``None`` when either end has no solved finish."""
        firsts = [s.prior_finish for s in self.steps if s.prior_finish is not None]
        lasts = [s.current_finish for s in self.steps if s.current_finish is not None]
        if not firsts or not lasts:
            return None
        return (lasts[-1] - firsts[0]).days


def _longest_run(indices: Sequence[int]) -> int:
    """Longest unbroken run of consecutive step indices in ``indices`` (ascending, distinct)."""
    if not indices:
        return 0
    longest = run = 1
    for prev, cur in pairwise(indices):
        run = run + 1 if cur == prev + 1 else 1
        longest = max(longest, run)
    return longest


def _finish_date(schedule: Schedule, cpm: CPMResult) -> dt.date | None:
    try:
        finish = offset_to_datetime(schedule.project_start, cpm.project_finish, schedule.calendar)
        return finish.date()
    except (ValueError, OverflowError):  # pragma: no cover - defensive; a solved CPM has a finish
        return None


def compute_pairwise_series(
    schedules: Sequence[Schedule], cpms: Sequence[CPMResult] | None = None
) -> PairwiseSeries:
    """Compare every consecutive version pair, oldest to newest, two at a time.

    ``cpms`` (parallel to ``schedules``, in the caller's order) reuses solves the caller already
    has — the multi-version routes always do, so the sweep costs only the diffs. Versions are
    ordered by data date first (:func:`order_versions`), so "earliest forward" means earliest by
    *data date*, not by load order.

    Returns an empty series for fewer than two versions: there is no comparison to make, and
    saying so is not the same as reporting no signals.
    """
    ordered = order_versions(list(schedules))
    if len(ordered) < 2:
        return PairwiseSeries(steps=(), versions=len(ordered))
    by_obj: dict[int, CPMResult] = {}
    if cpms is not None:
        by_obj = {id(s): c for s, c in zip(schedules, cpms, strict=True)}

    def solve(sch: Schedule) -> CPMResult | None:
        cached = by_obj.get(id(sch))
        if cached is not None:
            return cached
        try:
            return compute_cpm(sch)
        except CPMError:
            return None

    steps: list[PairStep] = []
    uncomparable: list[str] = []
    index = 0
    for prior, current in pairwise(ordered):
        prior_cpm, current_cpm = solve(prior), solve(current)
        pair_label = f"{_label(prior)} → {_label(current)}"
        if prior_cpm is None or current_cpm is None:
            # Law 2: an unsolvable side means we could not look — never "we looked, found none".
            uncomparable.append(pair_label)
            continue
        index += 1
        steps.append(
            PairStep(
                index=index,
                prior_label=_label(prior),
                current_label=_label(current),
                prior_date=prior.status_date.date() if prior.status_date else None,
                current_date=current.status_date.date() if current.status_date else None,
                findings=detect_manipulation(
                    current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm
                ),
                prior_finish=_finish_date(prior, prior_cpm),
                current_finish=_finish_date(current, current_cpm),
            )
        )
    return PairwiseSeries(
        steps=tuple(steps), uncomparable=tuple(uncomparable), versions=len(ordered)
    )
