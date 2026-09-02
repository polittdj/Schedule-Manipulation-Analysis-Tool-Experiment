"""Field roles on the page (operator 2026-09-02): the operator picks WHICH field is the WBS —
and which carry the Cost Account and Work Package — from every standard + custom field the loaded
files offer; the WBS pivots (/wbs page, its JSON and export) group by that field, and the
Groups & Filters page offers "Cost Account" / "Work Package" as filter fields that resolve to
the mapped columns. Red-first: the pre-feature tree has no ``/fields/roles`` route (404) and
/wbs groups only by the stored WBS column.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "tests" / "fixtures" / "test_projects" / "TP2_Bridge_4x10_Calendar.xml"
KEY = "TP2_Bridge_4x10_Calendar"
FIELD_ID = "188743731"  # MS Project Text1


def _fixture_with_custom_field() -> bytes:
    """TP2 with a project-level custom field aliased ``CA-WBS`` and a value on every task: the
    odd tasks under ``7.x``, the even ones under ``9.x`` — a breakdown the WBS column knows
    nothing about (its top levels are ``1`` and ``2``)."""
    xml = BASE.read_text(encoding="utf-8")
    defs = (
        "<ExtendedAttributes><ExtendedAttribute>"
        f"<FieldID>{FIELD_ID}</FieldID><FieldName>Text1</FieldName><Alias>CA-WBS</Alias>"
        "</ExtendedAttribute></ExtendedAttributes>"
    )
    xml = xml.replace("<Tasks>", defs + "<Tasks>", 1)
    n = 0

    def _inject(m: re.Match[str]) -> str:
        nonlocal n
        n += 1
        code = f"7.{n}" if n % 2 else f"9.{n}"
        return (
            f"<ExtendedAttribute><FieldID>{FIELD_ID}</FieldID><Value>{code}</Value>"
            "</ExtendedAttribute></Task>"
        )

    xml = re.sub(r"</Task>", _inject, xml)
    return xml.encode("utf-8")


def _client() -> TestClient:
    st = SessionState()
    c = TestClient(create_app(st))
    c.__enter__()
    data = _fixture_with_custom_field()
    files = [("files", (BASE.name, data, "text/xml"))]
    meta = json.dumps([{"rel": BASE.name, "mtime": 1_700_000_000_000}])
    assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    return c


def _wbs_groups(c: TestClient) -> list[str]:
    r = c.get(f"/api/wbs/{KEY}")
    assert r.status_code == 200
    return [g["wbs"] for g in r.json()["groups"]]


def test_wbs_pivot_groups_by_the_mapped_field_after_the_role_is_set() -> None:
    c = _client()
    assert _wbs_groups(c) == ["1", "2", "3"]  # the stored column, as before
    form = {"wbs": "CA-WBS", "next_url": f"/wbs/{KEY}"}
    r = c.post("/fields/roles", data=form, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/wbs/{KEY}"
    assert _wbs_groups(c) == ["7", "9"]
    page = c.get(f"/wbs/{KEY}").text
    assert "CA-WBS" in page and ">7<" in page and ">9<" in page
    # the export follows the same role (one truth for the pivot)
    x = c.get(f"/export/xlsx/wbs/{KEY}")
    assert x.status_code == 200 and len(x.content) > 1000
    # clearing the role restores the stored column
    c.post("/fields/roles", data={"wbs": ""}, follow_redirects=False)
    assert _wbs_groups(c) == ["1", "2", "3"]


def test_roles_are_offered_as_filter_fields_and_resolve_to_the_mapped_column() -> None:
    c = _client()
    page = c.get("/groups").text
    assert 'value="Cost Account"' not in page  # unmapped → not offered
    c.post("/fields/roles", data={"cost_account": "CA-WBS"}, follow_redirects=False)
    page = c.get("/groups").text
    assert 'value="Cost Account"' in page and "CA-WBS" in page
    # the value autocomplete resolves the role
    vals = c.get("/api/group-values", params={"field": "Cost Account"}).json()["values"]
    assert "7.1" in vals and "9.2" in vals
    # applying a role-named filter scopes the session to the mapped column's matches
    r = c.get("/groups", params={"field": "Cost Account", "value0": "7.3", "apply": "1"})
    assert r.status_code == 200 and "Cost Account" in r.text
    # the scoped population is exactly the one leaf carrying 7.3 (7.1 sits on the summary row)
    wbs_after = c.get(f"/api/wbs/{KEY}").json()["groups"]
    assert sum(g["total"] for g in wbs_after) == 1


def test_unknown_or_unmapped_input_is_rejected_or_ignored_never_guessed() -> None:
    c = _client()
    # a field none of the loaded files carry is refused (stays unmapped)
    c.post("/fields/roles", data={"wbs": "No Such Field"}, follow_redirects=False)
    assert _wbs_groups(c) == ["1", "2", "3"]
    # a wipe returns the roles to their default
    c.post("/fields/roles", data={"wbs": "CA-WBS"}, follow_redirects=False)
    assert _wbs_groups(c) == ["7", "9"]
    c.post("/session/wipe", follow_redirects=False)
    c2 = c  # same process/session object
    data = _fixture_with_custom_field()
    files = [("files", (BASE.name, data, "text/xml"))]
    meta = json.dumps([{"rel": BASE.name, "mtime": 1_700_000_000_001}])
    assert c2.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    assert _wbs_groups(c2) == ["1", "2", "3"]
