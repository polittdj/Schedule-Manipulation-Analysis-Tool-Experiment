"""Standing computed census: operator FILE CONTENT never reaches a served artifact as MARKUP.

Every activity name, resource name and project name in this tool comes out of an operator's
schedule file. Those strings are data, not authorship — a real MS Project activity may legally
be called ``Pour slab <2m> & cure``. Two things must hold, and neither had ever been measured
before this guard (page modules were a never-audited dimension of the 2026-08-16 audit):

* a **served HTML page** must render such a name as TEXT, never as elements; and
* an **exported workbook/document** must stay WELL-FORMED XML, because it leaves the tool and
  gets quoted in testimony (Law 2 — the MF-02/ADR-0411 family: an export that contradicts the
  screen is worse than no export).

Both oracles are deliberately INDEPENDENT of the code under test. The page census looks for the
raw injected substring in the response bytes — a correctly-escaped page can never contain it.
The export census parses every XML part of every produced archive with a real XML parser — a
writer that forgets to escape produces a part that will not parse.

Three ways this guard refuses to pass vacuously, each of which this repo has paid for:

* **the route list is COMPUTED from the app object, never hand-written.** The throwaway version
  of this census hand-listed its pages; two of the twenty-eight were 404s, and a 404 scored as
  "clean" — the sweep looked exhaustive and was not.
* **a non-success response is never scored.** An error page carries none of the injected content,
  so scoring one is indistinguishable from scoring an escaped page.
* **population floors.** If the enumerator ever stops finding routes the assertions would hold
  over an empty set, so each census asserts it saw a plausible number of responses.

``test_the_page_census_has_teeth`` and ``test_the_export_census_has_teeth`` then break the real
escaping helpers and require the censuses to go RED, so a green run means the instrument looked
and saw nothing — not that it failed to look.
"""

from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.reports.docx as docx_mod
import schedule_forensics.reports.xlsx as xlsx_mod
import schedule_forensics.web.analysis as analysis_mod
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)

#: An element with a distinctive attribute — if any renderer treats a name as markup, this
#: becomes a real <img> node. Chosen over a bare "<b>" because it cannot occur by accident.
RAW_TAG = "<img src=x onerror=SFPROBE>"
#: Table-structure corruption: markup that would silently restructure a rendered table.
ROW_BREAK = "</td></tr><tr><td>SFROWBREAK"
#: Every XML-hostile shape a legal MS Project activity name can carry.
XML_HOSTILE = "A&B <tag> \"q\" 's' ]]> <![CDATA[ </t></is></c>"


def _poisoned(marker_a: str, marker_b: str = "") -> bytes:
    """The shipped example with operator-supplied strings carrying `marker_a` / `marker_b`."""
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["name"] = f"Project {marker_a}"
    for i, task in enumerate(doc["tasks"]):
        tail = marker_b if (marker_b and i % 2) else marker_a
        task["name"] = f"{task['name']} {tail}"
        if task.get("resource_names"):
            task["resource_names"] = [f"{r} {marker_a}" for r in task["resource_names"]]
    return json.dumps(doc).encode()


def _loaded(payload: bytes) -> tuple[Any, TestClient, str]:
    state = SessionState()
    app = create_app(state)
    client = TestClient(app)
    resp = client.post("/upload", files={"files": ("probe.json", payload, "application/json")})
    assert resp.status_code == 200, resp.text
    return app, client, next(iter(state.schedules))


def _get_urls(
    app: Any, key: str, *, prefix: str = "", skip_prefix: str = "", fmt: str = "xlsx"
) -> list[str]:
    """Every GET route on the live app, with its path params filled — COMPUTED, never listed."""
    fill = {"name": key, "fmt": fmt, "uid": "2", "target": "2", "key": key}
    urls: list[str] = []
    for route in app.routes:
        path = str(getattr(route, "path", ""))
        methods = getattr(route, "methods", set()) or set()
        if "GET" not in methods or path.startswith("/static"):
            continue
        if prefix and not path.startswith(prefix):
            continue
        if skip_prefix and path.startswith(skip_prefix):
            continue
        params = re.findall(r"\{(\w+)\}", path)
        if any(p not in fill for p in params):
            continue
        url = path
        for p in params:
            url = url.replace("{" + p + "}", fill[p])
        urls.append(url)
    return sorted(set(urls))


