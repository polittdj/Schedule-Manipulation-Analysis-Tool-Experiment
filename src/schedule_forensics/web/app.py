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

import contextlib
import datetime as dt
import html
import json
import logging
import re
import tempfile
import threading
import time
from collections.abc import Callable, Sequence
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
from schedule_forensics.ai.briefing import (
    BriefingSection,
    ExecutiveBriefing,
    briefing_blocks,
    build_briefing,
)
from schedule_forensics.ai.citations import CitedStatement, Narrative
from schedule_forensics.ai.driving_facts import driving_path_facts, driving_path_summary
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.ai.ollama_process import OllamaLauncher
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
from schedule_forensics.engine.dcma_audit import AuditCheck, Citation, ScheduleAudit
from schedule_forensics.engine.driving_path import (
    DrivingPathEvolution,
    DrivingPathSnapshot,
    compute_driving_path_evolution,
)
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    PathTier,
    date_basis,
)
from schedule_forensics.engine.forecast import (
    CarnacSummary,
    ForecastSet,
    compute_carnac_summary,
    compute_finish_forecasts,
)
from schedule_forensics.engine.grouping import (
    MAX_FIELDS,
    Criterion,
    available_fields,
    available_fields_union,
    distinct_values,
    filter_schedule,
    group_values,
)
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import (
    WBSGroup,
    compute_activity_makeup,
    compute_baseline_compliance,
    compute_bei,
    compute_bri,
    compute_completion_performance,
    compute_constraint_distribution,
    compute_dcma14,
    compute_fei,
    compute_float_bands,
    compute_float_sums,
    compute_net_finish_impact,
    compute_ribbon,
    compute_schedule_quality,
    compute_wbs_breakdown,
)
from schedule_forensics.engine.metrics._common import MetricResult, non_summary
from schedule_forensics.engine.metrics.constraint_health import compute_constraint_health
from schedule_forensics.engine.metrics.evm import compute_schedule_variance
from schedule_forensics.engine.metrics.float_erosion import compute_float_erosion
from schedule_forensics.engine.metrics.health_extra import compute_health_checks
from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.engine.metrics.margin import compute_margin, compute_margin_trend
from schedule_forensics.engine.metrics.vertical_integration import compute_vertical_integration
from schedule_forensics.engine.metrics.year_phases import (
    YEAR_BASES,
    YearPhaseRow,
    YearPhases,
    compute_year_phases,
)
from schedule_forensics.engine.month_curves import MonthCurves, compute_month_curves
from schedule_forensics.engine.path_counterfactual import (
    PathCounterfactual,
    compute_path_counterfactual,
)
from schedule_forensics.engine.path_evolution import compute_path_evolution
from schedule_forensics.engine.path_trace import subschedule_to_target
from schedule_forensics.engine.recommendations import (
    SEVERITY_ORDER,
    Category,
    Finding,
    Severity,
)
from schedule_forensics.engine.s_curve import SCurve, compute_s_curve
from schedule_forensics.engine.sra import (
    ActivityRisk,
    OATSensitivity,
    RiskEvent,
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
    SRAResult,
    SSIResult,
    SSIRiskStat,
    compute_oat_sensitivity,
    compute_sra,
    compute_sra_ssi,
    factor_to_bc_wc,
)
from schedule_forensics.engine.trend import (
    compute_cei_trend,
    compute_float_ratio_trend,
    compute_hmi_trend,
    compute_quality_trend,
    order_versions,
)
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
from schedule_forensics.net_guard import is_local_http_endpoint, is_loopback_host
from schedule_forensics.reports.docx import (
    Block,
    Chart,
    ChartText,
    DocTable,
    Heading,
    Paragraph,
    render_document,
    render_docx,
)
from schedule_forensics.reports.tables import (
    Cell,
    Table,
    TableSet,
    activities_table,
    bow_wave_tables,
    carnac_table,
    dcma_table,
    driving_table,
    findings_table,
    forecast_tables,
    metric_results_table,
    month_curves_tables,
    path_evolution_tables,
    schedule_summary_table,
    trend_tables,
    wbs_breakdown_tables,
)
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.web import i18n
from schedule_forensics.web.help import METRIC_DICTIONARY, reliability_dimension

logger = logging.getLogger("schedule_forensics.web")

#: Locally-vendored static assets (CSS/JS) — served from /static; no CDN, no external fetch.
_STATIC_DIR = Path(__file__).parent / "static"
#: Bundled, non-CUI sample schedule for the "Load example" button.
_EXAMPLE = Path(__file__).parent / "examples" / "house_build.json"
#: File types the open/import picker accepts.
_ACCEPT = ".json,.xml,.mspdi,.xer,.mpp,.mpt"

