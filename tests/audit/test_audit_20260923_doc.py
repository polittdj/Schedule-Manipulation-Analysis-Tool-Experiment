"""Executable red/green tests for the 2026-09-23 read-only audit: the DOCUMENTATION findings.

One test per finding id (A0923-DOC-001 .. A0923-DOC-016). Every test here is a
VALIDATED-DEFECT test in the sense of ``test_audit_findings.py``: it asserts the CORRECT state
and FAILS (red) against the audited commit 8c71c639 — that red is the proof the finding is real.
Each is marked ``xfail(strict=True, raises=AssertionError)`` so the suite stays green today AND so
a fix that makes it pass is flagged (XPASS under strict = failure => remove the marker in the
fixing commit, and the test stands as the permanent pin).

Design rule for a documentation finding: the reproducer CHECKS THE CLAIM, it never freezes a
number. Each test parses the document for the statement under audit and compares it with a value
derived from the tree or the engine AT TEST TIME (``wc -l`` of the file, the engine's own figure,
the rendered route, ``git ls-files``). No figure measured by the audit is transcribed as an
expectation. A fixing PR that corrects the statement, or deletes the volatile number or the whole
sentence, makes the test pass: a claim that no longer exists cannot be false.

Scope: where the verifier narrowed the finder's scope, the verifier wins — only present-tense
statements are checked; dated records (a table or sentence under a dated heading that was true
when written) are excluded, and each docstring names what is and is not checked.

Drop-in path: tests/audit/ .  Run: pytest tests/audit/test_audit_20260923_doc.py -rA
"""

from __future__ import annotations

import dataclasses
import gzip
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.engine.metrics import (
    compute_change_metrics,
    compute_float_ratio,
    compute_net_finish_impact,
    compute_ribbon,
    compute_schedule_quality,
)
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

SRC = Path(schedule_forensics.__file__).resolve().parent
REPO = SRC.parent.parent  # .../src/schedule_forensics -> repo root
GOLDEN = REPO / "tests" / "fixtures" / "golden"
TP_DIR = REPO / "tests" / "fixtures" / "test_projects"

_MINUS = "\u2212"  # the docs print negative figures with U+2212 MINUS SIGN


# --------------------------------------------------------------------------------------------
# helpers — reading the documents and the tree
# --------------------------------------------------------------------------------------------
def _read(rel: str) -> str:
    """A tracked document's text; a deleted document carries no claim, so it reads as empty."""
    path = REPO / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _plain(text: str) -> str:
    """Prose as a reader sees it: blockquote and emphasis markers dropped, hard wraps joined."""
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    text = text.replace("**", "").replace(_MINUS, "-")
    return re.sub(r"\s+", " ", text)


def _int(token: str) -> int:
    """'8,037' / '1 666' / '-148' -> int (thousands separators the docs use are dropped)."""
    return int(re.sub(r"[,\s\u00a0\u202f]", "", token).replace(_MINUS, "-"))


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _section(text: str, heading_prefix: str) -> str:
    """The body of the first ``#`` heading that starts with ``heading_prefix`` (to the next one of
    the same or a higher level); empty when the heading is gone."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"(#+) ", line)
        if m and line[m.end() :].startswith(heading_prefix):
            level = len(m.group(1))
            body: list[str] = []
            for nxt in lines[i + 1 :]:
                h = re.match(r"(#+) ", nxt)
                if h and len(h.group(1)) <= level:
                    break
                body.append(nxt)
            return "\n".join(body)
    return ""


def _git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


@cache
def _tracked_files() -> tuple[str, ...]:
    if shutil.which("git") is None:
        pytest.skip("git is not available; tracked-file facts cannot be read")
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=False, env=_git_env()
    )
    if proc.returncode != 0:
        pytest.skip("the tree is not a git work tree; tracked-file facts cannot be read")
    return tuple(p for p in proc.stdout.decode("utf-8").split("\0") if p)


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _load_golden(rel: str) -> Schedule:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    return parse_mspdi_text(text, source_file=Path(rel).name)


@cache
def _golden_pair() -> tuple[Schedule, Schedule]:
    return (
        parse_mspdi(GOLDEN / "project2_5" / "Project2.mspdi.xml"),
        parse_mspdi(GOLDEN / "project2_5" / "Project5.mspdi.xml"),
    )


def _fuse_change() -> dict[str, Any]:
    path = GOLDEN / "project2_5" / "fuse_exports_2026-06.json"
    return json.loads(path.read_text(encoding="utf-8"))["change_P2_to_P5"]


def _load_by_path(name: str, path: Path) -> Any:
    """Load a repo module that is not on sys.path (a tool, or the oracle a doc names)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def _finish_date(sch: Schedule) -> Any:
    res = compute_cpm(sch)
    wall = res.project_finish_wall or offset_to_datetime(
        sch.project_start, res.project_finish, sch.calendar
    )
    return wall.date()


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------------------------
# A0923-DOC-001
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-001: CLAUDE.md states app.py's line count, and the count is not the file's",
)
def test_a0923_doc_001_claude_md_app_py_line_count_is_the_files() -> None:
    """CLAUDE.md's present-tense size figure for ``web/app.py`` must be the file's line count.

    Claim (A0923-DOC-001): at 8c71c639 ``wc -l src/schedule_forensics/web/app.py`` is not the
    figure CLAUDE.md states for it (the figure was exact at ADR-0390 and app.py has since grown).
    Authority (verbatim), CLAUDE.md:274-275: "re-exported from `app.py` with the `X as X` idiom so
    old import paths keep working. `app.py` is down from 17,197 lines to **8,037**." The ruler is
    the project's own "wc-truth" (docs/adr/0390...:33-34). Checked: every "`app.py` is down/up
    from N lines to M" sentence; the historical "from 17,197" anchor is not checked. Tier T3.
    """
    text = _plain(_read("CLAUDE.md"))
    stated = [
        _int(m.group(1))
        for m in re.finditer(
            r"`app\.py` is (?:now )?(?:down|up) from [\d,]+ lines to ([\d,]+)", text
        )
    ]
    actual = (SRC / "web" / "app.py").read_bytes().count(b"\n")  # wc -l
    assert all(n == actual for n in stated), (
        f"CLAUDE.md says app.py is {stated} lines; wc -l counts {actual}"
    )


