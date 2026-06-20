"""Coverage for web error/guard/render branches: empty-session guards, bad export formats, and the
counterfactual 'what-if' panel renderer across all its result shapes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.path_counterfactual import (
    GainedFloatActivity,
    PathCounterfactual,
    RevertedActivity,
)
from schedule_forensics.web.app import SessionState, _render_counterfactual, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()), raise_server_exceptions=False)


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


# --- the counterfactual panel renderer, every result shape ---------------------------------------


def test_render_counterfactual_none_is_nothing_to_revert() -> None:
    out = _render_counterfactual(None)
    assert "nothing to revert" in out


def test_render_counterfactual_changes_pulled_finish_in_with_target() -> None:
    pc = PathCounterfactual(
        prior_label="v1",
        current_label="v2",
        reverted=(
            RevertedActivity(10, "Pour slab", "duration_cut", ("duration 20d→40d restored",)),
        ),
        gained_float=(),
        actual_finish="2025-06-01",
        counterfactual_finish="2025-06-20",
        finish_delta_days=19,  # > 0 -> "later"
        target_uid=10,
        target_name="Pour slab",
        target_actual_finish="2025-06-01",
        target_counterfactual_finish="2025-06-20",
        target_delta_days=19,
    )
    out = _render_counterfactual(pc)
    assert "Pour slab" in out and "later" in out and "Target activity" in out


def test_render_counterfactual_earlier_and_no_change_deltas() -> None:
    pc = PathCounterfactual(
        prior_label="v1",
        current_label="v2",
        reverted=(RevertedActivity(5, "X", "logic_removed", ("1 link(s) removed",)),),
        gained_float=(),
        actual_finish="2025-06-10",
        counterfactual_finish="2025-06-05",
        finish_delta_days=-5,  # < 0 -> "earlier"
        target_uid=5,
        target_delta_days=0,  # == 0 -> "no change"
    )
    out = _render_counterfactual(pc)
    assert "earlier" in out and "no change" in out


def test_render_counterfactual_uncomputable_and_target_absent() -> None:
    pc = PathCounterfactual(
        prior_label="v1",
        current_label="v2",
        reverted=(RevertedActivity(5, "X", "changed", ("constraint restored",)),),
        gained_float=(),
        actual_finish="2025-06-01",
        counterfactual_finish="2025-06-01",
        finish_delta_days=0,
        target_uid=99,
        target_delta_days=None,  # target not in both networks
        uncomputable=True,
    )
    out = _render_counterfactual(pc)
    assert "unsolvable network" in out
    assert "not in both" in out.lower() or "individual impact is not shown" in out


def test_render_counterfactual_gained_float_only() -> None:
    pc = PathCounterfactual(
        prior_label="v1",
        current_label="v2",
        reverted=(),
        gained_float=(GainedFloatActivity(7, "Slack Riser"),),
        actual_finish="2025-06-01",
        counterfactual_finish="2025-06-01",
        finish_delta_days=0,
    )
    out = _render_counterfactual(pc)
    assert "Gained float" in out and "Slack Riser" in out


# --- empty-session and single-version route guards (the "load a schedule" / "<2 versions" paths) --


def test_empty_session_pages_and_apis_never_500(client: TestClient) -> None:
    pages = [
        "/forecast",
        "/scurve",
        "/curves",
        "/trend",
        "/cei",
        "/driving-path",
        "/compare",
        "/briefing",
        "/brief",
        "/path",
        "/groups",
        "/evolution",
        "/ribbon",
        "/api/cei",
        "/api/scurve",
        "/api/curves",
        "/api/trend",
        "/api/dashboard",
        "/api/forecast",
        "/api/evolution",
        "/api/group-values",
    ]
    for p in pages:
        assert client.get(p).status_code < 500, p


def test_single_version_multiversion_guards(client: TestClient) -> None:
    _upload(client, "Project5")
    # these need >=2 versions; one loaded must degrade gracefully, never 500
    for p in ("/trend", "/cei", "/compare", "/evolution", "/api/cei"):
        assert client.get(p).status_code < 500, p


def test_bad_and_empty_export_paths(client: TestClient) -> None:
    # unsupported export format -> _bad_format rejection (404/400), never 500
    assert client.get("/export/zzz/trend").status_code in (400, 404)
    # export with nothing loaded -> the not-loaded guard, never 500
    for fmt_path in ("/export/xlsx/trend", "/export/docx/brief", "/export/xlsx/forecast"):
        assert client.get(fmt_path).status_code < 500, fmt_path


# --- AI backend construction + translation helper branches ---------------------------------------


def test_local_backend_helpers_refuse_remote_endpoints() -> None:
    from schedule_forensics.ai.backend import AIConfig
    from schedule_forensics.web.app import _ollama_or_none, _openai_or_none

    remote = AIConfig(backend="ollama", endpoint="http://evil.example.com:11434")
    assert _ollama_or_none(remote) is None
    assert (
        _openai_or_none(AIConfig(backend="openai", openai_endpoint="http://evil.example.com:1234"))
        is None
    )


class _NumberedBackend:
    name = "numbered"
    is_local = True

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("numbered",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        lines = [ln for ln in prompt.splitlines() if "\t" in ln and ln[0].isdigit()]
        return "\n".join(f"{ln.split(chr(9))[0]}\t<t>{ln.split(chr(9), 1)[1]}" for ln in lines)


class _RaisingBackend(_NumberedBackend):
    def generate(self, prompt: str) -> str:
        raise RuntimeError("model died mid-generate")


def test_ai_translate_success_and_failure_paths() -> None:
    from schedule_forensics.web.app import _ai_translate

    out = _ai_translate(["Alpha", "Beta"], "es", _NumberedBackend())  # type: ignore[arg-type]
    assert out == {"Alpha": "<t>Alpha", "Beta": "<t>Beta"}
    # a backend that raises mid-generate degrades to an empty map (never propagates)
    assert _ai_translate(["Alpha"], "es", _RaisingBackend()) == {}  # type: ignore[arg-type]


def test_translate_batch_catalog_cache_and_ai_fill(monkeypatch: object) -> None:
    from schedule_forensics.web import app as appmod
    from schedule_forensics.web.app import SessionState, _translate_batch

    st = SessionState(language="es")
    st.translations[("es", "Cached Term")] = "Término en caché"
    monkeypatch.setattr(  # type: ignore[attr-defined]
        appmod, "_ai_translate", lambda need, lang, backend: {t: f"<es>{t}" for t in need}
    )
    out = _translate_batch(["Dashboard", "Cached Term", "Fresh Name"], "es", st)
    assert out["Dashboard"] == "Panel"  # catalog hit
    assert out["Cached Term"] == "Término en caché"  # session-cache hit
    assert out["Fresh Name"] == "<es>Fresh Name"  # AI-fill, now memoised
    assert st.translations[("es", "Fresh Name")] == "<es>Fresh Name"


# --- not-found + unschedulable (cyclic) report paths ---------------------------------------------


def test_missing_schedule_pages_and_exports_404(client: TestClient) -> None:
    for p in ("/analysis/nope", "/card/nope", "/wbs/nope"):
        assert client.get(p).status_code == 404, p
    for p in ("/export/xlsx/analysis/nope", "/export/xlsx/wbs/nope"):
        assert client.get(p).status_code == 404, p


def test_cyclic_schedule_renders_unschedulable_panel() -> None:
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    cyc = Schedule(
        name="cyc",
        source_file="cyc.xml",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=480),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=1, type=RelationshipType.FS),
        ),
    )
    st = SessionState()
    st.schedules["cyc"] = cyc
    c = TestClient(create_app(st), raise_server_exceptions=False)
    page = c.get("/analysis/cyc")
    assert page.status_code == 200  # degrades, never 500
    assert "cycle" in page.text.lower() or "cannot" in page.text.lower()


# --- _ai_status_note: every diagnostic branch via fake local backends ----------------------------


class _FakeProbe:
    def __init__(self, reason=None, models=()):
        self._reason = reason
        self._models = models

    def unavailable_reason(self):
        return self._reason

    def is_available(self) -> bool:
        return self._reason is None

    def list_models(self):
        return self._models


def test_ai_status_note_branches(monkeypatch: object) -> None:
    from schedule_forensics.ai.backend import AIConfig
    from schedule_forensics.web import app as appmod
    from schedule_forensics.web.app import _ai_status_note

    mp = monkeypatch  # type: ignore[assignment]
    # null/cloud backends -> no status line
    assert _ai_status_note(AIConfig(backend="null")) == ""
    # ollama down -> OFF notice with the reason + hint
    mp.setattr(appmod, "_ollama_or_none", lambda c: _FakeProbe(reason="connection refused"))  # type: ignore[attr-defined]
    off = _ai_status_note(AIConfig(backend="ollama", model="llama3.1:8b"))
    assert "Local AI is OFF" in off and "connection refused" in off
    # ollama reachable but the model isn't installed -> the pull hint
    mp.setattr(appmod, "_ollama_or_none", lambda c: _FakeProbe(models=("other:7b",)))  # type: ignore[attr-defined]
    miss = _ai_status_note(AIConfig(backend="ollama", model="llama3.1:8b"))
    assert "isn't installed" in miss
    # ollama reachable WITH the model -> ON
    mp.setattr(appmod, "_ollama_or_none", lambda c: _FakeProbe(models=("llama3.1:8b",)))  # type: ignore[attr-defined]
    assert "Local AI is ON" in _ai_status_note(AIConfig(backend="ollama", model="llama3.1:8b"))
    # openai-compatible server down -> the LM-Studio hint
    mp.setattr(appmod, "_openai_or_none", lambda c: _FakeProbe(reason="timed out"))  # type: ignore[attr-defined]
    out = _ai_status_note(AIConfig(backend="openai"))
    assert "Local AI is OFF" in out and "LM Studio" in out


# --- API + export guards under empty / single-version sessions -----------------------------------


def test_api_and_export_guards_empty_and_single(client: TestClient) -> None:
    # APIs with nothing loaded -> 4xx guards, never 500
    for p in ("/api/cei", "/api/scurve", "/api/curves", "/api/trend", "/api/forecast"):
        assert client.get(p).status_code < 500, p
    # /api/driving needs source+target params -> validation, never 500
    assert client.get("/api/driving/Project5").status_code < 500
    # exports for every kind with nothing loaded -> not-loaded guards
    for kind in ("trend", "cei", "curves", "forecast", "evolution", "brief", "briefing", "compare"):
        assert client.get(f"/export/xlsx/{kind}").status_code < 500, kind
    # single version: the >=2-version export guards
    _upload(client, "Project5")
    for kind in ("trend", "cei", "evolution", "compare"):
        assert client.get(f"/export/xlsx/{kind}").status_code < 500, kind


def _cyclic(name: str, day: int) -> object:
    """Two-task schedule with a 1<->2 logic cycle (CPM-unsolvable) but stored dates so the
    date-based views still have data. Exercises every route's CPMError degradation path."""
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    s = dt.datetime(2025, 1, day, 8, 0)
    f = dt.datetime(2025, 1, day + 1, 17, 0)
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2025, 1, 1),
        status_date=dt.datetime(2025, 1, day + 2),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480, start=s, finish=f, baseline_finish=f),
            Task(
                unique_id=2,
                name="B",
                duration_minutes=480,
                start=s,
                finish=f,
                baseline_finish=f,
                percent_complete=50.0,
            ),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=1, type=RelationshipType.FS),
        ),
    )


