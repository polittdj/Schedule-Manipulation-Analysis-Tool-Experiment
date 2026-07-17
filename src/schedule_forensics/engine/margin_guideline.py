"""NASA Figure 5-30 expected-margin guideline band + SRA margin-sufficiency reads (F3c).

Two pure, additive computations behind the parameterized expected-margin panel:

* **Tier-a — the Figure 5-30 guideline band.** SMH Rev 2 §5.5.11.2 ("How Much" Margin to
  Establish, printed p.120 / PDF p.121) gives a three-row table of "Established standards for
  margin allocation" (Figure 5-30) — per-life-cycle-phase margin *rate ranges*, each explicitly
  "Varies". §7.3.3.1.6 (printed p.309-314) prescribes tracking margin against a burndown, and the
  Figure 7-32 prose (printed p.312) states "Shown is a linear burndown but stepped burndowns that
  mimic the margin guidelines over time are sometimes used as well" — the direct textual license
  for a stepped expected-margin band whose slopes are the Fig 5-30 rates.
  :func:`expected_margin_band` evaluates that stepped band; the rates and phase dates are
  operator parameters (the handbook's values are ranges consolidated "from several NASA Centers",
  "suitable for early P/p planning" — program-defined by design, like the driving-slack day tiers).

* **Tier-b — the SRA percentile sufficiency read.** §7.3.3.2.3 (Sufficiency of Margin, printed
  p.322): "using a stochastic tracking curve takes the results from a routine SRA and plots the
  results against organizational margin requirements." :func:`margin_risk_read` reads the
  ALREADY-COMPUTED empirical step-CDF from :mod:`.sra` (no new sampling, no new math) against the
  deterministic finish D and the zero-margin boundary E, classifying by operator-set percentile
  thresholds. The 70/50 defaults quote the handbook's *example* thresholds (Figure 7-45 prose,
  printed p.323: "In this example case the 'Watch' area is between the 70th and 50th percentiles
  with no action required above and corrective action required below"; §7.3.3.2.1 Thresholds,
  printed p.320: "reasonable threshold recommendations would be to 'Watch' when less than 70%
  on-time completion and Corrective Action required when less than 50% on-time completion") —
  example/recommended values, NOT NASA rules; the handbook's general rule is "The P/p sets the
  thresholds during the Schedule Management Planning Process and documents them in the SMP"
  (§7.3.3.1.6 Thresholds, printed p.314).

Everything here is deterministic arithmetic over engine outputs; nothing samples, solves, or
mutates. No existing metric or parity target consumes this module.
"""

from __future__ import annotations

import datetime as dt
from bisect import bisect_right
from dataclasses import dataclass
from itertools import pairwise

#: Figure 5-30, verbatim (SMH Rev 2 §5.5.11.2, printed p.120 / PDF p.121; caption "Established
#: standards for margin allocation"). Columns: From (Point in Life Cycle) / To (Point in Life
#: Cycle) / Amount of Planned Margin. Kept word-for-word for UI + export provenance display.
FIG_5_30_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "Confirmation Review",
        "Beginning of Integration & Test",
        "Varies: 1-2 month of schedule margin per year",
    ),
    (
        "Start of Integration & Test",
        "Shipment to Launch Site",
        "Varies: 2-2.5 months of schedule margin per year",
    ),
    (
        "Delivery to Launch Site",
        "Launch",
        "Varies: 1 day per week, 1 week per month, 1 month per year",
    ),
)

#: The tool's DISCLOSED month -> work-day conversion for the Fig 5-30 rates: 1 month of schedule
#: margin = 30 work days. This is the same reading ADR-0230/0253 committed to for the GSFC Gold
#: Rule (30 margin work-days per program year == the handbook's "1 month per year" edge), and
#: §6.3.2.5.3.6 (printed p.266) states Fig 5-30 itself summarizes that organizational guidance
#: ("such as GSFC Gold Rules or the JPL Design Principles documents, summarized in Figure 5-30").
MONTH_WORK_DAYS = 30.0

#: PROVENANCE (operator-editable defaults; the figure's own values are RANGES marked "Varies" —
#: program-defined per the SMH itself, so editable-with-cited-defaults is the handbook-conformant
#: design, exactly like DEFAULT_SECONDARY_MAX_DAYS in engine/driving_slack.py). Conversion under
#: MONTH_WORK_DAYS = 30 (1 week = 7 d, 1 day = 1 wd per calendar week):
#:   row 1  "1-2 month ... per year"      -> (1 x 30, 2 x 30)     = (30.0, 60.0) wd/yr
#:   row 2  "2-2.5 months ... per year"   -> (2 x 30, 2.5 x 30)   = (60.0, 75.0) wd/yr
#:   row 3  three ALTERNATIVES, not a range — "1 month per year" = 30.0; "1 day per week"
#:          = 365.25 / 7 ~= 52.2; "1 week per month" = 7 x 12 = 84.0. The prefill spans the
#:          extremes (30.0, 84.0); the UI quotes all three alternatives verbatim beside the inputs.
FIG_5_30_DEFAULT_RATES: tuple[tuple[float, float], ...] = (
    (30.0, 60.0),
    (60.0, 75.0),
    (30.0, 84.0),
)


