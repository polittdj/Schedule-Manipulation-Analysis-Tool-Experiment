"""ADR-0348 against the oracle: MS Project's own stored dates, on the committed corpus.

The reference tool wrote a Start and a Finish for every task. Where the engine's CPM agrees
with MS Project on the **finish**, any remaining disagreement on the **start** is attributable
to the wall-clock spelling of the offset and to nothing else — no constraint, no progress, no
scheduling semantics. Before ADR-0348 that residual was 66 of 67 comparable Project5 tasks.

A second guard is a census: no ``offset_to_datetime`` call site in ``src/`` may be handed a
start-role offset again, which is how CC-01 would come back.
"""

from __future__ import annotations

import ast
import gzip
import re
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime, span_start_datetime
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
SRC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics"


def _load(rel: str) -> Schedule:
    path = GOLDEN / rel
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return parse_mspdi_text(raw.decode("utf-8"), source_file=path.name)


@pytest.mark.parametrize("rel", ["evm/EVM1.mspdi.xml", "project2_5/Project5.mspdi.xml"])
def test_a_rendered_start_matches_the_date_ms_project_stored(rel: str) -> None:
    sch = _load(rel)
    cpm = compute_cpm(sch)
    ps, cal = sch.project_start, sch.calendar

    compared = 0
    for task in sch.tasks:
        timing = cpm.timings.get(task.unique_id)
        if timing is None or task.is_summary:
            continue
        if task.start is None or task.finish is None:
            continue
        early_finish = max(timing.early_finish, 0)
        rendered_finish = offset_to_datetime(ps, early_finish, cal).date()
        if rendered_finish != task.finish.date():
            continue  # the engine and MSP disagree on the schedule itself, not on spelling
        rendered_start = span_start_datetime(ps, max(timing.early_start, 0), early_finish, cal)
        compared += 1
        assert rendered_start.date() == task.start.date(), (
            f"{task.name!r}: rendered {rendered_start.date()} but MS Project stored "
            f"{task.start.date()}"
        )
    assert compared >= 10, f"oracle population too small to be meaningful ({compared})"


@pytest.mark.parametrize("rel", ["evm/EVM1.mspdi.xml", "ssi_uid152/Large_Test_File.mspdi.xml.gz"])
def test_no_task_renders_its_start_after_its_finish(rel: str) -> None:
    """The inversion a naive start-spelling introduces on every milestone."""
    sch = _load(rel)
    cpm = compute_cpm(sch)
    ps, cal = sch.project_start, sch.calendar
    for task in sch.tasks:
        timing = cpm.timings.get(task.unique_id)
        if timing is None or task.is_summary:
            continue
        early_finish = max(timing.early_finish, 0)
        start = span_start_datetime(ps, max(timing.early_start, 0), early_finish, cal)
        finish = offset_to_datetime(ps, early_finish, cal)
        assert start <= finish, f"{task.name!r} renders start {start} after finish {finish}"


#: An offset expression naming a start is a start role; naming a finish is a finish role.
_START_ROLE = re.compile(r"early_start|late_start|start_offset|\bstart_ord\b")
_FINISH_ROLE = re.compile(r"early_finish|late_finish|project_finish|finish_offset|finish_ord")


#: ``span_start_datetime`` is the sanctioned implementation of the rule: its zero-duration
#: branch spells a start with the end-of-day form deliberately. The census is about its
#: *consumers*, so its own body is the one exemption — named, not a blanket file skip.
_SANCTIONED = "span_start_datetime"


def _start_role_call_sites() -> list[str]:
    """Every ``offset_to_datetime`` call in ``src/`` handed an unambiguously start-role offset."""
    found: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "offset_to_datetime" not in source:
            continue
        tree = ast.parse(source)
        exempt: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == _SANCTIONED:
                exempt.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) < 2:
                continue
            if node.lineno in exempt:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "offset_to_datetime":
                continue
            offset = ast.unparse(node.args[1])
            if _START_ROLE.search(offset) and not _FINISH_ROLE.search(offset):
                found.append(f"{path.name}:{node.lineno} offset={offset}")
    return found


def test_no_start_role_offset_is_spelled_with_offset_to_datetime() -> None:
    """CC-01's reintroduction guard — use ``span_start_datetime`` for a start (ADR-0348)."""
    assert _start_role_call_sites() == []


def test_the_census_guard_can_actually_see_a_start_role_call() -> None:
    """Vacuity check: the detector must fire on the shape it is meant to catch."""
    node = ast.parse("offset_to_datetime(ps, timing.early_start, cal)").body[0]
    assert isinstance(node, ast.Expr)
    call = node.value
    assert isinstance(call, ast.Call)
    offset = ast.unparse(call.args[1])
    assert _START_ROLE.search(offset) and not _FINISH_ROLE.search(offset)
