"""OR-01 — every roll-up title names the aggregation rule it applied (ADR-0321).

The Portfolio ledger's headline headings state the rule the view actually computed (latest
included version vs an average), the NEW "Avg DCMA-14 passes — included, solvable versions"
column is a VIEW-LAYER arithmetic mean over the engine's own per-version pass counts (no new
engine math; "—" when no included version solves — never a fake 0), and the per-file surfaces
(home manifest, dashboard cards, /card) name Site / Company · data date · computed finish ·
effective margin · DCMA-14 per file. Every expected figure below is derived from the ENGINE's
own ``compute_summary`` on the same bytes — the view may only restate them (Law 2) — and the
fixtures are deliberately NON-degenerate (distinct pass counts; a nonzero margin) so a
hardcoded value cannot pass.
"""

from __future__ import annotations

import datetime as dt
import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.summary import VersionSummary, compute_summary
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'

#: Three same-Project variants chosen because their engine DCMA-14 pass counts DIFFER (5 / 9 / 5
#: on this tree — asserted below, not assumed), so the average is a real mean, not a copy; the
#: middle one carries a name-based "Schedule Margin" activity so its effective margin is NONZERO
#: (2.0 d on this tree — asserted below) and a hardcoded fake 0 cannot pass the margin pins.
_ONE = "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
_TWO = (
    "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
    "<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration>"
    "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>"
    "<Task><UID>9</UID><Name>Schedule Margin</Name><Duration>PT16H0M0S</Duration>"
    "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink></Task>"
)
_THREE = (
    "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
    "<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration>"
    "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>"
    "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration>"
    "<ConstraintType>2</ConstraintType><ConstraintDate>2025-01-08T08:00:00</ConstraintDate>"
    "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type>"
    "<LinkLag>4800</LinkLag></PredecessorLink></Task>"
)
#: A logic loop — CPMError, so the version is UNSOLVABLE and must contribute "—", never a 0.
_CYCLE = (
    "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
    "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink></Task>"
    "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
    "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>"
)


def _mspdi(tasks: str, title: str, status: str, company: str | None = None) -> bytes:
    company_el = f"<Company>{company}</Company>" if company else ""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate><Title>{title}</Title>"
        f"{company_el}<StatusDate>{status}</StatusDate><Tasks>{tasks}</Tasks></Project>"
    ).encode()


#: filename -> bytes; keys become the session keys. Project Alpha = a0 (UNSOLVABLE, earliest)
#: + v1..v3 (solvable) — the MIXED-solvability pool; Project Gamma = g1, unsolvable only.
_FILES: dict[str, bytes] = {
    "a0.xml": _mspdi(_CYCLE, "Alpha", "2025-01-05T00:00:00"),
    "v1.xml": _mspdi(_ONE, "Alpha", "2025-01-10T00:00:00"),
    "v2.xml": _mspdi(_TWO, "Alpha", "2025-02-10T00:00:00", company="NASA Goddard"),
    "v3.xml": _mspdi(_THREE, "Alpha", "2025-03-10T00:00:00"),
    "g1.xml": _mspdi(_CYCLE, "Gamma", "2025-01-10T00:00:00"),
}
_SOLVABLE = ("v1.xml", "v2.xml", "v3.xml")


def _oracle(name: str) -> VersionSummary:
    """The ENGINE's answer for one uploaded file — the only source of an expected figure."""
    return compute_summary(parse_mspdi_text(_FILES[name].decode()))


def _client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    files = [("files", (fn, blob, "text/xml")) for fn, blob in _FILES.items()]
    assert c.post("/upload", files=files).status_code == 200
    return c


@pytest.fixture(scope="module")
def client() -> TestClient:
    return _client()


@pytest.fixture(scope="module")
def page(client: TestClient) -> str:
    return client.get("/portfolio").text


def _row_cells(page: str, title: str) -> list[str]:
    """The <td> cells of one project's ledger row (the row wrapping <b>{title}</b>)."""
    m = re.search(rf"<tr><td><details><summary><b>{title}</b>.*?</tr>", page, re.S)
    assert m is not None, f"no ledger row for {title}"
    return re.findall(r"<td>(.*?)</td>", m.group(0), re.S)


def _mdY(iso: str) -> str:
    return dt.date.fromisoformat(iso[:10]).strftime("%m/%d/%Y")


def _mean_cell(names: list[str]) -> str:
    """The expected average cell, from the engine's own pass counts (view-layer arithmetic)."""
    passes = [_oracle(n).dcma_pass for n in names]
    n = len(passes)
    return f"{sum(passes) / n:.1f} of 14 · {n} version{'' if n == 1 else 's'}"


def test_fixtures_are_non_degenerate() -> None:
    """The guards that make every later pin meaningful: distinct pass counts (a copied value
    cannot equal the mean) and a NONZERO margin (a hardcoded fake 0 cannot pass)."""
    passes = [_oracle(n).dcma_pass for n in _SOLVABLE]
    assert len(set(passes)) > 1, "the mean must not be a trivial copy"
    margin = _oracle("v2.xml").effective_margin_days
    assert margin is not None and margin != 0.0, "the margin pins need a nonzero engine value"
    assert _oracle("a0.xml").unsolvable and _oracle("g1.xml").unsolvable