def test_unschedulable_two_version_session_never_500s() -> None:
    st = SessionState()
    st.target_uid = 1  # exercise the target-panel CPMError paths too
    st.schedules["v1"] = _cyclic("v1", 6)  # type: ignore[assignment]
    st.schedules["v2"] = _cyclic("v2", 10)  # type: ignore[assignment]
    c = TestClient(create_app(st), raise_server_exceptions=False)
    paths = [
        "/",
        "/analysis/v1",
        "/card/v1",
        "/wbs/v1",
        "/path",
        "/trend",
        "/cei",
        "/scurve",
        "/curves",
        "/forecast",
        "/compare",
        "/evolution",
        "/driving-path",
        "/briefing",
        "/brief",
        "/ribbon",
        "/api/analysis/v1",
        "/api/cei",
        "/api/scurve",
        "/api/curves",
        "/api/trend",
        "/api/forecast",
        "/api/evolution",
        "/api/dashboard",
        "/export/xlsx/analysis/v1",
        "/export/xlsx/wbs/v1",
        "/export/xlsx/trend",
        "/export/xlsx/cei",
        "/export/xlsx/forecast",
        "/export/xlsx/evolution",
        "/export/xlsx/brief",
        "/export/xlsx/briefing",
        "/export/xlsx/compare",
        "/export/xlsx/curves",
    ]
    for p in paths:
        assert c.get(p).status_code < 500, p


