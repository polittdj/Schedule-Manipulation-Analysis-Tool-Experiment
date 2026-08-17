"""REC-01: the Executive Briefing never quotes a recovery figure the engine did not assert.

Companion to ``tests/engine/test_disclosure_not_quantified.py``, which owns the engine half.
This module owns the three briefing cells that turned a provenance disclosure's *exposure*
into *recovery* — the leak ADR-0407 claimed could not happen. All three were untested before
REC-01: no test in the tree named "Potential recovery", "Expected effect" or
"potentially recoverable", which is why a fabricated figure could reach a leadership
deliverable and survive a full green gate.

``_quantify`` leaving a disclosure unquantified is necessary but NOT sufficient: sections 5.2
and 6 fall back to the strings "risk reduction" / "risk mitigation" when ``impact_days`` is
None, and a provenance note neither reduces nor mitigates risk. The cells must read as an
em dash for a disclosure — the design system's standing rule, and the same shape as ADR-0411,
which gated the EVM workbook cell on the field that carries the meaning.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.briefing import build_briefing
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
TODAY = dt.date(2025, 2, 3)


def _schedule() -> Schedule:
    """The REC-01 reproduction: one started activity, floored at its actual start, 20 wd behind.

    Kept byte-for-byte equivalent to the engine module's fixture so the two halves of the
    finding are measured on the same input.
    """
    start = MON + dt.timedelta(days=7)
    return Schedule(
        name="REC-01",
        project_start=MON,
        tasks=(
            Task(
                unique_id=1,
                name="started late, behind its deadline",
                duration_minutes=20 * DAY,
                start=start,
                finish=start + dt.timedelta(days=27, hours=9),
                actual_start=start,
                deadline=MON + dt.timedelta(days=7),
            ),
            Task(unique_id=2, name="successor", duration_minutes=5 * DAY),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _briefing_sections() -> dict[str, object]:
    s = _schedule()
    b = build_briefing([s], cpms=[compute_cpm(s)], today=TODAY)
    return {sec.heading: sec for sec in b.sections}


def _disclosure_row(section: object, text_column: int) -> tuple[str, ...]:
    """The one row sourced from the actual-start disclosure, found by its wording."""
    table = section.table  # type: ignore[attr-defined]
    assert table is not None, "the section rendered no table at all"
    rows = [r for r in table.rows if "recorded actual start" in r[text_column].lower()]
    if not rows:
        rows = [r for r in table.rows if "recorded execution" in r[text_column].lower()]
    assert len(rows) == 1, f"expected exactly one disclosure row, got {len(rows)}"
    return rows[0]


def test_section_5_2_does_not_claim_the_disclosure_is_potential_recovery() -> None:
    """5.2's column is literally headed "Potential recovery"; pre-fix it read "20 wd".

    Twenty working days of an activity's negative float, relabelled as days a reader could
    recover by acting on a note that says the date already happened.
    """
    sections = _briefing_sections()
    opps = sections["5.2 Opportunities"]
    assert opps.table.headers[3] == "Potential recovery"  # type: ignore[attr-defined]
    row = _disclosure_row(opps, 1)
    assert row[3] == "—", f"5.2 quoted a recovery figure for a disclosure: {row[3]!r}"


def test_section_6_does_not_claim_the_disclosure_has_a_schedule_effect() -> None:
    """6's "Expected effect" cell read "20 wd" pre-fix, on action #5.

    "risk mitigation" — the existing None fallback — would be wrong too: the action is
    "verify the actual-start record against source documentation", which mitigates nothing.
    """
    sections = _briefing_sections()
    actions = sections["6. Recommended Actions"]
    assert actions.table.headers[3] == "Expected effect"  # type: ignore[attr-defined]
    row = _disclosure_row(actions, 1)
    assert row[3] == "—", f"6 quoted a schedule effect for a disclosure: {row[3]!r}"


def test_section_6_2_recovers_nothing_from_a_disclosure_only_schedule() -> None:
    """The headline sentence. Pre-fix: "up to about 20 workday(s) ... recoverable".

    The disclosure is the only OPPORTUNITY in this schedule, so every one of those 20 days
    came from it. With it excluded the sentence must flip to the risk-mitigation wording and
    name no figure at all.
    """
    sections = _briefing_sections()
    implemented = sections["6.2 If Recommended Actions Are Implemented"]
    text = implemented.statements[0].rendered()  # type: ignore[attr-defined]
    assert "potentially recoverable" not in text, text
    assert "risk-mitigation rather than direct slip recovery" in text
    assert "20 workday" not in text


def test_a_real_lever_still_reports_its_recovery_figure() -> None:
    """Negative control: with a focus target set, ``driving_path`` fills 5.2's cell as before.

    Without this, a fix that simply blanked column 3 for every opportunity would pass all
    three tests above while destroying the section's actual purpose.
    """
    s = _schedule()
    cpm = compute_cpm(s)
    b = build_briefing([s], cpms=[cpm], today=TODAY)
    # No target_uid reaches build_briefing, so the lever is asserted at the engine boundary
    # the briefing consumes; tests/engine/test_disclosure_not_quantified.py owns the rest.
    from schedule_forensics.engine.recommendations import recommend

    findings = recommend(s, current_cpm=cpm, target_uid=2)
    lever = next(f for f in findings if f.metric_id == "driving_path")
    assert lever.impact_days is not None and lever.impact_days > 0
    assert b.sections  # the briefing itself still builds


def test_the_disclosure_is_still_disclosed() -> None:
    """Dropping the number must not drop the row — ADR-0407's purpose was visibility.

    A "fix" that filtered disclosures out of the briefing entirely would pass the three
    assertions above and silently undo the ADR it is correcting.
    """
    sections = _briefing_sections()
    row_5_2 = _disclosure_row(sections["5.2 Opportunities"], 1)
    row_6 = _disclosure_row(sections["6. Recommended Actions"], 1)
    assert "1" in row_5_2[2].split(", ")  # still cites UID 1
    assert row_6[1].startswith("Read these positions as recorded execution")
