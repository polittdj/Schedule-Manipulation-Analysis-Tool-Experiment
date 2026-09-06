"""MC-05 (WP6b, ADR-0467): an SRA focus that is not a schedulable activity is refused, never
silently replaced by the project finish.

``_finish_of(result, target_uid)`` returned ``result.project_finish`` whenever the focus UID was
absent from the CPM timings — a summary task, an inactive or deleted activity, a stale UID from a
setup file — so every SSI / JCL / margin figure was the PROJECT finish under the focus's label.
The stale focus is a realistic state: the session target mirrors into the SRA focus
(ADR-0196) and a target set on one version can be a summary or absent in the version the SRA
runs on. The read now raises with the UID named; the JSON routes already turn a ``ValueError``
into a 422 with the message.

Red-first (2026-09-06): a summary focus and UID 999999 both ran and reported the project finish.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.sra import SRAConfig, compute_sra_ssi, deterministic_margin_bounds
from schedule_forensics.importers.mspdi import parse_mspdi

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture(scope="module")
def project5():  # type: ignore[no-untyped-def]
    return parse_mspdi(GOLDEN / "Project5.mspdi.xml")


def test_a_summary_focus_is_refused_by_name(project5) -> None:  # type: ignore[no-untyped-def]
    summary_uid = next(t.unique_id for t in project5.tasks if t.is_summary)
    with pytest.raises(ValueError, match=rf"focus UID {summary_uid}\b"):
        compute_sra_ssi(project5, config=SRAConfig(iterations=20, target_uid=summary_uid))


def test_an_absent_focus_is_refused_by_name(project5) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=r"focus UID 999999\b"):
        compute_sra_ssi(project5, config=SRAConfig(iterations=20, target_uid=999999))
    with pytest.raises(ValueError, match=r"focus UID 999999\b"):
        deterministic_margin_bounds(project5, 999999, frozenset())


def test_a_schedulable_focus_and_no_focus_still_run(project5) -> None:  # type: ignore[no-untyped-def]
    cpm = compute_cpm(project5)
    leaf = max(cpm.timings, key=lambda u: cpm.timings[u].early_finish)
    focused = compute_sra_ssi(project5, config=SRAConfig(iterations=20, target_uid=leaf))
    whole = compute_sra_ssi(project5, config=SRAConfig(iterations=20, target_uid=None))
    assert focused.deterministic_finish == cpm.timings[leaf].early_finish
    assert whole.deterministic_finish == cpm.project_finish