# --------------------------------------------------------------------------------------------
# A0923-DOC-002
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-002: README/USER-GUIDE say the dropzone takes 'up to 100 at once'; /upload "
    "loads 101",
)
def test_a0923_doc_002_documented_upload_limit_is_the_routes_behaviour() -> None:
    """A documented "up to N at once" import limit must be what ``POST /upload`` does with N+1.

    Claim (A0923-DOC-002): at 8c71c639 POST /upload of 101 distinct schedules through the
    in-process app loads all 101, while the user docs state a 100-file limit (the cap was removed
    deliberately by ADR-0225; the docs were not re-synced). Authority (verbatim): README.md:67-68
    "drag a file onto the dropzone or click **choose a file…** (`.json` / `.xml` / `.mspdi` /
    `.xer` / `.mpp` / `.mpt`, up to 100 at once)"; docs/USER-GUIDE.md:69-70 "(`.json`
    `.xml`/`.mspdi` `.xer` `.mpp` `.mpt`, up to **100** at once)"; docs/USER-GUIDE.md:3-4
    "everything below still works as described". Checked: every "up to N at once" in README.md and
    docs/USER-GUIDE.md, by uploading N+1 byte-distinct copies of the shipped example schedule and
    counting what the session holds. Tier T3.
    """
    claims: dict[int, list[str]] = {}
    for rel in ("README.md", "docs/USER-GUIDE.md"):
        for m in re.finditer(r"up to (\d[\d,]*) at once", _plain(_read(rel))):
            claims.setdefault(_int(m.group(1)), []).append(rel)
    example = (SRC / "web" / "examples" / "house_build.json").read_bytes()
    over: dict[int, int] = {}
    for cap in sorted(claims):
        state = SessionState()
        client = TestClient(create_app(state))
        files = [
            ("files", (f"v{i}.json", example + b"\n" * i, "application/json"))
            for i in range(cap + 1)
        ]
        client.post("/upload", files=files)
        if len(state.schedules) > cap:
            over[cap] = len(state.schedules)
    assert not over, (
        f"docs state an import limit {sorted(claims.items())}; uploading limit+1 loads {over}"
    )


# --------------------------------------------------------------------------------------------
# A0923-DOC-003
# --------------------------------------------------------------------------------------------
def _rail_labels() -> dict[str, list[str]]:
    from schedule_forensics.web import chrome

    return {rail: [ch.label for ch in chapters] for rail, chapters in chrome._SPINE}


