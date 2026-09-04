"""WP5 build B, RENDERED: a parent folder that holds several project folders is ASKED about,
never guessed — driven end to end in a REAL browser on both gestures.

The picker path uses REAL platform objects: Playwright's ``set_input_files`` accepts a directory
for a ``webkitdirectory`` input (measured here on 1.62: the FileList carries genuine
``webkitRelativePath`` values rooted at the picked folder's own name), so nothing about the
folder pick is faked. The drop path reuses ``test_multi_folder_drop_browser.py``'s fake-entry
machinery (entry objects are the one thing a test cannot mint without an OS drag) to prove the
SAME question fires for a single dropped root and stays silent for two — ADR-0437's contract
(N dropped folders → N Projects) is untouched.

Every assertion is on the LIVE ``SessionState`` behind the served app plus the rendered ask;
the per-test server keeps each scenario's population clean.

Observed RED on the pristine tree (2026-09-04): the ask never appeared (``#dzAsk`` absent), the
parent pick uploaded straight away as ONE Project — every build-B test below failed by name.

Skips only when the playwright PACKAGE is absent; browser resolution is
``tests/web/browser_chrome.py``'s decision (ADR-0406/0418).
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str, status: str) -> str:
    return (
        f"<Project {_NS}><Title>{title}</Title><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate>{_TASK}</Project>"
    )


@pytest.fixture
def served() -> Any:
    """A fresh SessionState + uvicorn per test — each scenario asserts on its own population."""
    import uvicorn

    from schedule_forensics.web.app import SessionState, create_app

    st = SessionState()
    app = create_app(st)
    port_sock = socket.socket()
    port_sock.bind(("127.0.0.1", 0))
    port = int(port_sock.getsockname()[1])
    port_sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield st, f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """``Programs/`` holds two project folders (one nested a level deeper), one schedule directly
    inside it and one non-schedule file; ``Solo/`` holds one sub-folder only (unambiguous)."""
    root = tmp_path_factory.mktemp("folders")
    files = {
        "Programs/Apollo/a1.xml": _mspdi("ignored-a1", "2025-01-10T00:00:00"),
        "Programs/Apollo/2024/a2.xml": _mspdi("ignored-a2", "2025-02-10T00:00:00"),
        "Programs/Artemis/b1.xml": _mspdi("ignored-b1", "2025-01-15T00:00:00"),
        "Programs/top.xml": _mspdi("ignored-top", "2025-03-01T00:00:00"),
        "Programs/readme.txt": "not a schedule",
        "Solo/s1.xml": _mspdi("ignored-s1", "2025-01-10T00:00:00"),
        "Solo/old/s0.xml": _mspdi("ignored-s0", "2024-12-10T00:00:00"),
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def _until(pred: Callable[[], bool], seconds: float = 15.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(0.15)
    return pred()


def _pick_parent(page: Any, corpus: Path) -> None:
    """Pick ``Programs`` through the REAL folder input (genuine webkitRelativePath values) and
    wait for the question."""
    page.set_input_files("#folderInput", str(corpus / "Programs"))
    page.locator("#dzAsk").wait_for(state="visible", timeout=10_000)


def test_picking_a_parent_folder_asks_before_loading_anything(served: Any, corpus: Path) -> None:
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url + "/", wait_until="domcontentloaded")
        _pick_parent(page, corpus)
        title = page.locator("#dzAskTitle").inner_text()
        items = page.locator("#dzAskList li").all_inner_texts()
        split = page.locator("#dzAskSplit").inner_text()
        one = page.locator("#dzAskOne").inner_text()
        note = page.locator("#dzAskNote").inner_text()
        focused = page.evaluate("document.activeElement && document.activeElement.id")
        browser.close()
    # nothing was uploaded before the operator answered
    assert st.schedules == {}, list(st.schedules)
    assert "Programs" in title and "2 sub-folders" in title, title
    # sub-folders BY NAME (the FileList arrives in filesystem-traversal order, which put Artemis
    # first on this box), schedules only (readme.txt never counts); the nested 2024/a2 is counted
    assert items == ["Apollo — 2 schedules", "Artemis — 1 schedule"], items
    assert split.startswith("2 Projects"), split
    assert "One Project" in one and "4 versions" in one, one
    # the schedule directly under the parent is named — it stays the parent's own Project
    assert "top.xml" not in note and "1 schedule directly under" in note and "Programs" in note
    assert focused == "dzAskSplit"  # keyboard users land on a real choice, not on nothing
    assert errors == []


def test_choosing_one_per_subfolder_loads_sibling_projects(served: Any, corpus: Path) -> None:
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        _pick_parent(page, corpus)
        page.click("#dzAskSplit")
        assert _until(lambda: len(st.schedules) >= 4), list(st.schedules)
        browser.close()
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Apollo", "Artemis", "Programs"}, sorted(projects)
    assert all(proj.origin == "folder" for proj in projects.values())
    assert len(projects["Apollo"].versions) == 2  # a1 + the nested 2024/a2
    assert len(projects["Artemis"].versions) == 1
    assert len(projects["Programs"].versions) == 1  # top.xml keeps the parent as its Project
    assert len(st.populations()) == 3


def test_choosing_one_project_keeps_the_parent_as_the_project(served: Any, corpus: Path) -> None:
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        _pick_parent(page, corpus)
        page.click("#dzAskOne")
        assert _until(lambda: len(st.schedules) >= 4), list(st.schedules)
        browser.close()
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Programs"}, sorted(projects)
    assert projects["Programs"].origin == "folder"
    assert len(projects["Programs"].versions) == 4
    assert len(st.populations()) == 1


def test_cancel_loads_nothing_and_clears_the_pick(served: Any, corpus: Path) -> None:
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        _pick_parent(page, corpus)
        page.click("#dzAskCancel")
        page.locator("#dzAsk").wait_for(state="hidden", timeout=5_000)
        time.sleep(0.6)  # a grace window in which a wrongly-started upload would land
        pending = page.evaluate("document.getElementById('folderInput').files.length")
        browser.close()
    assert st.schedules == {}, list(st.schedules)
    assert pending == 0  # the same folder can be picked again


def test_a_folder_with_one_subfolder_loads_without_asking(served: Any, corpus: Path) -> None:
    """One sub-folder is not ambiguous (ADR-0437: the folder is one Project) — the pick uploads
    straight away and the question never renders."""
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        # flag the ask the moment it would become visible — a timing-proof "never shown" oracle
        page.evaluate(
            """() => { window.__askShown = false;
              const box = document.getElementById('dzAsk');
              new MutationObserver(() => { if (!box.hidden) window.__askShown = true; })
                .observe(box, { attributes: true, attributeFilter: ['hidden'] }); }"""
        )
        page.set_input_files("#folderInput", str(corpus / "Solo"))
        assert _until(lambda: len(st.schedules) >= 2), list(st.schedules)
        shown = False
        try:  # the upload navigates the page; the flag is read only if the page is still here
            shown = bool(page.evaluate("window.__askShown"))
        except Exception:  # the upload's navigation tore the context down: nothing was shown
            shown = False
        browser.close()
    assert shown is False
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Solo"} and len(projects["Solo"].versions) == 2


#: Fake entry trees for the DROP path (see test_multi_folder_drop_browser.py for the contract).
#: ``roots`` names the top-level entries the synthetic drop exposes.
_DROP_JS = """([mode, a1, a2, b1]) => {
  const fileEntry = (name, content, mtime) => ({
    isFile: true, isDirectory: false, name,
    file: (ok) => ok(new File([content], name, { type: 'text/xml', lastModified: mtime })),
  });
  const dirEntry = (name, children) => ({
    isFile: false, isDirectory: true, name,
    createReader: () => { let i = 0;
      return { readEntries: (ok) => { ok(i < children.length ? [children[i++]] : []); } }; },
  });
  const apollo = dirEntry('Apollo', [fileEntry('a1.xml', a1, 1700000000000),
    dirEntry('2024', [fileEntry('a2.xml', a2, 1700086400000)])]);
  const artemis = dirEntry('Artemis', [fileEntry('b1.xml', b1, 1700172800000)]);
  const roots = mode === 'parent' ? { Programs: dirEntry('Programs', [apollo, artemis]) }
                                  : { Apollo: apollo, Artemis: artemis };
  const dt = new DataTransfer();
  for (const name of Object.keys(roots)) dt.items.add(new File(['x'], name));
  DataTransferItem.prototype.webkitGetAsEntry = function () {
    const f = this.getAsFile();
    return (f && roots[f.name]) || null;
  };
  window.dispatchEvent(
    new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
}"""

_PAYLOAD = [
    _mspdi("ignored-a1", "2025-01-10T00:00:00"),
    _mspdi("ignored-a2", "2025-02-10T00:00:00"),
    _mspdi("ignored-b1", "2025-01-15T00:00:00"),
]


def test_dropping_one_parent_folder_asks_the_same_question(served: Any) -> None:
    """One dropped root spanning two project folders is the SAME ambiguity as the pick — the
    shared plan asks, and the per-sub-folder answer lands two Projects."""
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        page.evaluate(_DROP_JS, ["parent", *_PAYLOAD])
        page.locator("#dzAsk").wait_for(state="visible", timeout=10_000)
        assert st.schedules == {}
        title = page.locator("#dzAskTitle").inner_text()
        page.click("#dzAskSplit")
        assert _until(lambda: len(st.schedules) >= 3), list(st.schedules)
        browser.close()
    assert "Programs" in title
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Apollo", "Artemis"}, sorted(projects)
    assert len(projects["Apollo"].versions) == 2 and len(projects["Artemis"].versions) == 1


def test_dropping_two_folders_never_asks(served: Any) -> None:
    """ADR-0437's contract byte-for-byte: N dropped folders are N Projects, no question."""
    from playwright.sync_api import sync_playwright

    st, url = served
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        page.evaluate(
            """() => { window.__askShown = false;
              const box = document.getElementById('dzAsk');
              new MutationObserver(() => { if (!box.hidden) window.__askShown = true; })
                .observe(box, { attributes: true, attributeFilter: ['hidden'] }); }"""
        )
        page.evaluate(_DROP_JS, ["siblings", *_PAYLOAD])
        assert _until(lambda: len(st.schedules) >= 3), list(st.schedules)
        shown = False
        try:
            shown = bool(page.evaluate("window.__askShown"))
        except Exception:  # the upload's navigation tore the context down: nothing was shown
            shown = False
        browser.close()
    assert shown is False
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Apollo", "Artemis"}, sorted(projects)
