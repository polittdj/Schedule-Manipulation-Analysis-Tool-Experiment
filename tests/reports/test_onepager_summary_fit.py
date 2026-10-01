"""The Compare slide's CHANGE SUMMARY strip fits its box in the face that paints it (ADR-0544).

Operator report (2026-10-01, with a screenshot of LODESTAR's Compare page): the summary text runs
outside the coloured boxes. Measured cause: LODESTAR sets the strip, the NEW / REMOVED / DUPLICATE
NAME tags and every delta in IBM Plex Mono — a monospace face advancing exactly 0.6 em per glyph
(measured in Chromium against the vendored WOFF2) — while the layout wrapped and sized them with
``CHAR_W`` = 0.52, Calibri's average. Every line painted 15% wider than its box.

Red first: on the pristine tree the first test below reported 4 lines over by up to 16.6 pt on a
pair shaped like the operator's lists. The mutation twin puts the 0.52 model back on the strip and
shows the SAME checker going red by name. The dense one-row lane of ADR-0524 keeps every count
whole, at a size that may now step below the 3.6-pt floor rather than cut (``SUMMARY_MIN``).
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as oc
from schedule_forensics.reports.onepager_compare import (
    AMBIGUOUS,
    CompareLayout,
    build_compare_layout,
    compare_onepager_docs,
)
from schedule_forensics.web.onepager_actions import read_list
from web.onepager_twin import twin_xlsx

#: IBM Plex Mono's advance, typed here from the Chromium measurement (never read off the module).
MONO = 0.6
#: ``.lss-badge``'s letter-spacing in ``lodestar_studio.css`` (0.4 px per glyph on the slide).
TRACK = 0.4
TODAY = dt.date(2026, 10, 1)
HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")

_LANES: dict[str, list[tuple[str, str, str]]] = {
    "GRC-MET Testing": [
        ("Facility Prep - Process Water", "11/20/26", "11/20/26"),
        ("Facility Prep - ISP Steam Ejector Systems", "11/6/26", "11/6/26"),
        ("Facility Prep - LOX Integrated System Checkout Test", "12/28/26", "12/28/26"),
        ("Facility Prep - LH2 Checkout Testing", "10/26/26", "10/26/26"),
        ("Blue Origin On-Dock", "10/16/26", "10/16/26"),
        ("MET ATP for Hot-Fire", "2/1/27", "2/1/27"),
        ("Facility Prep - MS: Follow-on IST Work Complete", "10/20/26", "10/20/26"),
        ("Exhaust Certification Test (ECT) ORR", "10/28/26", "10/28/26"),
        ("ECT Test", "12/9/26", "1/4/27"),
        ("MET Hot-Fire ORR/TRR", "2/1/27", "2/1/27"),
        ("Cold Fire / WDR", "2/8/27", "2/8/27"),
        ("Hotfire Test (Test Points #2-22)", "4/27/27", "4/27/27"),
    ],
    "Blue Origin": [
        ("BOR Demo Mission IDR #2", "9/15/26", "9/15/26"),
        ("MET On-Dock", "11/13/26", "11/13/26"),
        ("MET ORR/TRR", "1/5/27", "1/5/27"),
        ("MET Testing", "1/5/27", "4/16/27"),
        ("EOR FRR", "9/1/27", "9/1/27"),
        ("Mk2-D Launch (EOR Mission)", "9/15/27", "9/15/27"),
        ("BOTM - Uncrewed Demo Lander Launch", "3/18/28", "3/18/28"),
        ("Monthly Review", "5/5/27", "5/5/27"),  # repeats below: DUPLICATE NAME in the current list
        ("Monthly Review", "6/5/27", "6/5/27"),
    ],
    "Flight Manifests": [
        ("Artemis III", "6/15/27", "6/15/27"),
        ("Artemis IV", "3/31/28", "3/31/28"),
    ],
}


def _shift(text: str, days: int) -> str:
    return (dt.datetime.strptime(text, "%m/%d/%y") + dt.timedelta(days=days)).strftime("%m/%d/%y")


def _rows(current: bool) -> tuple[tuple[object, ...], ...]:
    """A pair shaped like the operator's August → September lists: a lane with eight slips, a
    lane with slips, a pull-in, a completion, a removal, an addition and a repeated name whose
    copies match no date, and a lane that stands still."""
    out: list[tuple[object, ...]] = [HEAD]
    for lane, items in _LANES.items():
        for i, (name, s, f) in enumerate(items):
            if (
                current
                and lane != "Flight Manifests"
                and name == "BOTM - Uncrewed Demo Lander Launch"
            ):
                continue  # removed
            if current and lane != "Flight Manifests" and name.startswith("Monthly"):
                out.append((lane, name, _shift(s, 3), _shift(f, 3), ""))  # both copies moved
            elif current and lane != "Flight Manifests" and i % 3 != 2:
                move = 21 + 5 * i if lane != "Blue Origin" or i != 3 else -9
                out.append(
                    (lane, name, _shift(s, move), _shift(f, move), "Complete" if i == 1 else "")
                )
            else:
                out.append((lane, name, s, f, ""))
        if current and lane == "Blue Origin":
            out.append(
                (lane, "BOTM - Uncrewed Demo Lander Launch (Mk2-A-U)", "3/22/28", "3/22/28", "")
            )
        out.append(())
    return tuple(out)


@pytest.fixture(scope="module")
def lay() -> CompareLayout:
    prior = read_list(twin_xlsx(_rows(False)), "August_IMS-GRC.xlsx", max_bytes=10**8)
    current = read_list(twin_xlsx(_rows(True)), "Sept_IMS-GRC.xlsx", max_bytes=10**8)
    assert not isinstance(prior, str) and not isinstance(current, str)
    doc = compare_onepager_docs(prior, current)
    assert any(r.status == AMBIGUOUS for r in doc.rows), "the pair must carry a DUPLICATE NAME tag"
    return build_compare_layout(doc, TODAY, "August IMS-GRC → Sept IMS-GRC")


def _overflows(lay: CompareLayout) -> list[tuple[str, float, str, float, float]]:
    """Every summary line wider, in a monospace face, than the box it is painted in."""
    bad = []
    for box in lay.summaries:
        avail = (box.x1 - box.x0) - 5  # the text starts 2.5 pt in and keeps 2.5 pt clear
        for line in box.lines:
            width = len(line) * box.pt * MONO
            if width > avail + 0.01:
                bad.append(
                    (lay.lanes[box.lane].name, box.pt, line, round(width, 1), round(avail, 1))
                )
    return bad


def test_every_summary_line_fits_its_box_in_the_monospace_face(lay: CompareLayout) -> None:
    """RED on the pristine tree: 4 lines over, by up to 16.6 pt (the screenshot's overflow)."""
    assert lay.summaries and all(box.lines for box in lay.summaries)
    assert _overflows(lay) == []
    # and nothing was cut to get there: the floor still holds, every count is whole
    for box, summary in zip(lay.summaries, (s for s in lay_lanes(lay)), strict=True):
        text = " ".join(box.lines)
        assert "…" not in text and box.pt >= oc.SUMMARY_FLOOR, (summary, box)


def lay_lanes(lay: CompareLayout) -> list[str]:
    return [ln.name for ln in lay.lanes]


def test_mutation_the_calibri_model_on_the_strip_is_caught_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUTATION: the 0.52 model put back on the strip — the SAME checker reports the lines that
    overflow, naming the lane and the line."""
    monkeypatch.setattr(oc, "MONO_CHAR_W", 0.52)
    prior = read_list(twin_xlsx(_rows(False)), "August_IMS-GRC.xlsx", max_bytes=10**8)
    current = read_list(twin_xlsx(_rows(True)), "Sept_IMS-GRC.xlsx", max_bytes=10**8)
    assert not isinstance(prior, str) and not isinstance(current, str)
    broken = build_compare_layout(compare_onepager_docs(prior, current), TODAY, "t")
    bad = _overflows(broken)
    assert bad, "the mutant was not caught"
    assert any(name == "GRC-MET Testing" for name, *_rest in bad), bad


def test_the_tags_and_deltas_are_sized_for_the_monospace_face(lay: CompareLayout) -> None:
    """A NEW / REMOVED / DUPLICATE NAME pill holds its word set in the monospace face with its
    tracking; a label's reserved width covers its delta in that face too."""
    tagged = [p for p in lay.items if p.badge]
    assert {p.badge for p in tagged} >= {"NEW", "REMOVED", "DUPLICATE NAME"}
    for p in tagged:
        need = len(p.badge) * (lay.label_pt * MONO + TRACK) + 2 * oc.BADGE_PAD
        assert p.badge_w >= need - 0.01, (p.badge, p.badge_w, need)
    with_delta = [p for p in lay.items if p.delta]
    assert with_delta
    for p in with_delta:
        need = len(p.label) * lay.label_pt * op.CHAR_W + len(f" {p.delta}") * lay.label_pt * MONO
        assert p.label_w >= need - 0.01, (p.label, p.delta, p.label_w, need)


def test_mutation_a_tag_sized_at_the_calibri_width_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(oc, "MONO_CHAR_W", 0.52)
    prior = read_list(twin_xlsx(_rows(False)), "p.xlsx", max_bytes=10**8)
    current = read_list(twin_xlsx(_rows(True)), "c.xlsx", max_bytes=10**8)
    assert not isinstance(prior, str) and not isinstance(current, str)
    broken = build_compare_layout(compare_onepager_docs(prior, current), TODAY, "t")
    dup = next(p for p in broken.items if p.badge == "DUPLICATE NAME")
    need = len(dup.badge) * (broken.label_pt * MONO + TRACK) + 2 * oc.BADGE_PAD
    assert dup.badge_w < need, "the mutant was not caught"


def test_a_strip_steps_below_the_floor_only_to_stay_whole() -> None:
    """ADR-0524's dense one-row lane: six moves in a lane packed into ONE row on a 56-row slide.
    In the monospace face the whole strip no longer fits two 3.6-pt lines; it fits at 3.5 pt —
    and that beats an ellipsis over the worst slip. The size never passes ``SUMMARY_MIN``."""
    moving_prior = [
        ("L", f"Item {i}", f"{1 + 2 * i}/1/2027", f"{1 + 2 * i}/1/2027", "") for i in range(5)
    ]
    moving_current = [
        ("L", "Item 0", "1/1/2027", "1/1/2027", "Done"),
        ("L", "Item 1", "3/9/2027", "3/9/2027", ""),
        ("L", "Item 2", "4/25/2027", "4/25/2027", ""),
        ("L", "Item 3", "7/1/2027", "7/1/2027", "Complete"),
        ("L", "Fresh", "11/15/2027", "11/15/2027", ""),
    ]
    filler = [
        (f"Filler {lane}", f"Long activity {lane}-{k}", "1/1/2027", "3/1/2027", "")
        for lane in range(7)
        for k in range(8)
    ]
    prior = read_list(twin_xlsx((HEAD, *moving_prior, *filler)), "p.xlsx", max_bytes=10**8)
    current = read_list(twin_xlsx((HEAD, *moving_current, *filler)), "c.xlsx", max_bytes=10**8)
    assert not isinstance(prior, str) and not isinstance(current, str)
    lay = build_compare_layout(compare_onepager_docs(prior, current), dt.date(2027, 3, 1), "t")
    box = next(b for b in lay.summaries if lay.lanes[b.lane].name == "L")
    assert lay.lanes[box.lane].rows == 1 and lay.row_h < oc.FLOORS[0][0]
    text = " ".join(box.lines)
    for part in ("slipped 1", "pulled in 1", "unchanged 2", "new 1", "removed 1", "complete 2"):
        assert part in text, (part, box.lines, box.pt)
    assert "…" not in text and oc.SUMMARY_MIN <= box.pt < oc.SUMMARY_FLOOR, box.pt
    assert _overflows(lay) == []
    assert len(box.lines) * box.pt * 1.25 <= (box.y1 - box.y0) - 1.5 + 0.01
