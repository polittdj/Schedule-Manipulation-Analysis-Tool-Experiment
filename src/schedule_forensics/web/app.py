"""Local-only FastAPI web app — the dark, NASA-themed forensic dashboard (M13, §6.A).

Runs entirely on the local machine (binds 127.0.0.1 only): upload up to twenty schedules,
see each one's DCMA audit, Acumen §A/§C metrics, cited risk/opportunity/concern findings
and AI narrative, compare two versions (manipulation trends + Net Finish Impact), manage the
local AI model + classification (with the persistent CUI banner), browse the in-tool metric
dictionary, and wipe the session. No schedule content is ever logged (paths/counts only —
CUI), and the AI never leaves the box (`ai.route_backend` fail-closed). Interactive
Power-BI-style visuals are layered on at M14; M13 is the shell + server-rendered views.
"""

from __future__ import annotations

import datetime as dt
import html
import logging
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from urllib.parse import quote, urlparse

import uvicorn
from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Template

from schedule_forensics.ai import (
    AIBackend,
    AIConfig,
    Classification,
    NullBackend,
    OllamaBackend,
    OpenAICompatBackend,
    banner_for,
    reattach,
    route_backend,
)
from schedule_forensics.ai.brief import DiagnosticBrief, brief_blocks, build_brief
from schedule_forensics.ai.briefing import BriefingSection, ExecutiveBriefing, build_briefing
from schedule_forensics.ai.citations import CitedStatement, Narrative
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.ai.qa import (
    answer_question,
    build_fact_sheet,
    build_workbook_fact_sheet,
    figure_agreement,
)
from schedule_forensics.engine import (
    analyze_floats,
    audit_schedule,
    compute_cpm,
    compute_driving_slack,
    recommend,
)
from schedule_forensics.engine.bow_wave import BowWave, compute_bow_wave
from schedule_forensics.engine.cpm import CPMError, CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit
from schedule_forensics.engine.driving_slack import date_basis
from schedule_forensics.engine.forecast import ForecastSet, compute_finish_forecasts
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import (
    compute_activity_makeup,
    compute_baseline_compliance,
    compute_completion_performance,
    compute_constraint_distribution,
    compute_float_bands,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.engine.metrics._common import MetricResult, non_summary
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.engine.trend import compute_quality_trend, order_versions
from schedule_forensics.importers import (
    MAX_FILES,
    ImporterError,
    decode_xer_bytes,
    load_schedule,
    parse_json,
    parse_json_text,
    parse_mspdi_text,
    parse_xer_text,
    supported_extensions,
    to_json_text,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.net_guard import is_loopback_host
from schedule_forensics.reports.docx import Block, render_document, render_docx
from schedule_forensics.reports.tables import (
    Table,
    TableSet,
    activities_table,
    bow_wave_tables,
    dcma_table,
    driving_table,
    findings_table,
    forecast_tables,
    metric_results_table,
    schedule_summary_table,
    trend_tables,
)
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.web.help import METRIC_DICTIONARY

logger = logging.getLogger("schedule_forensics.web")

#: Locally-vendored static assets (CSS/JS) — served from /static; no CDN, no external fetch.
_STATIC_DIR = Path(__file__).parent / "static"
#: Bundled, non-CUI sample schedule for the "Load example" button.
_EXAMPLE = Path(__file__).parent / "examples" / "house_build.json"
#: File types the open/import picker accepts.
_ACCEPT = ".json,.xml,.mspdi,.xer,.mpp,.mpt"

_LAYOUT = Template(
    """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{ title }} — Schedule Forensics</title>
<link rel=icon href="/static/favicon.ico">
<script src="/static/theme.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css"></head><body>
<header><h1>&#9650; SCHEDULE FORENSICS</h1>
<nav><a href="/">Dashboard</a><a href="/brief">Diagnostic Brief</a><a href="/path">Path Analysis</a><a href="/trend">Trend</a>
<a href="/cei">Bow Wave / CEI</a>
<a href="/forecast">Forecast</a><a href="/briefing">Executive Briefing</a>
<a href="/settings">AI Settings</a><a href="/help">Metric Dictionary</a>
<form action="/session/wipe" method=post class=navform
onsubmit="return confirm('Wipe all loaded schedules?')"><button type=submit class=linkbtn>Wipe Session</button></form>
<a href="#" onclick="return sfQuit()" title="Stop the local server and exit">Quit</a>
<form action="/target" method=post class="navform targetform"
title="Focus every view on one activity (blank = clear)">
<input type=hidden name=next_url value="/">
<label>Target UID: <input name=uid type=number min=1 value="{{ target }}" placeholder="any"></label>
<button type=submit class=linkbtn>Set</button></form>
<button id=themeToggle type=button class=linkbtn title="Switch light/dark mode">Theme</button>
</nav></header>
<main>{{ banner }}{{ body }}</main><script src="/static/heartbeat.js"></script></body></html>"""
)


@dataclass(frozen=True)
class _Flash:
    """A one-shot import result message shown on the next dashboard render."""

    accepted: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Analysis:
    """Everything a report view needs, computed once from a single CPM pass per schedule.

    Building this runs the network just once and threads that CPM through the audit, the
    baseline-compliance panel, the findings, the narrative, and the activity grid — instead
    of each view recomputing the CPM several times over.
    """

    cpm: CPMResult
    audit: ScheduleAudit
    compliance: dict[str, MetricResult]
    float_bands: dict[str, MetricResult]
    completion: dict[str, MetricResult]
    findings: tuple[Finding, ...]
    narrative: Narrative
    activity_rows: list[dict[str, object]]


def _compute_analysis(sch: Schedule) -> _Analysis:
    """Run the engine once for ``sch`` (a single ``compute_cpm``, reused everywhere)."""
    cpm = compute_cpm(sch)
    return _Analysis(
        cpm=cpm,
        audit=audit_schedule(sch, cpm),
        compliance=compute_baseline_compliance(sch, cpm),
        float_bands=compute_float_bands(sch, cpm),
        completion=compute_completion_performance(sch),
        findings=recommend(sch, current_cpm=cpm),
        # the cached narrative is always the deterministic (NullBackend) one; a real
        # session-selected backend rephrases it per request via _polished_narrative
        # (citations re-attached, figures re-verified — see ai.citations.reattach).
        narrative=build_narrative(sch, current_cpm=cpm),
        activity_rows=_activity_rows(sch, cpm),
    )


@dataclass
class SessionState:
    """In-memory, local-only session: loaded schedules (by name) + AI config. No disk persistence."""

    schedules: dict[str, Schedule] = field(default_factory=dict)
    ai_config: AIConfig = field(default_factory=AIConfig)
    flash: _Flash | None = None  # transient import feedback, consumed on the next home() render
    # per-schedule analysis cache (key -> (schedule, analysis)); identity-checked so a re-upload
    # under the same key recomputes. Bounded by the ≤MAX_FILES loaded schedules; cleared on wipe.
    analyses: dict[str, tuple[Schedule, _Analysis]] = field(default_factory=dict)
    # optional session-wide target activity: every view that can focus on a UniqueID
    # (report trace, trend focus, compare movement) defaults to this when set.
    target_uid: int | None = None
    # the routed AI backend, cached briefly (config, probed-at, backend) so report renders
    # don't re-probe a down Ollama every time; reset on a settings change / TTL lapse.
    backend_cache: tuple[AIConfig, float, AIBackend] | None = None
    # per-schedule narrative as polished by a real (non-null) backend:
    # key -> (schedule identity, "backend/model" stamp, narrative). Cleared on wipe.
    polished: dict[str, tuple[Schedule, str, Narrative]] = field(default_factory=dict)
    # the cross-check second model, cached like backend_cache (None = off/unreachable).
    second_cache: tuple[AIConfig, float, AIBackend | None] | None = None

    def ordered(self) -> list[Schedule]:
        return list(self.schedules.values())

    def ordered_versions(self) -> list[tuple[str, Schedule]]:
        """(key, schedule) pairs ordered by data date, oldest first (undated keep load order)."""
        by_obj = {id(s): k for k, s in self.schedules.items()}
        return [(by_obj[id(s)], s) for s in order_versions(list(self.schedules.values()))]

    def analysis_for(self, key: str, sch: Schedule) -> _Analysis:
        """The cached analysis for ``key``, recomputing only if the schedule object changed."""
        cached = self.analyses.get(key)
        if cached is not None and cached[0] is sch:
            return cached[1]
        analysis = _compute_analysis(sch)
        self.analyses[key] = (sch, analysis)
        return analysis


def _banner_html(state: SessionState) -> str:
    # the persistent banner reflects the project's classification intent (config-driven);
    # actual generation still fails closed via route_backend.
    banner = banner_for(state.ai_config)
    css = "cloud" if banner.cloud_active else "local"
    return f'<div class="banner {css}">{html.escape(banner.text)}</div>'


def _flash_html(flash: _Flash | None) -> str:
    """Render one-shot import feedback (loaded N / per-file errors), or nothing."""
    if flash is None or (not flash.accepted and not flash.errors):
        return ""
    parts: list[str] = []
    if flash.accepted:
        names = ", ".join(_e(a) for a in flash.accepted)
        parts.append(f'<div class="notice ok">Loaded {len(flash.accepted)}: {names}</div>')
    for err in flash.errors:
        parts.append(f'<div class="notice err">Could not import {_e(err)}</div>')
    return "".join(parts)


def _ollama_or_none(config: AIConfig) -> OllamaBackend | None:
    if config.backend != "ollama":
        return None
    try:
        return OllamaBackend(endpoint=config.endpoint, model=config.model)
    except Exception:
        return None


def _openai_or_none(config: AIConfig) -> OpenAICompatBackend | None:
    if config.backend != "openai":
        return None
    try:
        # construction enforces loopback (CUIEgressError on a remote host — Law 1)
        return OpenAICompatBackend(endpoint=config.openai_endpoint, model=config.model)
    except Exception:
        return None


def _second_backend(state: SessionState) -> AIBackend | None:
    """The configured cross-check model, probed + cached like the primary (or ``None``).

    Only the two LOCAL backend kinds are constructible here — a cloud second model does
    not exist by design. Unreachable/missing servers cache as ``None`` (cross-check off)
    so a down second server costs one probe per TTL, not one per question.
    """
    cfg = state.ai_config
    if cfg.second_backend not in ("ollama", "openai"):
        return None
    cached = state.second_cache
    now = time.monotonic()
    if cached is not None and cached[0] == cfg and now - cached[1] < _BACKEND_PROBE_TTL:
        return cached[2]
    backend: AIBackend | None = None
    try:
        if cfg.second_backend == "ollama":
            backend = OllamaBackend(endpoint=cfg.endpoint, model=cfg.second_model or cfg.model)
        else:
            backend = OpenAICompatBackend(endpoint=cfg.openai_endpoint, model=cfg.second_model)
    except Exception:
        backend = None
    if backend is not None and not backend.is_available():
        backend = None
    state.second_cache = (cfg, now, backend)
    return backend


#: How long a routed-backend probe result is trusted before re-probing (seconds). Keeps
#: report renders from paying the Ollama availability probe on every page view, while an
#: Ollama started mid-session is still picked up promptly.
_BACKEND_PROBE_TTL = 15.0


def _active_backend(state: SessionState) -> AIBackend:
    """The session's routed AI backend (fail-closed local — `route_backend`).

    The routing result is cached for ``_BACKEND_PROBE_TTL`` seconds per config value; a
    settings save resets the cache so changes take effect immediately.
    """
    cached = state.backend_cache
    now = time.monotonic()
    if cached is not None and cached[0] == state.ai_config and now - cached[1] < _BACKEND_PROBE_TTL:
        return cached[2]
    backend, _banner = route_backend(
        state.ai_config,
        null_backend=NullBackend(),
        ollama_backend=_ollama_or_none(state.ai_config),
        openai_backend=_openai_or_none(state.ai_config),
    )
    state.backend_cache = (state.ai_config, now, backend)
    return backend


def _polished_narrative(
    state: SessionState, key: str, sch: Schedule, analysis: _Analysis
) -> Narrative:
    """The report narrative, rephrased by the session-selected backend when one is active.

    The Null backend (the default, and the fail-closed route) returns the cached
    deterministic narrative at zero cost. A real backend rephrases each statement once per
    (schedule, backend, model) — `reattach` re-verifies citations AND figures, so polish can
    never drop a citation or alter a number — and any generation failure falls back to the
    deterministic narrative (a dying model server must never 500 the report)."""
    backend = _active_backend(state)
    if backend.name == "null":
        return analysis.narrative
    stamp = f"{backend.name}/{getattr(backend, 'model', '')}"
    cached = state.polished.get(key)
    if cached is not None and cached[0] is sch and cached[1] == stamp:
        return cached[2]
    sources = analysis.narrative.statements
    try:
        polished = tuple(backend.generate(s.text) for s in sources)
    except Exception:
        logger.warning("AI narrative generation failed; serving the deterministic narrative")
        return analysis.narrative
    narrative = Narrative(title=analysis.narrative.title, statements=reattach(polished, sources))
    state.polished[key] = (sch, stamp, narrative)
    return narrative


def _ask_panel_html(state: SessionState, page_schedule: str | None = None) -> str:
    """The Ask-the-AI panel every page carries once schedules are loaded (M18 item 4).

    Scope select: the whole workbook (multi-version cited facts) or any single loaded
    schedule; a page with a natural schedule context pre-selects it. The disclaimer is
    standing and permanent — answers may be model-interpreted (settings: AI answer mode)
    but are always grounded by, and shown with, the engine's cited facts.
    """
    if not state.schedules:
        return ""
    keys = [k for k, _ in state.ordered_versions()]
    options: list[str] = []
    if len(keys) > 1:
        sel = " selected" if page_schedule is None else ""
        options.append(f'<option value=""{sel}>Workbook — all {len(keys)} versions</option>')
    for k in keys:
        sel = " selected" if k == page_schedule or len(keys) == 1 else ""
        options.append(f'<option value="{_e(k)}"{sel}>{_e(k)}</option>')
    return f"""
<div class=panel id=askPanel><h2>Ask the AI</h2>
<p class=muted><b>AI can err &mdash; verify against citations.</b> Answers are grounded in the
engine's computed, cited facts, and the matching facts are always shown with the answer.
With no local model active you get the facts themselves.</p>
<div class=viz-controls>
<label>About <select id=askScope>{"".join(options)}</select></label>
<input id=askInput type=text size=60 maxlength=500
 placeholder="e.g. Why is the finish slipping? How many critical activities?">
<button id=askBtn type=button>Ask</button></div>
<div id=askOut></div></div>
<script src="/static/ask.js"></script>"""


def _page(
    state: SessionState,
    title: str,
    body: str,
    *,
    status_code: int = 200,
    ask_schedule: str | None = None,
) -> HTMLResponse:
    return HTMLResponse(
        _LAYOUT.render(
            title=title,
            banner=_banner_html(state),
            body=body + _ask_panel_html(state, ask_schedule),
            target=state.target_uid if state.target_uid is not None else "",
        ),
        status_code=status_code,
    )


def _parse_uid(value: str | None) -> int | None:
    """A UniqueID from form/query text — blank, non-numeric, or non-positive means none."""
    if value is None:
        return None
    text = value.strip()
    if not text.isdigit():
        return None
    uid = int(text)
    return uid if uid > 0 else None


def _e(text: object) -> str:
    return html.escape(str(text))


def create_app(
    state: SessionState | None = None,
    *,
    auto_shutdown: bool = False,
    idle_grace: float = 10.0,
) -> FastAPI:
    """Build the FastAPI app. ``state`` lets a test/launcher inject a fresh session.

    ``auto_shutdown`` (set by the desktop launcher) makes :func:`serve` run a watchdog that
    stops the server once the browser stops sending heartbeats for ``idle_grace`` seconds —
    so closing the window turns the whole tool off. ``request_shutdown`` is wired by
    :func:`serve`; the in-page "Quit" control and the watchdog both call it.
    """
    app = FastAPI(title="Schedule Forensics", docs_url=None, redoc_url=None)
    app.state.session = state if state is not None else SessionState()
    app.state.auto_shutdown = auto_shutdown
    app.state.idle_grace = idle_grace
    app.state.last_beat = time.monotonic()
    app.state.browser_seen = False  # armed once the first heartbeat arrives
    app.state.shutting_down = False
    app.state.request_shutdown = None  # set by serve() to flip the server's should_exit
    app.state.active_requests = 0  # in-flight work holds the auto-shutdown watchdog
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.middleware("http")
    async def _liveness(request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        # A long import (several real .mpp files spawning Java) once starved the heartbeat
        # and the watchdog killed the server MID-LOAD. Any request in flight is proof the
        # operator is here: count it (the watchdog waits) and refresh the beat on completion.
        app.state.active_requests += 1
        try:
            response: Response = await call_next(request)
            return response
        finally:
            app.state.active_requests -= 1
            app.state.last_beat = time.monotonic()

    def session() -> SessionState:
        s: SessionState = app.state.session
        return s

    @app.post("/api/heartbeat")
    def heartbeat() -> JSONResponse:
        app.state.last_beat = time.monotonic()
        app.state.browser_seen = True
        return JSONResponse({"ok": True})

    @app.post("/api/shutdown")
    def shutdown() -> JSONResponse:
        _trigger_shutdown(app)
        return JSONResponse({"stopping": True})

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        st = session()
        flash = _flash_html(st.flash)
        st.flash = None  # one-shot: clear after rendering
        rows = "".join(
            f'<tr><td><a href="/analysis/{quote(name)}">{_e(name)}</a></td>'
            f"<td>{len(non_summary(sch))}</td><td class=muted>{_e(sch.source_file or '-')}</td>"
            f'<td class=row-actions><a href="/analysis/{quote(name)}">Open report</a>'
            f' &middot; <a href="/card/{quote(name)}">Card</a>'
            f' &middot; <a href="/download/{quote(name)}.json">Save .json</a></td></tr>'
            for name, sch in st.schedules.items()
        )
        loaded = (
            "<div class=panel><h2>Loaded schedules</h2>"
            "<table><tr><th>Schedule</th><th>Activities</th><th>Source</th><th></th></tr>"
            f"{rows}</table>"
            + (
                '<p style="margin-top:14px"><a class=btn-link href="/briefing">'
                "Executive briefing &rarr;</a>"
                + (
                    ' &middot; <a class=btn-link href="/trend">Trend across all versions &rarr;</a>'
                    ' &middot; <a class=btn-link href="/cei">Bow Wave / CEI &rarr;</a>'
                    ' &middot; <a class=btn-link href="/compare">Compare the two most recent &rarr;</a>'
                    if len(st.schedules) >= 2
                    else ""
                )
                + "</p>"
            )
            + "</div>"
            if rows
            else ""
        )
        body = f"""
{flash}
<section class=hero>
  <h2>Forensic schedule analysis &mdash; entirely on your machine</h2>
  <p class=muted>Open or import a Microsoft&nbsp;Project / Primavera schedule to get a DCMA-14 audit,
  Acumen-Fuse&nbsp;&amp;&nbsp;SSI-parity metrics, driving-path and manipulation-trend analysis, and a
  cited AI narrative &mdash; nothing leaves this computer.</p>
</section>
<div class=panel>
  <div id=dropzone class=dropzone>
    <div class=dz-icon>&#8682;</div>
    <p class=dz-title>Drop a schedule here, or
      <button type=button class=linkbtn id=pickBtn>choose a file&hellip;</button></p>
    <p class=muted>Microsoft Project <code>.mpp</code> / <code>.mpt</code>, MS Project XML
      <code>.xml</code>, Primavera <code>.xer</code>, or the tool's own <code>.json</code>
      &mdash; up to {MAX_FILES} at once.</p>
    <div class=dz-actions>
      <form action="/example" method=post><button type=submit class=btn>Load example</button></form>
      <span class=muted>or import your own file above</span>
    </div>
  </div>
  <form id=uploadForm action="/upload" method=post enctype="multipart/form-data" hidden>
    <input id=fileInput type=file name=files multiple accept="{_ACCEPT}">
  </form>
</div>
{loaded}
<script src="/static/home.js"></script>"""
        return _page(st, "Dashboard", body)

    @app.post("/example")
    def load_example() -> RedirectResponse:
        st = session()
        schedule = parse_json(_EXAMPLE).model_copy(update={"source_file": "house_build.json"})
        key = _unique_key(_clean_key(schedule.name), st.schedules)
        st.schedules[key] = schedule
        logger.info("loaded bundled example schedule")
        return RedirectResponse(url=f"/analysis/{quote(key)}", status_code=303)

    @app.get("/download/{name}")
    def download_json(name: str) -> Response:
        st = session()
        key = name[:-5] if name.endswith(".json") else name
        sch = st.schedules.get(key)
        if sch is None:
            return Response("not found", status_code=404)
        filename = _safe_filename(f"{key}.json")
        return Response(
            to_json_text(sch),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/upload")
    def upload(files: list[UploadFile]) -> RedirectResponse:
        # sync on purpose: parsing runs in the threadpool, so the event loop keeps serving
        # heartbeats and pages while big native .mpp files import (Java subprocess each)
        st = session()
        accepted: list[str] = []
        errors: list[str] = []
        if len(files) > MAX_FILES:
            dropped = len(files) - MAX_FILES
            errors.append(
                f"{dropped} file(s) beyond the {MAX_FILES}-file batch cap "
                "(load them in a second batch)"
            )
        for upload_file in files[:MAX_FILES]:
            name = upload_file.filename or "schedule"
            data = upload_file.file.read()
            try:
                schedule = _parse_upload(name, data)
            except (ImporterError, ValueError, OSError) as exc:
                reason = str(exc).splitlines()[0][:160] if str(exc) else "unreadable file"
                errors.append(f"{name}: {reason}")
                logger.warning("rejected upload; ext=%s bytes=%d", Path(name).suffix, len(data))
                continue
            key = _unique_key(_clean_key(name), st.schedules)
            st.schedules[key] = schedule.model_copy(update={"source_file": name})
            accepted.append(key)
        logger.info(
            "loaded %d schedule(s); %d rejected; total now %d",
            len(accepted),
            len(errors),
            len(st.schedules),
        )
        st.flash = _Flash(accepted=tuple(accepted), errors=tuple(errors))
        # a single clean open jumps straight to its report; otherwise back to the dashboard
        if len(accepted) == 1 and not errors:
            return RedirectResponse(url=f"/analysis/{quote(accepted[0])}", status_code=303)
        return RedirectResponse(url="/", status_code=303)

    @app.get("/analysis/{name}", response_class=HTMLResponse)
    def analysis(name: str) -> HTMLResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return _page(st, name, _unschedulable_panel(sch, exc))
        narrative = _polished_narrative(st, name, sch, analysis)
        bar = _export_bar(f"analysis/{quote(name, safe='')}")
        return _page(
            st,
            name,
            bar + _analysis_body(name, sch, analysis, st.target_uid, narrative),
            ask_schedule=name,
        )

    @app.get("/card/{name}", response_class=HTMLResponse)
    def schedule_card(name: str) -> HTMLResponse:
        """The deck's *Metrics* page (PBIX page 1): the schedule's ID card."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return _page(st, name, _unschedulable_panel(sch, exc), ask_schedule=name)
        return _page(st, f"{name} — card", _card_body(name, sch, analysis), ask_schedule=name)

    @app.get("/api/analysis/{name}")
    def analysis_json(name: str) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_analysis_data(sch, analysis))

    @app.get("/api/driving/{name}")
    def driving_json(
        name: str,
        target: int = Query(...),
        secondary: int = Query(10),
        tertiary: int = Query(20),
    ) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            cpm = st.analysis_for(name, sch).cpm
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_driving_data(sch, cpm, target, secondary, tertiary))

    @app.get("/compare", response_class=HTMLResponse)
    def compare() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Compare", "<div class=panel>Load at least two versions to compare.</div>"
            )
        # Forensic order is by data date (the Acumen/SSI ProjectTimeNow pattern), not load
        # order; unschedulable versions (e.g. a logic cycle) are skipped, never a 500.
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Compare",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to compare.</div>",
            )
        prior, current = schedules[-2], schedules[-1]
        body = (
            _export_bar("compare")
            + _skipped_notice(skipped)
            + _compare_body(prior, current, cpms[-2], cpms[-1])
        )
        if st.target_uid is not None:
            body += _focus_panel([prior, current], [cpms[-2], cpms[-1]], st.target_uid)
        return _page(st, "Compare", body)

    def _solvable_versions() -> tuple[list[Schedule], list[CPMResult], list[str]]:
        """Ordered (schedules, cpms) for every loaded version whose network solves,
        plus the names of versions skipped (e.g. a logic cycle) — multi-version views
        must degrade to the analyzable subset, never 500 on one bad file."""
        st = session()
        schedules: list[Schedule] = []
        cpms: list[CPMResult] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                cpms.append(st.analysis_for(key, sch).cpm)
                schedules.append(sch)
            except CPMError:
                skipped.append(key)
        return schedules, cpms, skipped

    def _skipped_notice(skipped: list[str]) -> str:
        if not skipped:
            return ""
        names = ", ".join(_e(s) for s in skipped)
        return (
            f'<div class="notice err">Skipped (network cannot be solved — see each report '
            f"for the reason): {names}</div>"
        )

    @app.get("/path", response_class=HTMLResponse)
    def path_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Path Analysis",
                "<div class=panel>Load a schedule to run the SSI-style path analysis.</div>",
            )
        keys = [k for k, _ in st.ordered_versions()]
        return _page(st, "Path Analysis", _path_body(keys, st.target_uid))

    def _ask_response(
        st: SessionState, facts: tuple[CitedStatement, ...], text: str
    ) -> JSONResponse:
        """Shared Q&A response: route the backend(s), answer in the configured mode.

        With a cross-check second model configured and reachable, BOTH models answer
        independently and a deterministic figure-agreement note is computed — the
        engine compares, never a third model."""
        mode = st.ai_config.qa_mode
        answer, used = answer_question(_active_backend(st), facts, text, mode=mode)
        second_answer: str | None = None
        second_model: str | None = None
        agreement: str | None = None
        second = _second_backend(st)
        if second is not None:
            second_answer, _ = answer_question(second, facts, text, mode=mode)
            second_model = f"{second.name}/{getattr(second, 'model', '') or 'default'}"
            if answer and second_answer:
                agreement = figure_agreement(answer, second_answer)
        return JSONResponse(
            {
                "answer": answer,  # null => no local model active / answer failed the gate
                "mode": mode,
                "second_answer": second_answer,
                "second_model": second_model,
                "agreement": agreement,
                "facts": [
                    {
                        "text": f.text,
                        "citations": [
                            {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                            for c in f.citations[:3]
                        ],
                    }
                    for f in used
                ],
            }
        )

    def _schedule_facts(st: SessionState, name: str, sch: Schedule) -> tuple[CitedStatement, ...]:
        analysis = st.analysis_for(name, sch)
        return build_fact_sheet(
            sch,
            analysis.cpm,
            analysis.audit,
            analysis.findings,
            analysis.float_bands,
            analysis.completion,
            compute_finish_forecasts(sch, analysis.cpm),
        )

    @app.post("/api/ask/{name}")
    def ask(name: str, question: str = Form("")) -> JSONResponse:
        """Grounded Q&A on ONE schedule: engine facts; the configured mode governs prose."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        text = question.strip()[:500]
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        try:
            facts = _schedule_facts(st, name, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _ask_response(st, facts, text)

    @app.post("/api/ask")
    def ask_workbook(question: str = Form("")) -> JSONResponse:
        """Grounded Q&A across EVERY loaded version (the multi-version pages' panel)."""
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "not found"}, status_code=404)
        text = question.strip()[:500]
        if not text:
            return JSONResponse({"error": "ask a question"}, status_code=422)
        if len(st.schedules) == 1:
            key, sch = next(iter(st.schedules.items()))
            try:
                facts = _schedule_facts(st, key, sch)
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            return _ask_response(st, facts, text)
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "no analyzable versions loaded"}, status_code=422)
        return _ask_response(st, build_workbook_fact_sheet(schedules, cpms), text)

    @app.get("/trend", response_class=HTMLResponse)
    def trend_view(target: str | None = Query(None)) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Trend",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to see a trend.</div>",
            )
        # an explicit ?target= (even blank, from the Focus form) wins; otherwise the
        # session-wide target focuses the trend automatically
        uid = _parse_uid(target) if target is not None else st.target_uid
        return _page(
            st,
            "Trend",
            _export_bar("trend") + _skipped_notice(skipped) + _trend_body(schedules, cpms, uid),
        )

    @app.get("/api/trend")
    def trend_json(target: str | None = Query(None)) -> JSONResponse:
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        return JSONResponse(_trend_data(schedules, cpms, uid))

    @app.get("/cei", response_class=HTMLResponse)
    def cei_view() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st,
                "Bow Wave / CEI",
                "<div class=panel>Load at least two versions (monthly snapshots) to run the "
                "bow-wave / CEI analysis.</div>",
            )
        try:
            wave = compute_bow_wave([s for _, s in st.ordered_versions()])
        except ValueError as exc:
            return _page(st, "Bow Wave / CEI", f"<div class=panel>{_e(exc)}</div>")
        return _page(st, "Bow Wave / CEI", _export_bar("cei") + _cei_body(wave))

    @app.get("/api/cei")
    def cei_json() -> JSONResponse:
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave([s for _, s in st.ordered_versions()])
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_cei_data(wave))

    @app.get("/forecast", response_class=HTMLResponse)
    def forecast_view() -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Forecast",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to forecast the "
                "finish.</div>",
            )
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        return _page(
            st,
            "Forecast",
            _export_bar("forecast") + _skipped_notice(skipped) + _forecast_body(schedules, sets),
        )

    @app.get("/api/forecast")
    def forecast_json() -> JSONResponse:
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        return JSONResponse(_forecast_data(schedules, sets))

    # --- exports (M18): every view's tables, rendered locally as Excel or Word -------

    _EXPORT_MEDIA: dict[str, tuple[str, Callable[[TableSet], bytes]]] = {
        "xlsx": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            render_xlsx,
        ),
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            render_docx,
        ),
    }

    def _export_response(fmt: str, tableset: TableSet, stem: str) -> Response:
        media, renderer = _EXPORT_MEDIA[fmt]
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem) or "export"
        return Response(
            content=renderer(tableset),
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{safe}.{fmt}"'},
        )

    def _bad_format(fmt: str) -> JSONResponse | None:
        if fmt not in _EXPORT_MEDIA:
            return JSONResponse({"error": "format must be xlsx or docx"}, status_code=404)
        return None

    @app.get("/export/{fmt}/analysis/{name}")
    def export_analysis(fmt: str, name: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            analysis = st.analysis_for(name, sch)
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        quality = compute_schedule_quality(sch, analysis.cpm)
        tableset = TableSet(
            f"Schedule Forensics - {sch.name}",
            (
                schedule_summary_table(sch),
                dcma_table(analysis.audit),
                metric_results_table("Schedule quality (Acumen)", quality),
                metric_results_table("Float bands", analysis.float_bands),
                metric_results_table("Completion performance", analysis.completion),
                metric_results_table("Baseline compliance", analysis.compliance),
                findings_table(analysis.findings),
                activities_table(analysis.activity_rows),
            ),
        )
        return _export_response(fmt, tableset, f"{name}-analysis")

    @app.get("/export/{fmt}/path/{name}")
    def export_path(
        fmt: str,
        name: str,
        target: int = Query(...),
        secondary: int = Query(10),
        tertiary: int = Query(20),
    ) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        try:
            cpm = st.analysis_for(name, sch).cpm
        except CPMError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        data = _driving_data(sch, cpm, target, secondary, tertiary)
        rows = data.get("rows") or []
        if not rows:
            return JSONResponse({"error": str(data.get("note", "no path"))}, status_code=422)
        tableset = TableSet(
            f"Path analysis - {sch.name}",
            (driving_table(rows, target),),  # type: ignore[arg-type]
        )
        return _export_response(fmt, tableset, f"{name}-path-uid{target}")

    @app.get("/export/{fmt}/trend")
    def export_trend(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        tableset = TableSet(
            "Schedule-quality trend", trend_tables(compute_quality_trend(schedules, cpms))
        )
        return _export_response(fmt, tableset, "trend")

    @app.get("/export/{fmt}/cei")
    def export_cei(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave([s for _, s in st.ordered_versions()])
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt, TableSet("Bow Wave - CEI", bow_wave_tables(wave)), "bow-wave-cei"
        )

    @app.get("/export/{fmt}/forecast")
    def export_forecast(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        labels = [s.source_file or s.name for s in schedules]
        return _export_response(
            fmt, TableSet("Finish forecasts", forecast_tables(labels, sets)), "forecast"
        )

    @app.get("/export/{fmt}/compare")
    def export_compare(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        manip = detect_manipulation(
            schedules[-1], schedules[-2], current_cpm=cpms[-1], prior_cpm=cpms[-2]
        )
        tableset = TableSet(
            "Compare - manipulation signals",
            (findings_table(manip),),
        )
        return _export_response(fmt, tableset, "compare-signals")

    @app.get("/brief", response_class=HTMLResponse)
    def brief_view() -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Diagnostic Brief",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to build the "
                "diagnostic brief.</div>",
            )
        brief = build_brief(schedules, cpms)
        return _page(
            st,
            "Diagnostic Brief",
            _export_bar("brief") + _skipped_notice(skipped) + _brief_body(brief),
        )

    @app.get("/export/{fmt}/brief")
    def export_brief(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        brief = build_brief(schedules, cpms)
        if fmt == "docx":
            blocks = cast("list[Block]", brief_blocks(brief))
            return Response(
                content=render_document(blocks),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="diagnostic-brief.docx"'},
            )
        tables = tuple(s.table for s in brief.sections if s.table is not None)
        questions = Table(
            "Questions the data raises",
            ("#", "Question (cited)"),
            tuple(
                (i + 1, stmt.rendered())
                for i, stmt in enumerate(p for s in brief.sections for p in s.paragraphs)
            ),
        )
        return _export_response(
            fmt, TableSet(brief.title, (*tables, questions)), "diagnostic-brief"
        )

    @app.get("/briefing", response_class=HTMLResponse)
    def briefing_view() -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Executive Briefing",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least one analyzable schedule to build the briefing.</div>",
            )
        # the session-selected backend may polish the briefing prose (citations + figures
        # re-verified by reattach inside build_briefing); a generation failure degrades to
        # the deterministic briefing instead of a 500
        try:
            briefing = build_briefing(schedules, cpms=cpms, backend=_active_backend(st))
        except Exception:
            logger.warning("AI briefing generation failed; serving the deterministic briefing")
            briefing = build_briefing(schedules, cpms=cpms)
        body = _skipped_notice(skipped) + _briefing_body(briefing)
        return _page(st, "Executive Briefing", body)

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> HTMLResponse:
        st = session()
        return _page(st, "AI Settings", _settings_body(st))

    @app.post("/settings")
    def update_settings(
        classification: str = Form("CLASSIFIED"),
        backend: str = Form("ollama"),
        model: str = Form("llama3.1:8b"),
        qa_mode: str = Form("interpretive"),
        openai_endpoint: str = Form("http://127.0.0.1:1234"),
        second_backend: str = Form("none"),
        second_model: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        try:
            cls = Classification(classification)
        except ValueError:
            cls = Classification.CLASSIFIED  # unknown -> safe default
        if qa_mode not in ("interpretive", "strict"):
            qa_mode = "interpretive"
        if second_backend not in ("none", "ollama", "openai"):
            second_backend = "none"
        # the backend constructor enforces loopback too (Law 1) — this just keeps a typo'd
        # remote host from sitting in the config looking accepted
        if not is_loopback_host(urlparse(openai_endpoint.strip()).hostname or ""):
            openai_endpoint = "http://127.0.0.1:1234"
        st.ai_config = AIConfig(
            classification=cls,
            backend=backend,
            model=model,
            endpoint=st.ai_config.endpoint,
            qa_mode=qa_mode,
            openai_endpoint=openai_endpoint.strip(),
            second_backend=second_backend,
            second_model=second_model.strip(),
        )
        st.backend_cache = None  # re-route immediately — a settings change must take effect now
        st.second_cache = None
        return RedirectResponse(url="/settings", status_code=303)

    @app.get("/help", response_class=HTMLResponse)
    def help_page() -> HTMLResponse:
        st = session()
        rows = "".join(
            f"<tr><td>{_e(d.name)}</td><td>{_e(d.definition)}</td>"
            f"<td><code>{_e(d.formula)}</code></td><td class=muted>{_e(d.source)}</td></tr>"
            for d in METRIC_DICTIONARY.values()
        )
        body = (
            "<div class=panel><h2>Metric dictionary</h2>"
            "<p class=muted>Every metric the tool emits, with its formula and source. "
            "Each computed value also cites file + UniqueID + task name so you can verify it "
            "in the parent schedule.</p>"
            f"<table><tr><th>Metric</th><th>Definition</th><th>Formula</th><th>Source</th></tr>{rows}</table></div>"
        )
        return _page(st, "Metric Dictionary", body)

    @app.post("/target")
    def set_target(uid: str = Form(""), next_url: str = Form("/")) -> RedirectResponse:
        """Set (or clear, with a blank/invalid uid) the session-wide target activity."""
        st = session()
        st.target_uid = _parse_uid(uid)
        # local redirect only: a path on this app, never a scheme/host ("//host" included)
        dest = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/session/wipe")
    def wipe() -> RedirectResponse:
        st = session()
        st.schedules.clear()
        st.analyses.clear()
        st.polished.clear()
        st.flash = None
        st.target_uid = None
        logger.info("session wiped")
        return RedirectResponse(url="/", status_code=303)

    @app.get("/healthz")
    def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "loaded": len(session().schedules)})

    return app


def _safe_filename(name: str) -> str:
    """Strip characters that could break out of the Content-Disposition filename (header hygiene)."""
    return name.translate({ord(c): None for c in '"\\\r\n'})


def _clean_key(name: str) -> str:
    """A friendly schedule key: the filename with all supported extensions stripped."""
    exts = {e.lower() for e in supported_extensions()}
    path = Path(Path(name).name)
    while path.suffix.lower() in exts:
        path = path.with_suffix("")
    return path.name or "schedule"


def _unique_key(base: str, existing: dict[str, Schedule]) -> str:
    """``base`` unless taken, else ``base (2)``, ``base (3)``, … so uploads never collide."""
    if base not in existing:
        return base
    counter = 2
    while f"{base} ({counter})" in existing:
        counter += 1
    return f"{base} ({counter})"


def _parse_upload(name: str, data: bytes) -> Schedule:
    """Parse uploaded bytes by extension — text formats in memory, .mpp via a temp file."""
    # decode EXACTLY like the file-path importers so the same file can never parse
    # differently (or reject) depending on whether it was opened or uploaded
    suffix = Path(name).suffix.lower()
    if suffix == ".json":
        return parse_json_text(data.decode("utf-8-sig"))
    if suffix in {".xml", ".mspdi"}:
        return parse_mspdi_text(data.decode("utf-8-sig", errors="replace"))
    if suffix == ".xer":
        return parse_xer_text(decode_xer_bytes(data))
    # native .mpp / .mpt — needs the MPXJ runner + a JRE. Write into a temp *directory* and
    # close the file before parsing: on Windows an open NamedTemporaryFile handle blocks the
    # MPXJ java subprocess from reading the path (the upload would always fail on Windows).
    with tempfile.TemporaryDirectory(prefix="sf-upload-") as tmp:
        temp_path = Path(tmp) / f"upload{suffix or '.mpp'}"
        temp_path.write_bytes(data)
        return load_schedule(temp_path)


def _status_class(status: object) -> str:
    # the values are CSS class names (not secrets); B105 is a false positive here.
    return {"PASS": "pass", "FAIL": "fail"}.get(str(status), "na")  # nosec B105


def _unschedulable_panel(sch: Schedule, exc: CPMError) -> str:
    """A readable notice when the network itself cannot be scheduled (e.g. a logic cycle).

    The schedule still loaded; only the CPM-derived analysis is unavailable. We name the
    reason (no schedule contents — CUI) instead of returning a server error.
    """
    return (
        f"<div class=panel><h2>{_e(sch.name)} &mdash; cannot compute the network</h2>"
        f'<div class="notice err">This schedule loaded, but its critical-path network '
        f"could not be solved: {_e(exc)}</div>"
        "<p class=muted>The most common cause is a circular dependency (a logic loop) in the "
        "predecessor/successor links. Open the file in Microsoft Project and resolve the loop, "
        "then re-import. The activity list is still available from the dashboard.</p></div>"
    )


def _target_panel(sch: Schedule, analysis: _Analysis, target: int) -> str:
    """The session target activity's metrics in THIS schedule (or a gentle absence note)."""
    row = next((r for r in analysis.activity_rows if r["unique_id"] == target), None)
    if row is None:
        return (
            f"<div class=panel><h2>Target activity UID {target}</h2>"
            f'<p class="notice err">This schedule does not contain UniqueID {target}.</p></div>'
        )
    variance = ""
    if row["finish"] and row["baseline_finish"]:
        days = (
            dt.date.fromisoformat(str(row["finish"]))
            - dt.date.fromisoformat(str(row["baseline_finish"]))
        ).days
        cls = "fail" if days > 0 else "pass"
        variance = (
            f"<tr><th>Finish vs baseline</th>"
            f"<td><b class={cls}>{days:+d} calendar days</b></td></tr>"
        )
    flags = ", ".join(
        label
        for label, on in (
            ("critical", row["is_critical"]),
            ("milestone", row["is_milestone"]),
            ("summary", row["is_summary"]),
        )
        if on
    )
    cells = "".join(
        f"<tr><th>{label}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Start", row["start"] or "—"),
            ("Finish", row["finish"] or "—"),
            ("Baseline finish", row["baseline_finish"] or "—"),
            (
                "Total float (days)",
                row["total_float_days"] if row["total_float_days"] is not None else "—",
            ),
            (
                "Free float (days)",
                row["free_float_days"] if row["free_float_days"] is not None else "—",
            ),
            ("% complete", row["percent_complete"]),
            ("Flags", flags or "—"),
        )
    )
    return f"""
<div class=panel><h2>Target activity &mdash; UID {target}: {_e(row["name"])}</h2>
<p class=muted>The session-wide target: the trace below runs to it automatically, the Trend page
focuses on it, and Compare shows its movement. Set or clear it in the header.</p>
<table>{cells}{variance}</table>
<p class=cite>{_e(row["name"])} (UID {target}, {_e(row["source_file"] or "schedule")})</p></div>"""