def _doc_rail_lists() -> list[tuple[str, str, list[str]]]:
    """(where, RAIL, names) for every off-spine rail enumeration in the three docs."""
    out: list[tuple[str, str, list[str]]] = []
    readme = _plain(_read("README.md"))
    for m in re.finditer(r"with a Setup rail \(([^)]*)\) off the spine", readme):
        out.append(("README.md", "SETUP", [n.strip() for n in m.group(1).split(",")]))
    guide = _plain(_read("docs/USER-GUIDE.md"))
    for m in re.finditer(r"a Setup rail off the spine holds (.+?)\. ", guide):
        names = re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(1))
        out.append(
            ("docs/USER-GUIDE.md", "SETUP", [re.sub(r"^the\s+", "", n.strip()) for n in names])
        )
    lines = _read("docs/DESIGN-SYSTEM.md").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- Off-spine rails"):
            bullet = [line]
            for nxt in lines[i + 1 :]:
                if nxt.startswith("- ") or not nxt.strip() or nxt.startswith("#"):
                    break
                bullet.append(nxt)
            text = _plain("\n".join(bullet))
            for m in re.finditer(r"\b(Forensics|Library|Control|Setup) \(([^)]*)\)", text):
                names = [n.strip() for n in m.group(2).split(",")]
                out.append(("docs/DESIGN-SYSTEM.md", m.group(1).upper(), names))
    return out


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-003: README/USER-GUIDE put the Workbench on the Setup rail and "
    "DESIGN-SYSTEM's Library omits One-Pager Compare",
)
def test_a0923_doc_003_documented_rail_membership_is_the_navs() -> None:
    """Every documented off-spine rail enumeration must list exactly that rail's nav entries.

    Claim (A0923-DOC-003): at 8c71c639 ``chrome._SPINE`` puts Metric Workbench on LIBRARY, SETUP is
    [Groups & Filters, AI Settings, Metric Dictionary], and LIBRARY also holds One-Pager Compare;
    the docs disagree. Authority (verbatim): README.md:105-107 "with a Setup rail (Workbench,
    Groups & Filters, AI Settings, Metric Dictionary) off the spine."; docs/USER-GUIDE.md:25-26 "a
    **Setup** rail off the spine holds the Metric Workbench, Groups & Filters, AI Settings, and the
    Metric Dictionary."; docs/DESIGN-SYSTEM.md:61-65 "**Library** (Metric Workbench, One-Pager
    Timeline, WBS Rollup, Schedule ID Card, EVM)". Checked: each enumeration's names (a doc name
    matches a nav label equal to it or ending in it, e.g. "Workbench") against the rail's labels
    in ``chrome._SPINE``, both directions. Tier T3.
    """
    rails = _rail_labels()
    all_labels = [label for labels in rails.values() for label in labels]
    wrong: list[str] = []
    for where, rail, names in _doc_rail_lists():
        matched = set()
        for name in names:
            hits = [lab for lab in all_labels if lab == name or lab.endswith(" " + name)]
            matched.add(hits[0] if hits else f"<no nav entry: {name}>")
        if matched != set(rails.get(rail, [])):
            wrong.append(f"{where} {rail}: doc {sorted(matched)} != nav {rails.get(rail)}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-004
# --------------------------------------------------------------------------------------------
_SCHEDULE_SUFFIXES = (".mpp", ".mpt", ".mpx", ".xer", ".p6xml", ".mspdi")


def _is_schedule_file(path: str) -> bool:
    low = path.lower()
    return low.endswith(_SCHEDULE_SUFFIXES) or ".mspdi.xml" in low


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-004: five present-tense doc statements call the committed reference intake "
    "absent / not committed / CUI",
)
def test_a0923_doc_004_docs_do_not_call_the_committed_intake_absent_or_cui() -> None:
    """A present-tense statement that reference files are absent or uncommitted must hold in git.

    Claim (A0923-DOC-004): at 8c71c639 git tracks 29 .mpp (incl. Large_Test_File, Project2/3/4,
    Project5_TAMPERED), 91 .xlsx, the .pbix and the Mission Ops v2 prototype under
    00_REFERENCE_INTAKE/ (committed by the operator, ADR-0152; NOT CUI per CLAUDE.md:18-24), yet
    docs say they are not. Authority (verbatim): docs/FUSE-VALIDATION.md:7-9 "(Large Test File,
    Project2 "Duration Bomb", Project3, Project4, Project5_TAMPERED) are real `.mpp`s that do not
    travel to the container"; docs/USER-GUIDE.md:290-291 "Schedule files, parsed derivatives,
    and reports are git-ignored and never committed."; docs/DESIGN-SYSTEM.md:5-6 "(`Mission Ops
    Redesign v2.dc.html` in the design handoff bundle — not committed"; docs/TEST-PROJECTS.md:36-37
    "`tests/fixtures/test_projects/TP*.xml` (committed; the only schedule-format path allowed in
    git"; docs/risks.md:10 (R-03 Status) "`.pbix` + proprietary-tool reruns remain with the
    operator". Scope after the 2026-09-25 falsification pass: these FIVE; FUSE-VALIDATION.md:17
    (a parenthetical under the dated "(2026-06-18)" heading, true when written),
    PARITY-REPORT.md:26-27/:39 (dated records) and FUSE-VALIDATION.md:147-150 (not an absence
    claim) are NOT checked. Oracle: ``git ls-files``.
    Tier T3.
    """
    tracked = _tracked_files()
    intake = [p for p in tracked if p.startswith("00_REFERENCE_INTAKE/")]
    intake_mpp = {_norm_name(Path(p).stem) for p in intake if p.lower().endswith(".mpp")}
    wrong: list[str] = []

    fuse = _plain(_read("docs/FUSE-VALIDATION.md"))
    for m in re.finditer(
        r"The other workbook projects \(([^)]*)\) are real `\.mpp`s that do not travel", fuse
    ):
        names = [re.sub(r'"[^"]*"', "", n).strip() for n in m.group(1).split(",")]
        present = [n for n in names if _norm_name(n) in intake_mpp]
        if present:
            wrong.append(f"FUSE-VALIDATION says {present} do not travel; they are tracked")
    # FUSE-VALIDATION.md:17 is a parenthetical under the dated "(2026-06-18)" heading (a record
    # that was true when written) and is deliberately NOT checked (falsification pass, 2026-09-25).

    guide = _plain(_read("docs/USER-GUIDE.md"))
    if "Schedule files, parsed derivatives, and reports are git-ignored and never committed" in (
        guide
    ):
        committed = [p for p in tracked if _is_schedule_file(p)]
        if committed:
            wrong.append(f"USER-GUIDE says schedule files are never committed: {committed[:2]}")

    design = _plain(_read("docs/DESIGN-SYSTEM.md"))
    for m in re.finditer(r"\(`([^`]+)` in the design handoff bundle \u2014 not committed", design):
        copies = [p for p in tracked if Path(p).name == m.group(1)]
        if copies:
            wrong.append(f"DESIGN-SYSTEM says {m.group(1)!r} is not committed: {copies[:2]}")

    battery = _plain(_read("docs/TEST-PROJECTS.md"))
    for m in re.finditer(
        r"`([^`]+)` \(committed; the only schedule-format path allowed in git", battery
    ):
        glob = m.group(1)
        others = [p for p in tracked if _is_schedule_file(p) and not Path(p).match(glob)]
        if others:
            wrong.append(f"TEST-PROJECTS says {glob} is the only schedule path: {others[:2]}")

    for line in _read("docs/risks.md").splitlines():
        if line.startswith("| R-03 |"):
            status = [c for c in _cells(line) if c][-1]
            if ".pbix" in status and "remain with the operator" in status:
                pbix = [p for p in tracked if p.lower().endswith(".pbix")]
                if pbix:
                    wrong.append(f"risks.md R-03 says the .pbix remains with the operator: {pbix}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-005
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-005: PARITY-REPORT §E still reports the engine at -148 with a 96<->99 SN04 "
    "swap as a live residual",
)
def test_a0923_doc_005_parity_report_section_e_states_the_engines_figures() -> None:
    """PARITY-REPORT's §E engine figures and 'What remains' residuals must be the engine's.

    Claim (A0923-DOC-005): at 8c71c639 compute_net_finish_impact(Project5, Project2) on the
    committed goldens yields -134 and the SN04 no-longer-critical set equals Fuse's (symmetric
    difference empty; closed by ADR-0474), while the report still states -148 and a 96<->99 swap.
    Authority (verbatim), docs/PARITY-REPORT.md:156-157 "(e.g. Net Finish Impact is now **−148**,
    not the old −99)"; :172 "| **HSD10 Net Finish Impact (days)** | **−148** (CPM-finish basis)";
    :174 "membership 33/34 — engine UID 99 ↔ Fuse UID 96"; :385-389 "* **SN04 membership swap
    (96↔99).** ... * **HSD10 basis (−148 vs −134).**". Checked: those statements against the engine
    and the Fuse transcription (fuse_exports_2026-06.json); the report's CLOSED honesty note
    (:177-187) and :269-270 are true and not checked. Tier T3.
    """  # noqa: RUF002
    p2, p5 = _golden_pair()
    nfi = int(compute_net_finish_impact(p5, p2).value)
    change = compute_change_metrics(p5, p2)
    fuse = _fuse_change()
    engine_set = set(change["no_longer_critical"].offender_uids)
    fuse_set = set(fuse["no_longer_critical_uids"])
    raw = _read("docs/PARITY-REPORT.md").replace(_MINUS, "-")
    text = _plain(raw)
    wrong: list[str] = []
    for m in re.finditer(r"Net Finish Impact is now (-?\d+)", text):
        if int(m.group(1)) != nfi:
            wrong.append(f"'Net Finish Impact is now {m.group(1)}' (engine {nfi})")
    for line in raw.splitlines():
        cells = _cells(line) if line.startswith("|") else []
        if cells and cells[0].replace("*", "").startswith("HSD10 Net Finish Impact"):
            num = re.search(r"-?\d+", cells[1].replace("*", ""))
            if num and int(num.group()) != nfi:
                wrong.append(f"§E table engine cell {num.group()} (engine {nfi})")
        if cells and cells[0].startswith("SN04 No Longer Critical"):
            swap = re.search(r"engine UID (\d+) \u2194 Fuse UID (\d+)", cells[-1])
            if swap and not (
                int(swap.group(1)) in engine_set - fuse_set
                and int(swap.group(2)) in fuse_set - engine_set
            ):
                wrong.append(
                    f"§E table SN04 swap {swap.groups()} (engine^fuse {engine_set ^ fuse_set})"
                )
    for m in re.finditer(r"SN04 membership swap \((\d+)\u2194(\d+)\)", text):
        if engine_set ^ fuse_set != {int(m.group(1)), int(m.group(2))}:
            wrong.append(
                f"'What remains' SN04 swap {m.groups()} (engine^fuse {engine_set ^ fuse_set})"
            )
    for m in re.finditer(r"HSD10 basis \((-?\d+) vs (-?\d+)\)", text):
        stored = fuse["net_finish_impact_days_stored"]
        if (int(m.group(1)), int(m.group(2))) != (nfi, stored):
            wrong.append(f"'What remains' HSD10 {m.groups()} (engine {nfi}, Fuse {stored})")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-006
# --------------------------------------------------------------------------------------------
def _stored_dates_table() -> list[dict[str, str]]:
    lines = _read("docs/PARITY-REPORT.md").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| File | Stored finish |") and "Stored slack exact" in line:
            header = _cells(line)
            rows = []
            for nxt in lines[i + 2 :]:
                if not nxt.startswith("|"):
                    break
                rows.append(dict(zip(header, _cells(nxt), strict=False)))
            return rows
    return []


