"""Narrative tests — cited story on the golden P5-vs-P2, backend rephrasing, clean schedule."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


class _ShoutBackend:
    """A fake model that rephrases (upper-cases) — proves citations survive rephrasing."""

    name = "shout"
    is_local = True

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("shout",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return prompt.upper()


class _FabricatorBackend(_ShoutBackend):
    """A fake model that invents a figure — its rephrases must all be discarded."""

    name = "fabricator"

    def generate(self, prompt: str) -> str:
        return "Everything is fine, only 12345 minor issues remain."


def test_golden_narrative_is_fully_cited(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    narrative = build_narrative(golden_project5, golden_project2, target_uid=143)
    assert narrative.statements
    assert_all_cited(narrative.statements)  # §6.D — every statement cited
    text = narrative.to_text()
    assert "99 calendar days" in text  # the headline slip is told
    assert "Project2.mspdi.xml → Project5.mspdi.xml" in narrative.title


def test_backend_rephrases_text_but_keeps_citations(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    p2, p5 = golden_project2, golden_project5
    plain = build_narrative(p5, p2)
    shouted = build_narrative(p5, p2, backend=_ShoutBackend())
    # same number of statements + identical citations, but rephrased (upper-cased) prose
    assert len(shouted.statements) == len(plain.statements)
    assert [s.citations for s in shouted.statements] == [s.citations for s in plain.statements]
    assert any(s.text.isupper() for s in shouted.statements if s.text.strip())
    assert_all_cited(shouted.statements)


def test_figure_mangling_backend_falls_back_to_verbatim_statements(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    # the fabricator replaces every statement with invented numbers; the figure gate in
    # reattach must discard each rephrase, leaving the deterministic narrative verbatim
    plain = build_narrative(golden_project5, golden_project2)
    mangled = build_narrative(golden_project5, golden_project2, backend=_FabricatorBackend())
    assert [s.text for s in mangled.statements] == [s.text for s in plain.statements]
    assert "12345" not in mangled.to_text()


def test_clean_schedule_gets_cited_clean_bill() -> None:
    # all-complete, resourced FS chain: no DCMA / compliance / manipulation findings fire
    tasks = [
        Task(
            unique_id=i,
            name=f"T{i}",
            duration_minutes=DAY,
            percent_complete=100.0,
            resource_names=("Crew",),
        )
        for i in (1, 2, 3)
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
    ]
    clean = Schedule(name="clean", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    narrative = build_narrative(clean)
    assert len(narrative.statements) >= 1
    assert_all_cited(narrative.statements)  # even the clean-bill statement cites the finish driver
    assert "well-formed" in narrative.to_text()
