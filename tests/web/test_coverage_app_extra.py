"""Second coverage pass over web/app.py: the AI-status/translation/second-backend helper branches,
the export/ask/translate route guards, and the render-helpers (forecast ruler, WBS, DCMA tooltip,
compare, counterfactual, briefing, settings, watchdog, path-evolution / driving-corridor) reached
only by their less-common inputs. Direct unit calls + TestClient, no network, no real Ollama."""

from __future__ import annotations

import datetime as dt
import types

from fastapi.testclient import TestClient

from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web import app as appmod
from schedule_forensics.web.app import SessionState, create_app

# --- small fakes + builders (inlined; never imported across test packages, for CI sys.path) ------


class _Probe:
    """A stand-in local backend for _ai_status_note: a reason (None == reachable), a model list,
    and an optional list_models() that raises (the diagnostics-only except arm)."""

    def __init__(self, reason: str | None = None, models: tuple[str, ...] = (), raise_list=False):
        self._reason = reason
        self._models = models
        self._raise = raise_list

    def unavailable_reason(self) -> str | None:
        return self._reason

    def is_available(self) -> bool:
        return self._reason is None

    def list_models(self) -> tuple[str, ...]:
        if self._raise:
            raise RuntimeError("list blew up")
        return self._models


class _FakeBackend:
    """A routed backend for _settings_body: a name (drives the dropdown branch) and a model list
    that can raise (the except arm)."""

    def __init__(self, name: str, models: tuple[str, ...] = (), raise_list: bool = False):
        self.name = name
        self._models = models
        self._raise = raise_list

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        if self._raise:
            raise RuntimeError("list blew up")
        return self._models

    def generate(self, prompt: str) -> str:
        return prompt

    def pull_model(self, model: str) -> None: ...


def _cyclic(name: str, day: int) -> Schedule:
    """A 1<->2 logic cycle (CPM-unsolvable) but with stored dates — every CPMError arm."""
    s = dt.datetime(2025, 1, day, 8, 0)
    f = dt.datetime(2025, 1, day + 1, 17, 0)
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2025, 1, 1),
        status_date=dt.datetime(2025, 1, day + 2),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480, start=s, finish=f, baseline_finish=f),
            Task(unique_id=2, name="B", duration_minutes=480, start=s, finish=f, baseline_finish=f),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=1, type=RelationshipType.FS),
        ),
    )


def _linear(name: str, uid2_minutes: int) -> Schedule:
    """A solvable 1->2->3 chain; uid2's duration sets the finish (used for the compare delta)."""
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=uid2_minutes),
            Task(unique_id=3, name="C", duration_minutes=480),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),
        ),
    )


def _three_task(name: str) -> Schedule:
    """A solvable schedule whose UIDs are 1, 2, 3 (so 999/888 are guaranteed absent)."""
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=480),
            Task(unique_id=3, name="C", duration_minutes=480),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )


# --- _model_installed / _ai_status_note --------------------------------------------------------


def test_model_installed_blank_model_is_always_satisfied() -> None:
    from schedule_forensics.web.app import _model_installed

    assert _model_installed("", ("llama3.1:8b",)) is True


def test_ai_status_note_probe_none_and_reachable_and_listmodels_raises(monkeypatch) -> None:
    from schedule_forensics.web.app import _ai_status_note

    # construction refused the endpoint -> probe None -> empty status line
    monkeypatch.setattr(appmod, "_ollama_or_none", lambda c: None)
    assert _ai_status_note(AIConfig(backend="ollama", model="x")) == ""

    # reachable openai-compatible server (is_ollama False) -> the model-pull check is skipped, ON
    monkeypatch.setattr(appmod, "_openai_or_none", lambda c: _Probe(reason=None))
    assert "Local AI is ON" in _ai_status_note(AIConfig(backend="openai"))

    # reachable ollama whose list_models() raises -> installed=() -> still ON (never sinks the page)
    monkeypatch.setattr(appmod, "_ollama_or_none", lambda c: _Probe(raise_list=True))
    assert "Local AI is ON" in _ai_status_note(AIConfig(backend="ollama", model="x"))


# --- _second_backend (cache hit, openai construction + except) ----------------------------------


def test_second_backend_caches_and_handles_openai_construction(monkeypatch) -> None:
    from schedule_forensics.web.app import _second_backend

    # ollama second backend: not reachable -> None, cached; the 2nd call returns the cached None
    st = SessionState()
    st.ai_config = AIConfig(second_backend="ollama")
    assert _second_backend(st) is None
    assert _second_backend(st) is None  # cache hit (no re-construction)

    # openai second backend whose construction raises -> the except arm -> None (and no probe)
    st2 = SessionState()
    st2.ai_config = AIConfig(second_backend="openai", second_model="m")

    def _boom(**kwargs: object) -> object:
        raise RuntimeError("refused")

    monkeypatch.setattr(appmod, "OpenAICompatBackend", _boom)
    assert _second_backend(st2) is None


