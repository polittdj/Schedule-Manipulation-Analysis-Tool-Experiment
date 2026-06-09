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
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.engine import (
    analyze_floats,
    audit_schedule,
    compute_cpm,
    compute_driving_slack,
    recommend,
)
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import compute_baseline_compliance
from schedule_forensics.importers import (
    MAX_FILES,
    ImporterError,
    load_schedule,
    parse_mspdi_text,
    parse_xer_text,
    supported_extensions,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.net_guard import is_loopback_host
from schedule_forensics.web.help import METRIC_DICTIONARY

logger = logging.getLogger("schedule_forensics.web")

#: Locally-vendored static assets (CSS/JS) — served from /static; no CDN, no external fetch.
_STATIC_DIR = Path(__file__).parent / "static"

_CSS = """
:root{--bg:#0b0e14;--panel:#121826;--ink:#e6edf3;--muted:#8b98a5;--accent:#4aa3ff;
--ok:#3fb950;--warn:#d29922;--bad:#f85149;--line:#243044}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}header{background:#070a10;border-bottom:1px solid var(--line);
padding:14px 22px;display:flex;align-items:center;gap:18px}header h1{font-size:17px;margin:0;letter-spacing:.5px}
header nav a{margin-right:14px;color:var(--muted)}header nav a:hover{color:var(--ink)}
main{max-width:1100px;margin:0 auto;padding:24px}.panel{background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:18px 20px;margin:0 0 18px}h2{font-size:16px;margin:0 0 12px;color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:7px 10px;
border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}
.pass{color:var(--ok)}.fail{color:var(--bad)}.na{color:var(--muted)}
.sev-HIGH{color:var(--bad);font-weight:600}.sev-MEDIUM{color:var(--warn)}.sev-LOW,.sev-INFO{color:var(--muted)}
.banner{padding:10px 16px;border-radius:8px;margin:0 0 16px;font-weight:600}
.banner.local{background:#0d2818;border:1px solid var(--ok);color:var(--ok)}
.banner.cloud{background:#3a1d1d;border:1px solid var(--bad);color:var(--bad)}
.muted{color:var(--muted)}.cite{color:var(--muted);font-size:12px}
button,input[type=submit]{background:var(--accent);color:#04111f;border:0;border-radius:7px;
padding:8px 14px;font-weight:600;cursor:pointer}input,select{background:#0a0f1a;color:var(--ink);
border:1px solid var(--line);border-radius:7px;padding:7px 9px}
"""

_LAYOUT = Template(
    """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{ title }} — Schedule Forensics</title><style>{{ css }}</style>
<link rel=stylesheet href="/static/app.css"></head><body>
<header><h1>&#9650; SCHEDULE FORENSICS</h1>
<nav><a href="/">Dashboard</a><a href="/settings">AI Settings</a><a href="/help">Metric Dictionary</a>
<a href="/session/wipe" onclick="return confirm('Wipe all loaded schedules?')">Wipe Session</a></nav></header>
<main>{{ banner }}{{ body }}</main></body></html>"""
)


@dataclass
class SessionState:
    """In-memory, local-only session: loaded schedules (by name) + AI config. No disk persistence."""

    schedules: dict[str, Schedule] = field(default_factory=dict)
    ai_config: AIConfig = field(default_factory=AIConfig)

    def ordered(self) -> list[Schedule]:
        return list(self.schedules.values())


def _banner_html(state: SessionState) -> str:
    # the persistent banner reflects the project's classification intent (config-driven);
    # actual generation still fails closed via route_backend.
    banner = banner_for(state.ai_config)
    css = "cloud" if banner.cloud_active else "local"
    return f'<div class="banner {css}">{html.escape(banner.text)}</div>'


def _ollama_or_none(config: AIConfig) -> OllamaBackend | None:
    if config.backend != "ollama":
        return None
    try:
        return OllamaBackend(endpoint=config.endpoint, model=config.model)
    except Exception:
        return None


def _page(state: SessionState, title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        _LAYOUT.render(title=title, css=_CSS, banner=_banner_html(state), body=body)
    )


def _e(text: object) -> str:
    return html.escape(str(text))


def create_app(state: SessionState | None = None) -> FastAPI:
    """Build the FastAPI app. ``state`` lets a test/launcher inject a fresh session."""
    app = FastAPI(title="Schedule Forensics", docs_url=None, redoc_url=None)
    app.state.session = state if state is not None else SessionState()
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    def session() -> SessionState:
        s: SessionState = app.state.session
        return s

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        st = session()
        exts = ", ".join(sorted(supported_extensions()))
        rows = "".join(
            f'<tr><td><a href="/analysis/{_e(name)}">{_e(name)}</a></td>'
            f"<td>{len(sch.tasks)}</td><td class=muted>{_e(sch.source_file or '-')}</td></tr>"
            for name, sch in st.schedules.items()
        )
        loaded = (
            f"<table><tr><th>Schedule</th><th>Tasks</th><th>File</th></tr>{rows}</table>"
            if rows
            else "<p class=muted>No schedules loaded yet.</p>"
        )
        compare = (
            '<p><a href="/compare">Compare the two most recent versions &rarr;</a></p>'
            if len(st.schedules) >= 2
            else ""
        )
        body = f"""
<div class=panel><h2>Upload schedules (up to {MAX_FILES})</h2>
<form action="/upload" method=post enctype="multipart/form-data">
<input type=file name=files multiple>
<input type=submit value="Analyze">
<p class=muted>Supported: {_e(exts)}. Files are parsed locally and never leave this machine.</p>
</form></div>
<div class=panel><h2>Loaded schedules</h2>{loaded}{compare}</div>"""
        return _page(st, "Dashboard", body)

    @app.post("/upload")
    async def upload(files: list[UploadFile]) -> RedirectResponse:
        st = session()
        accepted = 0
        for upload_file in files[:MAX_FILES]:
            name = upload_file.filename or "schedule"
            data = await upload_file.read()
            try:
                schedule = _parse_upload(name, data)
            except (ImporterError, ValueError, OSError):
                logger.warning(
                    "rejected upload (unparseable); ext=%s bytes=%d", Path(name).suffix, len(data)
                )
                continue
            key = _unique_key(_clean_key(name), st.schedules)
            st.schedules[key] = schedule.model_copy(update={"source_file": name})
            accepted += 1
        logger.info("loaded %d schedule(s); total now %d", accepted, len(st.schedules))
        return RedirectResponse(url="/", status_code=303)

    @app.get("/analysis/{name}", response_class=HTMLResponse)
    def analysis(name: str) -> HTMLResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(st, "Not found", f"<div class=panel>No schedule named {_e(name)}.</div>")
        return _page(st, name, _analysis_body(name, sch))

    @app.get("/api/analysis/{name}")
    def analysis_json(name: str) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(_analysis_data(sch))

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
        return JSONResponse(_driving_data(sch, target, secondary, tertiary))

    @app.get("/compare", response_class=HTMLResponse)
    def compare() -> HTMLResponse:
        st = session()
        if len(st.schedules) < 2:
            return _page(
                st, "Compare", "<div class=panel>Load at least two versions to compare.</div>"
            )
        prior, current = st.ordered()[-2], st.ordered()[-1]
        return _page(st, "Compare", _compare_body(prior, current))

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

    @app.get("/session/wipe")
    def wipe() -> RedirectResponse:
        st = session()
        st.schedules.clear()
        logger.info("session wiped")
        return RedirectResponse(url="/", status_code=303)

    @app.get("/healthz")
    def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "loaded": len(session().schedules)})

    return app


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
    if suffix in {".xml", ".mspdi"}:
        return parse_mspdi_text(data.decode("utf-8"))
    if suffix == ".xer":
        return parse_xer_text(data.decode("utf-8", errors="replace"))
    # native .mpp / .mpt — needs the MPXJ runner + a JRE; write to a local temp file
    with tempfile.NamedTemporaryFile(suffix=suffix or ".mpp", delete=True) as handle:
        handle.write(data)
        handle.flush()
        return load_schedule(Path(handle.name))