def _markup_leaks(client: TestClient, urls: list[str]) -> tuple[list[str], int]:
    """URLs whose SUCCESS HTML response carries an injected marker verbatim, and how many
    responses were actually scored (a non-success is never scored — see the module docstring)."""
    leaks: list[str] = []
    scored = 0
    for url in urls:
        resp = client.get(url)
        if resp.status_code >= 400:
            continue
        if "html" not in resp.headers.get("content-type", ""):
            continue  # a JSON payload carrying the raw string is correct; the DOM leg covers it
        # Counted only for HTML. Counting every success would let the floor be satisfied by the
        # JSON APIs alone, so a tree whose every PAGE had stopped rendering would still pass it.
        scored += 1
        if RAW_TAG in resp.text or ROW_BREAK in resp.text:
            leaks.append(url)
    return leaks, scored


def test_no_page_renders_operator_content_as_markup() -> None:
    app, client, key = _loaded(_poisoned(RAW_TAG, ROW_BREAK))
    urls = _get_urls(app, key, skip_prefix="/export")
    leaks, scored = _markup_leaks(client, urls)
    assert not leaks, f"operator content rendered as markup on: {leaks}"
    # Floor: the app serves dozens of GET routes; a collapsed enumerator must not pass silently.
    assert scored >= 30, f"census scored only {scored} responses — the enumerator is broken"


def test_the_page_census_has_teeth() -> None:
    """Break the REAL escape helper on a real page module; the census must go red BY NAME.

    ``analysis.py`` binds ``_e`` with a ``from … import`` at import time, so the patch goes on
    the CONSUMING module — the per-call-site rule this repo has hit repeatedly.
    """
    app, client, key = _loaded(_poisoned(RAW_TAG, ROW_BREAK))
    urls = _get_urls(app, key, skip_prefix="/export")
    target = f"/analysis/{key}"
    assert target in urls, "the per-schedule analysis page left the computed route set"

    clean, _ = _markup_leaks(client, [target])
    assert not clean, "precondition: the page is escaped before the mutation"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(analysis_mod, "_e", lambda text: str(text))
        broken, scored = _markup_leaks(client, [target])
    assert scored == 1
    assert broken == [target], "the census cannot see an unescaped activity name — it is blind"


def _corrupt_archives(client: TestClient, urls: list[str]) -> tuple[list[str], int]:
    """Export URLs whose archive contains an XML part that will not parse, and how many
    archives were EXAMINED.

    ``scored`` counts every archive opened, corrupt ones included. Counting only the
    well-formed ones would make a corruption shrink the population, so the floor assertion
    would fire first and report "the enumerator is broken" for a tree whose real defect is an
    unescaped writer — a red for the wrong reason, which this repo does not count as a red.
    """
    corrupt: list[str] = []
    scored = 0
    for url in urls:
        resp = client.get(url)
        if resp.status_code >= 400:
            continue
        try:
            archive = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:  # pragma: no cover - a non-archive export
            continue
        scored += 1
        for part in archive.namelist():
            if not part.endswith((".xml", ".rels")):
                continue
            try:
                ET.fromstring(archive.read(part))
            except ET.ParseError:
                corrupt.append(url)
                break
    return corrupt, scored


def _export_urls(app: Any, key: str) -> list[str]:
    """BOTH shipped formats. `reports/docx.py` has its own `_esc`, so an xlsx-only census leaves
    the docx writer unguarded — and its teeth test still passes off the xlsx corruption, which is
    exactly how a half-covered guard reads as a whole one."""
    return _get_urls(app, key, prefix="/export", fmt="xlsx") + _get_urls(
        app, key, prefix="/export", fmt="docx"
    )


def test_every_export_archive_stays_well_formed_under_a_hostile_name() -> None:
    app, client, key = _loaded(_poisoned(XML_HOSTILE))
    urls = _export_urls(app, key)
    corrupt, scored = _corrupt_archives(client, urls)
    assert not corrupt, f"export archives are not well-formed XML: {corrupt}"
    assert scored >= 30, f"only {scored} archives scored — the export enumerator is broken"


def test_the_export_census_has_teeth() -> None:
    """Neuter the writers' XML escaping; the census must report corrupt archives."""
    app, client, key = _loaded(_poisoned(XML_HOSTILE))
    urls = _export_urls(app, key)

    clean, scored = _corrupt_archives(client, urls)
    assert not clean, "precondition: every archive parses before the mutation"
    assert scored >= 30, f"only {scored} archives scored — the export enumerator is broken"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(xlsx_mod, "_esc", lambda value: value)
        mp.setattr(docx_mod, "_esc", lambda value: value)
        corrupt, _ = _corrupt_archives(client, urls)
    assert corrupt, "the census cannot see an unescaped XML writer — it is blind"
    # Both writers, named: an xlsx-only population would satisfy the line above while the docx
    # writer went unwatched.
    assert any("/xlsx/" in u for u in corrupt), "the census never reaches reports/xlsx.py"
    assert any("/docx/" in u for u in corrupt), "the census never reaches reports/docx.py"
