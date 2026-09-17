"""R-49 (ADR-0490): an ABSENT ``TotalSlack`` on a ``Critical`` task is a ZERO when the file carries
the element elsewhere — because the vendored MPXJ MSPDI writer omits zero durations.

Provenance, measured on the intake ``.mpp`` files through the vendored MPXJ itself (a Java probe
against ``org.mpxj``): on ``Large Test File2.mpp`` the reader holds ``TotalSlack = 0.0d`` for all
62 critical activities whose element the written XML lacks, and NULL for none (786 zero slacks in
memory, 0 literal zeros in the XML); the project's critical-slack threshold is ``0.0d``. So an
absent element on a task the file flags ``Critical`` can only be a zero: MS Project flags Critical
exactly when slack ≤ the threshold, and a NEGATIVE slack is always written (123 of them on that
file). The inference is bounded twice — never on a file that carries no ``TotalSlack`` at all (a
writer that never emits the element is not one that dropped a zero), and never on a task the file
does not flag Critical — until R-62 (ADR-0507, 2026-09-18) retired that second bound: the writer's
rule is class-blind, so every absent slack in a file that carries the element is the dropped zero
(``test_mspdi_absent_slack_is_zero.py`` carries the provenance). The Critical pins below still hold;
the two that asserted ``None`` for a non-Critical absent slack were re-derived on that date.

Why it matters (Law 2): ``effective_total_float`` prefers the source tool's STORED, progress-aware
slack and falls back to the engine's pure-logic CPM float only when the file carried none — so the
zero-slack subset, and ONLY that subset, was silently scored on the other basis. On every fixture in
the repo but one the two bases agreed to the minute for those tasks (Fuse's Zero Days Float 66 / 2
on the Large Test Files was already exact); on ``Hard_File`` they did not: UID 241 recomputed to
480 min and UID 249 to 360 min where MS Project stored 0 — the red-first this module was observed
to fail on (2026-09-14), on a real file, before the importer changed. Those two recomputed floats
were the R-64 chain's artefact: milestone 216 hands UID 241 a Friday-noon instant the project axis
rendered a day early, and 249 follows it. ADR-0505 carries the instant, and the two bases now agree
on every stored-zero Critical activity of every golden (34 on Hard_File) — the engine's own float
for 241 and 249 is 0. The inference is still what makes the STORED basis a zero; its red-first
lives in the synthetic cases below, which no engine change can touch.
"""

from __future__ import annotations

import gzip
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics._common import effective_total_float, non_summary
from schedule_forensics.importers.json_schedule import parse_json_text, to_json_text
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _gz(rel: str) -> Schedule:
    path = GOLDEN / rel
    return parse_mspdi_text(gzip.decompress(path.read_bytes()).decode("utf-8"), source_file=rel)


def _mspdi(tasks: str) -> Schedule:
    return parse_mspdi_text(
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate><Tasks>{tasks}</Tasks></Project>"
    )


#: A (5 d) and B (2 d) both feed the milestone M; C (1 d) too. Pure logic: A critical, B 3 d of
#: float, C 4 d. The FILE says: C carries a stored slack (4 d = 19 200 tenths of a minute), A and B
#: are Critical with the element ABSENT (what MPXJ writes for a zero), D is not Critical and absent,
#: E carries no Critical element at all.
_SYNTHETIC = (
    "<Task><UID>1</UID><Name>A</Name><Duration>PT40H0M0S</Duration><Critical>1</Critical></Task>"
    "<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration><Critical>1</Critical></Task>"
    "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration><Critical>0</Critical>"
    "<TotalSlack>19200</TotalSlack></Task>"
    "<Task><UID>4</UID><Name>D</Name><Duration>PT8H0M0S</Duration><Critical>0</Critical></Task>"
    "<Task><UID>5</UID><Name>E</Name><Duration>PT8H0M0S</Duration></Task>"
    "<Task><UID>9</UID><Name>M</Name><Duration>PT0H0M0S</Duration><Milestone>1</Milestone>"
    "<Critical>1</Critical>"
    "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
    "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
    "<PredecessorLink><PredecessorUID>3</PredecessorUID><Type>1</Type></PredecessorLink>"
    "</Task>"
)


def test_an_absent_slack_on_a_critical_task_is_zero_when_the_file_carries_the_element() -> None:
    sch = _mspdi(_SYNTHETIC)
    by = sch.tasks_by_id
    assert by[3].stored_total_float_minutes == 1920  # the carried element, tenths → minutes
    assert by[1].stored_total_float_minutes == 0  # Critical, absent → the writer dropped a zero
    assert by[2].stored_total_float_minutes == 0
    assert by[9].stored_total_float_minutes == 0  # a critical milestone likewise
    # R-62 (ADR-0507): the writer drops EVERY zero, so a non-Critical absent slack is a zero too —
    # re-derived 2026-09-18 from ``None`` (ADR-0490's deliberate second bound, now measured away)
    assert by[4].stored_total_float_minutes == 0
    assert by[5].stored_total_float_minutes == 0
    assert by[4].stored_is_critical is False and by[5].stored_is_critical is None


