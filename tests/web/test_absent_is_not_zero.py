"""ADR-0343 — the three carried falsy-zero rows, settled by RENDERING the page.

`audit/FALSY-ZERO-SWEEP-20260729.md` classified three sites UNSURE, for one stated reason: the
sweep never rendered the pages, so it could not tell whether an absent figure reached the analyst
as an em dash or as a fabricated `0`. Both surfaces were then measured (this module's fixtures are
the measurement) and both fabricated:

* `/cei`'s "Latest scored month" panel drew ``Finished 0 / Short of plan 0 / 0 planned in the
  month`` when ``cei_planned``/``cei_finished`` are ``None`` — under a *"scored month"* heading, on
  a page whose own takeaway reads *"No month could be CEI-scored"*, beside KPI cards already
  rendering "—" for those same two fields.
* `/groups`' breakdown rendered ``0%`` completion for a value carried only by summary rows, beside
  a BEI cell already rendering "—" for that same empty population.

Every expectation below is DERIVED from the engine, not transcribed: the empty-population set is
recomputed here from ``group_values``/``non_summary`` so the tests keep meaning if the fixtures
change. Each fabricating branch is paired with its true-positive twin — a fix that stops inventing
a zero must not also stop reporting a real one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.grouping import filter_schedule, group_values
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: value-then-label, the order :func:`_stat_cards` emits (reading forward from a label picks up the
#: NEXT card's value — the mis-read that made the first pass of this measurement wrong).
_CARD = re.compile(
    r"<div class=stat-card><div class=stat-value>(.*?)</div><div class=stat-label>(.*?)</div>"
)
_ROW = re.compile(
    r"<tr><td>([^<]*)</td><td class=num>(\d+)</td><td class=num>(.*?)</td>"
    r"<td class=num>(.*?)</td></tr>"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload_golden(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def _golden_schedule(name: str):  # type: ignore[no-untyped-def]
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    return parse_mspdi_text(data.decode("utf-8", "replace"), source_file=f"{name}.mspdi.xml")


def _kpi(page: str) -> dict[str, str]:
    return {label: value for value, label in _CARD.findall(page)}


# --------------------------------------------------------------------------------------------
# /cei — an unscorable month is not a month scored zero
# --------------------------------------------------------------------------------------------

_TASKS = [
    {
        "unique_id": 1,
        "name": "A",
        "duration_minutes": 2400,
        "start": "2026-01-05T08:00:00",
        "finish": "2026-01-09T17:00:00",
        "actual_finish": "2026-01-09T17:00:00",
        "percent_complete": 100.0,
    },
    {
        "unique_id": 2,
        "name": "B",
        "duration_minutes": 2400,
        "start": "2026-02-02T08:00:00",
        "finish": "2026-02-06T17:00:00",
    },
]


def _upload_undated_pair(client: TestClient) -> None:
    """Two versions, NEITHER carrying a data date.

    ``bow_wave`` sets ``cei_period``/``cei_planned``/``cei_finished`` only inside its
    ``lo <= period <= hi`` block, which is reached only when the PRIOR snapshot has a status
    month. ``order_versions`` sorts undated files after dated ones, so with no data date anywhere
    the newest snapshot's predecessor is undated too and all three fields stay ``None``. An MSPDI
    export without ``<StatusDate>`` is an ordinary file, not an exotic one.
    """
    for name in ("aaa_v1", "bbb_v2"):
        payload = {
            "name": name,
            "project_start": "2026-01-05T08:00:00",
            "tasks": _TASKS,
            "relationships": [{"predecessor_id": 1, "successor_id": 2}],
        }
        resp = client.post(
            "/upload",
            files={"files": (f"{name}.json", json.dumps(payload), "application/json")},
        )
        assert resp.status_code == 200


def test_unscorable_cei_month_renders_no_measured_zero(client: TestClient) -> None:
    _upload_undated_pair(client)
    page = client.get("/cei").text

    # the page already knew: the takeaway and every affected KPI card say so
    assert "No month could be CEI-scored" in page
    cards = _kpi(page)
    for label in ("Latest CEI", "CEI month", "Planned that month", "Finished that month"):
        assert cards[label] == "—", f"{label} = {cards[label]!r}"

    # ...and the panel below them no longer contradicts it
    assert "0 planned in the month" not in page
    assert "Latest scored month" not in page
    assert "Monthly plan vs done" in page
    assert "absent — not zero" in page
    # no stacked bar is drawn for a month that was never scored (the sibling pile bar keeps its own)
    assert page.count('class="stack-foot"') == 1


def test_the_unscored_panel_keeps_its_place_in_the_two_up_grid(client: TestClient) -> None:
    """The replacement is the same panel shell, so the sibling does not reflow into the gap."""
    _upload_undated_pair(client)
    page = client.get("/cei").text
    bars = page.split('<div class="ws-bars">', 1)[1]
    assert bars.count('<div class="panel status-stack">') == 2
    assert bars.index("Monthly plan vs done") < bars.index("Where the finishes sit")


def test_a_really_scored_month_still_reports_its_figures(client: TestClient) -> None:
    """The true-positive twin: the goldens DO score a month, and nothing about that moved."""
    _upload_golden(client, "Project2")
    _upload_golden(client, "Project5")
    page = client.get("/cei").text

    assert "Latest scored month" in page and "Monthly plan vs done" not in page
    assert "planned in the month" in page
    cards = _kpi(page)
    assert cards["Planned that month"] == "3" and cards["Finished that month"] == "3"
    assert cards["Latest CEI"] == "1.00"
    assert page.count('class="stack-foot"') == 2


# --------------------------------------------------------------------------------------------
# /groups — a completion percentage over an empty population is not 0%
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["WBS", "Activity Type"])
@pytest.mark.parametrize("name", ["Project5", "Project2"])
def test_breakdown_rows_over_an_empty_population_render_a_dash(
    client: TestClient, name: str, field: str
) -> None:
    """``group_values`` scans EVERY task, summaries included, so a value carried only by rollup
    rows (WBS "0", Activity Type "Summary") arrives with no non-summary activities behind it."""
    _upload_golden(client, name)
    page = client.get(f"/groups?breakdown={field}").text
    rendered = {value: pct for value, _n, pct, _bei in _ROW.findall(page)}

    schedule = _golden_schedule(name)
    empty = {
        value
        for value in group_values(schedule, field)
        if not non_summary(filter_schedule(schedule, [(field, value)]))
    }
    assert empty, f"fixture {name} no longer exercises an empty {field} population"

    for value in empty:
        assert rendered[value] == "<span class=muted>—</span>", (
            f"{field}={value!r} has no non-summary activities but rendered {rendered[value]!r}"
        )
        # the row is now internally consistent: its BEI cell already said the same thing
    assert all("—" in pct for value, pct in rendered.items() if value in empty)


@pytest.mark.parametrize("name", ["Project5", "Project2"])
def test_a_group_that_is_genuinely_zero_percent_still_says_zero(
    client: TestClient, name: str
) -> None:
    """The true-positive twin. Suppressing the fabricated zeros must not suppress the real ones —
    on these goldens most WBS rows ARE 0% complete over a real population, and they still say so.
    """
    _upload_golden(client, name)
    page = client.get("/groups?breakdown=WBS").text
    rendered = {value: pct for value, _n, pct, _bei in _ROW.findall(page)}

    schedule = _golden_schedule(name)
    honest_zero = set()
    for value in group_values(schedule, "WBS"):
        tasks = non_summary(filter_schedule(schedule, [("WBS", value)]))
        if tasks and not any(t.percent_complete >= 100.0 for t in tasks):
            honest_zero.add(value)
    assert honest_zero, f"fixture {name} no longer exercises a real 0% group"

    for value in honest_zero:
        assert rendered[value] == "0%", f"WBS={value!r} lost its real 0% ({rendered[value]!r})"


@pytest.mark.parametrize("name", ["Project5", "Project2"])
def test_every_rendered_percentage_is_backed_by_a_population(client: TestClient, name: str) -> None:
    """The whole-table invariant, not a sample: a percentage appears in the completion column
    if and only if that value has at least one non-summary activity behind it."""
    _upload_golden(client, name)
    page = client.get("/groups?breakdown=WBS").text
    schedule = _golden_schedule(name)
    for value, _n, pct, _bei in _ROW.findall(page):
        populated = bool(non_summary(filter_schedule(schedule, [("WBS", value)])))
        assert populated == pct.endswith("%"), f"WBS={value!r}: population={populated} cell={pct!r}"