@dataclass(frozen=True)
class GuidelineBandConfig:
    """The operator's Fig 5-30 band: four phase-boundary dates + three (low, high) wd/yr rates.

    ``phase_dates`` = (Confirmation Review, start of I&T, delivery to launch site, launch) —
    program facts the engine cannot derive; strictly increasing (validated by the caller's
    fail-soft setter, re-checked here). ``rates`` are work-days of expected margin accumulation
    per program year inside each of the three Fig 5-30 phases.
    """

    phase_dates: tuple[dt.date, dt.date, dt.date, dt.date]
    rates: tuple[tuple[float, float], ...] = FIG_5_30_DEFAULT_RATES

    def __post_init__(self) -> None:
        if len(self.phase_dates) != 4:
            raise ValueError("phase_dates must be the four Fig 5-30 boundaries")
        if any(b <= a for a, b in pairwise(self.phase_dates)):
            raise ValueError("phase_dates must be strictly increasing")
        if len(self.rates) != 3:
            raise ValueError("rates must carry the three Fig 5-30 rows")
        for low, high in self.rates:
            if not (0 < low <= high <= 365):
                raise ValueError("each rate must satisfy 0 < low <= high <= 365 wd/yr")


@dataclass(frozen=True)
class BandPoint:
    """The expected-margin band evaluated at one date: remaining guideline margin, both edges."""

    date: dt.date
    low_wd: float
    high_wd: float


def expected_margin_band(
    config: GuidelineBandConfig, at_dates: tuple[dt.date, ...]
) -> tuple[BandPoint, ...]:
    """The stepped Fig 5-30 expected-margin band evaluated at ``at_dates`` + the phase boundaries.

    Arithmetic (the "stepped burndown that mimics the margin guidelines", Fig 7-32 prose): at
    status date ``t``, each band edge is the guideline margin still to be ACCUMULATED over the
    remaining phase windows —

        expected_edge(t) = sum over the three phases of
                           rate_edge * overlap_days(phase ∩ [t, launch]) / 365.0

    Piecewise linear, kinking at the phase boundaries (they are always included as evaluation
    points so a chart renders the kinks exactly); the full three-phase sum before Confirmation
    Review, 0 at/after launch. Results are rounded to 0.1 wd (the margin dashboard's display
    precision). Dates outside [first, launch] evaluate to the clamped edge values, never negative.
    """
    cr, it_start, ship, launch = config.phase_dates
    segments = ((cr, it_start), (it_start, ship), (ship, launch))

    def edge(t: dt.date, which: int) -> float:
        total = 0.0
        for (seg_a, seg_b), rate in zip(segments, config.rates, strict=True):
            lo = max(t, seg_a)
            if lo < seg_b:
                total += rate[which] * (seg_b - lo).days / 365.0
        return round(total, 1)

    points = sorted(set(at_dates) | set(config.phase_dates))
    return tuple(BandPoint(date=d, low_wd=edge(d, 0), high_wd=edge(d, 1)) for d in points)


def band_position(effective_wd: float, low_wd: float, high_wd: float) -> str:
    """Classify actual effective margin against the band edges: ``below`` / ``within`` / ``above``.

    ``below`` is the guideline-deviation state (§7.3.3.1.6 Thresholds, printed p.314: "Deviations
    from the guidelines trigger a requirement for either an explanation about why the deviation is
    acceptable or for the initiation of activities to mitigate the trend"); ``above`` is reported
    neutrally (margin richer than the operator-set guideline range).
    """
    if effective_wd < low_wd:
        return "below"
    if effective_wd > high_wd:
        return "above"
    return "within"


# --- tier-b: SRA percentile sufficiency ------------------------------------------------------

#: Default Watch / Corrective-Action percentile thresholds — the handbook's EXAMPLE values
#: (Figure 7-45 prose, §7.3.3.2.3, printed p.323; "reasonable threshold recommendations",
#: §7.3.3.2.1, printed p.320). Operator-editable; never presented as a NASA rule — the handbook's
#: rule is that thresholds are program-set in the SMP (§7.3.3.1.6 Thresholds, printed p.314).
DEFAULT_WATCH_PCT = 70.0
DEFAULT_CORRECTIVE_PCT = 50.0


@dataclass(frozen=True)
class PercentileRow:
    """One percentile of the SRA finish distribution read against the margin window [E, D]."""

    pct: float
    finish_offset: int  # inverse-CDF read (first breakpoint with cum >= pct), working minutes
    delta_vs_plan_wd: float  # (finish - D) / wmpd; positive = beyond the planned finish
    margin_needed_wd: float  # max(0, finish - E) / wmpd; the buffer this percentile consumes
    covered: bool  # finish <= D  <=>  the margin window absorbs this percentile


