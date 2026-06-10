"""Local-only FastAPI web app — the dark, NASA-themed forensic dashboard (M13, §6.A).

Runs entirely on the local machine (binds 127.0.0.1 only): upload up to ten schedules,
see each one's DCMA audit, Acumen §A/§C metrics, cited risk/opportunity/concern findings
and AI narrative, compare two versions (manipulation trends + Net Finish Impact), manage the
local AI model + classification (with the persistent CUI banner), browse the in-tool metric
dictionary, and wipe the session. No schedule content is ever logged (paths/counts only —
CUI), and the AI never leaves the box (`ai.route_backend` fail-closed). Interactive
Power-BI-style visuals are layered on at M14; M13 is the shell + server-rendered views.
"""

from __future__ import annotations

import html
import logging
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Template

from schedule_forensics.ai import (
    AIConfig,
    Classification,
    NullBackend,
    OllamaBackend,
    banner_for,
    route_backend,
)
from schedule_forensics.ai.briefing import ExecutiveBriefing, build_briefing
from schedule_forensics.ai.citations import Narrative
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.engine import (
    analyze_floats,
    audit_schedule,
    compute_cpm,
    compute_driving_slack,
    recommend,
)
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_net_finish_impact,
)
from schedule_forensics.engine.metrics._common import MetricResult, non_summary
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.engine.trend import compute_quality_trend, order_versions
from schedule_forensics.importers import (
    MAX_FILES,
    ImporterError,
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
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css"></head><body>
<header><h1>&#9650; SCHEDULE FORENSICS</h1>
<nav><a href="/">Dashboard</a><a href="/trend">Trend</a><a href="/briefing">Executive Briefing</a>
<a href="/settings">AI Settings</a><a href="/help">Metric Dictionary</a>
<form action="/session/wipe" method=post class=navform
onsubmit="return confirm('Wipe all loaded schedules?')"><button type=submit class=linkbtn>Wipe Session</button></form>
<a href="#" onclick="return sfQuit()" title="Stop the local server and exit">Quit</a></nav></header>
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
        findings=recommend(sch, current_cpm=cpm),
        # single-schedule narrative is deterministic (NullBackend) and CPM-threaded, so it is
        # safe to cache alongside the rest; if a per-request AI backend is wired in later, move
        # the narrative back out of the cached analysis.
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
    # under the same key recomputes. Bounded by the ≤10 loaded schedules; cleared on wipe.
    analyses: dict[str, tuple[Schedule, _Analysis]] = field(default_factory=dict)

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


def _page(state: SessionState, title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_LAYOUT.render(title=title, banner=_banner_html(state), body=body))


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
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

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
    async def upload(files: list[UploadFile]) -> RedirectResponse:
        st = session()
        accepted: list[str] = []
        errors: list[str] = []
        for upload_file in files[:MAX_FILES]:
            name = upload_file.filename or "schedule"
            data = await upload_file.read()
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
            return _page(st, "Not found", f"<div class=panel>No schedule named {_e(name)}.</div>")
        return _page(st, name, _analysis_body(name, sch, st.analysis_for(name, sch)))

    @app.get("/api/analysis/{name}")
    def analysis_json(name: str) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(_analysis_data(sch, st.analysis_for(name, sch)))

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
        return JSONResponse(
            _driving_data(sch, st.analysis_for(name, sch).cpm, target, secondary, tertiary)
        )

    @app.get("/compare", response_class=HTMLResponse)
    def compare() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Compare", "<div class=panel>Load at least two versions to compare.</div>"
            )
        keys = list(st.schedules)
        prior_key, current_key = keys[-2], keys[-1]
        prior, current = st.schedules[prior_key], st.schedules[current_key]
        # Forensic order is by data date (the Acumen/SSI ProjectTimeNow pattern), not load
        # order: the snapshot with the earlier status date is the prior, whichever was
        # uploaded first. Load order stands only when a data date is missing or tied.
        if (
            prior.status_date is not None
            and current.status_date is not None
            and prior.status_date > current.status_date
        ):
            prior_key, current_key = current_key, prior_key
            prior, current = current, prior
        prior_cpm = st.analysis_for(prior_key, prior).cpm
        current_cpm = st.analysis_for(current_key, current).cpm
        return _page(st, "Compare", _compare_body(prior, current, prior_cpm, current_cpm))

    @app.get("/trend", response_class=HTMLResponse)
    def trend_view() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Trend", "<div class=panel>Load at least two versions to see a trend.</div>"
            )
        pairs = st.ordered_versions()
        cpms = [st.analysis_for(k, s).cpm for k, s in pairs]
        return _page(st, "Trend", _trend_body([s for _, s in pairs], cpms))

    @app.get("/api/trend")
    def trend_json() -> JSONResponse:
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        pairs = st.ordered_versions()
        cpms = [st.analysis_for(k, s).cpm for k, s in pairs]
        return JSONResponse(_trend_data([s for _, s in pairs], cpms))

    @app.get("/briefing", response_class=HTMLResponse)
    def briefing_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Executive Briefing",
                "<div class=panel>Load at least one schedule to build the briefing.</div>",
            )
        pairs = st.ordered_versions()
        schedules = [s for _, s in pairs]
        cpms = [st.analysis_for(k, s).cpm for k, s in pairs]
        return _page(st, "Executive Briefing", _briefing_body(build_briefing(schedules, cpms=cpms)))

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> HTMLResponse:
        st = session()
        return _page(st, "AI Settings", _settings_body(st))

    @app.post("/settings")
    def update_settings(
        classification: str = Form("CLASSIFIED"),
        backend: str = Form("ollama"),
        model: str = Form("llama3.1:8b"),
    ) -> RedirectResponse:
        st = session()
        try:
            cls = Classification(classification)
        except ValueError:
            cls = Classification.CLASSIFIED  # unknown -> safe default
        st.ai_config = AIConfig(
            classification=cls, backend=backend, model=model, endpoint=st.ai_config.endpoint
        )
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

    @app.post("/session/wipe")
    def wipe() -> RedirectResponse:
        st = session()
        st.schedules.clear()
        st.analyses.clear()
        st.flash = None
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
    suffix = Path(name).suffix.lower()
    if suffix == ".json":
        return parse_json_text(data.decode("utf-8"))
    if suffix in {".xml", ".mspdi"}:
        return parse_mspdi_text(data.decode("utf-8"))
    if suffix == ".xer":
        return parse_xer_text(data.decode("utf-8", errors="replace"))
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


