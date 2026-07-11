"""Plain-language conclusions for a Monte-Carlo SRA run — "what do these results mean?".

Operators asked for the simulation outputs to be *explained*, not just plotted: the classic
Hulett deliverable sentences ("the CPM date is <15% likely to be met", "the 80% target is
9/21", "the 'critical path' is only 18% likely to delay the project — now watch Units 1 & 3").
This module turns an :class:`~schedule_forensics.engine.sra.SRAResult` (legacy whole-project
model) or :class:`~schedule_forensics.engine.sra.SSIResult` (SSI focus-event model) into a
tuple of :class:`Conclusion` cards, each a simple finding + what-it-means + the evidence
figures behind it.

Fidelity (Law 2): the sentences are **deterministic templates** filled with figures read
straight off the result object — no AI, no new statistics, no re-simulation. Every digit in a
``finding`` also appears in that conclusion's ``evidence`` pairs (test-enforced, mirroring the
AI citations gate's numeric-subset philosophy). Thresholds and phrasing follow the intake
references: Hulett "Advanced Project Schedule Risk Analysis" (Lisbon deck — realism tiers,
2,500/10,000 iteration guidance, constraints frustrate the analysis, risk-critical vs
CPM-critical), INT-02 (ICEAA 2015 — contingency from P-levels) and the SRA Concepts primer
(commit at P70-P80, correlation understates spread when ignored).
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import is_effective_critical
from schedule_forensics.engine.sra import SRAResult, SSIResult
from schedule_forensics.model.schedule import Schedule

#: Working minutes per displayed working day (the model-wide 8-hour convention).
_MPD = 480

#: Sampling-precision guidance (Hulett): 2,500 iterations suffice for decisions.
_DECISION_ITERATIONS = 2500

#: An activity is a "hidden driver" when it delays the project in at least this fraction of
#: iterations while NOT being critical in the deterministic plan (Hulett's risk-critical path).
_HIDDEN_CI = 0.4

#: Report a duration-sensitivity driver only above this |Spearman| (noise floor).
_MIN_SENS = 0.25


@dataclass(frozen=True)
class Conclusion:
    """One plain-language conclusion card."""

    topic: str  # short label, e.g. "Planned-date realism"
    severity: str  # "bad" | "warn" | "info" | "good"
    finding: str  # the one-sentence finding, figures included
    meaning: str  # what it means / what to do, in simple terms
    evidence: tuple[tuple[str, str], ...]  # (label, value) figure pairs backing the finding


def _wd(minutes: float) -> int:
    """Working-minute offset difference -> whole working days (presentation rounding)."""
    return round(minutes / _MPD)


def _pct(fraction: float) -> int:
    """A 0..1 fraction as a whole percent (display rounding)."""
    return round(fraction * 100)


def _day(iso: str) -> str:
    """An ISO date or datetime shortened to its calendar-day part (presentation truncation)."""
    return iso.split("T")[0] if "T" in iso else iso


def _days(n: int) -> str:
    """``N working day(s)`` with number agreement."""
    return f"{n} working day" if n == 1 else f"{n} working days"


def _realism(det_date: str, det_percentile: float, focus: str) -> Conclusion:
    """Hulett's headline: how likely is the plan's own date? ("CPM date is <15% likely")."""
    det_date = _day(det_date)
    pct = _pct(det_percentile)
    ev = (("Planned finish", det_date), ("Chance of meeting it", f"{pct}%"))
    if pct < 15:
        return Conclusion(
            "Planned-date realism",
            "bad",
            f"The planned finish for {focus} ({det_date}) is only about {pct}% likely to be "
            "met — the plan is optimistic.",
            "Fewer than about 1 outcome in 7 finishes by the planned date. Do not commit to "
            "this date as-is: add visible schedule contingency or retire risk first.",
            ev,
        )
    if pct < 40:
        return Conclusion(
            "Planned-date realism",
            "warn",
            f"The planned finish for {focus} ({det_date}) has about a {pct}% chance of being "
            "met — worse than a coin flip.",
            "The plan is more likely to slip than to hold. Treat the planned date as a "
            "stretch goal, not a commitment.",
            ev,
        )
    if pct < 60:
        return Conclusion(
            "Planned-date realism",
            "info",
            f"Meeting the planned finish for {focus} ({det_date}) is roughly a coin flip — "
            f"about {pct}% of simulated outcomes finish by it.",
            "Even odds. A promise at this date will be missed about half the time; promise a "
            "later date or carry explicit contingency.",
            ev,
        )
    if pct < 85:
        return Conclusion(
            "Planned-date realism",
            "good",
            f"The planned finish for {focus} ({det_date}) is solid — about {pct}% of "
            "simulated outcomes finish by it.",
            "The plan carries a realistic amount of room. Keep the ranges current as work "
            "progresses so this stays true.",
            ev,
        )
    return Conclusion(
        "Planned-date realism",
        "good",
        f"The planned finish for {focus} ({det_date}) is conservative — about {pct}% of "
        "simulated outcomes finish by then.",
        "There may be room to commit earlier — or the entered ranges overstate the risk. "
        "Revisit the ranges before banking the margin.",
        ev,
    )


def _commitment(p50_date: str, p80_date: str) -> Conclusion:
    p50_date, p80_date = _day(p50_date), _day(p80_date)
    return Conclusion(
        "Commitment dates",
        "info",
        f"For an even-odds date, plan on {p50_date}; to promise with 80% confidence, plan on "
        f"{p80_date}.",
        "Standard practice (Hulett, GAO, NASA): manage the team to the 50/50 date and commit "
        "externally at the 80% date — the gap between them is your schedule contingency.",
        (("P50 (even odds)", p50_date), ("P80 (commitment)", p80_date)),
    )


def _contingency(det_finish: int, p80: int, p80_date: str, det_date: str) -> Conclusion:
    p80_date, det_date = _day(p80_date), _day(det_date)
    buffer_wd = _wd(p80 - det_finish)
    if buffer_wd > 0:
        return Conclusion(
            "Contingency needed",
            "warn",
            f"Protecting an 80%-confidence promise takes about {_days(buffer_wd)} of "
            "schedule contingency beyond the current plan.",
            "Add it as explicit, visible schedule margin before the committed milestone — "
            "not hidden padding inside activity durations.",
            (
                ("Planned finish", det_date),
                ("P80 finish", p80_date),
                ("Contingency", _days(buffer_wd)),
            ),
        )
    return Conclusion(
        "Contingency needed",
        "good",
        "The current plan already finishes at or beyond the 80%-confidence date — no added "
        "contingency is needed.",
        "The plan's own date is at least as late as the P80 date, so an 80% promise is "
        "already covered.",
        (("Planned finish", det_date), ("P80 finish", p80_date)),
    )


def _spread(p10: int, p90: int, p10_date: str, p90_date: str) -> Conclusion:
    p10_date, p90_date = _day(p10_date), _day(p90_date)
    spread_wd = _wd(p90 - p10)
    return Conclusion(
        "Predictability",
        "info",
        f"The realistic finish window spans about {_days(spread_wd)} ({p10_date} to {p90_date}).",
        "The wider this window, the less predictable the finish. Narrow it by firming up "
        "the drivers named below — they contribute the most spread.",
        (
            ("P10 (early)", p10_date),
            ("P90 (late)", p90_date),
            ("Window", _days(spread_wd)),
        ),
    )


def _hidden_drivers(
    rows: list[tuple[str, float, bool]],
) -> list[Conclusion]:
    """Hulett's risk-critical-path lesson from (name, criticality index, plan-critical) rows."""
    out: list[Conclusion] = []
    hidden = sorted(
        ((n, ci) for n, ci, plan_crit in rows if ci >= _HIDDEN_CI and not plan_crit),
        key=lambda r: r[1],
        reverse=True,
    )[:3]
    if hidden:
        listing = "; ".join(f"{n} ({_pct(ci)}%)" for n, ci in hidden)
        out.append(
            Conclusion(
                "Hidden drivers",
                "warn",
                f"Not on today's critical path, but on the delaying path in a large share of "
                f"simulations: {listing}.",
                "This is merge bias — parallel paths compete to drive the finish, so managing "
                "only the plan's critical path misses these. Mitigate them now (Hulett's "
                "'risk critical path').",
                tuple((n, f"critical in {_pct(ci)}% of iterations") for n, ci in hidden),
            )
        )
    plan_cis = [ci for _n, ci, plan_crit in rows if plan_crit]
    if plan_cis:
        max_ci = max(plan_cis)
        if max_ci < 0.5:
            out.append(
                Conclusion(
                    "Critical-path reliance",
                    "info",
                    f"Today's critical path drives the finish in only about {_pct(max_ci)}% "
                    "of simulations.",
                    "The deterministic critical path is not the whole story here — watching "
                    "it alone will miss the paths that actually delay the project most often.",
                    (("Plan-critical path, highest criticality", f"{_pct(max_ci)}%"),),
                )
            )
    return out


