"""Free float is bounded by the total float, and a successor's leveling delay is not slack (R-74).

**What the audit row claimed, and what the corpus says.** R-74 reported that MS Project's stored
``FreeSlack`` "never exceeds its ``TotalSlack`` (0 of the 3,315 activities across the 44 files that
store both)" while the engine's free float exceeded its total on 1,870 incomplete activities. The
first half is a statement about a FILTER, not about MS Project: every one of the 1,230 corpus rows
whose stored ``TotalSlack`` is NEGATIVE has its ``FreeSlack`` element ABSENT, and the MPXJ MSPDI
writer omits a zero duration (ADR-0490 / R-62 proved that for ``TotalSlack`` from the same writer
rule). Read with that rule, MS Project itself reads free (0) above total (negative) on **1,227**
rows. So the engine's 1,867 (re-measured; the row said 1,870) is TWO classes:

* **1,229** whose total float is NEGATIVE, where free floors at 0 — the class MS Project itself
  exhibits, and on 577 of them the engine's total equals the stored total exactly. NOT a defect,
  and deliberately left alone.
* **638** whose total is >= 0. Of the 622 carrying a stored ``FreeSlack`` the engine exceeded it on
  **622 of 622**, and the stored ``FreeSlack`` equals the stored ``TotalSlack`` on **610** of them.
  That is the defect, and it is what this module pins.

**Two mechanisms, measured separately.**

1. *The bound.* MS Project's Free Slack is never above its Total Slack and is stored EQUAL to it on
   1,116 of the 3,315 — including **116 of 116** activities that have no successor at all, which is
   the independent reading that fixes the rule. The bound's floor matters: clamping to a negative
   total MANUFACTURES 1,239 negative free floats, and the corpus stores none.
2. *The leveling delay.* The forward pass ADDS a successor's stored leveling delay to its early
   start and the backward pass SUBTRACTS it from the need it presents (``ls_need``); the free-float
   calculation did neither, so the delay was counted as slack the predecessor owns. This is
   independent of the bound and is worth 38 more exact figures ON TOP of it.

**Refuted before the first edit (QC-3).** The row prescribed two remedies and BOTH fail as written:
measuring to the successors' LATE starts takes the exact count 2,471 -> **963**, and "bounded by the
total" without the floor manufactures the 1,239 negatives above. The leveling delay, which the row
does not name, is a third mechanism; alone it is worth only +38, so it is not the row's headline
either. Subtracting the delay on FINISH-type anchors as well overshoots: +2 exact for +7 low.

**Measured over the 44-file corpus** (15 committed goldens + 29 fresh ``.mpp`` conversions, 22,105
scheduled activities), free float against the stored ``FreeSlack`` of the 3,315: exact
**2,471 -> 3,004**, high **772 -> 198**, and the total float is untouched (10,610 of 12,680 exact,
before and after). Isolated to the 2,926 rows whose total ALREADY matched the stored TotalSlack
exactly -- so a total-float residual cannot flatter the result -- exact goes **79.5% -> 97.7%** and
the low count does NOT move (14 -> 14): every new low sits on a row whose own total float is still
inexact, which is the bound doing its job, not a free-float regression.

Red first: every assertion below was observed to fail on the pristine engine, by name, except the
two marked as controls.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
_NS = "{http://schemas.microsoft.com/project}"


def _text(rel: str) -> str:
    path = GOLDEN / rel
    raw = path.read_bytes()
    return gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")


def _load(rel: str) -> tuple[Schedule, CPMResult]:
    sch = parse_mspdi_text(_text(rel))
    return sch, compute_cpm(sch)


def _stored(rel: str) -> dict[int, tuple[int | None, int | None]]:
    """UID -> (stored TotalSlack, stored FreeSlack) in working minutes, ``None`` when the element
    is absent. Read from the golden's own XML: the model carries the total but not the free."""
    root = ET.fromstring(_text(rel))
    out: dict[int, tuple[int | None, int | None]] = {}
    for el in root.iter(f"{_NS}Task"):
        uid = el.findtext(f"{_NS}UID")
        if uid is None:
            continue
        ts, fs = el.findtext(f"{_NS}TotalSlack"), el.findtext(f"{_NS}FreeSlack")
        out[int(uid)] = (
            None if ts is None else round(int(ts) / 10),
            None if fs is None else round(int(fs) / 10),
        )
    return out


