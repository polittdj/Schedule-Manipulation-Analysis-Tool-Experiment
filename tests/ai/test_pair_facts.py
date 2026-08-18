"""Consecutive-pair comparative FACTS for Ask-the-AI (ADR-0424).

Operator report (2026-08-18): "In the Schedule Integrity page when there are more than two
schedules loaded the tool only does a comparative analysis of the last two schedules when you Ask
the AI a question." Reproduced on a 4-version workbook whose manipulation sat in the first two
updates — the workbook fact sheet held ZERO manipulation facts, neither shortened activity was
named anywhere, and the only statement on the subject was *"No incomplete activity on the critical
path had its duration shortened between v03.mpp and v04.mpp"*: an affirmative negative, scoped to
one of three available comparisons, that reads as a workbook verdict.

These assertions are about the EVIDENCE, not model prose — and specifically about each fact's
``text``, because the Ask prompt is assembled from ``f.text`` alone and never ``f.rendered()``, so
anything living only in the citation tuple is invisible to the model.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path

import pytest

from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.ai.pair_facts import _MAX_DETAIL_FACTS, pairwise_comparison_facts
from schedule_forensics.ai.qa import build_workbook_fact_sheet, model_evidence, relevant_facts
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
_D0 = dt.datetime(2026, 4, 15)


@pytest.fixture(scope="module")
def base() -> Schedule:
    return parse_mspdi_text(
        (_GOLDEN / "Project5.mspdi.xml").read_text(encoding="utf-8"), source_file="base.mpp"
    )


def _victims(sch: Schedule) -> list[int]:
    return [
        t.unique_id
        for t in sch.tasks
        if not t.is_summary and t.percent_complete < 100.0 and t.duration_minutes >= 4800
    ]


def _workbook(base: Schedule, n: int, cut_at: set[int]) -> list[Schedule]:
    """``n`` versions; a duration is halved going INTO each 1-based step index in ``cut_at``."""
    victims = _victims(base)
    out, cur = [], base
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
        label = f"v{i + 1:02d}.mpp"
        out.append(
            cur.model_copy(
                update={
                    "name": label,
                    "source_file": label,
                    "status_date": _D0 + dt.timedelta(days=30 * i),
                }
            )
        )
    return out


def _facts(versions: list[Schedule]):
    return pairwise_comparison_facts(versions, [compute_cpm(v) for v in versions])


def _blob(facts) -> str:
    return "\n".join(f.text for f in facts)


# --- THE regression --------------------------------------------------------------------------


def test_the_series_fact_names_every_consecutive_comparison(base: Schedule) -> None:
    """32 loaded versions must produce 31 stated comparisons, not one."""
    versions = _workbook(base, 32, cut_at=set())
    blob = _blob(_facts(versions))
    assert "PAIRWISE COMPARISON SERIES: all 32 loaded version(s)" in blob
    assert "31 comparison(s)" in blob
    for i in range(1, 32):
        assert f"step {i} v{i:02d}.mpp to v{i + 1:02d}.mpp" in blob, f"step {i} missing"


def test_manipulation_in_an_early_pair_reaches_the_fact_TEXT(base: Schedule) -> None:
    """The cut is in step 1 of 3 and the newest pair is clean — the old fact sheet said nothing.

    The activity name must be in ``text``: the Ask prompt never renders citations.
    """
    versions = _workbook(base, 4, cut_at={1})
    cut_name = next(t.name for t in versions[0].tasks if t.unique_id == _victims(base)[1])
    blob = _blob(_facts(versions))
    assert "Manipulation signal at step 1 of 3 (v01.mpp to v02.mpp)" in blob
    assert "duration shortened" in blob
    assert cut_name in blob, "the shortened activity must be NAMED in the fact text"


def test_the_workbook_fact_sheet_carries_the_series_end_to_end(base: Schedule) -> None:
    versions = _workbook(base, 6, cut_at={1, 3})
    facts = build_workbook_fact_sheet(versions, [compute_cpm(v) for v in versions])
    assert_all_cited(facts)
    blob = _blob(facts)
    assert "PAIRWISE COMPARISON SERIES: all 6 loaded version(s)" in blob
    assert "MANIPULATION-SIGNAL RECURRENCE" in blob
    assert "Manipulation signal at step 1 of 5" in blob
    assert "Manipulation signal at step 3 of 5" in blob


# --- the frame must survive fact selection ----------------------------------------------------


def test_the_comparison_block_survives_a_question_that_would_otherwise_rank_it_out(
    base: Schedule,
) -> None:
    """Pinning is what keeps the comparative frame in the evidence, so the oracle must be one
    that CHANGES when pinning is removed.

    A no-overlap question ("zzz qqq xyzzy") does not discriminate: the block is inserted directly
    behind the pinned population facts, so it also happens to lead the ranked tail and survives
    either way. The question below matches OTHER facts strongly enough to fill the cap, which is
    the state where only ``pinned`` can save the frame — the control below proves the difference.
    """
    versions = _workbook(base, 8, cut_at={1, 2})
    facts = build_workbook_fact_sheet(versions, [compute_cpm(v) for v in versions])
    question = "what is the total float on the critical path and the DCMA check pass rate?"
    for selected in (model_evidence(facts, question), relevant_facts(facts, question)):
        texts = [f.text for f in selected]
        assert any(t.startswith("PAIRWISE COMPARISON SERIES") for t in texts)
        assert any(t.startswith("MANIPULATION-SIGNAL RECURRENCE") for t in texts)

    # CONTROL — the same question over the same facts with the frame's pin removed drops it.
    # Without this the assertions above could pass on a build that never pinned anything.
    unpinned = tuple(
        dataclasses.replace(f, pinned=False)
        if f.text.startswith(("PAIRWISE COMPARISON SERIES", "MANIPULATION-SIGNAL RECURRENCE"))
        else f
        for f in facts
    )
    dropped = [f.text for f in relevant_facts(unpinned, question)]
    assert not any(t.startswith("PAIRWISE COMPARISON SERIES") for t in dropped), (
        "the control did not move — this question cannot detect a lost pin, so the assertions "
        "above prove nothing about pinning"
    )


# --- recurrence: the arithmetic behind "is this a pattern?" ------------------------------------


def test_recurrence_states_counts_runs_and_refuses_to_assert_intent(base: Schedule) -> None:
    versions = _workbook(base, 7, cut_at={1, 2, 3})
    blob = _blob(_facts(versions))
    assert "duration shortened fired in 3 of 6 step(s)" in blob
    assert "longest unbroken run 3 step(s)" in blob
    assert "Read these as counts, not as intent" in blob
    assert "does not assert why" in blob


def test_a_clean_workbook_states_a_MEASURED_absence_rather_than_going_silent(
    base: Schedule,
) -> None:
    """Law 2's shape: "we compared every update and nothing fired" is a finding; silence is not."""
    blob = _blob(_facts(_workbook(base, 5, cut_at=set())))
    assert "none of the 4 consecutive-pair comparison(s) fired any manipulation signal" in blob
    assert "not an unexamined one" in blob