_LAYOUT = Template(
    """<!doctype html><html lang="{{ lang }}"><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{{ title }} — Schedule Forensics</title>
<link rel=icon href="/static/favicon.ico">
<script>window.SF_LANG={{ lang_json }};window.SF_I18N={{ catalog_json }};</script>
<script src="/static/theme.js"></script>
<script src="/static/checklist.js"></script>
<script src="/static/gantt.js"></script>
<script src="/static/colresize.js"></script>
<script src="/static/a11y.js"></script>
<script src="/static/translate.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css"></head><body>
<div class="cui-banner {{ cui_class }}" data-no-i18n>{{ cui_text }}</div>
<header><h1>&#9650; SCHEDULE FORENSICS</h1>
<nav>
<span class=nav-group><span class=nav-grp-label>Overview</span><a href="/">Dashboard</a><a href="/mission">Mission Control</a></span>
<span class=nav-group><span class=nav-grp-label>Assessment</span><a href="/ribbon">Quality Ribbon</a><a href="/path">Path Analysis</a><a href="/driving-path">Driving Path</a><a href="/evolution">Critical-Path Evolution</a></span>
<span class=nav-group><span class=nav-grp-label>Control</span><a href="/trend">Trend</a><a href="/cei">Bow Wave / CEI</a><a href="/curves">Finish &amp; Slippage</a><a href="/scurve">S-Curve</a><a href="/phases">Year Phases</a><a href="/forecast">Forecast</a></span>
<span class=nav-group><span class=nav-grp-label>Risks</span><a href="/risks">Risks &amp; Opportunities</a><a href="/sra">Risk Analysis</a></span>
<span class=nav-group><span class=nav-grp-label>Reporting</span><a href="/brief">Diagnostic Brief</a><a href="/briefing">Executive Briefing</a><a href="/help">Metric Dictionary</a></span>
<span class=nav-group><span class=nav-grp-label>Setup</span><a href="/groups">Groups &amp; Filters</a><a href="/settings">AI Settings</a></span>
<form action="/session/wipe" method=post class=navform
onsubmit="return confirm('Wipe all loaded schedules?')"><button type=submit class=linkbtn>Wipe Session</button></form>
<a href="#" onclick="return sfQuit()" title="Stop the local server and exit">Quit</a>
<form action="/target" method=post class="navform targetform"
title="Focus every view on one activity (blank = clear)">
<input type=hidden name=next_url value="/">
<label>Target UID: <input name=uid type=number min=1 value="{{ target }}" placeholder="any"></label>
<button type=submit class=linkbtn>Set</button></form>
<button id=themeToggle type=button class=linkbtn title="Switch light/dark mode">Theme</button>
<label class=ui-scale-ctl title="Rescale the whole page — text and layout together">Size
<select id=uiScale data-no-i18n>
<option value="0.9">90%</option><option value="1">100%</option><option value="1.1">110%</option>
<option value="1.25">125%</option><option value="1.5">150%</option><option value="1.75">175%</option>
</select></label>
<form action="/language" method=post class="navform langform"
title="Display language for the UI and AI results">
<label>Language: <select name=lang data-no-i18n
onchange="this.form.submit()">{{ lang_options }}</select></label>
</form>
</nav>
<span class="nasa-globe" data-no-i18n title="NASA"><canvas width="132" height="132" aria-hidden="true"></canvas><span class="nasa-globe-text">NASA</span></span>
</header>
<main>{{ banner }}{{ body }}</main><script src="/static/heartbeat.js"></script>
<script src="/static/chartframe.js"></script>
<script src="/static/target.js"></script>
<script src="/static/globe.js"></script>
<div class="cui-banner {{ cui_class }} bottom" data-no-i18n>{{ cui_text }}</div>
</body></html>"""
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
    # UI/AI display language (ADR-0099): "en" (source) or "es". Drives the layout's lang attribute
    # and the client translation pass; AI fallback translations are memoised in ``translations``.
    language: str = "en"
    # AI-fallback translation cache: (lang, source text) -> translated, so a string is translated
    # at most once per session (the catalog covers fixed terms; this covers dynamic content).
    translations: dict[tuple[str, str], str] = field(default_factory=dict)
    # the routed AI backend, cached briefly (config, probed-at, backend) so report renders
    # don't re-probe a down Ollama every time; reset on a settings change / TTL lapse.
    backend_cache: tuple[AIConfig, float, AIBackend] | None = None
    # per-schedule narrative as polished by a real (non-null) backend:
    # key -> (schedule identity, "backend/model" stamp, narrative). Cleared on wipe.
    polished: dict[str, tuple[Schedule, str, Narrative]] = field(default_factory=dict)
    # the cross-check second model, cached like backend_cache (None = off/unreachable).
    second_cache: tuple[AIConfig, float, AIBackend | None] | None = None
    # session-wide group/filter (ADR-0104): when set, EVERY metric on EVERY page — and every loaded
    # file — is scoped to the tasks matching ALL criteria. Empty tuple = no filter (full schedules).
    active_filter: tuple[Criterion, ...] = ()
    # identity-stable cache of filtered schedules, id(original) -> (original, filtered), so a scoped
    # schedule keeps one identity across a request and the analysis cache below still hits. Cleared
    # whenever the filter changes (set_filter) or the session is wiped.
    _scoped: dict[int, tuple[Schedule, Schedule]] = field(default_factory=dict)
    # SRA manual inputs (ADR-0106, manual path). The global triangular multipliers applied to every
    # activity's REMAINING duration when no per-activity override is set (defaults = the industry
    # "Quick Risk" screening values, Deltek Acumen "Realistic" 90/100/110).
    sra_low: float = 0.9
    sra_ml: float = 1.0
    sra_high: float = 1.10
    # per-activity 3-point overrides: uid -> (optimistic, most_likely, pessimistic) WORKING MINUTES.
    sra_overrides: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    # discrete risk register (ADR-0106 risk-driver method): probability x triangular impact
    # multiplier on the affected activities' sampled durations. Set via POST /sra/risk-event.
    sra_risks: list[RiskEvent] = field(default_factory=list)
    # monotonic id counter so each registered risk keeps a stable, unique id across removals.
    sra_risk_seq: int = 0
    # which loaded file the SRA runs against (operator choice). None / unknown key => the latest
    # solvable version (the historical default). Set via GET /sra?file=<key>.
    sra_file: str | None = None
    # --- SSI Schedule Risk & Opportunity Analysis inputs (ADR-0123) ---
    # the focus event whose finish the SSI run/OAT report (SSI "Flag for Analysis"); None => project.
    sra_focus_uid: int | None = None
    # the Risk Factors table: (factor 1..5, % subtract for Best Case, % add for Worst Case).
    sra_factor_rows: tuple[tuple[int, float, float], ...] = field(
        default_factory=lambda: RiskFactorTable().rows
    )
    sra_factors: dict[int, int] = field(default_factory=dict)  # uid -> Risk Ranking Factor 1..5
    sra_bcwc: dict[int, tuple[int, int]] = field(default_factory=dict)  # uid -> (BC, WC) minutes
    sra_ssi_risks: list[ScheduleRisk] = field(default_factory=list)  # additive-days risk register
    sra_ssi_risk_seq: int = 0
    sra_occurrence_mode: str = "random_each"  # "random_each" | "exact_overall"
    sra_use_risk_register: bool = True
    sra_correlation: float = 0.0  # 0 = independent; 0.3-0.5 typical blanket correlation

    def scope(self, sch: Schedule) -> Schedule:
        """``sch`` reduced to the active filter AND truncated to the target endpoint — the single
        point every page funnels through.

        Returns ``sch`` unchanged when neither a filter nor a target endpoint is set. Otherwise
        applies the session filter, then (when a Target UID is set) restricts the result to that
        activity plus everything that drives it (:func:`subschedule_to_target`), so every metric and
        visual treats the target as the schedule's endpoint and omits work beyond it. A version that
        does not contain the target keeps its (filtered) full population. The result is memoised by
        the original's identity so repeated calls in one request share one object (keeping the
        per-key analysis cache valid); the memo resets on :meth:`set_filter` / :meth:`set_target` /
        wipe."""
        if not self.active_filter and self.target_uid is None:
            return sch
        cached = self._scoped.get(id(sch))
        if cached is not None and cached[0] is sch:
            return cached[1]
        scoped = filter_schedule(sch, self.active_filter) if self.active_filter else sch
        if self.target_uid is not None and any(
            t.unique_id == self.target_uid and not t.is_summary for t in scoped.tasks
        ):
            # target present in this (filtered) version → truncate to it + its drivers; a version
            # that doesn't contain the target keeps its full (filtered) population.
            scoped = subschedule_to_target(scoped, self.target_uid)
        self._scoped[id(sch)] = (sch, scoped)
        return scoped

    def set_filter(self, criteria: Sequence[Criterion]) -> None:
        """Set (or clear, with ``()``) the session-wide filter and invalidate the scope/analysis
        caches so every page recomputes against the new scope."""
        self.active_filter = tuple(criteria)
        self._scoped.clear()
        self.analyses.clear()
        self.polished.clear()

    def set_target(self, uid: int | None) -> None:
        """Set (or clear) the session-wide Target UID *endpoint* and invalidate the scope/analysis
        caches so every metric, audit, and visual recomputes against the target's driving
        sub-network (or the full schedule again when cleared)."""
        self.target_uid = uid
        self._scoped.clear()
        self.analyses.clear()
        self.polished.clear()

    def ordered(self) -> list[Schedule]:
        """Loaded schedules **scoped to the active filter**, ordered by data date (oldest first).

        This is what the multi-version views that call engine functions directly (bow-wave, S-curve,
        month curves) iterate, so the filter reaches them too. Views that go through
        :meth:`analysis_for` pass the raw schedule from :meth:`ordered_versions` (it scopes)."""
        return [self.scope(s) for s in order_versions(list(self.schedules.values()))]

    def ordered_versions(self) -> list[tuple[str, Schedule]]:
        """(key, UNSCOPED schedule) pairs, oldest first. Callers either hand the schedule to
        :meth:`analysis_for` (which scopes it) or, for the filter UI, need the full field/value set —
        so this stays raw. Use :meth:`ordered` / :meth:`scope` when you need the filtered tasks."""
        by_obj = {id(s): k for k, s in self.schedules.items()}
        return [(by_obj[id(s)], s) for s in order_versions(list(self.schedules.values()))]

    def analysis_for(self, key: str, sch: Schedule) -> _Analysis:
        """The cached analysis for ``key`` over the active scope; recomputes when the schedule object
        or the filter changes (both reflected in the scoped object's identity)."""
        scoped = self.scope(sch)
        cached = self.analyses.get(key)
        if cached is not None and cached[0] is scoped:
            return cached[1]
        analysis = _compute_analysis(scoped)
        self.analyses[key] = (scoped, analysis)
        return analysis


def _banner_html(state: SessionState) -> str:
    # the persistent banner reflects the project's classification intent (config-driven);
    # actual generation still fails closed via route_backend.
    banner = banner_for(state.ai_config)
    css = "cloud" if banner.cloud_active else "local"
    return f'<div class="banner {css}">{html.escape(banner.text)}</div>'


def _filter_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a session-wide group/filter is active, so the
    operator always knows the metrics are scoped — with one-click manage/clear (ADR-0104)."""
    if not state.active_filter:
        return ""
    parts = []
    for fld, value in state.active_filter:
        vals = _criterion_value_list(value)
        shown = (
            "(populated)"
            if not vals
            else _e(", ".join(vals[:3]) + (f" +{len(vals) - 3}" if len(vals) > 3 else ""))
        )
        parts.append(f"{_e(fld)} = {shown}")
    chips = " &middot; ".join(parts)
    return (
        '<div class="panel filter-active" style="border-left:4px solid var(--accent)">'
        f"<b>Filter active</b> &mdash; every metric on every page (all files) is scoped to: "
        f'{chips}. <a href="/groups">manage</a> &middot; '
        '<a href="/groups?clear=1">clear filter</a></div>'
    )


def _endpoint_clear_form(label: str) -> str:
    """An inline form that clears the Target-UID endpoint, returning to the current page (the
    shared ``targetform`` class lets target.js rewrite next_url to the current location)."""
    return (
        '<form action="/target" method=post class="targetform endpoint-clear">'
        '<input type=hidden name=uid value=""><input type=hidden name=next_url value="/">'
        f"<button type=submit class=linkbtn>{_e(label)}</button></form>"
    )


def _endpoint_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a Target UID endpoint is active, so the operator
    always knows every metric/visual is limited to that activity and the work that drives it — with
    the count of omitted activities and a one-click clear (forensic transparency)."""
    uid = state.target_uid
    if uid is None:
        return ""
    found = False
    kept = total = 0
    for s in state.schedules.values():
        if any(t.unique_id == uid and not t.is_summary for t in s.tasks):
            found = True
        scoped = state.scope(s)
        total += sum(1 for t in s.tasks if not t.is_summary)
        kept += sum(1 for t in scoped.tasks if not t.is_summary)
    if not found:
        return (
            '<div class="panel endpoint-active" style="border-left:4px solid var(--bad)">'
            f"<b>Endpoint UID {uid} not found</b> &mdash; no loaded version contains that activity, "
            f"so nothing is being truncated. Check the UID. {_endpoint_clear_form('clear endpoint')}"
            "</div>"
        )
    omitted = total - kept
    return (
        '<div class="panel endpoint-active" style="border-left:4px solid var(--warn)">'
        f"<b>Analysis endpoint: UID {uid}</b> &mdash; every metric and visual on every page is "
        f"limited to UID {uid} and the activities that drive it "
        f"({kept} of {total} activities shown; {omitted} omitted). "
        f"{_endpoint_clear_form('clear endpoint')}</div>"
    )


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
        return OllamaBackend(
            endpoint=config.endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def _openai_or_none(config: AIConfig) -> OpenAICompatBackend | None:
    if config.backend != "openai":
        return None
    try:
        # construction enforces loopback (CUIEgressError on a remote host — Law 1)
        return OpenAICompatBackend(
            endpoint=config.openai_endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def _model_installed(model: str, installed: tuple[str, ...]) -> bool:
    """Tolerant match of a configured model name against an Ollama install list.

    Ollama tags models ``name:tag`` (``llama3.1:8b``); a config of ``llama3.1`` should match
    ``llama3.1:8b`` (and vice-versa) so the diagnostic doesn't cry "not installed" over a tag.
    """
    m = model.strip().lower()
    if not m:
        return True
    base = m.split(":")[0]
    return any(n.strip().lower() == m or n.strip().lower().split(":")[0] == base for n in installed)


def _ai_status_note(cfg: AIConfig) -> str:
    """An actionable settings line when a configured LOCAL backend isn't actually serving.

    Turns the silent 'Active backend: null' into a concrete reason + fix (the operator could
    not see why the AI was off): server down / wrong port / model not pulled. Empty for the
    Null backend (no server expected) and for cloud (handled by the banner)."""
    if cfg.backend not in ("ollama", "openai"):
        return ""
    probe = _ollama_or_none(cfg) if cfg.backend == "ollama" else _openai_or_none(cfg)
    if probe is None:  # construction refused a non-loopback endpoint — field validation handles it
        return ""
    is_ollama = cfg.backend == "ollama"
    label = "Ollama" if is_ollama else "the OpenAI-compatible server"
    endpoint = cfg.endpoint if is_ollama else cfg.openai_endpoint
    # unavailable_reason() is on the concrete local backends (not the AIBackend protocol); fall
    # back to is_available() for any other backend object (e.g. a test/cloud stand-in).
    reason_fn = getattr(probe, "unavailable_reason", None)
    reason = (
        reason_fn() if callable(reason_fn) else (None if probe.is_available() else "not reachable")
    )
    if reason is not None:
        if is_ollama:
            hint = (
                "The tool tries to start Ollama for you when it launches, so if this still shows "
                "OFF it is probably still starting — <b>wait a few seconds and reload this page</b>. "
                "If it never connects, Ollama may not be installed, or it is on a different port: "
                f"start it manually (the Ollama app, or <code>ollama serve</code>) and confirm the "
                f"port matches <code>{_e(endpoint)}</code>. On a work laptop the local model still "
                "works — the tool talks to it directly and never via a proxy."
            )
        else:
            hint = (
                "Start your local server (LM Studio / llamafile / vLLM), load a model, and confirm "
                f"the port matches <code>{_e(endpoint)}</code>."
            )
        return (
            f'<div class="notice err">Local AI is OFF — could not reach {label} at '
            f"<code>{_e(endpoint)}</code>: {_e(reason)}. {hint}</div>"
        )
    if is_ollama and cfg.model:  # reachable — is the chosen model actually pulled?
        try:
            installed = probe.list_models()
        except Exception:  # diagnostics only, never sink the page
            installed = ()
        if installed and not _model_installed(cfg.model, installed):
            return (
                f'<div class="notice err">Ollama is reachable but the selected model '
                f"<code>{_e(cfg.model)}</code> isn't installed — <b>pick an installed model from "
                f"the Model dropdown below</b> and Save (installed: {_e(', '.join(installed))}), or "
                f"run <code>ollama pull {_e(cfg.model)}</code> to fetch it.</div>"
            )
    return (
        f'<div class="notice ok">Local AI is ON — {label} reachable at '
        f"<code>{_e(endpoint)}</code>; answers are interpreted by the local model.</div>"
    )


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
            backend = OllamaBackend(
                endpoint=cfg.endpoint,
                model=cfg.second_model or cfg.model,
                timeout=cfg.gen_timeout,
            )
        else:
            backend = OpenAICompatBackend(
                endpoint=cfg.openai_endpoint, model=cfg.second_model, timeout=cfg.gen_timeout
            )
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


def _ai_translate(texts: list[str], lang: str, backend: AIBackend) -> dict[str, str]:
    """Translate ``texts`` with the configured model; return only the ones it produced.

    Numbered, tab-delimited round-trip so partial/garbled output degrades gracefully (the caller
    keeps the source text for anything not returned). The Null backend (no model) returns nothing —
    the catalog already covers the fixed UI, and dynamic content stays in the source language."""
    if backend.name == "null" or not texts:
        return {}
    target = i18n.LANGUAGES.get(lang, lang)
    prompt = (
        f"Translate each numbered line into {target}. These are short UI labels and "
        "schedule-activity names from a project-management tool. Output ONLY the translations, one "
        "per line, each prefixed with its number and a tab, in the same order. Keep numbers, dates, "
        "codes and IDs unchanged.\n\n" + "\n".join(f"{i}\t{t}" for i, t in enumerate(texts))
    )
    try:
        raw = backend.generate(prompt)
    except Exception:
        return {}
    out: dict[str, str] = {}
    for line in raw.splitlines():
        num, sep, es = line.partition("\t")
        if sep and num.strip().isdigit() and int(num.strip()) < len(texts) and es.strip():
            out[texts[int(num.strip())]] = es.strip()
    return out


def _translate_batch(texts: list[str], lang: str, state: SessionState) -> dict[str, str]:
    """Translations for ``texts``: catalog → session cache → AI model. Source text for the rest."""
    cat = i18n.catalog_for(lang)
    out: dict[str, str] = {}
    need: list[str] = []
    for raw in texts:
        key = raw.strip()
        if not key:
            continue
        if key in cat:
            out[raw] = cat[key]
        elif (lang, key) in state.translations:
            out[raw] = state.translations[(lang, key)]
        elif raw not in need:
            need.append(raw)
    for raw, translated in _ai_translate(need, lang, _active_backend(state)).items():
        state.translations[(lang, raw.strip())] = translated
        out[raw] = translated
    return out


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
<p class=muted><b>AI can err &mdash; verify against citations.</b> Ask anything about the loaded
data: with a local model active (Ollama) you get a full written analysis grounded in the
engine's computed, cited facts &mdash; the matching facts are always shown alongside. With no
local model active you get the cited facts themselves; <a href="/settings">enable Ollama in AI
Settings</a> for interpretation.</p>
<div class=viz-controls>
<label>About <select id=askScope>{"".join(options)}</select></label>
<input id=askInput type=text size=60 maxlength=500
 placeholder="e.g. Why is the finish slipping? How many critical activities?">
<button id=askBtn type=button>Ask</button></div>
<div class=viz-controls><span class=muted>Driving path (exact, no AI):</span>
<label>to UID <input id=drivePathUid type=number min=1 step=1 style="width:7em"
 placeholder="UID"></label>
<button id=drivePathBtn type=button>Show driving path</button></div>
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
    lang = i18n.normalize(state.language)
    lang_options = "".join(
        f'<option value="{code}"{" selected" if code == lang else ""}>{_e(name)}</option>'
        for code, name in i18n.LANGUAGES.items()
    )
    # NASA CUI page-marking (top + bottom banner on every page). Default CLASSIFIED → mark CUI;
    # only the operator-asserted UNCLASSIFIED mode drops the CUI controls marking. Kept out of the
    # i18n pass (data-no-i18n) so the control marking stays in its required standard wording.
    classified = state.ai_config.classification is Classification.CLASSIFIED
    cui_class = "cui" if classified else "unclassified"
    cui_text = (
        "Controlled Unclassified Information • CUI"
        if classified
        else "Unclassified • no CUI controls asserted"
    )
    return HTMLResponse(
        _LAYOUT.render(
            title=title,
            banner=_banner_html(state),
            body=(
                _filter_banner(state)
                + _endpoint_banner(state)
                + body
                + _ask_panel_html(state, ask_schedule)
            ),
            target=state.target_uid if state.target_uid is not None else "",
            lang=lang,
            lang_json=json.dumps(lang),
            # the catalog is only shipped to the client when not English (no payload for en)
            catalog_json=json.dumps(i18n.catalog_for(lang)),
            lang_options=lang_options,
            cui_class=cui_class,
            cui_text=cui_text,
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


def _parse_uid_list(value: str | None) -> list[int]:
    """UniqueIDs from a free-text list (comma / space / semicolon separated), order-preserving.

    Each token is parsed with :func:`_parse_uid` rules (positive integers only); blanks and
    non-numeric tokens are dropped, and duplicates are removed keeping first appearance."""
    if not value:
        return []
    out: list[int] = []
    for token in value.replace(";", " ").replace(",", " ").split():
        uid = _parse_uid(token)
        if uid is not None and uid not in out:
            out.append(uid)
    return out


def _to_float(value: str | None, default: float) -> float:
    """A float from form/query text — blank or non-numeric falls back to ``default``."""
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


def _clamp_float(
    value: str | None, lo: float, hi: float, default: float, *, scale: float = 1.0
) -> float:
    """Parse ``value`` times ``scale``, clamp to ``[lo, hi]``; non-numeric keeps ``default``."""
    parsed = _to_float(value, default / scale if scale else default)
    return max(lo, min(hi, parsed * scale))


def _e(text: object) -> str:
    return html.escape(str(text))


#: Content-Security-Policy that enforces the air-gap (Law 1) in EVERY browser at runtime, not
#: just in the test: ``default-src``/``connect-src``/``img-src`` are ``'self'`` so the page can
#: never pull or beacon to a remote host (no CDN, no font, no exfil fetch). ``'unsafe-inline'``
#: is allowed for style + script because the UI legitimately uses inline ``style=`` (the Gantt's
#: px widths) and two inline handlers (Quit / wipe-confirm); that permits INLINE code but still
#: forbids any REMOTE script/style, so the no-remote-asset guarantee holds. Tightening to a strict
#: ``script-src 'self'`` (after moving the two handlers to addEventListener) is a tracked follow-up.
_CSP = (
    "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
    "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
    "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
)
#: Security headers added to every response (CSP enforces the air-gap; nosniff/Referrer/Frame
#: are free hardening for the CUI threat model — the operator analyzes opposing-party files).
_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

#: FastAPI defaults for the optional repeated-string query params (the S-curve per-chart filter's
#: cf/cv). Each param needs its OWN ``Query`` instance: FastAPI binds the field's query key from the
#: FieldInfo, so sharing one instance across two params silently aliases the second to the first's
#: key (cv would read cf's values). Module-level singletons still dodge a call-in-default (ruff B008).
_CF_QUERY = Query(default_factory=list)
_CV_QUERY = Query(default_factory=list)


def create_app(
    state: SessionState | None = None,
    *,
    auto_shutdown: bool = False,
    idle_grace: float = 600.0,
    ollama: OllamaLauncher | None = None,
) -> FastAPI:
    """Build the FastAPI app. ``state`` lets a test/launcher inject a fresh session.

    ``auto_shutdown`` (set by the desktop launcher) makes :func:`serve` run a watchdog that
    stops the server once the browser stops sending heartbeats for ``idle_grace`` seconds —
    so closing the window turns the whole tool off. ``request_shutdown`` is wired by
    :func:`serve`; the in-page "Quit" control and the watchdog both call it.

    ``idle_grace`` defaults to **600s (10 minutes)** of no heartbeat before the tool times out
    (ADR-0120). The page beats every 3s, but browsers throttle timers in a backgrounded/minimized
    tab — so a short grace would shut a still-open tool down when it was merely in the background.
    Ten minutes also lets the operator navigate away briefly (or let the laptop sleep) and come
    back to the same session. The in-page **Quit** control still stops it immediately.

    ``ollama`` (passed by the desktop launcher) is the Ollama process manager. It is started
    **lazily** — only when the operator turns the Ollama backend on in AI Settings — and stopped
    on tool close, so the tool never spins Ollama up for a session that never uses the AI (ADR-0122).
    """
    app = FastAPI(title="Schedule Forensics", docs_url=None, redoc_url=None)
    app.state.session = state if state is not None else SessionState()
    app.state.auto_shutdown = auto_shutdown
    app.state.idle_grace = idle_grace
    app.state.ollama = ollama  # lazy-started on AI enable, stopped on close (None in tests)
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
            for key, value in _SECURITY_HEADERS.items():
                response.headers.setdefault(key, value)  # CSP/nosniff on every response (Law 1)
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
            f' &middot; <a href="/wbs/{quote(name)}">WBS</a>'
            f' &middot; <a href="/download/{quote(name)}.json">Save .json</a></td></tr>'
            for name, sch in st.ordered_versions()  # earliest -> latest data date
        )
        loaded = (
            "<div class=panel><h2>Schedule health</h2>"
            "<p class=muted>A health snapshot per loaded schedule &mdash; activity status mix, "
            "critical-path exposure, computed finish vs. baseline, and the DCMA-14 checks at a "
            "glance. Click any card to dive into its full report.</p>"
            "<div id=dashboardHealth class=dash-cards></div></div>"
            '<script src="/static/dashboard.js"></script>'
            "<div class=panel><h2>Loaded schedules</h2>"
            "<table><tr><th scope=col>Schedule</th><th scope=col>Activities</th><th scope=col>Source</th><th scope=col></th></tr>"
            f"{rows}</table>"
            + (
                '<p style="margin-top:14px"><a class=btn-link href="/briefing">'
                "Executive briefing &rarr;</a>"
                + (
                    ' &middot; <a class=btn-link href="/trend">Trend across all versions &rarr;</a>'
                    ' &middot; <a class=btn-link href="/cei">Bow Wave / CEI &rarr;</a>'
                    ' &middot; <a class=btn-link href="/curves">Finish &amp; slippage curves &rarr;</a>'
                    ' &middot; <a class=btn-link href="/evolution">Critical-path evolution &rarr;</a>'
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
  schedule-quality&nbsp;&amp;&nbsp;schedule-risk metrics, driving-path and manipulation-trend analysis,
  and a cited AI narrative &mdash; nothing leaves this computer.</p>
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

    @app.get("/api/dashboard")
    def dashboard_json() -> JSONResponse:
        return JSONResponse(_dashboard_data(session()))

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
        # Render the DETERMINISTIC narrative immediately so the report opens at once; ai_polish.js
        # fetches /api/ai/narrative in the background and swaps in the local-AI-polished prose when a
        # model is active. The old synchronous per-statement generate here blocked the whole render
        # for minutes on a slow local model — a big .mpp landing on /analysis with a 72B Ollama active
        # looked exactly like "the file won't load" (the browser tab just kept spinning).
        bar = _export_bar(f"analysis/{quote(name, safe='')}")
        return _page(
            st,
            name,
            bar + _analysis_body(name, sch, analysis, st.target_uid),
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
        focus = _target_panel(sch, analysis, st.target_uid) if st.target_uid is not None else ""
        return _page(
            st, f"{name} — card", focus + _card_body(name, sch, analysis), ask_schedule=name
        )

    @app.get("/wbs/{name}", response_class=HTMLResponse)
    def wbs_breakdown_view(name: str) -> HTMLResponse:
        """The deck's *Completion Metrics* + *SPI and Earned Schedule* pages (PBIX 8, 9):
        the completion family and Earned Schedule pivoted by WBS."""
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return _page(
                st,
                "Not found",
                f"<div class=panel>No schedule named {_e(name)}.</div>",
                status_code=404,
            )
        groups = compute_wbs_breakdown(sch)
        focus = ""
        if st.target_uid is not None:
            try:
                focus = _target_panel(sch, st.analysis_for(name, sch), st.target_uid)
            except CPMError:
                focus = ""  # unschedulable: skip the focus panel, still show the WBS pivot
        return _page(st, f"{name} — WBS", focus + _wbs_body(name, groups), ask_schedule=name)

    @app.get("/api/wbs/{name}")
    def wbs_json(name: str) -> JSONResponse:
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(_wbs_data(compute_wbs_breakdown(sch)))

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

    @app.get("/phases", response_class=HTMLResponse)
    def phases_view(name: str = Query(""), basis: str = Query("finish")) -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Year Phases",
                "<div class=panel>Load a schedule to see the per-year phase view.</div>",
            )
        keys = [k for k, _ in st.ordered_versions()]
        current = name if name in st.schedules else keys[-1]
        yp = compute_year_phases(st.scope(st.schedules[current]), basis)
        return _page(st, "Year Phases", _phases_body(keys, current, yp), ask_schedule=current)

    @app.get("/api/phases")
    def phases_json(basis: str = Query("finish")) -> JSONResponse:
        """Per-version year-phase distribution on a LOCKED axis, for the animated stepper — every
        loaded version (oldest first) binned on the same basis, aligned to the union of years."""
        st = session()
        if basis not in YEAR_BASES:
            basis = "finish"
        years: set[int] = set()
        max_total = 1
        per: list[tuple[str, str | None, int, dict[int, YearPhaseRow]]] = []
        for _key, raw in st.ordered_versions():
            yp = compute_year_phases(st.scope(raw), basis)
            rows = {r.year: r for r in yp.rows}
            years.update(rows)
            for r in yp.rows:
                max_total = max(max_total, r.total)
            status = raw.status_date.date().isoformat() if raw.status_date else None
            per.append((raw.source_file or raw.name, status, yp.undated, rows))
        all_years = sorted(years)
        versions = [
            {
                "label": label,
                "status_date": status,
                "undated": undated,
                "rows": [
                    {
                        "year": y,
                        "total": rows[y].total if y in rows else 0,
                        "complete": rows[y].complete if y in rows else 0,
                        "in_progress": rows[y].in_progress if y in rows else 0,
                        "planned": rows[y].planned if y in rows else 0,
                        "milestones": rows[y].milestones if y in rows else 0,
                    }
                    for y in all_years
                ],
            }
            for (label, status, undated, rows) in per
        ]
        return JSONResponse(
            {
                "basis": basis,
                "basis_label": YEAR_BASES[basis],
                "years": all_years,
                "max_total": max_total,
                "versions": versions,
            }
        )

    @app.get("/mission", response_class=HTMLResponse)
    def mission_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Mission Control",
                "<div class=panel>Load a schedule to populate the visual wall.</div>",
            )
        return _page(st, "Mission Control", _mission_body(st.target_uid))

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
                schedules.append(
                    st.scope(sch)
                )  # the CPM is for the scoped schedule; keep them paired
            except CPMError:
                skipped.append(key)
        return schedules, cpms, skipped

    def _solvable_versions_full() -> tuple[
        list[Schedule], list[CPMResult], list[_Analysis], list[str]
    ]:
        """Like _solvable_versions() but also returns the cached _Analysis objects."""
        st = session()
        schedules: list[Schedule] = []
        cpms: list[CPMResult] = []
        analyses: list[_Analysis] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                a = st.analysis_for(key, sch)
                schedules.append(st.scope(sch))  # paired with a.cpm (both over the active scope)
                cpms.append(a.cpm)
                analyses.append(a)
            except CPMError:
                skipped.append(key)
        return schedules, cpms, analyses, skipped

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
                "<div class=panel>Load a schedule to run the path analysis.</div>",
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
            facts += driving_path_facts(sch, st.analysis_for(name, sch).cpm, text)
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
                facts += driving_path_facts(sch, st.analysis_for(key, sch).cpm, text)
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
            return _ask_response(st, facts, text)
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "no analyzable versions loaded"}, status_code=422)
        # driving-path questions resolve against the newest analyzable version
        facts = build_workbook_fact_sheet(schedules, cpms)
        facts += driving_path_facts(schedules[-1], cpms[-1], text)
        return _ask_response(st, facts, text)

    @app.get("/api/driving-path")
    def driving_path_answer(uid: int = Query(...), scope: str = Query("")) -> JSONResponse:
        """One-click DETERMINISTIC driving-path answer for a UID — engine only, NO AI. The Ask
        panel's "Driving path" button calls this so the operator never depends on the model for
        path/slack (the model kept getting it wrong); the figures come straight from the engine."""
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "no schedule loaded"}, status_code=400)
        key = scope.strip()
        if key and key in st.schedules:
            sch = st.schedules[key]
            try:
                cpm = st.analysis_for(key, sch).cpm
            except CPMError as exc:
                return JSONResponse({"error": str(exc)}, status_code=422)
        else:
            schedules, cpms, _skipped = _solvable_versions()
            if not schedules:
                return JSONResponse({"error": "no analyzable schedule loaded"}, status_code=422)
            sch, cpm = schedules[-1], cpms[-1]
        facts = driving_path_summary(sch, cpm, uid)
        if not facts:
            return JSONResponse(
                {
                    "uid": uid,
                    "answer": f"UID {uid} is not a scheduled activity in this file.",
                    "facts": [],
                }
            )
        return JSONResponse(
            {
                "uid": uid,
                "answer": " ".join(f.text for f in facts),
                "facts": [
                    {
                        "text": f.text,
                        "citations": [
                            {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                            for c in f.citations[:12]
                        ],
                    }
                    for f in facts
                ],
            }
        )

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
        schedules, cpms, analyses, _skipped = _solvable_versions_full()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        return JSONResponse(_trend_data(schedules, cpms, analyses, uid))

    @app.get("/api/margin")
    def margin_json() -> JSONResponse:
        """Schedule-margin burndown across versions: total vs effective buffer per submission.

        Iterates the loaded versions (oldest -> newest by data date), skipping any whose network
        cannot be solved, and reports each version's total and effective margin (working days) over
        the active scope. ``{"versions": []}`` when nothing analyzable is loaded.
        """
        st = session()
        rows: list[tuple[str, str | None, Schedule, CPMResult]] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                continue
            status = raw.status_date.date().isoformat() if raw.status_date else None
            rows.append((raw.source_file or raw.name, status, st.scope(raw), a.cpm))
        if not rows:
            return JSONResponse({"versions": []})
        points = compute_margin_trend(rows)
        return JSONResponse(
            {
                "versions": [
                    {
                        "label": p.label,
                        "status_date": p.status_date,
                        "total": p.total_margin_days,
                        "effective": p.effective_margin_days,
                    }
                    for p in points
                ]
            }
        )

    @app.get("/cei", response_class=HTMLResponse)
    def cei_view(target: str | None = Query(None)) -> HTMLResponse:
        st = session()
        # focusing a target from this view sets the session-wide target (ADR-0061), so the
        # /api/cei fetch that draws the chart sees the same activity; a blank clears it.
        if target is not None:
            st.target_uid = _parse_uid(target)
        if len(st.schedules) < 2:
            return _page(
                st,
                "Bow Wave / CEI",
                "<div class=panel>Load at least two versions (monthly snapshots) to run the "
                "bow-wave / CEI analysis.</div>",
            )
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid)
        except ValueError as exc:
            return _page(st, "Bow Wave / CEI", f"<div class=panel>{_e(exc)}</div>")
        return _page(st, "Bow Wave / CEI", _export_bar("cei") + _cei_body(wave, st.target_uid))

    @app.get("/api/cei")
    def cei_json() -> JSONResponse:
        st = session()
        if len(st.schedules) < 2:
            return JSONResponse({"error": "need at least two versions"}, status_code=400)
        try:
            wave = compute_bow_wave(st.ordered(), st.target_uid)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_cei_data(wave, st.target_uid))

    @app.get("/scurve", response_class=HTMLResponse)
    def scurve_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "S-Curve",
                "<div class=panel>Load a schedule to see the cumulative progress S-curve "
                "(load several versions to animate it over time).</div>",
            )
        try:
            sc = compute_s_curve(st.ordered())
        except ValueError as exc:
            return _page(st, "S-Curve", f"<div class=panel>{_e(exc)}</div>")
        return _page(st, "S-Curve", _scurve_body(sc, _scurve_filter_fields(st.ordered())))

    @app.get("/api/scurve")
    def scurve_json(cf: list[str] = _CF_QUERY, cv: list[str] = _CV_QUERY) -> JSONResponse:
        st = session()
        if not st.schedules:
            return JSONResponse({"error": "no schedule loaded"}, status_code=400)
        versions = st.ordered()
        # per-chart filter (independent of the page-wide Groups & Filters): up to MAX_FIELDS
        # (field, value) conditions over the parent file's fields, applied on top of the scope.
        criteria = _pair_criteria(cf, cv, versions)
        if criteria:
            versions = [
                v for v in (filter_schedule(s, criteria) for s in versions) if non_summary(v)
            ]
        if not versions:
            return JSONResponse({"months": [], "versions": []})
        try:
            sc = compute_s_curve(versions)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_scurve_data(sc))

    @app.get("/ribbon", response_class=HTMLResponse)
    def ribbon_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Schedule Quality Ribbon",
                "<div class=panel>Load one or more schedules to see the "
                "schedule-quality ribbon.</div>",
            )
        rows: list[tuple[str, object]] = []
        skipped: list[str] = []
        for key, sch in st.ordered_versions():
            try:
                analysis = st.analysis_for(key, sch)
            except CPMError:
                skipped.append(key)
                continue
            rows.append((key, compute_ribbon(sch, analysis.cpm, analysis.audit)))
        note = _skipped_notice(skipped) if skipped else ""
        return _page(st, "Schedule Quality Ribbon", _ribbon_body(rows, note))

    @app.get("/evolution", response_class=HTMLResponse)
    def evolution_view(target: str | None = Query(None), tier: str = Query("off")) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if len(schedules) < 2:
            return _page(
                st,
                "Critical-Path Evolution",
                _skipped_notice(skipped)
                + "<div class=panel>Load at least two analyzable versions to watch the "
                "critical path evolve.</div>",
            )
        uid = _parse_uid(target) if target is not None else st.target_uid
        return _page(
            st,
            "Critical-Path Evolution",
            _export_bar("evolution")
            + _skipped_notice(skipped)
            + _evolution_body(schedules, cpms, uid, tier),
        )

    @app.get("/api/evolution")
    def evolution_json(target: str | None = Query(None), tier: str = Query("off")) -> JSONResponse:
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        uid = _parse_uid(target) if target is not None else st.target_uid
        if tier in _EVO_TIER_SELECT:
            return JSONResponse(_evolution_tier_data(schedules, cpms, uid, tier))
        return JSONResponse(_evolution_data(schedules, cpms, uid))

    @app.get("/driving-path", response_class=HTMLResponse)
    def driving_path_view(
        source: str | None = Query(None), target: str | None = Query(None)
    ) -> HTMLResponse:
        st = session()
        schedules, cpms, skipped = _solvable_versions()
        if not schedules:
            return _page(
                st,
                "Driving Path",
                "<div class=panel>Load a schedule to trace the driving path between two "
                "activities.</div>",
            )
        src = _parse_uid(source)
        tgt = _parse_uid(target)
        return _page(
            st,
            "Driving Path",
            _skipped_notice(skipped) + _driving_path_body(schedules, cpms, src, tgt),
        )

    @app.get("/groups", response_class=HTMLResponse)
    def groups_view(request: Request) -> HTMLResponse:
        st = session()
        versions = st.ordered_versions()
        if not versions:
            return _page(
                st,
                "Groups & Filters",
                "<div class=panel>Load a schedule to scope the metrics by a field value.</div>",
            )
        qp = request.query_params
        version_key = qp.get("version") or versions[-1][0]
        sch = dict(versions).get(version_key, versions[-1][1])
        breakdown = qp.get("breakdown") or ""
        # Parse any submitted filter rows. Each row's selected values arrive as repeated value{i}
        # params (the MS-Project-style multi-select); a legacy single `value` list (one per field,
        # exact match) is still honoured. Empty values = "field is populated".
        fields = qp.getlist("field")
        legacy = qp.getlist("value")
        param_criteria: list[Criterion] = []
        for i, f in enumerate(fields):
            if not f:
                continue
            vals = qp.getlist(f"value{i}")
            param_criteria.append((f, vals if vals else (legacy[i] if i < len(legacy) else "")))
        param_criteria = param_criteria[:MAX_FIELDS]
        # Apply / clear MUTATE the session-wide filter (ADR-0104) so it scopes every page and every
        # loaded file; without them a row selection just PREVIEWS here without persisting.
        if "clear" in qp:
            st.set_filter(())
        elif "apply" in qp:
            st.set_filter(param_criteria)
        # the page shows the URL preview when rows are present, else the live session filter
        criteria: list[Criterion] = param_criteria if fields else list(st.active_filter)
        applied = bool(st.active_filter) and criteria == list(st.active_filter)
        return _page(
            st,
            "Groups & Filters",
            _groups_body(versions, version_key, sch, criteria, breakdown, applied),
        )

    @app.get("/api/group-values")
    def group_values_json(
        version: str | None = Query(None), field: str = Query("")
    ) -> JSONResponse:
        """Distinct values of ``field`` across ALL loaded files — the /groups value autocomplete.

        Aggregated over every version (not just one) because the filter applies to all files, so a
        value present in any version must be offerable. ``version`` is accepted for compatibility."""
        st = session()
        schedules = [s for _, s in st.ordered_versions()]
        if not schedules or not field:
            return JSONResponse({"values": []})
        values = distinct_values(schedules, field)
        return JSONResponse({"values": values[:500]})  # cap for a sane datalist

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
            _export_bar("forecast")
            + _skipped_notice(skipped)
            + _forecast_body(schedules, cpms, sets),
        )

    @app.get("/api/forecast")
    def forecast_json() -> JSONResponse:
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        sets = [compute_finish_forecasts(s, c) for s, c in zip(schedules, cpms, strict=True)]
        return JSONResponse(_forecast_data(schedules, sets))

    @app.get("/curves", response_class=HTMLResponse)
    def curves_view() -> HTMLResponse:
        st = session()
        # the finish/slippage curves are stored-date views — they do not need the network
        # to solve, so every loaded version contributes (unlike the CPM-gated pages)
        versions = st.ordered()
        if not versions:
            return _page(
                st,
                "Finish & Slippage",
                "<div class=panel>Load at least one schedule to see the finish and slippage "
                "curves.</div>",
            )
        try:
            curves = compute_month_curves(versions)
        except ValueError as exc:
            return _page(st, "Finish & Slippage", f"<div class=panel>{_e(exc)}</div>")
        return _page(st, "Finish & Slippage", _export_bar("curves") + _curves_body(curves))

    @app.get("/api/curves")
    def curves_json(hide_complete: bool = Query(False)) -> JSONResponse:
        st = session()
        versions = st.ordered()
        if not versions:
            return JSONResponse({"error": "need at least one schedule"}, status_code=400)
        if hide_complete:
            # drop 100%-complete activities so the curves show only the remaining/forecast work
            crit: list[Criterion] = [("% Complete", ["In Progress", "Not Started"])]
            versions = [v for v in (filter_schedule(s, crit) for s in versions) if non_summary(v)]
            if not versions:
                return JSONResponse({"months": [], "versions": []})
        try:
            curves = compute_month_curves(versions)
        except ValueError:
            return JSONResponse({"months": [], "versions": []})
        return JSONResponse(_curves_data(curves))

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
                metric_results_table("Schedule quality", quality),
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
        cols: str = Query(""),
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
        # selected custom-field columns to mirror the grid (ADR-0095): only the schedule's own
        # mapped fields, in the order requested, deduped.
        valid = set(sch.custom_field_labels)
        custom_labels = list(
            dict.fromkeys(c for c in (s.strip() for s in cols.split(",")) if c in valid)
        )
        tableset = TableSet(
            f"Path analysis - {sch.name}",
            (driving_table(rows, target, custom_labels),),  # type: ignore[arg-type]
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
            wave = compute_bow_wave(st.ordered(), st.target_uid)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt, TableSet("Bow Wave - CEI", bow_wave_tables(wave)), "bow-wave-cei"
        )

    @app.get("/export/{fmt}/evolution")
    def export_evolution(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if len(schedules) < 2:
            return JSONResponse({"error": "need at least two analyzable versions"}, status_code=400)
        ev = compute_path_evolution(schedules, cpms)
        return _export_response(
            fmt,
            TableSet("Critical-path evolution", path_evolution_tables(ev)),
            "critical-path-evolution",
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
        carnac = compute_carnac_summary(schedules[-1], cpms[-1], sets[-1])
        return _export_response(
            fmt,
            TableSet("Finish forecasts", (carnac_table(carnac), *forecast_tables(labels, sets))),
            "forecast",
        )

    @app.get("/export/{fmt}/curves")
    def export_curves(fmt: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        versions = st.ordered()
        if not versions:
            return JSONResponse({"error": "need at least one schedule"}, status_code=400)
        try:
            curves = compute_month_curves(versions)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return _export_response(
            fmt,
            TableSet("Finish & slippage curves", month_curves_tables(curves)),
            "finish-slippage-curves",
        )

    @app.get("/export/{fmt}/wbs/{name}")
    def export_wbs(fmt: str, name: str) -> Response:
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        sch = st.schedules.get(name)
        if sch is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        groups = compute_wbs_breakdown(sch)
        return _export_response(
            fmt,
            TableSet(f"WBS breakdown - {sch.name}", wbs_breakdown_tables(groups)),
            f"{name}-wbs",
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

    @app.get("/risks", response_class=HTMLResponse)
    def risks_view() -> HTMLResponse:
        st = session()
        if not st.schedules:
            return _page(
                st,
                "Risks & Opportunities",
                "<div class=panel>Load a schedule to see risks, issues &amp; opportunities.</div>",
            )
        # latest analyzable version (with the one before it for change findings), scoped to the
        # session filter; keep the key so the narrative cache + ask scope stay consistent.
        solv: list[tuple[str, Schedule, _Analysis]] = []
        skipped: list[str] = []
        for key, raw in st.ordered_versions():
            try:
                a = st.analysis_for(key, raw)
            except CPMError:
                skipped.append(key)
                continue
            solv.append((key, st.scope(raw), a))
        if not solv:
            return _page(
                st,
                "Risks & Opportunities",
                _skipped_notice(skipped) + "<div class=panel>No analyzable version loaded.</div>",
            )
        key, current, cur_an = solv[-1]
        prior = solv[-2][1] if len(solv) >= 2 else None
        prior_cpm = solv[-2][2].cpm if len(solv) >= 2 else None
        findings = recommend(
            current,
            prior,
            current_cpm=cur_an.cpm,
            prior_cpm=prior_cpm,
            target_uid=st.target_uid,
        )
        # Render the deterministic narrative immediately so the page never blocks on the model; the
        # local-AI polish (when a model is active) is fetched asynchronously by ai_polish.js via
        # /api/ai/narrative and swapped in. The old synchronous per-statement generate on page load
        # made this page hang (effectively "won't open") on big workbooks with a slow local model.
        body = _skipped_notice(skipped) + _risks_body(current, findings, cur_an.narrative, key)
        return _page(st, "Risks & Opportunities", body, ask_schedule=key)

    @app.get("/sra", response_class=HTMLResponse)
    def sra_view(file: str = Query("")) -> HTMLResponse:
        st = session()
        # operator picks which loaded file the SRA runs against; persist it so the simulation API
        # and the server-rendered override/risk tables all target the same schedule.
        if file.strip() and file.strip() in st.schedules:
            st.sra_file = file.strip()
        if not st.schedules:
            return _page(
                st,
                "Risk Analysis (SRA)",
                "<div class=panel>Load a schedule to run the Schedule Risk Analysis "
                "(Monte-Carlo).</div>",
            )
        # Render the controls + empty chart hosts IMMEDIATELY — the simulation (1000x CPM) is run
        # only when sra.js fetches /api/sra, never on page load (a synchronous run here would hang
        # the page on a large schedule, the prior Risks/Briefing bug).
        return _page(st, "Risk Analysis (SRA)", _sra_body(st))

    @app.post("/sra/risk")
    def sra_risk(
        low: str = Form(""),
        ml: str = Form(""),
        high: str = Form(""),
        uid: str = Form(""),
        opt_days: str = Form(""),
        ml_days: str = Form(""),
        pess_days: str = Form(""),
        remove: str = Form(""),
        clear: str = Form(""),
    ) -> RedirectResponse:
        """Persist the analyst's SRA risk inputs on the session, then redirect back to /sra.

        Handles three independent operations (any combination per request): the global triangular
        percentages (entered as 90/100/110 → stored as fractions, clamped + ordered), a per-activity
        3-point override (days → working minutes via the schedule calendar; ignored for an unknown /
        summary uid), and override removal (``remove`` a single uid / ``clear`` all)."""
        st = session()
        # global low/ml/high (percent inputs → fractions); only update on a non-blank value
        lo, mid, hi = st.sra_low, st.sra_ml, st.sra_high
        if low.strip():
            lo = _clamp_float(low, 0.05, 1.0, lo, scale=0.01)
        if ml.strip():
            mid = _clamp_float(ml, 0.5, 1.5, mid, scale=0.01)
        if high.strip():
            hi = _clamp_float(high, 1.0, 3.0, hi, scale=0.01)
        # coerce to low <= ml <= high (the triangular a <= m <= b)
        mid = max(lo, mid)
        hi = max(mid, hi)
        st.sra_low, st.sra_ml, st.sra_high = lo, mid, hi
        # per-activity override removal / clear
        if clear.strip():
            st.sra_overrides.clear()
        rm = _parse_uid(remove)
        if rm is not None:
            st.sra_overrides.pop(rm, None)
        # per-activity 3-point override (days → working minutes), only for a real non-summary task
        add_uid = _parse_uid(uid)
        if add_uid is not None and (opt_days.strip() or ml_days.strip() or pess_days.strip()):
            chosen = _sra_selected(st)
            if chosen is not None:
                _, sch, _cpm = chosen
                task = sch.tasks_by_id.get(add_uid)
                if task is not None and not task.is_summary:
                    per_day = sch.calendar.working_minutes_per_day or 1
                    o = max(0, round(_to_float(opt_days, 0.0) * per_day))
                    m = max(0, round(_to_float(ml_days, 0.0) * per_day))
                    p = max(0, round(_to_float(pess_days, 0.0) * per_day))
                    m = max(o, m)  # keep opt <= ml <= pess
                    p = max(m, p)
                    st.sra_overrides[add_uid] = (o, m, p)
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/risk-event")
    def sra_risk_event(
        name: str = Form(""),
        prob: str = Form(""),
        imp_low: str = Form(""),
        imp_ml: str = Form(""),
        imp_high: str = Form(""),
        affected: str = Form(""),
        remove: str = Form(""),
        clear: str = Form(""),
    ) -> RedirectResponse:
        """Maintain the discrete-risk register (ADR-0106 risk-driver method), then redirect to /sra.

        A risk = a name, a probability (% it occurs), a 3-point *multiplicative* impact on the
        sampled duration of the activities it is mapped to (entered as percentages, e.g. 100/120/150),
        and an ``affected`` UID list. ``clear`` empties the register; ``remove`` drops one risk by id.
        Affected UIDs are validated against the latest solvable schedule — unknown / summary uids are
        dropped, and a risk that maps to no real activity is ignored (it could never fire)."""
        st = session()
        if clear.strip():
            st.sra_risks.clear()
        rid = remove.strip()
        if rid:
            st.sra_risks = [r for r in st.sra_risks if r.id != rid]
        label = name.strip()
        uids = _parse_uid_list(affected)
        if label and uids:
            chosen = _latest_solvable(st)
            valid: list[int] = []
            if chosen is not None:
                _, sch, _cpm = chosen
                for u in uids:
                    task = sch.tasks_by_id.get(u)
                    if task is not None and not task.is_summary and u not in valid:
                        valid.append(u)
            if valid:
                # percentages -> fractions; probability clamped to [0,1]; impacts ordered & >= 0
                p = _clamp_float(prob, 0.0, 1.0, 0.0, scale=0.01)
                lo = max(0.0, _to_float(imp_low, 100.0) * 0.01)
                mid = max(0.0, _to_float(imp_ml, 100.0) * 0.01)
                hi = max(0.0, _to_float(imp_high, 100.0) * 0.01)
                mid = max(lo, mid)  # keep impact_low <= impact_ml <= impact_high
                hi = max(mid, hi)
                st.sra_risk_seq += 1
                st.sra_risks.append(
                    RiskEvent(
                        id=f"R{st.sra_risk_seq}",
                        name=label,
                        probability=p,
                        impact_low=lo,
                        impact_ml=mid,
                        impact_high=hi,
                        affected=tuple(valid),
                    )
                )
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/api/sra")
    def sra_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, cpm = chosen
        iters = max(100, min(10000, iterations))
        dist = "pert" if distribution == "pert" else "triangular"
        config = SRAConfig(
            iterations=iters,
            auto_low=st.sra_low,
            auto_most_likely=st.sra_ml,
            auto_high=st.sra_high,
            distribution=dist,
        )
        overrides = {
            u: ActivityRisk(u, o, m, p)
            for u, (o, m, p) in st.sra_overrides.items()
            if u in sch.tasks_by_id
        }
        # never 500 on the simulation — surface the engine message as a 422 instead
        try:
            result = compute_sra(
                sch, cpm, config=config, overrides=overrides, risks=tuple(st.sra_risks)
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_sra_data(st, sch, result))

    # --- SSI Schedule Risk & Opportunity Analysis (ADR-0123) -------------------------------
    @app.post("/sra/ssi-run-config")
    def ssi_run_config(
        focus_uid: str = Form(""),
        occurrence_mode: str = Form("random_each"),
        correlation: float = Form(0.0),
        use_risks: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        st.sra_focus_uid = int(focus_uid) if focus_uid.strip().isdigit() else None
        st.sra_occurrence_mode = (
            "exact_overall" if occurrence_mode == "exact_overall" else "random_each"
        )
        st.sra_correlation = min(1.0, max(0.0, correlation))
        st.sra_use_risk_register = use_risks in ("on", "true", "1")
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/factor-table")
    def ssi_factor_table(
        sub1: float = Form(50.0),
        add1: float = Form(10.0),
        sub2: float = Form(40.0),
        add2: float = Form(20.0),
        sub3: float = Form(30.0),
        add3: float = Form(30.0),
        sub4: float = Form(20.0),
        add4: float = Form(40.0),
        sub5: float = Form(10.0),
        add5: float = Form(50.0),
    ) -> RedirectResponse:
        st = session()
        raw = ((1, sub1, add1), (2, sub2, add2), (3, sub3, add3), (4, sub4, add4), (5, sub5, add5))
        st.sra_factor_rows = tuple(
            (f, min(100.0, max(0.0, s)), min(300.0, max(0.0, a))) for f, s, a in raw
        )
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/factor")
    def ssi_set_factor(uids: str = Form(""), factor: int = Form(3)) -> RedirectResponse:
        st = session()
        f = min(5, max(0, factor))  # factor 0 is valid = no Best/Worst uncertainty
        for tok in re.split(r"[,\s]+", uids.strip()):
            if tok.isdigit():
                st.sra_factors[int(tok)] = f
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/auto-calc")
    def ssi_auto_calc(scope: str = Form("all"), uids: str = Form("")) -> RedirectResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is not None:
            _key, sch, _cpm = chosen
            tbl = RiskFactorTable(rows=st.sra_factor_rows)
            want: set[int] | None = None
            if scope == "selected":
                want = {int(t) for t in re.split(r"[,\s]+", uids.strip()) if t.isdigit()}
            for t in non_summary(sch):
                u = t.unique_id
                if u not in st.sra_factors or (want is not None and u not in want):
                    continue
                rem = (
                    t.remaining_duration_minutes
                    if t.remaining_duration_minutes is not None
                    else t.duration_minutes
                )
                bc, _ml, wc = factor_to_bc_wc(rem, st.sra_factors[u], tbl)
                st.sra_bcwc[u] = (bc, wc)
        return RedirectResponse(url="/sra", status_code=303)

    @app.post("/sra/ssi-risk")
    def ssi_risk(
        action: str = Form("add"),
        rid: str = Form(""),
        name: str = Form(""),
        prob: float = Form(0.0),
        impact_days: float = Form(0.0),
        affected: str = Form(""),
        consequence: str = Form(""),
    ) -> RedirectResponse:
        st = session()
        if action == "remove":
            st.sra_ssi_risks = [r for r in st.sra_ssi_risks if r.id != rid]
        elif action == "clear":
            st.sra_ssi_risks = []
        else:
            uids = tuple(int(t) for t in re.split(r"[,\s]+", affected.strip()) if t.isdigit())
            if uids:
                st.sra_ssi_risk_seq += 1
                cons = int(consequence) if consequence.strip().isdigit() else None
                st.sra_ssi_risks.append(
                    ScheduleRisk(
                        id=f"R{st.sra_ssi_risk_seq}",
                        name=name.strip() or f"Risk {st.sra_ssi_risk_seq}",
                        probability=min(1.0, max(0.0, prob / 100.0)),
                        impact_days=impact_days,
                        affected=uids,
                        consequence_rating=min(5, max(1, cons)) if cons is not None else None,
                    )
                )
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/api/sra/ssi")
    def sra_ssi_json(
        iterations: int = Query(1000), distribution: str = Query("triangular")
    ) -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        cfg = SRAConfig(
            iterations=max(100, min(10000, iterations)),
            distribution="pert" if distribution == "pert" else "triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        try:
            result = compute_sra_ssi(
                sch,
                config=cfg,
                three_point=_ssi_three_point(st, sch),
                risks=tuple(st.sra_ssi_risks),
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return JSONResponse(_ssi_data(sch, result))

    @app.get("/api/sra/oat")
    def sra_oat_json() -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        exclude = (
            frozenset(u for r in st.sra_ssi_risks for u in r.affected)
            if st.sra_use_risk_register
            else frozenset()
        )
        try:
            oat = compute_oat_sensitivity(
                sch,
                three_point=_ssi_three_point(st, sch),
                target_uid=st.sra_focus_uid,
                exclude_uids=exclude,
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        names = sch.tasks_by_id
        mpd = sch.calendar.working_minutes_per_day or 480
        return JSONResponse(
            {
                "rows": [
                    {
                        "uid": o.unique_id,
                        "name": names[o.unique_id].name if o.unique_id in names else "",
                        "bc_days": round(o.bc_minutes / mpd, 1),
                        "wc_days": round(o.wc_minutes / mpd, 1),
                        "ml_days": round(o.ml_minutes / mpd, 1),
                        "opportunity": o.opportunity_days,
                        "risk": o.risk_days,
                        "total": o.total_days,
                    }
                    for o in oat[:40]
                ]
            }
        )

    @app.get("/api/sra/grid")
    def sra_grid_json() -> JSONResponse:
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, cpm = chosen
        return JSONResponse(
            {
                "rows": _ssi_grid_rows(st, sch, cpm),
                "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
            }
        )

    @app.post("/sra/grid")
    def sra_grid_save(deltas: str = Form("[]")) -> JSONResponse:
        """Batched inline-edit save from the SSI grid: one JSON array of per-task deltas
        ``[{uid, factor?, bc_days?, wc_days?, focus?}]`` (the fields_json/gantt JSON-in-page
        precedent). A factor delta auto-fills Best/Worst from the factor table; an explicit
        bc_days/wc_days delta is a manual override that wins (mirrors ``_ssi_three_point``)."""
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "No analyzable schedule loaded."}, status_code=400)
        _key, sch, _cpm = chosen
        mpd = sch.calendar.working_minutes_per_day or 480
        tbl = RiskFactorTable(rows=st.sra_factor_rows)
        by_id = sch.tasks_by_id
        try:
            items = json.loads(deltas)
        except (ValueError, TypeError):
            return JSONResponse({"error": "bad deltas payload"}, status_code=422)
        saved = 0
        for d in items if isinstance(items, list) else []:
            if not isinstance(d, dict):
                continue
            uid = d.get("uid")
            if not isinstance(uid, int) or uid not in by_id or by_id[uid].is_summary:
                continue
            task = by_id[uid]
            rem = (
                task.remaining_duration_minutes
                if task.remaining_duration_minutes is not None
                else task.duration_minutes
            )
            changed = False
            if d.get("focus"):
                st.sra_focus_uid = uid
                changed = True
            if d.get("factor") not in (None, ""):
                try:
                    # factor 0 is VALID (no Best/Worst uncertainty -> use remaining); only 1..5 carry
                    # a Best/Worst spread, so clamp to 0..5, not 1..5
                    f = min(5, max(0, int(d["factor"])))
                except (TypeError, ValueError):
                    f = None
                if f is not None:
                    st.sra_factors[uid] = f
                    bc, _ml, wc = factor_to_bc_wc(rem, f, tbl)
                    st.sra_bcwc[uid] = (bc, wc)
                    changed = True
            bc_min, wc_min = st.sra_bcwc.get(uid, (rem, rem))
            manual = False
            for key, slot in (("bc_days", 0), ("wc_days", 1)):
                if d.get(key) not in (None, ""):
                    try:
                        minutes = max(0, round(float(d[key]) * mpd))
                    except (TypeError, ValueError):
                        continue
                    bc_min, wc_min = (minutes, wc_min) if slot == 0 else (bc_min, minutes)
                    manual = True
            if manual:
                st.sra_bcwc[uid] = (int(bc_min), int(wc_min))
                changed = True
            saved += int(changed)
        return JSONResponse({"ok": True, "saved": saved})

    @app.get("/sra/ssi/save")
    def sra_ssi_save() -> Response:
        """Download the whole SSI setup (focus, factor table, per-task factors + Best/Worst,
        risk register, run options) as a versioned JSON file — local download, CUI-safe."""
        st = session()
        return Response(
            json.dumps(_ssi_setup_dict(st), indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sra-ssi-setup.json"'},
        )

    @app.post("/sra/ssi/load")
    def sra_ssi_load(setup: UploadFile) -> RedirectResponse:
        """Restore an SSI setup from a previously-saved JSON file. UIDs are validated against the
        active schedule (unknown/summary tasks dropped, factors clamped) so a setup saved on one
        version applies cleanly to another."""
        st = session()
        try:
            payload = json.loads(setup.file.read())
        except (ValueError, TypeError):
            return RedirectResponse(url="/sra", status_code=303)
        if isinstance(payload, dict):
            _apply_ssi_setup(st, payload)
        return RedirectResponse(url="/sra", status_code=303)

    @app.get("/export/{fmt}/sra")
    def export_sra(fmt: str) -> Response:
        """The SSI setup + a focus-targeted run + the deterministic OAT as a six-table Excel/Word
        hand-out (ADR-0123). Runs the Monte-Carlo + OAT on demand (off the page-load path)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        tp = _ssi_three_point(st, sch)
        cfg = SRAConfig(
            iterations=2000,
            distribution="triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        result = compute_sra_ssi(sch, config=cfg, three_point=tp, risks=tuple(st.sra_ssi_risks))
        exclude = (
            frozenset(u for r in st.sra_ssi_risks for u in r.affected)
            if st.sra_use_risk_register
            else frozenset()
        )
        oat = compute_oat_sensitivity(
            sch, three_point=tp, target_uid=st.sra_focus_uid, exclude_uids=exclude
        )
        if fmt == "docx":
            # the comprehensive narrative SRA report (PM summary -> per-section detail + vector
            # charts + the 5x5 matrices + assumptions); ADR-0124
            return Response(
                content=render_document(_sra_report_blocks(st, sch, result, oat)),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="sra-report.docx"'},
            )
        return _export_response(fmt, _ssi_export_tables(st, sch, result, oat), "sra-ssi")

    @app.get("/export/{fmt}/sra-registry")
    def export_sra_registry(fmt: str) -> Response:
        """The risk / opportunity registry as a standalone downloadable workbook/doc (register +
        the per-task Best/Worst durations) — the operator's downloadable risk registry (ADR-0124)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        st = session()
        chosen = _sra_selected(st)
        if chosen is None:
            return JSONResponse({"error": "need an analyzable schedule"}, status_code=400)
        _key, sch, _cpm = chosen
        tp = _ssi_three_point(st, sch)
        cfg = SRAConfig(
            iterations=2000,
            distribution="triangular",
            target_uid=st.sra_focus_uid,
            occurrence_mode=st.sra_occurrence_mode,
            use_risk_register=st.sra_use_risk_register,
            correlation=st.sra_correlation,
        )
        result = compute_sra_ssi(sch, config=cfg, three_point=tp, risks=tuple(st.sra_ssi_risks))
        keep = {"Risk register", "Per-task durations"}
        full = _ssi_export_tables(st, sch, result, [])  # registry needs no OAT (skip the 2N solves)
        ts = TableSet(
            f"SRA Risk Registry - {sch.name}",
            tuple(t for t in full.tables if t.title in keep),
        )
        return _export_response(fmt, ts, "sra-risk-registry")

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

    @app.get("/export/{fmt}/briefing")
    def export_briefing(fmt: str) -> Response:
        """The leadership Executive Briefing as a Word (.docx) or Excel (.xlsx) hand-out — the
        same cited content the /briefing page renders (ADR-0121)."""
        if (bad := _bad_format(fmt)) is not None:
            return bad
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"error": "need at least one analyzable schedule"}, status_code=400)
        briefing = build_briefing(schedules, cpms=cpms)
        if fmt == "docx":
            blocks = cast("list[Block]", briefing_blocks(briefing))
            return Response(
                content=render_document(blocks),
                media_type=_EXPORT_MEDIA["docx"][0],
                headers={"Content-Disposition": 'attachment; filename="executive-briefing.docx"'},
            )
        tables = tuple(
            Table(s.heading, s.table.headers or ("Field", "Value"), s.table.rows)
            for s in briefing.sections
            if s.table is not None and s.table.rows
        )
        return _export_response(fmt, TableSet(briefing.title, tables), "executive-briefing")

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
        # Render the DETERMINISTIC briefing immediately so the page opens instantly. The
        # synchronous per-section AI polish on page load made this page hang (effectively "won't
        # open") on big workbooks with a slow local model. ai_polish.js fetches /api/ai/briefing in
        # the background and swaps in the local-AI-polished version when a model is active.
        briefing = build_briefing(schedules, cpms=cpms)
        body = (
            _skipped_notice(skipped)
            + '<div id=briefingBody data-ai-endpoint="/api/ai/briefing">'
            + _briefing_body(briefing)
            + '</div><script src="/static/ai_polish.js"></script>'
        )
        return _page(st, "Executive Briefing", body)

    @app.get("/api/ai/narrative")
    def api_ai_narrative(key: str = "") -> JSONResponse:
        """Local-AI-polished Risks narrative for one schedule (fetched off the page-load path).

        Runs the (possibly slow) model here instead of during the page render, wrapping the whole
        AI path so it can never hang or 500 the page: ``{"polished": false}`` when no model is
        active or anything fails (the client keeps the engine read), else the polished list HTML."""
        st = session()
        raw = st.schedules.get(key)
        if raw is None:
            return JSONResponse({"polished": False})
        try:
            analysis = st.analysis_for(key, raw)
            narrative = _polished_narrative(st, key, st.scope(raw), analysis)
            polished = narrative is not analysis.narrative  # a real backend produced new prose
            html = "".join(f"<li>{_e(s.rendered())}</li>" for s in narrative.statements)
        except Exception:
            logger.warning("AI narrative endpoint failed; client keeps the deterministic read")
            return JSONResponse({"polished": False})
        return JSONResponse({"polished": polished, "html": html})

    @app.get("/api/ai/briefing")
    def api_ai_briefing() -> JSONResponse:
        """Local-AI-polished Executive Briefing (fetched off the page-load path).

        Same contract as :func:`api_ai_narrative`: never blocks or 500s the page —
        ``{"polished": false}`` when no model is active or generation fails, else the polished
        briefing body HTML for the client to swap in."""
        st = session()
        schedules, cpms, _skipped = _solvable_versions()
        if not schedules:
            return JSONResponse({"polished": False})
        backend = _active_backend(st)
        if backend.name == "null":
            return JSONResponse({"polished": False})
        try:
            briefing = build_briefing(schedules, cpms=cpms, backend=backend)
            html = _briefing_body(briefing)
        except Exception:
            logger.warning("AI briefing endpoint failed; client keeps the deterministic briefing")
            return JSONResponse({"polished": False})
        return JSONResponse({"polished": True, "html": html})

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
        endpoint: str = Form("http://127.0.0.1:11434"),
        openai_endpoint: str = Form("http://127.0.0.1:1234"),
        second_backend: str = Form("none"),
        second_model: str = Form(""),
        gen_timeout: float = Form(900.0),
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
        # generation timeout: clamp to a sane window (30s … 1h) so a big slow model can finish
        # but a wedged one can't hang a request forever
        gen_timeout = min(3600.0, max(30.0, gen_timeout))
        # the backend constructor enforces loopback too (Law 1) — this just keeps a typo'd
        # remote host from sitting in the config looking accepted
        if not is_local_http_endpoint(endpoint.strip()):
            endpoint = "http://127.0.0.1:11434"
        if not is_local_http_endpoint(openai_endpoint.strip()):
            openai_endpoint = "http://127.0.0.1:1234"
        st.ai_config = AIConfig(
            classification=cls,
            backend=backend,
            model=model,
            endpoint=endpoint.strip(),
            qa_mode=qa_mode,
            openai_endpoint=openai_endpoint.strip(),
            second_backend=second_backend,
            second_model=second_model.strip(),
            gen_timeout=gen_timeout,
        )
        st.backend_cache = None  # re-route immediately — a settings change must take effect now
        st.second_cache = None
        # Lazy Ollama lifecycle (ADR-0122): the desktop launcher's manager starts `ollama serve`
        # only when the operator turns the Ollama backend on — never at tool launch — and stops it
        # again the moment they switch the AI off it (to Null/OpenAI/Cloud), so the local model is
        # never left consuming RAM/CPU once it is no longer the chosen backend. Both run off-thread
        # so the redirect never waits on the server coming up or shutting down.
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            if "ollama" in (backend, second_backend):
                threading.Thread(target=manager.ensure_running, daemon=True).start()
            else:
                threading.Thread(target=manager.shutdown, daemon=True).start()
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/settings/ai-off")
    def ai_off() -> RedirectResponse:
        """One click: turn the AI fully off — route back to the deterministic Null backend AND stop
        the local model. The operator asked for an explicit off switch once the AI is on; this also
        frees the RAM/CPU the local model was using without quitting the tool."""
        st = session()
        st.ai_config = AIConfig(classification=st.ai_config.classification, backend="null")
        st.backend_cache = None  # re-route to Null immediately
        st.second_cache = None
        st.polished.clear()  # drop any model-polished narratives so pages show the engine read
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            threading.Thread(
                target=manager.shutdown, daemon=True
            ).start()  # unload + stop, off-thread
        return RedirectResponse(url="/settings", status_code=303)

    @app.get("/help", response_class=HTMLResponse)
    def help_page() -> HTMLResponse:
        st = session()
        rows = "".join(
            f"<tr><td>{_e(d.name)}</td><td class=muted>{_e(reliability_dimension(d.metric_id))}</td>"
            f"<td>{_e(d.definition)}</td>"
            f"<td><code>{_e(d.formula)}</code></td><td class=muted>{_e(d.source)}</td></tr>"
            for d in METRIC_DICTIONARY.values()
        )
        body = (
            "<div class=panel><h2>Metric dictionary</h2>"
            "<p class=muted>Every metric the tool emits, with its formula and source. "
            "Each computed value also cites file + UniqueID + task name so you can verify it "
            "in the parent schedule. The <b>Dimension</b> column tags each metric with the NASA "
            "Schedule Management Handbook reliability dimension it most informs (Comprehensiveness "
            "/ Construction / Realism / Affordability) &mdash; an organizational lens, not a "
            "computed figure.</p>"
            f"<table><tr><th scope=col>Metric</th><th scope=col>Dimension</th>"
            f"<th scope=col>Definition</th><th scope=col>Formula</th>"
            f"<th scope=col>Source</th></tr>{rows}</table></div>"
        )
        return _page(st, "Metric Dictionary", body)

    @app.post("/target")
    def set_target(uid: str = Form(""), next_url: str = Form("/")) -> RedirectResponse:
        """Set (or clear, with a blank/invalid uid) the session-wide target activity.

        The target now also acts as the analysis ENDPOINT (every metric/visual is restricted to it
        and its drivers), so this funnels through :meth:`SessionState.set_target` to invalidate the
        scope/analysis caches — otherwise stale full-population results would survive the change."""
        st = session()
        st.set_target(_parse_uid(uid))
        # local redirect only: a path on this app, never a scheme/host ("//host" included)
        dest = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/language")
    def set_language(request: Request, lang: str = Form("en")) -> RedirectResponse:
        """Set the UI/AI display language (ADR-0099); returns to the page the user was on."""
        session().language = i18n.normalize(lang)
        # return to the referring page, reduced to a local path (host stripped, no open redirect)
        path = urlparse(request.headers.get("referer") or "/").path or "/"
        dest = path if path.startswith("/") and not path.startswith("//") else "/"
        return RedirectResponse(url=dest, status_code=303)

    @app.post("/api/translate")
    async def translate_api(request: Request) -> JSONResponse:
        """Translate a batch of strings for the client (catalog → session cache → AI model).

        Covers what the catalog does not (imported names, AI prose). Falls back to the source text
        when no model is reachable, so the page is never broken — only less fully translated."""
        st = session()
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"translations": {}})
        lang = i18n.normalize(body.get("lang"))
        texts = body.get("texts")
        if lang == i18n.DEFAULT_LANGUAGE or not isinstance(texts, list):
            return JSONResponse({"translations": {}})
        wanted = [str(t) for t in texts][:400]
        return JSONResponse({"translations": _translate_batch(wanted, lang, st)})

    @app.post("/session/wipe")
    def wipe() -> RedirectResponse:
        st = session()
        st.schedules.clear()
        st.analyses.clear()
        st.polished.clear()
        st.set_filter(())  # drop the session-wide group/filter and its scope cache
        st.flash = None
        st.target_uid = None
        # reset the SRA manual inputs back to the screening defaults
        st.sra_low = 0.9
        st.sra_ml = 1.0
        st.sra_high = 1.10
        st.sra_overrides.clear()
        st.sra_risks.clear()
        st.sra_risk_seq = 0
        # A wipe is a full reset: turn the AI back off and stop any local model it is running, so a
        # wiped session never leaves Ollama consuming RAM/CPU (operator report: Ollama survived a
        # Wipe → Quit). Re-enabling is one click in AI Settings.
        st.ai_config = AIConfig(classification=st.ai_config.classification, backend="null")
        st.backend_cache = None
        st.second_cache = None
        manager = getattr(app.state, "ollama", None)
        if manager is not None:
            threading.Thread(target=manager.shutdown, daemon=True).start()
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


def _stoplight_board(checks: tuple[AuditCheck, ...]) -> str:
    """The handbook's canonical at-a-glance metric stoplight (Figs 7-10..7-38): one chip per DCMA-14
    check, green PASS / red FAIL / grey N/A, with the value + threshold. Pure presentation over the
    existing ``AuditCheck.status`` — adds no new threshold or number."""
    if not checks:
        return ""
    chips = []
    for c in checks:
        cls = _status_class(c.status)
        thr = "" if c.threshold is None else f" (≤ {c.threshold:g}{_e(c.unit)})"
        title = f"{c.name}: {c.value:g}{c.unit} vs threshold{thr or ' n/a'} — {c.status}"
        chips.append(
            f'<span class="sl-chip sl-{cls}" title="{_e(title)}">'
            f"<span class=sl-name>{_e(c.name)}</span> "
            f"<b>{c.value:g}{_e(c.unit)}</b></span>"
        )
    legend = (
        '<div class=sl-legend><span class="sl-key sl-pass">pass</span>'
        '<span class="sl-key sl-fail">fail</span>'
        '<span class="sl-key sl-na">n/a</span></div>'
    )
    return f'<div class=stoplight-board role=list aria-label="DCMA-14 stoplight">{"".join(chips)}</div>{legend}'


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
            f"<tr><th scope=col>Finish vs baseline</th>"
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
        f"<tr><th scope=col>{label}</th><td>{_e(value)}</td></tr>"
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
<table><tr><th scope=col></th><th scope=col>0 days</th><th scope=col>&lt; 5 days</th><th scope=col>&lt; 10 days</th></tr>
<tr><th scope=col>Total float</th>{cell("float_total_0")}{cell("float_total_lt5")}{cell("float_total_lt10")}</tr>
<tr><th scope=col>Free float</th>{cell("float_free_0")}{cell("float_free_lt5")}{cell("float_free_lt10")}</tr>
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
        f"<tr><th scope=col>{_e(label)}</th><td>{fmt(mid)}</td></tr>"
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
secondary/tertiary tiers within your day-bands trace back from it — data on the
left, a scalable timeline on the right with the gold data-date line. Add/remove columns,
filter rows, and hide completed work.</p>
<details class=path-explainer><summary>Why an activity can show 0&#8209;day driving slack here but not on another view</summary>
<p class=muted>This trace is <b>relative to the target UniqueID</b> you choose. An activity has
<b>0 days of driving slack</b> when a slip in it would push <i>this target's</i> finish, so it sits
on the driving path <b>to that target</b>. The same activity may legitimately not appear on a view
scoped to a <b>different</b> target, on the project&#8209;finish critical path (the DCMA
&ldquo;Critical Path Test&rdquo;), or when completed work is hidden &mdash; driving slack to a
target and the project's critical path answer different questions. Turn on the <b>Drives &#8594;</b>
column to see each activity's logic successors inside this trace (e.g. UID 8022 &#8594; UID 152);
a <b>*</b> marks the successor that keeps the chain on the driving path.</p></details>
<div class=viz-controls id=pathControls>
<label>Schedule <select id=pathSchedule>{options}</select></label>
<label>Target UID <input id=pathTarget type=number min=1 value="{target_uid if target_uid is not None else ""}" placeholder="UID"></label>
<label>Secondary &le; <input id=pathSec type=number min=1 value=10 title="days of driving slack"> d</label>
<label>Tertiary &le; <input id=pathTer type=number min=1 value=20 title="days of driving slack"> d</label>
<button id=pathRun type=button>Trace</button>
<label><input id=pathHideDone type=checkbox> hide 100% complete</label>
<label>Tier <span id=pathTier class=tier-filter></span></label>
<label>Filter <input id=pathFilter type=text placeholder="name / UID contains"></label>
<label>Zoom <input id=pathZoom type=range min=2 max=40 value=8 title="pixels per day"></label>
</div>
<div id=pathFields class=muted></div>
<div class="export-bar" id=pathExport style="display:none"><a id=pathXlsx href="#">&#11015; Excel</a><a id=pathDocx href="#">&#11015; Word</a></div>
<div id=pathStatus class=muted></div>
<div id=pathView class=path-view></div></div>
<script src="/static/path.js"></script>"""


def _mission_body(target_uid: int | None) -> str:
    """Mission Control — every visual on one wall at small scale: expand any tile (⤢), reveal its
    underlying data table (▦ Data), and Play-all to step every animated chart in lockstep. Each
    tile hosts the SAME chart scripts/endpoints the dedicated pages use, so the session-wide
    Target UID and Groups & Filters scope every tile automatically."""
    target = target_uid if target_uid is not None else ""

    def tile(
        title: str, full_url: str, inner: str, *, controls: str = "", wide: bool = False
    ) -> str:
        cls = "tile panel" + (" tile-wide" if wide else "")
        return f"""<section class="{cls}">
<div class=tile-head><h3>{title}</h3>
<span class=tile-actions>\
<button type=button class=tile-expand aria-pressed=false title="Enlarge / shrink this tile">\
&#11122; Enlarge</button>\
<button type=button class=tile-data aria-pressed=false>&#9638; Data</button>
<a href="{full_url}" class=btn-link>Open &#8599;</a></span></div>
{controls}
<div class=chart-host>{inner}</div></section>"""

    def steps(prev: str, play: str, nxt: str) -> str:
        return (
            f"<div class=mini-steps><button type=button id={prev}>&#8249;</button>"
            f"<button type=button id={play}>&#9654;</button>"
            f"<button type=button id={nxt}>&#8250;</button></div>"
        )

    tiles = "".join(
        [
            tile(
                "S-Curve",
                "/scurve",
                "<div id=scurveLabel class=muted></div><div id=scurveChart></div>",
                controls=steps("prevScurve", "scurvePlay", "nextScurve"),
            ),
            tile(
                "Bow Wave / CEI",
                "/cei",
                "<div id=snapLabel class=muted></div><div id=ceiChart></div>",
                controls=steps("prevSnap", "autoPlay", "nextSnap"),
            ),
            tile(
                "Forecast Drift",
                "/forecast",
                "<div id=driftLabel class=muted></div><div id=driftChart></div>",
                controls=steps("prevDrift", "driftPlay", "nextDrift"),
            ),
            tile(
                "Quality Offenders",
                "/trend",
                "<div id=qualLabel class=muted></div>"
                "<div class=qual-drill-grid><div id=qualBars></div><div id=qualDrill></div></div>"
                "<label class=muted>Metric <select id=qualMetric></select></label>",
                controls=steps("qualPrev", "qualPlay", "qualNext"),
            ),
            tile("Finishes", "/curves", "<div id=finishesChart></div>"),
            tile("Data-date Finishes", "/curves", "<div id=dataDateChart></div>"),
            tile("Slippage", "/curves", "<div id=slippageChart></div>"),
            tile(
                "Critical-Path Evolution",
                "/evolution",
                f'<div id=evoLabel class=muted></div><div id=evoChart data-target="{target}"></div>',
                controls=steps("prevEvo", "evoPlay", "nextEvo"),
                wide=True,
            ),
            tile(
                "Quality Trend",
                "/trend",
                f'<div id=trendCharts data-target="{target}"></div>',
                wide=True,
            ),
        ]
    )
    return f"""
<div class=panel><h2>Mission Control &mdash; every visual on one wall</h2>
<p class=muted>Every visual on one wall, each the same size. <b>&#11122; Enlarge</b> any tile to the
full width (and back), reveal the underlying numbers with <b>&#9638; Data</b>, and use
<b>Play all</b> to step every animated chart &mdash; S-Curve, Bow Wave, Forecast Drift, Quality
Offenders, and Critical-Path Evolution &mdash; in lockstep. The session <b>Target UID</b> and
<b>Groups &amp; Filters</b> apply to every tile.</p>
<div class=viz-controls>
<button id=missionPlay type=button>&#9654; Play all</button>
<button id=missionStep type=button>&#9197; Step all</button>
</div></div>
<div id=missionGrid class=mosaic>
{tiles}
</div>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>
<script src="/static/cei.js"></script>
<script src="/static/drift.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/curves.js"></script>
<script src="/static/trend.js"></script>
<script src="/static/path_evolution.js"></script>
<script src="/static/mission.js"></script>"""


def _carnac_cards(summary: CarnacSummary) -> str:
    """The deck's Carnac KPI card row (PBIX page 13) over the latest version."""

    def d(value: dt.date | None) -> str:
        return value.isoformat() if value is not None else "—"

    def n(value: float | None, *, suffix: str = "") -> str:
        return f"{value:g}{suffix}" if value is not None else "—"

    return _stat_cards(
        [
            ("Earliest start", d(summary.earliest_start)),
            ("Latest finish (CPM)", d(summary.latest_finish)),
            ("Project duration (wd)", n(summary.project_duration_days)),
            ("Forecasted end (rate)", d(summary.forecasted_end)),
            ("Estimated end (ES, to-go)", d(summary.estimated_end_es)),
            ("Avg tasks / month", n(summary.avg_tasks_per_month)),
            ("Remaining duration (wd)", n(summary.remaining_duration_days)),
            ("SPI(t)", n(summary.spi_t)),
            ("Earned schedule (wd)", n(summary.earned_schedule_days)),
            ("Tasks to complete", str(summary.to_go_count)),
        ]
    )


#: lane color per forecast method (matches static/drift.js so the ruler and the animation
#: read consistently): logic = accent, throughput = ok, performance = bad.
_FORECAST_METHOD_COLORS = {
    "cpm": "var(--accent)",
    "rate": "var(--ok)",
    "earned_schedule": "var(--bad)",
}


def _forecast_ruler(fc: ForecastSet) -> str:
    """A static single-version SVG 'ruler' (M18 item 8): the data date, the baseline finish,
    and the three method forecasts on one timeline so the spread between them is visible at a
    glance. Inline SVG (no JS, no external fetch); the multi-version movement is the animated
    drift stepper below. Methods with missing inputs render '— (inputs missing)'."""
    lanes = [(f.name, f.method_id, f.finish) for f in fc.forecasts]
    method_dates = [d for _, _, d in lanes if d is not None]
    axis_dates = list(method_dates)
    if fc.as_of is not None:
        axis_dates.append(fc.as_of)
    if fc.planned_finish is not None:
        axis_dates.append(fc.planned_finish)
    if not axis_dates:
        return ""
    lo, hi = min(axis_dates), max(axis_dates)
    if lo == hi:
        lo, hi = lo - dt.timedelta(days=15), hi + dt.timedelta(days=15)
    span = (hi - lo).days or 1

    w, pad_l, pad_r, pad_t, row_h = 940, 150, 130, 46, 40
    height = pad_t + row_h * len(lanes) + 24
    plot_w = w - pad_l - pad_r
    bottom = pad_t + row_h * len(lanes)

    def x(d: dt.date) -> float:
        return pad_l + ((d - lo).days / span) * plot_w

    parts = [
        f'<svg viewBox="0 0 {w} {height}" width="100%" role="img" '
        f'aria-label="Forecast finish dates on a shared timeline">'
    ]
    if fc.as_of is not None:
        ax = x(fc.as_of)
        parts.append(
            f'<line x1="{ax:.1f}" y1="{pad_t - 12}" x2="{ax:.1f}" y2="{bottom}" '
            'style="stroke:var(--muted)" stroke-width="1.5" stroke-dasharray="2 3"/>'
            f'<text x="{ax:.1f}" y="{pad_t - 16}" text-anchor="middle" '
            f'style="fill:var(--muted)" font-size="11">data date {fc.as_of.isoformat()}</text>'
        )
    if fc.planned_finish is not None:
        px = x(fc.planned_finish)
        parts.append(
            f'<line x1="{px:.1f}" y1="{pad_t - 12}" x2="{px:.1f}" y2="{bottom}" '
            'style="stroke:var(--warn)" stroke-width="2" stroke-dasharray="5 4"/>'
            f'<text x="{px:.1f}" y="{pad_t - 30}" text-anchor="middle" '
            f'style="fill:var(--warn)" font-size="11">baseline {fc.planned_finish.isoformat()}</text>'
        )
    for i, (name, mid, d) in enumerate(lanes):
        cy = pad_t + row_h * i + row_h / 2
        color = _FORECAST_METHOD_COLORS.get(mid, "var(--ink)")
        parts.append(
            f'<line x1="{pad_l}" y1="{cy:.1f}" x2="{w - pad_r}" y2="{cy:.1f}" '
            'style="stroke:var(--line)" stroke-width="1"/>'
            f'<text x="{pad_l - 10}" y="{cy + 4:.1f}" text-anchor="end" '
            f'style="fill:var(--muted)" font-size="12">{_e(name)}</text>'
        )
        if d is not None:
            cx = x(d)
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" style="fill:{color}"/>'
                f'<text x="{cx:.1f}" y="{cy - 11:.1f}" text-anchor="middle" '
                f'style="fill:var(--ink)" font-size="11">{d.isoformat()}</text>'
            )
        else:
            parts.append(
                f'<text x="{pad_l + 10}" y="{cy + 4:.1f}" '
                'style="fill:var(--muted)" font-size="11">&#8212; (inputs missing)</text>'
            )
    parts.append("</svg>")
    legend_items = "".join(
        f"<span class=chart-legend-item><span class=chart-swatch "
        f'style="background:{_FORECAST_METHOD_COLORS.get(mid, "var(--ink)")}"></span>'
        f"{_e(name)}</span>"
        for name, mid, _ in lanes
    )
    legend_items += (
        '<span class=chart-legend-item style="color:var(--muted)">'
        "&mdash; gold dashed = baseline finish &middot; grey dotted = data date</span>"
    )
    legend = f"<div class=chart-legend>{legend_items}</div>"
    spread = ""
    if len(method_dates) >= 2:
        lo_m, hi_m = min(method_dates), max(method_dates)
        spread = (
            f"<p class=muted>The three methods span <b>{(hi_m - lo_m).days} days</b> "
            f"({lo_m.isoformat()} &rarr; {hi_m.isoformat()}). A wide fan means the plan, the "
            "throughput, and the earned-schedule performance disagree about the finish.</p>"
        )
    return f"<div id=forecastRuler>{''.join(parts)}{legend}</div>{spread}"


def _forecast_explainer(fc: ForecastSet) -> str:
    """Plain-English methodology for the three finish forecasts (M18 item 8): one card per
    method (what it measures, the formula in words + symbols, when it is available, and this
    version's value), plus the static ruler. Every value reuses the forecast set — nothing
    is recomputed."""
    by = {f.method_id: f for f in fc.forecasts}

    def fin(mid: str) -> str:
        f = by.get(mid)
        return f.finish.isoformat() if (f is not None and f.finish is not None) else "&#8212;"

    rate_txt = f"{fc.rate_per_month:g} / month" if fc.rate_per_month is not None else "n/a"
    spi_txt = f"{fc.spi_t:g}" if fc.spi_t is not None else "n/a"
    cards = [
        (
            "Schedule logic (CPM)",
            "The date the plan claims",
            "Runs the network's own forward and backward pass over every activity, its links, "
            "durations and calendar, and reports the finish the logic computes. It reflects "
            "what the schedule says &mdash; not how the work has actually been going.",
            "Method: the critical-path method (the longest logic-driven chain to the end).",
            "Always available once the network schedules &mdash; it never reads &#8212;.",
            fin("cpm"),
        ),
        (
            "Completion-rate extrapolation",
            "The throughput answer",
            "Counts the activities that have actually finished, divides by the months elapsed "
            "since the project started to get a completion pace, then asks how long the "
            "remaining activities take at that same pace.",
            "Formula: rate = completed &divide; elapsed&nbsp;months, then "
            "finish = data&nbsp;date + (to-go &divide; rate) months "
            f"(here {fc.completed_count} done at {rate_txt}, {fc.remaining_count} to go).",
            "Needs a status (data) date and at least one completed activity, else &#8212;.",
            fin("rate"),
        ),
        (
            "Earned-schedule IEAC(t)",
            "The performance answer",
            "Earned Schedule (ES) is how much planned <i>time</i> the completed work was worth "
            "on the baseline; AT is the actual time elapsed; their ratio SPI(t) = ES &divide; AT "
            "is the schedule efficiency. The estimate projects the remaining planned duration "
            "at that observed efficiency.",
            f"Formula: IEAC(t) = AT + (PD &minus; ES) &divide; SPI(t) (here SPI(t) = {spi_txt}).",
            "Needs baselines, completed work, and SPI(t) &gt; 0, else &#8212;.",
            fin("earned_schedule"),
        ),
    ]
    card_html = "".join(
        f"<div class=forecast-method><h3>{_e(title)}</h3>"
        f"<p class=method-tag>{_e(tag)}</p>"
        f"<p>{what}</p><p class=muted>{how}</p>"
        f"<p class=muted><b>Availability:</b> {needs}</p>"
        f"<p class=method-finish>This version: <b>{value}</b></p></div>"
        for title, tag, what, how, needs, value in cards
    )
    return f"""
<div class=panel><h2>How the three forecasts are computed</h2>
<p class=muted>Each method answers "when will it really end?" from a different angle &mdash;
the plan's own logic, the observed throughput, and the earned-schedule performance. When they
agree you can trust the date; when they fan apart, the disagreement is itself a finding. Every
figure here reuses the forecast above &mdash; nothing is recomputed.</p>
<div class=card-cols>{card_html}</div>
<h3>Forecast spread &mdash; latest version</h3>
<p class=muted>The data date, the baseline finish, and the three method forecasts on one
timeline. The multi-version movement is animated in the stepper below when two or more
versions are loaded.</p>
{_forecast_ruler(fc)}</div>"""


def _forecast_body(
    schedules: list[Schedule], cpms: list[CPMResult], sets: list[ForecastSet]
) -> str:
    """The three-method finish-forecast page (M15/ADR-0030): logic vs throughput vs
    performance, the deck's Carnac KPI cards (PBIX p13, ADR-0042), plus per-version drift."""
    latest_sch, latest = schedules[-1], sets[-1]
    carnac = compute_carnac_summary(latest_sch, cpms[-1], latest)
    by_id = latest_sch.tasks_by_id
    method_rows = "".join(
        f"<tr><th scope=col>{_e(f.name)}</th>"
        f"<td><b>{f.finish.isoformat() if f.finish else '&mdash;'}</b></td>"
        f"<td class=muted>{_e(f.basis)}</td></tr>"
        for f in latest.forecasts
    )
    inputs = "".join(
        f"<tr><th scope=col>{_e(label)}</th><td>{_e(value)}</td></tr>"
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
<div id=driftChart class=chart-host></div>
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>CPM</th><th scope=col>Completion rate</th>
<th scope=col>Earned schedule</th></tr>{drift_rows}</table></div>
<script src="/static/drift.js"></script>"""
    return f"""
<div class=panel><h2>Forecast cards &mdash; {_e(latest_sch.name)}</h2>
<p class=muted>The reference deck's <i>Carnac</i> forecast KPIs (PBIX page 13): the project
window, the three forecast end dates, the completion rate, remaining and project duration,
SPI(t), Earned Schedule, and the to-go activity count. A card with missing inputs shows
"&mdash;" &mdash; never a fabricated value. Every figure reuses the forecast below.</p>
{_carnac_cards(carnac)}</div>
<div class=panel><h2>Finish forecast &mdash; {_e(latest_sch.name)}</h2>
<p class=muted>Three independent answers to "when will it really end": the schedule's own
logic (CPM), the observed completion throughput, and earned-schedule performance
(IEAC(t) = AT + (PD &minus; ES) / SPI(t)). Methods that disagree are themselves a finding.
A method whose inputs are missing shows "&mdash;" &mdash; never a fabricated date.</p>
<table><tr><th scope=col>Method</th><th scope=col>Forecast finish</th><th scope=col>Basis</th></tr>{method_rows}</table>
<h3>Inputs</h3><table>{inputs}</table>
<p class=cite>Finish-controlling: {_e(cite)}</p></div>
{_forecast_explainer(latest)}{drift}"""


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


def _curves_body(curves: MonthCurves) -> str:
    """The Finish & Slippage page (PBIX pages 6, 7, 12): three monthly-curve charts.

    Finishes (actual vs baseline, latest version), DATA Date Finishes (per-version
    actual-finish curves overlaid — the bow wave's line sibling), and Slippage (the
    per-version start and finish curves). All client-side SVG over /api/curves."""
    n_versions = len(curves.versions)
    latest = curves.versions[-1].label if curves.versions else ""
    multi = (
        ""
        if n_versions >= 2
        else "<p class=muted>Load more than one version (monthly snapshots, by data date) to "
        "see the per-version curve overlays — with a single version the curves show that "
        "version alone.</p>"
    )
    return f"""
<div class=viz-controls><label><input type=checkbox id=curvesHideDone> hide 100% complete</label>
<span class=muted>&mdash; show only the remaining / forecast work on every curve below.</span>
<label style="margin-left:1em">Time scale <select id=curvesGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label></div>
<div class=panel><h2>Finishes &mdash; actual vs baseline by month</h2>
<p class=muted>For the latest version (<b>{_e(latest)}</b>): activities counted by the month
they were <b>baselined</b> to finish (gold) against the month they <b>actually</b> finished
or are now scheduled to (blue). Where the blue curve sits to the right of the gold is slipped
finish work, read month by month.</p>
<div id=finishesChart class=chart-host></div></div>
<div class=panel><h2>DATA Date Finishes &mdash; actual-finish curve per version</h2>
<p class=muted>Each loaded version (oldest first by data date) plots its monthly actual/scheduled
finish curve on one shared month axis. As later versions push their curves to the right, you
see the bow wave of slipped finishes as a line family.</p>{multi}
<div id=dataDateChart class=chart-host></div></div>
<div class=panel><h2>Slippage &mdash; start &amp; finish curves per version</h2>
<p class=muted>Per version: activities counted by their <b>start</b> month (solid) and their
<b>finish</b> month (dashed). Start- and finish-curve drift across versions is the slippage
signature &mdash; the whole profile sliding right.</p>
<div id=slippageChart class=chart-host></div></div>
<script src="/static/timeaxis.js"></script>
<script src="/static/curves.js"></script>"""


def _curves_data(curves: MonthCurves) -> dict[str, object]:
    """JSON for the finish/slippage curves: shared month axis + per-version count series."""
    return {
        "months": list(curves.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_date": v.status_date,
                "status_index": v.status_index,
                "baseline_finishes": list(v.baseline_finishes),
                "actual_finishes": list(v.actual_finishes),
                "baseline_starts": list(v.baseline_starts),
                "actual_starts": list(v.actual_starts),
            }
            for v in curves.versions
        ],
    }


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _health_checks_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Extra structural health checks (handbook Fig. 6-9) as a stoplight list — green when clear,
    else the count + the first offending UIDs, with a plain-English reason for each."""
    checks = compute_health_checks(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            more = f" +{c.count - 8} more" if c.count > 8 else ""
            offs = f"<p class=cite>{_e(shown)}{_e(more)}</p>"
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Structural health checks</h2>"
        "<p class=muted>Deterministic schedule-construction checks from the NASA Schedule "
        "Management Handbook (Fig. 6-9), beyond DCMA-14 &mdash; green = clear, otherwise the count "
        "and the first offending activities (the activity grid above is the full record).</p>"
        + "".join(cards)
        + "</div>"
    )


def _schedule_variance_panel(sch: Schedule) -> str:
    """Schedule variance in TIME (handbook §7.3.3.1): project SVt = ES - AT (working days), plus the
    per-activity finish slip (actual - baseline). Favorable when ahead of plan (SVt >= 0)."""
    sv = compute_schedule_variance(sch, non_summary(sch))
    if sv.svt_days is None and sv.completed == 0:
        return (
            "<div class=panel><h2>Schedule variance (time)</h2>"
            "<p class=muted>Not computable yet &mdash; SVt needs a status (data) date, at least one "
            "completed activity, and baseline finishes; per-activity variance needs both an actual "
            "and a baseline finish. This schedule does not yet carry them.</p></div>"
        )
    if sv.svt_days is None:
        svt_val = "n/a"
    else:
        favorable = sv.svt_days >= 0
        sign = "+" if sv.svt_days > 0 else ""
        # SVt > 0 = ES ahead of AT = ahead of plan (favorable); < 0 = behind (unfavorable)
        svt_val = f"{sign}{sv.svt_days:g} wd ({'ahead' if favorable else 'behind'})"
    cards = _stat_cards(
        [
            ("Schedule variance (SVt = ES - AT)", svt_val),
            ("Earned Schedule (ES)", "n/a" if sv.es_days is None else f"{sv.es_days:g} wd"),
            ("Actual Time (AT)", "n/a" if sv.at_days is None else f"{sv.at_days:g} wd"),
            ("Completed activities measured", str(sv.completed)),
            (
                "Mean activity finish variance",
                "n/a"
                if sv.mean_activity_variance_days is None
                else f"{sv.mean_activity_variance_days:+g} wd",
            ),
        ]
    )
    table = ""
    if sv.worst:
        names = sch.tasks_by_id
        rows = "".join(
            f"<tr><td>{v.unique_id}</td>"
            f"<td>{_e(names[v.unique_id].name) if v.unique_id in names else ''}</td>"
            f'<td class="rk-score {"rk-high" if v.variance_days > 0 else "rk-min"}">'
            f"{v.variance_days:+g}</td></tr>"
            for v in sv.worst
        )
        table = (
            "<h3>Largest finish variances (actual &minus; baseline)</h3>"
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            "<th scope=col>Variance (wd)</th></tr>"
            f"{rows}</table>"
        )
    return (
        "<div class=panel><h2>Schedule variance (time)</h2>"
        "<p class=muted>The NASA Schedule Management Handbook (&sect;7.3.3.1) time view of progress. "
        "<b>SVt = ES &minus; AT</b> (Earned Schedule minus Actual Time): positive is "
        "<b>ahead</b> of plan (favorable), negative is <b>behind</b> (unfavorable) &mdash; the "
        "count-based Earned-Schedule companion to SPI(t). Per-activity finish variance is each "
        "completed activity's actual finish minus its baseline finish, in working days (positive = "
        "late).</p>"
        f"{cards}{table}</div>"
    )


#: float-erosion stoplight → the shared 5-level risk badge classes (green / amber / red)
_EROSION_BADGE = {"green": "rk-min", "yellow": "rk-mod", "red": "rk-extreme"}


def _float_erosion_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Float erosion by WBS (handbook Figs 7-34/7-35): per-top-level-WBS minimum / average total
    float, critical count, and a stoplight on the group's minimum float — where buffer is thinning."""
    fe = compute_float_erosion(sch, cpm)
    if not fe.groups:
        return (
            "<div class=panel><h2>Float erosion by WBS</h2>"
            "<p class=muted>No schedulable activities to group.</p></div>"
        )
    thr = f"{fe.low_float_threshold_days:g}"
    rows = []
    for g in fe.groups:
        badge = _EROSION_BADGE.get(g.status, "rk-min")
        rows.append(
            f"<tr><td>{_e(g.wbs)}</td><td>{g.count}</td>"
            f'<td class="rk-score {badge}">{g.min_float_days:g}</td>'
            f"<td>{g.avg_float_days:g}</td><td>{g.critical_count}</td></tr>"
        )
    proj_min = "n/a" if fe.min_float_days is None else f"{fe.min_float_days:g} wd"
    cards = _stat_cards(
        [
            ("Lowest total float (any WBS)", proj_min),
            ("WBS groups", str(len(fe.groups))),
            ("Eroded groups (min float < 0)", str(sum(1 for g in fe.groups if g.status == "red"))),
        ]
    )
    return (
        "<div class=panel><h2>Float erosion by WBS</h2>"
        "<p class=muted>Total float grouped by top-level WBS (NASA Schedule Management Handbook) "
        "&mdash; where buffer is thinning before the project-level margin is hit. The stoplight is on "
        f"each group's <b>minimum</b> total float: <b>red</b> below 0 (eroded / behind a constraint), "
        f"<b>amber</b> 0&ndash;{thr} working days (thin buffer), <b>green</b> above {thr}. Float is "
        "read progress-aware (the source tool's stored Total Slack when present).</p>"
        f"{cards}"
        "<table><tr><th scope=col>WBS</th><th scope=col>Activities</th>"
        "<th scope=col>Min float (wd)</th><th scope=col>Avg float (wd)</th>"
        "<th scope=col>Critical</th></tr>"
        f"{''.join(rows)}</table></div>"
    )


def _constraint_checks_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Constraint-health checks (handbook Fig. 6-9): unsatisfied hard date constraints and breached
    deadlines, as a stoplight list — green when clear, else the count + the first offending UIDs."""
    checks = compute_constraint_health(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            more = f" +{c.count - 8} more" if c.count > 8 else ""
            offs = f"<p class=cite>{_e(shown)}{_e(more)}</p>"
        pop = f"<span class=muted> of {c.population}</span>" if c.population else ""
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Constraint health</h2>"
        "<p class=muted>How imposed dates fare against the network logic (NASA Schedule Management "
        "Handbook, Fig. 6-9): a <b>hard constraint</b> the CPM date runs past cannot be honored, and "
        "a <b>deadline</b> the logic finish overruns is artificial negative float. Green = clear, "
        "otherwise the count and the first offending activities.</p>" + "".join(cards) + "</div>"
    )


def _vertical_integration_panel(sch: Schedule) -> str:
    """Vertical-integration check (handbook Fig. 6-9): summaries whose stored span does not envelope
    the work beneath them — a stoplight finding card, green when clear else the offending summaries."""
    vi = compute_vertical_integration(sch)
    ok = vi.count == 0
    badge_cls = "rk-min" if ok else "rk-high"
    badge = "✓ clear" if ok else str(vi.count)
    offs = ""
    if vi.offenders:
        shown = ", ".join(f"UID {u}" for u in vi.offenders[:8])
        more = f" +{vi.count - 8} more" if vi.count > 8 else ""
        offs = f"<p class=cite>{_e(shown)}{_e(more)}</p>"
    pop = f"<span class=muted> of {vi.population} summary group(s)</span>" if vi.population else ""
    note = (
        ""
        if vi.population
        else "<p class=muted>No summaries with a WBS code, stored dates, and dated descendants "
        "to evaluate.</p>"
    )
    return (
        "<div class=panel><h2>Vertical integration</h2>"
        "<p class=muted>Whether each summary (rollup) bar envelopes the detail activities beneath it "
        "(by WBS nesting), using the schedule's stored dates &mdash; the handbook's vertical-"
        "traceability check. A parent that starts after its earliest child or finishes before its "
        "latest is an inconsistent rollup.</p>"
        f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
        f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
        f"<b>Inconsistent vertical integration</b>{pop}</div>"
        f"<p>{_e(vi.description)}</p>{offs}</div>{note}</div>"
    )


def _logic_checks_panel(sch: Schedule) -> str:
    """Logic-integrity checks (out-of-sequence progress, redundant logic) as a stoplight list —
    green when clear, else the count + the first offending links, with a plain-English reason."""
    checks = compute_logic_integrity(sch).checks
    cards = []
    for c in checks:
        if not c.evaluated:
            cards.append(
                '<div class="finding sev-INFO">'
                '<div class=finding-head><span class="rk-score rk-min">n/a</span> '
                f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p></div>"
            )
            continue
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(c.offenders[:8])
            more = f" +{c.count - 8} more" if c.count > 8 else ""
            offs = f"<p class=cite>{_e(shown)}{_e(more)}</p>"
        pop = f"<span class=muted> of {c.population} link(s)</span>" if c.population else ""
        cards.append(
            f'<div class="finding sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    return (
        "<div class=panel><h2>Logic integrity</h2>"
        "<p class=muted>Forensic logic-construction checks from the NASA Schedule Management "
        "Handbook (Fig. 6-9), beyond DCMA-14 &mdash; <b>out-of-sequence</b> progress (work recorded "
        "in an order the logic forbids) and <b>redundant logic</b> (a direct link a longer path "
        "already implies). Green = clear, otherwise the count and the first offending links "
        "(written predecessor&rarr;successor by UniqueID).</p>" + "".join(cards) + "</div>"
    )


def _margin_panel(sch: Schedule, cpm: CPMResult) -> str:
    """Schedule-margin panel: total vs effective buffer, criticality, and the margin activities.

    Margin tasks are identified by the operator convention (name contains "margin"). "Effective
    margin" is how far the finish would pull in if all margin were removed — the buffer actually
    protecting the finish; margin sitting on a path with slack protects nothing."""
    m = compute_margin(sch, cpm)
    if m.count == 0:
        return (
            "<div class=panel><h2>Schedule margin</h2>"
            "<p class=muted>No schedule-margin tasks found (none named &lsquo;margin&rsquo;). "
            "Margin activities are identified by the operator convention: a non-summary activity "
            "whose name contains the word &ldquo;margin&rdquo; (case-insensitive).</p></div>"
        )
    crit_note = (
        f" &middot; {m.on_critical_count} on the critical path"
        if m.on_critical_count
        else " &middot; none on the critical path"
    )
    cards = _stat_cards(
        [
            ("Total margin", f"{m.total_margin_days:g} wd"),
            ("Effective margin", f"{m.effective_margin_days:g} wd"),
            ("Margin activities", f"{m.count}{crit_note}"),
        ]
    )
    rows = "".join(
        f"<tr><td>{t.unique_id}</td><td>{_e(t.name)}</td><td>{t.duration_days:g}</td>"
        f'<td class="rk-score {"rk-high" if t.on_critical else "rk-min"}">'
        f"{'Yes' if t.on_critical else 'No'}</td></tr>"
        for t in m.tasks
    )
    return (
        "<div class=panel><h2>Schedule margin</h2>"
        "<p class=muted>Explicit buffer activities that protect the project finish "
        "(NASA Schedule Management Handbook). <b>Total margin</b> is the sum of the margin "
        "activities' durations; <b>effective margin</b> is how far the finish would pull in if "
        "all margin were removed &mdash; the buffer actually protecting the finish (margin sitting "
        "on a path with slack protects nothing and counts toward total but not effective).</p>"
        f"{cards}"
        "<table><tr><th scope=col>UID</th><th scope=col>Name</th>"
        "<th scope=col>Days</th><th scope=col>On critical path?</th></tr>"
        f"{rows}</table>"
        "<p class=muted>Margin tasks are identified by the operator convention: a non-summary "
        "activity whose name contains the word &ldquo;margin&rdquo; (case-insensitive).</p></div>"
    )


def _scatter_panel(key: str) -> str:
    """An activity scatter (total float x duration) on the analysis page — a new visual type from
    the handbook/decks. Pure presentation over the activity rows the grid already serves."""
    return (
        "<div class=panel><h2>Activity scatter &mdash; float vs duration</h2>"
        "<p class=muted>One dot per activity: <b>total float</b> (x) against <b>duration</b> (y), "
        "red = critical, diamonds = milestones. Long-duration, low-float activities sit at the "
        "lower-left &mdash; the schedule's pressure points a count metric never reveals. The full "
        "activity grid above is the accessible data table.</p>"
        f'<div class=chart-host id=scatterChart data-name="{_e(key)}"></div></div>'
        '<script src="/static/scatter.js"></script>'
    )


def _float_histogram_panel(key: str) -> str:
    """An activity total-float distribution histogram on the analysis page (handbook §6.3.2.5.2.2).
    Pure presentation over the activity rows the grid already serves (binned client-side)."""
    return (
        "<div class=panel><h2>Total-float distribution</h2>"
        "<p class=muted>Activities binned by <b>total float</b> (working days), in DCMA-aligned "
        "bands. Mass at <b>0 / &lt; 0</b> is the critical-and-behind core; a spike in the "
        "<b>&gt; 44 d</b> band is float padding or missing successor logic (DCMA-06). The full "
        "activity grid above is the accessible data table.</p>"
        f'<div class=chart-host id=floatHist data-name="{_e(key)}"></div></div>'
        '<script src="/static/histogram.js"></script>'
    )


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
<tr><th scope=col>Calendar</th><td>{_e(cal.name)}</td></tr>
<tr><th scope=col>Working day</th><td>{_e(hours_text)}</td></tr>
<tr><th scope=col>Work week</th><td>{_e(days)}</td></tr>
<tr><th scope=col>Holidays</th><td>{_e(holidays)}</td></tr>
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
        f"<table class=card-table><tr><th scope=col>{_e(headers[0])}</th><th scope=col>Count</th>"
        f"<th scope=col>{_e(headers[1])}</th></tr>{body}</table>"
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


def _num(value: float | None, *, suffix: str = "") -> str:
    """Render an optional number for a table cell — em-dash when absent (never a fake 0)."""
    return f"{value:g}{suffix}" if value is not None else "&mdash;"


def _wbs_body(key: str, groups: tuple[WBSGroup, ...]) -> str:
    """The deck's *Completion Metrics* (PBIX 8) + *SPI and Earned Schedule* (PBIX 9) pages.

    Two WBS pivots over one version: a completion-by-WBS table (counts, %, ahead/on/behind,
    duration ratio) and the SPI(t)/Earned-Schedule-by-WBS combo chart + table. Grouped by
    the top-level WBS segment; every figure verifiable on the full report."""
    if not groups:
        return (
            "<div class=panel><h2>WBS breakdown</h2><p class=muted>This schedule has no "
            "schedulable activities to break down by WBS.</p></div>"
        )
    completion_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{g.total}</td><td>{g.completed}</td>"
        f"<td>{g.not_completed}</td><td>{g.percent_complete:g}%</td>"
        f"<td>{g.completed_ahead}</td><td>{g.completed_on_schedule}</td><td>{g.completed_behind}</td>"
        f"<td>{_num(g.avg_days_ahead)}</td><td>{_num(g.avg_days_late)}</td>"
        f"<td>{_num(g.avg_completion_variance)}</td>"
        f"<td>{g.longer_than_planned}</td><td>{g.shorter_than_planned}</td>"
        f"<td>{_num(g.duration_ratio_min)}</td><td>{_num(g.duration_ratio_avg)}</td>"
        f"<td>{_num(g.duration_ratio_max)}</td></tr>"
        for g in groups
    )
    es_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{_num(g.spi_t)}</td>"
        f"<td>{_num(g.earned_schedule_days)}</td><td>{_num(g.actual_time_days)}</td>"
        f"<td>{g.completed}/{g.total}</td></tr>"
        for g in groups
    )
    return f"""
<div class=panel><h2>Completion metrics by WBS &mdash; {len(groups)} groups</h2>
<p class=muted>The reference deck's <i>Completion Metrics</i> pivot (PBIX page 8), grouped by
the top-level WBS segment: counts and completion, the ahead / on-schedule / behind split with
average calendar days, and the actual-vs-baseline duration ratio. Every figure is verifiable
on the <a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
<div style="overflow-x:auto"><table class=wbs-table>
<tr><th scope=col>WBS</th><th scope=col>Total</th><th scope=col>Done</th><th scope=col>To go</th><th scope=col>% comp</th>
<th scope=col>Ahead</th><th scope=col>On sched</th><th scope=col>Behind</th>
<th scope=col>Avg ahead</th><th scope=col>Avg late</th><th scope=col>Avg var</th>
<th scope=col>Longer</th><th scope=col>Shorter</th><th scope=col>Dur min</th><th scope=col>Dur avg</th><th scope=col>Dur max</th></tr>
{completion_rows}</table></div></div>
<div class=panel><h2>SPI(t) &amp; Earned Schedule by WBS</h2>
<p class=muted>The deck's <i>SPI and Earned Schedule</i> pivot + combo (PBIX page 9). Per WBS
group: the count-based <b>SPI(t)</b> (Earned Schedule &divide; Actual Time; &lt; 1 = behind),
the <b>Earned Schedule</b> and <b>Actual Time</b> in working days. A group with no completions
or no baseline finishes reads &mdash; (never a fabricated value).</p>
<div id=wbsChart class=chart-host></div>
<table class=wbs-table><tr><th scope=col>WBS</th><th scope=col>SPI(t)</th><th scope=col>Earned schedule (wd)</th>
<th scope=col>Actual time (wd)</th><th scope=col>Completed</th></tr>{es_rows}</table></div>
<script src="/static/wbs.js"></script>"""


def _wbs_data(groups: tuple[WBSGroup, ...]) -> dict[str, object]:
    """JSON for the SPI/Earned-Schedule combo chart: per-WBS SPI(t) + ES/AT days."""
    return {
        "groups": [
            {
                "wbs": g.wbs,
                "total": g.total,
                "completed": g.completed,
                "percent_complete": g.percent_complete,
                "spi_t": g.spi_t,
                "earned_schedule_days": g.earned_schedule_days,
                "actual_time_days": g.actual_time_days,
            }
            for g in groups
        ],
    }


def _dcma_label(metric_id: str) -> str:
    """The spaced display label the operator asked for: ``DCMA01`` -> ``DCMA 01``;
    ``DCMA04_FS`` -> ``DCMA 04 FS``. Non-DCMA ids pass through unchanged."""
    if not metric_id.startswith("DCMA"):
        return metric_id
    base, _, suffix = metric_id[4:].partition("_")
    return f"DCMA {base}" + (f" {suffix.replace('_', ' ')}" if suffix else "")


def _dcma_measure(check: AuditCheck) -> str:
    """A concise measured value to sit beside the stoplight (replacing the old bar): a percentage
    with its count for population checks, the index for CPLI/BEI, a raw count otherwise."""
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"{check.value:.2f}"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return f"{pct:.1f}%  ({check.count} of {check.population})"
    if check.count:
        unit = f" {check.unit}" if check.unit and check.unit != "count" else ""
        return f"{check.count}{unit}"
    return str(check.status).title()  # e.g. the critical-path test: Pass / Fail


def _dcma_card(check: AuditCheck) -> dict[str, object]:
    """One DCMA check as Dashboard-overview JSON: the spaced label + human name, a simple measured
    value, the PASS/FAIL/NA status (the stoplight), and the help text for the hover tooltip — what
    the metric is, why it matters, the pass/fail threshold, and a pass + a fail example (operator
    request). ``status`` and ``count`` are retained for back-compatibility with existing readers."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    return {
        "label": _dcma_label(check.metric_id),
        "name": doc.name if doc else check.name,
        "status": str(check.status),
        "count": check.count,
        "value": check.value,
        "measure": _dcma_measure(check),
        "definition": doc.definition if doc else "",
        "why": doc.importance if doc else "",
        "threshold": doc.threshold if doc else "",
        "example_ok": doc.example_ok if doc else "",
        "example_fail": doc.example_fail if doc else "",
    }


def _dcma_definition_cell(metric_id: str) -> str:
    """The 'what it measures (how)' cell for a DCMA row, from the in-tool metric dictionary —
    plain-language definition + the formula/threshold, so each score is explained in place."""
    doc = METRIC_DICTIONARY.get(metric_id)
    if doc is None:
        return "<td></td>"
    return (
        f"<td class=dcma-def>{_e(doc.definition)} "
        f"<span class=muted>How: {_e(doc.formula)}</span></td>"
    )


def _dcma_metric_cell(check: AuditCheck) -> str:
    """The 'Check' cell: the metric name plus a hover/focus tooltip that explains the metric,
    its pass/fail criteria, why it matters, and what a failing value indicates (operator request).

    The tooltip is keyboard-operable (the trigger is focusable and labelled) and also carries a
    plain-text ``title=`` so the same detail is available with no CSS/JS (air-gap, a11y)."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    if doc is None:
        return f"<td>{_e(check.name)}</td>"
    display = f"{_dcma_label(check.metric_id)} — {doc.name}"
    tip_id = f"dcma-tip-{_e(check.metric_id)}"
    rich = [f"<b>{_e(display)}</b>", f"<p>{_e(doc.definition)}</p>"]
    title = f"{doc.definition}"
    threshold = doc.threshold or f"Pass criteria: {doc.formula}"
    rich.append(f"<p><b>Threshold:</b> {_e(threshold)}</p>")
    title += f" Threshold: {threshold}."
    if doc.importance:
        rich.append(f"<p><b>Why it matters:</b> {_e(doc.importance)}</p>")
        title += f" Why it matters: {doc.importance}"
    if doc.example_ok:
        rich.append(f"<p><b>Pass example:</b> {_e(doc.example_ok)}</p>")
        title += f" Pass example: {doc.example_ok}"
    if doc.example_fail:
        rich.append(f"<p><b>Fail example:</b> {_e(doc.example_fail)}</p>")
        title += f" Fail example: {doc.example_fail}"
    if doc.indicates:
        rich.append(f"<p><b>Indicates:</b> {_e(doc.indicates)}</p>")
        title += f" Indicates: {doc.indicates}"
    return (
        f"<td class=dcma-cell>"
        f'<span class=dcma-metric tabindex=0 role=button aria-describedby="{tip_id}" '
        f'title="{_e(title)}">{_e(display)} '
        f"<span class=dcma-info aria-hidden=true>&#9432;</span></span>"
        f'<div class=dcma-tip id="{tip_id}" role=tooltip>{"".join(rich)}</div></td>'
    )


def _dcma_count_cells(check: AuditCheck) -> str:
    """The Count + '% of tasks' cells, matching how Acumen Fuse shows each metric — the raw
    count over its population plus the percentage, instead of only a pass/fail colour.

    Count-based checks show ``n of population`` and the metric's percentage; the CPLI / BEI
    index checks show the index value (no count); the pass/fail critical-path test shows neither."""
    dash = "<span class=muted>&mdash;</span>"
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"<td class=num>{dash}</td><td class=num>{round(check.value, 2)}</td>"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return (
            f"<td class=num>{check.count} <span class=muted>of {check.population}</span></td>"
            f"<td class=num>{pct:.1f}%</td>"
        )
    return f"<td class=num>{check.count}</td><td class=num>{dash}</td>"


def _analysis_body(
    key: str,
    sch: Schedule,
    analysis: _Analysis,
    target: int | None = None,
    narrative: Narrative | None = None,
) -> str:
    audit = analysis.audit
    audit_rows = "".join(
        f'<tr>{_dcma_metric_cell(c)}<td class="{_status_class(c.status)}">{_e(c.status)}</td>'
        f"{_dcma_count_cells(c)}"
        f"{_dcma_definition_cell(c.metric_id)}"
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
<div class="charts chart-host" id=charts></div>
<div class=viz-controls>Driving path to target UID:
<input id=targetUid type=number min=1 placeholder="UID" value="{target if target is not None else ""}">
secondary&le;<input id=secMax type=number value=10>d
tertiary&le;<input id=terMax type=number value=20>d
<button id=ganttBtn type=button>Trace</button>
<label><input id=showDone type=checkbox checked> show completed tasks</label>
<label>Tier <span id=ganttTier class=tier-filter></span></label>
<label>Scale <input id=vizZoom type=range min=2 max=40 value=8 title="pixels per day — drag to zoom both timelines"></label>
<button id=fitBtn type=button title="Zoom out so the entire project fits on screen">Fit project</button></div>
<div id=gantt></div>
<h3>Activities &amp; Gantt <span class=muted>(add/remove columns; the right-hand timeline is
scalable — drag <b>Scale</b> to zoom (pixels/day) and scroll horizontally; red = critical,
diamonds = milestones, thin = summaries, amber line = data date; click a row to drill into its
metadata)</span></h3>
<div id=fieldToggles></div><div id=grid></div><div id=drill class=drill></div>
</div></div>
<script src="/static/app.js"></script>"""
    return f"""{viz}
{_scatter_panel(key)}
{_float_histogram_panel(key)}
{_calendar_panel(sch)}
{_float_bands_panel(analysis)}
{_completion_panel(analysis)}
{_health_checks_panel(sch, analysis.cpm)}
{_logic_checks_panel(sch)}
{_constraint_checks_panel(sch, analysis.cpm)}
{_vertical_integration_panel(sch)}
{_schedule_variance_panel(sch)}
{_float_erosion_panel(sch, analysis.cpm)}
{_margin_panel(sch, analysis.cpm)}
<div class=panel><h2>{_e(sch.name)} &mdash; DCMA-14 audit</h2>
<p class=muted>{audit.passed} passed &middot; {audit.failed} failed &middot; {audit.not_applicable} N/A.
Each row shows the <b>count</b> and the <b>percentage</b> of its population,
not just a pass/fail colour. <b>Hover or focus a check name</b> for its definition, pass/fail
criteria, why it matters, and what it indicates; full formulas + citations are in the
<a href="/help">Metric Dictionary</a>.</p>
{_stoplight_board(audit.checks)}
<table><tr><th scope=col>Check</th><th scope=col>Status</th><th scope=col>Count</th><th scope=col>% of tasks</th>
<th scope=col>What it measures (how)</th>
<th scope=col>Suggested improvement</th></tr>{audit_rows}</table></div>
<div class=panel><h2>Risks, opportunities &amp; concerns</h2>
<table><tr><th scope=col>Severity</th><th scope=col>Type</th><th scope=col>Finding</th><th scope=col>Course of action</th><th scope=col>Citations</th></tr>
{find_rows or "<tr><td colspan=5 class=muted>No findings — schedule is well-formed.</td></tr>"}</table></div>
<div class=panel><h2>AI narrative (local, cited)</h2>
<ul class=story data-ai-endpoint="/api/ai/narrative?key={_e(quote(key))}">{story}</ul></div>
<script src="/static/ai_polish.js"></script>"""


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
            head = "".join(f"<th scope=col>{_e(str(h))}</th>" for h in section.table.headers)
            rows = "".join(
                "<tr>"
                + "".join(f"<td>{_e('' if c is None else str(c))}</td>" for c in row)
                + "</tr>"
                for row in section.table.rows
            )
            parts.append(f"<table><tr>{head}</tr>{rows}</table>")
        parts.append("</div>")
    return "".join(parts)


_IMPACT_LABELS = {5: "Severe", 4: "Major", 3: "Moderate", 2: "Minor", 1: "Negligible"}
_LIKELIHOOD_LABELS = {5: "Certain", 4: "Likely", 3: "Possible", 2: "Unlikely", 1: "Rare"}


def _risk_band(score: int) -> tuple[str, str]:
    """(css class, label) for a 1..25 risk score — the conventional 5x5 risk heat bands."""
    if score >= 20:
        return "rk-extreme", "Extreme"
    if score >= 12:
        return "rk-high", "High"
    if score >= 6:
        return "rk-mod", "Moderate"
    if score >= 3:
        return "rk-low", "Low"
    return "rk-min", "Minimal"


def _wd(value: float) -> str:
    """A working-days figure for a quantified field (callers guard against None)."""
    return f"{value:.1f} wd"


def _finding_quant(f: Finding) -> str:
    """The quantified read for one finding: likelihood/impact/score, plus float, driving float to
    the target (when set), and the working-day schedule exposure if it is realised."""
    bits = [
        f"Likelihood: <b>{_LIKELIHOOD_LABELS[f.likelihood_score]}</b>",
        f"Impact: <b>{_IMPACT_LABELS[f.impact_score]}</b>",
        f"Risk score: <b>{f.risk_score}</b>/25",
    ]
    if f.float_days is not None:
        bits.append(f"Total float: <b>{_e(_wd(f.float_days))}</b>")
    if f.driving_float_days is not None:
        bits.append(f"Driving float to target: <b>{_e(_wd(f.driving_float_days))}</b>")
    if f.impact_days is not None and f.impact_days > 0:
        bits.append(f"Schedule exposure: <b>{_e(_wd(f.impact_days))}</b>")
    return '<p class="finding-quant">' + " &middot; ".join(bits) + "</p>"


def _finding_card(f: Finding) -> str:
    """One risk/issue/opportunity card: severity + risk-score badge, quantified read, detail,
    recommended action, citations."""
    cites = "; ".join(_e(str(c)) for c in f.citations[:3])
    more = f" +{len(f.citations) - 3} more" if len(f.citations) > 3 else ""
    action = (
        f"<p class=finding-action><b>Recommended action:</b> {_e(f.course_of_action)}</p>"
        if f.course_of_action
        else ""
    )
    band, _label = _risk_band(f.risk_score)
    return f"""<div class="finding sev-{_e(f.severity)}" data-score="{f.risk_score}"\
 data-impact="{f.impact_score}" data-likelihood="{f.likelihood_score}">
<div class=finding-head><span class="sev-badge sev-{_e(f.severity)}">{_e(f.severity)}</span>
<span class="rk-score {band}" title="Risk score = likelihood x impact">{f.risk_score}</span>
<b>{_e(f.title)}</b> <span class=muted>[{_e(f.metric_id)}]</span></div>
<p>{_e(f.detail)}</p>{_finding_quant(f)}{action}
<p class=cite>Cited: {cites}{_e(more)}</p></div>"""


def _risk_matrix(items: list[Finding]) -> str:
    """A 5x5 Likelihood (columns) by Impact (rows) heat-map of the risks + issues, each placed by
    its quantified scores; cells carry the conventional risk colour and the count landing there."""
    if not items:
        return ""
    counts: dict[tuple[int, int], int] = {}
    for f in items:
        counts[(f.impact_score, f.likelihood_score)] = (
            counts.get((f.impact_score, f.likelihood_score), 0) + 1
        )
    head = "".join(
        f"<th scope=col class=rk-axis>{_LIKELIHOOD_LABELS[lr]}<span class=muted> ({lr})</span></th>"
        for lr in range(1, 6)
    )
    body_rows = []
    for ir in range(5, 0, -1):
        cells = []
        for lr in range(1, 6):
            score = ir * lr
            band, _lab = _risk_band(score)
            n = counts.get((ir, lr), 0)
            n_html = f"<span class=rk-cell-n>{n}</span>" if n else ""
            tip = f"Impact {ir} x Likelihood {lr} = {score}" + (f" — {n} item(s)" if n else "")
            cells.append(
                f'<td class="rk-cell {band}{" rk-hit" if n else ""}" title="{tip}">'
                f"{n_html}<span class=rk-cell-s>{score}</span></td>"
            )
        body_rows.append(
            f"<tr><th scope=row class=rk-axis>{_IMPACT_LABELS[ir]}"
            f"<span class=muted> ({ir})</span></th>{''.join(cells)}</tr>"
        )
    legend = " ".join(
        f'<span class="rk-key {b}">{lab}</span>'
        for b, lab in (
            ("rk-min", "Minimal"),
            ("rk-low", "Low"),
            ("rk-mod", "Moderate"),
            ("rk-high", "High"),
            ("rk-extreme", "Extreme"),
        )
    )
    return (
        "<div class=panel><h2>Risk matrix &mdash; likelihood &times; impact</h2>"
        "<p class=muted>Each risk and issue placed by its quantified likelihood of occurrence and "
        "severity of schedule impact; cell colour is the conventional 5&times;5 risk heat "
        "(score = likelihood &times; impact, 1&ndash;25). The number in a cell is how many items "
        "fall there.</p>"
        '<table class="risk-matrix"><caption class=sr-only>Risk matrix: impact in rows (5 severe '
        "to 1 negligible) by likelihood in columns (1 rare to 5 certain); each cell shows its score "
        "and the count of items.</caption>"
        "<tr><th scope=col class=rk-corner>Impact &darr; / Likelihood &rarr;</th>"
        f"{head}</tr>{''.join(body_rows)}</table>"
        f"<p class=rk-legend>{legend}</p></div>"
    )


def _risk_ranking(items: list[Finding]) -> str:
    """The risks + issues ranked by score (highest first) as labelled bars, each annotated with the
    quantified float, driving float to the target, and working-day exposure."""
    if not items:
        return ""
    ranked = sorted(items, key=lambda f: (-f.risk_score, SEVERITY_ORDER[f.severity], f.metric_id))
    rows = []
    for f in ranked:
        band, band_label = _risk_band(f.risk_score)
        width = max(4, round(f.risk_score / 25 * 100))
        quant = []
        if f.float_days is not None:
            quant.append(f"float {_wd(f.float_days)}")
        if f.driving_float_days is not None:
            quant.append(f"driving float {_wd(f.driving_float_days)}")
        if f.impact_days is not None and f.impact_days > 0:
            quant.append(f"exposure {_wd(f.impact_days)}")
        quant_txt = (" &middot; " + " &middot; ".join(_e(q) for q in quant)) if quant else ""
        rows.append(
            f"<li class=rk-row><div class=rk-bar-track>"
            f'<div class="rk-bar {band}" style="width:{width}%"></div></div>'
            f'<div class=rk-row-meta><span class="rk-score {band}">{f.risk_score}</span> '
            f"<b>{_e(f.title)}</b> <span class=muted>[{_e(f.metric_id)}]</span>"
            f"<div class=rk-row-sub>{_LIKELIHOOD_LABELS[f.likelihood_score]} likelihood &middot; "
            f"{_IMPACT_LABELS[f.impact_score]} impact ({_e(band_label)}){quant_txt}</div>"
            f"</div></li>"
        )
    return (
        "<div class=panel><h2>Risk ranking &mdash; highest score first</h2>"
        "<p class=muted>Risks and issues ordered by score, with the quantified slack (total float, "
        "and driving float to the target when one is set) and the working-day schedule exposure if "
        "the item is realised.</p>"
        f"<ol class=rk-ranking>{''.join(rows)}</ol></div>"
    )


def _risks_section(title: str, lead: str, items: list[Finding], empty: str) -> str:
    body = "".join(_finding_card(f) for f in items) if items else f"<p class=muted>{empty}</p>"
    return (
        f"<div class=panel><h2>{title} <span class=muted>({len(items)})</span></h2>"
        f"<p class=muted>{lead}</p>{body}</div>"
    )


def _risks_body(
    sch: Schedule, findings: tuple[Finding, ...], narrative: Narrative, ai_key: str = ""
) -> str:
    """The Risks, Issues & Opportunities page: a high-level read first, then the cited detail.

    Grounded entirely in the engine's :func:`recommend` findings (RISK / CONCERN / OPPORTUNITY,
    each with a course of action and citations) plus the local-AI-polished narrative — high level
    first (executive read + a prioritized recovery plan), supporting detail beneath."""
    risks = [f for f in findings if f.category == Category.RISK]
    issues = [f for f in findings if f.category == Category.CONCERN]
    opps = [f for f in findings if f.category == Category.OPPORTUNITY]
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in narrative.statements)

    def _by_score(items: list[Finding]) -> list[Finding]:
        return sorted(items, key=lambda f: (-f.risk_score, SEVERITY_ORDER[f.severity], f.metric_id))

    threats = risks + issues
    matrix = _risk_matrix(threats)
    ranking = _risk_ranking(threats)

    # prioritized, de-duplicated recovery actions across risks + issues (most severe first)
    seen: set[str] = set()
    actions: list[Finding] = []
    for f in sorted(risks + issues, key=lambda x: (SEVERITY_ORDER[x.severity], x.metric_id)):
        if f.course_of_action and f.course_of_action not in seen:
            seen.add(f.course_of_action)
            actions.append(f)
    recovery = ""
    if actions:
        action_items = "".join(
            f"<li><b>{_e(a.course_of_action)}</b> "
            f"<span class=muted>&mdash; {_e(a.title)} ({_e(a.severity)})</span></li>"
            for a in actions
        )
        recovery = (
            "<div class=panel><h2>Recovery plan &mdash; prioritized actions</h2>"
            "<p class=muted>The highest-leverage actions to recover the plan, most severe first, "
            "each tied to the finding that motivates it.</p>"
            f"<ol class=recovery-list>{action_items}</ol></div>"
        )

    high_note = f" &mdash; {high} flagged HIGH severity" if high else ""
    summary = f"""
<div class=panel><h2>Risks, Issues &amp; Opportunities &mdash; {_e(sch.name)}</h2>
<p>At a glance: <b class=fail>{len(risks)} risk(s)</b>,
<b class=sev-MEDIUM>{len(issues)} issue(s)</b>, and
<b class=pass>{len(opps)} opportunity(ies)</b>{high_note}. The plain-English read is below; the
supporting detail for every item &mdash; with its citation and a recommended action &mdash;
follows in the sections beneath.</p>
<h3>AI read</h3>
<ul class=story id=riskStory data-ai-endpoint="/api/ai/narrative?key={_e(quote(ai_key))}">{story}</ul>
<p class=muted><b>AI can err &mdash; verify against the citations on each finding.</b> Enable a
local model in <a href="/settings">AI Settings</a> for a richer interpretation; the findings
themselves are engine-computed and cited.</p></div>
<script src="/static/ai_polish.js"></script>"""

    return (
        summary
        + matrix
        + ranking
        + recovery
        + _risks_section(
            "Risks",
            "Future-facing threats to the plan, highest risk score first.",
            _by_score(risks),
            "No forward-looking risks identified in this version.",
        )
        + _risks_section(
            "Issues (current concerns)",
            "Quality / integrity problems present right now, including manipulation signals.",
            _by_score(issues),
            "No current concerns identified in this version.",
        )
        + _risks_section(
            "Opportunities",
            "Levers to recover or improve the schedule.",
            _by_score(opps),
            "No specific opportunities surfaced from the current signals.",
        )
    )


