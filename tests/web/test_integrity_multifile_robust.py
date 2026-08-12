"""Schedule Integrity must not 500 with many files, and offers a two-file picker (ADR-0164).

The operator loaded ~20 schedule files, opened Schedule Integrity, and got an Internal Server
Error; even far fewer files failed, while exactly two worked. Two root causes were reproduced:
(1) ``change_effects`` direct-indexed ``base_cpm.timings[target]`` and KeyError'd when the target
UID was a summary/unscheduled activity (e.g. the project-summary UID 0); (2) reverting a single
change could reintroduce a logic cycle, so ``compute_cpm`` raised ``CPMError`` — unhandled — and
500'd the whole page. Both are now guarded, and the page compares ONE chosen pair (Baseline A vs
Comparison B) instead of sweeping every consecutive pair.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.change_effects import compute_change_effects
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"


def _client_with(n: int) -> TestClient:
    xml_a = gzip.decompress((GOLDEN / "Hard_File.mspdi.xml.gz").read_bytes())
    xml_b = gzip.decompress((GOLDEN / "Hard_File_updated.mspdi.xml.gz").read_bytes())
    c = TestClient(create_app(SessionState()), raise_server_exceptions=True)
    for i in range(n):
        xml = xml_a if i % 2 == 0 else xml_b
        # a trailing per-copy XML comment keeps every upload byte-UNIQUE: identical bytes would
        # (correctly, ADR-0259) collapse to one loaded file, and this fixture needs n real files
        xml = xml + f"\n<!-- copy {i} -->".encode()
        c.post("/upload", files={"files": (f"v{i}.mpp.xml", xml, "text/xml")})
    return c


# ── engine: never raise on the two reproduced failure modes ──────────────────────────────


def _cyclic_pair() -> tuple[Schedule, Schedule]:
    cal = Calendar(name="Std")
    fs = RelationshipType.FS
    tasks = tuple(
        Task(unique_id=u, name=n, duration_minutes=480) for u, n in ((1, "A"), (2, "B"), (3, "C"))
    )
    prior = Schedule(
        name="p",
        source_file="p.mpp",
        project_start=dt.datetime(2026, 1, 1),
        calendar=cal,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=fs),
            Relationship(predecessor_id=2, successor_id=3, type=fs),
        ),
    )
    current = Schedule(
        name="c",
        source_file="c.mpp",
        project_start=dt.datetime(2026, 1, 1),
        calendar=cal,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=2, successor_id=3, type=fs),
            Relationship(predecessor_id=3, successor_id=1, type=fs),
        ),
    )
    return prior, current


def test_change_effects_skips_a_cyclic_revert_instead_of_raising() -> None:
    prior, current = _cyclic_pair()
    ccpm = compute_cpm(current)
    report = compute_change_effects(prior, current, ccpm, target_uid=3)  # must NOT raise
    assert report is not None
    # restoring A->B closes A->B->C->A: unmeasurable, so it is skipped and disclosed
    assert report.skipped_unsolvable == 1
    assert all("188" not in e.label for e in report.per_change)  # (sanity: synthetic labels)


def test_change_effects_discloses_a_summary_target_instead_of_none() -> None:
    xml_a = gzip.decompress((GOLDEN / "Hard_File.mspdi.xml.gz").read_bytes()).decode()
    xml_b = gzip.decompress((GOLDEN / "Hard_File_updated.mspdi.xml.gz").read_bytes()).decode()
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    a = parse_mspdi_text(xml_a, source_file="A.mpp")
    b = parse_mspdi_text(xml_b, source_file="B.mpp")
    # UID 0 is the project-summary row: in tasks_by_id but excluded from CPM timings
    assert 0 in b.tasks_by_id and 0 not in compute_cpm(b).timings
    # guarded, no KeyError — and since ADR-0369 the unresolvable target is DISCLOSED (a
    # sentinel report with target_unavailable=True and no figures), never a silent None
    # indistinguishable from "no changes detected"; /integrity renders the banner from it.
    r = compute_change_effects(a, b, target_uid=0)
    assert r is not None and r.target_unavailable is True
    assert r.per_change == () and r.aggregate_solved is False


# ── web: /integrity never 500s with >2 files and offers the two-file picker ───────────────


@pytest.mark.parametrize("n", [3, 4, 6])
def test_integrity_renders_200_with_more_than_two_files(n: int) -> None:
    page = _client_with(n).get("/integrity")
    assert page.status_code == 200
    assert "name=a" in page.text and "name=b" in page.text  # Baseline (A) / Comparison (B) picker
    assert "Baseline (A)" in page.text and "Comparison (B)" in page.text


def test_integrity_does_not_500_with_a_summary_target_set() -> None:
    # POST — /target is POST-only; the old GET was a silent 405 that never set the focus, so
    # this test exercised the no-target path for its whole life (2026-08-08 root-cause session).
    # UID 0 can't ride the form (_parse_uid: non-positive clears), so DERIVE a real summary UID
    # from the loaded file — in tasks_by_id but excluded from CPM timings, the guarded case.
    c = _client_with(4)
    st = c.app.state.session  # type: ignore[attr-defined]
    sch = next(s for _k, s in st.ordered_versions())
    summary_uid = next(t.unique_id for t in sch.tasks if t.is_summary and t.unique_id > 0)
    c.post("/target", data={"uid": str(summary_uid), "next_url": "/"})
    page = c.get("/integrity?a=0&b=3")
    assert page.status_code == 200
    # and with the target REALLY set, the summary UID renders the ADR-0369 disclosure banner
    assert "target unavailable" in page.text


def test_integrity_two_file_picker_compares_the_chosen_pair() -> None:
    c = _client_with(4)
    # POST — the old GET 405'd silently, so the +21 pin below rode the AUTO-chosen target
    # (155 happens to be the last critical task); now the pin holds with 155 explicitly set,
    # measured on the raw pair (the 2026-08-08 pair-scope fix)
    c.post("/target", data={"uid": "155", "next_url": "/"})
    # ordered oldest-first: idx0 = a Hard_File, idx3 = a Hard_File_updated -> the 188->187 case
    page = c.get("/integrity?a=0&b=3").text
    assert "change-effects" in page
    assert "188&rarr;187" in page or "188→187" in page
    # DELIBERATELY re-pinned +23 -> +21 (ADR-0322) -> +15 (ADR-0391): engine-derived
    # counterfactual whose path crosses Hard_File's off-calendar tasks AND its started work —
    # see test_change_effects_integration.py for the full adjudication (old value reproduced on
    # the pre-change engine, new value verified stable).
    assert "+15 wd" in page


def test_integrity_guards_same_file_for_a_and_b() -> None:
    assert _client_with(4).get("/integrity?a=2&b=2").status_code == 200


def test_integrity_legacy_file_param_still_resolves_a_pair() -> None:
    page = _client_with(4).get("/integrity?file=v3.mpp.xml")
    assert page.status_code == 200


def _pair_header(html: str) -> tuple[str, str]:
    import re

    m = re.search(r"<h2>(.*?)&rarr;(.*?)</h2>", html)
    assert m, "no pair header"
    return m.group(1).strip(), m.group(2).strip()


def test_integrity_out_of_range_baseline_never_reverses_the_diff() -> None:
    """Adversarial-review finding (HIGH): ?b=0 (baseline omitted) or the legacy ?file=<oldest>
    must NOT resolve baseline to -1 and silently diff the NEWEST file against the oldest (a
    chronologically reversed, wrong forensic result). The pair must always read prior -> current
    chronologically (files are oldest-first, so prior's label must not be a later 'updated' file).
    """
    # ordered oldest-first: v0,v2 = Hard_File(7/7); v1,v3 = Hard_File_updated(8/11)
    c = _client_with(4)
    for url in ("/integrity?b=0", "/integrity?file=v0.mpp.xml"):
        prior_lbl, cur_lbl = _pair_header(c.get(url).text)
        # prior must be an oldest (Hard_File) file, never the newest 'updated' one -> not reversed
        assert "updated" not in prior_lbl, f"{url}: reversed diff, prior={prior_lbl}"
        assert prior_lbl != cur_lbl


def test_change_effects_discloses_when_every_revert_is_skipped() -> None:
    """Adversarial-review finding: when all detected reverts are cyclic (skipped_unsolvable), the
    engine must still return a report (not None) so the page can disclose the skip instead of
    silently omitting the panel (Law 2)."""
    cal = Calendar(name="Std")
    fs = RelationshipType.FS
    tasks = tuple(
        Task(unique_id=u, name=n, duration_minutes=480) for u, n in ((1, "A"), (2, "B"), (3, "C"))
    )
    # current is acyclic (3->2->1); prior additionally carried 1->3 (a removed link). Restoring
    # 1->3 closes 1->3->2->1 -> the only detected revert is unmeasurable.
    prior = Schedule(
        name="p",
        source_file="p.mpp",
        project_start=dt.datetime(2026, 1, 1),
        calendar=cal,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=1, successor_id=3, type=fs),
            Relationship(predecessor_id=2, successor_id=1, type=fs),
            Relationship(predecessor_id=3, successor_id=2, type=fs),
        ),
    )
    current = Schedule(
        name="c",
        source_file="c.mpp",
        project_start=dt.datetime(2026, 1, 1),
        calendar=cal,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=2, successor_id=1, type=fs),
            Relationship(predecessor_id=3, successor_id=2, type=fs),
        ),
    )
    report = compute_change_effects(prior, current, compute_cpm(current), target_uid=1)
    assert report is not None
    assert report.per_change == ()
    assert report.skipped_unsolvable == 1


def test_ribbon_drill_export_does_not_500_on_unknown_or_bad_file() -> None:
    """Adversarial-review finding: ribbon-drill Excel export guards analysis_for -> never 500."""
    c = _client_with(3)
    assert c.get("/export/xlsx/ribbon-drill/does-not-exist?metric=critical").status_code == 404
