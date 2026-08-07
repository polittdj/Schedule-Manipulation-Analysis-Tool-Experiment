"""SRA parity against SSI's 2026-08-06 exports — the oracle that settled ADR-0359.

The operator committed a fresh artifact set (main ``f1f13f9``): the schedule
(``00_REFERENCE_INTAKE/SRA Large Test File2.mpp``, root level — a NEWER vintage than the
``mpp/`` copy the ADR-0309 oracle uses), SSI's 5000-iteration focus-finish histogram, and —
new — SSI's **Sensitivity** export. That last sheet is what cracked the semantics open:

* SSI's "Duration Sensitivity" tornado is a **deterministic one-at-a-time re-solve** (day
  swings), not the Monte-Carlo Spearman correlation — two different instruments whose values
  are incomparable by construction.
* Its two R/O rows pin the register semantics to two decimals: the fired-alone focus slip is
  **304.48 wd for a 321-wd impact** on a 16.52-wd-ML task (and 35.03 for 45 on a 9.97-wd ML)
  — short of the impact by EXACTLY the affected activity's ML. A fired risk therefore
  **replaces** the activity's remaining duration; the old ``ML + impact`` stacking ran the
  whole distribution +25-35 calendar days long at P50-P90, and with replacement it lands
  within 1-3 days (ADR-0359).

Same reading discipline as the ADR-0309 oracle: every distribution target derives from the
occurrence-weighted histogram — the workbook's ``Mean Date`` / ``Standard Deviation`` cells
are computed over the DISTINCT dates with the weights discarded and are never asserted.
Distribution tolerances stay stated-not-exact (ADR-0106: std-lib Mersenne Twister vs a
NumPy-based commercial tool); the OAT rows are deterministic, so their tolerance is only the
export's 1-dp rounding.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import statistics as st
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.sra import (
    ScheduleRisk,
    SRAConfig,
    SSIResult,
    _ml_minutes,
    compute_oat_sensitivity,
    compute_sra_ssi,
)
from schedule_forensics.importers import parse_mpp
from schedule_forensics.model import Schedule

pytestmark = pytest.mark.parity

REPO = Path(__file__).resolve().parents[2]
MPP = REPO / "00_REFERENCE_INTAKE" / "SRA Large Test File2.mpp"
SRA_XLSX = REPO / "00_REFERENCE_INTAKE" / "SRA - Large Test File2_SRA_Results_2026-8-6.xlsx"
SENS_XLSX = (
    REPO / "00_REFERENCE_INTAKE" / "Sensitivity - Large Test File2_SRA_Results_2026-8-6.xlsx"
)

FOCUS_UID = 152
ITERATIONS = 5000
SEED = 12345
_EXCEL_EPOCH = dt.date(1899, 12, 30)
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

needs_java = pytest.mark.skipif(
    shutil.which("java") is None, reason="Java runtime not available in this environment"
)
needs_artifacts = pytest.mark.skipif(
    not (MPP.is_file() and SRA_XLSX.is_file() and SENS_XLSX.is_file()),
    reason="the 2026-08-06 SSI artifact set is not present in the reference intake",
)


def _iso_minutes(text: str | None) -> int | None:
    if not text:
        return None
    m = re.match(r"PT(?:([\d.]+)H)?(?:([\d.]+)M)?(?:([\d.]+)S)?$", text.strip())
    if m is None:
        return None
    hours, minutes, seconds = (float(g or 0) for g in m.groups())
    return round(hours * 60 + minutes + seconds / 60)


def _cells(path: Path) -> dict[str, str]:
    """sheet1's cells as {A1: value}, shared strings resolved — std-lib only."""
    with zipfile.ZipFile(path) as zf:
        shared = [
            "".join(t.text or "" for t in si.iter(f"{_M}t"))
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si")
        ]
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    cells: dict[str, str] = {}
    for row in sheet.iter(f"{_M}row"):
        for c in row.findall(f"{_M}c"):
            ref, kind, v = c.get("r"), c.get("t"), c.find(f"{_M}v")
            if ref is None or v is None or v.text is None:
                continue
            cells[ref] = shared[int(v.text)] if kind == "s" else v.text
    return cells


# --- fixtures ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def schedule() -> Schedule:
    return parse_mpp(MPP)