# ── (a) the ledger headings state the aggregation rule (OR-01's core ask) ────────────────────


def test_ledger_headings_state_the_aggregation_rule(page: str) -> None:
    """Reading the title alone must tell the analyst latest-value vs average — and the stated
    pool must be the pool the code APPLIES (included AND solvable, never "all")."""
    heads = re.findall(r"<th scope=col>(.*?)</th>", page)
    assert heads == [
        "Project",
        "Site / Company",
        "Versions",
        "Latest data date",
        "Computed finish — latest version",
        "Effective margin — latest version",
        "DCMA-14 — latest version",
        "Avg DCMA-14 passes — included, solvable versions",
    ]


def test_the_takeaway_discloses_both_aggregation_bases(page: str) -> None:
    m = re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page)
    assert m is not None
    assert "latest included version" in m.group(1)
    assert "average pooled across its included, solvable versions" in m.group(1)


# ── (b) the average column is the view-layer mean of ENGINE pass counts ──────────────────────


def test_avg_dcma_column_is_the_view_mean_of_engine_pass_counts(page: str) -> None:
    cells = _row_cells(page, "Alpha")
    assert cells[-1] == _mean_cell(list(_SOLVABLE))
    # the latest-version DCMA pill still carries the LATEST version's counts, verbatim
    latest = _oracle("v3.xml")
    assert f"{latest.dcma_pass} pass / {latest.dcma_fail} fail" in cells[-2]


def test_mixed_solvability_pool_is_disclosed_in_the_cell(page: str) -> None:
    """Alpha holds FOUR included versions but only three solve: the unsolvable one stays OUT
    of the mean (its audit never ran — a fake 0 would poison it) and the cell's own pool count
    says so, right where the analyst reads the figure."""
    cells = _row_cells(page, "Alpha")
    assert cells[2] == "4"  # the Versions column: all four included
    assert cells[-1].endswith("· 3 versions")  # the mean's ACTUAL pool: the three that solve


def test_avg_cell_is_em_dash_when_no_included_version_solves(page: str) -> None:
    """An unsolvable-only project has an empty pool and the cell is '—', never 0.0."""
    cells = _row_cells(page, "Gamma")
    assert cells[-1] == "—"
    assert "of 14" not in cells[-1]


def test_excluding_a_version_shifts_the_average_pool() -> None:
    """ADR-0259 exclusion re-scopes the mean AND its stated pool size — live, reversibly."""
    c = _client()
    assert (
        c.post(
            "/project/exclude", data={"key": "v2", "excluded": "1"}, follow_redirects=False
        ).status_code
        == 303
    )
    cells = _row_cells(c.get("/portfolio").text, "Alpha")
    assert cells[-1] == _mean_cell(["v1.xml", "v3.xml"])
    assert "2 versions" in cells[-1]
    c.post("/project/exclude", data={"key": "v2", "excluded": "0"}, follow_redirects=False)
    cells = _row_cells(c.get("/portfolio").text, "Alpha")
    assert cells[-1] == _mean_cell(list(_SOLVABLE))


# ── (c) the home manifest names, per file, what each figure is ───────────────────────────────


def test_home_manifest_names_each_per_file_figure(client: TestClient) -> None:
    home = client.get("/").text
    heads = re.findall(r"<th scope=col>(.*?)</th>", home)
    for h in ("Site / Company", "Data date", "Computed finish", "Effective margin", "DCMA-14"):
        assert h in heads, h
    s = _oracle("v2.xml")
    row = re.search(r'<tr><td><a href="/analysis/v2">.*?</tr>', home, re.S)
    assert row is not None
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(0), re.S)
    assert cells[3] == "NASA Goddard"
    assert s.status_date_iso is not None and cells[4] == _mdY(s.status_date_iso)
    assert s.finish_iso is not None and cells[5] == _mdY(s.finish_iso)
    assert s.effective_margin_days is not None
    assert cells[6] == f"{s.effective_margin_days:g} d"


def test_home_manifest_dcma_cell_agrees_with_the_health_cards_on_the_same_page(
    client: TestClient,
) -> None:
    """ONE page, ONE DCMA verdict per file: the manifest cell counts the SAME parity-aware
    card tier the health cards render, so the two can never disagree (the summary tier is
    default-mode only — the ADR-0321 recorded residual)."""
    cards = {c["key"]: c for c in client.get("/api/dashboard").json()["cards"]}
    home = client.get("/").text
    for key in ("v1", "v2", "v3"):
        statuses = [d["status"] for d in cards[key]["dcma"]]
        expected = f"{statuses.count('PASS')} pass / {statuses.count('FAIL')} fail"
        row = re.search(rf'<tr><td><a href="/analysis/{key}">.*?</tr>', home, re.S)
        assert row is not None
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(0), re.S)
        assert expected in cells[7], key


