"""Targeted AI-layer coverage — diagnostic-brief paragraph/branch variants, the grounded
Q&A fact-sheet/answer edge paths, and the Ollama backend's error-text + response decoding.

These build small, fully-controlled multi-version schedules (rising/easing pressure,
negative float, duration cuts, removed logic, healthy CEI) to reach the brief/qa branches
the broad suites do not, and inject a fake urllib opener (HTTPError / URLError(timeout) /
a body) to exercise probe_error_text and generate without a live Ollama.
"""

from __future__ import annotations

import datetime as dt
import json
import socket
import urllib.error

import pytest

from schedule_forensics.ai.brief import build_brief
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.ollama import OllamaBackend, probe_error_text
from schedule_forensics.ai.qa import (
    answer_question,
    build_workbook_fact_sheet,
    figure_agreement,
    model_evidence,
    relevant_facts,
)
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

_START = dt.datetime(2025, 1, 6, 8, 0)


# --- fake-model used for the Q&A answer paths --------------------------------------------


class _Model:
    name = "ollama"
    is_local = True

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


# === Diagnostic brief =====================================================================


def test_build_brief_rejects_an_empty_version_list() -> None:
    # line 71: a brief needs at least one analyzable schedule.
    with pytest.raises(ValueError, match="at least one analyzable schedule"):
        build_brief([], [])


def _negative_float_pair() -> tuple[list[Schedule], list[object]]:
    """A two-version set whose constrained successor is behind its own logic in BOTH
    versions, and worse in the latest (rising schedule pressure)."""

    def version(name: str, fnlt: dt.datetime, sd: dt.datetime) -> Schedule:
        a = Task(unique_id=1, name="Predecessor", duration_minutes=4800)  # 10 wd
        b = Task(
            unique_id=2,
            name="Constrained finish",
            duration_minutes=4800,
            constraint_type=ConstraintType.FNLT,
            constraint_date=fnlt,
        )
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=_START,
            status_date=sd,
            tasks=(a, b),
            relationships=(
                Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            ),
        )

    v1 = version("v1", dt.datetime(2025, 1, 10, 17, 0), dt.datetime(2025, 1, 6, 8, 0))
    v2 = version("v2", dt.datetime(2025, 1, 8, 17, 0), dt.datetime(2025, 1, 7, 8, 0))
    schedules = [v1, v2]
    return schedules, [compute_cpm(s) for s in schedules]


def test_brief_trends_and_risk_narrate_rising_negative_float() -> None:
    # Trends (lines 265-270) report negative-float activities went from n0 to n1 with a
    # rising/easing/holding trend; the risk-recovery section (lines 292-294) names the worst.
    schedules, cpms = _negative_float_pair()
    brief = build_brief(schedules, cpms, today=dt.date(2025, 1, 8))
    trends = next(s for s in brief.sections if s.heading == "Trends over time")
    trend_blob = " ".join(p.text for p in trends.paragraphs)
    assert "negative total float" in trend_blob
    # the constraint tightened version-over-version -> more pressure
    assert "rising schedule pressure" in trend_blob or "holding steady" in trend_blob
    risk = next(s for s in brief.sections if s.heading == "Risks, opportunities, and recovery plan")
    risk_blob = " ".join(p.text for p in risk.paragraphs)
    assert "behind their own logic" in risk_blob
    assert "Recovery:" in risk_blob
    for section in brief.sections:
        for paragraph in section.paragraphs:
            assert paragraph.citations  # §6 holds for the generated content


