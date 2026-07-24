"""Lazy segment drill-down keeps /api/trend small without changing a single number (ADR-0288).

The cross-file-comparison charts (status split / activity makeup / completion performance)
partition the WHOLE schedule, so shipping their per-segment UID arrays cost ~46% of the trend
payload — for data only ever read when the operator clicks a bar. The bars now carry a segment
NAME and the server rebuilds the set on demand.

Law 2 (fidelity over speed) is the hard line here: the drill result must be **byte-identical** to
the old explicit-UID path. These pins lock both halves — the payload no longer carries the arrays,
and every segment resolves to exactly the same activities.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: the three cross-file-comparison groups whose UID arrays are no longer shipped
_TRIMMED_GROUPS = ("status_split", "makeup", "completion_perf")


@pytest.fixture(scope="module")
def big() -> Schedule:
    xml = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(xml.decode(), source_file="Large_Test_File.mspdi.xml")


def _client(big: Schedule, n: int) -> TestClient:
    st = SessionState()
    for i in range(n):
        st.schedules[f"v{i}"] = big.model_copy(update={"source_file": f"LTF_v{i}.mspdi.xml"})
    return TestClient(create_app(st))


def test_trend_payload_no_longer_ships_the_partitioning_uid_arrays(big: Schedule) -> None:
    data = _client(big, 2).get("/api/trend").json()
    for row in data["versions"]:
        for group in _TRIMMED_GROUPS:
            block = row.get(group) or {}
            leaked = [k for k in block if k.endswith("_uids")]
            assert not leaked, f"{group} still ships {leaked}"
            assert block, f"{group} lost its counts — only the UID arrays should have gone"


def test_trend_payload_growth_per_version_is_roughly_halved(big: Schedule) -> None:
    """Size pin (ADR-0249 doctrine: measure, don't hand-wave).

    Measured on this 2,126-task fixture: the payload grew **46,600 B per loaded version** before
    the trim and **25,290 B** after — the UID arrays were 46% of it. The bound is set at 32 KB so
    it fails loudly if the arrays (or an equivalent per-activity blob) creep back in, without
    flaking on ordinary payload growth.
    """
    two = len(_client(big, 2).get("/api/trend").text)
    six = len(_client(big, 6).get("/api/trend").text)
    per_version = (six - two) / 4
    assert per_version < 32_000, f"trend payload grows {per_version:.0f} B/version (was ~46,600)"


def _expected(big: Schedule) -> dict[str, list[int]]:
    ns = non_summary(big)
    return {
        "complete": [t.unique_id for t in ns if t.percent_complete >= 100.0],
        "in_progress": [t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0],
        "planned": [t.unique_id for t in ns if t.percent_complete <= 0.0],
        "milestones": [t.unique_id for t in ns if t.is_milestone],
        "normal": [t.unique_id for t in ns if not t.is_milestone],
        "summaries": [t.unique_id for t in big.tasks if t.is_summary and t.unique_id != 0],
    }


def test_every_segment_resolves_byte_identically_to_the_explicit_uid_path(big: Schedule) -> None:
    """Law 2: the drill rows must be the SAME activities, not merely a similar count."""
    c = _client(big, 2)
    for segment, uids in _expected(big).items():
        lazy = c.get(f"/api/activities/drill?file=v0&segment={segment}").json()
        explicit = c.get(
            "/api/activities/drill?file=v0&uids=" + ",".join(str(u) for u in uids)
        ).json()
        assert lazy["rows"] == explicit["rows"], segment
        assert len(lazy["rows"]) == len(uids), segment


def test_completion_performance_segments_resolve_from_the_analysis(big: Schedule) -> None:
    """ahead / on_schedule / behind come off the cached completion metrics, not a re-derivation."""
    c = _client(big, 2)
    counts = c.get("/api/trend").json()["versions"][0]["completion_perf"]
    for segment in ("ahead", "on_schedule", "behind"):
        rows = c.get(f"/api/activities/drill?file=v0&segment={segment}").json()["rows"]
        assert len(rows) == counts[segment], segment


def test_an_explicit_uid_list_still_wins_and_an_unknown_segment_is_empty(big: Schedule) -> None:
    c = _client(big, 2)
    # every other drill trigger in the tool still passes an explicit list — that path is unchanged
    uids = _expected(big)["normal"][:2]
    both = c.get(
        "/api/activities/drill?file=v0&segment=complete&uids=" + ",".join(str(u) for u in uids)
    ).json()
    assert len(both["rows"]) == 2  # the 2 explicit ids, NOT the 699 "complete" activities
    unknown = c.get("/api/activities/drill?file=v0&segment=not-a-segment").json()
    assert unknown["rows"] == []


def test_export_accepts_the_segment_too(big: Schedule) -> None:
    """The drill's Excel export resolves the same set — else the download would be empty."""
    c = _client(big, 2)
    r = c.get("/export/xlsx/activities-drill?file=v0&segment=milestones&title=Milestones")
    assert r.status_code == 200 and len(r.content) > 0


def test_client_segment_whitelist_matches_the_server_resolver() -> None:
    """trend.js only lazies keys the server can rebuild; drift would make a bar silently inert."""
    js = (
        Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static/trend.js"
    ).read_text(encoding="utf-8")
    block = js.split("var LAZY_SEGMENTS = {", 1)[1].split("};", 1)[0]
    client_segments = {
        p.split(":")[0].strip() for p in block.replace("\n", "").split(",") if ":" in p
    }
    expected = {
        "complete",
        "in_progress",
        "planned",
        "milestones",
        "normal",
        "summaries",
        "ahead",
        "on_schedule",
        "behind",
    }
    assert client_segments == expected


def test_drilldown_js_sends_the_segment_on_open_and_export() -> None:
    js = (
        Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static/drilldown.js"
    ).read_text(encoding="utf-8")
    assert "data-segment" in js  # the trigger carries it
    assert '"&segment=" + encodeURIComponent(segment || "")' in js  # the fetch sends it
    assert '"&segment=" + encodeURIComponent(state.segment || "")' in js  # so does the export
    # a lazy descriptor must not be treated as an id list
    assert "uids.segment" in js


def test_trend_payload_is_still_valid_json_with_all_counts(big: Schedule) -> None:
    """Guard the trim didn't take a count with it — the charts render from these."""
    row = json.loads(_client(big, 2).get("/api/trend").text)["versions"][0]
    assert set(row["status_split"]) == {"complete", "in_progress", "planned"}
    assert set(row["makeup"]) == {"milestones", "normal", "summaries"}
    assert set(row["completion_perf"]) == {"ahead", "on_schedule", "behind"}
