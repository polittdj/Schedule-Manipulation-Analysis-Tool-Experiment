"""Executable reproducers for the AUDIT-2026-09-23 findings in the EXP lane (A0923-EXP-001).

Campaign: AUDIT-2026-09-23, session 7, base 0b45eb28 (v1.0.294). AUDIT + PLAN ONLY: the audit
changed nothing under ``src/``; these tests are the evidence a fixing PR inherits. The EXP lane
is the static exhibit pack -- ``schedule_forensics.exhibits``: the ``schedule-forensics-report``
console script, its SVG / HTML / CSV renderers and the payload contract (ADR-0184).

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Everything runs in-process through ``exhibits.cli.main`` -- the function the console script binds
to (``pyproject.toml`` ``[project.scripts]``) -- writing a real pack into ``tmp_path`` (no server,
no browser, no subprocess). Inputs are the already-committed, non-CUI fixture
``tests/exhibits/fixtures/payload_small.json`` edited in memory; no fixture file is added; an
autouse fixture refuses every non-loopback connect and name lookup. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_exp.py -rxX``.
"""

from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.exhibits import cli

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _air_gapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """No way off the machine: a non-loopback connect or any name lookup other than a loopback
    literal raises before a packet is sent (the CLI opens no socket; this pins that it never
    starts to)."""
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


# --------------------------------------------------------------------------------------------
# A0923-EXP-001 (T3): the exhibit pack's provenance line floors tf_threshold_minutes on a fixed
# 480-minute day, so a positive threshold prints as 'tf_threshold=0wd' in report.html and in
# every SVG footer while the pack's own payload.json carries the field verbatim
# --------------------------------------------------------------------------------------------
_EXP_001_FIXTURE = (
    Path(__file__).resolve().parent.parent / "exhibits" / "fixtures" / "payload_small.json"
)
_EXP_001_TOKEN = re.compile(r"tf_threshold=(\S+)")
_EXP_001_VALUE = re.compile(r"([0-9]+(?:\.[0-9]+)?)(min|wd)")
_EXP_001_ASSUMED_DAY = 480  # the only day a 'wd' in the footer can mean: RunManifest carries none


def _exp_001_minutes(token: str) -> int | None:
    """The threshold a printed token states, in the payload's own unit (minutes) -- ``None`` when
    the token cannot be read back exactly (a floored or otherwise lossy figure, or no figure)."""
    m = _EXP_001_VALUE.fullmatch(token)
    if m is None:
        return None
    number, unit = m.groups()
    if unit == "min":
        return int(number) if number.isdigit() else None
    minutes = float(number) * _EXP_001_ASSUMED_DAY
    return int(minutes) if minutes == int(minutes) else None


def _exp_001_pack(tmp_path: Path, tf_minutes: int) -> tuple[int, int | None, dict[str, list[str]]]:
    """Render the committed fixture with ONLY manifest.tf_threshold_minutes changed, through the
    function the console script binds to; return (exit code, the field the written pack's
    payload.json carries, {surface: every printed 'tf_threshold=' token})."""
    doc = json.loads(_EXP_001_FIXTURE.read_text(encoding="utf-8"))
    doc["manifest"]["tf_threshold_minutes"] = tf_minutes
    payload = tmp_path / f"payload_{tf_minutes}.json"
    payload.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / f"pack_{tf_minutes}"
    rc = cli.main(["--payload", str(payload), "--out", str(out)])
    if rc != 0:
        return rc, None, {}
    written = json.loads((out / "payload.json").read_text(encoding="utf-8"))
    tokens: dict[str, list[str]] = {}
    for surface in ["report.html", *sorted(f.name for f in out.glob("*.svg"))]:
        text = (out / surface).read_text(encoding="utf-8")
        tokens[surface] = _EXP_001_TOKEN.findall(text)
    return rc, int(written["manifest"]["tf_threshold_minutes"]), tokens


