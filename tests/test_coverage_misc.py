"""Targeted coverage for the table builders' edge cells and the CUI log redactor's
non-string fallback — narrow branches the broader report/logging suites do not reach.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.path_evolution import (
    CriticalSnapshot,
    PathChange,
    PathEvolution,
)
from schedule_forensics.logging_redaction import _redact_value
from schedule_forensics.reports.tables import (
    activities_table,
    path_evolution_tables,
    trend_tables,
)


def test_trend_tables_returns_empty_for_no_trends() -> None:
    # line 202: an empty trend sequence yields no tables (the multi-version views guard).
    assert trend_tables([]) == ()


def test_path_evolution_tables_emit_entered_and_left_change_rows() -> None:
    # line 411 (and the left-changes companion): a snapshot carrying per-activity attribution
    # rows produces one change row per entered/left PathChange in the "with reasons" table.
    snapshot = CriticalSnapshot(
        label="v2.xml",
        status_date="2025-02-01",
        project_finish="2025-03-31",
        finish_delta_days=5,
        critical=(1, 2),
        entered=(2,),
        left=(3,),
        stayed=(1,),
        duration_changed=(2,),
        shortened_on_path=(),
        removed_logic_count=1,
        entered_changes=(
            PathChange(uid=2, name="Now critical", reason="slack_consumed", detail="a slip"),
        ),
        left_changes=(
            PathChange(uid=3, name="Off path", reason="gained_float", detail="float returned"),
        ),
    )
    summary, changes = path_evolution_tables(PathEvolution(snapshots=(snapshot,)))
    assert summary.title == "Critical-path evolution"
    # one entered + one left change row, each carrying its UID, direction, reason, and detail
    assert changes.rows == (
        ("v2.xml", "entered", 2, "Now critical", "slack_consumed", "a slip"),
        ("v2.xml", "left", 3, "Off path", "gained_float", "float returned"),
    )


def test_activities_table_stringifies_non_primitive_cell_values() -> None:
    # line 440: a cell value that is not None/str/int/float (here a datetime.date) is rendered
    # via str() so the neutral table model stays plain (str | int | float | None) for renderers.
    rows = [{"unique_id": 1, "name": "A", "start": dt.date(2025, 1, 6)}]
    table = activities_table(rows)
    start_index = next(i for i, label in enumerate(table.headers) if label == "Start")
    assert table.rows[0][start_index] == "2025-01-06"  # the date object was stringified


def test_redact_value_stringifies_and_redacts_a_path() -> None:
    # line 140: a non-str, non-container value (a Path) is stringified, then redacted. An
    # absolute directory path becomes an inert <path...> token, never leaking the layout.
    redacted_dir = _redact_value(Path("/home/analyst/secret/cui-archive"))
    assert isinstance(redacted_dir, str)
    assert "/home/analyst/secret" not in redacted_dir  # the absolute path is scrubbed
    assert redacted_dir.startswith("<path")  # replaced by a stable, non-reversible token
    # a Path that IS a sensitive schedule file name redacts to a <file:...> token (same line 140)
    redacted_file = _redact_value(Path("/tmp/Site Alpha.mpp"))
    assert isinstance(redacted_file, str)
    assert "Site Alpha" not in redacted_file
    assert "<file:mpp#" in redacted_file
    # a plain non-path object still routes through str()+redact without leaking sensitive names
    assert _redact_value(dt.date(2025, 1, 6)) == "2025-01-06"  # no CUI -> passes through unchanged
