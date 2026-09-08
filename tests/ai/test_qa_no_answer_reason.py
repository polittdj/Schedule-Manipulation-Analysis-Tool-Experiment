"""Ask-the-AI names WHY it produced no prose (the five silent no-answer paths).

Measured defect (operator field report, 32-version workbook): five materially different
failures — the routed backend is Null, the model server refuses a generation (HTTP 404 for a
model that is not installed), the generation times out, the model returns an empty completion,
and strict mode discards the answer — all returned a byte-identical payload, so the panel
printed ONE sentence naming only two of them. The operator, whose AI Settings showed a
configured model, was told "no local model is active".

``answer_question_detail`` is the diagnosis at the layer that KNOWS: the qa layer sees the
backend, the exception and the gate verdict. It never sees the operator's configuration — that
half belongs to the web layer (``tests/web/test_ask_no_answer_reason.py``).
"""

from __future__ import annotations

import urllib.error

from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.qa import (
    DISCARDED_UNSOURCED,
    EMPTY_ANSWER,
    GENERATION_FAILED,
    NO_MODEL,
    answer_question,
    answer_question_detail,
    build_fact_sheet,
)
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import compute_completion_performance, compute_float_bands
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.schedule import Schedule


class _Model:
    """A fake local model whose reply — or failure — is configurable."""

    name = "ollama"
    is_local = True

    def __init__(self, reply: str = "", boom: BaseException | None = None) -> None:
        self.reply = reply
        self.boom = boom

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        if self.boom is not None:
            raise self.boom
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


def test_no_model_is_reported_as_no_model(golden_project5: Schedule) -> None:
    answer, used, why = answer_question_detail(NullBackend(), _facts(golden_project5), "how?")
    assert answer is None and used
    assert why is not None and why.code == NO_MODEL


def test_a_refused_generation_is_reported_as_a_generation_failure(
    golden_project5: Schedule,
) -> None:
    """Ollama answers ``/api/tags`` (so routing picks it) and 404s ``/api/generate`` when the
    selected model is not installed. That is NOT "no local model is active"."""
    boom = urllib.error.HTTPError("http://127.0.0.1:11434/api/generate", 404, "Not Found", {}, None)  # type: ignore[arg-type]
    answer, used, why = answer_question_detail(_Model(boom=boom), _facts(golden_project5), "how?")
    assert answer is None and used
    assert why is not None and why.code == GENERATION_FAILED
    assert "404" in why.detail  # the status the server actually returned, not a guess


def test_a_timed_out_generation_says_it_timed_out(golden_project5: Schedule) -> None:
    boom = urllib.error.URLError(TimeoutError("timed out"))
    _answer, _used, why = answer_question_detail(_Model(boom=boom), _facts(golden_project5), "?")
    assert why is not None and why.code == GENERATION_FAILED
    assert "timed out" in why.detail.lower()


def test_an_empty_completion_is_its_own_code(golden_project5: Schedule) -> None:
    _answer, _used, why = answer_question_detail(_Model("   \n"), _facts(golden_project5), "?")
    assert why is not None and why.code == EMPTY_ANSWER


def test_strict_discard_names_the_figure_it_discarded_over(golden_project5: Schedule) -> None:
    facts = _facts(golden_project5)
    model = _Model("The programme carries 987654 days of hidden float.")
    answer, used, why = answer_question_detail(model, facts, "how bad?", mode="strict")
    assert answer is None and used
    assert why is not None and why.code == DISCARDED_UNSOURCED
    assert "987654" in why.detail  # the operator can see WHICH figure cost them the answer


def test_a_kept_answer_carries_no_failure(golden_project5: Schedule) -> None:
    """The negative half: a reason that fires when the answer survives is a reason that means
    nothing. Annotate KEEPS an unsourced figure (flagged), so it must report no failure."""
    facts = _facts(golden_project5)
    answer, _used, why = answer_question_detail(
        _Model("The programme carries 987654 days of hidden float."), facts, "?", mode="annotate"
    )
    assert answer is not None and why is None
    grounded = _Model(f"Per the facts: {facts[0].text}")
    answer2, _used2, why2 = answer_question_detail(grounded, facts, "frame?", mode="strict")
    assert answer2 is not None and why2 is None


def test_the_two_tuple_form_is_unchanged(golden_project5: Schedule) -> None:
    """``answer_question`` is the published 2-tuple API a dozen call sites use; the detail form
    is additive. Same inputs, same first two values."""
    facts = _facts(golden_project5)
    for model, mode in (
        (NullBackend(), "annotate"),
        (_Model("   "), "annotate"),
        (_Model("The programme carries 987654 days of hidden float."), "strict"),
        (_Model(f"Per the facts: {facts[0].text}"), "strict"),
    ):
        pair = answer_question(model, facts, "how?", mode=mode)
        triple = answer_question_detail(model, facts, "how?", mode=mode)
        assert pair == triple[:2]