def _exp_001_wrong(tokens: dict[str, list[str]], tf_minutes: int) -> dict[str, str]:
    """Surfaces whose tf_threshold token(s) do not read back to the field (or carry none)."""
    wrong: dict[str, str] = {}
    for surface, printed in tokens.items():
        bad = [t for t in printed if _exp_001_minutes(t) != tf_minutes]
        if not printed:
            wrong[surface] = "no tf_threshold token"
        elif bad:
            wrong[surface] = " ".join(f"{t} x{bad.count(t)}" for t in sorted(set(bad)))
    return wrong


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-EXP-001: the exhibit pack's provenance line prints tf_threshold_minutes // 480 "
    "as 'wd' (report_html.py:53; render_svg.py:59 in every SVG footer) -- a floor on a fixed "
    "480-minute day the payload does not carry -- so 240 / 720 / 1200 minutes print as "
    "'tf_threshold=0wd' / '1wd' / '2wd' in report.html and 9 of 9 SVG footers while the pack's "
    "payload.json carries the field verbatim",
)
def test_a0923_exp_001_the_provenance_line_states_the_threshold_the_payload_carries(
    tmp_path: Path,
) -> None:
    """Claim (as verified by P3 and P6): at 0b45eb28 the exhibits CLI's only working path
    (``schedule-forensics-report --payload P --out D`` -> ``exhibits.cli.main``) renders the
    committed fixture payload with only manifest.tf_threshold_minutes changed to 240 / 720 / 1200
    as 'tf_threshold=0wd' / '1wd' / '2wd' in report.html (10 tokens: the meta line + the 9 inline
    SVGs) and in 9 of 9 standalone SVG provenance footers -- ``tf_threshold_minutes // 480`` at
    report_html.py:53 and render_svg.py:59 (``_footer``, drawn by every EXHIBITS renderer): a
    FLOOR on a fixed 480-minute day, while the same pack's payload.json carries the field verbatim
    (240 / 720 / 1200). Whole multiples of 480 (0, 480) print right -- the control. The non-480-day
    leg is UNREACHABLE (``--inputs`` exits 4; no payload builder in src; RunManifest carries no
    minutes-per-day) and is not asserted.

    Authority: src/schedule_forensics/exhibits/render_svg.py:9-10 "Rendering rules (hard rails):
    ZERO arithmetic beyond axis scaling/tick placement -- every value drawn is a payload field; no
    wall-clock reads; gaps render as GAPS with the payload's stated reason, never interpolation";
    src/schedule_forensics/exhibits/payload.py:3 "Pydantic v2, validated on load: a missing field is
    a LOUD failure, never a defaulted zero."; docs/adr/0184-cp-volatility-exhibits-layer.md:26 "zero
    render-time arithmetic beyond axis scaling". Hand arithmetic: 240 / 480 = 0.5, 720 / 480 = 1.5,
    1200 / 480 = 2.5 working days on the 480 the label assumes; the floor prints 0 / 1 / 2.

    Tier: T3 (latent; not LAW-1) -- the provenance line that makes a screenshot citable misstates
    the run's float-threshold basis; no exhibit figure moves. Correct = every printed token reads
    back to the payload field without loss: the field verbatim ('240min', the rail's own form) or an
    exact day figure on the assumed 480 ('0.5wd'); a floored figure is neither.
    """
    if not _EXP_001_FIXTURE.is_file():
        pytest.fail(f"precondition: the committed fixture {_EXP_001_FIXTURE} is present")
    committed = json.loads(_EXP_001_FIXTURE.read_text(encoding="utf-8"))
    if committed["manifest"].get("tf_threshold_minutes") != 0:
        pytest.fail("precondition: the committed fixture carries manifest.tf_threshold_minutes 0")
    # control: whole multiples of the assumed day read back exactly on the audited tree too
    for tf in (0, 480):
        rc, field, tokens = _exp_001_pack(tmp_path, tf)
        if rc != 0 or field != tf:
            pytest.fail(f"precondition: the pack renders (exit {rc}) and payload.json carries {tf}")
        if len(tokens) != 10 or len(tokens["report.html"]) != 10:
            pytest.fail(f"precondition: report.html + 9 SVGs, 10 tokens in report.html: {tokens}")
        if _exp_001_wrong(tokens, tf):
            pytest.fail(f"precondition (control): {tf} min reads back on every surface: {tokens}")
    problems: dict[str, dict[str, str]] = {}
    for tf in (240, 720, 1200):
        rc, field, tokens = _exp_001_pack(tmp_path, tf)
        if rc != 0 or field != tf:
            pytest.fail(f"precondition: the pack renders (exit {rc}) and payload.json carries {tf}")
        wrong = _exp_001_wrong(tokens, tf)
        svg_wrong = {k: v for k, v in wrong.items() if k.endswith(".svg")}
        if len(svg_wrong) == 9 and len(set(svg_wrong.values())) == 1:
            wrong = {k: v for k, v in wrong.items() if not k.endswith(".svg")}
            wrong["9 of 9 svg footers"] = next(iter(svg_wrong.values()))
        if wrong:
            problems[f"tf_threshold_minutes={tf} (payload.json {field})"] = wrong
    assert problems == {}, (
        "the provenance line does not state the payload's tf_threshold_minutes (hand: 240 = 0.5 wd "
        "on the 480 the label assumes, 720 = 1.5, 1200 = 2.5; the field verbatim in minutes is the "
        f"rail's own form): {problems}"
    )