# --- anti-newest-bias in the detail allocation ------------------------------------------------


def test_detail_facts_are_allocated_oldest_first_so_early_steps_are_never_crowded_out(
    base: Schedule,
) -> None:
    """A "top N by severity/recency" cut would rebuild the newest-first bias being removed.

    With more signal-bearing steps than the detail budget, EVERY early step must still get one
    before any step gets a second.
    """
    n_steps = _MAX_DETAIL_FACTS + 4
    versions = _workbook(base, n_steps + 1, cut_at=set(range(1, n_steps + 1)))
    facts = _facts(versions)
    details = [f for f in facts if f.text.startswith("Manipulation signal at step ")]
    assert len(details) == _MAX_DETAIL_FACTS
    steps_detailed = [int(f.text.split("step ", 1)[1].split(" ", 1)[0]) for f in details]
    assert steps_detailed == sorted(steps_detailed)
    assert steps_detailed[0] == 1, "the OLDEST step must be represented"
    assert len(set(steps_detailed)) == _MAX_DETAIL_FACTS, "one per step before any step repeats"


def test_a_truncated_detail_allocation_says_so(base: Schedule) -> None:
    n_steps = _MAX_DETAIL_FACTS + 4
    versions = _workbook(base, n_steps + 1, cut_at=set(range(1, n_steps + 1)))
    series_fact = _facts(versions)[0].text
    assert "are counted in this series and in the recurrence tally but are not" in series_fact
    assert "further signal(s)" in series_fact


def test_no_truncation_note_when_everything_is_detailed(base: Schedule) -> None:
    series_fact = _facts(_workbook(base, 4, cut_at={1, 2}))[0].text
    assert "further signal(s)" not in series_fact


# --- contracts ---------------------------------------------------------------------------------


