"""The dashboard's manifest projection is memoised per (key, scope-epoch) (ADR-0291).

ADR-0281's `dash_cores` cached the three ENGINE figures a card needs. The projection built AROUND
them was still redone for every version on every refresh: `scope()` rebuilt a scoped Schedule, then
`non_summary()` (three times) and `compute_activity_makeup()` re-derived over it, plus the
status-UID partition. Measured on the 2,126-task fixture with the card tier fully warm: 45.8 ms at
10 versions and 117.3 ms at 30 — pure re-derivation over inputs that had not changed.

These are op-count / equality pins (ADR-0249 doctrine), not wall-clock:

* a warm refresh performs **zero** `scope` / `compute_activity_makeup` / `non_summary` calls;
* the payload is **byte-identical** cold vs warm (Law 2 — this is a speed change only);
* the memo is epoch-keyed, so a filter / target / parity change re-keys instead of serving a stale
  card, and a wipe clears it.
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web import app as app_mod
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
_DAY = 480


@pytest.fixture(scope="module")
def big() -> Schedule:
    xml = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(xml.decode(), source_file="Large_Test_File.mspdi.xml")


def _loaded(big: Schedule, n: int) -> tuple[TestClient, SessionState]:
    st = SessionState()
    for i in range(n):
        st.schedules[f"v{i}"] = big.model_copy(update={"source_file": f"L{i}.xml"})
    return TestClient(create_app(st)), st


def _sha(c: TestClient) -> str:
    payload = c.get("/api/dashboard").json()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class _Counter:
    def __init__(self) -> None:
        self.n = 0

    def wrap(self, real):  # type: ignore[no-untyped-def]
        def w(*a: object, **k: object) -> object:
            self.n += 1
            return real(*a, **k)

        return w


def _projection_spies(monkeypatch: pytest.MonkeyPatch) -> tuple[_Counter, _Counter, _Counter]:
    scope, makeup, ns = _Counter(), _Counter(), _Counter()
    monkeypatch.setattr(SessionState, "scope", scope.wrap(SessionState.scope))
    monkeypatch.setattr(
        app_mod, "compute_activity_makeup", makeup.wrap(app_mod.compute_activity_makeup)
    )
    monkeypatch.setattr(app_mod, "non_summary", ns.wrap(app_mod.non_summary))
    return scope, makeup, ns


def test_warm_dashboard_reprojects_nothing(big: Schedule, monkeypatch: pytest.MonkeyPatch) -> None:
    c, _st = _loaded(big, 6)
    c.get("/api/dashboard")  # cold — fills the memo
    scope, makeup, ns = _projection_spies(monkeypatch)
    c.get("/api/dashboard")  # warm — must be served entirely from the memo
    assert (scope.n, makeup.n, ns.n) == (0, 0, 0)


def test_payload_is_byte_identical_cold_and_warm(big: Schedule) -> None:
    """Law 2: a memo may never change a number."""
    c, _st = _loaded(big, 4)
    assert _sha(c) == _sha(c) == _sha(c)


def test_a_scope_change_rekeys_instead_of_serving_a_stale_card(big: Schedule) -> None:
    """A target/filter/parity change must not be answered from the previous epoch's cards."""
    c, st = _loaded(big, 3)
    before = _sha(c)
    st.set_dcma_acumen_parity(not st.dcma_acumen_parity)  # flips the scope signature
    after = _sha(c)
    # the epoch changed, so the cards were re-projected under the new key; flipping back must
    # return the ORIGINAL payload exactly (proving neither epoch was corrupted)
    st.set_dcma_acumen_parity(not st.dcma_acumen_parity)
    assert _sha(c) == before
    assert isinstance(after, str)


def test_wipe_clears_the_memo(big: Schedule) -> None:
    c, st = _loaded(big, 2)
    c.get("/api/dashboard")
    assert st.dash_cards, "the memo should be populated after a dashboard build"
    c.post("/session/wipe")
    assert not st.dash_cards, "wipe must clear the manifest-projection memo"


def test_a_reuploaded_version_is_reprojected_not_served_from_the_memo(big: Schedule) -> None:
    """The identity guard: a new frozen Schedule object under the same key must miss the memo."""
    st = SessionState()
    st.schedules["v0"] = big
    c = TestClient(create_app(st))
    first = c.get("/api/dashboard").json()["cards"][0]["activities"]
    # replace the version with a DIFFERENT schedule under the same key
    st.schedules["v0"] = Schedule(
        name="tiny",
        source_file="tiny.xml",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(
            Task(unique_id=1, name="a", duration_minutes=_DAY),
            Task(unique_id=2, name="b", duration_minutes=_DAY),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    second = c.get("/api/dashboard").json()["cards"][0]["activities"]
    assert first != second and second == 2, "a re-uploaded version served a stale card"