# --- _ai_translate / _translate_batch ----------------------------------------------------------


def test_ai_translate_skips_unparseable_lines() -> None:
    from schedule_forensics.web.app import _ai_translate

    class _Garbage:
        name = "g"
        is_local = True

        def is_available(self) -> bool:
            return True

        def list_models(self) -> tuple[str, ...]:
            return ("g",)

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return "no-tab-here\nalso-garbage"

    assert _ai_translate(["Alpha"], "es", _Garbage()) == {}  # type: ignore[arg-type]


def test_translate_batch_skips_blank_keys_and_dedupes(monkeypatch) -> None:
    from schedule_forensics.web.app import _translate_batch

    st = SessionState(language="es")
    monkeypatch.setattr(
        appmod, "_ai_translate", lambda need, lang, backend: {t: f"<x>{t}" for t in need}
    )
    out = _translate_batch(["   ", "Dup Term", "Dup Term"], "es", st)
    assert "   " not in out  # blank stripped -> continue
    assert out["Dup Term"] == "<x>Dup Term"  # asked for once despite the duplicate


# --- render helpers: forecast ruler, WBS, DCMA tooltip, counterfactual, briefing -----------------


def test_forecast_ruler_with_no_dates_is_empty() -> None:
    from schedule_forensics.engine.forecast import FinishForecast, ForecastSet
    from schedule_forensics.web.app import _forecast_ruler

    fc = ForecastSet(
        as_of=None,
        completed_count=0,
        remaining_count=0,
        rate_per_month=None,
        spi_t=None,
        planned_finish=None,
        forecasts=(FinishForecast("cpm", "CPM", None, "inputs missing"),),
        citation_uids=(),
    )
    assert _forecast_ruler(fc) == ""


def test_wbs_body_with_no_groups() -> None:
    from schedule_forensics.web.app import _wbs_body

    out = _wbs_body("k", ())
    assert "no schedulable activities" in out.lower()


def test_dcma_metric_cell_with_blank_importance_and_indicates(monkeypatch) -> None:
    from schedule_forensics.engine.dcma_audit import AuditCheck, CheckStatus
    from schedule_forensics.web.app import _dcma_metric_cell
    from schedule_forensics.web.help import MetricDoc

    monkeypatch.setitem(
        appmod.METRIC_DICTIONARY,
        "FAKE",
        MetricDoc(
            metric_id="FAKE",
            name="Fake",
            definition="d",
            formula="f",
            source="s",
            importance="",
            indicates="",
        ),
    )
    check = AuditCheck(
        metric_id="FAKE",
        name="Fake",
        status=CheckStatus.NOT_APPLICABLE,
        count=0,
        population=0,
        value=0.0,
        unit="count",
        threshold=None,
        suggested_improvement="",
        citations=(),
    )
    out = _dcma_metric_cell(check)
    assert "Fake" in out and "Why it matters" not in out and "Indicates" not in out


def test_counterfactual_panel_needs_two_versions() -> None:
    from schedule_forensics.web.app import _counterfactual_panel

    assert _counterfactual_panel([], [], None) == ""


def test_render_counterfactual_no_target_uid() -> None:
    from schedule_forensics.engine.path_counterfactual import PathCounterfactual, RevertedActivity
    from schedule_forensics.web.app import _render_counterfactual

    pc = PathCounterfactual(
        prior_label="v1",
        current_label="v2",
        reverted=(RevertedActivity(5, "X", "changed", ("constraint restored",)),),
        gained_float=(),
        actual_finish="2025-06-01",
        counterfactual_finish="2025-06-02",
        finish_delta_days=1,
        target_uid=None,  # no focus -> neither target sentence renders
        target_delta_days=None,
    )
    out = _render_counterfactual(pc)
    assert "X" in out and "Target activity" not in out and "individual impact" not in out


def test_briefing_body_renders_a_prose_fallback_section() -> None:
    from schedule_forensics.ai.briefing import BriefingSection, ExecutiveBriefing
    from schedule_forensics.ai.citations import CitedStatement
    from schedule_forensics.engine.dcma_audit import Citation
    from schedule_forensics.web.app import _briefing_body

    stmt = CitedStatement("a plain note", (Citation("f.xml", 1, "A"),))
    brief = ExecutiveBriefing(
        title="Briefing",
        generated_on=dt.date(2025, 1, 1),
        # "prose" is none of lede/trend/quality/project -> the readable list fallback
        sections=(BriefingSection("Misc", (stmt,), kind="prose"),),
    )
    out = _briefing_body(brief)
    assert "a plain note" in out and "Misc" in out