def _phases_body(keys: list[str], current: str, yp: YearPhases) -> str:
    """Year Trend / Phase: an animated stepper across versions (the presentation) + a per-version
    detail table. The stepper (phases.js → /api/phases) animates the per-year makeup across every
    loaded version on a locked axis; the table gives the picked version's exact numbers."""
    sched_opts = "".join(
        f'<option value="{_e(k)}"{" selected" if k == current else ""}>{_e(k)}</option>'
        for k in keys
    )
    basis_opts = "".join(
        f'<option value="{b}"{" selected" if b == yp.basis else ""}>{_e(label)}</option>'
        for b, label in YEAR_BASES.items()
    )
    table_rows = "".join(
        f"<tr><td>{r.year}</td><td>{r.total}</td><td>{r.complete}</td>"
        f"<td>{r.in_progress}</td><td>{r.planned}</td><td>{r.milestones}</td></tr>"
        for r in yp.rows
    )
    undated = (
        f" &middot; {yp.undated} activit{'y' if yp.undated == 1 else 'ies'} have no "
        f"{_e(YEAR_BASES[yp.basis]).lower()} date (not binned)"
        if yp.undated
        else ""
    )
    return f"""
<div class=panel><h2>Year Trend / Phase &mdash; activities per calendar year</h2>
<p class=muted>How the work spreads across the program's years (complete / in-progress / planned).
<b>Play</b> the stepper to watch the distribution shift across every loaded version on a locked
axis; <b>Bin by</b> keys each year on a different date &mdash; the right basis is a judgement call,
so choose the one your analysis needs.</p>
<form method=get action="/phases" class=viz-controls>
<label>Detail schedule <select name=name onchange="this.form.submit()">{sched_opts}</select></label>
<label>Bin by <select name=basis onchange="this.form.submit()">{basis_opts}</select></label>
<noscript><button type=submit>Update</button></noscript>
</form>
<div class=mini-steps><button type=button id=phasesPrev>&#8249;</button>
<button type=button id=phasesPlay>&#9654;</button>
<button type=button id=phasesNext>&#8250;</button></div>
<div id=phasesLabel class=muted></div>
<div class=chart-host id=phasesChart data-basis="{_e(yp.basis)}"></div></div>
<div class=panel><h3>Detail &mdash; {_e(current)}</h3>
<p class=muted>Binned by <b>{_e(YEAR_BASES[yp.basis])}</b>{undated}.</p>
<table><tr><th scope=col>Year</th><th scope=col>Activities</th><th scope=col>Complete</th>
<th scope=col>In progress</th><th scope=col>Planned</th><th scope=col>Milestones</th></tr>
{table_rows}</table></div>
<script src="/static/phases.js"></script>"""


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
        "dcma": {c.metric_id: _dcma_card(c) for c in audit.checks},
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
        # the schedule's mapped .mpp custom/extended fields (declared order) -> optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
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
    # file order (the task list order MS Project displays) so the Gantt nests parents above
    # their children regardless of UID numbering; the indent itself comes from outline_level.
    order = {t.unique_id: i for i, t in enumerate(sch.tasks)}
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
                "complete": task.is_complete or task.actual_finish is not None,
                "is_critical": fr.is_critical,
                "is_milestone": task.is_milestone,
                "is_summary": False,
                "outline_level": task.outline_level,
                "order": order[fr.unique_id],
                "resource_names": ", ".join(task.resource_names),
                "source_file": sch.source_file,
                # mapped .mpp custom/extended fields populated on this task (label -> value); the
                # grid offers each as an optional column (ADR-0088 mapping -> ADR-0093 display)
                "custom": dict(task.custom_field_map),
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
                "complete": task.is_complete or task.actual_finish is not None,
                "is_critical": False,
                "is_milestone": task.is_milestone,
                "is_summary": True,
                "outline_level": task.outline_level,
                "order": order[task.unique_id],
                "resource_names": ", ".join(task.resource_names),
                "source_file": sch.source_file,
                "custom": dict(task.custom_field_map),
            }
        )
    rows.sort(key=lambda r: cast(int, r["order"]))
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

    # Driving links: each traced activity's immediate logic successors that are themselves on the
    # trace to the target — the "what is this linked to on the way to the target" detail (e.g.
    # UID 8022 → UID 152). on_path marks the successor that keeps the chain on the 0-slack path.
    trace_ids = set(results)
    drives: dict[int, list[dict[str, object]]] = {uid: [] for uid in trace_ids}
    for rel in sch.relationships:
        if rel.predecessor_id in trace_ids and rel.successor_id in trace_ids:
            drives[rel.predecessor_id].append(
                {
                    "uid": rel.successor_id,
                    "type": rel.type.value,
                    "lag_days": round(rel.lag_minutes / per_day, 1) if per_day else 0.0,
                    "on_path": results[rel.successor_id].on_driving_path,
                }
            )

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
                # robust "complete" for the hide-completed toggles: a real .mpp/.xer may
                # report a done activity at 99.x% while carrying an actual finish — treat
                # an actual finish (or >=100%) as complete so the toggle never misses it.
                "complete": task.is_complete or task.actual_finish is not None,
                "is_milestone": task.is_milestone,
                "date_driven": uid in date_driven,
                "resource_names": ", ".join(task.resource_names),
                # immediate logic successors within this trace (uid, type, lag, on_path) — the
                # "linked to UID X" detail surfaced by the Drives → column
                "drives": drives[uid],
                # mapped custom fields populated on this task (label → value); the grid offers
                # each as an optional column (ADR-0088 mapping → ADR-0093 display)
                "custom": dict(task.custom_field_map),
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
        # the schedule's mapped custom fields (declared order) → optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
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
<table><tr><th scope=col>Version</th><th scope=col>Project finish</th><th scope=col>Completed</th><th scope=col>In&nbsp;progress</th><th scope=col>Critical</th></tr>{trend_rows}</table>
{impact_html}</div>
<div class=panel><h2>Manipulation-trend signals</h2>
<table><tr><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
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
<table><tr><th scope=col>Version</th><th scope=col>Computed finish</th><th scope=col>% complete</th></tr>{rows}</table>
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
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>Project finish</th><th scope=col>Completed</th>
<th scope=col>In&nbsp;progress</th><th scope=col>Critical</th></tr>{trend_rows}</table>
<p>Net Finish Impact across the series: <b class={cls}>{days:+d} calendar days</b>
&mdash; the project finish moved {word} between the first and last version.</p></div>
{focus_form}{focus_panel}
<div class=panel><h2>Trend charts</h2><div id=trendCharts class="charts chart-host"
data-target="{target if target is not None else ""}"></div></div>
<div class=panel id=qualDrillPanel><h2>Quality drill-down &amp; animation</h2>
<p class=muted>Step through the versions (oldest first) and watch the count of <b>offending
activities</b> for each schedule-quality metric move on a <b>locked axis</b> &mdash; bar
heights stay comparable frame to frame, so a metric that worsens stands out. Pick a metric to
list the exact activities behind its number in the current version (the drill-down).</p>
<div class=viz-controls>
<label>Metric <select id=qualMetric></select></label>
<button id=qualPrev type=button>&#9664; Prev</button>
<span id=qualLabel class=muted></span>
<button id=qualNext type=button>Next &#9654;</button>
<button id=qualPlay type=button>&#9654; Auto-play</button>
</div>
<div class=qual-drill-grid>
<div id=qualBars class=qual-bars></div>
<div id=qualDrill class=qual-offenders></div>
</div></div>
<div class=panel><h2>Schedule-quality trends</h2>
<p class=muted>How each schedule-quality metric moves across the versions.</p>
<ul>{quality_items}</ul></div>
<div class=panel><h2>Manipulation-trend signals (consecutive versions)</h2>
<table><tr><th scope=col>Step</th><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
{"".join(signal_rows) or "<tr><td colspan=4 class=muted>No manipulation signals detected across the series (honest progress).</td></tr>"}</table></div>
<div class=panel><h2>Schedule margin burndown</h2>
<p class=muted>Tracks <b>total</b> vs <b>effective</b> margin &mdash; the buffer protecting the project
finish &mdash; across submissions, so margin erosion (a buffer being spent or quietly removed) is
visible at a glance.</p>
<div class="chart-host" id=marginBurndown></div></div>
<script src="/static/trend.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/margin.js"></script>"""


def _trend_data(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    analyses: list[_Analysis],
    target: int | None = None,
) -> dict[str, object]:
    """JSON for the trend charts: per-version headline numbers + quality-metric series.

    The ``analyses`` are pre-computed (cached) _Analysis objects parallel to schedules/cpms.
    Extended in ADR-0039 to carry per-version cross-file comparison and float-analysis data
    for the PBIX page 4+5 charts rendered by trend.js.
    """
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

    # HMI and CEI are period-over-period (each version scored against the previous version's data
    # date), so they are computed once across the ordered series and indexed per version (first =
    # None). HMI is baseline-anchored; CEI is forecast-anchored (prior forecast vs current actuals).
    hmi_series = compute_hmi_trend(schedules)
    cei_series = compute_cei_trend(schedules)
    # Float Ratio is single-snapshot; the trend scores each version and carries the period-over-period
    # delta (this minus prior) so the chart reads as a period-to-period series (ADR-0103).
    float_ratio_series = compute_float_ratio_trend(schedules, cpms)
    version_rows: list[dict[str, object]] = []
    for i, (p, sch, cpm, an) in enumerate(zip(points, schedules, cpms, analyses, strict=True)):
        makeup = compute_activity_makeup(sch)
        cp = an.completion
        fb = an.float_bands
        fs = compute_float_sums(sch, cpm)
        # BEI lives in the DCMA14 check (metric_id="DCMA14")
        bei_chk = next((c for c in an.audit.checks if c.metric_id == "DCMA14"), None)
        bei: float | None = bei_chk.value if (bei_chk and bei_chk.population) else None
        mei_r = cp["mei"]
        epi_r = cp["epi"]
        sfr_r = cp["start_finish_ratio"]
        # FEI (to-go forecast execution) + BRI (baseline realism) — single-snapshot (ADR-0100)
        fei = compute_fei(sch)
        bri_r = compute_bri(sch)
        # SVt (Earned-Schedule time variance, working days) per version — the SV/SVt trend (D4)
        svt = compute_schedule_variance(sch, non_summary(sch)).svt_days
        version_rows.append(
            {
                "label": p.source_file or f"v{p.version_index + 1}",
                "status_date": p.status_date.date().isoformat() if p.status_date else None,
                "finish": p.project_finish.date().isoformat(),
                "completed": p.completed,
                "in_progress": p.in_progress,
                "critical": p.critical,
                # SVt (Earned-Schedule time variance, working days; None when undefined) — SV/SVt trend
                "svt_days": svt,
                # PBIX p4 — Cross File Comparison
                "makeup": {
                    "milestones": makeup.milestones,
                    "normal": makeup.normal,
                    "summaries": makeup.summaries,
                },
                "status_split": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                },
                "completion_perf": {
                    "ahead": cp["completed_ahead"].count,
                    "on_schedule": cp["completed_on_schedule"].count,
                    "behind": cp["completed_behind"].count,
                },
                "indices": {
                    "mei": mei_r.value if mei_r.population else None,
                    "bei": bei,
                    "epi": epi_r.value if epi_r.population else None,
                    "sfr": sfr_r.value if sfr_r.population else None,
                    # HMI / CEI (period-over-period): None on the first version (no predecessor)
                    "hmi_tasks": hmi_series.task_values[i],
                    "hmi_milestones": hmi_series.milestone_values[i],
                    "cei_tasks": cei_series.task_values[i],
                    "cei_milestones": cei_series.milestone_values[i],
                    "cei_starts": cei_series.start_values[i],
                    "cei_critical": cei_series.critical_values[i],
                    "cei_adjusted": cei_series.adjusted_values[i],
                    # FEI / BRI (single-snapshot, baseline-anchored)
                    "fei_starts": fei["fei_starts"].value if fei["fei_starts"].population else None,
                    "fei_finish": fei["fei_finish"].value if fei["fei_finish"].population else None,
                    "bri": bri_r.value if bri_r.population else None,
                    # Float Ratio (single-snapshot; the delta is period-over-period)
                    "float_ratio": float_ratio_series.values[i],
                    "float_ratio_aggregate": float_ratio_series.aggregate_values[i],
                    "float_ratio_delta": float_ratio_series.deltas[i],
                },
                # PBIX p5 — Float Analysis
                "float_sums": {
                    "total_days": fs.total_days,
                    "free_days": fs.free_days,
                },
                "float_bands": {
                    k: {"count": v.count, "pct": round(v.value, 1)} for k, v in fb.items()
                },
            }
        )

    # Per-metric drill-down (M18 item 8): every §A quality metric carries, per version,
    # the offending activities (UID + name) behind the trended number — the data the
    # drill-down/animation panel steps through. Names resolve against each version's own
    # task map (an activity can change name between versions). No cap (Law 1, local).
    by_id_per_version = [s.tasks_by_id for s in schedules]
    quality: dict[str, object] = {}
    for t in compute_quality_trend(schedules, cpms):
        offenders_per_version = [
            [
                {"uid": uid, "name": by_id_per_version[vi][uid].name}
                for uid in offs
                if uid in by_id_per_version[vi]
            ]
            for vi, offs in enumerate(t.offenders_by_version)
        ]
        quality[t.metric_id] = {
            "name": t.name,
            "values": list(t.values),
            "lower_is_better": t.lower_is_better,
            "worst_index": t.worst_index,
            "counts": [len(offs) for offs in t.offenders_by_version],
            "offenders": offenders_per_version,
        }
    return {"target": focus, "versions": version_rows, "quality": quality}


def _cei_body(wave: BowWave, target_uid: int | None = None) -> str:
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
Auto-play to watch the wave move. Tick <b>Running totals</b> for the cumulative finish curves,
and focus a <b>Target UID</b> to mark where that activity lands (and slides) in each snapshot.</p>
<form method=get action=/cei class=viz-controls>
<label>Target UID <input name=target type=number min=1 value="{target_uid if target_uid is not None else ""}"
placeholder="UID"></label> <button type=submit>Focus</button>
{'<a class=btn-link href="/cei?target=">clear focus</a>' if target_uid is not None else ""}</form>
<div class=viz-controls>
<button id=prevSnap type=button>&#9664; Prev</button>
<span id=snapLabel class=muted></span>
<button id=nextSnap type=button>Next &#9654;</button>
<button id=autoPlay type=button>&#9654; Auto-play</button>
<label><input id=ceiTotals type=checkbox> Running totals (cumulative)</label>
</div>
<div id=ceiChart class=chart-host></div></div>
<div class=panel><h2>CEI &mdash; Current Execution Index</h2>
<p class=muted>For each snapshot: of the activities the <i>previous</i> snapshot planned to
finish in the following month, how many this snapshot re-scheduled for that month and how
how many of those planned activities actually finished by the end of it. CEI = completed-on-time &divide; previously planned (1.00 = executed to plan; an unplanned finish in the month earns no credit).</p>
<table><tr><th scope=col>Snapshot</th><th scope=col>Period</th><th scope=col>Previously planned</th><th scope=col>Re-scheduled</th>
<th scope=col>Actually finished</th><th scope=col>CEI</th></tr>{rows}</table></div>
<script src="/static/cei.js"></script>"""