#: every committed MSPDI golden, gzipped ones included -- a plain ``*.xml`` glob cannot see them
_GOLDENS = tuple(
    sorted(
        p.relative_to(GOLDEN).as_posix()
        for p in list(GOLDEN.rglob("*.xml")) + list(GOLDEN.rglob("*.xml.gz"))
        if "schemas.microsoft.com/project"
        in (
            gzip.decompress(p.read_bytes())[:400] if p.suffix == ".gz" else p.read_bytes()[:400]
        ).decode("utf-8", "replace")
    )
)


def test_the_golden_pool_is_the_whole_committed_mspdi_set() -> None:
    """A control on this module's own population: the gzipped goldens are eleven of the fifteen,
    and a census that could not see them would under-report by construction."""
    assert len(_GOLDENS) == 15, _GOLDENS
    assert sum(1 for g in _GOLDENS if g.endswith(".gz")) == 11, _GOLDENS


# --- the row's own named witness ---------------------------------------------------------------


def test_uid_408_reads_the_stored_free_slack_not_the_gap_to_its_successor() -> None:
    """``Hard_File_updated3`` UID 408 ("Deploy technology infrastructure") stores TotalSlack
    24,000 tenths and FreeSlack 24,000 tenths -- 2,400 working minutes, the two EQUAL. The gap to
    its one FS successor's early start is 15,360 minutes, and the pristine engine reported that as
    free float: six times the slack MS Project says the activity has. The ``_updated2`` snapshot
    stores the pair equal at 21,120 against a gap of 21,600.

    R-74's own text names the logic-reestablished conversion, where the same UID reads 18,960 for
    a stored 16,740; that file is not a committed golden (it converts from ``.mpp`` and needs
    Java), so the two committed snapshots carry the pin and the conversion is recorded in the ADR.
    """
    for rel, expected in (
        ("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz", 2400),
        ("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz", 21120),
    ):
        stored_total, stored_free = _stored(rel)[408]
        assert (stored_total, stored_free) == (expected, expected), rel
        tm = _load(rel)[1].timing(408)
        assert tm.total_float == expected, rel
        assert tm.free_float == expected, (rel, tm.free_float)


# --- mechanism 2, isolated from the bound ------------------------------------------------------


def test_a_successors_leveling_delay_is_not_slack_the_predecessor_owns() -> None:
    """``Hard_File`` UID 402 is the witness that isolates the delay from the bound: its total
    float is 9,600 minutes, so the bound cannot be what moves it, and its one FS successor 403
    carries a 36,420-minute leveling delay. The pristine engine measured free float to 403's
    delayed early start and read **8,520** minutes; MS Project's stored FreeSlack is absent, i.e.
    zero by its writer's dropped-zero rule (the file carries the element elsewhere, on UID 408).

    UID 14 names the mechanism exactly: its successor 141 carries a 600-minute (ten elapsed hours)
    delay, and ``_succ_ls_wall``'s own comment has recorded that delay's role in the BACKWARD pass
    since ADR-0474 -- "UID 14 LF 11:00 = UID 141 LS 21:00 minus its 10 h". The free-float side was
    never done, so 14 read 600 minutes of free float against a total of 0.
    """
    sch, res = _load("fuse_hardfile/Hard_File.mspdi.xml.gz")
    stored = _stored("fuse_hardfile/Hard_File.mspdi.xml.gz")
    by = sch.tasks_by_id
    # the bound is inactive here: the total is far above the gap the pristine engine reported
    assert res.timing(402).total_float == 9600 == stored[402][0]
    assert stored[402][1] is None  # a dropped zero -- the file carries FreeSlack on UID 408
    assert stored[408][1] is not None
    (succ_402,) = sch.successors_of(402)
    assert succ_402.successor_id == 403
    assert by[403].leveling_delay_minutes == 36420
    assert res.timing(402).free_float == 0, res.timing(402).free_float
    # UID 14 -> 141, the ten elapsed hours _succ_ls_wall already subtracts on the backward side
    (succ_14,) = sch.successors_of(14)
    assert succ_14.successor_id == 141
    assert by[141].leveling_delay_minutes == 600
    assert res.timing(14).total_float == 0
    assert res.timing(14).free_float == 0, res.timing(14).free_float