def test_no_inference_on_a_file_that_carries_no_total_slack_at_all() -> None:
    """A writer that never emits the element did not drop a zero; Critical alone proves nothing."""
    sch = _mspdi(_SYNTHETIC.replace("<TotalSlack>19200</TotalSlack>", ""))
    assert all(t.stored_total_float_minutes is None for t in sch.tasks)
    assert sch.tasks_by_id[1].stored_is_critical is True  # the flag itself is untouched


def test_the_inferred_zero_is_the_effective_float_where_pure_logic_says_otherwise() -> None:
    """The point of the rule: the stored-preferring basis now covers the zero-slack subset.
    Re-derived 2026-09-18 (R-62, ADR-0507): D's absent slack is the file's own zero as well, so
    the recomputed-float FALLBACK is reached only on a file that carries no element at all."""
    sch = _mspdi(_SYNTHETIC)
    cpm = compute_cpm(sch)
    b = sch.tasks_by_id[2]
    assert cpm.timings[2].total_float == 3 * 480  # pure logic: B has three days
    assert effective_total_float(b, float(cpm.timings[2].total_float)) == 0.0  # the file's own
    d = sch.tasks_by_id[4]
    assert cpm.timings[4].total_float == 4 * 480  # pure logic: D has four days
    assert effective_total_float(d, float(cpm.timings[4].total_float)) == 0.0  # the file's own
    bare = _mspdi(_SYNTHETIC.replace("<TotalSlack>19200</TotalSlack>", ""))
    assert effective_total_float(bare.tasks_by_id[4], 4 * 480.0) == 4 * 480  # the fallback


def test_hard_file_uids_241_and_249_read_the_stored_zero_and_the_engine_now_agrees() -> None:
    """The one fixture in the repo where the two bases disagreed for a Critical task with an
    absent element: pure logic gave 480 and 360 minutes on the pre-ADR-0505 engine (the R-64
    chain: milestone 216's Friday-noon instant rendered a day early, UID 241 started from it);
    MS Project stored 0 and flagged both Critical. Red first on the pristine importer: the
    stored basis was None. The engine's own float is 0 now — and pinned, so a regression of
    the carried instant fails here by name as well as in the stored-dates oracle."""
    sch = _gz("fuse_hardfile/Hard_File.mspdi.xml.gz")
    cpm = compute_cpm(sch)
    for uid in (241, 249):
        t = sch.tasks_by_id[uid]
        assert t.stored_is_critical is True
        assert t.stored_total_float_minutes == 0  # the importer's inference: the stored basis
        assert cpm.timings[uid].total_float == 0  # the engine's own float, since ADR-0505
        # the stored basis wins whatever is recomputed
        assert effective_total_float(t, 480.0) == 0.0


def test_large_test_file2_infers_exactly_the_62_absent_critical_zeros() -> None:
    """62 of Fuse's 66 zero-float activities carry no element (the register's own count); the
    other four carry a stored slack that rounds to a whole-day zero (12, -139, 100, 12 min).
    Re-derived 2026-09-18 (R-62, ADR-0507): the completed activities the writer also zeroed read
    0 now as well, so the incomplete zeros are selected by progress, and nothing stays unknown."""
    sch = _gz("fuse_ltf/Large_Test_File2.mspdi.xml.gz")
    ts = non_summary(sch)
    inferred = [t for t in ts if t.stored_total_float_minutes == 0 and t.percent_complete < 100]
    assert len(inferred) == 62
    assert all(t.stored_is_critical for t in inferred)
    per_day = sch.calendar.working_minutes_per_day or 480
    rounds_to_zero = [
        t
        for t in ts
        if t.stored_total_float_minutes not in (None, 0)
        and round(t.stored_total_float_minutes / per_day) == 0
    ]
    assert sorted(t.unique_id for t in rounds_to_zero) == [844, 906, 5283, 7015]
    # the completed activities the writer also zeroed: 724 of them, every one a zero, none unknown
    done = [t for t in ts if t.percent_complete >= 100]
    assert len(done) == 724 and all(t.stored_total_float_minutes == 0 for t in done)
    assert not [t for t in ts if t.stored_total_float_minutes is None]


def test_fuse_zero_days_float_66_and_2_stay_exact_on_the_stored_basis() -> None:
    """Fuse's Zero Days Float (the Metric History, ADR-0473's workbook): 66 on Large Test File2,
    2 on Large Test File. Green on both trees by construction — on these two files every inferred
    zero recomputes to a zero as well — and pinned so the inference can never move them."""
    for rel, fuse in (
        ("fuse_ltf/Large_Test_File2.mspdi.xml.gz", 66),
        ("fuse_ltf/Large_Test_File.mspdi.xml.gz", 2),
    ):
        sch = _gz(rel)
        cpm = compute_cpm(sch)
        per_day = sch.calendar.working_minutes_per_day or 480
        zero = [
            t
            for t in non_summary(sch)
            if t.percent_complete < 100
            and round(
                effective_total_float(t, float(cpm.timings[t.unique_id].total_float)) / per_day
            )
            == 0
        ]
        assert len(zero) == fuse, rel


def test_the_inferred_zero_survives_the_tools_own_save_format() -> None:
    sch = _mspdi(_SYNTHETIC)
    again = parse_json_text(to_json_text(sch))
    assert again.tasks_by_id[1].stored_total_float_minutes == 0
    assert again.tasks_by_id[4].stored_total_float_minutes == 0  # R-62: a zero too, and it survives
