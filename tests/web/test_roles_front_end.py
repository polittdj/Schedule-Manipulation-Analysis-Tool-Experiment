"""Role-selection front page (v4 F4, ADR-0255).

The role is a curated ENTRY POINT only — the pins here enforce exactly that contract:
the picker renders all five roles + "Show everything"; picking persists, is fail-soft on an
unknown id, and is cleared by wipe; the active role gets a Start-here strip + a nav highlight
while EVERY chapter stays rendered (emphasis, never hiding); a clean import lands on the
role's page while any error/skip still lands on the dashboard (disclosure outranks the role
landing); and no role reproduces the pre-F4 behavior exactly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schedule_forensics.web.app import _ROLES, SessionState, create_app

# carries a project_title AND a status date so a clean ingest raises NO advisory notice (both
# the no-title and the mtime-tiebreak notices gate the role landing — audit ROLES-1/ADR-0256 —
# exercised by the dedicated test below)
_SCH_JSON = (
    '{"schema_version":"2.7.0","name":"X","project_title":"Program X",'
    '"project_start":"2026-01-05T08:00:00","status_date":"2026-02-02T08:00:00",'
    '"tasks":[{"unique_id":1,"name":"A","duration_minutes":480}],"relationships":[]}'
)
_SCH_JSON_UNTITLED = (
    '{"schema_version":"2.7.0","name":"N","project_start":"2026-01-05T08:00:00",'
    '"tasks":[{"unique_id":1,"name":"A","duration_minutes":480}],"relationships":[]}'
)


def _client() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_picker_renders_all_roles_plus_show_everything() -> None:
    _st, c = _client()
    h = c.get("/").text
    for r in _ROLES:
        assert r.label in h
    assert "Show everything" in h
    assert "Nothing is hidden" in h or "no number changes" in h  # the contract, stated on-page


def test_role_persists_shows_start_here_and_highlights_nav() -> None:
    st, c = _client()
    assert c.post("/role", data={"role": "pm"}, follow_redirects=False).status_code == 303
    assert st.role == "pm"
    h = c.get("/").text
    assert "aria-pressed=true" in h  # the active pill
    assert "Start here" in h and "/portfolio" in h and "/margin" in h  # the PM cards
    assert "role-hl" in h  # nav emphasis present
    # EMPHASIS ONLY: every chapter stays rendered — e.g. pages outside the PM set
    for still_there in ("/path", "/standards", "/help", "/cei"):
        assert still_there in h


def test_unknown_role_is_failsoft_and_clear_and_wipe_reset() -> None:
    st, c = _client()
    c.post("/role", data={"role": "analyst"}, follow_redirects=False)
    c.post("/role", data={"role": "not-a-role"}, follow_redirects=False)
    assert st.role == "analyst"  # unknown id ignored, never wipes the pick
    c.post("/role", data={"role": ""}, follow_redirects=False)
    assert st.role is None  # "Show everything"
    st.role = "auditor"
    c.post("/session/wipe", follow_redirects=False)
    assert st.role is None  # wipe returns to the un-roled console


def test_analysis_card_skipped_until_a_schedule_is_loaded() -> None:
    _st, c = _client()
    c.post("/role", data={"role": "analyst"}, follow_redirects=False)
    strip = c.get("/").text.split("class=start-strip", 1)[1]
    # @analysis unresolvable when empty — skipped, no dead link (the strip's first card is /trend)
    assert "/analysis/" not in strip.split("</div>", 1)[0]
    c.post("/upload", files={"files": ("x.json", _SCH_JSON.encode(), "application/json")})
    strip2 = c.get("/").text.split("class=start-strip", 1)[1]
    assert "/analysis/" in strip2.split("</div>", 1)[0]  # resolves once a schedule exists


def test_clean_upload_lands_on_the_role_page_and_default_is_preserved() -> None:
    st, c = _client()
    st.role = "pm"
    up = c.post(
        "/upload",
        files={"files": ("x.json", _SCH_JSON.encode(), "application/json")},
        follow_redirects=False,
    )
    assert up.status_code == 303 and up.headers["location"] == "/portfolio"
    # no role -> the pre-F4 behavior byte-for-byte: a single clean file opens its report
    st.role = None
    up2 = c.post(
        "/upload",
        files={"files": ("y.json", _SCH_JSON.replace('"X"', '"Y"').encode(), "application/json")},
        follow_redirects=False,
    )
    assert up2.headers["location"] == "/analysis/y"
    # the analyst role inherits the default landing (landing=None)
    st.role = "analyst"
    up3 = c.post(
        "/upload",
        files={"files": ("z.json", _SCH_JSON.replace('"X"', '"Z"').encode(), "application/json")},
        follow_redirects=False,
    )
    assert up3.headers["location"] == "/analysis/z"


def test_advisory_notices_also_gate_the_role_landing() -> None:
    # audit ROLES-1 (ADR-0256): notices render only on the dashboard flash, so a noticed ingest
    # must not be whisked away to a role landing. The pre-F4 fallthrough (single clean file ->
    # its /analysis report) is deliberately preserved — only the NEW role redirect is gated.
    st, c = _client()
    st.role = "pm"
    up = c.post(
        "/upload",
        files={"files": ("n.json", _SCH_JSON_UNTITLED.encode(), "application/json")},
        follow_redirects=False,
    )
    assert up.headers["location"] == "/analysis/n"  # not /portfolio — the notice held it back
    assert st.flash is not None and any("no project title" in n for n in st.flash.notices)


def test_errors_still_land_on_the_dashboard_despite_a_role() -> None:
    # disclosure outranks the role landing: an ingest with a rejected file goes to the dashboard
    # so the manifest is seen, even when a role with a landing page is active.
    st, c = _client()
    st.role = "pm"
    up = c.post(
        "/upload",
        files=[
            ("files", ("good.json", _SCH_JSON.encode(), "application/json")),
            ("files", ("bad.json", b"{not json", "application/json")),
        ],
        follow_redirects=False,
    )
    assert up.status_code == 303 and up.headers["location"] == "/"