def _status_class(status: object) -> str:
    # the values are CSS class names (not secrets); B105 is a false positive here.
    return {"PASS": "pass", "FAIL": "fail"}.get(str(status), "na")  # nosec B105


def _analysis_body(key: str, sch: Schedule) -> str:
    audit = audit_schedule(sch)
    audit_rows = "".join(
        f'<tr><td>{_e(c.name)}</td><td class="{_status_class(c.status)}">{_e(c.status)}</td>'
        f"<td>{_e(round(c.value, 1))}{_e(c.unit)}</td>"
        f"<td class=muted>{_e(c.suggested_improvement)}</td></tr>"
        for c in audit.checks
    )
    findings = recommend(sch, target_uid=None)
    find_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.category)}</td>'
        f"<td>{_e(f.title)}</td><td class=muted>{_e(f.course_of_action)}</td>"
        f"<td class=cite>{_e('; '.join(str(c) for c in f.citations[:2]))}"
        f"{_e(f' +{len(f.citations) - 2} more' if len(f.citations) > 2 else '')}</td></tr>"
        for f in findings
    )
    narrative = build_narrative(sch)
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


def _analysis_data(sch: Schedule) -> dict[str, object]:
    audit = audit_schedule(sch)
    compliance = compute_baseline_compliance(sch)
    return {
        "name": sch.name,
        "source_file": sch.source_file,
        "tasks": len(sch.tasks),
        "dcma": {
            c.metric_id: {"status": str(c.status), "count": c.count, "value": c.value}
            for c in audit.checks
        },
        "baseline_compliance": {k: v.count for k, v in compliance.items()},
        "activities": _activity_rows(sch),
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
            for f in recommend(sch)
        ],
    }


