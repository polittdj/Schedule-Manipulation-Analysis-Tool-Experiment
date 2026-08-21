"""Dropping SEVERAL folders at once loads each as its own Project — in a REAL browser.

Chromium's directory-picker dialog cannot multi-select (``webkitdirectory`` overrides
``multiple`` — WICG entries-api #24), so drag-and-drop is THE way to select several folders at
one time. Before this feature the drop handler forwarded ``dataTransfer.files`` untraversed: a
dropped folder surfaced as an unreadable bare-directory File and was reported with the misleading
"online-only in OneDrive" hint, and its schedules never loaded at all.

This module drives the REAL ``home.js`` end to end: a synthesized drop whose
``DataTransferItem.webkitGetAsEntry`` is patched to return fake FileSystemEntry trees (the only
part a test cannot manufacture — entry objects require an OS drag), through home.js's traversal,
its pre-read, the real ``fetch('/upload')``, and the server's per-folder grouping, asserted on the
live ``SessionState``. The Apollo reader deliberately yields its entries in 100-max-style batches
(one per call, then empty) to pin Chrome's readEntries drain contract.

Observed RED on the pre-feature tree: the fallback uploaded only the loose file — one Project,
no Apollo, no Artemis.

Skips only when the playwright PACKAGE is absent; browser resolution is
``tests/web/browser_chrome.py``'s decision (ADR-0406/0418).
"""

from __future__ import annotations

import socket
import threading
import time
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


@pytest.fixture(scope="module")
def served() -> Any:
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


#: Build the fake entry trees + the drop, in-page. Fake entries implement exactly the surface
#: home.js may touch: isDirectory/isFile/name, createReader().readEntries(ok, err) (BATCHED —
#: one entry per call, empty batch to finish, per Chrome's 100-entry contract), and
#: file(ok, err). webkitGetAsEntry is keyed by each item's placeholder-File NAME, not object
#: identity — DataTransferItemList wrappers are not guaranteed stable across reads.
_DROP_JS = """([apollo1, apollo2, artemis1, loose]) => {
  const enc = (s) => new File([s], 'x.xml', { type: 'text/xml', lastModified: 1700000000000 });
  const fileEntry = (name, content, mtime) => ({
    isFile: true, isDirectory: false, name,
    file: (ok) => ok(new File([content], name, { type: 'text/xml', lastModified: mtime })),
  });
  const dirEntry = (name, children) => {
    return {
      isFile: false, isDirectory: true, name,
      createReader: () => {
        let i = 0;  // fresh cursor per reader, batches of ONE, then the empty batch
        return { readEntries: (ok) => { ok(i < children.length ? [children[i++]] : []); } };
      },
    };
  };
  const roots = {
    Apollo: dirEntry('Apollo', [
      fileEntry('a1.xml', apollo1, 1700000000000),
      dirEntry('2024', [fileEntry('a2.xml', apollo2, 1700086400000)]),
    ]),
    Artemis: dirEntry('Artemis', [fileEntry('b1.xml', artemis1, 1700172800000)]),
    'loose.xml': fileEntry('loose.xml', loose, 1700259200000),
  };
  const dt = new DataTransfer();
  dt.items.add(new File(['x'], 'Apollo'));      // placeholder: a real folder drop exposes an
  dt.items.add(new File(['x'], 'Artemis'));     // unreadable bare-directory File here
  dt.items.add(new File([loose], 'loose.xml', { type: 'text/xml' }));
  DataTransferItem.prototype.webkitGetAsEntry = function () {
    const f = this.getAsFile();
    return (f && roots[f.name]) || null;
  };
  window.dispatchEvent(
    new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
}"""


def test_dropping_two_folders_and_a_loose_file_loads_three_projects(served: Any) -> None:
    from playwright.sync_api import sync_playwright

    st, url = served
    payload = [
        _mspdi("ignored-a1", "2025-01-10T00:00:00"),
        _mspdi("ignored-a2", "2025-02-10T00:00:00"),
        _mspdi("ignored-b1", "2025-01-15T00:00:00"),
        _mspdi("Loosey", "2025-01-20T00:00:00"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(url + "/", wait_until="domcontentloaded")
        page.evaluate(_DROP_JS, payload)
        # the upload is a fetch + client-side navigation; assert on the LIVE session state
        deadline = time.time() + 15
        while time.time() < deadline and len(st.schedules) < 4:
            time.sleep(0.2)
        browser.close()

    assert len(st.schedules) == 4, f"loaded keys: {list(st.schedules)}"
    projects = {proj.title: proj for proj in st.projects()}
    assert set(projects) == {"Apollo", "Artemis", "Loosey"}, sorted(projects)
    apollo = projects["Apollo"]
    assert apollo.origin == "folder"
    # BOTH Apollo files — the nested 2024/a2.xml proves recursion, and its arrival proves the
    # batched readEntries drain (the reader hands one entry per call)
    assert len(apollo.versions) == 2
    assert projects["Artemis"].origin == "folder"
    assert len(projects["Artemis"].versions) == 1
    # the loose dropped FILE stays loose: grouped by its own document Title, not by any folder
    assert projects["Loosey"].origin == "title"
