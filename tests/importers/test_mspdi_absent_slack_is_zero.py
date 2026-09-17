"""R-62 (ADR-0507): EVERY absent ``TotalSlack`` in a file that carries the element is the ZERO the
vendored MPXJ writer dropped — completed activities and summaries as much as ADR-0490's Critical
ones.

Provenance, measured on the vendored MPXJ 16.2.0 and the 29 intake ``.mpp`` files (2026-09-17):

* The writer's ``DatatypeConverter.printDurationInIntegerTenthsOfMinutes`` returns ``null`` for a
  null duration AND for one whose value is ``0.0`` — read off the bytecode, so a zero slack is never
  an element.
* MPXJ's ``Task.getTotalSlack()`` is a calculated field: the MPP reader maps the file's stored
  ``START_SLACK`` and ``FINISH_SLACK`` (``FieldMap14``, fixed-data offsets 28 / 32) and never a
  total, and ``MicrosoftSlackCalculator`` derives the total from those two — the smaller of them
  for an unstarted task, the finish slack for a started one. Microsoft's own field reference
  states the same rule: *"the smaller value of the Late Finish minus the Early Finish field, and
  the Late Start minus the Early Start field"*.
* Over all 29 files (17,402 task rows) the element is absent for exactly the tasks whose computed
  total is ``0.0`` — 7,095 of 7,095, none of them null: 5,466 completed activities, 583 Critical
  incomplete ones, 1,046 summaries and **no other class**. For 7,030 of them the file's own stored
  start AND finish slack are both zero; the other 65 (summaries and unstarted Critical tasks) carry
  one zero member, so MS Project's own rule on MS Project's own stored fields reads 0 for every one.
  Every completed activity in the corpus stores the pair (0, 0), and none carries the element.

So an absent element in a file the writer produced is a zero — whatever the task's class — and the
only guard the inference needs is the one ADR-0490 already had: the FILE carries the element
somewhere (a writer that never emits it dropped nothing). The Critical guard was the row's
conservatism, not the mechanism's; this module is where it is retired, red first on the pristine
importer (a completed activity read ``None``, rendered as an em-dash where MS Project shows ``0d``).
"""

from __future__ import annotations

import gzip
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.float_erosion import compute_float_erosion
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


#: One carried slack (C, 4 d) proves the writer emits the element; every other task is absent:
#: A Critical (ADR-0490's case), D not Critical and unstarted, E with no Critical element at all,
#: F COMPLETED (the R-62 case), S a summary. The writer's rule is class-blind: each is a zero.
_SYNTHETIC = (
    "<Task><UID>1</UID><Name>A</Name><Duration>PT40H0M0S</Duration><Critical>1</Critical></Task>"
    "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration><Critical>0</Critical>"
    "<TotalSlack>19200</TotalSlack></Task>"
    "<Task><UID>4</UID><Name>D</Name><Duration>PT8H0M0S</Duration><Critical>0</Critical></Task>"
    "<Task><UID>5</UID><Name>E</Name><Duration>PT8H0M0S</Duration></Task>"
    "<Task><UID>6</UID><Name>F</Name><Duration>PT8H0M0S</Duration><Critical>0</Critical>"
    "<PercentComplete>100</PercentComplete>"
    "<ActualStart>2025-01-06T08:00:00</ActualStart>"
    "<ActualFinish>2025-01-06T17:00:00</ActualFinish></Task>"
    "<Task><UID>7</UID><Name>S</Name><Duration>PT40H0M0S</Duration><Summary>1</Summary>"
    "<Critical>0</Critical></Task>"
)


def test_every_absent_slack_is_zero_when_the_file_carries_the_element() -> None:
    sch = _mspdi(_SYNTHETIC)
    by = sch.tasks_by_id
    assert by[3].stored_total_float_minutes == 1920  # the carried element, tenths → minutes
    assert by[1].stored_total_float_minutes == 0  # Critical (ADR-0490's inference, unchanged)
    assert by[4].stored_total_float_minutes == 0  # not Critical: the writer's rule is class-blind
    assert by[5].stored_total_float_minutes == 0  # no Critical element: the flag is no evidence
    assert by[6].stored_total_float_minutes == 0  # COMPLETED — R-62's own case
    assert by[7].stored_total_float_minutes == 0  # a summary's zero is dropped the same way
    # the flag itself is untouched by the inference
    assert by[4].stored_is_critical is False and by[5].stored_is_critical is None