def _analysis_body(key: str, sch: Schedule, analysis: _Analysis) -> str:
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
    narrative = analysis.narrative
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in narrative.statements)
    viz = f"""
<div class=panel><h2>Interactive analysis</h2>
<div id=viz data-name="{_e(key)}">
<div class=charts id=charts></div>
<div class=viz-controls>Driving path to target UID:
<input id=targetUid type=number min=1 placeholder="UID">
secondary&le;<input id=secMax type=number value=10>d
tertiary&le;<input id=terMax type=number value=20>d
<button id=ganttBtn type=button>Trace</button></div>
<div id=gantt></div>
<h3>Activities <span class=muted>(toggle columns; click a row to drill into its metadata)</span></h3>
<div id=fieldToggles></div><div id=grid></div><div id=drill class=drill></div>
</div></div>
<script src="/static/app.js"></script>"""
    return f"""{viz}
<div class=panel><h2>{_e(sch.name)} &mdash; DCMA-14 audit</h2>
<p class=muted>{audit.passed} passed &middot; {audit.failed} failed &middot; {audit.not_applicable} N/A</p>
<table><tr><th>Check</th><th>Status</th><th>Value</th><th>Suggested improvement</th></tr>{audit_rows}</table></div>
<div class=panel><h2>Risks, opportunities &amp; concerns</h2>
<table><tr><th>Severity</th><th>Type</th><th>Finding</th><th>Course of action</th><th>Citations</th></tr>
{find_rows or "<tr><td colspan=5 class=muted>No findings — schedule is well-formed.</td></tr>"}</table></div>
<div class=panel><h2>AI narrative (local, cited)</h2><ul>{story}</ul></div>"""


def _analysis_data(sch: Schedule, analysis: _Analysis) -> dict[str, object]:
    audit = analysis.audit
    compliance = analysis.compliance
    return {
        "name": sch.name,
        "source_file": sch.source_file,
        "tasks": len(sch.tasks),
        "dcma": {
            c.metric_id: {"status": str(c.status), "count": c.count, "value": c.value}
            for c in audit.checks
        },
        "baseline_compliance": {k: v.count for k, v in compliance.items()},
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
    """Per-activity rows for the interactive grid (float in days, citable metadata)."""
    by_id = sch.tasks_by_id
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
                "total_float_days": float(fr.total_float_days),
                "free_float_days": float(fr.free_float_days),
                "percent_complete": task.percent_complete,
                "is_critical": fr.is_critical,
                "source_file": sch.source_file,
            }
        )
    return rows


def _driving_data(
    sch: Schedule, cpm: CPMResult, target: int, secondary: int, tertiary: int
) -> dict[str, object]:
    """Driving-slack rows for the Gantt — tier + CPM ordinal positions for each traced UID."""
    by_id = sch.tasks_by_id
    if target not in by_id:
        return {"target_uid": target, "target_name": None, "rows": []}
    results = compute_driving_slack(
        sch,
        target_uid=target,
        secondary_max_days=secondary,
        tertiary_max_days=tertiary,
        cpm_result=cpm,
    )
    rows = []
    for uid in sorted(results):
        timing = cpm.timings.get(uid)
        rows.append(
            {
                "unique_id": uid,
                "name": by_id[uid].name,
                "tier": str(results[uid].tier),
                "driving_slack_days": int(results[uid].driving_slack_days),
                "on_driving_path": results[uid].on_driving_path,
                "start_ord": timing.early_start if timing else None,
                "finish_ord": timing.early_finish if timing else None,
            }
        )
    # order the Gantt by start so the driving chain reads top-to-bottom
    rows.sort(key=lambda r: (r["start_ord"] is None, r["start_ord"]))
    return {"target_uid": target, "target_name": by_id[target].name, "rows": rows}


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


