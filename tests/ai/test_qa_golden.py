"""Golden Q&A regression — pins WHICH cited facts a representative analyst question grounds the AI
on, for a committed golden schedule. The model is variable; the *grounding* must be stable, so a
change to fact-building or fact-selection that silently moves what a question retrieves fails here.

Deterministic: exercises ``build_fact_sheet`` + ``relevant_facts`` only (no live model).
"""

from __future__ import annotations

import pytest

from schedule_forensics.ai.qa import build_fact_sheet, relevant_facts
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import (
    compute_completion_performance,
    compute_float_bands,
)
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.schedule import Schedule


def _facts(schedule: Schedule):  # type: ignore[no-untyped-def]
    cpm = compute_cpm(schedule)
    return build_fact_sheet(
        schedule,
        cpm,
        audit_schedule(schedule, cpm),
        recommend(schedule, current_cpm=cpm),
        compute_float_bands(schedule, cpm),
        compute_completion_performance(schedule),
        compute_finish_forecasts(schedule, cpm),
    )


#: (analyst question, a token the SELECTED facts must contain). Each row is a grounding contract:
#: this question must reach a fact carrying this token, or the AI loses its evidence for the answer.
_GROUNDING = [
    ("how many hard constraints are there?", "Hard Constraints"),
    ("what does the finish forecast say?", "Finish forecast"),
    ("how is progress / completion performance?", "Completion performance"),
    ("how much total float is there?", "Float band"),
    ("what problems or findings exist?", "Finding ["),
    ("what share of DCMA checks pass?", "pass rate"),  # Layer A derived fact (ADR-0133)
]


@pytest.mark.parametrize("question,expected", _GROUNDING)
def test_question_grounds_on_the_expected_fact_family(
    question: str, expected: str, golden_project5: Schedule
) -> None:
    facts = _facts(golden_project5)
    selected = relevant_facts(facts, question)
    assert selected, question
    assert selected[0] is facts[0]  # the frame fact always leads (stable anchor)
    blob = " ".join(f.text for f in selected)
    assert expected in blob, f"{question!r} no longer grounds on a fact containing {expected!r}"


def test_every_selected_fact_is_cited_and_bounded(golden_project5: Schedule) -> None:
    """Whatever a question retrieves, every grounding fact carries a citation and the selection
    stays bounded (no padding back to the full sheet — the 'same answer no matter what you ask'
    regression)."""
    facts = _facts(golden_project5)
    for question, _ in _GROUNDING:
        selected = relevant_facts(facts, question)
        assert 1 <= len(selected) <= len(facts)
        assert all(f.citations for f in selected), question
