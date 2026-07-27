"""The dashboard no longer ships the status-segment UID arrays (ADR-0296).

ADR-0291 named this residual when it memoised the card projection: every card carried a
``status_mix_uids`` map — three UID arrays partitioning the whole schedule — read only when the
operator clicks a status-bar segment. Measured on the 2,126-task golden fixture that was **87.6%
of the entire /api/dashboard payload** (9,698 B per loaded version; 1,195 B without the arrays).

The bar now marks each segment with its NAME (the ADR-0288 lazy-descriptor pattern) and the drill
rebuilds the set on demand — against THIS card's own file, which is exactly what ADR-0295's
manifest-wide resolver and its forward guard made safe to rely on.

Law 2 pins: the drill rows must be **byte-identical** to the old explicit-UID path, and the counts
the charts render from must survive untouched.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static"


@pytest.fixture(scope="module")
def big() -> Schedule:
    xml = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(xml.decode(), source_file="Large_Test_File.mspdi.xml")


def _client(big: Schedule, n: int) -> TestClient:
    st = SessionState()
    for i in range(n):
        st.schedules[f"v{i}"] = big.model_copy(update={"source_file": f"L{i}.xml"})
    return TestClient(create_app(st))


def test_cards_no_longer_ship_uid_arrays_but_keep_every_count(big: Schedule) -> None:
    for card in _client(big, 2).get("/api/dashboard").json()["cards"]:
        leaked = [k for k in card if k.endswith("_uids")]
        assert not leaked, f"card {card['key']} still ships {leaked}"
        assert set(card["status_mix"]) == {"complete", "in_progress", "planned"}


def test_payload_growth_per_version_shrank_8x(big: Schedule) -> None:
    """Size pin (ADR-0249 doctrine: measure, don't hand-wave).

    Measured on this 2,126-task fixture: **9,698 B per loaded version** before the trim, **1,195 B**
    after — the arrays were 87.6% of the payload. The bound is 4,000 B so it fails loudly if the
    arrays (or an equivalent per-activity blob) creep back in, without flaking on ordinary growth.
    """
    two = len(_client(big, 2).get("/api/dashboard").text)
    six = len(_client(big, 6).get("/api/dashboard").text)
    per_version = (six - two) / 4
    assert per_version < 4_000, f"dashboard grows {per_version:.0f} B/version (was ~9,698)"


def test_every_segment_drill_is_byte_identical_to_the_explicit_uid_path(big: Schedule) -> None:
    """Law 2: the same activities, not merely a similar count."""
    c = _client(big, 2)
    ns = non_summary(big)
    expected = {
        "complete": [t.unique_id for t in ns if t.percent_complete >= 100.0],
        "in_progress": [t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0],
        "planned": [t.unique_id for t in ns if t.percent_complete <= 0.0],
    }
    card = c.get("/api/dashboard").json()["cards"][0]
    for segment, uids in expected.items():
        lazy = c.get(f"/api/activities/drill?file=v0&segment={segment}").json()
        explicit = c.get(
            "/api/activities/drill?file=v0&uids=" + ",".join(str(u) for u in uids)
        ).json()
        assert lazy["rows"] == explicit["rows"], segment
        assert len(lazy["rows"]) == card["status_mix"][segment], segment


def test_dashboard_js_marks_segments_lazily() -> None:
    """The client sends the segment NAME; nothing reads the retired array key any more."""
    js = (STATIC / "dashboard.js").read_text(encoding="utf-8")
    assert "SFDrill.mark(seg, { segment: s[0] }" in js
    assert "status_mix_uids" not in js
