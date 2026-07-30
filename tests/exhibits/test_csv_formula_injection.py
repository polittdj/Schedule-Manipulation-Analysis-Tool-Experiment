"""CSV exhibits must not hand a spreadsheet a formula to run (ADR-0313).

`csv.writer` quotes for CSV **grammar**; quoting does nothing about Excel/LibreOffice evaluating a
cell that begins `=`, `+`, `-`, `@`. These exhibits carry **task names straight from the schedule
file** — content the tool did not author and, in a delay-claim context, content an opposing party
may have written. So the vector is not hypothetical: it is "open the auditability twin of my
exhibit in Excel".

Also asserted here: the `.xlsx` writer needs **no** equivalent guard. That was verified, not
assumed — `reports/xlsx.py` emits every string as `t="inlineStr"` inside `<is><t>` and never emits
an `<f>` element, so Excel shows `=1+1` as literal text. The completion plan's item 5 named
"spreadsheet formula injection on export" and pointed at the workbook writer; measuring first
showed the workbook is safe and the CSV sibling is not.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from schedule_forensics.exhibits.csvout import _defuse, _emit
from schedule_forensics.reports.tables import Table, TableSet
from schedule_forensics.reports.xlsx import render_xlsx

TRIGGERS = ("=1+1", "+1+1", "-1+1", "@SUM(A1)", "=cmd|' /C calc'!A0", "\tlead", "\rlead")


@pytest.mark.parametrize("payload", TRIGGERS)
def test_a_leading_formula_trigger_is_defused_in_csv(payload: str) -> None:
    out = _emit(["Task name"], [[payload]])
    body = out.splitlines()[1]
    assert body.lstrip('"').startswith("'"), f"{payload!r} reached the cell unescaped: {body!r}"


def test_a_real_negative_number_is_not_mangled() -> None:
    """The guard must discriminate by TYPE, not by leading character. A float of -5 is the number
    -5; turning it into the text `'-5` would corrupt every negative float/slack column in every
    exhibit — a far worse outcome than the injection it was guarding."""
    assert _defuse(-5) == -5
    assert _defuse(-0.25) == -0.25
    assert _defuse(0) == 0
    assert _defuse(True) is True
    out = _emit(["Float"], [[-5], [-0.25]])
    assert out.splitlines()[1:] == ["-5", "-0.25"]


def test_ordinary_text_is_untouched() -> None:
    assert _defuse("Install piping") == "Install piping"
    assert _defuse("Phase 2 — rework") == "Phase 2 — rework"
    assert _emit(["n"], [["Install piping"]]).splitlines()[1] == "Install piping"


def test_none_still_reads_as_an_explicit_gap() -> None:
    """`csvout`'s module contract: "explicit empty string for None (a gap stays visibly a gap)."."""
    assert _emit(["a", "b"], [[None, 1]]).splitlines()[1] == ",1"


def test_the_xlsx_writer_is_not_a_formula_vector_and_needs_no_guard() -> None:
    """Pinned so nobody 'fixes' the workbook writer by cargo-culting the CSV guard onto it — that
    would prefix a visible apostrophe onto legitimate exhibit text for no security gain."""
    table = Table(title="t", headers=("Name",), rows=(("=1+1",), ("@SUM(A1)",)))
    raw = render_xlsx(TableSet(title="ts", tables=(table,)))
    sheet = next(n for n in zipfile.ZipFile(io.BytesIO(raw)).namelist() if "sheet1" in n)
    xml = zipfile.ZipFile(io.BytesIO(raw)).read(sheet).decode()
    assert "<f>" not in xml, "an <f> element WOULD make the workbook evaluate operator text"
    assert 't="inlineStr"' in xml
    assert "<t>=1+1</t>" in xml, "the text is stored verbatim, as text — that is the safe form"


def test_the_guard_is_a_no_op_on_the_committed_exhibit_corpus() -> None:
    """Blast-radius bound. These CSVs are the exhibits' *auditability twin* — they must reproduce
    exactly what the renderer consumed, so a guard that added stray apostrophes to real content
    would be a regression, not a fix. No string in the committed payload begins with a trigger."""
    import json
    from pathlib import Path

    payload = Path(__file__).parent / "fixtures" / "payload_small.json"
    data = json.loads(payload.read_text(encoding="utf-8"))
    hits: list[tuple[str, str]] = []

    def walk(node: object, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and node[:1] in ("=", "+", "-", "@", "\t", "\r"):
            hits.append((path, node))

    walk(data)
    assert hits == [], f"a real exhibit string would now be prefixed: {hits[:5]}"