def _iso_date(value: object) -> str:
    return value.date().isoformat() if hasattr(value, "date") else ""


def _activity_rows(sch: Schedule) -> list[dict[str, object]]:
    """Per-activity rows for the interactive grid (float in days, citable metadata)."""
    by_id = sch.tasks_by_id
    rows: list[dict[str, object]] = []
    for fr in analyze_floats(sch):
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


def _driving_data(sch: Schedule, target: int, secondary: int, tertiary: int) -> dict[str, object]:
    """Driving-slack rows for the Gantt — tier + CPM ordinal positions for each traced UID."""
    by_id = sch.tasks_by_id
    if target not in by_id:
        return {"target_uid": target, "target_name": None, "rows": []}
    cpm = compute_cpm(sch)
    results = compute_driving_slack(
        sch, target_uid=target, secondary_max_days=secondary, tertiary_max_days=tertiary
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


def _compare_body(prior: Schedule, current: Schedule) -> str:
    manip = detect_manipulation(current, prior)
    trend = trend_across_versions([prior, current])
    impact = next((s for s in trend), None)
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
    _ = impact
    return f"""
<div class=panel><h2>Version trend &mdash; {_e(prior.source_file or "prior")} &rarr; {_e(current.source_file or "current")}</h2>
<table><tr><th>Version</th><th>Project finish</th><th>Completed</th><th>In&nbsp;progress</th><th>Critical</th></tr>{trend_rows}</table></div>
<div class=panel><h2>Manipulation-trend signals</h2>
<table><tr><th>Severity</th><th>Signal</th><th>Course of action</th></tr>
{manip_rows or "<tr><td colspan=3 class=muted>No manipulation signals detected (honest progress).</td></tr>"}</table></div>"""


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


def run(
    host: str = "127.0.0.1", port: int = 8765
) -> None:  # pragma: no cover - launcher entrypoint
    """Serve the app on a loopback address only (refuses a non-local host — Law 1)."""
    import uvicorn

    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind a non-loopback host {host!r} (CUI: local-only).")
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