@pytest.fixture(scope="module")
def file_inputs(
    schedule: Schedule,
) -> tuple[dict[int, tuple[int, int, int]], list[ScheduleRisk]]:
    """The file's OWN stored SSI inputs — nothing invented here."""
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    mpd = schedule.calendar.working_minutes_per_day
    three: dict[int, tuple[int, int, int]] = {}
    risks: list[ScheduleRisk] = []
    for task in tasks:
        fields = dict(task.custom_fields)
        best = _iso_minutes(fields.get("Best Case Duration"))
        worst = _iso_minutes(fields.get("Worst Case Duration"))
        if best is not None and worst is not None:
            three[task.unique_id] = (best, ml[task.unique_id], worst)
        prob = fields.get("SSI SRA Risk Probability")
        impact = _iso_minutes(fields.get("SSI SRA Schedule Impact"))
        if prob and impact:
            risks.append(
                ScheduleRisk(
                    id=f"R{task.unique_id}",
                    name=task.name,
                    probability=float(prob),
                    impact_days=impact / mpd,
                    affected=frozenset({task.unique_id}),
                )
            )
    assert len(three) == 919, "the file's stored Best/Worst Case set changed"
    assert len(risks) == 2, "the file's stored risk register changed"
    return three, risks


@pytest.fixture(scope="module")
def oracle_hist() -> tuple[dt.date, list[tuple[dt.date, int]]]:
    cells = _cells(SRA_XLSX)
    assert int(float(cells["B3"])) == ITERATIONS, "oracle iteration count changed"
    assert cells["B4"].strip().lower() == "yes", "oracle must be the risks-included run"
    current = _EXCEL_EPOCH + dt.timedelta(days=int(float(cells["B5"])))
    rows: list[tuple[dt.date, int]] = []
    i = 10
    while f"A{i}" in cells:
        if cells.get(f"B{i}"):
            rows.append((dt.date.fromisoformat(cells[f"A{i}"]), int(float(cells[f"B{i}"]))))
        i += 1
    assert sum(n for _, n in rows) == ITERATIONS
    return current, rows


@pytest.fixture(scope="module")
def sens_rows() -> list[dict[str, float | int | str]]:
    cells = _cells(SENS_XLSX)
    out: list[dict[str, float | int | str]] = []
    i = 2
    while f"A{i}" in cells:
        out.append(
            {
                "uid": int(float(cells[f"A{i}"])),
                "name": cells.get(f"B{i}", ""),
                "opp": float(cells.get(f"E{i}") or 0),
                "risk": float(cells.get(f"F{i}") or 0),
                "total": float(cells.get(f"G{i}") or 0),
            }
        )
        i += 1
    assert len(out) == 66, "SSI's Sensitivity export changed shape"
    return out


# --- the deterministic OAT parity (the ADR-0359 semantics pin) --------------------


@needs_java
@needs_artifacts
def test_oat_matches_ssi_sensitivity_export_row_for_row(
    schedule: Schedule,
    file_inputs: tuple[dict[int, tuple[int, int, int]], list[ScheduleRisk]],
    sens_rows: list[dict[str, float | int | str]],
) -> None:
    """Every duration row and both R/O rows of SSI's Sensitivity sheet, to 1-dp rounding.

    Deterministic on both sides — no sampling tolerance involved. The sweep is restricted to
    the 66 exported rows (SSI's own top-66 by Total) so the parity gate stays minutes, not
    hours."""
    three, risks = file_inputs
    duration_uids = {r["uid"] for r in sens_rows if not str(r["name"]).startswith("R/O")}
    ro_rows = [r for r in sens_rows if str(r["name"]).startswith("R/O")]
    assert len(ro_rows) == 2, "the export's two R/O rows are the semantics pin"
    targeted = {u: three[u] for u in duration_uids if u in three}
    assert len(targeted) == len(duration_uids), "an exported duration row lost its stored 3-point"
    oat = compute_oat_sensitivity(schedule, three_point=targeted, target_uid=FOCUS_UID, risks=risks)
    dur = {o.unique_id: o for o in oat if o.risk_id is None}
    ro = {o.unique_id: o for o in oat if o.risk_id is not None}
    for row in sens_rows:
        uid = int(row["uid"])
        if str(row["name"]).startswith("R/O"):
            got = ro[uid]
            assert abs(got.risk_days - float(row["risk"])) <= 0.06, (
                f"R/O row {uid}: engine {got.risk_days} vs SSI {row['risk']} — the fired-alone "
                "slip IS the replace-semantics pin (impact replaces the ML, ADR-0359)"
            )
        else:
            got = dur[uid]
            # SSI signs opportunity negative; the engine's convention is positive-good.
            assert abs(got.opportunity_days - abs(float(row["opp"]))) <= 0.06, (
                f"duration row {uid} opportunity: engine {got.opportunity_days} vs SSI {row['opp']}"
            )
            assert abs(got.risk_days - float(row["risk"])) <= 0.06, (
                f"duration row {uid} risk: engine {got.risk_days} vs SSI {row['risk']}"
            )
    # the ranking agrees where the gaps are unambiguous: SSI's top five, in order
    top5 = [(int(r["uid"]), str(r["name"]).startswith("R/O")) for r in sens_rows[:5]]
    assert [(o.unique_id, o.risk_id is not None) for o in oat[:5]] == top5