def _float_bands_panel(analysis: _Analysis) -> str:
    """The deck-style low-float bands (M15/ADR-0030): to-go work running out of room."""
    fb = analysis.float_bands

    def cell(mid: str) -> str:
        r = fb[mid]
        return f"<td>{r.count} <span class=muted>({r.value:g}%)</span></td>"

    pop = fb["float_total_0"].population
    return f"""
<div class=panel><h2>Float analysis &mdash; low-float bands</h2>
<p class=muted>Of the {pop} incomplete activities, how many are running out of room: at 0 days
of float (critical or negative), under 5, and under 10 working days &mdash; cumulative bands on
this schedule's calendar. A swelling low-float band is the early warning that the schedule is
losing its ability to absorb slips.</p>
<table><tr><th></th><th>0 days</th><th>&lt; 5 days</th><th>&lt; 10 days</th></tr>
<tr><th>Total float</th>{cell("float_total_0")}{cell("float_total_lt5")}{cell("float_total_lt10")}</tr>
<tr><th>Free float</th>{cell("float_free_0")}{cell("float_free_lt5")}{cell("float_free_lt10")}</tr>
</table></div>"""


def _completion_panel(analysis: _Analysis) -> str:
    """The deck-style completion-performance read-out (M15/ADR-0030)."""
    cp = analysis.completion

    def fmt(mid: str) -> str:
        r = cp[mid]
        if r.unit == "%":
            return f"{r.count} of {r.population} ({r.value:g}%)" if r.population else "&mdash;"
        if r.unit == "days":
            return f"{r.value:g} days (over {r.count})" if r.count else "&mdash;"
        return f"{r.value:g}" if r.population else "&mdash;"

    rows = "".join(
        f"<tr><th>{_e(label)}</th><td>{fmt(mid)}</td></tr>"
        for mid, label in (
            ("completed_ahead", "Completed ahead of baseline"),
            ("completed_on_schedule", "Completed on schedule"),
            ("completed_behind", "Completed behind baseline"),
            ("avg_days_ahead", "Average days ahead (early finishers)"),
            ("avg_days_late", "Average days late (late finishers)"),
            ("avg_completion_variance", "Average completion variance (+ = late)"),
            ("longer_than_planned", "Activities longer than planned"),
            ("shorter_than_planned", "Activities shorter than baseline"),
            ("duration_ratio_min", "Duration ratio (actual / baseline) — min"),
            ("duration_ratio_avg", "Duration ratio — average"),
            ("duration_ratio_max", "Duration ratio — max"),
            ("mei", "MEI (milestones finished / milestones due)"),
            ("epi", "EPI (execution events recorded / events expected)"),
            ("start_finish_ratio", "Start-to-Finish Ratio (scheduled pairs / actual pairs)"),
            ("elapsed_since_last_finish", "Schedule elapsed since latest actual finish"),
        )
    )
    return f"""
<div class=panel><h2>Completion performance</h2>
<p class=muted>How the completed work actually performed against its baseline: the
ahead / on-schedule / behind split, the days gained and lost, and actual-vs-baseline
durations. Day variances are calendar days.</p>
<table>{rows}</table></div>"""


