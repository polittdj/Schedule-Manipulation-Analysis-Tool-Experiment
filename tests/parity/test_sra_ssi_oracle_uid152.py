"""SRA parity against SSI's OWN exported result (ADR-0309).

This is the first SRA test whose expected values come from the reference tool rather than from the
tool's own arithmetic. ADR-0307 recorded that the previous "headline parity anchor" was
self-referential; the fix for that is a test whose numbers are read out of a committed SSI export at
run time, so it cannot drift into agreeing with whatever the engine currently does.

Both halves of the comparison are committed and non-CUI (ADR-0003/0151/0152):

* input  — ``00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp``, which carries SSI's whole SRA
  *input* set in MS Project custom fields: ``SSI SRA Event`` (the focus flag, UID 152),
  ``Best Case Duration`` / ``Worst Case Duration`` on 919 activities, and
  ``SSI SRA Risk Probability`` / ``SSI SRA Schedule Impact`` on the two register risks.
* output — ``00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_*.xlsx``, SSI's 2000-iteration
  focus-finish histogram (245 distinct dates, 2000 occurrences).

**Read the workbook's summary cells with care.** Its ``Mean Date`` and ``Standard Deviation`` cells
are computed over the 245 DISTINCT dates with the ``Occurrences`` weights discarded (reproduced to
~11 ULP in ``audit/SRA-PARITY-20260729.md`` §1 and re-derived independently in
``audit/SRA-ROOTCAUSE-20260730.md`` §1.3). Its ``% Cumulative Probability`` column IS
occurrence-weighted. So this test derives every target from the histogram itself and never asserts
against those two cells — matching them would be a coincidence trap, not parity.

Tolerances are stated rather than exact because ADR-0106 documents that the std-lib Mersenne Twister
is not expected to match a NumPy-based commercial tool draw-for-draw. They are tight enough to fail
loudly: before ADR-0309 it missed the deterministic percentile by 35 points and sigma by 94 %.
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
    compute_sra_ssi,
)
from schedule_forensics.importers import parse_mpp
from schedule_forensics.model import Schedule

pytestmark = pytest.mark.parity

REPO = Path(__file__).resolve().parents[2]
MPP = REPO / "00_REFERENCE_INTAKE" / "mpp" / "SRA Large Test File2.mpp"
SSI_DIR = REPO / "00_REFERENCE_INTAKE" / "ssi"

FOCUS_UID = 152
ITERATIONS = 2000
SEED = 12345
_EXCEL_EPOCH = dt.date(1899, 12, 30)
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

needs_java = pytest.mark.skipif(
    shutil.which("java") is None, reason="Java runtime not available in this environment"
)
needs_mpp = pytest.mark.skipif(
    not MPP.is_file(), reason="SRA Large Test File2.mpp not present in the reference intake"
)


def _oracle_workbook() -> Path:
    hits = sorted(SSI_DIR.glob("SRA Large Test File2_SRA_Results_*.xlsx"))
    if not hits:
        pytest.skip("SSI SRA results export not present in the reference intake")
    return hits[-1]


def _iso_minutes(text: str | None) -> int | None:
    """An MSPDI ISO-8601 duration (``PT424H0M0S``) → whole working minutes."""
    if not text:
        return None
    m = re.match(r"PT(?:([\d.]+)H)?(?:([\d.]+)M)?(?:([\d.]+)S)?$", text.strip())
    if m is None:
        return None
    hours, minutes, seconds = (float(g or 0) for g in m.groups())
    return round(hours * 60 + minutes + seconds / 60)


# --- the SSI oracle ---------------------------------------------------------------


class _Oracle:
    """SSI's exported focus-finish distribution, occurrence-weighted."""

    def __init__(self, path: Path) -> None:
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
        assert int(float(cells["B3"])) == ITERATIONS, "oracle iteration count changed"
        assert cells["B4"].strip().lower() == "yes", "oracle must be the risks-included run"
        self.current_finish = _EXCEL_EPOCH + dt.timedelta(days=int(float(cells["B5"])))
        # (date, occurrences) straight off the histogram — the weights the summary cells drop
        self.rows: list[tuple[dt.date, int]] = []
        i = 10
        while f"A{i}" in cells:
            occ = cells.get(f"B{i}")
            if occ:
                self.rows.append((dt.date.fromisoformat(cells[f"A{i}"]), int(float(occ))))
            i += 1
        self.samples = [d for d, n in self.rows for _ in range(n)]

    @property
    def total(self) -> int:
        return len(self.samples)

    def offset(self, day: dt.date) -> int:
        """Calendar days from the deterministic (SSI "Current Finish") date."""
        return (day - self.current_finish).days

    def percentile_at(self, day: dt.date) -> float:
        """Fraction of iterations finishing on or before ``day`` — the tool's ``<=`` basis."""
        return sum(n for d, n in self.rows if d <= day) / self.total

    def quantile(self, pct: float) -> dt.date:
        """First histogram date whose cumulative share reaches ``pct``."""
        seen = 0
        for day, n in self.rows:
            seen += n
            if seen / self.total >= pct:
                return day
        return self.rows[-1][0]