def _table_goldens(label: str, by_stem: dict[str, str]) -> list[str]:
    """A table row's golden(s): 'Hard_File' -> its oracle path; 'Large Test File / File2' -> the
    two paths (the second part renames the first part's last word)."""
    rels: list[str] = []
    first: list[str] = []
    for part in (p.strip() for p in label.split(" / ")):
        words = part.replace(" ", "_").split("_")
        stem = "_".join(words) if not first else "_".join([*first[:-1], *words])
        first = first or words
        if stem in by_stem:
            rels.append(by_stem[stem])
    return rels


def _head_numbers(cell: str) -> list[int]:
    """The cell's current figure(s) — the text before its '(was …)' history — as ints."""
    head = cell.replace("*", "").split("(")[0]
    return [_int(part) for part in head.split("/") if re.search(r"\d", part)]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-006: PARITY-REPORT's stored-dates table no longer states what the oracle's "
    "census measures",
)
def test_a0923_doc_006_stored_dates_table_is_the_oracles_census() -> None:
    """Each golden's 'Finish within a day' and 'Stored slack exact' cells must be the census.

    Claim (A0923-DOC-006): at 8c71c639 the stored-dates oracle's own ``_census``
    (tests/parity/test_hard_file_stored_dates_oracle.py — the instrument the report names as the
    pin) measures stored-slack-exact 110/110, 103/103, 74/76, 63/68, 17/19, 106/106, 99/99,
    922/760 and LTF within-a-day 1,689/1,655; the table prints other figures. Authority
    (verbatim), docs/PARITY-REPORT.md:242-244 "The rules were derived from the stored dates and
    are pinned by `tests/parity/test_hard_file_stored_dates_oracle.py` (floors)"; :246 "| File |
    Stored finish | CPM finish (before → after) | Finish within a day (of 110 / 126) | Critical
    agreed | Stored slack exact |"; e.g. :250 "| 38 / 76 (ADR-0510; was 36) |", :255 "1 666 / 1
    687 ... | 865 / 668 (were 842 / 655) |". Checked: the 'Finish within a day' and 'Stored slack
    exact' cells of every row, recomputed with the oracle's ``_load``/``_census``; the 'Critical
    agreed' column is outside the claim and not checked. Tier T3.
    """
    table = _stored_dates_table()
    if not table:
        return  # the table is gone: nothing left to be false
    oracle = _load_by_path(
        "_a0923_stored_dates_oracle",
        REPO / "tests" / "parity" / "test_hard_file_stored_dates_oracle.py",
    )
    by_stem = {
        Path(row[0]).name.split(".")[0]: row[0]
        for row in (*oracle._HARD_FILE, *oracle._PROJECTS, *oracle._LARGE)
    }
    finish_col = next((k for k in table[0] if k.startswith("Finish within")), "")
    wrong: list[str] = []
    for row in table:
        label = row.get("File", "")
        rels = _table_goldens(label, by_stem)
        if not rels:
            continue
        census = [oracle._census(*oracle._load(rel), rel) for rel in rels]
        finish_doc = _head_numbers(row.get(finish_col, ""))
        slack_doc = _head_numbers(row.get("Stored slack exact", ""))
        if len(rels) == 1:
            finish_now = [census[0]["finish_1d"]]
            slack_now = [census[0]["tf_exact"], census[0]["tf_n"]]
        else:  # the two-file row prints file / file2 numerators side by side
            finish_now = [c["finish_1d"] for c in census]
            slack_now = [c["tf_exact"] for c in census]
        if finish_doc and finish_doc != finish_now:
            wrong.append(f"{label}: within-a-day {finish_doc} vs census {finish_now}")
        if slack_doc and slack_doc != slack_now:
            wrong.append(f"{label}: stored slack exact {slack_doc} vs census {slack_now}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-007
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-007: TEST-PROJECTS/PARITY-REPORT describe TP1's retired single-block "
    "210/210/120-minute residual as live",
)
def test_a0923_doc_007_tp1_ragged_slack_statements_are_the_engines() -> None:
    """The present-tense TP1 ragged-slack statements must match compute_driving_slack(TP1, 43).

    Claim (A0923-DOC-007): at 8c71c639 the engine gives completed UIDs 11/12/13 driving slack
    300/300/180 min (SSI's 0.63/0.63/0.38 d; ADR-0117 honours the lunch break), while the docs
    still state the retired single-block figures as the pinned truth and as a live 'by design'
    residual. Authority (verbatim): docs/TEST-PROJECTS.md:177 "incl. completed UIDs 11, 12, 13,
    which carry **210/210/120 minutes** of raggedness"; :198-201 "the engine uses its single-block
    model (ADR-0010), giving 0.44/0.25"; docs/PARITY-REPORT.md:410-412 "the engine on its
    single-block model (ADR-0010: 0.44 = 210/480)". The dated SSI-verification table cells
    (TEST-PROJECTS.md:196, PARITY-REPORT.md:408) are records and NOT checked. Tier T3.
    """
    sch = parse_mspdi(TP_DIR / "TP1_Library_Progressed.xml")
    battery = _plain(_read("docs/TEST-PROJECTS.md"))
    target = re.search(r"Tasks traced to UID (\d+)", battery) or re.search(r"UID (\d+) \(", battery)
    results = compute_driving_slack(sch, int(target.group(1)) if target else 43)
    per_day = Decimal(sch.calendar.working_minutes_per_day)
    ragged = {
        uid: r.driving_slack_minutes
        for uid, r in results.items()
        if 0 < r.driving_slack_minutes < sch.calendar.working_minutes_per_day
    }
    fractions = {_round2(Decimal(m) / per_day) for m in ragged.values()}
    wrong: list[str] = []
    for m in re.finditer(
        r"completed UIDs ((?:\d+, )*\d+), which carry ((?:\d+/)*\d+) minutes", battery
    ):
        uids = [int(u) for u in m.group(1).split(", ")]
        stated = [int(x) for x in m.group(2).split("/")]
        engine = [results[u].driving_slack_minutes if u in results else None for u in uids]
        if stated != engine:
            wrong.append(f"TEST-PROJECTS UIDs {uids} carry {stated} min; engine {engine}")
    for m in re.finditer(
        r"the engine uses its single-block model \(ADR-0010\), giving ((?:\d?\.\d+/)*\d?\.\d+)",
        battery,
    ):
        stated_f = {Decimal(x) for x in m.group(1).split("/")}
        if stated_f != fractions:
            wrong.append(f"TEST-PROJECTS engine fractions {sorted(stated_f)}; engine {fractions}")
    parity = _plain(_read("docs/PARITY-REPORT.md"))
    for m in re.finditer(
        r"the engine on its single-block model \(ADR-0010: (\d?\.\d+) = (\d+)/(\d+)\)", parity
    ):
        if int(m.group(2)) not in ragged.values():
            wrong.append(f"PARITY-REPORT engine {m.group(2)} min; engine {sorted(ragged.items())}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-008
# --------------------------------------------------------------------------------------------
def _tp3_table() -> dict[str, list[str]]:
    section = _section(_read("docs/TEST-PROJECTS.md"), "TP3")
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        if line.startswith("|") and not set(line) <= set("|-: "):
            cells = _cells(line)
            rows[cells[0]] = cells[1:]
    return rows


def _uids_outside_parentheses(cell: str) -> set[int]:
    return {int(x) for x in re.findall(r"\d+", re.sub(r"\([^)]*\)", "", cell))}


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-008: TEST-PROJECTS' 'engine-measured and pinned' TP3 table disagrees with "
    "audit_schedule(TP3) on six rows",
)
def test_a0923_doc_008_tp3_expected_values_are_the_engines() -> None:
    """The TP3 rows the audit found stale must equal audit_schedule(TP3), as the doc promises.

    Claim (A0923-DOC-008): at 8c71c639 audit_schedule(TP3) yields Leads 1, Negative Float 4
    {24,28,29,41}, Invalid Forecast Dates 4 {14,25,26,32} + Invalid Actual Dates 1 {31},
    Resources 11 of 11, BEI 0.58 (7 of 12), CPLI 0.93 FAIL. Authority (verbatim):
    docs/TEST-PROJECTS.md:7-9 "The DCMA/float/driving/manipulation counts in the tables below are
    **engine-measured and pinned by `tests/test_projects/`**"; :232 "| Leads | **2** |"; :236 "|
    Negative float | **3** (−3 d: the MFO on 41 caps its chain) | 24, 28, 29 |"; :239 "| Invalid
    dates | **4** | 31 (actual finish 05-05 > DD), 25/26/32 (...) |"; :240 "| Resources | 10 of 10
    unresourced"; :241 "| BEI | **0.62** (8 finished of 13 due)"; :242 "| CPLI | 0.97 (PASS)";
    docs/PARITY-REPORT.md:419 "the engine counts lead links = 2". Checked: those six rows and the
    PARITY-REPORT engine-side Leads figure; the rows that still reproduce, and the HELD Fuse side
    of Insufficient Detail (R-53), are not checked. Tier T3.
    """  # noqa: RUF002
    audit = audit_schedule(parse_mspdi(TP_DIR / "TP3_Outage_DCMA_Seeded.xml"))
    checks = {c.name: c for c in audit.checks}

    def uids(*names: str) -> set[int]:
        return {cit.unique_id for n in names for cit in checks[n].citations}

    rows = _tp3_table()
    wrong: list[str] = []
    if "Leads" in rows:
        stated = _int(re.findall(r"\d+", rows["Leads"][0])[0])
        if stated != checks["Leads"].count:
            wrong.append(f"Leads {stated} (engine {checks['Leads'].count})")
    if "Negative float" in rows:
        cells = rows["Negative float"]
        stated = int(re.findall(r"\d+", cells[0])[0])
        named = _uids_outside_parentheses(cells[1]) if len(cells) > 1 else set()
        nf = checks["Negative Float"]
        if (stated, named) != (nf.count, uids("Negative Float")):
            wrong.append(
                f"Negative float {stated} {sorted(named)} (engine {nf.count} "
                f"{sorted(uids('Negative Float'))})"
            )
    for label, names in (
        ("Invalid dates", ("Invalid Forecast Dates", "Invalid Actual Dates")),
        ("Invalid forecast dates", ("Invalid Forecast Dates",)),
        ("Invalid actual dates", ("Invalid Actual Dates",)),
    ):
        if label in rows:
            cells = rows[label]
            stated = int(re.findall(r"\d+", cells[0])[0])
            named = _uids_outside_parentheses(cells[1]) if len(cells) > 1 else set()
            count = sum(checks[n].count for n in names)
            if (stated, named) != (count, uids(*names)):
                wrong.append(
                    f"{label} {stated} {sorted(named)} (engine {count} {sorted(uids(*names))})"
                )
    if "Resources" in rows:
        m = re.search(r"(\d+) of (\d+)", rows["Resources"][0])
        res = checks["Resources"]
        if m and (int(m.group(1)), int(m.group(2))) != (res.count, res.population):
            wrong.append(f"Resources {m.group(0)} (engine {res.count} of {res.population})")
    if "BEI" in rows:
        m = re.search(r"(\d\.\d+)", rows["BEI"][0])
        if m and Decimal(m.group(1)) != _round2(Decimal(str(checks["BEI"].value))):
            wrong.append(f"BEI {m.group(1)} (engine {checks['BEI'].value})")
    if "CPLI" in rows:
        m = re.search(r"(\d\.\d+) \((PASS|FAIL)\)", rows["CPLI"][0])
        cpli = checks["CPLI"]
        status = "PASS" if str(cpli.status).upper().endswith("PASS") else "FAIL"
        if m and (Decimal(m.group(1)), m.group(2)) != (_round2(Decimal(str(cpli.value))), status):
            wrong.append(f"CPLI {m.group(1)} {m.group(2)} (engine {cpli.value} {status})")
    parity = _plain(_read("docs/PARITY-REPORT.md"))
    for m in re.finditer(r"the engine counts lead links = (\d+)", parity):
        if int(m.group(1)) != checks["Leads"].count:
            wrong.append(
                f"PARITY-REPORT engine leads {m.group(1)} (engine {checks['Leads'].count})"
            )
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-009
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-009: TEST-PROJECTS' prose task counts match no counting convention of the "
    "committed TP files",
)
def test_a0923_doc_009_tp_prose_task_counts_are_the_files() -> None:
    """Each TP section's lead sentence must count the tasks its committed file(s) carry.

    Claim (A0923-DOC-009): at 8c71c639 the committed TP XML carry 23/16/21/15 non-summary tasks
    (20+3, 14+2, 19+2, 13+2 normal+milestone) for TP1/TP2/TP3/TP4, while the prose says otherwise
    (never true at any sha). Authority (verbatim), docs/TEST-PROJECTS.md:158 "26 working tasks + 3
    milestones"; :213 "15 working tasks"; :226 "22 working tasks + 2 milestones"; :250 "Same
    14-task project". Checked: "N working tasks + M milestones" must be (normal, milestone); a bare
    "N working tasks" / "Same N-task project" must be the normal or the non-summary count, of every
    file the section covers (TP4: v1..v5). The import-check table (:141-146) is right and not
    checked. Tier T3.
    """
    text = _read("docs/TEST-PROJECTS.md")
    wrong: list[str] = []
    for tp in ("TP1", "TP2", "TP3", "TP4"):
        body = _plain(_section(text, tp))
        files = sorted(TP_DIR.glob(f"{tp}_*.xml"))
        counts = []
        for f in files:
            tasks = [t for t in parse_mspdi(f).tasks if not t.is_summary]
            ms = sum(1 for t in tasks if t.is_milestone)
            counts.append((f.name, len(tasks) - ms, ms))
        pair = re.search(r"(\d+) working tasks \+ (\d+) milestones", body)
        single = re.search(r"(\d+) working tasks(?! \+)", body) or re.search(
            r"Same (\d+)-task project", body
        )
        for name, normal, ms in counts:
            if pair and (int(pair.group(1)), int(pair.group(2))) != (normal, ms):
                wrong.append(f"{tp}: '{pair.group(0)}' vs {name} {normal}+{ms}")
            elif not pair and single and int(single.group(1)) not in (normal, normal + ms):
                wrong.append(f"{tp}: '{single.group(0)}' vs {name} {normal}+{ms}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-010
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-010: CONNECT-A-BIGGER-AI-MODEL states a 900 s default timeout, says 900 is "
    "'bigger', and names llama3.1:8b the standard brain",
)
def test_a0923_doc_010_connect_ai_guide_states_the_shipped_defaults() -> None:
    """The guide's default timeout, its 'bigger number' and its 'standard brain' must be AIConfig's.

    Claim (A0923-DOC-010): at 8c71c639 AIConfig() defaults to gen_timeout 3600.0 s (the settings
    form's maximum, ADR-0162) and model 'qwen2.5:7b-instruct' (ADR-0215). Authority (verbatim),
    docs/CONNECT-A-BIGGER-AI-MODEL.md:84 "| 16 GB (a normal modern laptop) | `llama3.1:8b` | The
    tool's standard brain — balanced and reliable. |"; :135-137 "Find the box called
    **"Generation timeout (seconds)"** and type a bigger number, like `900`."; :230 "**The default
    generation timeout is 900 seconds (15 minutes)**". Checked: the stated default equals
    ``AIConfig().gen_timeout``; the "bigger number" exceeds it; the "standard brain" is
    ``AIConfig().model``. Tier T3.
    """
    cfg = AIConfig()
    raw = _read("docs/CONNECT-A-BIGGER-AI-MODEL.md")
    text = _plain(raw)
    wrong: list[str] = []
    for m in re.finditer(r"The default generation timeout is (\d[\d,]*) seconds", text):
        if _int(m.group(1)) != cfg.gen_timeout:
            wrong.append(f"default timeout {m.group(1)} s (AIConfig {cfg.gen_timeout})")
    for m in re.finditer(r"type a bigger number, like `(\d+)`", text):
        if not int(m.group(1)) > cfg.gen_timeout:
            wrong.append(f"'a bigger number, like {m.group(1)}' is not above {cfg.gen_timeout}")
    for m in re.finditer(r"\|\s*`([^`]+)`\s*\|\s*The tool's standard brain", raw):
        if m.group(1) != cfg.model:
            wrong.append(f"standard brain {m.group(1)!r} (AIConfig {cfg.model!r})")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-011
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-011: ACUMEN-PARITY-MODE says check 9 reports one row per activity, not the "
    "field tally; parity mode reports the field tally",
)
def test_a0923_doc_011_parity_mode_check9_count_is_what_the_doc_says() -> None:
    """If the doc says check 9's figure is per activity, parity mode's count must equal activities.

    Claim (A0923-DOC-011): at 8c71c639 audit_schedule(Large_Test_File2, acumen_parity=True)
    reports Invalid Forecast Dates count=322 over 170 cited activities — a FIELD tally (ADR-0520
    amends ADR-0283) equal to Fuse's ribbon. Authority (verbatim), docs/ACUMEN-PARITY-MODE.md:59-62
    "(Acumen's ribbon also counts invalid *date fields* — a start flag and a finish flag can both
    fire on one activity, so the ribbon number runs up to ~2× the activity count; the tool reports
    **one row per activity**, matching Acumen's activity **detail**, not the ribbon's field
    tally.)". Checked: when that sentence stands, every parity-mode DCMA-09 count on the LTF2
    golden equals its number of distinct cited activities. Tier T2.
    """  # noqa: RUF002
    text = _plain(_read("docs/ACUMEN-PARITY-MODE.md"))
    if not re.search(
        r"the tool reports one row per activity.{0,80}not the ribbon's field tally", text
    ):
        return  # the statement is gone: nothing left to be false
    sch = _load_golden("fuse_ltf/Large_Test_File2.mspdi.xml.gz")
    audit = audit_schedule(sch, acumen_parity=True)
    rows = {
        c.name: (c.count, len({cit.unique_id for cit in c.citations}))
        for c in audit.checks
        if str(c.metric_id).startswith("DCMA09")
    }
    assert rows, "no DCMA-09 check in the parity audit"
    assert all(count == acts for count, acts in rows.values()), (
        f"the doc says one row per activity; parity mode reports (count, activities) {rows}"
    )


