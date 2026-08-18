"""Every route must survive text that ``str.isdigit()`` accepts and ``int()`` rejects.

``str.isdigit()`` is **True** for superscripts (``"²"``), Arabic-Indic digits (``"٣"``)
and circled forms (``"①"``) — while ``int()`` raises ``ValueError`` on all of them. So an
``isdigit()``-gated conversion is not a guard: it lets the value through and then crashes. Typing
a superscript into an ordinary form field answered **500** on 12 routes across 5 code sites.

The population is COMPUTED from the live app — every ``APIRoute``'s every declared parameter —
never a hand-maintained list, because this class hides in whichever field nobody thought to fuzz.
That is not hypothetical here: fuzzing only the routes a coverage census flagged as having no
adverse test found **6**; fuzzing every field of every route found **12**.

The tool's own answer already existed at ``sra_grid_save``'s ``_uid`` helper, whose comment reads
*"int() directly (not isdigit(), which admits values int() rejects — '--5', '²', … — and would
500 the endpoint)"*. Five other sites never got the memo; this guard is what makes that permanent.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.web.app import SessionState, create_app

from .test_ask_driving_facts_scope import EXAMPLE

#: Every value here MUST satisfy ``str.isdigit()`` AND make ``int()`` raise (both asserted below).
#: Arabic-Indic digits are deliberately ABSENT: they are ``isdecimal()``-true and ``int()`` parses
#: them fine, so they are valid input, not a crash vector.
UNICODE_DIGITS = ["²", "²²", "①", "²³", "¹⁰", "⑨"]


def test_the_probe_values_really_are_isdigit_true() -> None:
    """Guard the guard: if these stopped satisfying ``isdigit()`` the sweep below would pass
    vacuously, never reaching the conversion it exists to exercise."""
    for value in UNICODE_DIGITS:
        assert value.isdigit(), f"{value!r} must be isdigit()-true to exercise the gate"
        with pytest.raises(ValueError):
            int(value)


def _client() -> tuple[TestClient, object]:
    st = SessionState()
    st.schedules["v0"] = parse_json_text(EXAMPLE.read_text(encoding="utf-8"))
    app = create_app(st)
    return TestClient(app, raise_server_exceptions=True), app


def _field_slots() -> list[tuple[str, str, str]]:
    """(method, path, field) for every declared parameter of every route — computed, not listed."""
    _, app = _client()
    slots = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for name in inspect.signature(route.endpoint).parameters:
            for method in sorted(route.methods or set()):
                if method != "HEAD":
                    slots.append((method, route.path, name))
    return slots


def test_the_sweep_has_a_population() -> None:
    slots = _field_slots()
    assert len(slots) > 200, f"only {len(slots)} field slots — the sweep lost its population"


def test_no_route_raises_on_unicode_digit_input() -> None:
    client, _app = _client()
    crashes: list[str] = []
    for method, path, field in _field_slots():
        url = path.replace("{fmt}", "xlsx").replace("{name}", "v0").replace("{key}", "v0")
        for value in UNICODE_DIGITS:
            try:
                if method == "POST":
                    client.post(url, data={field: value})
                else:
                    client.get(url, params={field: value})
            except Exception as exc:  # an unhandled exception IS the defect
                crashes.append(
                    f"{method} {path} [{field}={value!r}] -> {type(exc).__name__}: {exc}"
                )
                break
    assert not crashes, "routes raised on isdigit()-true, int()-invalid input:\n" + "\n".join(
        f"  {c}" for c in crashes
    )


def test_the_fix_narrowed_nothing_that_int_accepts() -> None:
    """The first version of this fix was ``isascii() and isdigit()`` — and it was WRONG in the
    other direction: across all 788 single-character numeric code points that predicate disagrees
    with ``int()`` on 650, so Arabic-Indic digits (which ``int()`` parses fine) would have silently
    stopped resolving. ``isdecimal()`` disagrees on zero. This pins the non-narrowing half, which
    a crash-only test cannot see."""
    from schedule_forensics.web.app import _parse_uid

    assert _parse_uid("3") == 3
    assert _parse_uid("٣") == 3, "an int()-parseable digit form must still resolve"
    assert _parse_uid("١٢") == 12
    assert _parse_uid("²") is None, "an int()-invalid digit form must resolve to None, not raise"
    assert _parse_uid("abc") is None
    assert _parse_uid("") is None