# --- fixtures ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def oracle() -> _Oracle:
    return _Oracle(_oracle_workbook())


@pytest.fixture(scope="module")
def schedule() -> Schedule:
    """The reference schedule, converted from the committed .mpp by the vendored MPXJ (~30 s)."""
    return parse_mpp(MPP)


@pytest.fixture(scope="module")
def ssi_run(schedule: Schedule) -> SSIResult:
    """The SRA run configured from the file's OWN SSI inputs — nothing invented here."""
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}

    three_point: dict[int, tuple[int, int, int]] = {}
    risks: list[ScheduleRisk] = []
    mpd = schedule.calendar.working_minutes_per_day
    for task in tasks:
        fields = dict(task.custom_fields)
        best = _iso_minutes(fields.get("Best Case Duration"))
        worst = _iso_minutes(fields.get("Worst Case Duration"))
        if best is not None and worst is not None:
            three_point[task.unique_id] = (best, ml[task.unique_id], worst)
        prob, impact = fields.get("SSI SRA Risk Probability"), fields.get("SSI SRA Schedule Impact")
        impact_minutes = _iso_minutes(impact)
        if prob and impact_minutes:
            risks.append(
                ScheduleRisk(
                    id=f"R{task.unique_id}",
                    name=task.name,
                    probability=float(prob),
                    impact_days=impact_minutes / mpd,
                    affected=frozenset({task.unique_id}),
                )
            )

    assert len(three_point) == 919, "SSI's stored Best/Worst Case set changed"
    assert len(risks) == 2, "SSI's stored risk register changed"
    return compute_sra_ssi(
        schedule,
        config=SRAConfig(iterations=ITERATIONS, seed=SEED, target_uid=FOCUS_UID),
        three_point=three_point,
        risks=risks,
    )


def _weighted_dates(schedule: Schedule, run: SSIResult) -> list[dt.date]:
    """The run's realigned finish dates, one per iteration, rebuilt from its own CDF."""
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


# --- the parity assertions --------------------------------------------------------


@needs_java
@needs_mpp
def test_the_focus_and_inputs_are_the_ones_ssi_ran(schedule: Schedule, oracle: _Oracle) -> None:
    """The file's own SSI focus flag picks UID 152, and its stored finish is SSI's anchor."""
    flagged = [
        t.unique_id
        for t in non_summary(schedule)
        if dict(t.custom_fields).get("SSI SRA Event") in ("1", "Yes", "true")
    ]
    assert flagged == [FOCUS_UID]
    focus = next(t for t in non_summary(schedule) if t.unique_id == FOCUS_UID)
    assert focus.finish is not None
    assert focus.finish.date() == oracle.current_finish == dt.date(2029, 4, 19)
    assert oracle.total == ITERATIONS


@needs_java
@needs_mpp
def test_the_deterministic_finish_is_computed_not_imposed(schedule: Schedule) -> None:
    """ADR-0309: the CPM reaches the stored finish on its own.

    Before ADR-0309 ordinary ``compute_cpm`` put UID 152 at 2025-06-30 — 1,388 calendar days early —
    and only the display correction hid it. Asserting the RAW offset (not the realigned display
    date) is the point: a constant correction can make any basis land on the anchor.
    """
    from schedule_forensics.engine.cpm import compute_cpm

    raw = compute_cpm(schedule).timings[FOCUS_UID].early_finish
    computed = offset_to_datetime(schedule.project_start, raw, schedule.calendar)
    focus = next(t for t in non_summary(schedule) if t.unique_id == FOCUS_UID)
    assert focus.finish is not None
    assert abs((computed - focus.finish).total_seconds()) <= 60


