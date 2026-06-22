"""P2→P3→P4→P5 cross-version validation against Acumen Fuse's ``2345`` Metric History Report.

The operator's ``2345 - Metric History Report.xlsx`` scores the manipulation series as **four
consecutive snapshots** of one schedule — ``Project2`` (status 2026-05-24) → ``Project3`` (06-30) →
``Project4`` (07-29) → ``Project5_TAMPERED`` (08-27). This test loads the authoritative source
``.mpp`` files (converted fresh via the vendored MPXJ) and asserts the tool reproduces Acumen's
per-version numbers across the chain — the first time **Project3 / Project4** are validated against
Acumen (Project2 / Project5 were covered by the parity goldens; this extends to the full chain and
the High-Float fix from ADR-0109/#204, which lands P5 High Float at an exact 44).

Cross-version **CEI / HMI** are intentionally **deferred**: Acumen reports ``Critical CEI`` as
**N/A** for every snapshot of this chain (and of the TP / 2345 chains — no consecutive-period
``Previous*`` linkage), and the Metric-History template carries **no HMI rows** at all. The only
non-N/A CEI reference on hand is the ``L12`` (Large-Test-File v1→v2) report, whose source ``.mpp``
is not in the intake this session — so a CEI/HMI cross-version reference test awaits that file.
See ADR-0110 / ``docs/STATE/HANDOFF.md``.

Like ``test_mpp_mpxj`` / the ``.aft`` audit, this **skips** when the (git-ignored, non-CUI) source
schedules or a JVM are absent (e.g. on CI), and runs on an operator machine that has the intake.
NOT marked ``parity`` — it is a forward-looking Acumen reference harness (currently all-exact).
"""

from __future__ import annotations

import datetime as dt
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics import compute_dcma14, compute_schedule_quality
from schedule_forensics.importers import parse_mpp
from schedule_forensics.model.schedule import Schedule

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INTAKE = _REPO_ROOT / "00_REFERENCE_INTAKE"


@dataclass(frozen=True)
class Expected:
    """Acumen ``2345 - Metric History Report`` values for one snapshot of the chain."""

    mpp: str
    status: dt.date
    bei: float  # BEI - Value Tasks
    bei_complete: int  # BEI - Complete Tasks (numerator)
    critical: int  # Critical Path (Tasks & Milestones) == Zero Days Float
    high_float: int  # High Float 44d
    hard_constraints: int  # Hard Constraints
    negative_float: int  # Negative Float
    missing_logic: int  # Missing Logic (incomplete-scoped, as the report reports it)


# Verbatim from ``00_REFERENCE_INTAKE/audit/2345_bundle/2345 - Metric History Report.xlsx``.
CHAIN: tuple[Expected, ...] = (
    Expected("Project2.mpp", dt.date(2026, 5, 24), 0.74, 20, 41, 44, 0, 0, 4),
    Expected("Project3.mpp", dt.date(2026, 6, 30), 0.67, 24, 40, 42, 0, 0, 4),
    Expected("Project4.mpp", dt.date(2026, 7, 29), 0.58, 25, 37, 41, 0, 0, 4),
    Expected("Project5_TAMPERED.mpp", dt.date(2026, 8, 27), 0.59, 27, 4, 44, 1, 0, 5),
)


def _find(mpp: str) -> Path | None:
    if not _INTAKE.exists():
        return None
    hits = sorted(_INTAKE.rglob(mpp))
    return hits[0] if hits else None


_have_java = shutil.which("java") is not None
_missing = [e.mpp for e in CHAIN if _find(e.mpp) is None]

pytestmark = pytest.mark.skipif(
    not _have_java or bool(_missing),
    reason=(
        "Java runtime not available"
        if not _have_java
        else f"chain .mpp not present (git-ignored intake): {_missing}"
    ),
)


@pytest.fixture(scope="module")
def chain() -> dict[str, Schedule]:
    out: dict[str, Schedule] = {}
    for e in CHAIN:
        path = _find(e.mpp)
        assert path is not None  # guarded by pytestmark
        out[e.mpp] = parse_mpp(path)
    return out


def test_chain_loads_four_consecutive_snapshots(chain: dict[str, Schedule]) -> None:
    for e in CHAIN:
        s = chain[e.mpp]
        assert s.status_date is not None
        assert s.status_date.date() == e.status, e.mpp


def test_bei_matches_acumen_across_the_chain(chain: dict[str, Schedule]) -> None:
    """BEI - Value Tasks (and its complete-task numerator) for all four snapshots."""
    for e in CHAIN:
        d = compute_dcma14(chain[e.mpp])
        assert round(d["DCMA14"].value, 2) == e.bei, e.mpp
        assert d["DCMA14"].count == e.bei_complete, e.mpp


def test_structural_metrics_match_acumen_across_the_chain(chain: dict[str, Schedule]) -> None:
    """Critical path, High Float (44d), Hard Constraints, Negative Float, Missing Logic."""
    for e in CHAIN:
        s = chain[e.mpp]
        c = compute_cpm(s)
        d = compute_dcma14(s)
        sq = compute_schedule_quality(s, c)
        assert sq["critical"].count == e.critical, e.mpp  # == Zero Days Float
        assert d["DCMA06"].count == e.high_float, e.mpp  # High Float 44d (stored slack, #204)
        assert d["DCMA05"].count == e.hard_constraints, e.mpp
        assert d["DCMA07"].count == e.negative_float, e.mpp
        assert d["DCMA01"].count == e.missing_logic, e.mpp  # incomplete-scoped, as Acumen reports
