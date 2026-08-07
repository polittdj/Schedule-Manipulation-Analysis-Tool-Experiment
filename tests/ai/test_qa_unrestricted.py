"""The UNRESTRICTED Ask-the-AI mode (ADR-0361): full model power, still fully local.

The operator's opt-in beyond interpretive: the model is INVITED to calculate new figures and
interpret without restraint, and the caller may feed it the bounded per-activity data table
as raw material. The answer is returned verbatim — no figure gate, no identifier gate, no
unit gate. What does NOT change: the backend is the same loopback-validated one every mode
uses (Law 1 lives at backend construction), and the Null backend still answers nothing.
"""

from __future__ import annotations

from schedule_forensics.ai.citations import Citation, CitedStatement
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.qa import answer_question


class _Model:
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


def _fact() -> tuple[CitedStatement, ...]:
    return (
        CitedStatement(
            text="The project finish is 2029-04-19 with 14 critical activities.",
            citations=(Citation(source_file="s.mpp", unique_id=152, task_name="Finish"),),
        ),
    )


def test_unrestricted_returns_invented_figures_verbatim() -> None:
    """The very answer strict discards and annotate flags comes back untouched here —
    the operator opted into ungated calculation (774 appears in no cited fact)."""
    model = _Model("My computed slip is 774 days, a figure I derived myself.")
    text, shown = answer_question(model, _fact(), "how bad is it?", mode="unrestricted")
    assert text == "My computed slip is 774 days, a figure I derived myself."
    assert shown  # the cited facts still ride along for verification
    assert "[AI-derived" not in text


def test_unrestricted_feeds_the_data_block_and_invites_calculation() -> None:
    model = _Model("ok")
    block = "UID|Name|Dur(d)\n152|Finish|0"
    answer_question(model, _fact(), "q", mode="unrestricted", data_block=block)
    prompt = model.prompts[0]
    assert "ACTIVITY DATA:" in prompt and block in prompt
    assert "MAY calculate new figures" in prompt
    assert "unrestricted" in prompt.lower()
    # other modes never receive the block, even if a caller passes one
    model2 = _Model("ok")
    answer_question(model2, _fact(), "q", mode="annotate", data_block=block)
    assert "ACTIVITY DATA:" not in model2.prompts[0]


def test_unrestricted_still_fails_closed_on_the_null_backend() -> None:
    """No local model => no prose, in every mode — unrestricted relaxes the gates, never
    the locality (Law 1)."""
    text, shown = answer_question(NullBackend(), _fact(), "q", mode="unrestricted")
    assert text is None
    assert shown
