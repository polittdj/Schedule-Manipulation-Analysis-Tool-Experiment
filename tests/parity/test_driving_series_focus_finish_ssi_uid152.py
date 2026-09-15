"""The DRIVING-PATH SERIES' focus finish is SSI's own Current Finish on the operator's IMS (OR-20).

Oracle: the operator's SSI Directional Path Tool exports for focus UID 152 —
``00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx``
(Finish serial 46297.5 = 2026-10-02 12:00 on the focus row; the same instant every one of the 76
path members' Start/Finish reproduces from the golden's stored dates, measured 76 of 76) and the
leveled export the ``ssi_uid152_leveled`` golden was pinned from (2026-10-09 15:13). SSI runs
inside MS Project, so its Current Finish IS the file's stored Finish — the input identity
``test_sra_ssi_oracle_uid152_v2`` already relies on — and it is the date an analyst comparing the
tool's answer to MS Project will hold it to.

The network's computed finish on both versions is 2028-09-28, two years past the focus: a series
that printed the network finish as the focus's finish (the defect the operator's model alleged of
itself) or the engine's logic-only finish where it disagrees with the file, is red here by name.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

import pytest

from schedule_forensics.ai.driving_facts import driving_path_series
from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
FOCUS = 152
#: SSI's Current Finish for the focus in each export (the oracle), by golden.
SSI_FOCUS_FINISH = {
    "ssi_uid152/Large_Test_File.mspdi.xml.gz": dt.date(2026, 10, 2),
    "ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz": dt.date(2026, 10, 9),
}


def _load(rel: str) -> Schedule:
    raw = gzip.decompress((_GOLDEN / rel).read_bytes()).decode("utf-8")
    return parse_mspdi_text(raw, source_file=Path(rel).name)


@pytest.fixture(scope="module")
def series_text() -> tuple[str, dict[str, dt.date]]:
    scheds = [_load(rel) for rel in SSI_FOCUS_FINISH]
    cpms = [compute_cpm(s) for s in scheds]
    facts = driving_path_series(scheds, cpms, FOCUS)
    text = next(f.text for f in facts if f.text.startswith("DRIVING-PATH SERIES"))
    network = {
        s.source_file or s.name: offset_to_datetime(
            s.project_start, c.project_finish, s.calendar
        ).date()
        for s, c in zip(scheds, cpms, strict=True)
    }
    return text, network


def test_the_focus_finish_is_ssis_current_finish_in_every_version(
    series_text: tuple[str, dict[str, dt.date]],
) -> None:
    text, _ = series_text
    for rel, finish in SSI_FOCUS_FINISH.items():
        label = Path(rel).name
        seg = text[text.index(label) :]
        assert f"UID {FOCUS} finishes {finish.isoformat()}" in seg[:400], seg[:400]


def test_the_network_finish_is_never_printed_as_the_focus_finish(
    series_text: tuple[str, dict[str, dt.date]],
) -> None:
    """The alleged defect, refuted by name: the network finishes 2028-09-28 on both versions and
    that date must not appear in the focus series at all."""
    text, network = series_text
    assert all(f == dt.date(2028, 9, 28) for f in network.values()), network  # the precondition
    assert "2028-09-28" not in text, text
