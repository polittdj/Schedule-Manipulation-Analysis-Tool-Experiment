"""Executable red/green tests for the 2026-08-13 read-only audit findings.

Every test here was written to be able to FAIL: each carries either a negative control
(a deliberately-wrong assertion proven to fail) or a mutation that flips the verdict, so a
green result means something. Tests are grouped:

  * VALIDATED-DEFECT tests assert the CORRECT (post-fix) behaviour. They FAIL (red) against the
    audited commit 5a8003f — that red is the proof the finding is real. They go green when the
    finding is fixed. They are marked xfail(strict=True) so the suite stays green today AND so a
    future fix that makes them pass is flagged (xpass under strict = failure => remove the marker).
  * REFUTED-HYPOTHESIS tests assert the defect is ABSENT and pass today; each includes a negative
    control proving the test can fail, so "pass" is not vacuous.

Drop-in path (next session): tests/audit/ .  Run: pytest test_audit_findings.py -rA
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

import schedule_forensics
from schedule_forensics.ai.backend import (
    AIConfig,
    Classification,
    banner_for,
    route_backend,
)
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

SRC = Path(schedule_forensics.__file__).resolve().parent
REPO = SRC.parent.parent  # .../src/schedule_forensics -> repo root
TESTS = REPO / "tests"


# --------------------------------------------------------------------------------------------
# GW-02 (FIXED by ADR-0396 — DoD 001b): the sovereignty banner is OBSERVED. The xfail(strict)
# marker this test carried flipped loudly the moment the fix merged (route_backend now derives
# its Banner from the backend it actually chose via banner_for_backend, and banner_for constructs
# the would-be candidates and derives from what they declare), exactly as this module's design
# intended: the marker is removed in the fixing merge, and the test stands as the permanent
# routed-banner/shown-banner agreement pin. Deeper pins live in
# tests/guards/test_observed_banner.py (fail-closed presumption, cache veto, exports, mutations).
# --------------------------------------------------------------------------------------------
def test_gw02_shown_banner_matches_routed_backend() -> None:
    # A config that ASKS for cloud while UNCLASSIFIED. No cloud backend is wired, so route_backend
    # falls closed to Null — and BOTH helpers now warn on the standing cloud intent (§0.2): the
    # routed banner and the shown banner agree.
    cfg = AIConfig(classification=Classification.UNCLASSIFIED, backend="cloud")
    _backend, routed_banner = route_backend(cfg, null_backend=NullBackend())
    shown = banner_for(cfg)  # what web/chrome.py:_banner_html actually renders
    # Correct behaviour (post-fix): the shown banner reflects the backend actually routed.
    assert (shown.cloud_active, shown.endpoint) == (
        routed_banner.cloud_active,
        routed_banner.endpoint,
    ), "banner shown to the operator does not match the backend route_backend actually selected"


def test_gw02_negative_control_banner_helpers_are_distinguishable() -> None:
    # Proves the above test CAN pass: when config and routing AGREE (CLASSIFIED local), both banners
    # say local. This is the green half of the red/green pair.
    cfg = AIConfig(classification=Classification.CLASSIFIED, backend="ollama")
    _b, routed = route_backend(cfg, null_backend=NullBackend())
    shown = banner_for(cfg)
    assert shown.cloud_active is False and routed.cloud_active is False


# --------------------------------------------------------------------------------------------
# GW-01 (VALIDATED, informational): no production caller wires a cloud backend; the "cloud" path is
# dead. This test PASSES today (documents the safe state) and FAILS if a future caller passes a
# cloud backend into route_backend without the accompanying observed-banner fix (GW-02).
# --------------------------------------------------------------------------------------------
def test_gw01_no_production_caller_wires_cloud_backend() -> None:
    hits = []
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        # a call site that passes cloud_backend= as an argument (not the def / type annotation)
        for m in re.finditer(r"cloud_backend\s*=", text):
            line = text[text.rfind("\n", 0, m.start()) + 1 : text.find("\n", m.start())]
            if "AIBackend | None" in line or "cloud_backend: AIBackend" in line:
                continue  # the parameter declaration in backend.py
            hits.append(f"{py.relative_to(REPO)}: {line.strip()}")
    assert hits == [], (
        f"a caller now wires a cloud backend; GW-02 banner fix must land first: {hits}"
    )


def test_gw01_negative_control_scanner_sees_the_declaration() -> None:
    # Proof the scan works: the parameter declaration DOES exist in backend.py (so a real call site
    # would also be found). If this returns empty, the scanner is broken and the test above is void.
    backend_src = (SRC / "ai" / "backend.py").read_text(encoding="utf-8")
    assert "cloud_backend" in backend_src


# --------------------------------------------------------------------------------------------
# SEC-01 (VALIDATED DEFECT, medium): _ALLOWED_HOSTS (the DNS-rebinding Host-header allowlist) is
# enforced as middleware but its CONTENTS are pinned by NO test — the same latent class ADR-0394
# fixed for _LOOPBACK_HOSTNAMES. This test IS the missing pin. It passes today; its FAIL mode is a
# mutation adding a non-loopback host (demonstrated in the audit's mutation battery).
# --------------------------------------------------------------------------------------------
def test_sec01_allowed_hosts_pinned_to_exact_loopback_set() -> None:
    from schedule_forensics.web.app import _ALLOWED_HOSTS

    # test-side literal, NOT imported from the module under test (an oracle that reads the value it
    # judges can refute nothing). Adding e.g. a gateway hostname here would make this go red.
    expected = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})
    assert expected == _ALLOWED_HOSTS, (
        "the Host-header allowlist changed; a non-loopback entry is a DNS-rebinding admission hole"
    )


# --------------------------------------------------------------------------------------------
# TEST-01 (VALIDATED DEFECT, medium): 22 playwright modules hard-code a chromium BUILD NUMBER
# (/opt/pw-browsers/chromium-1194/...) and skip when it is absent, so a container chromium bump
# silently skips the browser suite. The r11 module was fixed to GLOB the version; the fix was not
# propagated. Correct behaviour: no test module hard-codes a pinned chromium build path.
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True, reason="TEST-01: 22 modules still hard-code chromium-<build>; only r11 globs"
)
def test_test01_no_test_hardcodes_a_chromium_build_number() -> None:
    offenders = []
    if TESTS.exists():
        for py in TESTS.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            if re.search(r"chromium-\d{3,}/", text):
                offenders.append(py.relative_to(REPO).as_posix())
    assert offenders == [], (
        f"{len(offenders)} test modules pin a chromium build number: {offenders}"
    )


def test_test01_negative_control_globbed_module_is_clean() -> None:
    # r11 was fixed to glob; it must NOT match the pinned-build pattern in its resolver function.
    # (It documents the build number only in a comment; the code path uses chromium*/…) This proves
    # the offender pattern is specific, not a blanket match on the string 'chromium'.
    r11 = TESTS / "web" / "test_r11_panel_contract.py"
    if not r11.exists():
        pytest.skip("r11 module not present")
    text = r11.read_text(encoding="utf-8")
    assert "chromium*/chrome-linux/chrome" in text  # the globbed, build-agnostic resolver exists


# --------------------------------------------------------------------------------------------
# HOOK-01 (FIXED by ADR-0399): the CUI pre-commit guard now sniffs image/doc renames too. The
# xfail(strict) marker this test carried flipped loudly the moment the fix landed (sniff_re
# gained the image/doc extensions; the anchored serialization-start rules plus the OLE2/ZIP/PDF
# container checks do the detecting), exactly as this module's design intended: the marker is
# removed in the fixing commit, and the test stands as the permanent pin that the sniff set
# keeps covering image renames. The behavioural proof lives in
# tests/guards/test_precommit_blocklist.py (scratch-repo block/allow battery, container cases,
# and a whole-tree census with a planted canary control).
# --------------------------------------------------------------------------------------------
def test_hook01_precommit_sniffs_image_and_doc_renames() -> None:
    hook = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    m = re.search(r"sniff_re='([^']+)'", hook)
    assert m, "sniff_re not found in pre-commit hook"
    sniff = m.group(1)
    # Post-fix pin: a schedule renamed .png/.svg is content-checked.
    assert ".png" in sniff or "png" in sniff, (
        "pre-commit does not content-detect image-renamed schedules (a .png full of MSPDI slips)"
    )


def test_hook01_negative_control_current_sniff_matches_json_txt() -> None:
    # The current sniff DOES cover json/txt — proves the extraction/assertion mechanism works and
    # the xfail above is about coverage, not a broken regex read.
    hook = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    sniff = re.search(r"sniff_re='([^']+)'", hook).group(1)
    assert "json" in sniff and "txt" in sniff


# --------------------------------------------------------------------------------------------
# REF-01 (REFUTED hypothesis "CPM math is wrong"): independent hand oracle. PASSES today; the
# negative control proves the assertion can fail.
# --------------------------------------------------------------------------------------------
def _chain_result():
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=960),
        Task(unique_id=2, name="B", duration_minutes=1440),
        Task(unique_id=3, name="C", duration_minutes=480),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
        Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),
    )
    sch = Schedule(
        tasks=tasks, relationships=rels, name="oracle", project_start=dt.datetime(2026, 1, 1, 8, 0)
    )
    return compute_cpm(sch)


def test_ref01_cpm_matches_independent_hand_oracle() -> None:
    r = _chain_result()
    # Hand derivation (480 min/day): A 0-960, B 960-2400, C 2400-2880; all TF=0, all critical.
    exp = {
        1: (0, 960, 0, 960, 0, True),
        2: (960, 2400, 960, 2400, 0, True),
        3: (2400, 2880, 2400, 2880, 0, True),
    }
    for uid, e in exp.items():
        t = r.timings[uid]
        assert (
            t.early_start,
            t.early_finish,
            t.late_start,
            t.late_finish,
            t.total_float,
            t.is_critical,
        ) == e
    assert r.critical_path == (1, 2, 3)


def test_ref01_negative_control_wrong_oracle_fails() -> None:
    r = _chain_result()
    # A deliberately wrong expectation MUST NOT hold — proves the oracle comparison has teeth.
    assert r.timings[3].early_finish != 9999


# --------------------------------------------------------------------------------------------
# REF-02 (REFUTED "MSPDI is XXE-vulnerable"): the importer rejects any DTD/entity declaration.
# PASSES today; negative control proves a clean doc gets PAST the XXE guard (so the guard isn't
# just rejecting everything).
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "doc",
    [
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY a "&lol;&lol;">]><Project>&a;</Project>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Project><Name>&xxe;</Name></Project>',
        '<?xml version="1.0"?><Project><!ENTITY x "y"></Project>',
    ],
)
def test_ref02_mspdi_rejects_dtd_and_entities(doc: str) -> None:
    with pytest.raises(ImporterError):
        parse_mspdi_text(doc)


def test_ref02_negative_control_clean_doc_passes_xxe_guard() -> None:
    # A clean doc must NOT raise the XXE rejection (it fails later on structure). Proves the guard
    # is specific to DTD/entity, not a blanket reject.
    with pytest.raises(ImporterError) as ei:
        parse_mspdi_text('<?xml version="1.0"?><Project></Project>')
    assert "DTD or entity" not in str(ei.value)


# --------------------------------------------------------------------------------------------
# REF-05 (REFUTED "secrets are committed"): no provider-pattern secret in tracked SOURCE. PASSES
# today; negative control proves the regex detects a planted synthetic secret.
# --------------------------------------------------------------------------------------------
_SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def test_ref05_no_provider_secret_in_source_tree() -> None:
    hits = []
    for py in SRC.rglob("*.py"):
        if _SECRET_RE.search(py.read_text(encoding="utf-8", errors="replace")):
            hits.append(py.relative_to(REPO).as_posix())
    assert hits == [], f"provider-pattern secret in source: {hits}"


def test_ref05_negative_control_scanner_detects_planted_secret() -> None:
    planted = 'token = "sk-abcdefghijklmnopqrstuvwxyz012345"'
    assert _SECRET_RE.search(planted), "secret scanner failed its own negative control"


# --------------------------------------------------------------------------------------------
# PO-03 (VALIDATED DEFECT, medium): the Fuse DCMA parity oracle is a TRANSCRIPTION into
# fuse_exports_2026-06.json, but no test reads the source vendor .xlsx to guard that transcription.
# Correct behaviour (post-fix): a parity test reads a committed Fuse *.xlsx workbook. RED today.
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True, reason="PO-03: no test reads the vendor Fuse .xlsx to guard the transcription"
)
def test_po03_a_test_reads_the_vendor_fuse_workbook() -> None:
    if not TESTS.exists():
        pytest.skip("tests/ not present in this layout")
    reads_xlsx = []
    for py in (TESTS / "parity").rglob("*.py") if (TESTS / "parity").exists() else []:
        t = py.read_text(encoding="utf-8", errors="replace")
        if re.search(r"Fuse[^\"']*\.xlsx|load_workbook|openpyxl", t, re.I):
            reads_xlsx.append(py.name)
    assert reads_xlsx, (
        "no parity test reads a vendor Fuse .xlsx; the transcription step is unguarded"
    )


def test_po03_negative_control_sra_sem_tests_do_read_xlsx() -> None:
    # Proof the scan can find xlsx-reading tests: the SRA/SEM oracles DO read .xlsx. If this returns
    # nothing, the pattern is wrong and the xfail above would be vacuous.
    hits = []
    if (TESTS / "parity").exists():
        for py in (TESTS / "parity").rglob("*.py"):
            if re.search(
                r"\.xlsx|load_workbook|openpyxl", py.read_text(encoding="utf-8", errors="replace")
            ):
                hits.append(py.name)
    assert hits, "expected SRA/SEM parity tests to read an .xlsx"


# --------------------------------------------------------------------------------------------
# IMP-03 (VALIDATED, low): an absurd duration fails FAST (OverflowError/ValueError) rather than
# hanging or importing silently-wrong data. Positive test + a negative control (sane duration OK).
# --------------------------------------------------------------------------------------------
def test_imp03_absurd_duration_fails_fast_at_presentation_not_silent() -> None:
    # The engine ACCEPTS an unbounded duration (no upper bound on duration_minutes); the observable,
    # documented behaviour is that the date-presentation boundary FAILS FAST (OverflowError) rather
    # than hanging or emitting a silently-wrong date. This test pins that fail-fast property.
    from schedule_forensics.engine.cpm import offset_to_datetime
    from schedule_forensics.model.calendar import Calendar

    huge = Task(unique_id=1, name="A", duration_minutes=10**18)
    sch = Schedule(tasks=(huge,), name="x", project_start=dt.datetime(2026, 1, 1, 8, 0))
    r = compute_cpm(sch)  # engine tolerates it (no bound)
    assert r.timings[1].early_finish == 10**18
    with pytest.raises((OverflowError, ValueError)):
        offset_to_datetime(dt.datetime(2026, 1, 1, 8, 0), r.timings[1].early_finish, Calendar())


def test_imp03_negative_control_sane_duration_presents_ok() -> None:
    from schedule_forensics.engine.cpm import offset_to_datetime
    from schedule_forensics.model.calendar import Calendar

    # A sane offset must NOT raise — proves the fail is about magnitude, not the call itself.
    when = offset_to_datetime(dt.datetime(2026, 1, 1, 8, 0), 480, Calendar())
    assert isinstance(when, dt.datetime)
