"""Active-project scoping (ADR-0258) + duplicate review/excludes (ADR-0259) + Site (ADR-0260).

The master-prompt acceptance criteria, encoded: loading files belonging to several real Projects
yields exactly that many selectable Projects; every analysis population draws from ONE (the active)
Project only — no cross-project mixing anywhere but Portfolio; switching the active project visibly
changes the population; excludes are reversible and never silent; a single-Project session behaves
exactly as before scoping existed.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(
    title: str | None,
    status: str | None = None,
    company: str | None = None,
    extra_task: bool = False,
) -> bytes:
    """A minimal valid MSPDI document with optional <Title>, <StatusDate>, and <Company>."""
    title_el = f"<Title>{title}</Title>" if title is not None else ""
    status_el = f"<StatusDate>{status}</StatusDate>" if status else ""
    company_el = f"<Company>{company}</Company>" if company else ""
    tasks = (
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
        if extra_task
        else _TASK
    )
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"{title_el}{company_el}{status_el}{tasks}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def _load_three_projects(client: TestClient) -> None:
    """Alpha (2 loose versions) + Beta (1 loose) + Gamma (a folder) — 3 distinct Projects."""
    client.post(
        "/upload",
        files=[
            ("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
            ("files", ("b1.xml", _mspdi("Beta", "2025-01-15T00:00:00"), "text/xml")),
        ],
    )
    client.post(
        "/upload",
        files=[("files", ("g1.xml", _mspdi("ignored", "2025-03-01T00:00:00"), "text/xml"))],
        data={"file_meta": json.dumps([{"rel": "Gamma/g1.xml", "mtime": 5}])},
    )


def test_three_projects_yield_three_selectable_projects_and_no_mixing(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    _load_three_projects(client)
    assert {p.title for p in st.projects()} == {"Alpha", "Beta", "Gamma"}
    # the newest-loaded Project (the Gamma folder) auto-became ACTIVE (ADR-0258) …
    active = st.active_population()
    assert active is not None and active[1] == "Gamma"
    # … and the analysis population is ONLY its versions — zero cross-project mixing
    assert [k for k, _ in st.ordered_versions()] == ["g1"]
    assert len(st.ordered()) == 1
    # while the manifest still lists every loaded file
    assert {k for k, _ in st.all_versions()} == {"a1", "a2", "b1", "g1"}


def test_switching_the_active_project_visibly_changes_the_population(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    _load_three_projects(client)
    resp = client.post(
        "/project/select",
        data={"pid": "title:alpha", "next_url": "/trend"},
        follow_redirects=False,
    )
    assert resp.status_code == 303 and resp.headers["location"] == "/trend"
    # open-redirect guard: only a local path is honored
    evil = client.post(
        "/project/select",
        data={"pid": "title:alpha", "next_url": "//evil.example"},
        follow_redirects=False,
    )
    assert evil.headers["location"] == "/"
    assert [k for k, _ in st.ordered_versions()] == ["a1", "a2"]  # Alpha's two versions only
    # the banner names the active Project and lists ONLY its files
    page = client.get("/trend").text
    assert "Alpha" in page and "a1.xml" in page and "a2.xml" in page
    assert "b1.xml" not in page and "g1.xml" not in page  # no other project's file bleeds in


def test_unknown_pid_is_ignored_fail_soft(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    _load_three_projects(client)
    before = st.active_project
    client.post("/project/select", data={"pid": "title:nope"}, follow_redirects=False)
    assert st.active_project == before


def test_portfolio_still_shows_every_project(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    _load_three_projects(client)
    client.post("/project/select", data={"pid": "title:beta"}, follow_redirects=False)
    page = client.get("/portfolio").text
    assert "Alpha" in page and "Beta" in page and "Gamma" in page  # the ONE cross-project page
    assert "Analyze this project" in page


def test_single_project_session_behaves_exactly_as_before(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", ("v1.xml", _mspdi("Solo", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("v2.xml", _mspdi("Solo", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    # one Project → the fast no-restriction path: analysis population == manifest
    assert [k for k, _ in st.ordered_versions()] == [k for k, _ in st.all_versions()]
    assert len(st.ordered()) == 2
    # no project strip in the banner (nothing to switch), no auto-select notice
    assert "Projects loaded" not in client.get("/trend").text


def test_exclude_is_reversible_and_never_silent(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", ("v1.xml", _mspdi("Solo", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("v2.xml", _mspdi("Solo", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    resp = client.post(
        "/project/exclude", data={"key": "v1", "excluded": "1"}, follow_redirects=False
    )
    assert resp.status_code == 303 and resp.headers["location"] == "/portfolio"
    assert [k for k, _ in st.ordered_versions()] == ["v2"]  # left the analysis population
    assert {k for k, _ in st.all_versions()} == {"v1", "v2"}  # …but stays loaded
    page = client.get("/portfolio").text
    assert "excluded" in page and "Restore" in page  # badged, with the way back
    client.post("/project/exclude", data={"key": "v1", "excluded": "0"}, follow_redirects=False)
    assert [k for k, _ in st.ordered_versions()] == ["v1", "v2"]  # fully reversible


def test_same_date_different_content_needs_review_until_one_is_excluded(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    # same Project, same data date, DIFFERENT bytes (one has an extra task) → pending review
    client.post(
        "/upload",
        files=[
            ("files", ("r1.xml", _mspdi("Twin", "2025-01-10T00:00:00"), "text/xml")),
            (
                "files",
                ("r2.xml", _mspdi("Twin", "2025-01-10T00:00:00", extra_task=True), "text/xml"),
            ),
        ],
    )
    p = st.projects()[0]
    assert p.pending_review is True
    page = client.get("/portfolio").text
    assert "unresolved duplicate/revision decision" in page
    assert "different content" in page  # the notice names the conflict
    # the differentiators the decision needs are shown per version
    assert "activities" in page and "data date" in page
    # excluding one copy resolves the review flag
    client.post("/project/exclude", data={"key": "r2", "excluded": "1"}, follow_redirects=False)
    assert st.projects()[0].pending_review is False
    assert "unresolved duplicate/revision decision" not in client.get("/portfolio").text


def test_company_becomes_the_portfolio_site_column(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    client.post(
        "/upload",
        files=[
            (
                "files",
                (
                    "s1.xml",
                    _mspdi("Orion", "2025-01-10T00:00:00", company="NASA Goddard"),
                    "text/xml",
                ),
            ),
        ],
    )
    assert st.schedules["s1"].company == "NASA Goddard"
    page = client.get("/portfolio").text
    assert "Site / Company" in page and "NASA Goddard" in page


def test_untitled_loose_files_pool_into_one_population(
    sc: tuple[SessionState, TestClient],
) -> None:
    """Title-less loose files carry no project-identity signal: Portfolio lists each as its own
    needs-attention row (ADR-0225, unchanged), but ANALYSIS pools them as one explicit
    "(untitled files)" population (ADR-0258) — the classic drop-N-untitled-exports version-series
    workflow keeps working instead of shattering into N single-file projects."""
    st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", (f"u{i}.xml", _mspdi(None, f"2025-0{i}-10T00:00:00"), "text/xml"))
            for i in (1, 2, 3)
        ],
    )
    # ONLY untitled files → one population → the unrestricted fast path (pre-scoping behavior)
    assert len(st.projects()) == 3  # Portfolio still shows three needs-attention rows
    assert [k for k, _ in st.ordered_versions()] == ["u1", "u2", "u3"]
    assert "Projects loaded" not in client.get("/trend").text  # no strip — nothing to switch
    # add a TITLED project: two populations — untitled files never bleed into it
    client.post(
        "/upload",
        files=[("files", ("t1.xml", _mspdi("Titled", "2025-04-10T00:00:00"), "text/xml"))],
    )
    assert [k for k, _ in st.ordered_versions()] == ["t1"]  # newest (titled) auto-selected
    client.post(
        "/project/select", data={"pid": "untitled:", "next_url": "/"}, follow_redirects=False
    )
    assert [k for k, _ in st.ordered_versions()] == ["u1", "u2", "u3"]  # the pool, no titled file
    assert "(untitled files)" in client.get("/trend").text  # honestly labeled in the banner


def test_wipe_resets_selection_and_excludes(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    _load_three_projects(client)
    client.post("/project/exclude", data={"key": "a1", "excluded": "1"}, follow_redirects=False)
    assert st.active_project is not None and st.excluded_keys == {"a1"}
    client.post("/session/wipe")
    assert st.active_project is None and st.excluded_keys == set()
