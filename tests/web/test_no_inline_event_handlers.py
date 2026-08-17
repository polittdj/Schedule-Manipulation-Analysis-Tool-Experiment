"""JS-01 (audit 2026-08-16): the strict CSP forbids inline handlers, so none may be emitted.

The app serves ``script-src 'self'`` with no ``'unsafe-inline'`` (Law 1's air-gap CSP). Any
inline ``on*=`` attribute in server-rendered HTML is therefore **dead code that looks like a
working control** — and one was shipped: the Acumen-Fuse parity-mode checkbox on ``/analysis``
carried ``onchange="this.form.submit()"`` inside a form with **no submit button**, so it had no
other way to submit.

Measured in Chromium (not inferred from the CSP text): clicking the control left the URL
unchanged, left the page state unchanged, left the SERVER state unchanged on reload, and the
browser logged *"Refused to execute inline event handler because it violates the following
Content Security Policy directive: script-src 'self'"*. The operator could not switch between
the pure-logic and Acumen-parity DCMA views at all — on a forensic tool where that toggle
changes reported numbers, a control that silently does nothing is worse than an absent one.

ADR-0268 had already built the cure — ``chrome.js`` delegates these events by data attribute,
and its own header says it exists *because* the CSP forbids inline handlers. Its selector was
``select[data-sf-autosubmit]``, so a checkbox fell straight through it.

These are census guards: they fail on ANY page, not just the one that regressed, because the
whole view layer generates HTML from this one package.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

VIEW_LAYER = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web"
EXAMPLE = VIEW_LAYER / "examples/house_build.json"

#: Any HTML event attribute. Deliberately broad: the defect was ``onchange``, but ``onclick``
#: and friends are equally dead under this CSP, and a guard that names only the one that broke
#: is a guard that waits for the next one.
_INLINE_HANDLER = re.compile(r"\son(?:change|click|input|submit|load|key\w+|focus|blur|mouse\w+)=")


def _view_modules() -> list[Path]:
    return sorted(p for p in VIEW_LAYER.glob("*.py") if p.name != "__init__.py")


def test_no_view_module_emits_an_inline_event_handler() -> None:
    """Source census over the whole view layer — every page's HTML is generated here.

    Scanning source rather than driving 137 routes is what makes this exhaustive: a route this
    test never thought to visit still cannot smuggle a handler past it.
    """
    offenders: list[str] = []
    for path in _view_modules():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _INLINE_HANDLER.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()[:110]}")
    assert not offenders, (
        "inline event handlers are dead under `script-src 'self'` — delegate via chrome.js's "
        "data-sf-* attributes (ADR-0268) instead:\n" + "\n".join(offenders)
    )


def test_the_served_analysis_page_carries_no_inline_handler() -> None:
    """The rendered check, because source and served HTML have disagreed in this repo before."""
    client = TestClient(create_app(SessionState()))
    client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,
    )
    html = client.get("/analysis/plan").text
    assert html
    found = _INLINE_HANDLER.findall(html)
    assert not found, f"/analysis served {len(found)} inline handler(s): {found[:5]}"


def test_the_parity_toggle_is_delegated_and_submittable() -> None:
    """The specific control: delegated for JS users, and submittable WITHOUT any JS at all.

    Both halves matter. ``data-sf-autosubmit`` restores the one-click UX; the real submit
    button means the toggle still works if the delegation ever breaks again — which is exactly
    the failure mode that produced JS-01, so the fix must not depend solely on scripting.
    """
    client = TestClient(create_app(SessionState()))
    client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,
    )
    html = client.get("/analysis/plan").text
    form = re.search(r'<form[^>]*action="/dcma/scope".*?</form>', html, re.S)
    assert form, "the parity form is not served at all"
    body = form.group(0)
    assert "name=parity" in body and "data-sf-autosubmit" in body
    assert re.search(r"<button[^>]*type=submit", body), (
        "the parity form has no submit button — with JS blocked or broken there is no way to "
        "apply the toggle, which is the JS-01 dead-end all over again"
    )


def test_chrome_js_delegation_covers_inputs_not_only_selects() -> None:
    """The one-word cause: the delegation matched ``select[...]``, so a checkbox fell through.

    Pinned as a JS source contract (the repo's idiom for its vendored, build-step-free JS).
    """
    js = (VIEW_LAYER / "static/chrome.js").read_text(encoding="utf-8")
    assert '"[data-sf-autosubmit]"' in js, (
        "chrome.js must delegate autosubmit for ANY element, not just <select> — a checkbox "
        "matched by `select[data-sf-autosubmit]` is a dead control"
    )


@pytest.mark.parametrize("attr", ["data-sf-autosubmit", "data-sf-navselect", "data-sf-confirm"])
def test_the_delegated_attributes_are_still_the_contract(attr: str) -> None:
    """ADR-0268's vocabulary is load-bearing for every page; pin it so a rename is deliberate."""
    js = (VIEW_LAYER / "static/chrome.js").read_text(encoding="utf-8")
    assert attr in js