def _path_body(keys: list[str], target_uid: int | None) -> str:
    """The SSI-style path-analysis workspace: controls, data grid left, scalable Gantt right.

    All interaction is client-side (`static/path.js`) over `/api/driving` — field
    add/remove, filters (incl. hide-completed), tier day-bands, zoom, the data-date
    line. The grounded ask-the-AI panel is the page-shell one (`_ask_panel_html`)."""
    options = "".join(f'<option value="{_e(k)}">{_e(k)}</option>' for k in keys)
    return f"""
<div class=panel><h2>Path analysis &mdash; driving / secondary / tertiary to a target</h2>
<p class=muted>Pick a schedule and a target UniqueID: the driving path (slack &le; 0) and the
secondary/tertiary tiers within your day-bands trace back from it, SSI-style — data on the
left, a scalable timeline on the right with the gold data-date line. Add/remove columns,
filter rows, and hide completed work.</p>
<div class=viz-controls id=pathControls>
<label>Schedule <select id=pathSchedule>{options}</select></label>
<label>Target UID <input id=pathTarget type=number min=1 value="{target_uid if target_uid is not None else ""}" placeholder="UID"></label>
<label>Secondary &le; <input id=pathSec type=number min=1 value=10 title="days of driving slack"> d</label>
<label>Tertiary &le; <input id=pathTer type=number min=1 value=20 title="days of driving slack"> d</label>
<button id=pathRun type=button>Trace</button>
<label><input id=pathHideDone type=checkbox> hide 100% complete</label>
<label>Tier <select id=pathTier><option value="">all</option><option>DRIVING</option>
<option>SECONDARY</option><option>TERTIARY</option><option>BEYOND</option></select></label>
<label>Filter <input id=pathFilter type=text placeholder="name / UID contains"></label>
<label>Zoom <input id=pathZoom type=range min=2 max=40 value=8 title="pixels per day"></label>
</div>
<div id=pathFields class=muted></div>
<div class="export-bar" id=pathExport style="display:none"><a id=pathXlsx href="#">&#11015; Excel</a><a id=pathDocx href="#">&#11015; Word</a></div>
<div id=pathStatus class=muted></div>
<div id=pathView class=path-view></div></div>
<script src="/static/path.js"></script>"""