# --- the floor: the negative-total class is deliberately untouched ------------------------------


def test_a_negative_total_does_not_drag_the_free_float_negative() -> None:
    """UID 155 ("Customer Service Program Development") is behind its constraint on two snapshots
    and MS Project stores the negative TotalSlack while OMITTING FreeSlack -- its writer drops a
    zero rather than storing a negative free slack, and the corpus stores no negative FreeSlack
    anywhere. So the bound is floored at zero: a clamp straight to the total would report -480 and
    -12,480 minutes of free float here, two of the 1,239 negatives that form measured across the
    corpus. This assertion is what goes red if the floor is removed."""
    for rel, total in (
        ("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz", -480),
        ("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz", -12480),
    ):
        stored_total, stored_free = _stored(rel)[155]
        assert (stored_total, stored_free) == (total, None), rel
        tm = _load(rel)[1].timing(155)
        assert tm.total_float == total, rel
        assert tm.free_float == 0, (rel, tm.free_float)


# --- the invariant, over every committed golden ------------------------------------------------


def test_free_float_exceeds_the_total_on_exactly_the_negative_total_rows() -> None:
    """The shape of the fix, stated as a census over all fifteen goldens: free float is above the
    total on 427 rows and 427 rows have a negative total -- the SAME rows. The pristine engine had
    842 against the same 427, the 415 difference being the defect. Every row is checked
    individually, so a coincidence of counts cannot pass this."""
    above = negative = 0
    for rel in _GOLDENS:
        for tm in _load(rel)[1].timings.values():
            if tm.total_float < 0:
                negative += 1
            if tm.free_float > tm.total_float:
                above += 1
                assert tm.total_float < 0, (rel, tm.unique_id, tm.free_float, tm.total_float)
            else:
                assert tm.free_float <= max(tm.total_float, 0), (rel, tm.unique_id)
    assert (above, negative) == (427, 427)


def test_the_goldens_reproduce_the_stored_free_slack_at_the_pinned_rate() -> None:
    """The oracle census over the fifteen goldens, against MS Project's own stored FreeSlack:
    1,034 exact of 1,142, 69 high, 39 low. Pristine: 839 / 276 / 27. The 69 are the residual, not
    a claim of completeness -- across the whole 44-file corpus 198 remain high, of which 144 sit on
    rows whose TOTAL float is itself still inexact (the Large Test File crew-calendar chains) and
    54 are minute-scale residuals of the same family, all FS, on 15 distinct UIDs, deltas of 2, 60
    or 120 minutes. None is a free-float RULE error and none is silently claimed fixed."""
    pop = exact = high = low = 0
    for rel in _GOLDENS:
        res = _load(rel)[1]
        for uid, (_, stored_free) in _stored(rel).items():
            if stored_free is None or uid not in res.timings:
                continue
            pop += 1
            got = res.timing(uid).free_float
            exact += got == stored_free
            high += got > stored_free
            low += got < stored_free
    assert (pop, exact, high, low) == (1142, 1075, 40, 27)


def test_the_total_float_is_untouched_by_this_change() -> None:
    """A control: ADR-0522's bound reads the total, it never writes it — that is still true.

    The figure MOVED on 2026-09-22 (R-77, ADR-0523) because the AXIS moved, not because the bound
    began writing: 3,897 -> 4,098 of 4,559 over the goldens, 10,610 -> 11,041 of 12,680 across the
    44-file corpus, every one of them TOWARD MS Project's own stored TotalSlack. A stored instant
    read in the working minutes of the calendar's own segments lands its pin where the reference
    tool put it; the contiguous clamp had been billing the lunch hour as work."""
    pop = exact = 0
    for rel in _GOLDENS:
        res = _load(rel)[1]
        for uid, (stored_total, _) in _stored(rel).items():
            if stored_total is None or uid not in res.timings:
                continue
            pop += 1
            exact += res.timing(uid).total_float == stored_total
    assert (pop, exact) == (4559, 4098)
