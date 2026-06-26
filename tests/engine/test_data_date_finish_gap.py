"""Guard the pure-logic-CPM vs source-tool-stored finish gap (audit F-02 / ADR-0108).

The engine's CPM is intentionally *pure-logic*: it does not floor an in-progress activity's
remaining duration at the data date, so on an out-of-sequence / progressed schedule it can compute
a finish *earlier* than the source tool's progress-aware (stored) finish — understating the slip.
TP4 v5 (the falsified-baseline manipulation case) is the canonical example: MS Project's stored
finish is 2026-07-17, but pure-logic CPM computes 2026-06-26.

This was a HIGH audit finding precisely because it was **unguarded** and TEST-PROJECTS.md overstated
its numbers as "pinned by tests" when the battery only asserted ``finish > 0``. This test pins both
sides so the gap cannot silently change, and confirms the "As-scheduled (stored dates)" forecast
method now surfaces the stored finish alongside the understated CPM finish (so it is no longer
hidden from the analyst). The fix is *surfacing + guarding*, NOT an engine reschedule (two attempts
to make the CPM data-date-aware regressed Acumen/EVM parity and were reverted — ADR-0108).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.importers.mspdi import parse_mspdi

TP4_V5 = (
    Path(__file__).resolve().parents[1] / "fixtures" / "test_projects" / "TP4_DataCenter_v5.xml"
)


def test_tp4_v5_pure_logic_cpm_understates_the_stored_finish() -> None:
    sch = parse_mspdi(TP4_V5)

    # pure-logic CPM finish — the (understated) date the engine computes
    cpm = compute_cpm(sch)
    cpm_finish = offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar).date()
    assert cpm_finish == dt.date(2026, 6, 26)

    # the source tool's stored (progress-aware) finish — ~3 weeks later
    stored_finish = max(t.finish for t in sch.tasks if t.finish is not None).date()
    assert stored_finish == dt.date(2026, 7, 17)
    assert stored_finish > cpm_finish  # the gap the engine does NOT close (ADR-0108)


def test_as_scheduled_forecast_surfaces_the_stored_finish() -> None:
    """The fix for F-02: the stored finish is now a first-class forecast method, so the analyst
    sees the source-tool finish next to the pure-logic CPM finish rather than only the latter."""
    fs = compute_finish_forecasts(parse_mspdi(TP4_V5))
    by_id = {f.method_id: f.finish for f in fs.forecasts}
    assert by_id["cpm"] == dt.date(2026, 6, 26)
    assert by_id["as_scheduled"] == dt.date(2026, 7, 17)  # surfaced, not hidden