def _top_drivers(rows: list[tuple[str, float]]) -> Conclusion | None:
    """(name, Spearman duration sensitivity) -> the 'work these first' card."""
    top = sorted(
        ((n, s) for n, s in rows if abs(s) >= _MIN_SENS),
        key=lambda r: abs(r[1]),
        reverse=True,
    )[:3]
    if not top:
        return None
    listing = "; ".join(f"{n} ({s:+.2f})" for n, s in top)
    return Conclusion(
        "Top duration drivers",
        "info",
        f"Duration risk on these activities moves the finish most: {listing}.",
        "Tighten these estimates, add resources, or de-risk them first — a day saved here "
        "moves the finish more than a day saved anywhere else. (Figures are rank "
        "correlations between the sampled duration and the finish.)",
        tuple((n, f"sensitivity {s:+.2f}") for n, s in top),
    )


def _discrete_risks(rows: list[tuple[str, float, float]]) -> Conclusion | None:
    """(name, occurrence fraction, mean delta working days) -> top mitigation targets."""
    top = sorted(
        ((n, p, d) for n, p, d in rows if d > 0),
        key=lambda r: r[2],
        reverse=True,
    )[:3]
    if not top:
        return None
    listing = "; ".join(
        f"'{n}' (occurs in {_pct(p)}% of runs, costs ~{round(d)} working days)" for n, p, d in top
    )
    return Conclusion(
        "Costliest risks",
        "warn",
        f"The discrete risks that cost the most time when they hit: {listing}.",
        "These are the highest-value mitigation targets — reduce their likelihood or blunt "
        "their impact, then re-run to see the finish window tighten.",
        tuple((n, f"{_pct(p)}% occurrence, ~{round(d)} working days impact") for n, p, d in top),
    )