# --------------------------------------------------------------------------------------------
# A0923-DOC-012
# --------------------------------------------------------------------------------------------
def _computed_metric_names() -> set[str]:
    """Every metric name the engine computes a figure for (schedule quality, the Fuse ribbon row,
    and Float Ratio on the golden Project2, which Fuse also scores)."""
    sch = parse_mspdi(TP_DIR / "TP1_Library_Progressed.xml")
    cpm = compute_cpm(sch)
    names = set(compute_schedule_quality(sch))
    names |= {
        f.name for f in dataclasses.fields(compute_ribbon(sch, cpm, audit_schedule(sch, cpm)))
    }
    p2, _p5 = _golden_pair()
    names |= {k for k, v in compute_float_ratio(p2).items() if v.population > 0}
    return names


def _metric_keys(name: str) -> list[str]:
    """'Number of Leads/Lags' -> ['number_of_leads', 'number_of_lags']; 'Avg/Max Float' ->
    ['avg_float', 'max_float']; 'Logic Density' -> ['logic_density']."""
    words = name.split()
    slashed = next((i for i, w in enumerate(words) if "/" in w), None)
    variants = (
        [name]
        if slashed is None
        else [
            " ".join([*words[:slashed], alt, *words[slashed + 1 :]])
            for alt in words[slashed].split("/")
        ]
    )
    return [re.sub(r"[^a-z0-9]+", "_", v.lower()).strip("_") for v in variants]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-012: FUSE-VALIDATION calls Float Ratio still-uncomputed and lists shipped "
    "ribbon metrics + a Ribbon view as next-PR work",
)
def test_a0923_doc_012_fuse_validation_open_work_is_not_already_shipped() -> None:
    """A metric the doc lists as uncomputed / to-implement must not already be computed.

    Claim (A0923-DOC-012): at 8c71c639 compute_schedule_quality exposes logic_density /
    insufficient_detail / merge_hotspot / number_of_leads / number_of_lags, the ribbon row carries
    avg/max float, engine/metrics/float_ratio.py computes Float Ratio (ADR-0103/0519) and /ribbon
    is served. Authority (verbatim), docs/FUSE-VALIDATION.md:107-108 "The still-uncomputed Fuse
    **proprietary** metrics (Float Ratio™ and the composite Score) remain the target values for
    the follow-on work"; :143-145 "**Missing Fuse metrics** (next PR): implement Logic Density™,
    Float Ratio™, Insufficient Detail™, Merge Hotspot, Number of Leads/Lags, Avg/Max Float,
    calibrated to the per-project values above, and surface them in a Ribbon view." Checked: each
    listed metric against the engine's computed metric names, and 'a Ribbon view' against the
    app's routes; the composite Score (still uncomputed — true) and the Year Trend/Phase bullet
    (outside the claim) are not checked. Tier T3.
    """
    text = _plain(_read("docs/FUSE-VALIDATION.md")).replace("\u2122", "")
    listed: list[tuple[str, str]] = []
    for m in re.finditer(r"still-uncomputed Fuse proprietary metrics \(([^)]*)\)", text):
        parts = re.split(r",\s*|\s+and\s+", m.group(1))
        listed += [("still-uncomputed", n.strip()) for n in parts if n.strip()]
    ribbon_view = False
    for m in re.finditer(r"Missing Fuse metrics \(next PR\): implement (.+?), calibrated", text):
        listed += [("next PR", n.strip()) for n in m.group(1).split(", ") if n.strip()]
        ribbon_view = ribbon_view or "surface them in a Ribbon view" in text
    computed = _computed_metric_names()
    shipped: list[str] = []
    for where, name in listed:
        keys = _metric_keys(name)
        if all(any(c == k or c.startswith(k + "_") for c in computed) for k in keys):
            shipped.append(f"{where}: {name}")
    if ribbon_view and any(
        getattr(r, "path", None) == "/ribbon" for r in create_app(SessionState()).routes
    ):
        shipped.append("next PR: a Ribbon view (/ribbon is served)")
    assert not shipped, f"FUSE-VALIDATION lists as uncomputed / next-PR what ships: {shipped}"