def _forecast_body(schedules: list[Schedule], sets: list[ForecastSet]) -> str:
    """The three-method finish-forecast page (M15/ADR-0030): logic vs throughput vs
    performance, plus the per-version forecast drift."""
    latest_sch, latest = schedules[-1], sets[-1]
    by_id = latest_sch.tasks_by_id
    method_rows = "".join(
        f"<tr><th>{_e(f.name)}</th>"
        f"<td><b>{f.finish.isoformat() if f.finish else '&mdash;'}</b></td>"
        f"<td class=muted>{_e(f.basis)}</td></tr>"
        for f in latest.forecasts
    )
    inputs = "".join(
        f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Data date", latest.as_of.isoformat() if latest.as_of else "none recorded"),
            ("Completed activities", latest.completed_count),
            ("To-go activities", latest.remaining_count),
            (
                "Historical completion rate",
                # `is not None`: a rate rounding to 0.0 must not display as absent (#67 class)
                f"{latest.rate_per_month:g} / month"
                if latest.rate_per_month is not None
                else "n/a",
            ),
            ("SPI(t)", f"{latest.spi_t:g}" if latest.spi_t is not None else "n/a"),
            (
                "Baseline (planned) finish",
                latest.planned_finish.isoformat() if latest.planned_finish else "n/a",
            ),
        )
    )
    cite = "; ".join(
        f"{by_id[uid].name} (UID {uid})" for uid in latest.citation_uids[:3] if uid in by_id
    )
    drift = ""
    if len(sets) >= 2:
        drift_rows = "".join(
            f"<tr><td>{_e(sch.source_file or sch.name)}</td>"
            f"<td>{fs.as_of.isoformat() if fs.as_of else '-'}</td>"
            + "".join(
                f"<td>{f.finish.isoformat() if f.finish else '&mdash;'}</td>" for f in fs.forecasts
            )
            + "</tr>"
            for sch, fs in zip(schedules, sets, strict=True)
        )
        drift = f"""
<div class=panel><h2>Forecast drift across versions</h2>
<p class=muted>The three forecasts re-run per loaded version (oldest first). Forecasts that
keep sliding right are the bow-wave signature; methods that diverge from the CPM date tell
you the logic and the observed performance disagree.</p>
<div class=viz-controls>
<button id=prevDrift type=button>&#9664; Prev</button>
<span id=driftLabel class=muted></span>
<button id=nextDrift type=button>Next &#9654;</button>
<button id=driftPlay type=button>&#9654; Auto-play</button>
</div>
<p class=muted>Each forecast marker sits on a <b>locked date axis</b> (held fixed across every
version); step or play to watch the three forecasts drift toward later dates as the project
progresses. Faint markers are the prior version's forecasts.</p>
<div id=driftChart></div>
<table><tr><th>Version</th><th>Data date</th><th>CPM</th><th>Completion rate</th>
<th>Earned schedule</th></tr>{drift_rows}</table></div>
<script src="/static/drift.js"></script>"""
    return f"""
<div class=panel><h2>Finish forecast &mdash; {_e(latest_sch.name)}</h2>
<p class=muted>Three independent answers to "when will it really end": the schedule's own
logic (CPM), the observed completion throughput, and earned-schedule performance
(IEAC(t) = AT + (PD &minus; ES) / SPI(t)). Methods that disagree are themselves a finding.
A method whose inputs are missing shows "&mdash;" &mdash; never a fabricated date.</p>
<table><tr><th>Method</th><th>Forecast finish</th><th>Basis</th></tr>{method_rows}</table>
<h3>Inputs</h3><table>{inputs}</table>
<p class=cite>Finish-controlling: {_e(cite)}</p></div>{drift}"""