def test_compare_body_reports_an_earlier_finish() -> None:
    from schedule_forensics.web.app import _compare_body

    prior = _linear("v1", uid2_minutes=4800)  # longer -> later finish
    current = _linear("v2", uid2_minutes=480)  # shorter -> earlier finish
    out = _compare_body(prior, current, compute_cpm(prior), compute_cpm(current))
    assert "earlier" in out


# --- _settings_body: list_models raising, and the installed-model dropdown skip -------------------


def test_settings_body_listmodels_raises(monkeypatch) -> None:
    from schedule_forensics.web.app import _settings_body

    fake = _FakeBackend("x", raise_list=True)
    monkeypatch.setattr(appmod, "route_backend", lambda *a, **k: (fake, None))
    out = _settings_body(SessionState())
    assert "none available" in out


def test_settings_body_dropdown_with_installed_model(monkeypatch) -> None:
    from schedule_forensics.web.app import _settings_body

    st = SessionState()
    st.ai_config = AIConfig(backend="ollama", model="m1")
    fake = _FakeBackend("ollama", ("m1",))
    monkeypatch.setattr(appmod, "route_backend", lambda *a, **k: (fake, None))
    out = _settings_body(st)
    assert "<select name=model>" in out and "not installed" not in out


# --- shutdown + watchdog -------------------------------------------------------------------------


def test_trigger_shutdown_without_a_callback() -> None:
    from schedule_forensics.web.app import _trigger_shutdown

    app_obj = types.SimpleNamespace(
        state=types.SimpleNamespace(shutting_down=False, request_shutdown=None)
    )
    _trigger_shutdown(app_obj)  # callback is None -> sets the flag and returns
    assert app_obj.state.shutting_down is True


def test_watchdog_already_shutting_down_exits_immediately() -> None:
    from schedule_forensics.web.app import _watchdog

    app_obj = types.SimpleNamespace(
        state=types.SimpleNamespace(
            shutting_down=True, idle_grace=1.0, active_requests=0, browser_seen=False, last_beat=0.0
        )
    )
    _watchdog(app_obj, poll=0.01)  # while-condition false up front -> no body


def test_watchdog_holds_off_while_requests_are_in_flight(monkeypatch) -> None:
    from schedule_forensics.web.app import _watchdog

    state = types.SimpleNamespace(
        shutting_down=False, idle_grace=1.0, active_requests=1, browser_seen=True, last_beat=0.0
    )
    app_obj = types.SimpleNamespace(state=state)

    def _sleep(_seconds: float) -> None:
        state.shutting_down = True  # end the loop after the first (in-flight) pass

    monkeypatch.setattr(appmod.time, "sleep", _sleep)
    _watchdog(app_obj, poll=0.01)  # active_requests > 0 -> continue, then exit


# --- _evolution_data: absent-from-version critical/left rows (timing None, task None) -------------