def test_brief_skips_non_high_manipulation_and_handles_missing_status_dates() -> None:
    # A removed logic link is a MEDIUM manipulation finding; _manipulation_questions must SKIP
    # it (line 386, the non-HIGH continue). With both versions carrying NO status date, the
    # remaining-cut (line 408) and stale-forecast (line 449) questions short-circuit to [].
    a = Task(unique_id=1, name="A", duration_minutes=480)
    b = Task(unique_id=2, name="B", duration_minutes=480)
    linked = Schedule(
        name="linked",
        source_file="v1.xml",
        project_start=_START,
        tasks=(a, b),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    unlinked = Schedule(
        name="unlinked",
        source_file="v2.xml",
        project_start=_START,
        tasks=(a, b),  # the 1->2 link is gone
    )
    schedules = [linked, unlinked]
    brief = build_brief(schedules, [compute_cpm(s) for s in schedules], today=dt.date(2025, 1, 8))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    # the MEDIUM removed-logic finding is NOT promoted into the HIGH-only questions section
    assert "logic links removed" not in blob
    # no status dates -> no remaining-cut / stale-forecast questions were emitted from them
    assert "had its remaining duration cut" not in blob


def test_brief_remaining_cut_question_fires_on_an_unjustified_cut() -> None:
    # lines 431/434: a task whose remaining duration is cut by far more working days than
    # elapsed, with progress barely moving, raises the "remaining duration cut" question.
    prior = Schedule(
        name="prior",
        source_file="prior.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 7, 17, 0),
        tasks=(
            Task(
                unique_id=1,
                name="Long task",
                duration_minutes=48000,  # 100 wd
                remaining_duration_minutes=48000,
                percent_complete=0.0,
            ),
        ),
    )
    current = Schedule(
        name="current",
        source_file="current.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 8, 17, 0),  # one day later
        tasks=(
            Task(
                unique_id=1,
                name="Long task",
                duration_minutes=48000,
                remaining_duration_minutes=4800,  # slashed by ~90 wd in a single day
                percent_complete=1.0,  # progress barely moved
            ),
        ),
    )
    schedules = [prior, current]
    brief = build_brief(schedules, [compute_cpm(s) for s in schedules], today=dt.date(2025, 1, 9))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    assert "had its remaining duration cut" in blob
    assert "Long task" in blob


def test_brief_forecast_spread_question_is_silent_when_methods_agree() -> None:
    # line 533: a tiny finished schedule has no wide forecast disagreement, so the forecast
    # spread question returns [] — yet the section is still produced and cited.
    done = Task(
        unique_id=1,
        name="Done",
        duration_minutes=480,
        percent_complete=100.0,
        actual_start=_START,
        actual_finish=dt.datetime(2025, 1, 6, 16, 0),
    )
    schedule = Schedule(
        name="solo",
        source_file="solo.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 7, 17, 0),
        tasks=(done,),
    )
    brief = build_brief([schedule], [compute_cpm(schedule)], today=dt.date(2025, 1, 8))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    assert "disagree by" not in blob  # the forecast-spread question did not fire


_FEB = dt.datetime(2025, 2, 15, 16, 0)
_MAR = dt.datetime(2025, 3, 15, 16, 0)
_APR = dt.datetime(2025, 4, 15, 16, 0)


def _done(uid: int, sched_finish: dt.datetime, actual_finish: dt.datetime) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=480,
        percent_complete=100.0,
        actual_start=actual_finish - dt.timedelta(hours=8),
        actual_finish=actual_finish,
        finish=sched_finish,
        baseline_finish=sched_finish,
    )


def _open(uid: int, sched_finish: dt.datetime) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=480,
        finish=sched_finish,
        baseline_finish=sched_finish,
    )


def _rising_cei_versions() -> list[Schedule]:
    """Three versions whose bow-wave CEI RISES (0.5 -> 1.0): one of the two activities the
    first version planned to finish in March slipped (0.5), then the next period's planned
    work all landed on time (1.0). A rising-and-high series is 'healthy, not declining'."""
    v1 = Schedule(
        name="v1",
        source_file="v1.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 2, 1, 17, 0),
        tasks=(_open(1, _MAR), _open(2, _MAR), _open(3, _APR), _open(4, _APR)),
    )
    v2 = Schedule(
        name="v2",
        source_file="v2.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 3, 1, 17, 0),
        tasks=(_done(1, _MAR, _MAR), _open(2, _APR), _open(3, _APR), _open(4, _APR)),
    )
    v3 = Schedule(
        name="v3",
        source_file="v3.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 4, 1, 17, 0),
        tasks=(
            _done(1, _MAR, _MAR),
            _done(2, _APR, _APR),
            _done(3, _APR, _APR),
            _done(4, _APR, _APR),
        ),
    )
    return [v1, v2, v3]


def test_brief_cei_question_is_silent_when_execution_is_healthy() -> None:
    # line 560: a CEI series that is high (>= 0.7) and NOT declining (it rises 0.5 -> 1.0)
    # raises no bow-wave question — the execution-index narrative is suppressed.
    schedules = _rising_cei_versions()
    from schedule_forensics.engine.bow_wave import compute_bow_wave

    ceis = [s.cei for s in compute_bow_wave(schedules).snapshots if s.cei is not None]
    assert ceis == [0.5, 1.0]  # the precondition the branch hinges on
    brief = build_brief(schedules, [compute_cpm(s) for s in schedules], today=dt.date(2025, 5, 1))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    assert "execution index (CEI" not in blob  # healthy, rising execution -> no CEI question


