"""The sub-day-float probe fixture must keep DISCRIMINATING (ADR-0390 follow-up; the 44-day
side and the measured rule added by ADR-0514, R-03).

`tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml` is not a test input — it is an **operator
input**. It exists to be run through Deltek Acumen Fuse once, by hand, on a licensed machine, to
settle a question no formula can answer.

Fuse's `7. Negative Float` filters on a bare ``Total Float < 0``. Two INDEPENDENT sources agree
on that, which is why it is stated as fact here rather than as a reading:

* the operator's Fuse **v8.11.0CU1** metric-definition screens — Formula box EMPTY, mode Basic,
  Primary Formula filters ``Baseline Duration > 0`` and ``Total Float < 0``, inclusions
  Planned + In Progress / Normal + Milestone (Summary and Level of Effort unchecked);
* the committed library itself, ``00_REFERENCE_INTAKE/acumen_v8.11.0/NASA Metrics_Complete_*.aft``
  — the metric named ``7. Negative Float`` (NOT the four generically-named "Negative Float"
  metrics, which are different metrics) has an EMPTY ``<Formula>`` and a ``PrimaryFilter`` of
  exactly ``Baseline Duration GreaterThan 0`` AND ``Total Float LessThan 0``.

That empty ``<Formula>`` is the answer to a question this repo carried for weeks as "the AFT has
NO formula for Negative Float": there is no formula because the metric is defined by FILTERS.

Our parity mode instead applies ``round(total_float / mpd) < 0`` (ADR-0280). The two agree only
if Fuse's Total Float FIELD is itself whole-day-grained, and neither source says whether it is.
The fixture's three sub-day magnitudes are chosen so ONE run answers three questions:
``-0.25 d`` (any whole-day treatment, round or truncate, drops it), ``-0.50 d`` (the rounding
TIE — Python's banker's ``round()`` drops it, half-away-from-zero would keep it), and
``-0.75 d`` (rounds to -1 and is kept; truncates to 0 and is dropped).

The fixture's whole value is that it contains activities where the two rules DISAGREE. If a CPM
change ever flattened that, the fixture would still load, still look fine, and the operator would
burn a licensed-tool run on a schedule that could not answer the question — and we would not find
out until the answer came back meaningless. So the discrimination is pinned here.

This guard asserts the fixture's SHAPE, never Fuse's answer.

**ADR-0514 (R-03) changed what the run is for.** The FIELD's rule is now measured from the
operator's own Fuse exports (``tests/parity/test_fuse_total_float_field_oracle.py``): the Total
Float Fuse displays is the stored slack rounded HALF-TO-EVEN to whole days, and the DCMA float
sets read that field UID-exact on both Large Test File snapshots. The fixture therefore carries
BOTH thresholds — the 44-day side (``+44.25 / +44.50 / +44.75 d`` discriminators, ``+45.00`` and
``+44.00 d`` controls) beside the negative side — and the run's remaining value is the filter's
reading exactly at the two ties, which no corpus activity occupies: a confirmation, not a blocker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.dcma14 import compute_dcma14
from schedule_forensics.importers.mspdi import parse_mspdi

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "mspdi" / "NEGFLOAT_SubDay_Probe.xml"


def _floats() -> tuple[dict[int, int], int, dict[int, str]]:
    sch = parse_mspdi(FIXTURE)
    cpm = compute_cpm(sch)
    mpd = sch.calendar.working_minutes_per_day
    tf = {t.unique_id: cpm.timings[t.unique_id].total_float for t in sch.tasks}
    names = {t.unique_id: t.name for t in sch.tasks}
    return tf, mpd, names


def _pure(minutes: int) -> bool:
    """The metric definition as Fuse writes it: a bare ``Total Float < 0``."""
    return minutes < 0


def _parity(minutes: int, mpd: int) -> bool:
    """Our ADR-0280 parity rule: round to whole days FIRST, then compare."""
    return round(minutes / mpd) < 0


def _pure_high(minutes: int, mpd: int) -> bool:
    """Fuse's "6. High Float" as written: a bare ``Total Float > 44`` (working days)."""
    return minutes > 44 * mpd