def test_every_export_kind_rejects_a_bad_format(client: TestClient) -> None:
    _upload(client, "Project5")
    _upload(client, "Project2")
    for kind in (
        "analysis/Project5",
        "wbs/Project5",
        "trend",
        "cei",
        "curves",
        "forecast",
        "evolution",
        "brief",
        "briefing",
        "compare",
        "path/Project5",
    ):
        # bad format -> 400/404; path export validates its UID params first (422) — all rejected
        assert client.get(f"/export/zzz/{kind}").status_code in (400, 404, 422), kind


def test_render_heavy_pages_with_focus_and_breakdown() -> None:
    """Drive the path/groups/forecast/evolution/driving renderers with a focus UID + a breakdown so
    their target-panel, basis-date, breakdown, and impact branches render."""
    st = SessionState()
    c = TestClient(create_app(st), raise_server_exceptions=False)
    g = Path("tests/fixtures/golden/project2_5")
    for n in ("Project5", "Project2"):
        c.post(
            "/upload",
            files={"files": (f"{n}.mspdi.xml", (g / f"{n}.mspdi.xml").read_bytes(), "text/xml")},
        )
    key = next(iter(st.schedules))
    paths = [
        "/path?target=3",
        "/path?target=4",
        f"/analysis/{key}?",
        "/groups?breakdown=WBS",
        "/groups?breakdown=Resource",
        "/groups?breakdown=Critical",
        "/groups?apply=1&field=Critical&value0=Yes&breakdown=WBS",
        "/evolution?target=3",
        "/driving-path?source=3&target=5",
        "/driving-path?source=3&target=5&secondary=10&tertiary=20",
        "/forecast",
        "/scurve",
        "/ribbon",
        "/briefing",
        "/api/driving/Project5?source=3&target=5",
        "/api/evolution?target=3",
    ]
    for p in paths:
        assert c.get(p).status_code < 500, p
    # set a session-wide target too (drives the per-page default-focus branches)
    c.post("/target", data={"target": "3"}, follow_redirects=False)
    for p in ("/trend", "/cei", "/evolution", f"/analysis/{key}", f"/card/{key}", f"/wbs/{key}"):
        assert c.get(p).status_code < 500, p