def _forecast_data(schedules: list[Schedule], sets: list[ForecastSet]) -> dict[str, object]:
    # LOCKED date axis (item 5) for the drift animation: span every version's three
    # forecasts + data dates + baseline finishes, so the time scale is held fixed through
    # the stepper and the forecasts visibly drift right rather than the axis rescaling.
    axis_dates: list[dt.date] = []
    for fs in sets:
        if fs.as_of is not None:
            axis_dates.append(fs.as_of)
        if fs.planned_finish is not None:
            axis_dates.append(fs.planned_finish)
        axis_dates.extend(f.finish for f in fs.forecasts if f.finish is not None)
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    # the method order/labels the animation plots (stable, deterministic)
    methods = [{"id": f.method_id, "name": f.name} for f in (sets[-1].forecasts if sets else [])]
    return {
        "axis": axis,
        "methods": methods,
        "versions": [
            {
                "label": sch.source_file or sch.name,
                "as_of": fs.as_of.isoformat() if fs.as_of else None,
                "completed": fs.completed_count,
                "remaining": fs.remaining_count,
                "rate_per_month": fs.rate_per_month,
                "spi_t": fs.spi_t,
                "planned_finish": fs.planned_finish.isoformat() if fs.planned_finish else None,
                "forecasts": {
                    f.method_id: f.finish.isoformat() if f.finish else None for f in fs.forecasts
                },
            }
            for sch, fs in zip(schedules, sets, strict=True)
        ],
    }


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _calendar_panel(sch: Schedule) -> str:
    """The working calendar the analysis runs on — imported from the file (ADR-0028).

    Every computed date, float, and day-denominated threshold rides this calendar, so the
    analyst must be able to verify the time basis (and spot a fail-soft default) on the page.
    """
    cal = sch.calendar
    days = ", ".join(_WEEKDAY_NAMES[d] for d in cal.work_weekdays)
    hours_text = f"{cal.working_minutes_per_day / 60:g} h/day ({cal.working_minutes_per_day} min)"
    if cal.holidays:
        shown = ", ".join(d.isoformat() for d in cal.holidays[:10])
        extra = f" (+{len(cal.holidays) - 10} more)" if len(cal.holidays) > 10 else ""
        holidays = f"{len(cal.holidays)} — {shown}{extra}"
    else:
        holidays = "none"
    return f"""
<div class=panel><h2>Working calendar</h2>
<p class=muted>The time basis behind every computed date, float, and day-denominated
threshold — imported from the file's project calendar (the standard 8h/Mon-Fri default
when the file carries none).</p>
<table>
<tr><th>Calendar</th><td>{_e(cal.name)}</td></tr>
<tr><th>Working day</th><td>{_e(hours_text)}</td></tr>
<tr><th>Work week</th><td>{_e(days)}</td></tr>
<tr><th>Holidays</th><td>{_e(holidays)}</td></tr>
</table></div>"""


def _stat_cards(cards: list[tuple[str, str]]) -> str:
    """A responsive grid of label/value stat cards (the deck's KPI-card row)."""
    items = "".join(
        f"<div class=stat-card><div class=stat-value>{_e(value)}</div>"
        f"<div class=stat-label>{_e(label)}</div></div>"
        for label, value in cards
    )
    return f"<div class=stat-grid>{items}</div>"


def _count_bar_table(headers: tuple[str, str], rows: list[tuple[str, int, float]]) -> str:
    """A count + percent table with an inline percent bar (deck pie/pivot, as a table)."""
    body = "".join(
        f"<tr><td>{_e(label)}</td><td>{count}</td>"
        f'<td class=pct-cell><span class=pct-bar style="width:{min(pct, 100):.0f}%"></span>'
        f"<span class=pct-num>{pct:.1f}%</span></td></tr>"
        for label, count, pct in rows
    )
    return (
        f"<table class=card-table><tr><th>{_e(headers[0])}</th><th>Count</th>"
        f"<th>{_e(headers[1])}</th></tr>{body}</table>"
    )