def _parity_high(minutes: int, mpd: int) -> bool:
    """The parity rule on the 44-day side: whole days first (half-to-even), then ``> 44``."""
    return round(minutes / mpd) > 44


def test_the_fixture_still_discriminates_between_the_two_rules() -> None:
    """At least one activity where `pure` says negative and `parity` says not.

    This is the entire reason the file exists. Zero such activities = a wasted Fuse run.
    """
    tf, mpd, _names = _floats()
    disagree = {u: v for u, v in tf.items() if _pure(v) != _parity(v, mpd)}
    assert disagree, (
        "the probe fixture no longer discriminates: every activity's total float is classified "
        "identically by `total_float < 0` and by `round(total_float/mpd) < 0`, so running it "
        "through Acumen Fuse could not tell the two rules apart. Restore a sub-day negative "
        f"float (strictly between -1 and 0 days). Floats seen (days): "
        f"{ {u: round(v / mpd, 3) for u, v in sorted(tf.items())} }"
    )


def test_the_controls_are_unambiguous() -> None:
    """The run is only interpretable if the controls behave, so pin them too.

    A whole-day negative float that Fuse does NOT count means the run was misconfigured (wrong
    metric, wrong project, filters edited) — it does not mean our rounding is right. Equally, a
    zero/positive-float activity that Fuse DOES count means the same. Both rules must agree on
    every control, or the control cannot adjudicate anything.
    """
    tf, mpd, names = _floats()
    must_neg = [u for u, n in names.items() if "MUST BE COUNTED BY NEGATIVE FLOAT" in n]
    must_high = [u for u, n in names.items() if "MUST BE COUNTED BY HIGH FLOAT" in n]
    must_not = [u for u, n in names.items() if "MUST NOT BE COUNTED" in n]
    assert must_neg and must_high and must_not, (
        "the fixture's control activities are no longer identifiable by name — the operator reads "
        f"these labels off Fuse's grid to interpret the run. Names: {sorted(names.values())}"
    )
    for u in must_neg:
        assert _pure(tf[u]) and _parity(tf[u], mpd), (
            f"UID {u} ({names[u]}) is labelled MUST BE COUNTED BY NEGATIVE FLOAT but is not "
            f"negative under both rules ({tf[u] / mpd:+.3f} d) — it cannot serve as a control"
        )
    for u in must_high:
        assert _pure_high(tf[u], mpd) and _parity_high(tf[u], mpd), (
            f"UID {u} ({names[u]}) is labelled MUST BE COUNTED BY HIGH FLOAT but is not high "
            f"under both rules ({tf[u] / mpd:+.3f} d) — it cannot serve as a control"
        )
    for u in must_not:
        assert not (_pure(tf[u]) or _parity(tf[u], mpd)), (
            f"UID {u} ({names[u]}) is labelled MUST NOT BE COUNTED but reads as negative "
            f"({tf[u] / mpd:+.3f} d) — it cannot serve as a negative control"
        )
        assert not (_pure_high(tf[u], mpd) or _parity_high(tf[u], mpd)), (
            f"UID {u} ({names[u]}) is labelled MUST NOT BE COUNTED but reads as high float "
            f"({tf[u] / mpd:+.3f} d) — it cannot serve as a negative control"
        )


def test_no_activity_falls_out_of_the_parity_population() -> None:
    """Every activity must clear `Baseline Duration > 0`, or the population confounds the answer.

    Fuse's Negative Float filters on `Baseline Duration > 0` and our `_baselined` requires
    `>= mpd` (ADR-0367, adjudicated). If any probe activity sat below that line, "Fuse did not
    count it" would be ambiguous between "the rounding rule excluded it" and "the population
    filter excluded it" — and the run would prove nothing.
    """
    sch = parse_mspdi(FIXTURE)
    mpd = sch.calendar.working_minutes_per_day
    thin = {
        t.unique_id: t.baseline_duration_minutes
        for t in sch.tasks
        if (t.baseline_duration_minutes or 0) < mpd
    }
    assert not thin, (
        "these probe activities have a baseline duration below one working day, so the parity "
        f"population filter would exclude them and confound the result: {thin} (mpd={mpd})"
    )