# --- the stochastic distribution parity -------------------------------------------


@pytest.fixture(scope="module")
def ssi_run(
    schedule: Schedule,
    file_inputs: tuple[dict[int, tuple[int, int, int]], list[ScheduleRisk]],
) -> SSIResult:
    three, risks = file_inputs
    return compute_sra_ssi(
        schedule,
        config=SRAConfig(iterations=ITERATIONS, seed=SEED, target_uid=FOCUS_UID),
        three_point=three,
        risks=risks,
    )


def _run_dates(schedule: Schedule, run: SSIResult) -> list[dt.date]:
    focus = next(t for t in non_summary(schedule) if t.unique_id == FOCUS_UID)
    assert focus.finish is not None
    cal, start = schedule.calendar, schedule.project_start
    naive = offset_to_datetime(start, max(run.deterministic_finish, 0), cal)
    correction = focus.finish - naive

    def as_date(offset: float) -> dt.date:
        return (offset_to_datetime(start, max(round(offset), 0), cal) + correction).date()

    out: list[dt.date] = []
    previous = 0.0
    for offset, cumulative in run.cdf:
        out += [as_date(offset)] * round((cumulative - previous) * ITERATIONS)
        previous = cumulative
    return out


@needs_java
@needs_artifacts
def test_distribution_matches_the_weighted_histogram(
    schedule: Schedule,
    ssi_run: SSIResult,
    oracle_hist: tuple[dt.date, list[tuple[dt.date, int]]],
) -> None:
    """Mean/sigma/P50/P80/P90 against the occurrence-weighted histogram (never the summary cells).

    Measured landing under replace semantics: mean -3.3 cal, sigma +1.8%, percentiles ≤3 cal d.
    Tolerances are ~3x the measurement so a Mersenne-vs-NumPy re-seed cannot flake them, yet
    the old additive semantics (mean +25, P50-P90 +32-35) fails every one of them."""
    current, rows = oracle_hist
    samples = [d for d, n in rows for _ in range(n)]
    o_off = [(d - current).days for d in samples]
    dates = _run_dates(schedule, ssi_run)
    assert len(dates) == ITERATIONS
    e_off = [(d - current).days for d in dates]

    focus = next(t for t in non_summary(schedule) if t.unique_id == FOCUS_UID)
    assert focus.finish is not None and focus.finish.date() == current, (
        "the stored focus finish IS SSI's Current Finish — input identity, not a tolerance"
    )

    assert abs(st.mean(e_off) - st.mean(o_off)) <= 10.0
    assert abs(st.pstdev(e_off) / st.pstdev(o_off) - 1.0) <= 0.05

    def quantile(vals: list[dt.date], pct: float) -> dt.date:
        s = sorted(vals)
        return s[min(len(s) - 1, int(pct * len(s)))]

    def oracle_quantile(pct: float) -> dt.date:
        seen = 0
        for d, n in rows:
            seen += n
            if seen / ITERATIONS >= pct:
                return d
        return rows[-1][0]

    for pct in (0.50, 0.80, 0.90):
        gap = abs((quantile(dates, pct) - oracle_quantile(pct)).days)
        assert gap <= 9, f"P{int(pct * 100)} off by {gap} cal d"


@needs_java
@needs_artifacts
def test_per_risk_outcomes_land_on_the_fired_alone_swings(ssi_run: SSIResult) -> None:
    """The register outcomes: hit rates within binomial noise of the stored probabilities, and
    each mean fired-vs-not delta within a few wd of SSI's deterministic fired-alone swing
    (304.48 / 35.03 — interactions with the background variation explain the residual)."""
    by_id = {r.id: r for r in ssi_run.risks}
    r1, r2 = by_id["R7443"], by_id["R7433"]
    assert abs(r1.hits / ITERATIONS - 0.86) <= 0.02
    assert abs(r2.hits / ITERATIONS - 0.63) <= 0.02
    assert abs(r1.mean_delta_days - 304.48) <= 8.0
    assert abs(r2.mean_delta_days - 35.03) <= 8.0