def _scurve_filter_fields(versions: list[Schedule]) -> dict[str, list[str]]:
    """The parent file(s)' filterable fields → their distinct values, for the S-curve's own
    up-to-5-field filter. Capped so the embedded payload stays small on large schedules."""
    out: dict[str, list[str]] = {}
    for fld in available_fields_union(versions):
        values = distinct_values(versions, fld)
        if 0 < len(values) <= 1000:
            out[fld] = values[:300]
    return out


def _pair_criteria(cf: list[str], cv: list[str], versions: list[Schedule]) -> list[Criterion]:
    """Zip the cf/cv query lists into validated (field, value) criteria (<= MAX_FIELDS)."""
    fields = set(available_fields_union(versions))
    out: list[Criterion] = []
    for fld, value in zip(cf, cv, strict=False):
        if fld in fields and value:
            out.append((fld, value))
        if len(out) >= MAX_FIELDS:
            break
    return out


def _scurve_interpretation(sc: SCurve) -> str:
    """A grounded, always-present plain-English read of the S-curve: plan-vs-actual at the data
    date and how that gap is trending across versions — what the trend says about execution."""
    versions = sc.versions
    if not versions:
        return ""
    latest = versions[-1]
    si = latest.status_index
    if si is None or si >= len(latest.planned):
        read = (
            "This version has no data date, so plan-vs-actual can't be read at a status point; "
            "the curves show how the planned and scheduled finishes are distributed over time."
        )
    else:
        actual, planned = latest.actual[si], latest.planned[si]
        gap = planned - actual
        if gap > 2:
            verdict = f"running <b>{gap:.0f} points behind plan</b> at the data date"
            health = (
                "Execution is lagging the baseline — less work has completed than was promised "
                "by now, so the forecast finish is at risk unless the team recovers."
            )
        elif gap < -2:
            verdict = f"running <b>{-gap:.0f} points ahead of plan</b> at the data date"
            health = "Execution is ahead of the baseline — work is completing faster than planned."
        else:
            verdict = "tracking <b>on plan</b> at the data date"
            health = "Execution is essentially on the baseline at the status date."
        read = (
            f"As of the latest data date, <b>{actual:.0f}%</b> of the work has finished versus "
            f"<b>{planned:.0f}%</b> planned — {verdict}. {health}"
        )
    gaps = [
        v.planned[v.status_index] - v.actual[v.status_index]
        for v in versions
        if v.status_index is not None and v.status_index < len(v.planned)
    ]
    trend = ""
    if len(gaps) >= 2:
        delta = gaps[-1] - gaps[0]
        if delta > 1:
            trend = (
                f" Across the loaded versions the gap has <b>widened by {delta:.0f} points</b> — "
                "the schedule is falling further behind."
            )
        elif delta < -1:
            trend = (
                f" Across the loaded versions the gap has <b>narrowed by {-delta:.0f} points</b> — "
                "the team is recovering."
            )
        else:
            trend = " The plan-vs-actual gap has held roughly steady across the loaded versions."
    return (
        "<div class=panel><h2>AI interpretation</h2>"
        f"<p>{read}{trend}</p>"
        "<p class=muted><b>Auto-generated</b> from the S-curve's computed values &mdash; verify "
        'against the chart. Enable a local model in <a href="/settings">AI Settings</a> for a '
        "fuller, model-written read.</p></div>"
    )