def test_brief_cei_question_silent_when_cei_uncomputable() -> None:
    # line 556: three all-complete versions produce no usable CEI value (every snapshot's CEI
    # is None), so the question short-circuits without raising.
    def complete_version(name: str, sd: dt.datetime) -> Schedule:
        t = Task(
            unique_id=1,
            name="A",
            duration_minutes=480,
            percent_complete=100.0,
            actual_start=_START,
            actual_finish=dt.datetime(2025, 1, 6, 16, 0),
        )
        return Schedule(
            name=name, source_file=f"{name}.xml", project_start=_START, status_date=sd, tasks=(t,)
        )

    schedules = [
        complete_version("v1", dt.datetime(2025, 1, 7, 17, 0)),
        complete_version("v2", dt.datetime(2025, 1, 8, 17, 0)),
        complete_version("v3", dt.datetime(2025, 1, 9, 17, 0)),
    ]
    brief = build_brief(schedules, [compute_cpm(s) for s in schedules], today=dt.date(2025, 1, 10))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    assert "execution index (CEI" not in blob


def test_brief_cei_question_silent_when_bow_wave_has_no_finishes() -> None:
    # lines 552-553: with three versions carrying NO finish dates at all, compute_bow_wave
    # raises ValueError, which the CEI question swallows (returns []).
    def empty_version(name: str, sd: dt.datetime) -> Schedule:
        # a single milestone with no finish/baseline dates -> nothing to profile
        t = Task(unique_id=1, name="M", duration_minutes=0, is_milestone=True)
        return Schedule(
            name=name, source_file=f"{name}.xml", project_start=_START, status_date=sd, tasks=(t,)
        )

    schedules = [
        empty_version("v1", dt.datetime(2025, 1, 7, 17, 0)),
        empty_version("v2", dt.datetime(2025, 1, 8, 17, 0)),
        empty_version("v3", dt.datetime(2025, 1, 9, 17, 0)),
    ]
    # must not raise — the ValueError from compute_bow_wave is caught inside the brief
    brief = build_brief(schedules, [compute_cpm(s) for s in schedules], today=dt.date(2025, 1, 10))
    questions = next(s for s in brief.sections if s.heading == "Questions the data raises")
    blob = " ".join(p.text for p in questions.paragraphs)
    assert "execution index (CEI" not in blob


# === Grounded Q&A =========================================================================


def test_fact_sheet_without_finish_drivers_omits_the_driving_fact() -> None:
    # branch 141->150: when no activity drives the computed finish (here an all-summary
    # schedule with an empty CPM network) the "Finish-driving activities" fact is skipped, and
    # forecasts that have no finish date are likewise skipped (branch 151->150).
    from schedule_forensics.ai.qa import build_fact_sheet
    from schedule_forensics.engine.dcma_audit import audit_schedule
    from schedule_forensics.engine.forecast import compute_finish_forecasts
    from schedule_forensics.engine.metrics import (
        compute_completion_performance,
        compute_float_bands,
    )
    from schedule_forensics.engine.recommendations import recommend

    schedule = Schedule(
        name="all-summary",
        source_file="all-summary.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 7, 17, 0),
        tasks=(Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True),),
    )
    cpm = compute_cpm(schedule)
    facts = build_fact_sheet(
        schedule,
        cpm,
        audit_schedule(schedule, cpm),
        recommend(schedule, current_cpm=cpm),
        compute_float_bands(schedule, cpm),
        compute_completion_performance(schedule),
        compute_finish_forecasts(schedule, cpm),
    )
    text = " ".join(f.text for f in facts)
    assert "Schedule frame" in text  # the frame fact always leads
    assert "Finish-driving activities" not in text  # no drivers -> the fact is omitted


def test_relevant_facts_and_model_evidence_handle_an_empty_sheet() -> None:
    # lines 283 / 307: with no facts, both selectors return the empty tuple, never an index error.
    assert relevant_facts((), "anything?") == ()
    assert model_evidence((), "anything?") == ()


def test_answer_question_discards_an_empty_generation() -> None:
    # line 392: a model that returns only whitespace yields no prose — the caller falls back
    # to the cited facts (here an empty sheet, so just None + ()).
    answer, used = answer_question(_Model("   "), (), "anything?")
    assert answer is None and used == ()


def test_figure_agreement_when_only_one_side_has_extra_figures() -> None:
    # branch 326->328: the primary cites no extra figure but the second does.
    only_second = figure_agreement("No numbers here.", "The slip is 15 days.")
    assert "DIFFER" in only_second and "only the second cites" in only_second
    assert "only the primary cites" not in only_second
    # branch 328->330: the primary cites an extra figure but the second does not.
    only_primary = figure_agreement("The slip is 12 days.", "No numbers here.")
    assert "DIFFER" in only_primary and "only the primary cites" in only_primary
    assert "only the second cites" not in only_primary


