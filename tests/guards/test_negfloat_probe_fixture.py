"""The sub-day-negative-float probe fixture must keep DISCRIMINATING (ADR-0390 follow-up).

`tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml` is not a test input — it is an **operator
input**. It exists to be run through Deltek Acumen Fuse once, by hand, on a licensed machine, to
settle a question no formula can answer: Fuse's `7. Negative Float` metric filters on a bare
``Total Float < 0`` (confirmed from the operator's v8.11.0CU1 metric-definition screens — the
Formula box is EMPTY, the metric is filter-driven, which is why the `.aft` carries no formula
text for it). Our parity mode instead applies ``round(total_float / mpd) < 0``. The two agree
only if Fuse's Total Float FIELD is itself whole-day-grained, and nothing in the library says
whether it is.

The fixture's whole value is that it contains activities where the two rules DISAGREE. If a CPM
change ever flattened that, the fixture would still load, still look fine, and the operator would
burn a licensed-tool run on a schedule that could not answer the question — and we would not find
out until the answer came back meaningless. So the discrimination is pinned here.

This guard asserts the fixture's SHAPE, never Fuse's answer: the answer is the thing we do not
know yet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
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
    must_count = [u for u, n in names.items() if "MUST BE COUNTED" in n]
    must_not = [u for u, n in names.items() if "MUST NOT BE COUNTED" in n]
    assert must_count and must_not, (
        "the fixture's control activities are no longer identifiable by name — the operator reads "
        f"these labels off Fuse's grid to interpret the run. Names: {sorted(names.values())}"
    )
    for u in must_count:
        assert _pure(tf[u]) and _parity(tf[u], mpd), (
            f"UID {u} ({names[u]}) is labelled MUST BE COUNTED but is not negative under both "
            f"rules ({tf[u] / mpd:+.3f} d) — it cannot serve as a positive control"
        )
    for u in must_not:
        assert not _pure(tf[u]) and not _parity(tf[u], mpd), (
            f"UID {u} ({names[u]}) is labelled MUST NOT BE COUNTED but reads as negative "
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


@pytest.mark.parametrize("uid_marker", ["DISCRIMINATOR", "MUST BE COUNTED", "MUST NOT BE COUNTED"])
def test_every_role_the_operator_reads_is_present(uid_marker: str) -> None:
    """The operator identifies rows in Fuse's grid BY NAME; each role must exist to be read."""
    _, _, names = _floats()
    assert any(uid_marker in n for n in names.values()), (
        f"no activity is labelled {uid_marker!r}; the operator cannot interpret the Fuse grid "
        f"without it. Names present: {sorted(names.values())}"
    )
