"""Exhibits layer (ADR-0184) — golden-first tests per the master prompt §8: payload
validation (loud failures), structural render assertions (element counts, provenance footer,
the EX-01 <pattern>, EX-03 rebaseline breaks, EX-04 CIC-null gaps), determinism (double-run
byte equality), the air gap (no external URL in any emitted file), and the CLI exit-code
matrix. No pixel-diff image regression by design."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from schedule_forensics.exhibits.csvout import CSV_WRITERS
from schedule_forensics.exhibits.payload import (
    ExhibitPayload,
    canonical_json,
    load_payload,
    run_id_for,
    states,
)
from schedule_forensics.exhibits.render_svg import EXHIBITS, render_ex01_barcode
from schedule_forensics.exhibits.report_html import render_report

FIXTURE = Path(__file__).parent / "fixtures" / "payload_small.json"


@pytest.fixture(scope="module")
def payload() -> ExhibitPayload:
    return load_payload(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_exercises_all_six_states_and_gaps(payload: ExhibitPayload) -> None:
    seen = {c.state for c in payload.cells}
    assert seen == set(states())
    assert any(u.cic is None and u.cic_null_reason for u in payload.update_summaries)
    assert any(t.crosses_rebaseline for t in payload.transitions)
    assert any((f.recompute_delta_nonzero_task_count or 0) > 0 for f in payload.manifest.files)
    assert any(f.recompute_delta_nonzero_task_count is None for f in payload.manifest.files)


def test_payload_missing_field_fails_loud() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del doc["cells"][0]["state"]
    with pytest.raises(ValueError):
        load_payload(json.dumps(doc))
    doc2 = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc2["extra_top_level"] = 1  # unknown fields are rejected too (extra="forbid")
    with pytest.raises(ValueError):
        load_payload(json.dumps(doc2))


def test_run_id_is_deterministic_and_timestamp_free() -> None:
    a = run_id_for(["cc" * 32, "aa" * 32], {"basis": "correct", "tf": 0})
    b = run_id_for(["aa" * 32, "cc" * 32], {"tf": 0, "basis": "correct"})
    assert a == b and len(a) == 16  # order/key-order independent, stable


def test_every_exhibit_renders_with_provenance_footer(payload: ExhibitPayload) -> None:
    for ex_id, (stem, renderer) in EXHIBITS.items():
        svg = renderer(payload)
        assert svg.startswith("<svg"), ex_id
        assert f"run {payload.manifest.run_id}" in svg, ex_id
        assert "basis=correct" in svg and "lf_mode=strict" in svg, ex_id
        assert "unmatched=1" in svg and "transitions n=6" in svg, ex_id
        assert "var(--" not in svg, f"{ex_id} leaked a CSS variable into standalone SVG"
        assert stem


def test_ex01_barcode_structure(payload: ExhibitPayload) -> None:
    svg = render_ex01_barcode(payload)
    # constraint-critical cells reference the hatch <pattern> (grayscale survivability)
    assert 'fill="url(#sfHatch)"' in svg
    assert "<pattern" in svg
    # instability sort: the flappers (T8/T3/T2) must appear ABOVE the stable spine task T1
    y_of = {}
    for uid in (1, 2, 8):
        m = re.search(rf'<text x="186" y="(\d+)"[^>]*>{uid} ', svg)
        assert m, uid
        y_of[uid] = int(m.group(1))
    assert y_of[8] < y_of[1] and y_of[2] < y_of[1]
    # six-state legend present
    for st in states():
        assert st in svg


def test_ex03_breaks_at_rebaseline_and_marks_edits(payload: ExhibitPayload) -> None:
    svg = EXHIBITS["EX-03"][1](payload)
    # exactly one rebaseline boundary in the fixture -> exactly one boundary line and TWO
    # observed-churn segments (the line never connects across the boundary)
    assert svg.count('class="rebaseline"') == 1
    assert svg.count('class="churn-seg"') == 2
    assert "n=6 transitions" in svg
    assert "✎" in svg  # above-median edit-count transitions are marked


def test_ex04_cic_null_renders_gap_with_reason(payload: ExhibitPayload) -> None:
    svg = EXHIBITS["EX-04"][1](payload)
    assert svg.count('class="cic-gap"') == 1
    assert "re-baselined at this update" in svg
    assert svg.count('class="cic-seg"') == 2  # the gap splits the trend into two segments
    assert "⚠" in svg  # driving-tree-incomplete marker


def test_ex07_two_series_one_axis(payload: ExhibitPayload) -> None:
    svg = EXHIBITS["EX-07"][1](payload)
    assert svg.count('class="edge-series"') == 1
    assert svg.count('class="task-series"') == 1
    assert 'stroke-dasharray="5 3"' in svg  # dash-pattern separates the series (not color alone)


def test_csv_siblings_carry_the_rendered_rows(payload: ExhibitPayload) -> None:
    for ex_id, writer in CSV_WRITERS.items():
        text = writer(payload)
        assert text.splitlines()[0], ex_id  # a header row exists
    ex03 = CSV_WRITERS["EX-03"](payload).splitlines()
    assert len(ex03) == 1 + 6  # header + six transitions
    ex06 = CSV_WRITERS["EX-06"](payload)
    assert "weighted_instability" in ex06.splitlines()[0]


def test_report_html_is_self_contained(payload: ExhibitPayload) -> None:
    html = render_report(payload)
    assert "<script" not in html
    assert html.count("<svg") == len(EXHIBITS)
    assert "page-break-inside: avoid" in html


def test_air_gap_no_external_urls(payload: ExhibitPayload) -> None:
    outputs = [render_report(payload)]
    outputs += [r(payload) for _s, r in EXHIBITS.values()]
    outputs += [w(payload) for w in CSV_WRITERS.values()]
    for text in outputs:
        for needle in ('src="http', 'href="http', "url(http"):
            assert needle not in text


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "schedule_forensics.exhibits.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_code_matrix(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    # 0: success from the fixture payload
    r = _run_cli(["--payload", str(FIXTURE), "--out", str(out), "--json-summary"])
    assert r.returncode == 0, r.stderr
    assert (out / "report.html").exists() and (out / "summary.json").exists()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == "f1x7ure0golden01"
    assert summary["nonzero_recompute_delta_files"] == ["IMS_2025-04-30.mpp"]
    # 5: refuse a non-empty out dir without --force
    assert _run_cli(["--payload", str(FIXTURE), "--out", str(out)]).returncode == 5
    # 2: unreadable payload
    r2 = _run_cli(["--payload", str(tmp_path / "nope.json"), "--out", str(tmp_path / "o2")])
    assert r2.returncode == 2
    # 3: --inputs without a terminus
    dummy = tmp_path / "a.xml"
    dummy.write_text("<x/>", encoding="utf-8")
    assert _run_cli(["--inputs", str(dummy), "--out", str(tmp_path / "o3")]).returncode == 3
    # 4: engine artifacts missing for real inputs (parked live wiring, disclosed)
    r4 = _run_cli(["--inputs", str(dummy), "--target-uid", "1", "--out", str(tmp_path / "o4")])
    assert r4.returncode == 4 and "engine artifacts missing" in r4.stderr
    # 2: --inputs naming a missing file
    assert (
        _run_cli(
            [
                "--inputs",
                str(tmp_path / "ghost.mpp"),
                "--target-uid",
                "1",
                "--out",
                str(tmp_path / "o5"),
            ]
        ).returncode
        == 2
    )


def test_double_run_is_byte_identical(tmp_path: Path) -> None:
    hashes = []
    for run in ("one", "two"):
        out = tmp_path / run
        r = _run_cli(["--payload", str(FIXTURE), "--out", str(out), "--json-summary"])
        assert r.returncode == 0, r.stderr
        digest = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir())}
        hashes.append(digest)
    assert hashes[0] == hashes[1]


def test_static_and_interactive_consume_identical_bytes(payload: ExhibitPayload) -> None:
    """Parity gate §5.5: the embed string and the renderer input are the SAME serialization."""
    embedded = canonical_json(payload)
    rendered_from = canonical_json(load_payload(embedded))
    assert embedded == rendered_from


def test_cli_main_in_process(tmp_path: Path) -> None:
    """The same matrix through main() directly (coverage twin of the subprocess test)."""
    from schedule_forensics.exhibits import cli

    out = tmp_path / "pack"
    assert cli.main(["--payload", str(FIXTURE), "--out", str(out), "--json-summary"]) == 0
    for ex_id, (stem, _r) in EXHIBITS.items():
        assert (out / f"{ex_id}_{stem}.svg").exists()
        assert (out / f"{ex_id}_{stem}.csv").exists()
    assert cli.main(["--payload", str(FIXTURE), "--out", str(out)]) == cli.EXIT_OUT_NOT_EMPTY
    assert cli.main(["--payload", str(FIXTURE), "--out", str(out), "--force"]) == 0
    assert (
        cli.main(["--payload", str(tmp_path / "missing.json"), "--out", str(tmp_path / "a")])
        == cli.EXIT_INGEST
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert cli.main(["--payload", str(bad), "--out", str(tmp_path / "b")]) == cli.EXIT_INGEST
    dummy = tmp_path / "in.xml"
    dummy.write_text("<x/>", encoding="utf-8")
    assert cli.main(["--inputs", str(dummy), "--out", str(tmp_path / "c")]) == cli.EXIT_NO_TERMINUS
    assert (
        cli.main(["--inputs", str(dummy), "--target-uid", "1", "--out", str(tmp_path / "d")])
        == cli.EXIT_ENGINE_MISSING
    )
    assert (
        cli.main(
            [
                "--inputs",
                str(tmp_path / "ghost.mpp"),
                "--target-uid",
                "1",
                "--out",
                str(tmp_path / "e"),
            ]
        )
        == cli.EXIT_INGEST
    )
    assert cli.main(["--out", str(tmp_path / "f")]) == cli.EXIT_INGEST
    # single-format runs
    assert (
        cli.main(["--payload", str(FIXTURE), "--out", str(tmp_path / "g"), "--format", "html"]) == 0
    )
    assert (tmp_path / "g" / "report.html").exists()
    assert (
        cli.main(["--payload", str(FIXTURE), "--out", str(tmp_path / "h"), "--format", "csv"]) == 0
    )