def _scurve_body(sc: SCurve, fields: dict[str, list[str]]) -> str:
    """The animated S-curve view: cumulative planned vs actual/forecast progress per version,
    with a per-chart up-to-5-field filter over the parent file's fields."""
    # escape "<" so a field value can never break out of the inline <script> embed
    fields_json = json.dumps(fields).replace("<", "\\u003c")
    return f"""
<div class=panel><h2>S-Curve &mdash; cumulative progress</h2>
<p class=muted>Each version's cumulative progress on a fixed 0&ndash;100% scale: <b>gold</b> =
planned (share of activities the baseline had finishing by each month), <b>blue</b> =
actual / forecast (share whose actual or scheduled finish lands by each month). The dashed
line is that version's data date &mdash; actuals to its left, forecast to its right; the blue
curve sitting below the gold at the data date is work behind plan. Step through the versions
or press Auto-play to watch the actual curve climb (and lag) over time.</p>
<div class=viz-controls id=scurveFilterBar><span class=muted>Filter this chart by up to
{MAX_FIELDS} field(s) of the parent file:</span> <span id=scurveFilter></span></div>
<div class=viz-controls>
<label id=scurveVersionWrap style="display:none">File <select id=scurveVersion data-no-i18n>
<option value=all>All files (chronological)</option>
</select></label>
<button id=prevScurve type=button>&#9664; Prev</button>
<span id=scurveLabel class=muted></span>
<button id=nextScurve type=button>Next &#9654;</button>
<button id=scurvePlay type=button>&#9654; Auto-play</button>
<label>Time scale <select id=scurveGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label>
</div>
<div id=scurveChart class=chart-host></div></div>
{_scurve_interpretation(sc)}
<script>window.SF_SCURVE_FIELDS = {fields_json};</script>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>"""


def _ribbon_body(rows: list[tuple[str, object]], note: str) -> str:
    """The Acumen-Fuse-style Schedule Quality Ribbon: one row per loaded schedule, one column
    per ribbon metric — the metrics validated against the operator's Fuse workbook export."""
    cols = [
        ("Missing Logic", "missing_logic"),
        ("Logic Density™", "logic_density"),
        ("Critical", "critical"),
        ("Hard Constraints", "hard_constraints"),
        ("Negative Float", "negative_float"),
        ("Number of Lags", "number_of_lags"),
        ("Number of Leads", "number_of_leads"),
        ("Merge Hotspot", "merge_hotspot"),
        ("Avg Float (d)", "avg_float_days"),
        ("Max Float (d)", "max_float_days"),
    ]
    head = "<th scope=col>Schedule</th>" + "".join(
        f"<th scope=col>{_e(label)}</th>" for label, _ in cols
    )
    body = ""
    for key, r in rows:
        cells = "".join(f"<td>{_e(getattr(r, attr))}</td>" for _, attr in cols)
        body += f"<tr><td>{_e(key)}</td>{cells}</tr>"
    return f"""{note}
<div class=panel><h2>Schedule Quality Ribbon</h2>
<p class=muted>The schedule-quality ribbon metrics, one row per loaded
schedule. <b>Missing Logic</b> = activities missing a predecessor and/or successor;
<b>Logic Density™</b> = logic links per activity (2&times;links &divide; activities);
<b>Critical</b> = activities the source tool flags critical (its stored Critical / Total Slack);
<b>Lags</b> / <b>Leads</b> = activities whose predecessors carry a positive / negative offset,
counted across all statuses (planned, in-progress, or complete &mdash; unlike the
incomplete-only DCMA-14 checks); <b>Hard Constraints</b> / <b>Negative Float</b> are the DCMA
counts; <b>Merge Hotspot</b> = activities with more than two predecessors. These are validated
against the reference schedule-quality export. <i>Insufficient Detail™ and Float Ratio™ are
proprietary formulas and are omitted pending their exact definition.</i></p>
<table><tr>{head}</tr>{body}</table></div>"""


def _scurve_data(sc: SCurve) -> dict[str, object]:
    return {
        "months": list(sc.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_index": v.status_index,
                "status_date": v.status_date,
                "activities": v.activities,
                "planned": list(v.planned),
                "actual": list(v.actual),
            }
            for v in sc.versions
        ],
    }


def _cei_data(wave: BowWave, target_uid: int | None = None) -> dict[str, object]:
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
        "target_uid": target_uid,
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
                "target_scheduled_index": s.target_scheduled_index,
                "target_finished_index": s.target_finished_index,
            }
            for s in wave.snapshots
        ],
    }