def _trend_body(schedules: list[Schedule], cpms: list[CPMResult]) -> str:
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
    return f"""
<div class=panel><h2>Version trend &mdash; {len(schedules)} versions, oldest first (by data date)</h2>
<table><tr><th>Version</th><th>Data date</th><th>Project finish</th><th>Completed</th>
<th>In&nbsp;progress</th><th>Critical</th></tr>{trend_rows}</table>
<p>Net Finish Impact across the series: <b class={cls}>{days:+d} calendar days</b>
&mdash; the project finish moved {word} between the first and last version.</p></div>
<div class=panel><h2>Trend charts</h2><div id=trendCharts class=charts></div></div>
<div class=panel><h2>Schedule-quality trends</h2>
<p class=muted>How each Acumen &sect;A quality metric moves across the versions.</p>
<ul>{quality_items}</ul></div>
<div class=panel><h2>Manipulation-trend signals (consecutive versions)</h2>
<table><tr><th>Step</th><th>Severity</th><th>Signal</th><th>Course of action</th></tr>
{"".join(signal_rows) or "<tr><td colspan=4 class=muted>No manipulation signals detected across the series (honest progress).</td></tr>"}</table></div>
<script src="/static/trend.js"></script>"""


def _trend_data(schedules: list[Schedule], cpms: list[CPMResult]) -> dict[str, object]:
    """JSON for the trend charts: per-version headline numbers + quality-metric series."""
    points = trend_across_versions(schedules, cpms)
    return {
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


def _cite_tag(citations: tuple[Citation, ...]) -> str:
    shown = "; ".join(str(c) for c in citations[:3])
    extra = f"; +{len(citations) - 3} more" if len(citations) > 3 else ""
    return f"{shown}{extra}"


def _briefing_body(briefing: ExecutiveBriefing) -> str:
    """Render the ExecutiveBriefing as panels (print-friendly; every sentence cited)."""
    parts = [
        f"<div class=panel><h2>{_e(briefing.title)}</h2>"
        f"<p class=muted>Report generated on {_e(briefing.generated_on.strftime('%A, %B %d, %Y'))}."
        " Every statement cites file + UniqueID + task name; use the browser's Print for a"
        " hand-out copy.</p></div>"
    ]
    for section in briefing.sections:
        items = "".join(
            f"<li>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></li>"
            for s in section.statements
        )
        parts.append(f"<div class=panel><h2>{_e(section.heading)}</h2><ul>{items}</ul></div>")
    return "".join(parts)


def _settings_body(state: SessionState) -> str:
    cfg = state.ai_config
    backend, _banner = route_backend(
        cfg, null_backend=NullBackend(), ollama_backend=_ollama_or_none(cfg)
    )
    models: tuple[str, ...] = ()
    try:
        models = backend.list_models()
    except Exception:
        models = ()
    model_list = ", ".join(_e(m) for m in models) or "<span class=muted>none available</span>"

    def sel(value: str, current: str) -> str:
        return " selected" if value == current else ""

    return f"""
<div class=panel><h2>Local AI</h2>
<p>Active backend: <b>{_e(backend.name)}</b> &middot; installed models: {model_list}</p>
<form action="/settings" method=post>
<p>Classification:
<select name=classification>
<option value=CLASSIFIED{sel("CLASSIFIED", cfg.classification)}>CLASSIFIED (CUI — local only)</option>
<option value=UNCLASSIFIED{sel("UNCLASSIFIED", cfg.classification)}>UNCLASSIFIED (cloud allowed, banner shown)</option>
</select></p>
<p>Backend:
<select name=backend>
<option value=ollama{sel("ollama", cfg.backend)}>Ollama (local)</option>
<option value=null{sel("null", cfg.backend)}>Null (offline, deterministic)</option>
<option value=cloud{sel("cloud", cfg.backend)}>Cloud (UNCLASSIFIED only)</option>
</select></p>
<p>Model: <input name=model value="{_e(cfg.model)}"></p>
<input type=submit value="Save"></form>
<p class=muted>The tool never sends schedule data off this machine while CLASSIFIED. Cloud is only
reachable after you explicitly switch to UNCLASSIFIED, and a persistent banner names the endpoint.</p></div>"""


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
    """Stop the server when the browser stops beating (closing the window = tool off)."""
    grace = app.state.idle_grace
    while not app.state.shutting_down:
        time.sleep(poll)
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