def _constraints(n_constraints: int) -> Conclusion | None:
    if n_constraints <= 0:
        return None
    noun = "hard constraint caps" if n_constraints == 1 else "hard constraints cap"
    return Conclusion(
        "Hard constraints",
        "warn",
        f"{n_constraints} {noun} the simulated dates — the distribution piles up against "
        "the constraint.",
        "The results likely UNDERSTATE the real risk (Hulett: constraints left in the "
        "schedule frustrate the risk analysis). Re-run with the constraints relaxed to see "
        "the true exposure.",
        (("Hard-constrained activities", str(n_constraints)),),
    )


def _inputs(auto_used: bool) -> Conclusion:
    if auto_used:
        return Conclusion(
            "Input quality",
            "warn",
            "Some duration ranges are the automatic screening defaults, not analyst-entered "
            "estimates.",
            "Treat this run as a screening placeholder. Hold a risk interview (Hulett) to "
            "collect optimistic / most-likely / pessimistic ranges from the people doing "
            "the work, then re-run.",
            (("Ranges", "auto screening defaults in use"),),
        )
    return Conclusion(
        "Input quality",
        "good",
        "Duration ranges were supplied by the analyst — the defensible basis for the distribution.",
        "Keep the ranges current: re-interview when scope or staffing changes, and adjust "
        "ranges to remaining work as activities progress.",
        (("Ranges", "analyst-entered"),),
    )


def _precision(iterations: int) -> Conclusion:
    ev = (("Iterations", f"{iterations:,}"),)
    if iterations < _DECISION_ITERATIONS:
        return Conclusion(
            "Sampling precision",
            "info",
            f"{iterations:,} iterations is screening precision.",
            "Fine for exploration; use 2,500+ iterations for decisions and about 10,000 for "
            "final reports (Hulett).",
            ev,
        )
    return Conclusion(
        "Sampling precision",
        "good",
        f"{iterations:,} iterations — sufficient sampling precision for decision use.",
        "Hulett: 2,500 iterations are enough for decisions; around 10,000 gives smooth "
        "curves for final reports.",
        ev,
    )


def _correlation(correlation: float, used_risks: bool) -> Conclusion | None:
    if correlation > 0:
        return Conclusion(
            "Correlation",
            "info",
            f"A blanket correlation of {correlation:.1f} was applied across activity durations.",
            "Correlated durations move together (shared vendors, teams, technology), which "
            "realistically widens the finish spread compared to independent sampling.",
            (("Correlation", f"{correlation:.1f}"),),
        )
    if not used_risks:
        return Conclusion(
            "Correlation",
            "info",
            "Durations were sampled independently — no correlation and no mapped risks.",
            "Real projects share risk drivers (the same supplier, team, or technology), "
            "which makes durations move together. Independent sampling can understate the "
            "spread; set a correlation or map register risks to activities.",
            (("Correlation", "0.0"), ("Risk register", "not applied")),
        )
    return None


