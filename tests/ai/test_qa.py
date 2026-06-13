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
    # one invented figure discards the whole answer (strict mode)
    fabricator = _Model("The project will finish in 99999 days.")
    answer2, used2 = answer_question(fabricator, facts, "when will it finish?")
    assert answer2 is None and used2

    # a dying model degrades to the facts, never an error
    class _Boom(_Model):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("gone")

    answer3, used3 = answer_question(_Boom(""), facts, "anything?")
    assert answer3 is None and used3


def test_interpretive_mode_keeps_derived_figures_but_still_grounds(
    golden_project5: Schedule,
) -> None:
    """M18 "AI at full power": the model may COMPUTE from the facts (a derived figure no
    longer discards the answer) — the cited facts still ride along, and the Null/failed
    paths stay fail-closed."""
    facts = _facts(golden_project5)
    deriver = _Model("The slip works out to 42 working days beyond the baseline.")
    answer, used = answer_question(deriver, facts, "how bad is it?", mode="interpretive")
    assert answer is not None and "42" in answer  # derived figure survives
    assert used  # the cited facts always accompany the answer
    assert "compute" in deriver.prompts[-1]  # the interpretive prompt was used
    # the same reply in strict mode is discarded wholesale
    answer2, _ = answer_question(
        _Model("The slip works out to 42 working days beyond the baseline."),
        facts,
        "how bad is it?",
        mode="strict",
    )
    assert answer2 is None
    # Null backend and failures stay fail-closed in interpretive mode too
    answer3, used3 = answer_question(NullBackend(), facts, "anything?", mode="interpretive")
    assert answer3 is None and used3


def test_figure_agreement_is_deterministic_and_names_the_disagreement() -> None:
    from schedule_forensics.ai.qa import figure_agreement

    same = figure_agreement("Finish slips 12 days (SPI 0.47).", "SPI 0.47 means 12 days late.")
    assert "identical figures" in same
    differ = figure_agreement("The slip is 12 days.", "The slip is 15 days.")
    assert "DIFFER" in differ and "12" in differ and "15" in differ
    assert "verify against the cited facts" in differ
    # figure-free prose counts as agreement (nothing to contradict)
    assert "identical" in figure_agreement("It is slipping.", "The schedule is late.")


def test_workbook_fact_sheet_spans_versions_and_is_cited(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    from schedule_forensics.ai.qa import build_workbook_fact_sheet

    schedules = [golden_project2, golden_project5]
    cpms = [compute_cpm(s) for s in schedules]
    facts = build_workbook_fact_sheet(schedules, cpms)
    assert_all_cited(facts)  # §6 — every fact carries file + UID + task
    text = " ".join(f.text for f in facts)
    assert "Schedule Forensics analysis" in text  # the workbook frame
    assert "Project2" in text and "Project5" in text  # both versions narrated
    assert "Latest-version finish forecast" in text
    assert "over time" in text  # the cross-version quality-trend sentences are present