def test_every_fact_is_cited_and_the_frame_is_pinned(base: Schedule) -> None:
    facts = _facts(_workbook(base, 5, cut_at={1, 3}))
    assert_all_cited(facts)
    assert facts[0].pinned and facts[1].pinned
    assert not any(f.pinned for f in facts[2:]), "only the frame is pinned; details are ranked"


def test_a_single_version_has_no_comparison_to_make(base: Schedule) -> None:
    assert pairwise_comparison_facts(_workbook(base, 1, cut_at=set())) == ()
    assert pairwise_comparison_facts([]) == ()


# --- silence is never an answer: "could not compare" vs "compared and clean" -------------------


def test_when_no_pair_can_be_compared_the_fact_says_so_rather_than_vanishing(
    base: Schedule,
) -> None:
    """Returning () here would be the very defect this module closes: the reader could not tell
    "no comparison was possible" from "the comparisons were made and were clean"."""
    from schedule_forensics.engine import pair_series as mod

    versions = _workbook(base, 3, cut_at={1})
    real = mod.compute_cpm

    def fake(sch: Schedule, *a: object, **k: object) -> object:
        if sch.source_file == "v02.mpp":  # the middle version breaks BOTH adjacent pairs
            raise mod.CPMError("synthetic: this network does not solve")
        return real(sch, *a, **k)  # type: ignore[arg-type]

    mod.compute_cpm = fake  # type: ignore[assignment]
    try:
        facts = pairwise_comparison_facts(versions)  # no cpms -> the engine meets the failure
    finally:
        mod.compute_cpm = real  # type: ignore[assignment]

    assert facts, "an all-uncomparable workbook must still produce a stated fact"
    text = facts[0].text
    assert "NONE of the 2 adjacent version pair(s) could be compared" in text
    assert "v01.mpp → v02.mpp" in text and "v02.mpp → v03.mpp" in text
    assert "missing analysis, NOT an absence of signals" in text
    assert facts[0].pinned and facts[0].citations


def test_a_workbook_whose_pair_population_is_too_small_says_so(base: Schedule) -> None:
    """``build_workbook_fact_sheet`` has BOTH populations: versions loaded, and versions that
    could be prepared for diffing. When the second is under two, the gap is stated, not skipped."""
    versions = _workbook(base, 4, cut_at={1})
    cpms = [compute_cpm(v) for v in versions]
    facts = build_workbook_fact_sheet(
        versions, cpms, pair_schedules=versions[:1], pair_cpms=cpms[:1]
    )
    blob = _blob(facts)
    assert "4 version(s) are loaded, but fewer than two of them could be prepared" in blob
    assert "missing analysis, NOT an absence of signals" in blob
    assert_all_cited(facts)


def test_an_uncomparable_pair_does_not_shrink_the_STATED_version_count(base: Schedule) -> None:
    """``len(steps) + 1`` is not the version count: an uncomparable pair removes a step without
    removing the versions, and deriving it made a 4-version workbook claim "all 2 loaded
    version(s) were compared" while also asserting "every update is here"."""
    from schedule_forensics.engine import pair_series as mod

    versions = _workbook(base, 4, cut_at=set())
    real = mod.compute_cpm

    def fake(sch: Schedule, *a: object, **k: object) -> object:
        if sch.source_file == "v03.mpp":  # breaks the v02->v03 and v03->v04 pairs
            raise mod.CPMError("synthetic: this network does not solve")
        return real(sch, *a, **k)  # type: ignore[arg-type]

    mod.compute_cpm = fake  # type: ignore[assignment]
    try:
        text = pairwise_comparison_facts(versions)[0].text
    finally:
        mod.compute_cpm = real  # type: ignore[assignment]

    assert "all 4 loaded version(s)" in text, "the STATED count must be the versions loaded"
    assert "1 comparison(s)" in text, "only one pair was actually comparable"
    # and the completeness claim must retract itself when it is no longer true
    assert "every update is here" not in text
    assert "which is not every update in the workbook" in text
    assert "v02.mpp → v03.mpp" in text and "v03.mpp → v04.mpp" in text
    assert "unmeasured, NOT signal-free" in text


def test_the_completeness_claim_stands_when_every_pair_WAS_compared(base: Schedule) -> None:
    """The control for the test above: with nothing uncomparable the strong claim is correct."""
    text = _facts(_workbook(base, 4, cut_at={1}))[0].text
    assert "all 4 loaded version(s)" in text
    assert "3 comparison(s)" in text
    assert "every update is here, not just the newest pair" in text
    assert "could NOT be compared" not in text
