"""Guards on the byte weight and the bounds of the session cache tiers (ADR-0292).

ADR-0281 deferred "instrument-then-byte-budget the cpms/summaries/dash_cores tiers". Measuring them
(2,126-task fixture) split the answer in two, so the guards do too:

* ``dash_cores`` (2.8 KiB/entry) and ``dash_cards`` (20.1 KiB/entry) are genuinely trivial and need
  no bound — :func:`test_the_light_cache_tiers_stay_light` is what keeps that true, failing if a
  per-activity payload ever lands in one (the way ADR-0288 found the trend payload doing).
* ``analyses`` (~7.2 MiB/entry) and ``cpms`` (~641 KiB/entry) are heavy and must be COUNT-bounded;
  the bound, and that it actually evicts, are asserted rather than their weights.

MEASUREMENT NOTE — sizing these is easy to get wrong, twice. Every tier stores ``(sch, value)``
where ``sch`` REFERENCES a Schedule already held in ``SessionState.schedules``, so a per-tier
``seen`` set counts that Schedule repeatedly (~900 KiB/entry for ``dash_cores`` — ~380x too high).
But charging the tiers in sequence through ONE shared set is also misleading: ``cpms`` then reads as
0.1 KiB/entry purely because ``analyses`` was charged first and shares its objects. Its STANDALONE
cost is 641 KiB, which is the number that matters once ``analyses`` evicts. This file charges
``schedules`` first and then each light tier, and asserts the heavy tiers' BOUNDS rather than their
weights.
"""

from __future__ import annotations

import gzip
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: STANDALONE KiB-per-entry ceilings (~5x measured, so ordinary drift never flakes but a
#: per-activity payload landing in a tier does fail). Measured 2026-07-24, 2,126-task fixture:
#: dash_cores 2.8 · dash_cards 20.1 KiB/entry. ``cpms`` is NOT here — at ~641 KiB/entry it is
#: heavy by nature (it retains the scoped Schedule + CPMResult), which is exactly why ADR-0292
#: gave it an LRU bound instead of a weight ceiling.
_CEILINGS_KIB = {"dash_cores": 16.0, "dash_cards": 96.0}


def _charge(obj: object, seen: set[int]) -> int:
    """Transitive size of ``obj``, counting each object at most once across ALL calls sharing
    ``seen`` — so an object already charged to an earlier tier is free here."""
    oid = id(obj)
    if oid in seen:
        return 0
    seen.add(oid)
    size = sys.getsizeof(obj, 0)
    if isinstance(obj, dict):
        for k, v in obj.items():
            size += _charge(k, seen) + _charge(v, seen)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for item in obj:
            size += _charge(item, seen)
    elif hasattr(obj, "__dict__"):
        size += _charge(vars(obj), seen)
    return size


@pytest.fixture(scope="module")
def big() -> Schedule:
    xml = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(xml.decode(), source_file="Large_Test_File.mspdi.xml")


def test_the_light_cache_tiers_stay_light(big: Schedule) -> None:
    """dash_cores / dash_cards must stay KiB-per-entry — that is why they need no LRU bound."""
    n = 6
    st = SessionState()
    for i in range(n):
        st.schedules[f"v{i}"] = big.model_copy(update={"source_file": f"L{i}.xml"})
    client = TestClient(create_app(st))
    client.get("/api/dashboard")  # fills cpms + dash_cores + dash_cards

    seen: set[int] = set()
    _charge(st.schedules, seen)  # the loaded schedules are held regardless — charge them FIRST
    for name, ceiling in _CEILINGS_KIB.items():
        tier = getattr(st, name)
        entries = len(tier)
        assert entries == n, f"{name} should hold one entry per version, got {entries}"
        per_entry_kib = _charge(tier, seen) / entries / 1024
        assert per_entry_kib < ceiling, (
            f"{name} grew to {per_entry_kib:.1f} KiB/entry (ceiling {ceiling}). A per-activity "
            "payload has probably landed in this tier — either trim it (see ADR-0288) or revisit "
            "ADR-0292's decision that these tiers need no byte budget."
        )


def test_the_heavy_tiers_are_both_bounded(big: Schedule) -> None:
    """The two heavy tiers must BOTH be count-bounded (ADR-0292).

    ``analyses`` (~7.2 MiB/entry) was always capped. ``cpms`` (~641 KiB/entry) was a plain dict:
    while a key is resident in ``analyses`` the two share their objects, so ``cpms`` looked free —
    but after an analysis eviction the ``cpms`` entry kept the scoped Schedule + CPMResult alive by
    itself, so the analysis cap did not actually bound session memory. Both are now LRU-bounded.
    """
    from schedule_forensics.web.app import (
        _ANALYSIS_CACHE_MAX,
        _CPM_CACHE_MAX,
        _LRUCache,
    )
    from schedule_forensics.web.app import (
        SessionState as _S,
    )

    assert 8 <= _ANALYSIS_CACHE_MAX <= 64, (
        "the dominant memory consumer must stay deliberately capped"
    )
    assert _CPM_CACHE_MAX >= _ANALYSIS_CACHE_MAX, "the lighter tier should retain at least as many"
    st = _S()
    assert isinstance(st.cpms, _LRUCache), "cpms must be LRU-bounded, not a plain dict"


def test_the_cpm_tier_actually_evicts_past_its_cap(big: Schedule) -> None:
    """A bound that never evicts is not a bound — drive past the cap and check it holds."""
    from schedule_forensics.web.app import _CPM_CACHE_MAX

    st = SessionState()
    tiny = big.model_copy(update={"tasks": big.tasks[:2], "relationships": ()})
    for i in range(_CPM_CACHE_MAX + 5):
        st.cpm_scoped_for(f"k{i}", tiny.model_copy(update={"source_file": f"k{i}.xml"}))
    assert len(st.cpms) <= _CPM_CACHE_MAX, (
        f"cpms grew to {len(st.cpms)} past its {_CPM_CACHE_MAX} cap"
    )