# --------------------------------------------------------------------------------------------
# A0923-DOC-013
# --------------------------------------------------------------------------------------------
def _section_e_reproduced() -> dict[str, bool]:
    """Engine vs the Fuse transcription on the five change metrics risks.md R-13 names."""
    p2, p5 = _golden_pair()
    ch = compute_change_metrics(p5, p2)
    f = _fuse_change()

    def started(s: Schedule) -> int:
        return sum(1 for t in s.tasks if not t.is_summary and t.actual_start is not None)

    new_starts = started(p5) - started(p2)
    fuse_start_slips = round(new_starts / f["start_cei_by_status_dates"]) - new_starts
    return {
        "SN04 no-longer-critical": sorted(ch["no_longer_critical"].offender_uids)
        == sorted(f["no_longer_critical_uids"]),
        "SN05 finish slips": list(ch["finish_date_slips"].offender_uids)
        == f["finish_slips_cei_incomplete_uids"],
        "SN06 start slips": ch["start_date_slips"].count == fuse_start_slips,
        "SN07 duration increases": list(ch["remaining_duration_increases"].offender_uids)
        == f["original_duration_increases_uids"],
        "SN09 float erosion": list(ch["float_erosion"].offender_uids)
        == f["float_erosion_stored_basis_uids"],
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-013: risks.md R-13 says §E is 'not yet reproduced' and R-14 says 99 "
    "mismatches; the engine reproduces §E and the manifest reads 143",
)
def test_a0923_doc_013_risk_register_rows_state_the_measured_facts() -> None:
    """R-13's 'not reproduced' and R-14's mismatch count must be what the tree measures.

    Claim (A0923-DOC-013): at 8c71c639 the engine reproduces every §E change count on the
    committed pair (SN04 34 UID-exact, SN05/06/07 9, SN09 1) and the intake manifest re-derives
    143 extension mismatches, while the living register says otherwise. Authority (verbatim),
    docs/risks.md:21 (R-13) "**Acumen Schedule-Network (§E) change-metric semantics not yet
    reproduced**" and Status "Accepted (M9: investigated, not MSPDI-reproducible, ...)";
    docs/risks.md:23 (R-14) "99 tracked files carry an extension their bytes contradict" and
    Status "renaming 99 operator-uploaded files". Checked: R-13's claim against the engine vs the
    Fuse transcription; R-14's two counts against ``tools/intake_manifest.py``'s scan. R-14's '65
    static assets' sits in a dated 2026-08-03 block (a record) and is NOT checked. Tier T3.
    """
    rows = {
        _cells(line)[0]: line
        for line in _read("docs/risks.md").splitlines()
        if line.startswith("| R-")
    }
    wrong: list[str] = []
    r13 = rows.get("R-13", "")
    if "not yet reproduced" in r13 or "not MSPDI-reproducible" in r13:
        reproduced = _section_e_reproduced()
        if all(reproduced.values()):
            wrong.append(f"R-13 says §E is not reproduced; engine==Fuse on {sorted(reproduced)}")
    stated = [
        int(g)
        for m in re.finditer(
            r"(\d+) tracked files carry an extension|renaming (\d+) operator-uploaded files",
            rows.get("R-14", ""),
        )
        for g in m.groups()
        if g
    ]
    if stated:
        if shutil.which("git") is None:
            pytest.skip("git is not available; the intake manifest scan reads git blobs")
        tool = _load_by_path("_a0923_intake_manifest", REPO / "tools" / "intake_manifest.py")
        mismatches = sum(1 for e in tool.scan(REPO) if e.mismatch)
        if any(n != mismatches for n in stated):
            wrong.append(f"R-14 states {stated} mismatches; the manifest scan finds {mismatches}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-014
# --------------------------------------------------------------------------------------------
def test_a0923_doc_014_next_session_prompt_version_and_pointers_are_the_trees() -> None:
    """Every 'Highest ADR N. Version V.' and every file:line pointer in the kickoff must hold.

    FIXED-UPSTREAM: the defect below was reproduced at 8c71c639 and was closed by a65e1b21 (#715,
    ADR-0527), which rewrote the closing line in step with the tree and deleted the stale
    pointer paragraph. This test therefore carries NO xfail marker: it is kept as a pin that
    re-derives both facts from the tree on every run. Negative control (session 2, 2026-09-25):
    on a copy of the 8c71c639 tree it fails by name with AssertionError.

    Claim (A0923-DOC-014): at 8c71c639 (highest ADR 0526, version 1.0.289) the kickoff prompt's
    closing line says 0525 / 1.0.288 while its own :32 is right, and its R-71 blast-radius note
    cites cpm.py:3205 for the TaskTiming.is_critical read at cpm.py:3251. Authority (verbatim),
    docs/STATE/NEXT-SESSION-PROMPT.md:185 "Highest ADR 0525. Version 1.0.288. Schema 2.17.0."; :32
    "Highest ADR **0526**. Version **1.0.289**."; :74-75 "`TaskTiming.is_critical` has **2** reads
    in `src/` (`cpm.py:3205`, `float_analysis.py:90`), `CPMResult.critical_path` **2**
    (`dcma14.py:596`, `web/path.py:51`)". Checked: ADR against docs/adr/, version against
    pyproject.toml, each cited line against the source (it must read the named attribute).
    Tier T3.
    """
    text = _plain(_read("docs/STATE/NEXT-SESSION-PROMPT.md"))
    adrs = [int(p.name[:4]) for p in (REPO / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    version = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    wrong: list[str] = []
    for m in re.finditer(r"Highest ADR (\d{4})\. Version ([\d.]+?)\.?(?:\s|$)", text):
        if (int(m.group(1)), m.group(2)) != (max(adrs), version):
            wrong.append(f"'{m.group(0).strip()}' (tree: ADR {max(adrs):04d}, version {version})")
    group = r"`(\w+)\.(\w+)`(?: has)? (\d+) (?:reads? in `src/` )?\(((?:`[^`]+:\d+`(?:, )?)+)\)"
    for m in re.finditer(group, text):
        attr = m.group(2)
        for rel, line_no in re.findall(r"`([^`]+):(\d+)`", m.group(4)):
            hits = [p for p in SRC.rglob(Path(rel).name) if p.as_posix().endswith("/" + rel)]
            lines = [p.read_text(encoding="utf-8").splitlines() for p in hits]
            ok = any(
                int(line_no) <= len(src) and f".{attr}" in src[int(line_no) - 1] for src in lines
            )
            if not ok:
                wrong.append(f"`{rel}:{line_no}` does not read .{attr}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-015
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-015: FUSE-VALIDATION lists EVM2's finish as 2012-10-02 among the "
    "'unchanged' finishes; the engine computes 2012-10-03",
)
def test_a0923_doc_015_fuse_validation_finish_list_is_the_engines() -> None:
    """Each project finish FUSE-VALIDATION lists as the engine's current finish must be computed.

    Claim (A0923-DOC-015): at 8c71c639 EVM2's CPM finish is 2012-10-03 (moved by ADR-0487; stored
    2012-10-04), while the maintained list — refreshed in place for Project2/Project5 at ADR-0474 —
    still says 2012-10-02. Authority (verbatim), docs/FUSE-VALIDATION.md:71-74 "the project finish
    is unchanged on all four genuine MS Project exports (Project2 2027-08-30, Project5 2028-01-25,
    EVM1 2012-09-12, EVM2 2012-10-02 — the Project2 / Project5 figures moved to the stored
    2027-09-14 / 2028-01-26 with ADR-0474, ...)". Checked: each listed finish (Project2/Project5 as
    moved) against the engine's CPM finish of the committed golden. The PARITY-REPORT.md:368 '374
    round() sites' sits in a dated ADR-0515 entry that was exact on its date and is NOT checked.
    Tier T3.
    """
    text = _plain(_read("docs/FUSE-VALIDATION.md"))
    m = re.search(r"unchanged on all four genuine MS Project exports \(([^)]*)\)", text)
    if not m:
        return  # the list is gone: nothing left to be false
    _date = r"(\d{4}-\d{2}-\d{2})"
    stated = dict(re.findall(r"\b(Project2|Project5|EVM1|EVM2) " + _date, m.group(1)))
    moved = re.search(
        rf"Project2 / Project5 figures moved to the stored {_date} / {_date}", m.group(1)
    )
    if moved:
        stated["Project2"], stated["Project5"] = moved.groups()
    goldens = {
        "Project2": "project2_5/Project2.mspdi.xml",
        "Project5": "project2_5/Project5.mspdi.xml",
        "EVM1": "evm/EVM1.mspdi.xml",
        "EVM2": "evm/EVM2.mspdi.xml",
    }
    wrong = []
    for name, date in sorted(stated.items()):
        engine = _finish_date(_load_golden(goldens[name])).isoformat()
        if engine != date:
            wrong.append(f"{name} listed {date}, engine CPM finish {engine}")
    assert not wrong, "; ".join(wrong)


# --------------------------------------------------------------------------------------------
# A0923-DOC-016
# --------------------------------------------------------------------------------------------
def _css_rules(css: str) -> list[tuple[tuple[str, ...], str, str]]:
    """(enclosing at-rule / nesting preludes, selector, declarations) for every style rule."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[tuple[str, ...], str, str]] = []
    stack: list[str] = []
    start = i = 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            prelude = css[start:i].strip()
            close, nested = css.find("}", i + 1), css.find("{", i + 1)
            close = len(css) if close == -1 else close
            if prelude.startswith("@") or (nested != -1 and nested < close):
                stack.append(prelude)
                start = i + 1
            else:
                rules.append((tuple(stack), prelude, css[i + 1 : close]))
                i, start = close, close + 1
        elif ch == "}":
            if stack:
                stack.pop()
            start = i + 1
        elif ch == ";":  # the end of a block-less at-rule statement (@import …;)
            start = i + 1
        i += 1
    return rules


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-DOC-016: DESIGN-SYSTEM says the hidden-tooltip overflow fix is unmade; hud.css "
    "ships it (ADR-0477)",
)
def test_a0923_doc_016_design_system_does_not_call_the_shipped_ui03_fix_unmade() -> None:
    """If the rulebook says the resting [data-sf-hint]::after box is unfixed, no rule may fix it.

    Claim (A0923-DOC-016): at 8c71c639 hud.css:57-58 collapses the resting
    ``[data-sf-hint]::after`` box when the host is neither hovered nor focused (ADR-0477, R-20 /
    UI-03 CLOSED), while the design-system rulebook still describes the overflow as live and the
    fix as unmade. Authority (verbatim), docs/DESIGN-SYSTEM.md:373-378 "it extends past the
    viewport and the document scrolls sideways on every page at 1440 px. ... the fix (render the
    box only on hover/focus, pinned across the census's 34 page states) is priced in the WP8
    report, not made blind." Checked: when that status sentence stands, no shipped stylesheet may
    carry a rule that collapses or removes the resting ``[data-sf-hint]:not(:hover)...::after``
    box. The bullet's lesson (measure scrollWidth) is not a status claim and is not checked.
    Tier T3.
    """
    text = _plain(_read("docs/DESIGN-SYSTEM.md"))
    unmade = re.search(r"the fix \([^)]*\) is priced in the WP8 report, not made blind", text)
    sideways = "the document scrolls sideways on every page at 1440 px" in text
    if not (unmade or sideways):
        return  # the status sentence is gone: nothing left to be false
    fixes = []
    for css_file in sorted((SRC / "web" / "static").glob("*.css")):
        for _context, selector, body in _css_rules(css_file.read_text(encoding="utf-8")):
            decl = re.sub(r"\s+", "", body)
            if (
                "[data-sf-hint]" in selector
                and ":not(:hover)" in selector
                and "::after" in selector
                and re.search(r"max-width:0(?:px)?(?:;|$)|content:none|display:none", decl)
            ):
                fixes.append(f"{css_file.name}: {selector.strip()}")
    assert not fixes, f"the rulebook says the resting-box fix is unmade; shipped: {fixes}"