def _card_body(key: str, sch: Schedule, analysis: _Analysis) -> str:
    """The deck's *Metrics* page (PBIX page 1) — the schedule's ID card.

    Reproduces the landing-page aggregates: activity makeup, status split, completion
    performance, the primary-constraint distribution, and the KPI cards — all from the
    engine outputs already computed for this schedule (no recomputation of the CPM)."""
    makeup = compute_activity_makeup(sch)
    constraints = compute_constraint_distribution(sch)
    cpm, comp = analysis.cpm, analysis.completion
    cal = sch.calendar

    # makeup pie -> count/percent table
    total = makeup.total or 1
    makeup_tbl = _count_bar_table(
        ("Task makeup", "% of activities"),
        [
            ("Normal", makeup.normal, 100.0 * makeup.normal / total),
            ("Milestones", makeup.milestones, 100.0 * makeup.milestones / total),
            ("Summaries", makeup.summaries, 100.0 * makeup.summaries / (total + makeup.summaries)),
        ],
    )
    status_tbl = _count_bar_table(
        ("Activity status", "% of activities"),
        [
            ("Complete", makeup.complete, 100.0 * makeup.complete / total),
            ("In progress", makeup.in_progress, 100.0 * makeup.in_progress / total),
            ("Planned", makeup.planned, 100.0 * makeup.planned / total),
        ],
    )
    # completion-performance split (deck "Completion Performance" pie)
    split = [
        ("Completed ahead", comp["completed_ahead"]),
        ("Completed on schedule", comp["completed_on_schedule"]),
        ("Completed behind", comp["completed_behind"]),
    ]
    perf_tbl = _count_bar_table(
        ("Completion performance", "% of measured completions"),
        [(label, r.count, r.value) for label, r in split],
    )
    constraint_tbl = _count_bar_table(
        ("Primary constraint", "% of activities"),
        [(r.constraint_type, r.count, r.percent) for r in constraints],
    )

    # KPI cards (reuse the engine outputs the report already computed)
    starts = [t.start for t in non_summary(sch) if t.start is not None]
    earliest = min(starts).date().isoformat() if starts else "—"
    latest_finish = (
        offset_to_datetime(sch.project_start, cpm.project_finish, cal).date().isoformat()
    )
    critical = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and (tm := cpm.timings.get(t.unique_id)) is not None
        and tm.total_float <= 0
    )
    togo_normal = sum(
        1 for t in non_summary(sch) if t.percent_complete < 100.0 and not t.is_milestone
    )
    togo_ms = sum(1 for t in non_summary(sch) if t.percent_complete < 100.0 and t.is_milestone)
    ahead, late = comp["avg_days_ahead"], comp["avg_days_late"]
    stale = comp["elapsed_since_last_finish"]
    cards = _stat_cards(
        [
            ("Earliest start", earliest),
            ("Computed finish", latest_finish),
            ("Data date", sch.status_date.date().isoformat() if sch.status_date else "—"),
            ("Activities complete", f"{100.0 * makeup.complete / total:.1f}%"),
            ("Critical (incomplete)", str(critical)),
            ("To-go activities", str(togo_normal)),
            ("To-go milestones", str(togo_ms)),
            ("Avg days ahead", f"{ahead.value:g}" if ahead.population else "—"),
            ("Avg days late", f"{late.value:g}" if late.population else "—"),
            ("% elapsed since last finish", f"{stale.value:g}%" if stale.population else "—"),
        ]
    )
    return f"""
<div class=panel><h2>Schedule card &mdash; {_e(sch.name)}</h2>
<p class=muted>The schedule's ID card (the reference deck's <i>Metrics</i> page): activity
makeup, status, completion performance, the primary-constraint distribution, and the
headline KPI cards — every figure computed from this file and verifiable on the
<a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
{cards}</div>
<div class="panel"><div class=card-cols>
<div>{makeup_tbl}</div><div>{status_tbl}</div>
<div>{perf_tbl}</div><div>{constraint_tbl}</div>
</div></div>"""


def _analysis_body(
    key: str,
    sch: Schedule,
    analysis: _Analysis,
    target: int | None = None,
    narrative: Narrative | None = None,
) -> str:
    audit = analysis.audit
    audit_rows = "".join(
        f'<tr><td>{_e(c.name)}</td><td class="{_status_class(c.status)}">{_e(c.status)}</td>'
        f"<td>{_e(round(c.value, 1))}{_e(c.unit)}</td>"
        f"<td class=muted>{_e(c.suggested_improvement)}</td></tr>"
        for c in audit.checks
    )
    findings = analysis.findings
    find_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.category)}</td>'
        f"<td>{_e(f.title)}</td><td class=muted>{_e(f.course_of_action)}</td>"
        f"<td class=cite>{_e('; '.join(str(c) for c in f.citations[:2]))}"
        f"{_e(f' +{len(f.citations) - 2} more' if len(f.citations) > 2 else '')}</td></tr>"
        for f in findings
    )
    story_source = narrative if narrative is not None else analysis.narrative
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in story_source.statements)
    target_panel = _target_panel(sch, analysis, target) if target is not None else ""
    viz = f"""{target_panel}
<div class=panel><h2>Interactive analysis</h2>
<div id=viz data-name="{_e(key)}">
<div class=charts id=charts></div>
<div class=viz-controls>Driving path to target UID:
<input id=targetUid type=number min=1 placeholder="UID" value="{target if target is not None else ""}">
secondary&le;<input id=secMax type=number value=10>d
tertiary&le;<input id=terMax type=number value=20>d
<button id=ganttBtn type=button>Trace</button>
<label><input id=showDone type=checkbox checked> show completed tasks</label></div>
<div id=gantt></div>
<h3>Activities &amp; Gantt <span class=muted>(add/remove columns; bars on the right — red = critical,
diamonds = milestones, thin = summaries, amber line = data date; click a row to drill into its
metadata)</span></h3>
<div id=fieldToggles></div><div id=grid></div><div id=drill class=drill></div>
</div></div>
<script src="/static/app.js"></script>"""
    return f"""{viz}
{_calendar_panel(sch)}
{_float_bands_panel(analysis)}
{_completion_panel(analysis)}
<div class=panel><h2>{_e(sch.name)} &mdash; DCMA-14 audit</h2>
<p class=muted>{audit.passed} passed &middot; {audit.failed} failed &middot; {audit.not_applicable} N/A</p>
<table><tr><th>Check</th><th>Status</th><th>Value</th><th>Suggested improvement</th></tr>{audit_rows}</table></div>
<div class=panel><h2>Risks, opportunities &amp; concerns</h2>
<table><tr><th>Severity</th><th>Type</th><th>Finding</th><th>Course of action</th><th>Citations</th></tr>
{find_rows or "<tr><td colspan=5 class=muted>No findings — schedule is well-formed.</td></tr>"}</table></div>
<div class=panel><h2>AI narrative (local, cited)</h2><ul>{story}</ul></div>"""


def _brief_body(brief: DiagnosticBrief) -> str:
    """The Diagnostic Brief page: cited prose + the finish table, print-friendly."""
    parts = [
        f"<div class=panel><h2>{_e(brief.title)}</h2>",
        f"<p class=muted>Report generated on {brief.generated_on.strftime('%A, %B %d, %Y')}. "
        "Every claim carries its citation [schedule, UID, activity] — see the final "
        "section for how to verify.</p></div>",
    ]
    for section in brief.sections:
        parts.append(f"<div class=panel><h2>{_e(section.heading)}</h2>")
        for stmt in section.paragraphs:
            parts.append(f"<p>{_e(stmt.rendered())}</p>")
        if section.table is not None:
            head = "".join(f"<th>{_e(str(h))}</th>" for h in section.table.headers)
            rows = "".join(
                "<tr>"
                + "".join(f"<td>{_e('' if c is None else str(c))}</td>" for c in row)
                + "</tr>"
                for row in section.table.rows
            )
            parts.append(f"<table><tr>{head}</tr>{rows}</table>")
        parts.append("</div>")
    return "".join(parts)


def _export_bar(path: str, *, xlsx_id: str = "", docx_id: str = "") -> str:
    """The per-view 'download as Excel / Word' links (local files only — Law 1)."""
    a = f' id="{xlsx_id}"' if xlsx_id else ""
    b = f' id="{docx_id}"' if docx_id else ""
    return (
        f'<div class="export-bar"><a{a} href="/export/xlsx/{path}">&#11015; Excel</a>'
        f'<a{b} href="/export/docx/{path}">&#11015; Word</a></div>'
    )


def _analysis_data(sch: Schedule, analysis: _Analysis) -> dict[str, object]:
    audit = analysis.audit
    compliance = analysis.compliance
    return {
        "name": sch.name,
        "source_file": sch.source_file,
        "tasks": len(sch.tasks),
        "status_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "calendar": {
            "name": sch.calendar.name,
            "working_minutes_per_day": sch.calendar.working_minutes_per_day,
            "work_weekdays": list(sch.calendar.work_weekdays),
            "holidays": [d.isoformat() for d in sch.calendar.holidays],
        },
        "dcma": {
            c.metric_id: {"status": str(c.status), "count": c.count, "value": c.value}
            for c in audit.checks
        },
        "baseline_compliance": {k: v.count for k, v in compliance.items()},
        "float_bands": {
            k: {"count": v.count, "population": v.population, "value": v.value}
            for k, v in analysis.float_bands.items()
        },
        "completion": {
            k: {"count": v.count, "population": v.population, "value": v.value, "unit": v.unit}
            for k, v in analysis.completion.items()
        },
        "activities": analysis.activity_rows,
        "findings": [
            {
                "severity": str(f.severity),
                "category": str(f.category),
                "title": f.title,
                "citations": [
                    {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                    for c in f.citations
                ],
            }
            for f in analysis.findings
        ],
    }


def _iso_date(value: object) -> str:
    return value.date().isoformat() if hasattr(value, "date") else ""


def _activity_rows(sch: Schedule, cpm: CPMResult) -> list[dict[str, object]]:
    """Per-activity rows for the interactive grid + Gantt (float in days, citable metadata).

    Scheduled activities carry their CPM floats; WBS summary rows (which the CPM excludes)
    are included too so the Gantt reads like the source plan, with null floats.
    """
    by_id = sch.tasks_by_id
    per_day = sch.calendar.working_minutes_per_day
    rows: list[dict[str, object]] = []
    for fr in analyze_floats(sch, cpm):
        task = by_id[fr.unique_id]
        rows.append(
            {
                "unique_id": fr.unique_id,
                "name": task.name,
                "wbs": task.wbs or "",
                "start": _iso_date(task.start),
                "finish": _iso_date(task.finish),
                "baseline_start": _iso_date(task.baseline_start),
                "baseline_finish": _iso_date(task.baseline_finish),
                "duration_days": round(
                    task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
                )
                if per_day
                else 0.0,
                "total_float_days": float(fr.total_float_days),
                "free_float_days": float(fr.free_float_days),
                "percent_complete": task.percent_complete,
                "is_critical": fr.is_critical,
                "is_milestone": task.is_milestone,
                "is_summary": False,
                "resource_names": ", ".join(task.resource_names),
                "source_file": sch.source_file,
            }
        )
    for task in sch.tasks:
        if not task.is_summary:
            continue
        rows.append(
            {
                "unique_id": task.unique_id,
                "name": task.name,
                "wbs": task.wbs or "",
                "start": _iso_date(task.start),
                "finish": _iso_date(task.finish),
                "baseline_start": _iso_date(task.baseline_start),
                "baseline_finish": _iso_date(task.baseline_finish),
                "duration_days": round(task.duration_minutes / per_day, 1) if per_day else 0.0,
                "total_float_days": None,
                "free_float_days": None,
                "percent_complete": task.percent_complete,
                "is_critical": False,
                "is_milestone": task.is_milestone,
                "is_summary": True,
                "resource_names": ", ".join(task.resource_names),
                "source_file": sch.source_file,
            }
        )
    rows.sort(key=lambda r: cast(int, r["unique_id"]))
    return rows