def conclusions_from_sra(
    sch: Schedule, cpm: CPMResult, result: SRAResult
) -> tuple[Conclusion, ...]:
    """Conclusion cards for the legacy whole-project model (:func:`compute_sra`)."""
    names = sch.tasks_by_id
    out: list[Conclusion] = [
        _realism(result.deterministic_finish_date, result.deterministic_percentile, "the project"),
        _commitment(result.p50_date, result.p80_date),
        _contingency(
            result.deterministic_finish,
            result.p80,
            result.p80_date,
            result.deterministic_finish_date,
        ),
        _spread(result.p10, result.p90, result.p10_date, result.p90_date),
    ]
    # risk-critical vs plan-critical (Hulett) — plan-critical on the tool's effective basis
    rows: list[tuple[str, float, bool]] = []
    sens_rows: list[tuple[str, float]] = []
    for a in result.activities:
        task = names.get(a.unique_id)
        if task is None:
            continue
        timing = cpm.timings.get(a.unique_id)
        tf = timing.total_float if timing is not None else 0.0
        label = f"{task.name} (UID {a.unique_id})"
        rows.append((label, a.criticality_index, is_effective_critical(task, tf)))
        sens_rows.append((label, a.duration_sensitivity))
    out.extend(_hidden_drivers(rows))
    if (drivers := _top_drivers(sens_rows)) is not None:
        out.append(drivers)
    if (
        risks := _discrete_risks(
            [
                (
                    r.name,
                    (r.hits / result.iterations if result.iterations else 0.0),
                    r.mean_delta_days,
                )
                for r in result.risk_drivers
            ]
        )
    ) is not None:
        out.append(risks)
    if (constraints := _constraints(len(result.constraints_flagged))) is not None:
        out.append(constraints)
    out.append(_inputs(result.auto_used))
    out.append(_precision(result.iterations))
    return tuple(out)


def conclusions_from_ssi(sch: Schedule, result: SSIResult) -> tuple[Conclusion, ...]:
    """Conclusion cards for the SSI focus-event model (:func:`compute_sra_ssi`)."""
    names = sch.tasks_by_id
    focus = (
        f"'{names[result.target_uid].name}'"
        if result.target_uid is not None and result.target_uid in names
        else "the project"
    )
    if result.p10 == result.p90:
        # degenerate run: every iteration produced the same finish — no uncertainty inputs.
        # The percentile/contingency cards would be meaningless, so say so honestly instead.
        return (
            Conclusion(
                "No uncertainty inputs",
                "warn",
                "Every iteration produced the same finish — the run carried no duration "
                "ranges and no risks, so it holds no risk information yet.",
                "Assign Risk Ranking Factors or Best/Worst-Case durations in the grid "
                "above (or map register risks to activities), then re-run.",
                (("P10", _day(result.p10_date)), ("P90", _day(result.p90_date))),
            ),
            _precision(result.iterations),
        )
    out: list[Conclusion] = [
        _realism(result.deterministic_finish_date, result.deterministic_percentile, focus),
        _commitment(result.p50_date, result.p80_date),
        _contingency(
            result.deterministic_finish,
            result.p80,
            result.p80_date,
            result.deterministic_finish_date,
        ),
        _spread(result.p10, result.p90, result.p10_date, result.p90_date),
    ]
    if (
        risks := _discrete_risks(
            [
                (
                    r.name,
                    (r.hits / result.iterations if result.iterations else 0.0),
                    r.mean_delta_days,
                )
                for r in result.risks
            ]
        )
    ) is not None:
        out.append(risks)
    if (corr := _correlation(result.correlation, result.used_risks)) is not None:
        out.append(corr)
    out.append(_precision(result.iterations))
    return tuple(out)


def conclusions_as_dicts(conclusions: tuple[Conclusion, ...]) -> list[dict[str, object]]:
    """JSON-ready form for the web payloads (``sra.js`` renders the cards)."""
    return [
        {
            "topic": c.topic,
            "severity": c.severity,
            "finding": c.finding,
            "meaning": c.meaning,
            "evidence": [{"label": lbl, "value": val} for lbl, val in c.evidence],
        }
        for c in conclusions
    ]