def _latest_solvable(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The newest analyzable version (key, scoped schedule, cpm), scoped to the session filter.

    The same selection ``/api/sra`` and ``POST /sra/risk`` share: iterate the loaded versions
    oldest-first, keep the last one whose CPM solves, and return its scoped schedule + CPM. Returns
    ``None`` when nothing loaded version is analyzable (the caller surfaces the empty state)."""
    chosen: tuple[str, Schedule, CPMResult] | None = None
    for key, raw in st.ordered_versions():
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            continue
        chosen = (key, st.scope(raw), analysis.cpm)
    return chosen


def _sra_selected(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The schedule the SRA runs against — the operator's pick (``st.sra_file``) when it names a
    loaded, solvable version, otherwise the latest-solvable default. One resolver shared by the
    page, the simulation API, and the override POST so all three always agree on the file."""
    key = st.sra_file
    if key is not None and key in st.schedules:
        raw = st.schedules[key]
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            pass  # the chosen file no longer solves (e.g. filtered to nothing) -> fall back
        else:
            return (key, st.scope(raw), analysis.cpm)
    return _latest_solvable(st)


def _sra_overrides_table(st: SessionState, sch: Schedule | None) -> str:
    """The current per-activity overrides as a table (UID, opt/ml/pess in days) + Remove buttons."""
    if not st.sra_overrides:
        return "<p class=muted>No per-activity overrides &mdash; every activity uses the global triangular above.</p>"
    per_day = sch.calendar.working_minutes_per_day if sch is not None else 0
    names = sch.tasks_by_id if sch is not None else {}

    def _days(minutes: int) -> str:
        return f"{minutes / per_day:g}" if per_day else str(minutes)

    rows = []
    for uid in sorted(st.sra_overrides):
        opt, ml, pess = st.sra_overrides[uid]
        name = _e(names[uid].name) if uid in names else ""
        rows.append(
            f"<tr><td>{uid}</td><td>{name}</td><td>{_days(opt)}</td><td>{_days(ml)}</td>"
            f"<td>{_days(pess)}</td><td>"
            f'<form action="/sra/risk" method=post class=navform style="display:inline">'
            f'<input type=hidden name=remove value="{uid}">'
            "<button type=submit class=linkbtn>Remove</button></form></td></tr>"
        )
    return (
        "<table><thead><tr><th scope=col>UID</th><th scope=col>Activity</th>"
        "<th scope=col>Optimistic (d)</th><th scope=col>Most-likely (d)</th>"
        "<th scope=col>Pessimistic (d)</th><th scope=col></th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + '<form action="/sra/risk" method=post class=navform style="margin-top:8px">'
        + '<input type=hidden name=clear value="1">'
        + "<button type=submit>Clear all overrides</button></form>"
    )


def _sra_risk_table(st: SessionState, sch: Schedule | None) -> str:
    """The discrete-risk register as a table (name, probability, impact, affected) + Remove buttons."""
    if not st.sra_risks:
        return (
            "<p class=muted>No discrete risks registered &mdash; the run uses duration uncertainty "
            "only. Add a risk above to model a probabilistic event (e.g. a 40%-likely permit delay "
            "that stretches its activities 1.2&ndash;1.6&times;).</p>"
        )
    names = sch.tasks_by_id if sch is not None else {}

    def _affected(uids: tuple[int, ...]) -> str:
        chips = []
        for u in uids:
            nm = _e(names[u].name) if u in names else "?"
            chips.append(f"{u} &mdash; {nm}")
        return "; ".join(chips)

    rows = []
    for r in st.sra_risks:
        impact = f"{r.impact_low * 100:g}/{r.impact_ml * 100:g}/{r.impact_high * 100:g}%"
        rows.append(
            f"<tr><td>{_e(r.id)}</td><td>{_e(r.name)}</td><td>{r.probability * 100:g}%</td>"
            f"<td>{impact}</td><td>{_affected(r.affected)}</td><td>"
            f'<form action="/sra/risk-event" method=post class=navform style="display:inline">'
            f'<input type=hidden name=remove value="{_e(r.id)}">'
            "<button type=submit class=linkbtn>Remove</button></form></td></tr>"
        )
    return (
        "<table><thead><tr><th scope=col>ID</th><th scope=col>Risk</th>"
        "<th scope=col>Probability</th><th scope=col>Impact (lo/ml/hi)</th>"
        "<th scope=col>Affected activities</th><th scope=col></th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + '<form action="/sra/risk-event" method=post class=navform style="margin-top:8px">'
        + '<input type=hidden name=clear value="1">'
        + "<button type=submit>Clear all risks</button></form>"
    )


def _ssi_three_point(st: SessionState, sch: Schedule) -> dict[int, tuple[int, int, int]]:
    """Per-task ``(BestCase, MostLikely=remaining, WorstCase)`` minutes for the SSI run — a manual /
    auto Best-Worst override when present, else derived from the task's Risk Ranking Factor. Tasks
    with neither are absent (the engine treats them as a point mass = no duration uncertainty)."""
    tbl = RiskFactorTable(rows=st.sra_factor_rows)
    out: dict[int, tuple[int, int, int]] = {}
    for t in non_summary(sch):
        u = t.unique_id
        rem = (
            t.remaining_duration_minutes
            if t.remaining_duration_minutes is not None
            else t.duration_minutes
        )
        if u in st.sra_bcwc:
            bc, wc = st.sra_bcwc[u]
            out[u] = (bc, rem, wc)
        elif u in st.sra_factors:
            out[u] = factor_to_bc_wc(rem, st.sra_factors[u], tbl)
    return out


def _ssi_matrix_counts(risks: Sequence[SSIRiskStat], *, opportunity: bool) -> list[list[int]]:
    """A 5x5 ``[consequence-1][probability-1]`` count grid for the risks (impact >= 0) or the
    opportunities (impact < 0) — the operator's Risk / Opportunity Assessment Matrix."""
    grid = [[0] * 5 for _ in range(5)]
    for r in risks:
        if (r.impact_days < 0) == opportunity:
            # clamp defensively: a hand-edited / third-party setup.json can carry a rating outside
            # 1..5 (the form route clamps, the load route did too after the fix below) and must never
            # IndexError or silently mis-bin a forensic export
            c = min(5, max(1, r.consequence_rating))
            p = min(5, max(1, r.probability_rating))
            grid[c - 1][p - 1] += 1
    return grid


def _ssi_data(sch: Schedule, result: SSIResult) -> dict[str, object]:
    """The SSI run summary for ``sra.js`` — the focus finish dates + percentile + per-risk stats +
    the 5x5 Risk/Opportunity matrices. Dates are already realigned to the stored finish (ADR-0123)."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    return {
        "target_uid": result.target_uid,
        "focus_name": focus,
        "iterations": result.iterations,
        "occurrence_mode": result.occurrence_mode,
        "correlation": result.correlation,
        "used_risks": result.used_risks,
        "deterministic": {
            "date": result.deterministic_finish_date,
            "percentile": round(result.deterministic_percentile * 100, 1),
        },
        "mean": result.mean_date,
        "std_days": round(result.std_days, 1),
        "percentiles": [
            {"label": "P10", "date": result.p10_date},
            {"label": "P50", "date": result.p50_date},
            {"label": "P80", "date": result.p80_date},
            {"label": "P90", "date": result.p90_date},
        ],
        "risks": [
            {
                "id": r.id,
                "name": r.name,
                "probability": round(r.probability * 100, 1),
                "impact_days": r.impact_days,
                "hits": r.hits,
                "mean_delta_days": r.mean_delta_days,
                "probability_rating": r.probability_rating,
                "consequence_rating": r.consequence_rating,
            }
            for r in result.risks
        ],
        "risk_matrix": _ssi_matrix_counts(result.risks, opportunity=False),
        "opportunity_matrix": _ssi_matrix_counts(result.risks, opportunity=True),
        # dense plotting series (realigned dates): the cumulative S-curve + the finish-date histogram
        "s_curve": [{"date": d, "p": p} for d, p in result.s_curve],
        "finish_hist": [{"date": d, "count": c} for d, c in result.finish_hist],
    }


def _ssi_grid_rows(st: SessionState, sch: Schedule, cpm: CPMResult) -> list[dict[str, object]]:
    """Per-task rows for the editable SSI Gantt grid: the activity row (name, indent, dates,
    bar metadata — reusing ``_activity_rows``) plus the SSI inputs (Remaining d, Risk Ranking
    Factor, Best/Worst-case days, a risk flag, the focus flag). Only leaf (non-summary) tasks
    are editable — summaries carry no factor."""
    mpd = sch.calendar.working_minutes_per_day or 480
    risk_uids = {u for r in st.sra_ssi_risks for u in r.affected}
    by_id = sch.tasks_by_id
    rows = _activity_rows(sch, cpm)
    for row in rows:
        uid = cast("int", row["unique_id"])
        task = by_id.get(uid)
        editable = task is not None and not row["is_summary"]
        rem_days: float | None = None
        if editable and task is not None and mpd:
            rem_min = (
                task.remaining_duration_minutes
                if task.remaining_duration_minutes is not None
                else task.duration_minutes
            )
            rem_days = round(rem_min / mpd, 1)
        bc_days: float | None = None
        wc_days: float | None = None
        if uid in st.sra_bcwc and mpd:
            bc_days = round(st.sra_bcwc[uid][0] / mpd, 1)
            wc_days = round(st.sra_bcwc[uid][1] / mpd, 1)
        row.update(
            {
                "remaining_days": rem_days,
                "factor": st.sra_factors.get(uid),
                "bc_days": bc_days,
                "wc_days": wc_days,
                "has_risk": uid in risk_uids,
                "is_focus": uid == st.sra_focus_uid,
                "editable": editable,
            }
        )
    return rows


_SSI_SETUP_VERSION = 1


def _ssi_setup_dict(st: SessionState) -> dict[str, object]:
    """The whole SSI setup as a plain, versioned, JSON-serialisable dict (Save/Load + Excel)."""
    return {
        "setup_version": _SSI_SETUP_VERSION,
        "focus_uid": st.sra_focus_uid,
        "occurrence_mode": st.sra_occurrence_mode,
        "use_risk_register": st.sra_use_risk_register,
        "correlation": st.sra_correlation,
        "factor_table": [[f, sub, add] for f, sub, add in st.sra_factor_rows],
        "factors": {str(u): f for u, f in st.sra_factors.items()},
        "bcwc_minutes": {str(u): [bc, wc] for u, (bc, wc) in st.sra_bcwc.items()},
        "risks": [
            {
                "id": r.id,
                "name": r.name,
                "probability": r.probability,
                "impact_days": r.impact_days,
                "affected": list(r.affected),
                "consequence_rating": r.consequence_rating,
            }
            for r in st.sra_ssi_risks
        ],
    }


def _apply_ssi_setup(st: SessionState, data: dict[str, object]) -> None:
    """Repopulate the SSI SessionState from a saved setup dict, validating against the active
    schedule: unknown / summary UIDs are dropped, factors clamped 1..5, probabilities 0..1."""
    chosen = _sra_selected(st)
    leaf: set[int] = set()
    if chosen is not None:
        _key, sch, _cpm = chosen
        leaf = {t.unique_id for t in non_summary(sch)}

    def _ok(uid: object) -> bool:
        return isinstance(uid, int) and (not leaf or uid in leaf)

    rows = data.get("factor_table")
    if isinstance(rows, list) and len(rows) == 5:
        with contextlib.suppress(TypeError, ValueError, IndexError):
            st.sra_factor_rows = tuple(
                (int(r[0]), min(100.0, max(0.0, float(r[1]))), min(300.0, max(0.0, float(r[2]))))
                for r in rows
            )
    focus = data.get("focus_uid")
    st.sra_focus_uid = focus if isinstance(focus, int) and _ok(focus) else None
    mode = data.get("occurrence_mode")
    st.sra_occurrence_mode = "exact_overall" if mode == "exact_overall" else "random_each"
    st.sra_use_risk_register = bool(data.get("use_risk_register", True))
    try:
        st.sra_correlation = min(1.0, max(0.0, float(data.get("correlation", 0.0))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        st.sra_correlation = 0.0
    factors: dict[int, int] = {}
    raw_factors = data.get("factors")
    if isinstance(raw_factors, dict):
        for key, val in raw_factors.items():
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            if _ok(uid):
                try:
                    factors[uid] = min(5, max(0, int(val)))  # 0 = no Best/Worst uncertainty
                except (TypeError, ValueError):
                    continue
    st.sra_factors = factors
    bcwc: dict[int, tuple[int, int]] = {}
    raw_bcwc = data.get("bcwc_minutes")
    if isinstance(raw_bcwc, dict):
        for key, pair in raw_bcwc.items():
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
            if _ok(uid) and isinstance(pair, list) and len(pair) == 2:
                try:
                    bcwc[uid] = (max(0, int(pair[0])), max(0, int(pair[1])))
                except (TypeError, ValueError):
                    continue
    st.sra_bcwc = bcwc
    risks: list[ScheduleRisk] = []
    seq = 0
    raw_risks = data.get("risks")
    if isinstance(raw_risks, list):
        for item in raw_risks:
            if not isinstance(item, dict):
                continue
            affected = tuple(u for u in item.get("affected", []) if _ok(u))
            if not affected:
                continue
            seq += 1
            cons = item.get("consequence_rating")
            try:
                prob = min(1.0, max(0.0, float(item.get("probability", 0.0))))
                impact = float(item.get("impact_days", 0.0))
            except (TypeError, ValueError):
                continue
            risks.append(
                ScheduleRisk(
                    id=str(item.get("id") or f"R{seq}"),
                    name=str(item.get("name") or f"Risk {seq}"),
                    probability=prob,
                    impact_days=impact,
                    affected=affected,
                    consequence_rating=min(5, max(1, int(cons))) if isinstance(cons, int) else None,
                )
            )
    st.sra_ssi_risks = risks
    st.sra_ssi_risk_seq = seq


def _ssi_export_tables(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> TableSet:
    """The six-table SSI hand-out (ADR-0123): run setup, per-task durations, risk register,
    focus-finish results, OAT sensitivity, and the two 5x5 matrices."""
    mpd = sch.calendar.working_minutes_per_day or 480
    names = sch.tasks_by_id
    focus_name = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    setup = Table(
        "Run setup",
        ("Field", "Value"),
        (
            (
                "Focus event",
                f"{result.target_uid} - {focus_name}"
                if result.target_uid is not None
                else focus_name,
            ),
            ("Occurrence mode", result.occurrence_mode),
            ("Correlation", result.correlation),
            ("Risk register", "on" if result.used_risks else "off"),
            ("Iterations", result.iterations),
            ("Schedule", sch.name),
        ),
    )
    dur_rows: list[tuple[Cell, ...]] = []
    for uid in sorted(set(st.sra_factors) | set(st.sra_bcwc)):
        task = names.get(uid)
        if task is None:
            continue
        bc = st.sra_bcwc.get(uid)
        dur_rows.append(
            (
                uid,
                task.name,
                st.sra_factors.get(uid),
                round(bc[0] / mpd, 2) if bc else None,
                round(bc[1] / mpd, 2) if bc else None,
            )
        )
    durations = Table(
        "Per-task durations",
        ("UID", "Task", "Factor", "Best case d", "Worst case d"),
        tuple(dur_rows),
    )
    risk_by_id = {r.id: r for r in st.sra_ssi_risks}
    risks = Table(
        "Risk register",
        (
            "ID",
            "Name",
            "Probability %",
            "Impact d",
            "Affected",
            "Consequence",
            "Hits",
            "Mean delta d",
        ),
        tuple(
            (
                rs.id,
                rs.name,
                round(rs.probability * 100, 1),
                rs.impact_days,
                ", ".join(str(u) for u in risk_by_id[rs.id].affected)
                if rs.id in risk_by_id
                else "",
                rs.consequence_rating,
                rs.hits,
                rs.mean_delta_days,
            )
            for rs in result.risks
        ),
    )
    results = Table(
        "Focus-finish results",
        ("Measure", "Value"),
        (
            ("Deterministic finish", result.deterministic_finish_date),
            ("Deterministic percentile", round(result.deterministic_percentile * 100, 1)),
            ("P10", result.p10_date),
            ("P50", result.p50_date),
            ("P80", result.p80_date),
            ("P90", result.p90_date),
            ("Mean", result.mean_date),
            ("Std deviation (working days)", round(result.std_days, 2)),
        ),
    )
    sens = Table(
        "OAT sensitivity",
        (
            "UID",
            "Task",
            "Best case d",
            "Worst case d",
            "ML d",
            "Opportunity wd",
            "Risk wd",
            "Total wd",
        ),
        tuple(
            (
                o.unique_id,
                names[o.unique_id].name if o.unique_id in names else "",
                round(o.bc_minutes / mpd, 2),
                round(o.wc_minutes / mpd, 2),
                round(o.ml_minutes / mpd, 2),
                o.opportunity_days,
                o.risk_days,
                o.total_days,
            )
            for o in oat[:200]
        ),
    )
    risk_grid = _ssi_matrix_counts(result.risks, opportunity=False)
    opp_grid = _ssi_matrix_counts(result.risks, opportunity=True)
    risk_matrix = Table(
        "Risk matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(risk_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    opp_matrix = Table(
        "Opportunity matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(opp_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    return TableSet(
        f"Schedule Risk & Opportunity Analysis - {sch.name}",
        (setup, durations, risks, results, sens, risk_matrix, opp_matrix),
    )


# The NASA 5x5 priority ranks (1..25) + tri-band zones (mirrors web/static/sra_ssi.js), reused to
# render the Risk/Opportunity matrices as shaded grids in the Word report (ADR-0124).
_NASA_RANK = (
    (1, 3, 5, 8, 12),
    (2, 6, 11, 14, 17),
    (4, 9, 15, 19, 21),
    (7, 13, 18, 22, 24),
    (10, 16, 20, 23, 25),
)
_NASA_ZONE = (
    ("g", "g", "g", "g", "y"),
    ("g", "g", "y", "y", "r"),
    ("g", "y", "y", "r", "r"),
    ("g", "y", "r", "r", "r"),
    ("g", "y", "r", "r", "r"),
)
_NASA_FILL = {
    "risk": {"g": "43A047", "y": "FFD400", "r": "E53935"},
    "opp": {"g": "A8D3EA", "y": "3D8EC4", "r": "15527D"},
}
_NASA_LIK = ("Remote", "Unlikely", "Possible", "Highly Likely", "Near Certainty")
_NASA_CONS_RISK = ("Low", "Minor", "Moderate", "Significant", "Severe")
_NASA_CONS_OPP = ("Low", "Minor", "Moderate", "High", "Very High")


def _sra_chart_scurve(result: SSIResult) -> Chart | None:
    """The cumulative finish-date S-curve as a fully-labelled vector chart: gridlines + axis + dense
    curve + dashed deterministic line + P10/50/80/90 dots, with a title, y-axis confidence ticks,
    x-axis date ticks + axis title, a legend, and a parked block of the percentile dates."""
    pts = [(dt.date.fromisoformat(d), p) for d, p in result.s_curve]
    if len(pts) < 2:
        return None
    x0 = min(d.toordinal() for d, _ in pts)
    span = (max(d.toordinal() for d, _ in pts) - x0) or 1

    def fx(day: dt.date) -> float:
        return max(0.0, min(1.0, (day.toordinal() - x0) / span))

    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.25, 0.5, 0.75, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    curve = (tuple((fx(d), p) for d, p in pts), "0B6BCB", 19050)
    detf = fx(dt.date.fromisoformat(result.deterministic_finish_date))
    det_line = (((detf, 0.0), (detf, 1.0)), "D29922", 9525)
    dots = tuple(
        (fx(dt.date.fromisoformat(ds)), q, "E8352E")
        for q, ds in (
            (0.10, result.p10_date),
            (0.50, result.p50_date),
            (0.80, result.p80_date),
            (0.90, result.p90_date),
        )
    )
    start_iso, end_iso = pts[0][0].isoformat(), pts[-1][0].isoformat()
    labels = (
        ChartText(0.0, 1.15, "Finish-date confidence (S-curve)", "l", 18, "222B35", True),
        *(ChartText(-0.015, q, f"{int(q * 100)}%", "r", 12) for q in (0.0, 0.25, 0.5, 0.75, 1.0)),
        ChartText(0.0, -0.07, start_iso, "l", 12),
        ChartText(1.0, -0.07, end_iso, "r", 12),
        ChartText(
            0.5, -0.18, "Forecast finish date  (y = % chance of finishing on or before)", "c", 12
        ),
        ChartText(
            0.02,
            0.84,
            f"P10  {result.p10_date}\nP50  {result.p50_date}\nP80  {result.p80_date}\n"
            f"P90  {result.p90_date}\nDeterministic  {result.deterministic_finish_date}",
            "l",
            13,
            "33414E",
        ),
        ChartText(0.04, -0.30, "— confidence curve", "l", 11, "0B6BCB"),
        ChartText(0.40, -0.30, "- - deterministic (logic-only) finish", "l", 11, "B5790C"),
        ChartText(0.80, -0.30, "* P10-P90 markers", "l", 11, "E8352E"),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.7,
        polylines=(*grids, axis, curve, det_line),
        dots=dots,
        labels=labels,
    )


def _sra_chart_hist(result: SSIResult) -> Chart | None:
    """The finish-date distribution (histogram) as labelled vector bars: title, a 0..max frequency
    y-axis, x-axis date ticks + axis title, and a call-out on the most-likely (tallest) bar."""
    bins = result.finish_hist
    if not bins:
        return None
    maxc = max((c for _d, c in bins), default=0) or 1
    peak_i = max(range(len(bins)), key=lambda i: bins[i][1])
    peak_date, peak_count = bins[peak_i]
    n = len(bins)
    rects = tuple(
        (i / n + 0.008, 0.0, (i + 1) / n - 0.008, c / maxc, "3D8EC4")
        for i, (_d, c) in enumerate(bins)
    )
    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.5, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    labels = (
        ChartText(0.0, 1.15, "Finish-date distribution", "l", 18, "222B35", True),
        ChartText(-0.015, 0.0, "0", "r", 12),
        ChartText(-0.015, 0.5, f"{round(maxc / 2)}", "r", 12),
        ChartText(-0.015, 1.0, f"{maxc}", "r", 12),
        ChartText(-0.04, 1.13, "Iterations", "l", 11),
        ChartText(0.0, -0.07, bins[0][0], "l", 12),
        ChartText(1.0, -0.07, bins[-1][0], "r", 12),
        ChartText(0.5, -0.18, "Forecast finish date  (y = number of simulated finishes)", "c", 12),
        ChartText(
            (peak_i + 0.5) / n,
            min(1.07, peak_count / maxc + 0.07),
            f"most likely\n{peak_date} ({peak_count})",
            "c",
            11,
            "1A5276",
        ),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.5,
        polylines=(*grids, axis),
        rects=rects,
        labels=labels,
    )


def _sra_chart_tornado(oat: Sequence[OATSensitivity]) -> Chart | None:
    """The duration-sensitivity tornado: per task a centred bar — opportunity-to-accelerate (green,
    left of centre) and risk-of-delay (red, right) — scaled to the largest total swing, with a
    title, per-row UID + total-swing labels, a centre baseline, a working-day scale, and a legend."""
    rows = [o for o in oat if o.total_days > 0][:12]
    if not rows:
        return None
    maxv = max((o.opportunity_days + o.risk_days for o in rows), default=0.0) or 1.0
    n = len(rows)
    rects: list[tuple[float, float, float, float, str]] = []
    labels: list[ChartText] = [
        ChartText(
            0.0, 1.13, "Duration sensitivity (tornado) — working-day swing", "l", 18, "222B35", True
        ),
        ChartText(0.27, 1.04, "◀ opportunity (accelerate)", "c", 11, "2E7D32"),
        ChartText(0.73, 1.04, "risk (delay) ▶", "c", 11, "C62828"),
        ChartText(0.5, -0.06, "0", "c", 12),
        ChartText(0.0, -0.06, f"-{maxv:g} wd", "l", 11),
        ChartText(1.0, -0.06, f"+{maxv:g} wd", "r", 11),
        ChartText(
            0.5,
            -0.17,
            "Working days the focus finish moves when each task is swung Best↔Worst",
            "c",
            12,
        ),
    ]
    for i, o in enumerate(rows):
        y0 = 1.0 - (i + 0.85) / n
        y1 = 1.0 - (i + 0.15) / n
        yc = 1.0 - (i + 0.5) / n
        opp = (o.opportunity_days / maxv) * 0.5
        risk = (o.risk_days / maxv) * 0.5
        if opp > 0:
            rects.append((0.5 - opp, y0, 0.5, y1, "43A047"))
        if risk > 0:
            rects.append((0.5, y0, 0.5 + risk, y1, "E53935"))
        labels.append(ChartText(-0.015, yc, str(o.unique_id), "r", 11, "33414E"))
        labels.append(ChartText(1.0, yc, f"{o.total_days:g} wd", "l", 11, "33414E"))
    center = (((0.5, 0.0), (0.5, 1.0)), "555555", 9525)
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.9,
        polylines=(center,),
        rects=tuple(rects),
        labels=tuple(labels),
    )


def _sra_matrix_chart(result: SSIResult, *, opportunity: bool) -> Chart:
    """The 5x5 Risk/Opportunity assessment matrix as a shaded grid: NASA rank (1-25) + (count)."""
    counts = _ssi_matrix_counts(result.risks, opportunity=opportunity)  # [consequence-1][prob-1]
    fam = "opp" if opportunity else "risk"
    cons = _NASA_CONS_OPP if opportunity else _NASA_CONS_RISK
    fill = _NASA_FILL[fam]

    def cell(lk: int, c: int) -> tuple[str, str, str]:
        cnt = counts[c - 1][lk - 1]
        zone = _NASA_ZONE[lk - 1][c - 1]
        text = f"{_NASA_RANK[lk - 1][c - 1]}" + (f" ({cnt})" if cnt else "")
        dark_text = zone == "r" or (opportunity and zone == "y")
        return (text, fill[zone], "FFFFFF" if dark_text else "10202E")

    header = (
        ("L \\ C", "E9EEF5", "333333"),
        *((f"{c + 1} {cons[c]}", "E9EEF5", "333333") for c in range(5)),
    )
    body = tuple(
        ((f"{lk} {_NASA_LIK[lk - 1]}", "E9EEF5", "333333"), *(cell(lk, c) for c in range(1, 6)))
        for lk in range(5, 0, -1)
    )
    return Chart(kind="matrix", grid=(header, *body))


def _sra_report_blocks(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> list[Block]:
    """The comprehensive narrative SRA Word report (ADR-0124): a PM-level executive summary, then
    per-section detail (focus-finish + S-curve + distribution, duration sensitivity + tornado,
    per-task durations, risk register, the 5x5 matrices) with embedded vendor-free vector charts,
    plus a methodology & assumptions section. Reuses the export tables for the data grids."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    by_title = {t.title: t for t in _ssi_export_tables(st, sch, result, oat).tables}

    def doc(title: str) -> DocTable:
        t = by_title[title]
        return DocTable(t.headers, t.rows)

    top = oat[0] if oat else None
    top_txt = (
        f"{top.unique_id} {names[top.unique_id].name if top.unique_id in names else ''} "
        f"({top.total_days:g} wd total swing)"
        if top
        else "n/a"
    )
    det_pct = round(result.deterministic_percentile * 100)
    blocks: list[Block] = [Heading(f"Schedule Risk Analysis Report - {sch.name}", level=0)]
    blocks += [
        Heading("Executive summary", level=1),
        Paragraph(
            f"This Schedule Risk Analysis evaluates the finish of {focus} over {result.iterations} "
            f"Monte-Carlo iterations. The deterministic (logic-only) finish is "
            f"{result.deterministic_finish_date} (about P{det_pct}). The risk-adjusted finish is most "
            f"likely {result.p50_date} (P50); {result.p80_date} at P80 and {result.p90_date} at P90 "
            f"carry progressively more contingency. The mean outcome is {result.mean_date} with a "
            f"standard deviation of {round(result.std_days, 1)} working days. "
            f"{len(result.risks)} discrete risk/opportunity event(s) were modeled. The largest "
            f"duration-sensitivity driver is task {top_txt}."
        ),
        DocTable(
            ("Measure", "Value"),
            (
                (
                    "Focus event",
                    f"{result.target_uid} - {focus}" if result.target_uid is not None else focus,
                ),
                (
                    "Deterministic finish",
                    f"{result.deterministic_finish_date} (P{round(result.deterministic_percentile * 100, 1)})",
                ),
                ("P50 (most likely)", result.p50_date),
                ("P80", result.p80_date),
                ("P90", result.p90_date),
                ("Mean", result.mean_date),
                ("Std deviation (working days)", round(result.std_days, 1)),
                ("Risk / opportunity events", len(result.risks)),
                ("Top sensitivity driver", top_txt),
            ),
        ),
        Paragraph(
            "Read the P-values as confidence levels: a P80 date has an approximately 80% modeled "
            "chance of being met. The deterministic finish typically sits well below P50, so the gap "
            "between them is the contingency the current logic does not yet carry.",
            lead="How to read this:",
        ),
    ]
    blocks += [
        Heading("How to set up this analysis (inputs)", level=1),
        Paragraph(
            "The forecast is driven entirely by the inputs below. Enter them on the Schedule Risk & "
            "Opportunity Analysis page, then run the Monte-Carlo. This section documents exactly what "
            "was used for this report so the analysis can be reviewed and reproduced."
        ),
        DocTable(
            ("Input", "How you enter it", "What it does"),
            (
                (
                    "Focus event",
                    "Type the task UID whose finish you want to forecast (blank = project finish).",
                    "Every result (S-curve, percentiles, sensitivity) is measured at this event's finish.",
                ),
                (
                    "Risk Ranking Factor (0-5)",
                    "Per task, in the grid or the 'Assign Risk Ranking Factor' box (one value, a list of "
                    "UIDs, or paste a whole column from Excel/MS Project).",
                    "0 = no duration uncertainty (uses the Remaining Duration as-is). 1-5 widen the "
                    "Best/Worst-case spread using the Risk Factors table below.",
                ),
                (
                    "Best / Worst-case duration",
                    "Auto-calculated from the factor (ML = current Remaining Duration), or type a value "
                    "to override.",
                    "Sets the low/high ends of each task's sampled duration range.",
                ),
                (
                    "Risk / Opportunity register",
                    "Add an event with a probability %, a schedule impact in days (positive = delay/risk, "
                    "negative = acceleration/opportunity), and the affected task UID(s).",
                    "On each iteration the event may fire and add its impact to the affected tasks.",
                ),
                (
                    "Occurrence mode",
                    "Choose 'Random each iteration' or 'Exact percentage overall'.",
                    "How often registered events fire across the run (see below).",
                ),
                (
                    "Correlation",
                    "0 to 1 (0 = independent; 0.3-0.5 typical).",
                    "Couples task durations so highs/lows do not fully cancel, widening the spread.",
                ),
            ),
        ),
        Heading("Risk Factors table (factor -> Best/Worst case)", level=2),
        Paragraph(
            "Best case = ML x (1 - subtract%/100); Worst case = ML x (1 + add%/100), where ML is the "
            "task's current Remaining Duration. These are the percentages used for this report:"
        ),
        DocTable(
            ("Risk Ranking Factor", "% subtract (Best case)", "% add (Worst case)"),
            (
                ("0 (no uncertainty)", "0", "0"),
                *((f, f"{s:g}", f"{a:g}") for f, s, a in st.sra_factor_rows),
            ),
        ),
        Paragraph(_OCC_RANDOM, lead="Random each iteration:"),
        Paragraph(_OCC_EXACT, lead="Exact percentage overall:"),
    ]
    blocks += [
        Heading("Focus-finish results", level=1),
        Paragraph(
            "The simulated finish-date distribution of the focus event: the deterministic finish, the "
            "P10/P50/P80/P90 confidence dates, the mean, and the spread (standard deviation)."
        ),
        doc("Focus-finish results"),
    ]
    sc = _sra_chart_scurve(result)
    if sc is not None:
        blocks += [
            Heading("Finish-date confidence (S-curve)", level=2),
            sc,
            Paragraph(
                "Cumulative probability of finishing on or before each date (blue). The dashed amber "
                "line is the deterministic finish; the red dots mark P10/P50/P80/P90.",
                italic=True,
            ),
        ]
    hc = _sra_chart_hist(result)
    if hc is not None:
        blocks += [
            Heading("Finish-date distribution", level=2),
            hc,
            Paragraph(
                "How many of the simulated runs landed on each finish date (taller = more likely). The "
                "labelled bar is the single most-likely finish date.",
                italic=True,
            ),
        ]
    blocks += [
        Heading("Duration sensitivity (one-at-a-time)", level=1),
        Paragraph(
            "Each ranked activity's Best/Worst-case duration is swung independently to measure how far "
            "it can pull in (opportunity to accelerate, green) or push out (risk of delay, red) the "
            "focus finish. This deterministic one-at-a-time method is validated against the "
            "reference tool."
        ),
    ]
    tor = _sra_chart_tornado(oat)
    if tor is not None:
        ranked = sum(1 for o in oat if o.total_days > 0)
        scope = (
            f"Top {min(12, ranked)} of {ranked} ranked activities shown"
            if ranked > 12
            else "All ranked activities shown"
        )
        blocks += [
            tor,
            Paragraph(
                "Bars centred on zero: green extends left (acceleration), red right (delay); the "
                f"longest total swing sets the scale. {scope}; the full set is in the table below.",
                italic=True,
            ),
        ]
    blocks.append(doc("OAT sensitivity"))
    blocks += [
        Heading("Per-task Best/Worst-case durations", level=1),
        Paragraph(
            "The Risk Ranking Factor assigned to each ranked task and the Best/Worst-case durations "
            "derived from it (ML = current Remaining Duration), or entered manually."
        ),
        doc("Per-task durations"),
    ]
    blocks += [
        Heading("Risk / Opportunity register", level=1),
        Paragraph(
            "Discrete risks and opportunities, each with its probability, additive schedule impact, "
            "simulated occurrence count, and 1-5 probability/consequence ratings."
        ),
        doc("Risk register"),
    ]
    blocks += [
        Heading("Risk & Opportunity assessment matrices", level=1),
        Paragraph(
            "Each event is placed by its Likelihood of Occurrence (rows, 1-5) and Consequence/Benefit "
            "of Occurrence (columns, 1-5). Each cell shows the NASA priority rank (1-25) and, in "
            "parentheses, the count of events that land there."
        ),
        Heading("Risk Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=False),
        Heading("Opportunity Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=True),
    ]
    blocks += [
        Heading("Methodology & assumptions", level=1),
        Paragraph(
            "Best/Worst-case durations use ML = the current Remaining Duration; "
            "BC = ML x (1 - subtract%/100), WC = ML x (1 + add%/100) with the per-factor percentages "
            f"from the Risk Factors table. Occurrence mode: {result.occurrence_mode}. Correlation: "
            f"{result.correlation:g}. Risk register: {'on' if result.used_risks else 'off'}. "
            "Consequence (1-5) is auto-rated from the schedule impact via the NASA Schedule guideline "
            "(impact days converted to calendar months: <1 week=1, 1 week to <1 month=2, 1 to "
            "<3 months=3, 3 to <=6 months=4, >6 months=5)."
        ),
        Paragraph(
            "The Best/Worst-case derivation and the deterministic one-at-a-time sensitivity are "
            "validated against the reference tool. The stochastic distribution (S-curve, histogram, "
            "percentiles) uses a standard-library random generator that is statistically "
            "representative but NOT bit-identical to the reference tool's, so treat the P-values as "
            "close, not exact "
            "(ADR-0005/0106). All computation is local and offline; this document carries the CUI "
            "marking in its header and footer.",
            italic=True,
        ),
    ]
    return blocks


_OCC_RANDOM = (
    "When this option is selected, the probability of risks/opportunities occurring is evaluated "
    "independently on each iteration of the SRA using the entered probability of occurrence. Over "
    "many iterations the average result will be close to the entered percentage, but the exact "
    "number of occurrences may vary each time you run the SRA."
)
_OCC_EXACT = (
    "When this option is selected, the total number of times a given risk/opportunity occurs is "
    "determined at the beginning of the SRA process based on the entered probability and the total "
    "number of SRA iterations chosen. That total is then randomly distributed across the iterations, "
    "so the risk/opportunity occurs the exact expected number of times overall."
)


def _ssi_panel(st: SessionState) -> str:
    """The SSI Schedule Risk & Opportunity Analysis controls (ADR-0123): focus event, Risk Factors
    table + per-task ranking + auto-calc, occurrence/correlation run options, the risk register, and
    the run/sensitivity buttons feeding ``/api/sra/ssi`` and ``/api/sra/oat`` (run off page-load)."""
    factor_rows = "".join(
        f"<tr><td>{f}</td>"
        f'<td><input type=number name=sub{f} min=0 max=100 step=1 value="{s:g}" style="width:60px"></td>'
        f'<td><input type=number name=add{f} min=0 max=300 step=1 value="{a:g}" style="width:60px"></td></tr>'
        for f, s, a in st.sra_factor_rows
    )
    risk_rows = (
        "".join(
            f"<tr><td>{_e(r.id)}</td><td>{_e(r.name)}</td><td>{r.probability * 100:g}%</td>"
            f"<td>{r.impact_days:g} d</td><td>{', '.join(str(u) for u in r.affected)}</td>"
            f'<td><form action="/sra/ssi-risk" method=post style="display:inline">'
            f'<input type=hidden name=action value=remove><input type=hidden name=rid value="{_e(r.id)}">'
            f"<button type=submit class=linkbtn>remove</button></form></td></tr>"
            for r in st.sra_ssi_risks
        )
        or "<tr><td colspan=6 class=muted>No risks registered.</td></tr>"
    )
    rand_ck = " checked" if st.sra_occurrence_mode == "random_each" else ""
    exact_ck = " checked" if st.sra_occurrence_mode == "exact_overall" else ""
    iters = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    return f"""
<div class=panel><h2>Schedule Risk &amp; Opportunity Analysis</h2>
<p class=muted>Rank each task 1&ndash;5 (Risk Ranking Factor), auto-calculate
its Best/Worst Case from the factor table, attach discrete risks with an additive schedule impact in
days, and run a Monte-Carlo to a chosen <b>focus event</b>. The current Remaining Duration is the Most
Likely. <b>Best/Worst Case and the deterministic sensitivity are validated against the reference
tool</b>; the random distribution is statistically close, not bit-identical (a different RNG,
ADR-0005).</p>
<form action="/sra/ssi-run-config" method=post class=viz-controls>
<label>Focus event UID <input type=number name=focus_uid min=1 value="{st.sra_focus_uid or ""}"
 placeholder="project finish"></label>
<label title="{_e(_OCC_RANDOM)}"><input type=radio name=occurrence_mode value=random_each{rand_ck}>
 Random each iteration &#9432;</label>
<label title="{_e(_OCC_EXACT)}"><input type=radio name=occurrence_mode value=exact_overall{exact_ck}>
 Exact percentage overall &#9432;</label>
<label title="Blanket correlation between the task duration distributions (0 = independent; 0.3&ndash;0.5 typical) — offsets the cancelling of extreme high/low results.">Correlation
 <input type=number name=correlation min=0 max=1 step=0.05 value="{st.sra_correlation:g}" style="width:60px"></label>
<label><input type=checkbox name=use_risks value=on{" checked" if st.sra_use_risk_register else ""}>
 Use risk register</label>
<button type=submit>Save run options</button></form>
<h3>Risk Factors table</h3>
<form action="/sra/factor-table" method=post>
<table style="width:auto"><tr><th>Factor</th><th>% subtract (Best Case)</th><th>% add (Worst Case)</th></tr>
{factor_rows}</table><button type=submit>Save factor table</button></form>
<h3>Assign Risk Ranking Factor &amp; calculate Best/Worst durations</h3>
<form action="/sra/factor" method=post class=viz-controls>
<label>UIDs <input type=text name=uids placeholder="101, 102 205"></label>
<label title="0 = no Best/Worst uncertainty (use the remaining duration as-is); 1-5 widen the Best/Worst spread.">Factor (0&ndash;5) <input type=number name=factor min=0 max=5 value=3 style="width:56px"></label>
<button type=submit>Set factor</button></form>
<p class=muted>{len(st.sra_factors)} task(s) ranked; {len(st.sra_bcwc)} have calculated Best/Worst durations.</p>
<form action="/sra/auto-calc" method=post style="display:inline"><input type=hidden name=scope value=all>
<button type=submit>Calculate SRA Durations — all</button></form>
<form action="/sra/auto-calc" method=post style="display:inline;margin-left:8px"><input type=hidden name=scope value=selected>
<input type=text name=uids placeholder="selected UIDs" style="width:150px">
<button type=submit>Calculate — selected</button></form>
<h3>Risk / Opportunity register</h3>
<form action="/sra/ssi-risk" method=post class=viz-controls><input type=hidden name=action value=add>
<label>Name <input type=text name=name maxlength=80 placeholder="e.g. Permit delay"></label>
<label>Probability % <input type=number name=prob min=0 max=100 step=any placeholder="79"></label>
<label>Schedule impact (days) <input type=number name=impact_days step=any placeholder="100 (negative = opportunity)"></label>
<label>Affected UIDs <input type=text name=affected placeholder="106"></label>
<label title="Leave blank to auto-rate from the schedule impact (NASA Schedule guideline: the impact days converted to calendar months -- &lt;1 week=1, 1 week to &lt;1 month=2, 1 to &lt;3 months=3, 3 to &lt;=6 months=4, &gt;6 months=5).">Consequence 1-5 <input type=number name=consequence min=1 max=5 style="width:56px" placeholder="auto &#9432;"></label>
<button type=submit>Add risk</button></form>
<table><tr><th>ID</th><th>Name</th><th>Prob</th><th>Impact</th><th>Affected</th><th></th></tr>{risk_rows}</table>
<h3>Editable schedule grid</h3>
<p class=muted>The whole schedule as a spreadsheet-style grid: type a <b>Risk Ranking Factor</b> (0&ndash;5) or
edit <b>Best/Worst Case</b> days inline, and pick the <b>focus</b> event with the radio. <b>Factor 0
means no duration uncertainty</b> &mdash; no Best/Worst case, the remaining duration is used as-is;
1&ndash;5 widen the Best/Worst spread. A factor auto-fills Best/Worst from the table above; an explicit
Best/Worst entry is a manual override.
<b>Paste from Excel / MS&nbsp;Project:</b> copy a whole column (or a Factor/BC/WC block) and paste it
onto the first cell to fill the column down across every task in one go. Edits queue until you press
<b>Save grid</b>. Summary rows are bold and not editable.</p>
<div class=viz-controls>
<label>Zoom <input id=ssiGridZoom type=range min=0.4 max=6 step=0.2 value=1.4></label>
<button id=ssiGridReload type=button>Refresh grid</button>
<button id=ssiGridSave type=button>Save grid</button>
<span id=ssiGridStatus class=muted aria-live=polite></span></div>
<div id=ssiGrid class=sra-grid-host></div>
<div class=viz-controls style="margin-top:12px">
<label>Iterations <select id=ssiIters>{iters}</select></label>
<label>Distribution <select id=ssiDist data-no-i18n><option value=triangular>Triangular</option>
<option value=pert>Beta-PERT</option></select></label>
<button id=ssiRun type=button>Run SRA</button>
<button id=ssiOat type=button title="Deterministic one-at-a-time Best/Worst swing on the focus event (2xN CPM solves)">Run sensitivity</button></div>
<p id=ssiStatus class=muted aria-live=polite></p>
<div id=ssiResult></div><div id=ssiCharts class=ssi-charts></div>
<div id=ssiMatrices class=ssi-matrices></div>
<p class=muted style="font-size:11px">Tip: each chart and matrix has its own toolbar (full screen, zoom in/out, reset) to enlarge or shrink it, and hovering any point, bar, or matrix cell calls out its values (a matrix cell lists the risks that land there).</p>
<h3>Sensitivity — deterministic one-at-a-time (OAT)</h3><div id=ssiOatOut></div>
<h3>Save / load setup &amp; export</h3>
<div class=viz-controls>
<a class=btn href="/sra/ssi/save" download>Save setup (JSON)</a>
<form action="/sra/ssi/load" method=post enctype="multipart/form-data" style="display:inline">
<label>Load setup <input type=file name=setup accept="application/json,.json"></label>
<button type=submit>Load</button></form>
<a class=btn href="/export/xlsx/sra">Export tables (Excel)</a>
<a class=btn href="/export/docx/sra" title="A full PM-level SRA report: summary, S-curve, distribution, sensitivity tornado, risk register, and the 5x5 matrices as embedded graphics.">Download SRA report (Word)</a>
<a class=btn href="/export/xlsx/sra-registry">Download risk registry (Excel)</a>
<a class=btn href="/export/docx/sra-registry">Risk registry (Word)</a></div>
<script src="/static/gantt.js"></script><script src="/static/sra_ssi.js"></script>
<script src="/static/sra_grid.js"></script></div>"""


def _sra_body(st: SessionState) -> str:
    """The Schedule Risk Analysis (SRA) results page: risk-input panel + (empty) chart hosts.

    The simulation is intentionally NOT run here — ``sra.js`` fetches ``/api/sra`` (which now reads
    the session's manual risk inputs) and renders the confidence S-curve, finish-date histogram,
    and the sensitivity tornado. Running 1000x CPM during the page render would hang on a large
    schedule, so the page opens instantly and the run happens off the page-load path.
    """
    iter_opts = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    sch = _sra_selected(st)
    scoped = sch[1] if sch is not None else None
    selected_key = sch[0] if sch is not None else None
    file_opts = "".join(
        f'<option value="{_e(key)}"{" selected" if key == selected_key else ""}>{_e(key)}</option>'
        for key, _raw in st.ordered_versions()
    )
    file_selector = (
        '<form method=get action="/sra" class=viz-controls style="margin-bottom:8px">'
        "<label>Run SRA against file "
        f"<select name=file>{file_opts}</select></label>"
        "<button type=submit>Run on this file</button></form>"
        if len(st.schedules) > 1
        else ""
    )
    low_pct = f"{st.sra_low * 100:g}"
    ml_pct = f"{st.sra_ml * 100:g}"
    high_pct = f"{st.sra_high * 100:g}"
    on_defaults = (
        st.sra_low == 0.9 and st.sra_ml == 1.0 and st.sra_high == 1.10 and not st.sra_overrides
    )
    if on_defaults:
        disclaimer = (
            '<div class="notice warn" role=note><b>Auto defaults &mdash; screening placeholder, '
            "not SME-validated.</b> With no analyst-supplied risk ranges this run applies an "
            "industry-default <b>triangular</b> distribution to each activity's <i>remaining</i> "
            "duration (Min&nbsp;90% / Most-Likely&nbsp;100% / Max&nbsp;110% &mdash; an industry "
            '"Realistic" default). It is a <b>screening placeholder, not SME-validated</b> (GAO/NASA/AACE '
            "prefer elicited ranges) and is overridable per-activity. A duration-only run is a "
            "<i>schedule</i> confidence level &mdash; JCL (cost-loaded) is out of scope until cost "
            "inputs exist (ADR-0106).</div>"
        )
    else:
        disclaimer = (
            '<div class="notice ok" role=note>Using your analyst-supplied uncertainty (global '
            f"low/ml/high = {low_pct}/{ml_pct}/{high_pct}%, {len(st.sra_overrides)} per-activity "
            "overrides). A duration-only run is a <i>schedule</i> confidence level &mdash; JCL "
            "(cost-loaded) is out of scope until cost inputs exist (ADR-0106).</div>"
        )
    return f"""
{_ssi_panel(st)}
<div class=panel><h2>Legacy SRA &mdash; Monte-Carlo (multiplicative risk drivers)</h2>
<p class=muted>A seeded Monte-Carlo simulation samples each activity's duration from its
distribution and recomputes the network finish through the trusted CPM solver, building a
finish-date confidence curve. The deterministic CPM finish is marked against the distribution
so you can read how much contingency it implies (the deterministic date typically sits well
below P50). Per-activity criticality and duration sensitivity drive the tornado.</p>
{disclaimer}
{file_selector}
<p class=muted>Active file: <b>{_e(selected_key) if selected_key else "&mdash;"}</b>
{"(latest solvable version)" if st.sra_file is None else ""}</p>
<div class=viz-controls>
<label>Iterations <select id=sraIters>{iter_opts}</select></label>
<label>Distribution <select id=sraDistribution data-no-i18n>
<option value=triangular selected>Triangular</option>
<option value=pert>Beta-PERT</option>
</select></label>
<button id=sraRun type=button>Run simulation</button>
</div>
<p id=sraStatus class=muted aria-live=polite></p></div>
<div class=panel><h2>Risk inputs</h2>
<p class=muted>These uncertainty ranges feed the next simulation run. The <b>global</b> triangular
applies to every activity's <i>remaining</i> duration (the standard "Quick Risk" screening
approach); completed work is fixed at its actuals (no uncertainty). Per-activity 3-point overrides
take precedence over the global for the activities you elicit.</p>
<form action="/sra/risk" method=post class=viz-controls>
<label>Low % <input type=number id=sraLow name=low min=5 max=100 step=any value="{low_pct}"></label>
<label>Most-likely % <input type=number id=sraMl name=ml min=50 max=150 step=any value="{ml_pct}"></label>
<label>High % <input type=number id=sraHigh name=high min=100 max=300 step=any value="{high_pct}"></label>
<button type=submit>Save global risk</button>
</form>
<h3>Per-activity override (3-point, days)</h3>
<form action="/sra/risk" method=post class=viz-controls>
<label>UID <input type=number name=uid min=1 step=1></label>
<label>Optimistic (d) <input type=number name=opt_days min=0 step=any></label>
<label>Most-likely (d) <input type=number name=ml_days min=0 step=any></label>
<label>Pessimistic (d) <input type=number name=pess_days min=0 step=any></label>
<button type=submit>Add override</button>
</form>
{_sra_overrides_table(st, scoped)}</div>
<div class=panel><h2>Risk register (discrete risk drivers)</h2>
<p class=muted>Discrete, probabilistic events (the GAO/AACE/Hulett <b>risk-driver</b> method). Each risk
has a <b>probability</b> of occurring; when it occurs it multiplies the sampled duration of the
activities it is mapped to by a 3-point <b>impact</b> factor (entered as percentages &mdash; e.g.
100/120/150 means no change to +50%). One risk mapped to several activities correlates them
automatically (the shared-driver correlation, no coefficient needed). Risks combine with the
duration uncertainty above; the resulting "Risk drivers" tornado ranks each by the schedule slip it
causes.</p>
<form action="/sra/risk-event" method=post class=viz-controls>
<label>Risk name <input type=text name=name maxlength=80 placeholder="e.g. Permit delay"></label>
<label>Probability % <input type=number name=prob min=0 max=100 step=any placeholder="40"></label>
<label>Impact low % <input type=number name=imp_low min=0 step=any placeholder="100"></label>
<label>Impact ml % <input type=number name=imp_ml min=0 step=any placeholder="120"></label>
<label>Impact high % <input type=number name=imp_high min=0 step=any placeholder="150"></label>
<label>Affected UIDs <input type=text name=affected placeholder="101, 102 205"></label>
<button type=submit>Add risk</button>
</form>
{_sra_risk_table(st, scoped)}
<h3>Risk drivers (tornado)</h3>
<p class=muted>The mean project-finish slip each risk contributes &mdash; the difference between the
mean finish over the iterations the risk fired and the iterations it did not (working days), with
its observed occurrence rate. Empty until a risk is registered.</p>
<div id=sraRisk class=chart-host></div></div>
<div class=panel><h2>Finish-date confidence (S-curve)</h2>
<p class=muted>Cumulative probability of finishing on or before each date, with P10/P50/P80/P90
markers and the deterministic CPM finish annotated with the percentile it sits at.</p>
<div id=sraCdf class=chart-host></div></div>
<div class=panel><h2>Finish-date distribution</h2>
<div id=sraHist class=chart-host></div></div>
<div class=panel><h2>Duration sensitivity (tornado)</h2>
<p class=muted>The activities whose duration most drives the project finish (Spearman rank
correlation), with each activity's Criticality Index and Schedule Sensitivity Index.</p>
<div id=sraSens class=chart-host></div></div>
<script src="/static/sra.js"></script>"""


def _sra_data(st: SessionState, sch: Schedule, result: SRAResult) -> dict[str, object]:
    """The SRA results payload for ``sra.js`` — offsets resolved to ISO dates on the calendar."""
    cal = sch.calendar
    ps = sch.project_start

    def _iso(offset: int) -> str:
        return offset_to_datetime(ps, max(offset, 0), cal).isoformat()

    names = sch.tasks_by_id
    # tornado: the most influential activities by |duration sensitivity| (top 20)
    top = sorted(result.activities, key=lambda a: abs(a.duration_sensitivity), reverse=True)[:20]
    sensitivity = [
        {
            "uid": a.unique_id,
            "name": names[a.unique_id].name if a.unique_id in names else "",
            "ci": round(a.criticality_index, 4),
            "sens": round(a.duration_sensitivity, 4),
            "ssi": round(a.ssi, 4),
        }
        for a in top
    ]
    return {
        "iterations": result.iterations,
        "auto_used": result.auto_used,
        "manual": {
            "low": st.sra_low,
            "ml": st.sra_ml,
            "high": st.sra_high,
            "overrides": len(st.sra_overrides),
        },
        "deterministic": {
            "date": _iso(result.deterministic_finish),
            "percentile": round(result.deterministic_percentile * 100, 1),
        },
        "percentiles": [
            {"label": "P10", "date": result.p10_date},
            {"label": "P50", "date": result.p50_date},
            {"label": "P80", "date": result.p80_date},
            {"label": "P90", "date": result.p90_date},
        ],
        "mean": _iso(round(result.mean)),
        "cdf": [[_iso(offset), prob] for offset, prob in result.cdf],
        "histogram": [[_iso(lo), _iso(hi), count] for lo, hi, count in result.histogram],
        "sensitivity": sensitivity,
        "constraints_flagged": len(result.constraints_flagged),
        "risk_drivers": [
            {
                "id": d.id,
                "name": d.name,
                "probability": round(d.probability, 4),
                "hits": d.hits,
                "iterations": result.iterations,
                "delta_days": d.mean_delta_days,
            }
            for d in result.risk_drivers
        ],
    }


def _task_name_across(schedules: list[Schedule], uid: int) -> str | None:
    """The activity's name from the newest version that has it (None if no version does)."""
    for sch in reversed(schedules):
        task = sch.tasks_by_id.get(uid)
        if task is not None:
            return task.name
    return None


def _corridor_chips(snap: DrivingPathSnapshot) -> str:
    """The corridor as an ordered chain of UID — name chips; entered chips flag the new ones."""
    if not snap.between.path:
        return f"<span class=muted>{_e(snap.status)}</span>"
    entered = set(snap.entered)
    chips: list[str] = []
    for uid, name in zip(snap.between.path, snap.names, strict=True):
        cls = "ev-entered" if uid in entered else "ev-stayed"
        chips.append(f'<span class="dp-chip {cls}">{uid} &mdash; {_e(name)}</span>')
    return " <span class=dp-arrow>&rarr;</span> ".join(chips)


def _task_iso_dates(
    sch: Schedule,
    basis_start: dict[int, int],
    basis_finish: dict[int, int],
    uid: int,
) -> tuple[str | None, str | None]:
    """A task's (start, finish) as ISO dates — the same stored-or-CPM basis the Path page uses
    (stored dates render verbatim; otherwise the date_basis offsets convert on the calendar)."""
    task = sch.tasks_by_id.get(uid)
    if task is None:
        return None, None
    if task.start is not None and task.finish is not None:
        return task.start.date().isoformat(), task.finish.date().isoformat()
    cal = sch.calendar
    s, f = basis_start.get(uid), basis_finish.get(uid)
    si = (
        offset_to_datetime(sch.project_start, max(s, 0), cal).date().isoformat()
        if s is not None
        else None
    )
    fi = (
        offset_to_datetime(sch.project_start, max(f, 0), cal).date().isoformat()
        if f is not None
        else None
    )
    return si, fi


def _driving_path_gantt(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    evo: DrivingPathEvolution,
    a_name: str,
    b_name: str,
) -> dict[str, object]:
    """Per-version corridor activities with dates — the payload the animated Gantt steps through.

    Each version carries the corridor's activities (ordered, with start/finish + an ``entered``
    flag vs the prior version) so the JS can draw the bars on a date axis held fixed across every
    version, the corridor visibly shifting as the schedule slips."""
    version_data: list[dict[str, object]] = []
    for sch, cpm, snap in zip(schedules, cpms, evo.snapshots, strict=True):
        basis_start, basis_finish = date_basis(sch, cpm)
        by_id = sch.tasks_by_id
        entered = set(snap.entered)
        acts: list[dict[str, object]] = []
        for uid, name in zip(snap.between.path, snap.names, strict=True):
            start, finish = _task_iso_dates(sch, basis_start, basis_finish, uid)
            task = by_id.get(uid)
            acts.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "is_milestone": task.is_milestone if task is not None else False,
                    "entered": uid in entered,
                }
            )
        version_data.append(
            {
                "label": snap.label,
                "data_date": snap.status_date,
                "status": snap.status,
                "change_note": snap.change_note,
                "drives": snap.between.drives,
                "activities": acts,
            }
        )
    return {
        "source_uid": evo.source_uid,
        "target_uid": evo.target_uid,
        "source_name": a_name,
        "target_name": b_name,
        "versions": version_data,
    }


def _driving_tiers_panel(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    """Three columns of the activities driving ``target`` in the LATEST version, bucketed by
    driving-slack tier (ADR-0011): critical/driving (0 working days — the driving path), secondary
    (<= 10 days), tertiary (<= 20 days). Fewer days = more control over the target."""
    sch, cpm = schedules[-1], cpms[-1]
    if target not in sch.tasks_by_id:
        return ""  # the corridor branch already reports a target absent from every version
    try:
        results = compute_driving_slack(sch, target, cpm_result=cpm)
    except (KeyError, ValueError):
        return ""
    by_id = sch.tasks_by_id
    buckets: dict[str, list[tuple[int, str, float]]] = {
        "driving": [],
        "secondary": [],
        "tertiary": [],
    }
    for uid, r in results.items():
        if uid == target:
            continue
        label = _EVO_TIER_LABEL.get(r.tier)
        if label in buckets:
            t = by_id.get(uid)
            buckets[label].append(
                (uid, t.name if t is not None else f"UID {uid}", float(r.driving_slack_days))
            )
    for items in buckets.values():
        items.sort(key=lambda a: (a[2], a[0]))
    cols = [
        ("driving", "Critical / driving", "0 days"),
        ("secondary", "Secondary", f"&le; {DEFAULT_SECONDARY_MAX_DAYS} days"),
        ("tertiary", "Tertiary", f"&le; {DEFAULT_TERTIARY_MAX_DAYS} days"),
    ]
    blocks: list[str] = []
    for key, title, sub in cols:
        items = buckets[key]
        if items:
            rows = "".join(
                f"<tr><td class=num>{u}</td><td>{_e(n)}</td><td class=num>{d:.1f}</td></tr>"
                for u, n, d in items
            )
            body = (
                "<table class=card-table><tr><th scope=col>UID</th>"
                "<th scope=col>Activity</th><th scope=col>Slack (d)</th></tr>"
                f"{rows}</table>"
            )
        else:
            body = "<p class=muted>none</p>"
        blocks.append(
            f'<div style="flex:1;min-width:15em"><h3>{title} '
            f"<span class=muted>({len(items)} &middot; {sub})</span></h3>{body}</div>"
        )
    focus = by_id.get(target)
    fname = _e(focus.name) if focus is not None else f"UID {target}"
    return (
        f"<div class=panel><h2>Driving tiers to {target} &mdash; {fname}</h2>"
        "<p class=muted>Activities driving this target in the latest version, by their driving "
        "slack: <b>critical</b> (0 working days &mdash; the driving path), <b>secondary</b>, and "
        "<b>tertiary</b>. Fewer days = more control over the target (ADR-0011).</p>"
        '<div style="display:flex;gap:1em;align-items:flex-start;flex-wrap:wrap">'
        f"{''.join(blocks)}</div></div>"
    )


def _driving_tier_trend(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    """Per-version trend of how the driving path to ``target`` degrades: the count of activities at
    each driving-slack tier — driving (0 days) / secondary (<=10) / tertiary (<=20) — over the
    loaded versions, oldest first. A GROWING driving count means slack is eroding into the path
    (more activities now control the target's date); the delta column flags that movement."""
    if len(schedules) < 2:
        return ""
    rows: list[tuple[str, str, int | None, int | None, int | None, int | None]] = []
    prior_driving: int | None = None
    any_present = False
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        dd = sch.status_date.date().isoformat() if sch.status_date else "&mdash;"
        if target not in sch.tasks_by_id:
            rows.append((label, dd, None, None, None, None))
            continue
        any_present = True
        counts = {"driving": 0, "secondary": 0, "tertiary": 0}
        try:
            for uid, r in compute_driving_slack(sch, target, cpm_result=cpm).items():
                if uid == target:
                    continue
                lab = _EVO_TIER_LABEL.get(r.tier)
                if lab in counts:
                    counts[lab] += 1
        except (KeyError, ValueError):
            pass
        delta = None if prior_driving is None else counts["driving"] - prior_driving
        prior_driving = counts["driving"]
        rows.append((label, dd, counts["driving"], counts["secondary"], counts["tertiary"], delta))
    if not any_present:
        return ""

    def num(v: int | None) -> str:
        return "&mdash;" if v is None else str(v)

    body = ""
    for label, dd, drv, sec, ter, delta in rows:
        if delta is None or delta == 0:
            dtxt = "" if delta is None else "0"
        elif delta > 0:  # the driving path GREW — slack eroded (degradation)
            dtxt = f'<span style="color:var(--bad)">&#9650;+{delta}</span>'
        else:
            dtxt = f'<span style="color:var(--ok)">&#9660;{delta}</span>'
        body += (
            f"<tr><td>{_e(label)}</td><td>{dd}</td><td class=num>{num(drv)}</td>"
            f"<td class=num>{num(sec)}</td><td class=num>{num(ter)}</td>"
            f"<td class=num>{dtxt}</td></tr>"
        )
    return (
        "<div class=panel><h2>Driving-slack degradation trend</h2>"
        "<p class=muted>How the driving path to this target changes across the loaded versions "
        "(oldest first): the count of activities at each driving-slack tier. A rising "
        "<b>driving (0d)</b> count means slack is eroding into the path &mdash; more work now "
        "controls the target's finish (ADR-0011).</p>"
        "<table class=card-table><tr><th scope=col>Version</th><th scope=col>Data date</th>"
        "<th scope=col>Driving (0d)</th><th scope=col>Secondary</th><th scope=col>Tertiary</th>"
        f"<th scope=col>&Delta; driving</th></tr>{body}</table></div>"
    )


def _driving_path_body(
    schedules: list[Schedule], cpms: list[CPMResult], source: int | None, target: int | None
) -> str:
    """Server-rendered Driving Path view: the controlling logic corridor between two chosen
    UniqueIDs, and how it changes across every loaded version (oldest first by data date)."""
    form = f"""
<div class=panel><form method=get action=/driving-path class=viz-controls>
<label>From (source UniqueID): <input name=source type=number min=1
value="{source if source is not None else ""}" placeholder="UID A"></label>
<label>To (target UniqueID): <input name=target type=number min=1
value="{target if target is not None else ""}" placeholder="UID B"></label>
<button type=submit>Trace</button></form>
<p class=muted style="margin:.4em 0 0">The <b>driving path</b> from A to B is the chain of
activities controlling B's date that lie on a logic route from A &mdash; the work that, if it
slips, moves B. If A reaches B only through activities with float, the two are <b>connected</b>
but A does not <b>drive</b> B (the slack is reported instead). Trace it across every loaded
version to see the corridor shift.</p></div>"""

    tiers_html = (
        _driving_tiers_panel(schedules, cpms, target) + _driving_tier_trend(schedules, cpms, target)
        if target is not None
        else ""
    )

    if source is None or target is None:
        hint = (
            "Enter a source and a target UniqueID above to trace the driving path between them"
            + (
                " &mdash; or enter just a target to see its driving tiers above."
                if target is None
                else "."
            )
        )
        return form + tiers_html + f"<div class=panel><p class=muted>{hint}</p></div>"

    a_name = _task_name_across(schedules, source)
    b_name = _task_name_across(schedules, target)
    if a_name is None or b_name is None:
        missing = source if a_name is None else target
        return (
            form
            + tiers_html
            + (
                f'<div class="notice err">UniqueID {missing} is not present in any loaded '
                f"version.</div>"
            )
        )

    evo = compute_driving_path_evolution(schedules, cpms, source, target)
    header = (
        f"<div class=panel><h2>Driving path: {source} &mdash; {_e(a_name)} "
        f"&rarr; {target} &mdash; {_e(b_name)}</h2>"
        f"<p class=muted>{len(evo.snapshots)} version(s), oldest first.</p></div>"
    )

    # animated date-axis Gantt of the corridor over the versions (ADR-0096); only when at least
    # one version actually has a corridor to draw (and there's more than one version to step).
    gantt = _driving_path_gantt(schedules, cpms, evo, a_name, b_name)
    versions = cast("list[dict[str, object]]", gantt["versions"])
    has_corridor = any(v["activities"] for v in versions)
    gantt_html = ""
    if has_corridor and len(schedules) > 1:
        blob = json.dumps(gantt).replace("</", "<\\/")  # safe to embed in a <script> tag
        gantt_html = f"""
<div class=panel><h2>Corridor over time</h2>
<p class=muted>The driving corridor drawn on a date axis held fixed across every version, so it
visibly shifts as the schedule slips. Step or play through the versions; activities that
<b class=ev-entered>entered</b> the corridor since the prior version are outlined.</p>
<div class=viz-controls>
<button id=dpPrev type=button>&#9664; Prev</button>
<span id=dpLabel class=muted></span>
<button id=dpNext type=button>Next &#9654;</button>
<button id=dpPlay type=button>&#9654; Auto-play</button>
<span class=muted style="margin-left:1em">Zoom:</span>
<button id=dpZoomOut type=button title="zoom out">&minus;</button>
<button id=dpZoomIn type=button title="zoom in">&plus;</button>
</div>
<div id=dpChart class=path-view></div></div>
<script type="application/json" id=dpData>{blob}</script>
<script src="/static/driving_path.js"></script>"""

    rows: list[str] = []
    for snap in evo.snapshots:
        when = f" &middot; data date {snap.status_date}" if snap.status_date else ""
        note = f' <span class="dp-note">{_e(snap.change_note)}</span>' if snap.change_note else ""
        delta = ""
        if snap.length_delta:
            sign = "+" if snap.length_delta > 0 else ""
            delta = f" <span class=muted>(corridor length {sign}{snap.length_delta})</span>"
        left = ""
        if snap.left:
            names = ", ".join(
                f"{uid} {_e(_task_name_across(schedules, uid) or '')}".strip() for uid in snap.left
            )
            left = f"<div class=muted>Left the corridor: <span class=ev-left>{names}</span></div>"
        rows.append(
            f"<div class=panel><h3>{_e(snap.label)}{when}</h3>"
            f"<p>{_corridor_chips(snap)}</p>"
            f"<p class=muted>{_e(snap.status)}{note}{delta}</p>"
            f"{left}</div>"
        )

    return form + tiers_html + header + gantt_html + "".join(rows)


def _metric_scorecard_table(results: dict[str, MetricResult]) -> str:
    """A compact check/value/status table from a DCMA-14 result dict (over any (sub)schedule)."""
    rows = []
    for m in results.values():
        if m.unit == "ratio":  # CPLI / BEI — an index
            valcell = f"{round(m.value, 2)}"
        elif m.population:
            pct = m.value if m.unit == "%" else 100.0 * m.count / m.population
            valcell = f"{m.count} <span class=muted>of {m.population}</span> ({pct:.1f}%)"
        else:
            valcell = str(m.count)
        rows.append(
            f"<tr><td>{_e(m.name)}</td><td class=num>{valcell}</td>"
            f'<td class="{_status_class(m.status)}">{_e(m.status)}</td></tr>'
        )
    return (
        "<table class=card-table><tr><th scope=col>Check</th><th scope=col>Value</th>"
        f"<th scope=col>Status</th></tr>{''.join(rows)}</table>"
    )


def _groups_field_options(fields: Sequence[str], selected: str) -> str:
    """``<option>`` list of the given selectable fields with one pre-selected."""
    opts = ['<option value="">(field…)</option>']
    for f in fields:
        sel = " selected" if f == selected else ""
        opts.append(f'<option value="{_e(f)}"{sel}>{_e(f)}</option>')
    return "".join(opts)


def _criterion_value_list(value: str | Sequence[str]) -> list[str]:
    """A criterion's selected values as a list ([] = no value restriction / field populated)."""
    if isinstance(value, str):
        return [value] if value else []
    return [v for v in value if v]


def _groups_form(
    versions: list[tuple[str, Schedule]],
    version_key: str,
    sch: Schedule,
    criteria: list[Criterion],
    breakdown: str,
) -> str:
    """The scope controls: filter rows (applied session-wide to every file), a preview-version
    picker, and a breakdown field. Field options are the union across all loaded files."""
    fields = available_fields_union([s for _, s in versions])
    vsel = ""
    if len(versions) > 1:
        vopts = "".join(
            f'<option value="{_e(k)}"{" selected" if k == version_key else ""}>'
            f"{_e(s.source_file or s.name)}</option>"
            for k, s in versions
        )
        vsel = f"<label>Preview file: <select name=version>{vopts}</select></label> "
    # MAX_FIELDS filter rows. groups.js mounts an MS-Project-style value checklist (SFChecklist)
    # per row from the field's actual values; the chosen values are submitted as hidden value{i}
    # inputs (rendered here too, so the current selection round-trips and works without JS).
    rows = []
    for i in range(MAX_FIELDS):
        f, v = criteria[i] if i < len(criteria) else ("", "")
        selected = _criterion_value_list(v)
        hidden = "".join(f'<input type=hidden name="value{i}" value="{_e(x)}">' for x in selected)
        data_sel = _e(json.dumps(selected))
        rows.append(
            f'<div class=group-row data-row="{i}" data-selected="{data_sel}">'
            f"<select name=field class=gf-field>{_groups_field_options(fields, f)}</select> "
            f"<span class=gf-values></span><span class=gf-hidden>{hidden}</span></div>"
        )
    bsel = f"<select name=breakdown>{_groups_field_options(fields, breakdown)}</select>"
    return f"""
<div class=panel><form method=get action=/groups class=group-form data-version="{_e(version_key)}">
{vsel}
<fieldset><legend>Filter &mdash; scope every metric on every page, across all loaded files, to tasks
matching ALL rows (up to {MAX_FIELDS})</legend>
{"".join(rows)}</fieldset>
<label>Break down by: {bsel}</label>
<div class=viz-controls><button type=submit name=apply value=1>Apply to all pages</button>
<a class=btn-link href="/groups?clear=1">clear filter</a></div>
</form>
<p class=muted style="margin:.3em 0 0">Pick a field (standard or custom, e.g. <b>CA-WBS</b>), then
choose its <b>values</b> from the dropdown (checkboxes with <b>All / None</b> and a search, like MS
Project). <b>Apply</b> makes it the session-wide scope &mdash; <b>every</b> metric on <b>every</b> page,
for <b>every</b> loaded file, then runs over the matching activities until you clear it. Within a field
the chosen values are OR'd; combine up to {MAX_FIELDS} fields (AND). <b>Break down by</b> a field to
score each of its values separately (one BEI per group) on the preview file below.</p></div>
<script src="/static/groups.js"></script>"""


def _groups_breakdown_table(sub: Schedule, field: str) -> str:
    """One row per distinct value of ``field`` in ``sub`` — population, % complete, and BEI."""
    groups = group_values(sub, field)
    if not groups:
        return (
            f"<div class=panel><h3>Breakdown by {_e(field)}</h3>"
            f"<p class=muted>No activities in scope carry a value for this field.</p></div>"
        )
    limit = 200
    shown = list(groups.items())[:limit]
    rows = []
    for value, uids in shown:
        group = filter_schedule(sub, [(field, value)])
        tasks = non_summary(group)
        total = len(tasks) or 1
        complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
        bei = compute_bei(group)
        bei_cell = f"{round(bei.value, 2)}" if bei.population else "<span class=muted>—</span>"
        rows.append(
            f"<tr><td>{_e(value)}</td><td class=num>{len(uids)}</td>"
            f"<td class=num>{100.0 * complete / total:.0f}%</td>"
            f"<td class=num>{bei_cell} <span class=muted>({bei.count}/{bei.population})</span></td></tr>"
        )
    more = (
        f"<p class=muted>Showing the first {limit} of {len(groups)} values.</p>"
        if len(groups) > limit
        else ""
    )
    return (
        f"<div class=panel><h3>Breakdown by {_e(field)} &mdash; {len(groups)} value(s)</h3>"
        "<table class=card-table><tr><th scope=col>Value</th><th scope=col>Activities</th>"
        "<th scope=col>% complete</th><th scope=col>BEI</th></tr>"
        f"{''.join(rows)}</table>{more}</div>"
    )


def _groups_per_file_table(versions: list[tuple[str, Schedule]], criteria: list[Criterion]) -> str:
    """One row per loaded file: how many of its activities the active filter matches (ADR-0104)."""
    rows = []
    grand_m = grand_t = 0
    for _key, s in versions:
        sub = filter_schedule(s, criteria)
        matched, total = len(non_summary(sub)), len(non_summary(s))
        grand_m += matched
        grand_t += total
        pct = f"{100.0 * matched / total:.0f}%" if total else "&mdash;"
        rows.append(
            f"<tr><td>{_e(s.source_file or s.name)}</td><td class=num>{matched}</td>"
            f"<td class=num>{total}</td><td class=num>{pct}</td></tr>"
        )
    tpct = f"{100.0 * grand_m / grand_t:.0f}%" if grand_t else "&mdash;"
    return (
        f"<h3>Per file &mdash; {len(versions)} loaded</h3>"
        "<table class=card-table><tr><th scope=col>File</th><th scope=col>Matched</th>"
        "<th scope=col>Activities</th><th scope=col>%</th></tr>"
        f"{''.join(rows)}"
        f"<tr><td><b>All files</b></td><td class=num><b>{grand_m}</b></td>"
        f"<td class=num><b>{grand_t}</b></td><td class=num><b>{tpct}</b></td></tr></table>"
    )


def _groups_body(
    versions: list[tuple[str, Schedule]],
    version_key: str,
    sch: Schedule,
    criteria: list[Criterion],
    breakdown: str,
    applied: bool = False,
) -> str:
    """The Groups & Filters view: build a filter that scopes EVERY metric on EVERY page across ALL
    loaded files (ADR-0104), see its reach per file, and preview the scorecard/breakdown on one
    file. ``applied`` marks whether ``criteria`` is the live session scope (vs a URL preview)."""
    form = _groups_form(versions, version_key, sch, criteria, breakdown)
    sub = filter_schedule(sch, criteria) if criteria else sch

    if criteria:

        def _chip(field: str, value: str | Sequence[str]) -> str:
            vals = _criterion_value_list(value)
            shown = (
                "(populated)"
                if not vals
                else _e(", ".join(vals[:4]) + (f" +{len(vals) - 4}" if len(vals) > 4 else ""))
            )
            return f'<span class="dp-chip">{_e(field)} = {shown}</span>'

        chips = " ".join(_chip(f, v) for f, v in criteria)
        matched, total = len(non_summary(sub)), len(non_summary(sch))
        live = (
            "This filter is the session-wide scope &mdash; applied to "
            if applied
            else "Not applied yet &mdash; <b>Apply to all pages</b> to scope "
        )
        summary = (
            f"<div class=panel><h2>Active scope</h2><p>{chips}</p>"
            f"<p class=muted>{live}<b>every metric on every page</b>, for all loaded files "
            "(logical AND across rows; values OR'd within a row).</p>"
            f"<p class=muted><b>{matched}</b> of {total} activities match in the preview file.</p>"
            f"{_groups_per_file_table(versions, criteria)}</div>"
        )
    else:
        summary = (
            f"<div class=panel><h2>Active scope</h2><p class=muted>No filter &mdash; every page uses "
            f"the full schedules ({len(non_summary(sch))} activities in the preview file). Build a "
            "filter above and <b>Apply to all pages</b> to scope the whole tool.</p></div>"
        )

    if not non_summary(sub):
        scorecard = "<div class=panel><p class=muted>No activities match this filter.</p></div>"
    else:
        makeup = compute_activity_makeup(sub)
        cards = _stat_cards(
            [
                ("Activities", str(makeup.total)),
                ("Normal", str(makeup.normal)),
                ("Milestones", str(makeup.milestones)),
                ("Complete", str(makeup.complete)),
                ("In progress", str(makeup.in_progress)),
                ("Planned", str(makeup.planned)),
            ]
        )
        try:
            dcma = compute_dcma14(sub)
            table = _metric_scorecard_table(dcma)
        except CPMError as exc:
            table = f'<p class="notice err">Network for this scope cannot be solved: {_e(exc)}</p>'
        preview_name = _e(sch.source_file or sch.name)
        scorecard = (
            f"<div class=panel><h2>Preview &mdash; metric scorecard for {preview_name}</h2>"
            f"<p class=muted>The same scope drives this file's full report and every other page.</p>"
            f"{cards}{table}</div>"
        )

    breakdown_html = (
        _groups_breakdown_table(sub, breakdown)
        if breakdown and breakdown in available_fields(sch)
        else ""
    )
    return form + summary + scorecard + breakdown_html


def _evolution_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None = None,
    tier: str = "off",
) -> str:
    """The Critical-Path Evolution view (M18 item 7): a Bow-Wave-style stepper over the
    versions, showing the critical path and how it enters/leaves between versions. ``target``
    focuses a UniqueID (highlighted across every frame); zoom/pan controls scope the axis. ``tier``
    scopes the stepper to a driving-slack tier (secondary/tertiary/all) instead of the float
    critical path — the activities driving the focused UID (or the project finish)."""
    tier_opts = "".join(
        f'<option value="{v}"{" selected" if tier == v else ""}>{lbl}</option>'
        for v, lbl in [
            ("off", "Critical path"),
            ("secondary", f"Secondary tier (≤{DEFAULT_SECONDARY_MAX_DAYS}d slack)"),
            ("tertiary", f"Tertiary tier (≤{DEFAULT_TERTIARY_MAX_DAYS}d slack)"),
            ("all", "All tiers (colour-coded)"),
        ]
    )
    focus_form = f"""
<div class=panel><form method=get action=/evolution class=viz-controls>
Focus a specific activity across every version &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{'<a class=btn-link href="/evolution?target=">clear focus</a>' if target is not None else ""}
<label style="margin-left:1em">Path tier:
<select name=tier data-no-i18n onchange="this.form.submit()">{tier_opts}</select></label>
<span class=muted>critical / secondary / tertiary by driving slack to the focused UID (or the
project finish).</span>
</form></div>"""
    return (
        focus_form
        + f"""
<div class=panel><h2>Critical-Path Evolution</h2>
<p class=muted>Step through the versions (oldest first by data date) to watch the critical
path change, drawn as a <b>Gantt</b> on a date axis held fixed across every version (so the
path visibly extends as the finish slips). Bars are colored
<b class=ev-entered>green</b> for activities that <b>entered</b> the path since the prior
version, <b class=ev-stayed>grey</b> for those that <b>stayed</b>, with a &#9650; marking a
duration change; activities that <b class=ev-left>left</b> the path appear below as dashed
ghost bars at their prior position. Every entered/left activity carries a <b>reason chip</b>
explaining <b>why</b> it moved &mdash; a new task, a duration change, a logic change, a
constraint, a completion, or a slip elsewhere consuming its float (hover the chip for the
detail). The callout reports the finish movement and the schedule-optics signals, so a path
shedding work while the finish holds steady (a slip being absorbed rather than recovered) is
visible.</p>
<div class=viz-controls>
<button id=prevEvo type=button>&#9664; Prev</button>
<span id=evoLabel class=muted></span>
<button id=nextEvo type=button>Next &#9654;</button>
<button id=evoPlay type=button>&#9654; Auto-play</button>
<label class=muted style="margin-left:1em"><input type=checkbox id=evoHideDone> hide completed</label>
</div>
<div class=viz-controls>
<span class=muted>Zoom the date axis:</span>
<button id=evoZoomOut type=button title="zoom out">&minus;</button>
<button id=evoZoomIn type=button title="zoom in">&plus;</button>
<button id=evoPanL type=button title="pan earlier">&#9664;</button>
<button id=evoPanR type=button title="pan later">&#9654;</button>
<button id=evoZoomReset type=button>reset</button>
</div>
<div class=viz-controls>
<label>Filter the path:
<select id=evoFilterMode>
<option value=none selected>none &mdash; whole critical path</option>
<option value=driving>driving path to the focused UID</option>
<option value=version>track one version's path</option>
<option value=movement>entered / left / stayed</option>
<option value=search>name / UID search</option>
</select></label>
<select id=evoFilterVersion style="display:none"></select>
<span id=evoFilterMovement style="display:none">
<label><input type=checkbox class=evoMove value=entered checked> entered</label>
<label><input type=checkbox class=evoMove value=stayed checked> stayed</label>
<label><input type=checkbox class=evoMove value=left checked> left</label>
</span>
<input id=evoFilterText type=search placeholder="name or UID" style="display:none">
<span id=evoFilterNote class=muted></span>
</div>
<p class=muted style="margin:.2em 0">Each row carries its grid columns &mdash; <b>%&nbsp;complete</b>,
<b>duration</b> (working days), <b>start</b> and <b>finish</b> &mdash; beside the bar.
Use <b>Focus</b> above to highlight one activity across every version.</p>
<div id=evoChart data-target="{target if target is not None else ""}"
data-tier="{tier}"></div></div>
<script src="/static/path_evolution.js"></script>"""
        + _counterfactual_panel(schedules, cpms, target)
    )


def _counterfactual_panel(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None
) -> str:
    """The 'what-if' panel for the latest version pair: revert the duration/logic/constraint
    changes that took non-completed activities off the critical path, and report what the
    finish (and the target UID) would have been — isolating slip removed by changes vs progress."""
    if len(schedules) < 2:
        return ""
    pc = compute_path_counterfactual(
        schedules[-2], schedules[-1], cpms[-2], cpms[-1], target_uid=target
    )
    return _render_counterfactual(pc)


def _render_counterfactual(pc: PathCounterfactual | None) -> str:
    """Render the counterfactual panel from a computed result (split out for direct testing)."""
    intro = """
<div class=panel><h2>What-if: work removed from the critical path</h2>
<p class=muted>Between the latest two versions, some activities leave the critical (driving)
path. A <b>completed</b> activity leaving is real progress (excluded here). An unchanged
activity leaving <b>gained float</b> &mdash; a slip elsewhere made another chain longer, so this
one is no longer on the longest path (nothing about it changed). But an activity that leaves
because <b>its own remaining duration was cut, a logic link was removed, or a constraint was
dropped</b> can make a slipping finish look recovered. Below, those specific changes (on
non-completed activities) are reverted to their prior values and the schedule re-run &mdash; the
gap is schedule time the <b>changes</b>, not progress, removed from the path.</p>"""
    if pc is None:
        return (
            intro + "<p class=muted>No non-completed activity left the critical path between the "
            "last two versions &mdash; nothing to revert.</p></div>"
        )

    def _delta(days: int) -> str:
        if days > 0:
            return f"<b class=fail>+{days} day(s) later</b>"
        if days < 0:
            return f"<b class=pass>{days} day(s) earlier</b>"
        return "<b>no change</b>"

    rows = "".join(
        f"<tr><td>{r.uid}</td><td>{_e(r.name)}</td><td>{_e(r.reason)}</td>"
        f"<td>{_e('; '.join(r.changes))}</td></tr>"
        for r in pc.reverted
    )
    body = [intro]
    if pc.reverted:
        finish_line = (
            f"Computed finish is <b>{_e(pc.actual_finish)}</b>; had these "
            f"{len(pc.reverted)} change(s) not been made it would be "
            f"<b>{_e(pc.counterfactual_finish)}</b> ({_delta(pc.finish_delta_days)})."
        )
        if pc.uncomputable:
            finish_line = (
                "Reverting these changes produced an unsolvable network (a logic cycle), so the "
                "counterfactual finish cannot be computed; the changed activities are named below."
            )
        body.append(f"<p>{finish_line}</p>")
        if pc.target_uid is not None and pc.target_delta_days is not None:
            body.append(
                f"<p>Target activity <b>UID {pc.target_uid}: {_e(pc.target_name or '')}</b> "
                f"finishes <b>{_e(pc.target_actual_finish or '')}</b> now; without the changes "
                f"it would finish <b>{_e(pc.target_counterfactual_finish or '')}</b> "
                f"({_delta(pc.target_delta_days)}).</p>"
            )
        elif pc.target_uid is not None:
            body.append(
                f"<p class=muted>Target UID {pc.target_uid} is not in both the current and "
                "counterfactual networks, so its individual impact is not shown.</p>"
            )
        body.append(
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th><th scope=col>Why it left</th>"
            f"<th scope=col>Change reverted</th></tr>{rows}</table>"
        )
    if pc.gained_float:
        names = "; ".join(f"{g.name} (UID {g.uid})" for g in pc.gained_float)
        body.append(
            f"<p class=muted><b>Gained float (no change to revert):</b> {_e(names)} left the path "
            "because a slip elsewhere lengthened another chain, freeing this one's float &mdash; "
            "not because the activity itself was altered.</p>"
        )
    body.append("</div>")
    return "".join(body)


def _evolution_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None
) -> dict[str, object]:
    """JSON for the critical-path evolution Gantt stepper: per-version snapshots with each
    critical activity's bar geometry (start/finish), the entered/left attribution (the reason
    WHY each entered or left the path), and a date axis LOCKED across every version so bars
    stay comparable frame to frame. ``target`` (if set) is echoed so the view can highlight
    that UniqueID's row in every frame."""
    evolution = compute_path_evolution(schedules, cpms)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = offset_to_datetime(sch.project_start, timing.early_start, sch.calendar).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def is_complete_in(idx: int, uid: int) -> bool:
        """Robust complete flag (ADR-0051: ≥100% OR an actual finish) for ``uid`` in version
        ``idx`` — False when the activity is absent from that version."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        return task is not None and (task.is_complete or task.actual_finish is not None)

    def stats(idx: int, uid: int) -> dict[str, object]:
        """Per-activity grid columns for the row: %complete, duration (working days), and the
        robust complete flag. Empty when the activity is absent from version ``idx`` (e.g. a
        removed activity shown at its prior position)."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": is_complete_in(idx, uid),
        }

    def path_to_target(idx: int) -> list[int]:
        """When a UID is focused, the activities that DRIVE it in version ``idx`` — the target
        plus its transitive predecessors — so the "driving path to focus" filter can scope the
        Gantt to just the chain feeding the focused activity. Empty when no target is set or it
        is absent from this version."""
        if target is None or not (0 <= idx < len(schedules)) or target not in by_id[idx]:
            return []
        preds_of: dict[int, list[int]] = {}
        for r in schedules[idx].relationships:
            preds_of.setdefault(r.successor_id, []).append(r.predecessor_id)
        seen, stack = {target}, [target]
        while stack:
            for p in preds_of.get(stack.pop(), ()):
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return sorted(seen)

    snapshots: list[dict[str, object]] = []
    for i, s in enumerate(evolution.snapshots):
        names = {str(uid): by_id[i][uid].name for uid in s.critical if uid in by_id[i]}
        if i > 0:
            for uid in s.left:
                if uid in by_id[i - 1]:
                    names[str(uid)] = by_id[i - 1][uid].name
        entered_reason = {c.uid: c for c in s.entered_changes}
        dur_changed = set(s.duration_changed)
        critical_rows: list[dict[str, object]] = []
        for uid in s.critical:
            start, finish = bar(i, uid)
            change = entered_reason.get(uid)
            critical_rows.append(
                {
                    "uid": uid,
                    "name": names.get(str(uid), f"UID {uid}"),
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered_reason,
                    "duration_changed": uid in dur_changed,
                    "reason": change.reason if change is not None else None,
                    "detail": change.detail if change is not None else None,
                    **stats(i, uid),
                }
            )
        critical_rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for c in s.left_changes:
            start, finish = bar(i - 1, c.uid) if i > 0 else (None, None)
            # left activities are drawn at their PRIOR-version position, so %complete/duration
            # read from that version (i - 1); the complete flag is the CURRENT status, so an
            # activity that left *because it completed* hides under the hide-completed toggle.
            grid = stats(i - 1, c.uid)
            grid["complete"] = is_complete_in(i, c.uid)
            left_rows.append(
                {
                    "uid": c.uid,
                    "name": c.name,
                    "start": start,
                    "finish": finish,
                    "reason": c.reason,
                    "detail": c.detail,
                    **grid,
                }
            )
        snapshots.append(
            {
                "label": s.label,
                "status_date": s.status_date,
                "project_finish": s.project_finish,
                "finish_delta_days": s.finish_delta_days,
                "critical": list(s.critical),
                "entered": list(s.entered),
                "left": list(s.left),
                "duration_changed": list(s.duration_changed),
                "shortened_on_path": list(s.shortened_on_path),
                "removed_logic_count": s.removed_logic_count,
                "names": names,
                "critical_rows": critical_rows,
                "left_rows": left_rows,
                "path_to_target": path_to_target(i),
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target}


#: Evolution tier modes → the driving-slack tiers (ADR-0011) to include. "off" = the float
#: critical-path view (the page default, with its rich entered/left attribution).
_EVO_TIER_LABEL = {
    PathTier.DRIVING: "driving",
    PathTier.SECONDARY: "secondary",
    PathTier.TERTIARY: "tertiary",
}
_EVO_TIER_SELECT: dict[str, set[PathTier]] = {
    "critical": {PathTier.DRIVING},
    "secondary": {PathTier.SECONDARY},
    "tertiary": {PathTier.TERTIARY},
    "all": {PathTier.DRIVING, PathTier.SECONDARY, PathTier.TERTIARY},
}


def _project_finish_uid(sch: Schedule, cpm: CPMResult) -> int | None:
    """The non-summary activity that finishes last (drives the project finish) — the default focus
    for the tiered driving-path view when no target UID is pinned."""
    best_uid: int | None = None
    best: int | None = None
    for t in sch.tasks:
        if t.is_summary:
            continue
        tm = cpm.timings.get(t.unique_id)
        if tm is None:
            continue
        if best is None or tm.early_finish > best:
            best, best_uid = tm.early_finish, t.unique_id
    return best_uid


def _evolution_tier_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None, tier: str
) -> dict[str, object]:
    """Critical-Path Evolution scoped to a DRIVING-SLACK tier (ADR-0011) instead of the float
    critical path: per version, classify the activities driving the focus (the pinned ``target``,
    else that version's project-finish activity) into driving (0 days) / secondary (<=10 days) /
    tertiary (<=20 days), and show ONLY the chosen tier (``all`` shows all three, the client colours
    them by tier). Same payload shape as :func:`_evolution_data` so the Gantt stepper renders it
    unchanged; ``entered`` / ``left`` are by set difference of the tier membership across versions,
    and the version framing (label / data date / project finish) is reused from the evolution."""
    selected = _EVO_TIER_SELECT.get(tier, _EVO_TIER_SELECT["critical"])
    evolution = compute_path_evolution(schedules, cpms)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = offset_to_datetime(sch.project_start, timing.early_start, sch.calendar).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def grid(idx: int, uid: int) -> dict[str, object]:
        task = by_id[idx].get(uid) if 0 <= idx < len(by_id) else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": task.is_complete or task.actual_finish is not None,
        }

    # per-version tier membership: uid -> tier label, for the selected tiers only
    members: list[dict[int, str]] = []
    for i, sch in enumerate(schedules):
        focus = (
            target
            if (target is not None and target in by_id[i])
            else _project_finish_uid(sch, cpms[i])
        )
        m: dict[int, str] = {}
        if focus is not None:
            try:
                results = compute_driving_slack(sch, focus, cpm_result=cpms[i])
            except (KeyError, ValueError):
                results = {}
            for uid, r in results.items():
                if r.tier in selected:
                    m[uid] = _EVO_TIER_LABEL[r.tier]
        members.append(m)

    snapshots: list[dict[str, object]] = []
    prior: set[int] = set()
    for i, snap in enumerate(evolution.snapshots):
        cur = set(members[i])
        entered = (cur - prior) if i > 0 else set()
        left = (prior - cur) if i > 0 else set()
        rows: list[dict[str, object]] = []
        for uid in cur:
            start, finish = bar(i, uid)
            task = by_id[i].get(uid)
            rows.append(
                {
                    "uid": uid,
                    "name": task.name if task is not None else f"UID {uid}",
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered,
                    "duration_changed": False,
                    "reason": None,
                    "detail": None,
                    "tier": members[i][uid],
                    **grid(i, uid),
                }
            )
        rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for uid in sorted(left):
            start, finish = bar(i - 1, uid) if i > 0 else (None, None)
            g = grid(i - 1, uid)
            now = by_id[i].get(uid)
            g["complete"] = bool(now and (now.is_complete or now.actual_finish is not None))
            name = by_id[i - 1][uid].name if (i > 0 and uid in by_id[i - 1]) else f"UID {uid}"
            left_rows.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "reason": None,
                    "detail": None,
                    "tier": members[i - 1].get(uid) if i > 0 else None,
                    **g,
                }
            )
        prior = cur
        snapshots.append(
            {
                "label": snap.label,
                "status_date": snap.status_date,
                "project_finish": snap.project_finish,
                "finish_delta_days": snap.finish_delta_days,
                "critical": sorted(cur),
                "entered": sorted(entered),
                "left": sorted(left),
                "duration_changed": [],
                "shortened_on_path": [],
                "removed_logic_count": 0,
                "names": {str(u): (by_id[i][u].name if u in by_id[i] else f"UID {u}") for u in cur},
                "critical_rows": rows,
                "left_rows": left_rows,
                "path_to_target": [],
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target, "tier": tier}


def _dashboard_data(st: SessionState) -> dict[str, object]:
    """Per-loaded-schedule health snapshot for the Dashboard cards: status mix, critical
    exposure, computed finish vs baseline, and the DCMA-14 verdicts. Reuses the cached
    per-schedule analysis (one CPM each); an unschedulable file degrades to a flagged card."""
    cards: list[dict[str, object]] = []
    for key, sch in st.ordered_versions():  # earliest -> latest data date
        scoped = st.scope(sch)  # the active filter applies to the dashboard cards too
        card: dict[str, object] = {
            "key": key,
            "name": sch.name,
            "source_file": sch.source_file,
            "activities": len(non_summary(scoped)),
            "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        }
        try:
            an = st.analysis_for(key, sch)
        except CPMError:
            card["solvable"] = False
            cards.append(card)
            continue
        makeup = compute_activity_makeup(scoped)
        total = makeup.complete + makeup.in_progress + makeup.planned
        cpm_finish = offset_to_datetime(
            scoped.project_start, an.cpm.project_finish, scoped.calendar
        ).date()
        baseline_dates = [
            t.baseline_finish for t in non_summary(scoped) if t.baseline_finish is not None
        ]
        baseline_finish = max(baseline_dates).date() if baseline_dates else None
        fb0 = an.float_bands["float_total_0"]
        card.update(
            {
                "solvable": True,
                "status_mix": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                },
                "percent_complete": round(100 * makeup.complete / total, 1) if total else 0.0,
                "critical_count": fb0.count,
                "critical_pct": round(fb0.value, 1),
                "cpm_finish": cpm_finish.isoformat(),
                "baseline_finish": baseline_finish.isoformat() if baseline_finish else None,
                # positive = computed finish later than baseline (a slip)
                "finish_delta_days": (cpm_finish - baseline_finish).days
                if baseline_finish
                else None,
                "dcma": [
                    {"id": c.metric_id, "name": c.name, "status": str(c.status)}
                    for c in an.audit.checks
                ],
            }
        )
        cards.append(card)
    return {"cards": cards}


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
        head = (
            "<tr>"
            + "".join(f"<th scope=col>{_e(h)}</th>" for h in table.headers)
            + "<th scope=col>Citation</th></tr>"
        )
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_e(cell)}</td>" for cell in row)
        + f"<td class=cite>{_e(_cite_tag(cites))}</td></tr>"
        for row, cites in zip(table.rows, table.row_citations, strict=True)
    )
    return f"<table class=brief-table>{head}{body}</table>"


