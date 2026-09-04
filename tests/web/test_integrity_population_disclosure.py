"""I-01 (operator 2026-09-03): "/integrity is not picking up the same findings it once did".

The differential run (the golden trio, Project2→5 and the TP4 corpus through v1.0.221, v1.0.229
and this tree) produced IDENTICAL detector rows by name — the detectors did not change. What DID
narrow the page is the ADR-0258 active-Project population: with the loaded files grouped into
more than one Project (two dropped folders; loose files whose document Titles differ; a titled
file beside a title-less one), /integrity pairs ONLY the active Project's versions and, when
that Project holds one file, tells the operator to "Load at least two versions" — while the
other version sits loaded, one banner-switch away. On a testimony surface that is a silent
narrowing: the page must NAME the other Projects' versions and say how to reach them.

Red-first (QC-1): the two disclosure tests below were observed RED on the pristine tree (the
empty state carried no Project name, no other-Project count and no switch form); the
single-population guard was green before and after (the disclosure is multi-Project only).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _files() -> list[tuple[str, bytes]]:
    hf = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    hfu = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated.mspdi.xml.gz").read_bytes()
    )
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    return [("Hard_File.mpp.xml", hf), ("Hard_File_updated.mpp.xml", hfu), ("Project5.mpp.xml", p5)]


def _client(rels: list[str]) -> tuple[TestClient, SessionState]:
    st = SessionState()
    c = TestClient(create_app(st))
    for i, ((name, data), rel) in enumerate(zip(_files(), rels, strict=True)):
        r = c.post(
            "/upload",
            files={"files": (name, data, "text/xml")},
            data={
                "file_meta": json.dumps(
                    [{"rel": f"{rel}/{name}", "mtime": 1_700_000_000_000 + i * 86_400_000}]
                )
            },
        )
        assert r.status_code == 200
    return c, st


def test_two_projects_active_one_has_one_file_names_the_other_projects_versions() -> None:
    """Folder A holds two versions, folder B one; B loaded last so it is the ACTIVE Project
    (ADR-0258 heals to the most recently loaded file). /integrity must not merely say "load two
    versions": it names the active Project, says how many of the loaded files it holds, names
    Project A with its two versions, and carries the switch form back to /integrity."""
    c, st = _client(["projA", "projA", "projB"])
    assert st.active_population() is not None and st.active_population()[1] == "projB"
    page = c.get("/integrity").text
    assert "Load at least two versions" not in page  # the misleading message is gone
    assert "Project <b>projB</b> holds 1 of the 3 loaded files" in page
    assert "<b>projA</b> (2 versions)" in page
    # the switch lands back on THIS page (the app strips Referer; next_url is explicit)
    assert 'action="/project/select"' in page
    assert 'name=next_url value="/integrity"' in page
    assert 'value="folder:projA"' in page


def test_with_the_two_version_project_active_the_pair_page_still_states_its_population() -> None:
    """Switch to Project A: the findings page renders its pair AND states which Project the pair
    comes from and that one loaded file is outside it — the page never implies "all loaded
    files" when two are in play."""
    c, _st = _client(["projA", "projA", "projB"])
    r = c.post(
        "/project/select",
        data={"pid": "folder:projA", "next_url": "/integrity"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/integrity"
    page = c.get("/integrity").text
    assert "manipulation-pattern findings between Hard_File.mpp.xml and Hard_File_updated" in page
    assert "Project <b>projA</b> holds 2 of the 3 loaded files" in page
    assert "<b>projB</b> (1 version)" in page


def test_single_project_sessions_carry_no_project_disclosure() -> None:
    """The guard on the guard: one Project → the byte-shape of the page is the pre-change one
    (no Project disclosure line, no per-page switch form)."""
    c, _st = _client(["proj", "proj", "proj"])
    page = c.get("/integrity").text
    assert "holds" not in page.split("<h1", 1)[-1][:4000] or "of the 3 loaded files" not in page
    assert 'name=next_url value="/integrity"' not in page
    assert "manipulation-pattern findings between" in page


# ── the reduce-filter leg: an empty population is "nothing to compare", never "no findings" ──


def test_a_role_named_filter_with_no_mapping_reports_nothing_to_compare_not_no_findings() -> None:
    """ADR-0450 made an UNMAPPED role name match nothing (so a stale filter can never fall
    back to the WBS column). On /integrity that left the page asserting "No manipulation-
    pattern findings between A and B" — an affirmative negative on a testimony surface over
    an EMPTY population. Observed RED on the pristine tree: the takeaway read exactly that."""
    c, st = _client(["proj", "proj", "proj"])
    assert c.get("/groups?field=Cost+Account&value0=X&apply=1").status_code == 200
    assert st.active_filter == (("Cost Account", ["X"]),)
    page = c.get("/integrity").text
    assert "No manipulation-pattern findings" not in page
    assert "The active filter leaves nothing to compare between" in page
    assert "0 of " in page and "are in scope of the active filter" in page
    assert "clear or change the filter" in page


def test_a_narrowing_filter_states_the_in_scope_counts_beside_the_findings() -> None:
    """A real narrowing (WBS = 1) keeps whatever findings survive AND says how many activities
    of each version the detectors actually saw."""
    c, _st = _client(["proj", "proj", "proj"])
    assert c.get("/groups?field=WBS&value0=1&apply=1").status_code == 200
    page = c.get("/integrity").text
    assert "Reduce filter active:" in page
    assert " of " in page and "are in scope of the active filter" in page
    # and the counts are real: the scoped side is smaller than the raw side
    import re

    m = re.search(r"(\d+) of (\d+) activities in [^ ]+ and (\d+) of (\d+) in", page)
    assert m, page[:2000]
    a, a_all, b, b_all = (int(x) for x in m.groups())
    assert 0 < a < a_all and 0 < b < b_all, (a, a_all, b, b_all)


def test_highlight_mode_and_no_filter_carry_no_scope_phrase() -> None:
    """Highlight mode does not scope metrics (the banner says so) — no counts are claimed."""
    c, _st = _client(["proj", "proj", "proj"])
    assert c.get("/groups?field=WBS&value0=1&apply=1&mode=highlight").status_code == 200
    page = c.get("/integrity").text
    assert "are in scope of the active filter" not in page
    c.get("/groups?clear=1")
    assert "are in scope of the active filter" not in c.get("/integrity").text
