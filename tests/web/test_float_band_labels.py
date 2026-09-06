"""JS-06 (WP6b, ADR-0467): the float histogram's band labels admit the fractional floats they
hold — on the chart, in the drill heading, and in the export's mirror table.

``bucketOf`` places ``0 < v <= 5`` in the third band, so a 0.75-day float (EVM1 UID with a
sub-day slack; the XER fixture's 0.5) sat under a label reading ``1-5`` and a 5.5-day float under
``6-10``. The bands are upper-bound-inclusive by construction; their labels now say so
(``≤ 5``, ``≤ 10`` …), the drill heading spells the open lower bound ("over 0 and up to 5 working
days"), and the server's mirror table (the drill posts the band INDEX to the export) carries the
same labels in ASCII.

Red-first (2026-09-06): the labels read ``1-5`` / ``6-10`` (with en dashes) on both sides.
"""

from __future__ import annotations

import re
from pathlib import Path

import schedule_forensics.web as web_pkg
from schedule_forensics.web.app import _FLOAT_HIST_BANDS

# resolved through the package (not the CWD) so a shadowed tree under PYTHONPATH is what is read
JS = (Path(web_pkg.__file__).parent / "static" / "histogram.js").read_text(encoding="utf-8")


def test_the_chart_labels_are_upper_bound_inclusive() -> None:
    block = JS[JS.index("var BUCKETS") : JS.index("];", JS.index("var BUCKETS"))]
    labels = re.findall(r'label: "([^"]+)"', block)
    assert labels == ["< 0", "0", "≤ 5", "≤ 10", "≤ 20", "≤ 44", "> 44"]


def test_the_drill_heading_spells_the_open_lower_bound() -> None:
    assert "and up to" in JS and "over 44 working days" in JS


def test_the_export_mirror_table_matches_by_index_and_admits_band_edge_floats() -> None:
    assert [label for label, _ in _FLOAT_HIST_BANDS] == [
        "< 0",
        "0",
        "<= 5",
        "<= 10",
        "<= 20",
        "<= 44",
        "> 44",
    ]
    for value, index in ((-0.5, 0), (0, 1), (0.75, 2), (5, 2), (5.5, 3), (44.5, 6)):
        assert [m(value) for _, m in _FLOAT_HIST_BANDS].index(True) == index, value