@needs_java
@needs_mpp
def test_all_ml_reproduces_compute_cpm_on_a_progressed_file(schedule: Schedule) -> None:
    """The ADR-0106 equivalence, which was FALSE by 370 working days before ADR-0309."""
    from schedule_forensics.engine.cpm import compute_cpm

    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    assert sum(1 for t in tasks if ml[t.unique_id] != t.duration_minutes) == 92, (
        "the in-progress population changed; the equivalence claim needs re-measuring"
    )
    ordinary = compute_cpm(schedule).timings[FOCUS_UID].early_finish
    all_ml = compute_cpm(schedule, duration_overrides=ml).timings[FOCUS_UID].early_finish
    assert ordinary == all_ml


@needs_java
@needs_mpp
def test_the_distribution_matches_ssis_own_export(
    schedule: Schedule, ssi_run: SSIResult, oracle: _Oracle
) -> None:
    """The headline: shape, spread and position against SSI's 2000-iteration histogram."""
    samples = _weighted_dates(schedule, ssi_run)
    assert len(samples) == ITERATIONS

    # position — where the deterministic date sits in the distribution (was P40 vs SSI's P5.75)
    assert oracle.percentile_at(oracle.current_finish) == pytest.approx(0.0575, abs=1e-4)
    assert ssi_run.deterministic_percentile == pytest.approx(0.0575, abs=0.03)

    # spread — occurrence-weighted sigma in calendar days (was 125.5 vs SSI's 64.74)
    oracle_sigma = st.pstdev([d.toordinal() for d in oracle.samples])
    assert oracle_sigma == pytest.approx(64.744, abs=0.01)
    assert st.pstdev([d.toordinal() for d in samples]) == pytest.approx(oracle_sigma, rel=0.10)

    # centre — occurrence-weighted mean offset from the deterministic date (SSI: +111.45 d)
    oracle_mean = st.fmean(oracle.offset(d) for d in oracle.samples)
    assert oracle_mean == pytest.approx(111.45, abs=0.01)
    assert st.fmean(oracle.offset(d) for d in samples) == pytest.approx(oracle_mean, abs=10.0)

    # the reported percentile dates, each against SSI's own quantile
    percentiles = ((0.10, "p10_date"), (0.50, "p50_date"), (0.80, "p80_date"), (0.90, "p90_date"))
    for pct, attr in percentiles:
        expected = oracle.offset(oracle.quantile(pct))
        actual = oracle.offset(dt.date.fromisoformat(getattr(ssi_run, attr)))
        assert abs(actual - expected) <= 10, f"P{pct:.0%}: {actual:+d} d vs SSI {expected:+d} d"


@needs_java
@needs_mpp
def test_the_summary_cells_are_not_the_parity_target(oracle: _Oracle) -> None:
    """Guard the coincidence trap: SSI's Mean/StdDev cells drop the occurrence weights.

    Pinned so nobody "improves parity" by matching 107.82 — that figure is an artifact of SSI's
    own export, and the tool's working-day sigma sits misleadingly close to it.
    """
    with zipfile.ZipFile(_oracle_workbook()) as zf:
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    cells = {
        c.get("r"): (c.find(f"{_M}v").text or "")
        for row in sheet.iter(f"{_M}row")
        for c in row.findall(f"{_M}c")
        if c.find(f"{_M}v") is not None
    }
    # Excel serials, the basis the workbook's own cells are written in
    distinct = [(d - _EXCEL_EPOCH).days for d, _ in oracle.rows]
    assert len(distinct) == 245
    # the exported cells reproduce as UNWEIGHTED statistics over the distinct dates
    assert float(cells["B7"]) == pytest.approx(st.pstdev(distinct), abs=1e-6)
    assert int(float(cells["B6"])) == int(st.fmean(distinct))
    # ... and are therefore 1.66x the real, occurrence-weighted spread
    weighted = st.pstdev([d.toordinal() for d in oracle.samples])
    assert float(cells["B7"]) / weighted == pytest.approx(1.665, abs=0.01)