def test_home_manifest_unsolvable_file_keeps_em_dashes_never_zeroes(client: TestClient) -> None:
    home = client.get("/").text
    row = re.search(r'<tr><td><a href="/analysis/g1">.*?</tr>', home, re.S)
    assert row is not None
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(0), re.S)
    # site (none in the source), finish, margin, DCMA — all "—"; the data date IS carried
    assert cells[3] == "—" and cells[5] == "—" and cells[6] == "—" and cells[7] == "—"
    assert cells[4] == "01/10/2025"
    assert "0 pass" not in row.group(0)


# ── (d) the dashboard cards + /card page carry the missing OR-01 fields ──────────────────────


def test_dashboard_cards_carry_site_and_margin_verbatim(client: TestClient) -> None:
    """Row-level proof for ADR-0321's golden re-pin: the ONLY payload delta is the two new
    keys (the key-set pins), and each carries the engine/source value verbatim."""
    cards = {c["key"]: c for c in client.get("/api/dashboard").json()["cards"]}
    assert set(cards) == {"a0", "v1", "v2", "v3", "g1"}
    for key, name in (("v1", "v1.xml"), ("v2", "v2.xml"), ("v3", "v3.xml")):
        s = _oracle(name)
        assert cards[key]["solvable"] is True
        assert cards[key]["margin_days"] == s.effective_margin_days
        assert set(cards[key]) == {
            "key",
            "name",
            "source_file",
            "site",
            "margin_days",
            "activities",
            "data_date",
            "solvable",
            "status_mix",
            "percent_complete",
            "critical_count",
            "critical_pct",
            "cpm_finish",
            "baseline_finish",
            "finish_delta_days",
            "dcma",
        }
    assert cards["v1"]["site"] is None
    assert cards["v2"]["site"] == "NASA Goddard"
    assert cards["v2"]["margin_days"] not in (None, 0.0)  # the engine's own nonzero figure
    # the unsolvable cards degrade exactly as before, plus the two new fields as None
    for key in ("a0", "g1"):
        bad = cards[key]
        assert bad["solvable"] is False
        assert bad["site"] is None and bad["margin_days"] is None
        assert set(bad) == {
            "key",
            "name",
            "source_file",
            "site",
            "margin_days",
            "activities",
            "data_date",
            "solvable",
        }


def test_margin_confirm_reaches_the_dashboard_cards_immediately() -> None:
    """The ADR-0291 card memo bakes margin_days in, and its epoch key does NOT cover the
    margin overlay — /margin/confirm must invalidate it, or /api/dashboard keeps serving the
    pre-confirm margin the engine no longer computes (the ADR-0321 review's live repro)."""
    c = TestClient(create_app(SessionState()))
    assert (
        c.post("/upload", files=[("files", ("v1.xml", _FILES["v1.xml"], "text/xml"))]).status_code
        == 200
    )
    before = c.get("/api/dashboard").json()["cards"][0]
    assert before["margin_days"] == 0.0  # no margin-named task: the engine's own 0-day margin
    # the operator confirms activity UID 1 as THE margin activity (F3b overlay)
    assert (
        c.post(
            "/margin/confirm",
            data={"key": "v1", "action": "confirm", "uid": "1"},
            follow_redirects=False,
        ).status_code
        == 303
    )
    after = c.get("/api/dashboard").json()["cards"][0]
    expected = compute_summary(
        parse_mspdi_text(_FILES["v1.xml"].decode()), margin_uids=frozenset({1})
    ).effective_margin_days
    assert expected not in (None, 0.0)  # fixture guard: the confirm really changes the figure
    assert after["margin_days"] == expected


def test_dashboard_js_renders_the_two_new_stats(client: TestClient) -> None:
    js = client.get("/static/dashboard.js").text
    assert 'stat("Site / Company", c.site || "—")' in js
    assert 'stat("Effective margin",' in js
    assert 'c.margin_days != null ? c.margin_days + " d" : "—"' in js


def test_card_page_shows_site_and_margin(client: TestClient) -> None:
    """Label and value pinned ADJACENT (one stat card), not as two page-wide substrings."""
    s = _oracle("v2.xml")
    assert s.effective_margin_days is not None
    card = client.get("/card/v2").text
    assert (
        "<div class=stat-card><div class=stat-value>NASA Goddard</div>"
        "<div class=stat-label>Site / Company</div></div>"
    ) in card
    assert (
        f"<div class=stat-card><div class=stat-value>{s.effective_margin_days:g} d</div>"
        "<div class=stat-label>Effective margin</div></div>"
    ) in card


# ── (e) the new headings are in the offline i18n catalog (every language) ────────────────────


def test_new_headings_have_catalog_entries() -> None:
    from schedule_forensics.web.i18n import CATALOG

    for term in (
        "Latest data date",
        "Computed finish — latest version",
        "Effective margin — latest version",
        "DCMA-14 — latest version",
        "Avg DCMA-14 passes — included, solvable versions",
        "Effective margin",
        "DCMA-14",
    ):
        for lang in ("es", "fr", "de", "pt"):
            assert term in CATALOG[lang], (term, lang)