def _driving_data(
    sch: Schedule, cpm: CPMResult, target: int, secondary: int, tertiary: int
) -> dict[str, object]:
    """Driving-slack rows for the Gantt — tier + CPM ordinal positions for each traced UID."""
    by_id = sch.tasks_by_id
    if target not in by_id:
        return {
            "target_uid": target,
            "target_name": None,
            "rows": [],
            "note": f"UID {target} is not in this schedule.",
        }
    if by_id[target].is_summary:
        # summary rollups are not in the logic network — tracing one raised before
        return {
            "target_uid": target,
            "target_name": by_id[target].name,
            "rows": [],
            "note": f"UID {target} is a summary rollup — pick one of its activities instead.",
        }
    results = compute_driving_slack(
        sch,
        target_uid=target,
        secondary_max_days=secondary,
        tertiary_max_days=tertiary,
        cpm_result=cpm,
    )
    cal = sch.calendar
    per_day = cal.working_minutes_per_day
    # display the AS-SCHEDULED stored-date axis the slack math runs on — pure CPM
    # timings pack real files' completed work at the project start (wrong bars/dates)
    basis_start, basis_finish = date_basis(sch, cpm)
    date_driven = set(cpm.date_driven)

    def day(ordinal: int | None) -> str | None:
        if ordinal is None:
            return None
        return offset_to_datetime(sch.project_start, max(ordinal, 0), cal).date().isoformat()

    rows = []
    for uid in sorted(results):
        timing = cpm.timings.get(uid)
        task = by_id[uid]
        start_ord = basis_start.get(uid, timing.early_start if timing else None)
        finish_ord = basis_finish.get(uid, timing.early_finish if timing else None)
        if task.start is not None and task.finish is not None:
            # the same stored-or-CPM split date_basis() makes; stored dates render
            # verbatim (an actual start may legally predate the project start)
            start_iso: str | None = task.start.date().isoformat()
            finish_iso: str | None = task.finish.date().isoformat()
        else:
            start_iso, finish_iso = day(start_ord), day(finish_ord)
        rows.append(
            {
                "unique_id": uid,
                "name": task.name,
                "wbs": task.wbs or "",
                "tier": str(results[uid].tier),
                "driving_slack_days": int(results[uid].driving_slack_days),
                "on_driving_path": results[uid].on_driving_path,
                "start_ord": start_ord,
                "finish_ord": finish_ord,
                "start": start_iso,
                "finish": finish_iso,
                "baseline_finish": _iso_date(task.baseline_finish),
                "duration_days": round(
                    task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
                )
                if per_day
                else 0.0,
                "total_float_days": (
                    float(round(timing.total_float / per_day, 1)) if timing else None
                ),
                "percent_complete": task.percent_complete,
                "is_milestone": task.is_milestone,
                "date_driven": uid in date_driven,
                "resource_names": ", ".join(task.resource_names),
            }
        )
    # waterfall order: earliest finish first, so the chain cascades to the target's finish
    rows.sort(key=lambda r: (r["finish_ord"] is None, r["finish_ord"], r["start_ord"]))
    # the trace is logic-only by definition: say how much of the schedule it covers, so
    # absent (e.g. unlinked completed) work reads as explained, not missing
    activities = sum(1 for t in sch.tasks if not t.is_summary)
    coverage = (
        f"{len(rows)} of the schedule's {activities} activities have a logic path to this target"
    )
    driven_in_trace = sum(1 for r in rows if r["date_driven"])
    if driven_in_trace:
        coverage += f"; {driven_in_trace} traced date(s) are not supported by logic (see report)"
    return {
        "target_uid": target,
        "target_name": by_id[target].name,
        "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "coverage": coverage,
        "rows": rows,
    }


def _compare_body(
    prior: Schedule, current: Schedule, prior_cpm: CPMResult, current_cpm: CPMResult
) -> str:
    manip = detect_manipulation(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    trend = trend_across_versions([prior, current])
    impact = compute_net_finish_impact(current, prior, current_cpm=current_cpm, prior_cpm=prior_cpm)
    days = int(impact.value)
    if days < 0:
        impact_html = (
            f"<p>Net Finish Impact: <b class=fail>{days} calendar days</b> "
            "&mdash; the project finish moved later since the prior version.</p>"
        )
    elif days > 0:
        impact_html = (
            f"<p>Net Finish Impact: <b class=pass>+{days} calendar days</b> "
            "&mdash; the project finish moved earlier since the prior version.</p>"
        )
    else:
        impact_html = (
            "<p>Net Finish Impact: <b class=pass>0 calendar days</b> "
            "&mdash; the project finish is unchanged.</p>"
        )
    manip_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.title)}</td>'
        f"<td class=muted>{_e(f.course_of_action)}</td></tr>"
        for f in manip
    )
    trend_rows = "".join(
        f"<tr><td>{_e(p.source_file or p.version_index)}</td><td>{_e(p.project_finish.date())}</td>"
        f"<td>{p.completed}</td><td>{p.in_progress}</td><td>{p.critical}</td></tr>"
        for p in trend
    )
    return f"""
<div class=panel><h2>Version trend &mdash; {_e(prior.source_file or "prior")} &rarr; {_e(current.source_file or "current")}</h2>
<p class=muted>Versions are ordered by data date (oldest first); the trend reads prior &rarr; current.</p>
<table><tr><th>Version</th><th>Project finish</th><th>Completed</th><th>In&nbsp;progress</th><th>Critical</th></tr>{trend_rows}</table>
{impact_html}</div>
<div class=panel><h2>Manipulation-trend signals</h2>
<table><tr><th>Severity</th><th>Signal</th><th>Course of action</th></tr>
{manip_rows or "<tr><td colspan=3 class=muted>No manipulation signals detected (honest progress).</td></tr>"}</table></div>"""


def _focus_rows(
    schedules: list[Schedule], cpms: list[CPMResult], target: int
) -> list[tuple[str, str, str]]:
    """Per version: (label, the focus UID's computed finish date, % complete) — '—' if absent."""
    rows: list[tuple[str, str, str]] = []
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        timing = cpm.timings.get(target)
        task = sch.tasks_by_id.get(target)
        if timing is None or task is None:
            rows.append((label, "—", "—"))
            continue
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
        rows.append((label, finish.date().isoformat(), f"{task.percent_complete:g}%"))
    return rows


def _focus_panel(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
    title = f"Focus activity UID {target}" + (f" &mdash; {_e(names[0])}" if names else "")
    focus_rows = _focus_rows(schedules, cpms, target)
    rows = "".join(
        f"<tr><td>{_e(label)}</td><td>{_e(finish)}</td><td>{_e(pct)}</td></tr>"
        for label, finish, pct in focus_rows
    )
    note = "" if names else '<p class="notice err">No loaded version contains that UniqueID.</p>'
    known = [finish for _, finish, _ in focus_rows if finish != "—"]
    movement = ""
    if len(known) >= 2:
        # same sign convention as Net Finish Impact: negative == moved later (a slip)
        days = (dt.date.fromisoformat(known[0]) - dt.date.fromisoformat(known[-1])).days
        cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
        movement = (
            f"<p>Computed finish moved <b class={cls}>{days:+d} calendar days</b> "
            f"({word}) between the first and last version that schedule it.</p>"
        )
    return f"""
<div class=panel><h2>{title}</h2>{note}
<p class=muted>The focus activity's computed finish and progress across the versions
(its movement is charted below).</p>
<table><tr><th>Version</th><th>Computed finish</th><th>% complete</th></tr>{rows}</table>
{movement}</div>"""


def _trend_body(schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None) -> str:
    """The multi-version trend view: table, quality-trend sentences, pairwise signals, charts."""
    points = trend_across_versions(schedules, cpms)
    trend_rows = "".join(
        f"<tr><td>{_e(p.source_file or p.version_index)}</td>"
        f"<td>{_e(p.status_date.date()) if p.status_date else '-'}</td>"
        f"<td>{_e(p.project_finish.date())}</td>"
        f"<td>{p.completed}</td><td>{p.in_progress}</td><td>{p.critical}</td></tr>"
        for p in points
    )
    quality_items = "".join(
        f"<li>{_e(t.sentence())}</li>" for t in compute_quality_trend(schedules, cpms)
    )
    impact = compute_net_finish_impact(
        schedules[-1], schedules[0], current_cpm=cpms[-1], prior_cpm=cpms[0]
    )
    days = int(impact.value)
    cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
    signal_rows: list[str] = []
    for i in range(len(schedules) - 1):
        prior, current = schedules[i], schedules[i + 1]
        step = f"{_e(prior.source_file or prior.name)} &rarr; {_e(current.source_file or current.name)}"
        for f in detect_manipulation(current, prior, current_cpm=cpms[i + 1], prior_cpm=cpms[i]):
            signal_rows.append(
                f'<tr><td>{step}</td><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td>'
                f"<td>{_e(f.title)}</td><td class=muted>{_e(f.course_of_action)}</td></tr>"
            )
    focus_panel = _focus_panel(schedules, cpms, target) if target is not None else ""
    focus_form = f"""
<div class=panel><form method=get action=/trend class=viz-controls>
Focus the trend on a specific activity &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{'<a class=btn-link href="/trend?target=">clear focus</a>' if target is not None else ""}
</form></div>"""
    return f"""
<div class=panel><h2>Version trend &mdash; {len(schedules)} versions, oldest first (by data date)</h2>
<table><tr><th>Version</th><th>Data date</th><th>Project finish</th><th>Completed</th>
<th>In&nbsp;progress</th><th>Critical</th></tr>{trend_rows}</table>
<p>Net Finish Impact across the series: <b class={cls}>{days:+d} calendar days</b>
&mdash; the project finish moved {word} between the first and last version.</p></div>
{focus_form}{focus_panel}
<div class=panel><h2>Trend charts</h2><div id=trendCharts class=charts
data-target="{target if target is not None else ""}"></div></div>
<div class=panel><h2>Schedule-quality trends</h2>
<p class=muted>How each Acumen &sect;A quality metric moves across the versions.</p>
<ul>{quality_items}</ul></div>
<div class=panel><h2>Manipulation-trend signals (consecutive versions)</h2>
<table><tr><th>Step</th><th>Severity</th><th>Signal</th><th>Course of action</th></tr>
{"".join(signal_rows) or "<tr><td colspan=4 class=muted>No manipulation signals detected across the series (honest progress).</td></tr>"}</table></div>
<script src="/static/trend.js"></script>"""


def _trend_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None
) -> dict[str, object]:
    """JSON for the trend charts: per-version headline numbers + quality-metric series."""
    points = trend_across_versions(schedules, cpms)
    focus: dict[str, object] | None = None
    if target is not None:
        finishes: list[str | None] = []
        percents: list[float | None] = []
        for sch, cpm in zip(schedules, cpms, strict=True):
            timing = cpm.timings.get(target)
            task = sch.tasks_by_id.get(target)
            if timing is None or task is None:
                finishes.append(None)
                percents.append(None)
            else:
                fin = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
                finishes.append(fin.date().isoformat())
                percents.append(task.percent_complete)
        names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
        focus = {
            "uid": target,
            "name": names[0] if names else None,
            "finishes": finishes,
            "percents": percents,
        }
    return {
        "target": focus,
        "versions": [
            {
                "label": p.source_file or f"v{p.version_index + 1}",
                "status_date": p.status_date.date().isoformat() if p.status_date else None,
                "finish": p.project_finish.date().isoformat(),
                "completed": p.completed,
                "in_progress": p.in_progress,
                "critical": p.critical,
            }
            for p in points
        ],
        "quality": {
            t.metric_id: {"name": t.name, "values": list(t.values)}
            for t in compute_quality_trend(schedules, cpms)
        },
    }