def _sparse(name: str) -> object:
    """A schedule whose tasks carry NO stored start/finish/baseline dates and no status date,
    forcing the 'missing data' fallback branches in the date-based renderers/forecasts."""
    import datetime as dt

    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2025, 1, 1),
        status_date=None,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=960),
            Task(unique_id=3, name="WBS", duration_minutes=0, is_summary=True),
        ),
        relationships=(),
    )


def test_sparse_no_date_schedules_exercise_fallback_branches() -> None:
    st = SessionState()
    st.target_uid = 1
    st.schedules["s1"] = _sparse("s1")  # type: ignore[assignment]
    st.schedules["s2"] = _sparse("s2")  # type: ignore[assignment]
    c = TestClient(create_app(st), raise_server_exceptions=False)
    for p in (
        "/analysis/s1",
        "/card/s1",
        "/wbs/s1",
        "/path?target=1",
        "/driving-path?source=1&target=2",
        "/forecast",
        "/curves",
        "/scurve",
        "/cei",
        "/trend",
        "/evolution",
        "/briefing",
        "/brief",
        "/compare",
        "/ribbon",
        "/api/forecast",
        "/api/curves",
        "/api/cei",
        "/api/scurve",
        "/api/trend",
        "/api/evolution",
        "/api/dashboard",
        "/export/xlsx/forecast",
        "/export/xlsx/curves",
        "/export/xlsx/cei",
        "/export/xlsx/trend",
    ):
        assert c.get(p).status_code < 500, p