def test_the_shipped_metric_answers_differently_under_the_two_rules() -> None:
    """The strongest pin: DCMA-07 itself must disagree with itself across `acumen_parity`.

    The CPM-level check above proves the raw floats discriminate. This proves the discrimination
    survives all the way through the SHIPPED metric — population filter, baseline predicate,
    effective-float preference and all — which is the thing Fuse's number will actually be
    compared against. A fixture that discriminated in raw float but not in `compute_dcma14`
    would still buy the operator nothing.
    """
    sch = parse_mspdi(FIXTURE)
    cpm = compute_cpm(sch)
    pure = compute_dcma14(sch, cpm_result=cpm, acumen_parity=False)["DCMA07"]
    parity = compute_dcma14(sch, cpm_result=cpm, acumen_parity=True)["DCMA07"]
    assert pure.population == parity.population, (
        "the two modes disagree on the POPULATION, not just the rule — then a differing count "
        f"would be ambiguous between the two ({pure.population} vs {parity.population})"
    )
    assert pure.count > parity.count, (
        "DCMA-07 returns the same count under both rules, so running this fixture through Fuse "
        f"cannot tell them apart: pure={pure.count}/{pure.population}, "
        f"parity={parity.count}/{parity.population}"
    )
    pure_high = compute_dcma14(sch, cpm_result=cpm, acumen_parity=False)["DCMA06"]
    parity_high = compute_dcma14(sch, cpm_result=cpm, acumen_parity=True)["DCMA06"]
    assert pure_high.population == parity_high.population
    assert pure_high.count > parity_high.count, (
        "DCMA-06 returns the same count under both rules on the 44-day side: "
        f"pure={pure_high.count}, parity={parity_high.count}"
    )


def test_the_fixture_discriminates_the_high_float_rules_too() -> None:
    """The 44-day side (ADR-0514): at least one activity where ``> 44`` on the raw float and
    ``> 44`` on the whole-day field disagree, and the tie itself (+44.50 d) present by value."""
    tf, mpd, _names = _floats()
    disagree = {u: v for u, v in tf.items() if _pure_high(v, mpd) != _parity_high(v, mpd)}
    assert disagree, (
        "no activity separates `total_float > 44 d` from `round(total_float/mpd) > 44`; the run "
        f"could not adjudicate the 44-day side. Floats seen (days): "
        f"{ {u: round(v / mpd, 3) for u, v in sorted(tf.items())} }"
    )


@pytest.mark.parametrize(("marker", "days"), [("NEG-SUBDAY-050", -0.5), ("HIGH-SUBDAY-4450", 44.5)])
def test_the_two_ties_are_present_exactly(marker: str, days: float) -> None:
    """The reason the fixture exists after ADR-0514: the two exact ties (-0.50 d / +44.50 d),
    which no corpus activity occupies, each present by name at exactly that float — under the
    measured half-to-even field neither is counted (0 is not negative; 44 is not > 44)."""
    tf, mpd, names = _floats()
    hits = [u for u, n in names.items() if marker in n]
    assert len(hits) == 1, f"{marker!r} must name exactly one activity: {hits}"
    assert tf[hits[0]] == days * mpd, f"{marker}: {tf[hits[0]] / mpd:+.3f} d, expected {days:+.2f}"
    assert not _parity(tf[hits[0]], mpd) and not _parity_high(tf[hits[0]], mpd)


@pytest.mark.parametrize(
    "uid_marker",
    [
        "DISCRIMINATOR",
        "MUST BE COUNTED BY NEGATIVE FLOAT",
        "MUST BE COUNTED BY HIGH FLOAT",
        "MUST NOT BE COUNTED",
    ],
)
def test_every_role_the_operator_reads_is_present(uid_marker: str) -> None:
    """The operator identifies rows in Fuse's grid BY NAME; each role must exist to be read."""
    _, _, names = _floats()
    assert any(uid_marker in n for n in names.values()), (
        f"no activity is labelled {uid_marker!r}; the operator cannot interpret the Fuse grid "
        f"without it. Names present: {sorted(names.values())}"
    )