def _cei_body(wave: BowWave) -> str:
    """The Bow Wave / CEI view: per-snapshot animated chart + the CEI summary table."""
    rows = "".join(
        f"<tr><td>{_e(s.label)}</td><td>{_e(s.cei_period or '—')}</td>"
        f"<td>{s.cei_planned if s.cei_planned is not None else '—'}</td>"
        f"<td>{s.cei_scheduled if s.cei_scheduled is not None else '—'}</td>"
        f"<td>{s.cei_finished if s.cei_finished is not None else '—'}</td>"
        f"<td><b class={'fail' if s.cei is not None and s.cei < 0.8 else 'pass'}>"
        f"{f'{s.cei:.2f}' if s.cei is not None else '—'}</b></td></tr>"
        for s in wave.snapshots
    )
    return f"""
<div class=panel><h2>Bow Wave &mdash; Activity Finishes by month</h2>
<p class=muted>Gold = baselined to finish, blue = scheduled to finish, green = actually
finished; the dashed line is the snapshot's data date. Work that keeps sliding right shows
as a swelling wave of blue just past each data date. Step through the snapshots or press
Auto-play to watch the wave move.</p>
<div class=viz-controls>
<button id=prevSnap type=button>&#9664; Prev</button>
<span id=snapLabel class=muted></span>
<button id=nextSnap type=button>Next &#9654;</button>
<button id=autoPlay type=button>&#9654; Auto-play</button>
</div>
<div id=ceiChart></div></div>
<div class=panel><h2>CEI &mdash; Current Execution Index</h2>
<p class=muted>For each snapshot: of the activities the <i>previous</i> snapshot planned to
finish in the following month, how many this snapshot re-scheduled for that month and how
how many of those planned activities actually finished by the end of it. CEI = completed-on-time &divide; previously planned (1.00 = executed to plan; an unplanned finish in the month earns no credit).</p>
<table><tr><th>Snapshot</th><th>Period</th><th>Previously planned</th><th>Re-scheduled</th>
<th>Actually finished</th><th>CEI</th></tr>{rows}</table></div>
<script src="/static/cei.js"></script>"""


def _cei_data(wave: BowWave) -> dict[str, object]:
    # locked Y-axis (item 5): the chart's count scale is the max bar across EVERY snapshot,
    # held through the animation so the bars stay comparable frame-to-frame (a per-snapshot
    # max made each frame rescale, hiding the bow wave's growth).
    max_count = max(
        (max([0, *s.baselined, *s.scheduled, *s.finished]) for s in wave.snapshots),
        default=0,
    )
    return {
        "months": list(wave.month_labels),
        "max_count": max_count,
        "snapshots": [
            {
                "label": s.label,
                "status_index": s.status_index,
                "baselined": list(s.baselined),
                "scheduled": list(s.scheduled),
                "finished": list(s.finished),
                "cei": s.cei,
                "cei_period": s.cei_period,
                "cei_planned": s.cei_planned,
                "cei_scheduled": s.cei_scheduled,
                "cei_finished": s.cei_finished,
            }
            for s in wave.snapshots
        ],
    }


def _cite_tag(citations: tuple[Citation, ...]) -> str:
    shown = "; ".join(str(c) for c in citations[:3])
    extra = f"; +{len(citations) - 3} more" if len(citations) > 3 else ""
    return f"{shown}{extra}"


def _briefing_table_html(section: BriefingSection) -> str:
    """A section's cited table: engine figures verbatim, a citation column per row."""
    table = section.table
    if table is None or not table.rows:
        return ""
    head = ""
    if table.headers:
        head = "<tr>" + "".join(f"<th>{_e(h)}</th>" for h in table.headers) + "<th></th></tr>"
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_e(cell)}</td>" for cell in row)
        + f"<td class=cite>{_e(_cite_tag(cites))}</td></tr>"
        for row, cites in zip(table.rows, table.row_citations, strict=True)
    )
    return f"<table>{head}{body}</table>"


def _briefing_body(briefing: ExecutiveBriefing) -> str:
    """Render the ExecutiveBriefing readably (M18 reformat): the workbook lede as prose,
    the cross-version trend and per-project quality verdicts as cited tables, and the
    project summaries as side-by-side cards (polished prose + a profile strip). Every
    statement and every table row carries its file + UID + task citation (§6)."""
    parts = [
        f"<div class=panel><h2>{_e(briefing.title)}</h2>"
        f"<p class=muted>Report generated on {_e(briefing.generated_on.strftime('%A, %B %d, %Y'))}."
        " Every statement cites file + UniqueID + task name; use the browser's Print for a"
        " hand-out copy.</p></div>"
    ]
    cards: list[str] = []

    def flush_cards() -> None:
        if cards:
            parts.append(f"<div class=brief-cards>{''.join(cards)}</div>")
            cards.clear()

    for section in briefing.sections:
        prose = "".join(
            f"<p>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></p>"
            for s in section.statements
        )
        if section.kind == "project":
            cards.append(
                f"<div class=panel><h2>{_e(section.heading)}</h2>"
                f"{prose}{_briefing_table_html(section)}</div>"
            )
            continue
        flush_cards()
        if section.kind == "lede":
            parts.append(
                f'<div class="panel brief-lede"><h2>{_e(section.heading)}</h2>{prose}</div>'
            )
        elif section.kind in ("trend", "quality"):
            parts.append(
                f"<div class=panel><h2>{_e(section.heading)}</h2>"
                f"{_briefing_table_html(section)}</div>"
            )
        else:  # prose fallback — any future section kind stays readable and cited
            items = "".join(
                f"<li>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></li>"
                for s in section.statements
            )
            parts.append(f"<div class=panel><h2>{_e(section.heading)}</h2><ul>{items}</ul></div>")
    flush_cards()
    return "".join(parts)


def _settings_body(state: SessionState) -> str:
    cfg = state.ai_config
    backend, _banner = route_backend(
        cfg,
        null_backend=NullBackend(),
        ollama_backend=_ollama_or_none(cfg),
        openai_backend=_openai_or_none(cfg),
    )
    models: tuple[str, ...] = ()
    try:
        models = backend.list_models()
    except Exception:
        models = ()
    model_list = ", ".join(_e(m) for m in models) or "<span class=muted>none available</span>"
    second = _second_backend(state)
    second_status = (
        f"reachable ({_e(second.name)})"
        if second is not None
        else ("off" if cfg.second_backend == "none" else "configured but not reachable")
    )

    def sel(value: str, current: str) -> str:
        return " selected" if value == current else ""

    return f"""
<div class=panel><h2>Local AI</h2>
<p>Active backend: <b>{_e(backend.name)}</b> &middot; installed models: {model_list}
&middot; cross-check model: <b>{second_status}</b></p>
<form action="/settings" method=post>
<p>Classification:
<select name=classification>
<option value=CLASSIFIED{sel("CLASSIFIED", cfg.classification)}>CLASSIFIED (CUI — local only)</option>
<option value=UNCLASSIFIED{sel("UNCLASSIFIED", cfg.classification)}>UNCLASSIFIED (cloud allowed, banner shown)</option>
</select></p>
<p>Backend:
<select name=backend>
<option value=ollama{sel("ollama", cfg.backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.backend)}>OpenAI-compatible (local — LM Studio / llamafile / vLLM)</option>
<option value=null{sel("null", cfg.backend)}>Null (offline, deterministic)</option>
<option value=cloud{sel("cloud", cfg.backend)}>Cloud (UNCLASSIFIED only)</option>
</select></p>
<p>Model: <input name=model value="{_e(cfg.model)}"></p>
<p>OpenAI-compatible endpoint (loopback only):
<input name=openai_endpoint size=28 value="{_e(cfg.openai_endpoint)}"
 title="LM Studio defaults to http://127.0.0.1:1234; llamafile to http://127.0.0.1:8080"></p>
<p>AI answer mode:
<select name=qa_mode>
<option value=interpretive{sel("interpretive", cfg.qa_mode)}>Interpretive — the model may analyze
and derive figures grounded in the cited facts (the "AI can err" disclaimer rides every answer)</option>
<option value=strict{sel("strict", cfg.qa_mode)}>Strict — any answer containing a figure the
engine never computed is discarded wholesale</option>
</select></p>
<p>Cross-check second model:
<select name=second_backend>
<option value=none{sel("none", cfg.second_backend)}>Off</option>
<option value=ollama{sel("ollama", cfg.second_backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.second_backend)}>OpenAI-compatible (local)</option>
</select>
 model id: <input name=second_model size=20 value="{_e(cfg.second_model)}"
 title="blank = the server's default/loaded model"></p>
<input type=submit value="Save"></form>
<p class=muted>The tool never sends schedule data off this machine while CLASSIFIED. Cloud is only
reachable after you explicitly switch to UNCLASSIFIED, and a persistent banner names the endpoint.
Either answer mode is prose-only: the cited facts shown with each answer are always engine-computed.
With a cross-check model on, both local models answer every question independently and the engine
compares their figures deterministically — agreement is corroboration, the citations stay the
ground truth.</p></div>"""


def _trigger_shutdown(app: FastAPI) -> None:
    """Request a graceful server stop, once (idempotent). No-op if no server is wired."""
    if app.state.shutting_down:
        return
    app.state.shutting_down = True
    callback = app.state.request_shutdown
    if callback is not None:
        callback()


def _is_idle(browser_seen: bool, idle_seconds: float, grace: float) -> bool:
    """True once a browser has connected and then gone quiet for longer than ``grace``."""
    return browser_seen and idle_seconds > grace


def _watchdog(app: FastAPI, *, poll: float = 2.0) -> None:
    """Stop the server when the browser stops beating (closing the window = tool off).

    In-flight requests hold it off: a long import/trace is the opposite of an absent
    operator, even when the beat goes quiet because the work itself is consuming the
    server (the mid-load self-shutdown the operator hit)."""
    grace = app.state.idle_grace
    while not app.state.shutting_down:
        time.sleep(poll)
        if app.state.active_requests > 0:
            continue
        if _is_idle(app.state.browser_seen, time.monotonic() - app.state.last_beat, grace):
            logger.info("no browser heartbeat for %.0fs — shutting the tool down", grace)
            _trigger_shutdown(app)
            return


def serve(
    app: FastAPI,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    server_factory: Callable[[uvicorn.Config], uvicorn.Server] = uvicorn.Server,
    log_level: str = "warning",
) -> None:
    """Serve ``app`` on a loopback address (refuses a non-local host — Law 1).

    Wires graceful shutdown: the in-page Quit control, ``POST /api/shutdown``, and (when the
    app was built with ``auto_shutdown``) the browser-gone watchdog all flip the server's
    ``should_exit``, so the process ends cleanly with nothing left running.
    """
    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind a non-loopback host {host!r} (CUI: local-only).")
    server = server_factory(uvicorn.Config(app, host=host, port=port, log_level=log_level))
    app.state.request_shutdown = lambda: setattr(server, "should_exit", True)
    if app.state.auto_shutdown:
        threading.Thread(target=_watchdog, args=(app,), daemon=True).start()
    server.run()


def run(
    host: str = "127.0.0.1", port: int = 8765, *, auto_shutdown: bool = False
) -> None:  # pragma: no cover - server entrypoint (covered via serve() unit tests)
    """Serve the app on loopback. ``auto_shutdown`` enables the browser-gone watchdog."""
    serve(create_app(auto_shutdown=auto_shutdown), host=host, port=port)