def test_workbook_fact_sheet_single_version_skips_the_manipulation_pair() -> None:
    # branch 219->231: with a single ordered version there is no consecutive pair, so the
    # manipulation block is skipped; the latest-version forecast facts still appear, and a
    # forecast with no finish date is itself skipped (branch 240->239).
    done = Task(
        unique_id=1,
        name="Done",
        duration_minutes=480,
        percent_complete=100.0,
        actual_start=_START,
        actual_finish=dt.datetime(2025, 1, 6, 16, 0),
    )
    schedule = Schedule(
        name="solo",
        source_file="solo.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 7, 17, 0),
        tasks=(done,),
    )
    facts = build_workbook_fact_sheet([schedule], [compute_cpm(schedule)])
    text = " ".join(f.text for f in facts)
    assert "Manipulation signal" not in text  # no pair -> no manipulation facts
    assert "Latest-version finish forecast" in text  # the dated forecasts are still emitted


def test_workbook_fact_sheet_two_versions_includes_a_manipulation_signal() -> None:
    # line 224: with two ordered versions and a removed logic link, the latest pair's
    # manipulation signal is appended as a cited fact.
    a = Task(unique_id=1, name="A", duration_minutes=480)
    b = Task(unique_id=2, name="B", duration_minutes=480)
    linked = Schedule(
        name="v1",
        source_file="v1.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 7, 17, 0),
        tasks=(a, b),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    unlinked = Schedule(
        name="v2",
        source_file="v2.xml",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 14, 17, 0),
        tasks=(a, b),  # the link is gone
    )
    schedules = [linked, unlinked]
    facts = build_workbook_fact_sheet(schedules, [compute_cpm(s) for s in schedules])
    text = " ".join(f.text for f in facts)
    assert "Manipulation signal (latest pair)" in text
    assert "logic links removed" in text


# === Ollama backend: error-text + response decoding ======================================


def test_probe_error_text_decodes_http_url_and_timeout_errors() -> None:
    # line 74: an HTTPError reports its status code.
    http = urllib.error.HTTPError("http://127.0.0.1:11434", 503, "busy", {}, None)  # type: ignore[arg-type]
    assert probe_error_text(http) == "server returned HTTP 503"
    # line 81: a timeout (URLError wrapping a socket.timeout) reads as a timeout.
    timed_out = urllib.error.URLError(TimeoutError("timed out"))
    assert "timed out" in probe_error_text(timed_out)
    # line 83: an unresolved host name.
    unresolved = urllib.error.URLError(socket.gaierror("Name or service not known"))
    assert probe_error_text(unresolved) == "host could not be resolved"


def test_ollama_generate_reads_the_injected_response_body() -> None:
    # lines 96-97: the injected opener returns a JSON body, which generate() reads + decodes
    # into the model's response text.
    def opener(url: str, data: bytes | None, timeout: float) -> str:
        assert url.endswith("/api/generate")
        assert data is not None and b"prompt" in data
        return json.dumps({"response": "the model's words"})

    backend = OllamaBackend(endpoint="http://127.0.0.1:11434", opener=opener)
    assert backend.generate("hello") == "the model's words"


def test_urllib_opener_reads_and_decodes_the_response_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # lines 96-97: the default _urllib_opener reads the response body and decodes it to text.
    # A fake _NO_REDIRECT_OPENER returns a context-manager response with a bytes body, so the
    # read/decode is exercised without a live server (the injected-opener path bypasses this).
    from schedule_forensics.ai import ollama

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"response":"hi"}'

    class _Opener:
        def open(self, request: object, timeout: float) -> _Resp:
            # a POST carries the body; the helper sets method + content-type on the request
            assert getattr(request, "method", None) == "POST"
            return _Resp()

    monkeypatch.setattr(ollama, "_NO_REDIRECT_OPENER", _Opener())
    out = ollama._urllib_opener("http://127.0.0.1:11434/api/generate", b'{"prompt":"x"}', 5.0)
    assert json.loads(out) == {"response": "hi"}


def test_ollama_default_urllib_opener_surfaces_a_connection_error() -> None:
    # the real _urllib_opener path (no injected opener): nothing is listening on this loopback
    # port, so the availability probe reports a concrete, actionable reason rather than hanging.
    backend = OllamaBackend(endpoint="http://127.0.0.1:1", probe_timeout=0.5)
    reason = backend.unavailable_reason()
    assert reason is not None and reason  # a non-empty human reason
    assert NullBackend().is_available()  # sanity: the offline default is always available
