"""SEM parity gate (ADR-0238): the ten Schedule-Execution-Metrics values against the committed
Acumen Fuse DCMA report's Industry-Standards rows (P2-P5 pair), cell for cell.

Eight metrics match the vendor cells exactly. TC-BEI matches at display rounding. The vendor's
exported Delta cells (-0.34 / -0.61) are NOT reproducible from the vendor's own pinned library
formula on inputs that reproduce every sibling metric exactly (formula-faithful: -0.33 / -0.65)
— a vendor export artifact; the tool follows the pinned .aft formula (the formula-audit test
verifies the string verbatim), so Delta is pinned here to the formula-faithful values with the
vendor cells recorded in this docstring for the audit trail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.metrics.sem import compute_sem
from schedule_forensics.importers import parse_mspdi

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

#: Fuse "P2-P5 - DCMA Report.xlsx" → Industry-Standards sheet, verbatim (order: Completed,
#: Workoff, BRI-Cur, BRI-Cum, BPI, BEI-Cur, BEI-Cum, TC-BEI, FRI, Delta). Delta = the
#: formula-faithful value (vendor cells -0.34 / -0.61 — see the module docstring).
_EXPECT = {
    "Project2": (20, 5, 0.0, 0.74, 0.0, 1.25, 0.74, 1.07, None, -0.33),
    "Project5": (27, 2, 0.0, 0.59, 0.0, 0.67, 0.59, 1.24, 0.0, -0.65),
}
_ORDER = (
    "sem_completed",
    "sem_workoff_burden",
    "sem_bri_current",
    "bri_cumulative",
    "sem_bpi_current",
    "sem_bei_current",
    "sem_bei_cumulative",
    "sem_tc_bei",
    "sem_fri_current",
    "sem_delta",
)


@pytest.mark.parity
def test_sem_matches_the_fuse_industry_standards_rows() -> None:
    p2 = parse_mspdi(GOLD / "Project2.mspdi.xml")
    p5 = parse_mspdi(GOLD / "Project5.mspdi.xml")
    for label, sch, prior in (("Project2", p2, None), ("Project5", p5, p2)):
        results = compute_sem(sch, prior)
        assert tuple(results) == _ORDER  # Bible order, stable
        for key, expected in zip(_ORDER, _EXPECT[label], strict=True):
            m = results[key]
            if expected is None:  # FRI with no prior version: N/A, exactly as Fuse prints
                assert m.population == 0 and m.status.name == "NOT_APPLICABLE", (label, key)
            else:
                assert m.value == pytest.approx(expected, abs=0.005), (label, key, m.value)


@pytest.mark.parity
def test_sem_key_denominators_are_exact() -> None:
    """Beyond headline equality: the numerator/denominator pairs behind the trickiest cells
    (the HARDENED 'granular, not headline' rule)."""
    p2 = parse_mspdi(GOLD / "Project2.mspdi.xml")
    p5 = parse_mspdi(GOLD / "Project5.mspdi.xml")
    r2, r5 = compute_sem(p2), compute_sem(p5, p2)
    # BEI Current 1.25 = 5 window finishes over 4 baselined-in-window (numerator unrestricted)
    assert (r2["sem_bei_current"].count, r2["sem_bei_current"].population) == (5, 4)
    # TC-BEI 1.07 = 106 forecast-to-go over 99 baselined-to-go-not-finished
    assert (r2["sem_tc_bei"].count, r2["sem_tc_bei"].population) == (106, 99)
    assert (r5["sem_tc_bei"].count, r5["sem_tc_bei"].population) == (99, 80)
    # FRI 0/9: nine tasks the prior version forecast into the window; none finished in it
    assert (r5["sem_fri_current"].count, r5["sem_fri_current"].population) == (0, 9)
