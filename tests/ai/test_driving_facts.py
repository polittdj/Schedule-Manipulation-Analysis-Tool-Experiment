"""Per-UID driving-path facts for Ask-the-AI — the engine answers, the model only narrates.

The local model kept getting "driving path to UID X" / "how many drive X at 0 slack" wrong, so the
engine's exact, SSI-parity driving-slack result is injected as cited facts; these tests pin that the
counts/citations are the engine's and that injection is gated on a named UID + driving intent.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.driving_facts import driving_path_facts, driving_path_summary
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON, DAY = dt.datetime(2025, 1, 6, 8, 0), 480


def _t(uid: int, days: float) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(days * DAY))


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s)


def _network() -> Schedule:
    # long A(5d) -> C(5d) -> D(1d) drives D at 0 slack; short E(1d) -> D carries slack (not driver)
    return Schedule(
        name="s",
        project_start=MON,
        tasks=(_t(1, 5), _t(3, 5), _t(4, 1), _t(5, 1)),
        relationships=(_r(1, 3), _r(3, 4), _r(5, 4)),
    )


def test_summary_counts_only_zero_slack_drivers() -> None:
    s = _network()
    facts = driving_path_summary(s, compute_cpm(s), 4)
    assert facts
    assert "2 activities driving it with 0 days of driving slack" in facts[0].text
    cited = {c.unique_id for c in facts[0].citations}
    assert {1, 3} <= cited  # the long path drives D
    assert 5 not in cited  # E carries slack — NOT a driver


def test_summary_empty_for_unknown_uid() -> None:
    s = _network()
    assert driving_path_summary(s, compute_cpm(s), 999) == ()


def test_facts_require_both_intent_and_a_named_uid() -> None:
    s = _network()
    cpm = compute_cpm(s)
    assert driving_path_facts(s, cpm, "how many critical activities are there?") == ()  # no UID
    assert driving_path_facts(s, cpm, "tell me about UID 4") == ()  # UID but no driving intent
    facts = driving_path_facts(s, cpm, "what is the driving path to UID 4?")
    assert facts and "UID 4" in facts[0].text


def test_facts_do_not_treat_unrelated_numbers_as_uids() -> None:
    s = _network()
    # "0 days" must NOT be parsed as a focus UID — only the keyword-prefixed "UID 4" is
    facts = driving_path_facts(s, compute_cpm(s), "driving path with 0 days of slack to UID 4")
    assert facts and "UID 4" in facts[0].text