def _briefing_body(briefing: ExecutiveBriefing) -> str:
    """Render the leadership Executive Briefing (ADR-0121): a metadata header + a verdict banner,
    then the numbered forensic sections (Bottom Line, Performance, Critical Path Then & Now, Health
    Dashboard, Risks & Opportunities, Recommended Actions, How to Verify) as a single continuous
    document. Every statement and every table row carries its file + UID + task citation (§6)."""
    verdict_slug = briefing.verdict.lower().replace(" ", "-").replace("/", "")
    meta = "".join(
        f"<tr><th scope=row>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in briefing.meta_rows
    )
    banner = "".join(
        f"<div class=brief-stat><span class=brief-stat-label>{_e(k)}</span>"
        f"<span class=brief-stat-value>{_e(v)}</span></div>"
        for k, v in briefing.banner
    )
    parts = [
        '<div class="panel brief-doc">',
        f"<h2>{_e(briefing.title)}</h2>",
        f"<p class=brief-subtitle>{_e(briefing.subtitle)}</p>",
        f"<table class=brief-meta>{meta}</table>",
        f'<div class="brief-banner verdict-{_e(verdict_slug)}">{banner}</div>',
        "<p class=muted>Every statement and table row cites file + UniqueID + task name. "
        'Hand-out copy: <a href="/export/docx/briefing">&#11015; Word</a> &middot; '
        '<a href="/export/xlsx/briefing">&#11015; Excel</a>.</p>',
    ]
    for section in briefing.sections:
        tag = f"h{min(section.level + 2, 6)}"
        prose = "".join(
            f"<p>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></p>"
            for s in section.statements
        )
        parts.append(
            f"<{tag} class=brief-h>{_e(section.heading)}</{tag}>"
            f"{prose}{_briefing_table_html(section)}"
        )
    parts.append("</div>")
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
    status_note = _ai_status_note(cfg)

    def sel(value: str, current: str) -> str:
        return " selected" if value == current else ""

    # When a real local backend is active and reporting installed models, the Model field is a
    # dropdown of those models (one click to pick, e.g., a purpose-built model) instead of a
    # free-text box the operator must match exactly. The configured model is always kept as a
    # (selected) option — marked if it isn't installed — so a save never silently loses it.
    real_backend = backend.name in ("ollama", "openai-compat")
    if real_backend and models:
        option_models = list(models)
        if cfg.model and not _model_installed(cfg.model, models):
            option_models = [cfg.model, *option_models]
        model_field = (
            "<select name=model id=primaryModel>"
            + "".join(
                f'<option value="{_e(m)}"{sel(m, cfg.model)}>{_e(m)}'
                f"{'' if _model_installed(m, models) else ' — not installed'}</option>"
                for m in option_models
            )
            + "</select>"
        )
    else:
        model_field = f'<input name=model id=primaryModel value="{_e(cfg.model)}">'

    # A one-click "off" switch, shown only while a real local model is active (the operator asked
    # for an explicit way to turn the AI off once it is on). It routes back to the deterministic Null
    # backend AND stops the local model, freeing its RAM/CPU without quitting the tool.
    ai_off_btn = (
        '<form action="/settings/ai-off" method=post style="margin:6px 0 2px">'
        '<button type=submit class=btn-danger title="Switch the AI back to offline deterministic '
        "mode and stop the local model now (frees its RAM and CPU). You can turn it back on here any "
        'time.">Turn the AI off &amp; stop the local model</button></form>'
        if real_backend
        else ""
    )

    return f"""
<div class=panel><h2>Local AI</h2>
<p>Active backend: <b>{_e(backend.name)}</b> &middot; installed models: {model_list}
&middot; cross-check model: <b>{second_status}</b></p>
{status_note}
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
<p>Model: {model_field}</p>
<p>Generation timeout (seconds):
<input name=gen_timeout type=number min=30 max=3600 step=10 value="{_e(int(cfg.gen_timeout))}"
 title="How long a single answer may take. Raise it for a big, slow model (e.g. llama3.1:70b) so it can finish."></p>
<p>Ollama endpoint (loopback only):
<input name=endpoint size=28 value="{_e(cfg.endpoint)}"
 title="Ollama defaults to http://127.0.0.1:11434"></p>
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
<select name=second_backend id=secondBackend>
<option value=none{sel("none", cfg.second_backend)}>Off</option>
<option value=ollama{sel("ollama", cfg.second_backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.second_backend)}>OpenAI-compatible (local)</option>
</select>
 model id: <input name=second_model id=secondModel size=20 value="{_e(cfg.second_model)}"
 title="Turning the cross-check on auto-fills this with the primary model id; edit it to use a
different second model (e.g. qwen2.5:14b). Blank = the server's default/loaded model."></p>
<input type=submit value="Save"></form>
{ai_off_btn}
<p class=muted>The tool never sends schedule data off this machine while CLASSIFIED. Cloud is only
reachable after you explicitly switch to UNCLASSIFIED, and a persistent banner names the endpoint.
Either answer mode is prose-only: the cited facts shown with each answer are always engine-computed.
With a cross-check model on, both local models answer every question independently and the engine
compares their figures deterministically — agreement is corroboration, the citations stay the
ground truth.</p>
<details class=setup-guide><summary>How to download &amp; set up a local model (Llama&nbsp;3.1:8b and others)</summary>
<ol>
<li><b>Install Ollama</b> (one time). In your browser, go to <code>ollama.com/download</code> and run
the installer — Windows, macOS, or Linux. This is the only step that uses the internet.</li>
<li><b>Download the standard model.</b> Open a terminal / command prompt and run:
<br><code>ollama pull llama3.1:8b</code></li>
<li><b>Pick a model that fits your computer's memory (RAM):</b>
<ul>
<li>8&nbsp;GB &rarr; <code>ollama pull llama3.2:3b</code> (small, quick)</li>
<li>16&nbsp;GB &rarr; <code>ollama pull llama3.1:8b</code> (the tool's standard — balanced)</li>
<li>16&ndash;32&nbsp;GB &rarr; <code>ollama pull qwen2.5:14b</code> (noticeably smarter)</li>
<li>32&nbsp;GB+ &rarr; <code>ollama pull qwen2.5:32b</code> &middot; 64&nbsp;GB+ &rarr;
<code>ollama pull llama3.1:70b</code> (most powerful, slowest)</li>
</ul></li>
<li><b>Point the tool at it.</b> Set <i>Backend</i> = <i>Ollama (local)</i> above, choose the model
in <i>Model</i>, and click <b>Save</b>. The tool talks to Ollama only on
<code>127.0.0.1</code> — nothing leaves the machine.</li>
<li><b>(Optional) cross-check second model.</b> Pull a second model
(e.g. <code>ollama pull qwen2.5:14b</code>), set <i>Cross-check second model</i> to
<i>Ollama (local)</i> — the model id auto-fills with the primary; change it to the second model
so both answer every question and the engine compares their figures.</li>
<li><b>If a big model runs slowly,</b> raise <i>Generation timeout</i> above (it defaults to
900&nbsp;seconds). The full walk-through lives in <code>docs/CONNECT-A-BIGGER-AI-MODEL.md</code>.</li>
</ol>
<p class=muted style="margin-top:10px"><b>About Ollama running:</b> this tool starts Ollama only
when you turn the <i>Ollama (local)</i> backend on here, and when you close the tool it unloads the
model and <b>stops the Ollama server</b> (even one that was already running). If you installed
Ollama on Windows, its desktop app (<code>ollama&nbsp;app.exe</code>) <b>auto-starts again at your
next login</b> and brings the server back. To make Ollama run <i>only</i> with the tool, turn that
auto-start off once: <b>right-click the Ollama icon in the system tray &rarr; Settings &rarr;
uncheck &ldquo;Run at login&rdquo;</b> (or Windows <b>Settings &rarr; Apps &rarr; Startup &rarr;</b>
switch <b>Ollama</b> off), then sign out and back in.</p>
</details></div>
<script src="/static/settings.js"></script>"""


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
