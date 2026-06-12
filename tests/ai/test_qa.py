"""Grounded Q&A tests — cited fact sheet, relevance, and the no-invented-numbers gate."""

from __future__ import annotations

from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.qa import answer_question, build_fact_sheet, relevant_facts
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import (
    compute_completion_performance,
    compute_float_bands,
)
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.schedule import Schedule


class _Model:
    """A fake local model whose reply is configurable."""

    name = "ollama"
    is_local = True

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


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


def test_fact_sheet_is_fully_cited_and_covers_the_families(golden_project5: Schedule) -> None:
    facts = _facts(golden_project5)
    assert len(facts) > 10
    assert_all_cited(facts)  # §6 — every fact carries file + UID + task
    text = " ".join(f.text for f in facts)
    for token in ("Schedule frame", "Finish forecast", "DCMA", "Float band", "Finding"):
        assert token in text


def test_relevant_facts_match_question_terms(golden_project5: Schedule) -> None:
    facts = _facts(golden_project5)
    chosen = relevant_facts(facts, "what does the finish forecast say?")
    assert chosen[0] is facts[0]  # the frame fact always leads
    assert any("forecast" in f.text.lower() for f in chosen[1:4])
    # a vague question still returns a bounded, non-empty selection
    assert 1 <= len(relevant_facts(facts, "??")) <= 12


def test_null_backend_returns_facts_not_prose(golden_project5: Schedule) -> None:
    answer, used = answer_question(NullBackend(), _facts(golden_project5), "how many critical?")
    assert answer is None and used  # no model -> no generated prose, only cited facts


def test_grounded_answer_survives_and_invented_numbers_are_discarded(
    golden_project5: Schedule,
) -> None:
    facts = _facts(golden_project5)
    # an answer quoting only fact figures survives
    grounded = _Model(f"Per the facts: {facts[0].text}")
    answer, _ = answer_question(grounded, facts, "what is the schedule frame?")
    assert answer is not None and "Schedule frame" in answer
    # one invented figure discards the whole answer (Law 2)
    fabricator = _Model("The project will finish in 99999 days.")
    answer2, used2 = answer_question(fabricator, facts, "when will it finish?")
    assert answer2 is None and used2

    # a dying model degrades to the facts, never an error
    class _Boom(_Model):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("gone")

    answer3, used3 = answer_question(_Boom(""), facts, "anything?")
    assert answer3 is None and used3
