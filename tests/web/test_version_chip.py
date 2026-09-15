"""Every page states the installed build (OR-18, ADR-0494).

Operator directive 2026-09-15: *"add at the top of the launch page the version number of the
installed program so that we don't have to go through so much effort to tell if the correct
version has been uploaded to my computer"* — and, agreed the same day, *"the same chip in the
global header so every page and every screenshot pins the build."* OR-17 had to establish the
installed build from the WORDING of a screenshot because no page carried a version.

Pinned here: the Boot Screen (``/launch``, outside the story chrome) carries the version as the
first thing under the compliance chrome (after the CUI bar and the drawer, before the boot stage);
every chrome page carries it in the header beside the brand; both read the version at RENDER time
through ``chrome.tool_version`` — never a literal — and both are ``data-no-i18n`` so the DOM
translator never rewrites the number. Red first: the pristine ``/launch`` and ``/`` carry no
version anywhere in their visible text.
"""

from __future__ import annotations

import re
from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.chrome as chrome
from schedule_forensics.web.app import SessionState, create_app

CHIP = re.compile(
    r"<(div|span) class=(boot-version|brand-ver) data-tool-version data-no-i18n[^>]*>([^<]*)</"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _chips(page: str) -> list[tuple[str, str]]:
    return [(m.group(2), m.group(3)) for m in CHIP.finditer(page)]


def test_the_boot_screen_states_the_build_first_under_the_compliance_chrome(
    client: TestClient,
) -> None:
    page = client.get("/launch").text
    assert _chips(page) == [("boot-version", version("schedule-forensics"))]
    chip_at = page.index("class=boot-version")
    assert page.index('class="cui-banner') < chip_at  # the CUI bar stays first (design system §6)
    stage_at = page.index("<div id=sfBoot>")
    assert stage_at > chip_at  # before the boot stage: the top of the page
    assert "boot-version" not in page[stage_at:]  # exactly once, at the top


def test_every_chrome_page_states_the_build_in_the_header(client: TestClient) -> None:
    for path in ("/", "/settings", "/help"):
        page = client.get(path).text
        header = page[page.index("<header") : page.index("</header>")]
        assert _chips(header) == [("brand-ver", version("schedule-forensics"))], path
        assert "</h1>" in header and header.index("</h1>") < header.index("class=brand-ver"), path


def test_the_chip_is_read_at_render_time_never_a_literal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hard-coded version would pass every equality pin at the version it was written for; a
    probe value proves both surfaces read the installed metadata through the accessor."""
    monkeypatch.setattr(chrome, "_ASSET_VERSION", "9.9.9-probe")
    assert _chips(client.get("/launch").text) == [("boot-version", "9.9.9-probe")]
    assert _chips(client.get("/").text) == [("brand-ver", "9.9.9-probe")]
    # the settings status chip (ADR-0493) keeps its own binding: the page still states a version
    assert "data-tool-version" in client.get("/settings").text


def test_the_chip_is_never_translated_and_the_label_is_css_not_text(client: TestClient) -> None:
    """The element's TEXT is the bare version (so every pin and every screenshot reads the same
    digits); the visible "BUILD" label is CSS-generated, and the element opts out of translation."""
    from pathlib import Path

    import schedule_forensics.web as web

    static = Path(web.__file__).parent / "static"
    assert '.brand-ver::before{content:"BUILD "}' in (static / "base.css").read_text("utf-8")
    assert '.boot-version::before { content: "BUILD "; }' in (static / "launch.css").read_text(
        "utf-8"
    )
    for path in ("/launch", "/"):
        page = client.get(path).text
        assert "data-tool-version data-no-i18n" in page, path