@dataclass(frozen=True)
class MarginRiskRead:
    """The §7.3.3.2.3 sufficiency read: the SRA CDF against the deterministic margin window."""

    covered_pct: float  # 100 x CDF(D) — the fraction of simulated finishes the margin covers
    verdict: str | None  # "sufficient" | "watch" | "corrective"; None when no verdict is honest
    degenerate: bool  # every iteration finished at one offset (point-mass — no uncertainty)
    margin_wd: float  # (D - E) / wmpd, the margin window width in work days
    rows: tuple[PercentileRow, ...]
    watch_pct: float
    corrective_pct: float


def _cdf_at(cdf: tuple[tuple[int, float], ...], offset: int) -> float:
    """Fraction of iterations finishing at or before ``offset`` — the right-continuous step read.

    Mirrors ``sra._build_result``'s ``bisect_right(sorted_finishes, deterministic) / n`` exactly
    (the CDF stores, per distinct finish value, the count <= value over the same n), so
    ``_cdf_at(cdf, deterministic_finish) == deterministic_percentile`` — pinned by test.
    """
    offsets = [o for o, _ in cdf]
    idx = bisect_right(offsets, offset) - 1
    return cdf[idx][1] if idx >= 0 else 0.0


def _finish_at(cdf: tuple[tuple[int, float], ...], pct: float) -> int:
    """The first CDF breakpoint whose cumulative probability reaches ``pct``/100 — the exact
    empirical inverse (ceiling quantile) of the stored step-CDF; no resampling. The tiny epsilon
    absorbs count/n float representation so an exact breakpoint (e.g. 0.5 at n=1000) is matched."""
    target = pct / 100.0 - 1e-12
    for offset, cum in cdf:
        if cum >= target:
            return offset
    return cdf[-1][0]  # pct beyond the last breakpoint: the distribution maximum


def margin_risk_read(
    cdf: tuple[tuple[int, float], ...],
    deterministic_finish: int,
    zero_margin_finish: int,
    *,
    wmpd: int,
    watch_pct: float = DEFAULT_WATCH_PCT,
    corrective_pct: float = DEFAULT_CORRECTIVE_PCT,
    percentiles: tuple[float, ...] = (10.0, 50.0, 80.0, 90.0),
) -> MarginRiskRead:
    """Read an SRA finish distribution against the deterministic margin window ``[E, D]``.

    ``cdf`` is :mod:`.sra`'s stored empirical step-CDF; ``deterministic_finish`` (D) the run's own
    deterministic anchor; ``zero_margin_finish`` (E) the same solve with the margin activities
    zeroed (``sra.deterministic_margin_bounds``). All offsets share one working-minute axis.

    The covered percentile is ``100 x CDF(D)``; the verdict classifies it against the operator's
    Watch / Corrective-Action thresholds (>= watch: sufficient; >= corrective: watch; else
    corrective). By construction ``covered(P) <=> finish_at(P) <= D <=> margin_needed(P) <=
    margin_wd`` — internally consistent, tested. Degenerate distributions (a single CDF
    breakpoint: every iteration identical — no uncertainty/risk inputs) return no verdict; the
    caller discloses instead of fabricating certainty. Raises ``ValueError`` on an empty CDF.
    """
    if not cdf:
        raise ValueError("margin_risk_read needs a non-empty CDF")
    if wmpd <= 0:
        raise ValueError("wmpd must be positive")
    degenerate = len(cdf) == 1
    covered = round(100.0 * _cdf_at(cdf, deterministic_finish), 1)
    margin_wd = round(max(0, deterministic_finish - zero_margin_finish) / wmpd, 1)

    wanted = sorted(set(percentiles) | {watch_pct, corrective_pct})
    rows = []
    for pct in wanted:
        finish = _finish_at(cdf, pct)
        rows.append(
            PercentileRow(
                pct=pct,
                finish_offset=finish,
                delta_vs_plan_wd=round((finish - deterministic_finish) / wmpd, 1),
                margin_needed_wd=round(max(0, finish - zero_margin_finish) / wmpd, 1),
                covered=finish <= deterministic_finish,
            )
        )

    verdict: str | None
    if degenerate:
        verdict = None
    elif covered >= watch_pct:
        verdict = "sufficient"
    elif covered >= corrective_pct:
        verdict = "watch"
    else:
        verdict = "corrective"
    return MarginRiskRead(
        covered_pct=covered,
        verdict=verdict,
        degenerate=degenerate,
        margin_wd=margin_wd,
        rows=tuple(rows),
        watch_pct=watch_pct,
        corrective_pct=corrective_pct,
    )