def test_no_inference_on_a_file_that_carries_no_total_slack_at_all() -> None:
    """CONTROL, green on both trees: a writer that never emits the element did not drop a zero, so
    every absent slack — the completed task's included — stays unknown, never a fabricated 0."""
    sch = _mspdi(_SYNTHETIC.replace("<TotalSlack>19200</TotalSlack>", ""))
    assert all(t.stored_total_float_minutes is None for t in sch.tasks)
    assert sch.tasks_by_id[6].percent_complete == 100.0


def test_hard_file_updated3_reads_zero_for_its_42_completed_activities() -> None:
    """The row's witness: 42 completed activities carry no element on this golden (the probe's
    stored pair is (0, 0) for each); MS Project shows ``0d``; the pristine importer read
    ``None``."""
    sch = _gz("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    ns = non_summary(sch)
    done = [t for t in ns if t.percent_complete >= 100.0]
    assert len(done) == 42
    assert all(t.stored_total_float_minutes == 0 for t in done)
    assert all(not t.stored_is_critical for t in done)  # MS Project never flags finished work
    assert not [t for t in ns if t.stored_total_float_minutes is None]  # nothing is unknown
    absent_summaries = [t for t in sch.tasks if t.is_summary and t.stored_total_float_minutes == 0]
    assert len(absent_summaries) == 8  # the writer drops a summary's zero the same way


def test_large_test_file2_carries_the_probes_786_zeros() -> None:
    """ADR-0490's probe held 786 zero slacks in memory for this file's 1,722 non-summary tasks —
    62 Critical incomplete (which it inferred) and 724 completed (which it left ``None``). The
    importer now reproduces the probe's count exactly, and nothing stays unknown."""
    sch = _gz("fuse_ltf/Large_Test_File2.mspdi.xml.gz")
    ns = non_summary(sch)
    zeros = [t for t in ns if t.stored_total_float_minutes == 0]
    assert len(zeros) == 786
    assert sum(1 for t in zeros if t.percent_complete >= 100.0) == 724
    assert sum(1 for t in zeros if t.percent_complete < 100.0 and t.stored_is_critical) == 62
    assert not [t for t in ns if t.stored_total_float_minutes is None]


def test_the_completed_zero_survives_the_tools_own_save_format() -> None:
    sch = _mspdi(_SYNTHETIC)
    again = parse_json_text(to_json_text(sch))
    assert again.tasks_by_id[6].stored_total_float_minutes == 0
    assert again.tasks_by_id[4].stored_total_float_minutes == 0


def test_float_erosion_is_unmoved_by_a_completed_activitys_stored_zero() -> None:
    """The census the row asked for found ONE metric reading a completed activity's slack: float
    erosion by WBS, which scored finished work on the engine's recomputed float (the file's zero
    having been dropped) — four of Hard_File_updated4's groups read RED on completed work. Its
    population is now incomplete activities (ADR-0507), so the inferred zeros cannot reach it:
    the figures are identical whether the completed tasks carry 0 or ``None``. Green on the
    pristine tree by construction (both sides read ``None`` there); its teeth are the mutant that
    puts completed work back into the population, red by name."""
    sch = _gz("ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz")
    stripped = sch.model_copy(
        update={
            "tasks": tuple(
                t.model_copy(update={"stored_total_float_minutes": None})
                if t.percent_complete >= 100.0
                else t
                for t in sch.tasks
            )
        }
    )
    assert sum(1 for t in sch.tasks if t.percent_complete >= 100.0) > 0
    a = compute_float_erosion(sch, compute_cpm(sch))
    b = compute_float_erosion(stripped, compute_cpm(stripped))
    assert a == b