def _ev_snap(**kw: object) -> types.SimpleNamespace:
    base: dict[str, object] = dict(
        label="v",
        status_date=None,
        project_finish=0,
        finish_delta_days=0,
        critical=(),
        entered=(),
        left=(),
        duration_changed=(),
        shortened_on_path=(),
        removed_logic_count=0,
        entered_changes=(),
        left_changes=(),
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_evolution_data_handles_activities_absent_from_a_version(monkeypatch) -> None:
    from schedule_forensics.web.app import _evolution_data

    s0, s1 = _three_task("v1"), _three_task("v2")
    cpms = [compute_cpm(s0), compute_cpm(s1)]
    left_change = types.SimpleNamespace(uid=888, name="Gone", reason="logic", detail="link removed")
    evo = types.SimpleNamespace(
        snapshots=[
            _ev_snap(label="v1"),
            _ev_snap(label="v2", critical=(999,), left=(888,), left_changes=(left_change,)),
        ]
    )
    monkeypatch.setattr(appmod, "compute_path_evolution", lambda schedules, cpms: evo)
    data = _evolution_data([s0, s1], cpms, None)
    snaps = data["snapshots"]
    assert isinstance(snaps, list) and len(snaps) == 2
    # the critical UID 999 is in neither version -> no bar (start None) and an empty stats grid
    crit = snaps[1]["critical_rows"]
    assert crit and crit[0]["uid"] == 999 and crit[0]["start"] is None
    assert crit[0]["complete"] is False
    # the left UID 888 is absent from the prior version too -> it just renders without a name lookup
    assert snaps[1]["left_rows"][0]["uid"] == 888


# --- _driving_path_body: the "left the corridor" snapshot block -----------------------------------


def test_driving_path_body_renders_left_the_corridor(monkeypatch) -> None:
    from schedule_forensics.web.app import _driving_path_body

    sch = _three_task("v1")
    snap = types.SimpleNamespace(
        status_date=None,
        change_note="route shifted",
        length_delta=2,
        left=(2,),
        label="v1",
        status="connected",
    )
    evo = types.SimpleNamespace(snapshots=[snap])
    monkeypatch.setattr(appmod, "compute_driving_path_evolution", lambda s, c, src, tgt: evo)
    monkeypatch.setattr(
        appmod, "_driving_path_gantt", lambda *a, **k: {"versions": [{"activities": []}]}
    )
    monkeypatch.setattr(appmod, "_corridor_chips", lambda snap: "chips")
    out = _driving_path_body([sch], [compute_cpm(sch)], source=1, target=3)
    assert "Left the corridor" in out and "route shifted" in out and "corridor length +2" in out


# --- route guards: export-path, ask (CPMError / no-analyzable), translate (bad JSON), groups ------


def test_export_path_format_notfound_and_cpmerror_guards() -> None:
    st = SessionState()
    st.schedules["c"] = _cyclic("c", 6)
    c = TestClient(create_app(st), raise_server_exceptions=False)
    # bad format (target present so it gets past required-param validation) -> 404
    assert c.get("/export/zzz/path/c?target=1").status_code == 404
    # valid format, unknown schedule -> 404
    assert c.get("/export/xlsx/path/nope?target=1").status_code == 404
    # valid format, present schedule, but unsolvable network -> 422 (CPMError)
    assert c.get("/export/xlsx/path/c?target=1").status_code == 422


def test_ask_routes_cpmerror_and_no_analyzable_versions() -> None:
    # single unsolvable schedule: /api/ask/{name} and the single-version /api/ask both 422
    st = SessionState()
    st.schedules["c"] = _cyclic("c", 6)
    c = TestClient(create_app(st), raise_server_exceptions=False)
    assert c.post("/api/ask/c", data={"question": "what is the finish?"}).status_code == 422
    assert c.post("/api/ask", data={"question": "what is the finish?"}).status_code == 422

    # two unsolvable versions: the workbook ask finds nothing analyzable -> 422
    st2 = SessionState()
    st2.schedules["c1"] = _cyclic("c1", 6)
    st2.schedules["c2"] = _cyclic("c2", 10)
    c2 = TestClient(create_app(st2), raise_server_exceptions=False)
    assert c2.post("/api/ask", data={"question": "x"}).status_code == 422


def test_ask_response_skips_agreement_when_an_answer_is_empty(monkeypatch) -> None:
    st = SessionState()
    st.schedules["s"] = _three_task("s")
    second = types.SimpleNamespace(name="second", model="m")
    monkeypatch.setattr(appmod, "_second_backend", lambda state: second)
    monkeypatch.setattr(appmod, "answer_question", lambda backend, facts, text, mode: ("", ()))
    c = TestClient(create_app(st), raise_server_exceptions=False)
    r = c.post("/api/ask/s", data={"question": "anything"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "" and body["agreement"] is None and body["second_model"]


def test_translate_api_with_invalid_json_body() -> None:
    c = TestClient(create_app(SessionState()), raise_server_exceptions=False)
    r = c.post("/api/translate", content="not-json{", headers={"content-type": "application/json"})
    assert r.status_code == 200 and r.json() == {"translations": {}}


def test_groups_filter_row_with_an_empty_field_is_skipped() -> None:
    st = SessionState()
    st.schedules["s"] = _three_task("s")
    c = TestClient(create_app(st), raise_server_exceptions=False)
    # an empty `field` entry in the submitted filter form -> the row is skipped, never a 500
    assert c.get("/groups?field=&breakdown=WBS").status_code < 500


def test_groups_preview_scorecard_degrades_on_an_unsolvable_scope() -> None:
    st = SessionState()
    st.schedules["c"] = _cyclic("c", 6)
    c = TestClient(create_app(st), raise_server_exceptions=False)
    r = c.get("/groups")
    assert r.status_code < 500
    assert "cannot be solved" in r.text


# --- _driving_data: the "dates not supported by logic" coverage note on a real schedule ----------


def test_driving_data_flags_unsupported_dates() -> None:
    from schedule_forensics.web.app import _driving_data

    # uid1 has no predecessors and a stored start well past the project start, so the forward pass
    # FLOORS it there above its pure-logic early start (0) -> it is reported as a stored-date-driven
    # activity (CPMResult.date_driven), and a trace through it carries the "not supported" note.
    sch = Schedule(
        name="dd",
        source_file="dd.xml",
        project_start=dt.datetime(2025, 1, 1),
        tasks=(
            Task(unique_id=1, name="Floated", duration_minutes=480, start=dt.datetime(2025, 1, 20)),
            Task(unique_id=2, name="Succ", duration_minutes=480),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    cpm = compute_cpm(sch)
    assert 1 in cpm.date_driven
    data = _driving_data(sch, cpm, 2, 10, 20)
    assert "not supported by logic" in str(data["coverage"])