# --- direct render-helper unit tests (stored-vs-basis dates, doc-less DCMA cell) -----------------


def test_task_iso_dates_stored_basis_and_missing() -> None:
    import datetime as dt

    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import _task_iso_dates

    sch = Schedule(
        name="s",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(
            Task(
                unique_id=1,
                name="stored",
                duration_minutes=480,
                start=dt.datetime(2025, 1, 6),
                finish=dt.datetime(2025, 1, 7),
            ),
            Task(unique_id=2, name="basis", duration_minutes=480),  # no stored dates
        ),
        relationships=(),
    )
    # stored dates render verbatim
    assert _task_iso_dates(sch, {}, {}, 1) == ("2025-01-06", "2025-01-07")
    # no stored dates -> the date_basis offsets convert on the calendar
    s, f = _task_iso_dates(sch, {2: 480}, {2: 960}, 2)
    assert s is not None and f is not None
    # no stored dates and no basis entries -> None, None
    assert _task_iso_dates(sch, {}, {}, 2) == (None, None)
    # unknown uid -> None, None
    assert _task_iso_dates(sch, {}, {}, 99) == (None, None)


def test_dcma_metric_cell_for_an_undocumented_metric() -> None:
    from schedule_forensics.engine.dcma_audit import AuditCheck, CheckStatus
    from schedule_forensics.web.app import _dcma_metric_cell

    check = AuditCheck(
        metric_id="NOT_A_REAL_METRIC",
        name="Mystery Check",
        status=CheckStatus.NOT_APPLICABLE,
        count=0,
        population=0,
        value=0.0,
        unit="count",
        threshold=None,
        suggested_improvement="",
        citations=(),
    )
    # no dictionary entry -> the plain name cell (no tooltip), never an error
    assert _dcma_metric_cell(check) == "<td>Mystery Check</td>"


def test_dcma_definition_cell_for_an_undocumented_metric() -> None:
    from schedule_forensics.web.app import _dcma_definition_cell

    assert _dcma_definition_cell("NOT_A_REAL_METRIC") == "<td></td>"


def test_groups_breakdown_table_with_no_values() -> None:
    import datetime as dt

    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import _groups_breakdown_table

    # a population that carries no value for the field -> the "no values" panel, not a crash
    sub = Schedule(
        name="s",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),  # no resources
        relationships=(),
    )
    out = _groups_breakdown_table(sub, "Resource")
    assert "No activities in scope carry a value" in out


def test_briefing_table_html_handles_an_absent_table() -> None:
    from schedule_forensics.ai.briefing import BriefingSection
    from schedule_forensics.web.app import _briefing_table_html

    section = BriefingSection("Empty", (), kind="prose", table=None)
    assert _briefing_table_html(section) == ""
