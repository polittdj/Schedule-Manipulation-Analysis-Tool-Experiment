"""Session state, caches, and the per-schedule analysis chokepoint (ADR-0297 phase 1).

Extracted VERBATIM from ``web/app.py`` — the split is behaviour-free: every class, function,
constant, docstring and comment below is byte-for-byte the monolith's, only the module boundary
is new. ``web.app`` re-exports every public-to-tests name, so imports and monkeypatch targets
keep working; tests that patch the engine callables *called from this module* patch THIS module.

Contents: ``_LRUCache`` + the cache caps - ``_Flash`` - ``_Analysis`` / ``_DashCore`` /
``_dash_core`` - ``_compute_analysis`` (the single CPM pass every view reuses) - ``UnifiedRisk`` -
``SessionState`` (the in-memory, per-process session) - ``_iso_date`` / ``_activity_rows`` (the
grid rows ``_Analysis`` carries).
"""

from __future__ import annotations

import datetime as dt
import itertools
import threading
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar, cast

from schedule_forensics.ai import (
    AIBackend,
    AIConfig,
)
from schedule_forensics.ai.citations import Narrative
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.engine import (
    analyze_floats,
    audit_schedule,
    compute_cpm,
    recommend,
)
from schedule_forensics.engine.cache import get_default_cache
from schedule_forensics.engine.cpm import (
    CPMResult,
)
from schedule_forensics.engine.dcma_audit import ScheduleAudit
from schedule_forensics.engine.grouping import (
    Criterion,
    filter_to_uids,
    select,
    with_ancestors,
)
from schedule_forensics.engine.margin_dashboard import (
    GOLD_RULE_DAYS_PER_YEAR,
)
from schedule_forensics.engine.margin_guideline import (
    DEFAULT_CORRECTIVE_PCT,
    DEFAULT_WATCH_PCT,
    FIG_5_30_DEFAULT_RATES,
)
from schedule_forensics.engine.memory import (
    DEFAULT_WARN_BYTES,
)
from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_completion_performance,
    compute_float_bands,
)
from schedule_forensics.engine.metrics._common import (
    MetricResult,
    is_effective_critical,
)
from schedule_forensics.engine.msp_field_resolver import FieldValue
from schedule_forensics.engine.msp_filters import select as _select_saved
from schedule_forensics.engine.path_trace import subschedule_to_target
from schedule_forensics.engine.projects import (
    IngestRecord,
    Project,
    group_into_projects,
)
from schedule_forensics.engine.recommendations import (
    Finding,
)
from schedule_forensics.engine.sra import (
    ConditionalBranch,
    ProbabilisticBranch,
    RiskFactorTable,
)
from schedule_forensics.engine.summary import VersionSummary, compute_summary
from schedule_forensics.engine.trend import (
    order_versions,
)
from schedule_forensics.model.saved_view import SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


@dataclass(frozen=True)
class _Flash:
    """A one-shot import result message shown on the next dashboard render."""

    accepted: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    #: non-blocking grouping notices (v4): folders with disagreeing internal titles, files grouped
    #: by filename needing attention, or a data-date tie broken by last-modified time.
    notices: tuple[str, ...] = ()


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
    #: the exact (scoped) schedule every field above was computed FROM (ADR-0263): callers that
    #: need the schedule paired with this analysis use THIS reference instead of re-resolving
    #: st.scope(raw) in a second lock window — a concurrent filter/target change between the two
    #: windows could otherwise pair an old-epoch analysis with a new-epoch population.
    scoped: Schedule


@dataclass(frozen=True)
class _DashCore:
    """The three dashboard-card fields projected out of a full :class:`_Analysis` (ADR-0281).

    The Dashboard renders only 3 of ``_Analysis``'s 8 fields — the network finish, the zero-float
    band, and the DCMA-14 verdicts (see :func:`_dashboard_data`). Building a full analysis per
    loaded version just to read those three thrashed the 48-entry analysis LRU at N>48 (every
    refresh recomputed every version — the recorded ~65x cliff at ``_ANALYSIS_CACHE_MAX``). This
    tier stores ONLY the projected primitives the card needs — never the heavy engine objects (a
    ``MetricResult`` / ``AuditCheck`` pins citation tuples) — so an entry is ~1 KiB and a
    100-version portfolio's dashboard tier stays trivial next to the full-analysis cache."""

    project_finish: int  # cpm.project_finish (network-finish working-minute offset)
    critical_count: int  # float_bands["float_total_0"].count
    critical_pct: float  # float_bands["float_total_0"].value (rounded at render, unchanged)
    #: (metric_id, name, str(status)) per DCMA-14 check — exactly the card's ``dcma`` projection.
    dcma: tuple[tuple[str, str, str], ...]


def _dash_core(cpm: CPMResult, audit: ScheduleAudit, fb0: MetricResult) -> _DashCore:
    """Project the three dashboard-card fields from the engine results — the single source of
    truth for both the from-full-analysis and the compute-only tiers of ``dashboard_core_for``."""
    return _DashCore(
        project_finish=cpm.project_finish,
        critical_count=fb0.count,
        critical_pct=fb0.value,
        dcma=tuple((c.metric_id, c.name, str(c.status)) for c in audit.checks),
    )


def _compute_analysis(
    sch: Schedule,
    cpm: CPMResult | None = None,
    *,
    dcma_acumen_parity: bool = False,
) -> _Analysis:
    """Run the engine once for ``sch`` (a single ``compute_cpm``, reused everywhere).

    ``cpm`` lets a caller hand in an already-cached solve of THIS exact schedule (the ADR-0261
    P2 tier) so the network is never solved twice for one epoch — never a different input.
    ``dcma_acumen_parity`` forwards the single Acumen-parity DCMA mode (ADR-0280); it is part of the
    analysis cache signature so toggling it re-keys, never serving a stale audit."""
    cpm = cpm if cpm is not None else compute_cpm(sch)
    # ADR-0281: compute each deterministic dependency ONCE and thread it through the recommender and
    # the narrative — they used to each recompute the DCMA audit, baseline compliance, and findings
    # (3x audit / 3x compliance / 2x recommend per cold analysis).
    audit = audit_schedule(sch, cpm, acumen_parity=dcma_acumen_parity)
    compliance = compute_baseline_compliance(sch, cpm)
    # ADR-0282 Option A (ADR-0285): the findings follow the DISPLAYED audit — so when Acumen-parity
    # mode is on, the risk/concern findings, the narrative and the briefing all derive from the
    # parity
    # audit and agree with the ribbon (no more "the card says PASS but a finding says FAIL"). The
    # precomputed audit is the parity-aware one already computed above, so it is reused in BOTH
    # modes
    # (1x audit either way). Default mode is byte-identical to before. (Baseline compliance is
    # mode-independent — one Acumen-validated definition — so `compliance` is reused unchanged.)
    findings = recommend(
        sch,
        current_cpm=cpm,
        precomputed_audit=audit,
        precomputed_compliance=compliance,
        acumen_parity=dcma_acumen_parity,
    )
    return _Analysis(
        scoped=sch,
        cpm=cpm,
        audit=audit,
        compliance=compliance,
        float_bands=compute_float_bands(sch, cpm),
        completion=compute_completion_performance(sch),
        findings=findings,
        # the cached narrative is always the deterministic (NullBackend) one; a real
        # session-selected backend rephrases it per request via _polished_narrative
        # (citations re-attached, figures re-verified — see ai.citations.reattach).
        narrative=build_narrative(sch, current_cpm=cpm, precomputed_findings=findings),
        activity_rows=_activity_rows(sch, cpm),
    )


@dataclass(frozen=True)
class UnifiedRisk:
    """One operator-entered risk/opportunity that feeds BOTH SRA models.

    The operator enters a risk ONCE. It carries two magnitudes for the same event: an additive
    ``impact_days`` (the SSI model) and a multiplicative ``impact_pct`` uplift (the legacy model;
    ``20`` => x1.20). Typing one auto-derives the other from the affected tasks' remaining duration
    (client-side ``sra_risk.js``; the server mirrors it for the JS-off / load path). A field the
    operator set explicitly is *locked* (``days_locked`` / ``pct_locked``) and used verbatim for
    that
    model; the unlocked one is the derived value. At the web boundary this record is turned into the
    engine's frozen :class:`ScheduleRisk` (from ``impact_days``) and :class:`RiskEvent` (from
    ``impact_pct``) — the engine and its byte-frozen parity tests are untouched.
    """

    id: str
    name: str
    probability: float  # 0..1
    affected: tuple[int, ...]
    impact_days: float  # additive working days (>=0 risk, <0 opportunity) — the SSI magnitude
    impact_pct: (
        float  # multiplicative % uplift (20 => x1.20; <0 opportunity) -- the legacy magnitude
    )
    days_locked: bool = False  # the operator set days explicitly → use verbatim for the SSI model
    pct_locked: bool = False  # the operator set % explicitly → use verbatim for the legacy model
    consequence_rating: int | None = None  # 1..5 for the 5x5 matrix; None auto-derives from days


_V = TypeVar("_V")

#: Max full analyses / polished narratives kept resident before the least-recently-used is evicted
#: (audit #4). A full ``_Analysis`` is heavy (~6 KiB/task; a portfolio of 100 large versions would
#: otherwise pin >1 GiB); the summary tier (``summaries``) carries portfolio scale, so this cap
#: applies only to the expensive detailed caches. Generous enough that any realistic multi-version
#: comparison never evicts — an evicted entry simply recomputes byte-identically, so the cap only
#: trades memory for occasional recompute and can never change a computed number.
_ANALYSIS_CACHE_MAX = 48
#: Cap for the CPM-solve tier (ADR-0292). Entries are ~641 KiB vs ~7.2 MiB for a full analysis, so a
#: larger cap costs far less memory while keeping more versions cheap to re-serve after an analysis
#: eviction. 144 x 641 KiB is ~90 MiB worst case.
_CPM_CACHE_MAX = _ANALYSIS_CACHE_MAX * 3

#: ADR-0258: sentinel population id for the pooled title-less loose files — stable, storable and
#: selectable like a real Project pid, and never colliding with the engine's pid prefixes
#: (``folder:`` / ``title:`` / ``file:``).
_UNTITLED_PID = "untitled:"


# ── Role-selection front page (v4 F4, ADR-0255) ────────────────────────────────────────────
# Five audience roles, each a CURATED ENTRY POINT into pages that already exist. Selecting a
# role is pure wayfinding: it reorders/emphasizes (a "Start here" strip on the home page, a
# highlight on the role's chapters in the nav) and picks the post-upload landing page — it
# NEVER hides a page, never changes a computation, a default parameter, or a number (Law 2:
# every figure is identical under every role). The mapping is static, committed, and cited to
# the spine's own pages; "Show everything" (no role) is byte-identical to the pre-F4 behavior.


@dataclass(frozen=True)
class _Role:
    """One front-page audience role: a label, a one-line who-this-is-for, the post-upload
    landing route (None = inherit the default upload destination), and the "Start here" cards
    as (title, spine route, one-line why)."""

    id: str
    label: str
    blurb: str
    landing: str | None
    cards: tuple[tuple[str, str, str], ...]


_ROLES: tuple[_Role, ...] = (
    _Role(
        "scheduler",
        "Scheduler / Planner",
        "Builds and maintains the IMS — is the schedule sound enough to trust?",
        "/ribbon",
        (
            ("Schedule Quality Ribbon", "/ribbon", "The Fuse-parity quality read at a glance."),
            ("Schedule Integrity", "/integrity", "Logic, constraints, and structure health."),
            ("Where we stand (DCMA-14)", "@analysis", "The full report with the DCMA-14 audit."),
            ("Path Analysis", "/path", "What drives the finish, SSI-style."),
            ("Groups & Filters", "/groups", "Scope every metric to the population you manage."),
        ),
    ),
    _Role(
        "pm",
        "Program / Project Manager",
        "Owns the decisions — margin, forecast, and the portfolio picture.",
        "/portfolio",
        (
            ("Portfolio", "/portfolio", "Every project across the portfolio, at a glance."),
            ("Mission Control", "/mission", "The whole session on one wall."),
            ("Margin Dashboard", "/margin", "Burn-down, the Fig 5-30 band, and sufficiency."),
            ("Forecast", "/forecast", "Every finish forecast side by side."),
            ("Executive Briefing", "/briefing", "The cited story, ready to present."),
        ),
    ),
    _Role(
        "analyst",
        "Forensic Analyst",
        "Hunts manipulation — how the schedule moved and what changed it.",
        None,  # inherit the default (the analysis report / dashboard) — today's behavior
        (
            ("Where we stand", "@analysis", "The full per-schedule forensic report."),
            ("Trend", "/trend", "Every metric across every loaded version."),
            ("Critical-Path Evolution", "/evolution", "Whether the path holds or thrashes."),
            ("Bow Wave / CEI", "/cei", "Work pushed ahead of the data date."),
            ("Compare", "/compare", "What changed between the two most recent versions."),
        ),
    ),
    _Role(
        "auditor",
        "Auditor (DCMA / IG)",
        "Checks compliance — the standards, the scorecards, the definitions.",
        "/standards",
        (
            ("Standards & Execution Indices", "/standards", "SEM/SSI families, Fuse-validated."),
            ("Schedule Quality Ribbon", "/ribbon", "DCMA-14 and the quality gates."),
            ("Assessment Scorecards", "/scorecards", "The graded assessment rollup."),
            ("Metric Dictionary", "/help", "Every metric's definition, formula, and source."),
        ),
    ),
    _Role(
        "counsel",
        "Counsel / Testifying Expert",
        "Builds the record — cited narrative, exhibits, and the delta story.",
        "/briefing",
        (
            ("Executive Briefing", "/briefing", "The cited narrative, figure-gated."),
            ("Diagnostic Brief", "/brief", "The engine's findings with citations."),
            ("Compare", "/compare", "The version-to-version delta record."),
            ("Path Analysis", "/path", "The driving chain behind the finish date."),
        ),
    ),
)

_ROLE_BY_ID: dict[str, _Role] = {r.id: r for r in _ROLES}


class _LRUCache(OrderedDict[str, _V]):
    """A count-bounded, access-ordered LRU over string keys (std-lib only — no ``cachetools``).

    Used ONLY for value caches whose entries recompute IDENTICALLY on a miss (the detailed
    ``analyses`` / ``polished`` caches), so bounding memory never changes any computed output.
    Plain dict operations still work (``__setitem__`` / ``in`` / ``clear`` / ``== {}``, which the
    filter/wipe paths and tests rely on); production reads/writes go through :meth:`get_lru` /
    :meth:`put` for the LRU discipline (most-recently-used survives, least-recently-used evicts).
    """

    def __init__(self, maxsize: int) -> None:
        super().__init__()
        self._maxsize = maxsize

    def get_lru(self, key: str) -> _V | None:
        """Return the cached value and mark it most-recently-used, or ``None`` on a miss."""
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key: str, value: _V) -> None:
        """Insert/refresh ``key`` as most-recently-used, evicting the LRU entry over the cap."""
        self[key] = value
        self.move_to_end(key)
        while len(self) > self._maxsize:
            self.popitem(last=False)


@dataclass
class SessionState:
    """In-memory, local-only session: loaded schedules (by name) + AI config. No disk
    persistence."""

    schedules: dict[str, Schedule] = field(default_factory=dict)
    # ingestion origin per loaded key (v4 grouped ingestion): key -> (top folder name or None for a
    # loose file, browser last-modified epoch-ms or None). Feeds engine.projects grouping; the
    # Schedule itself carries the real document Title (``project_title``). Cleared on wipe.
    file_meta: dict[str, tuple[str | None, float | None]] = field(default_factory=dict)
    ai_config: AIConfig = field(default_factory=AIConfig)
    flash: _Flash | None = None  # transient import feedback, consumed on the next home() render
    # per-schedule analysis cache (key -> (schedule, analysis)); identity-checked so a re-upload
    # under the same key recomputes. Bounded by the loaded-schedule count; cleared on wipe.
    analyses: _LRUCache[tuple[Schedule, _Analysis]] = field(
        default_factory=lambda: _LRUCache(_ANALYSIS_CACHE_MAX)
    )
    # v4 Feature 2 lazy summary tier: the small per-version rollup (finish/margin/DCMA) the
    # Portfolio
    # needs, cached in-memory (key -> (scoped schedule, summary)) and — for uploads, keyed by the
    # raw
    # file content hash below — persisted in the SQLite cache so a portfolio of thousands renders
    # from
    # summaries, not a fresh CPM per row. Identity-checked and scope-aware like ``analyses``.
    summaries: dict[str, tuple[Schedule, VersionSummary]] = field(default_factory=dict)
    # ADR-0261 P2: the CPM-only tier — epoch-keyed like ``analyses`` ((key, scope-signature) →
    # (raw schedule, solve)). The multi-version population pass needs only dates/float per
    # version; this holds that solve without the heavy full analysis, and ``analysis_for``
    # reuses it so a network is never solved twice for one epoch. Cleared on wipe.
    # ADR-0292: BOUNDED. Each entry retains the scoped Schedule + CPMResult — measured at
    # ~641 KiB, i.e. ~11x a dash-core. While the same key is resident in ``analyses`` those objects
    # are shared and this tier is nearly free, but ``analyses`` is LRU-capped and this was a PLAIN
    # DICT: after an eviction the ``cpms`` entry kept the heavy objects alive on its own, so the
    # analysis cap did not actually bound session memory. Capped at 3x the analysis cap (entries are
    # ~11x lighter, and this tier is what makes an evicted version cheap to re-serve).
    cpms: _LRUCache[tuple[Schedule, CPMResult]] = field(
        default_factory=lambda: _LRUCache(_CPM_CACHE_MAX)
    )
    # ADR-0281: the dashboard card tier — epoch-keyed like ``cpms`` ((key, scope-signature) →
    # (raw schedule, _DashCore)). The home Dashboard needs only 3 of the 8 ``_Analysis`` fields per
    # version; this holds that ~1 KiB projection so a portfolio of many versions renders (and
    # refreshes) without ever building — or LRU-thrashing — a full analysis. Plain dict (not the
    # capped LRU): the whole point is that it never evicts under the cap. Cleared on wipe.
    dash_cores: dict[str, tuple[Schedule, _DashCore]] = field(default_factory=dict)
    #: ADR-0291 — the projected dashboard CARD per (key, scope-epoch). ``dash_cores`` caches the
    #: three ENGINE figures; this caches the MANIFEST PROJECTION built around them (the scoped
    #: schedule's activity count, status mix + its UID partition, and the baseline finish), which
    #: was otherwise re-derived for every version on every dashboard refresh even when fully warm.
    #: Plain dict, epoch-keyed exactly like ``dash_cores``, cleared on wipe.
    dash_cards: dict[str, tuple[Schedule, dict[str, object]]] = field(default_factory=dict)
    # ADR-0261 P3: per-version Performance-page memo, keyed by the SCOPED schedule's object
    # identity (one scoped object per version per epoch, courtesy of the scope memo):
    # id -> (scoped ref, effective-critical set, serialized G1-G5 block, truncated flag). The
    # census/flow/burden/DRM passes are pure functions of the scoped version, so /performance
    # stops recomputing every loaded version on every render. Identity-keyed ⇒ MUST die with
    # the epoch: cleared alongside the scope memos and on wipe.
    _perf_memo: dict[int, tuple[Schedule, frozenset[int], dict[str, object], bool]] = field(
        default_factory=dict
    )
    # key -> raw uploaded-file content hash (the SQLite summary/parse cache key). Only set for the
    # /upload path; a schedule loaded another way simply has no on-disk summary (in-memory only).
    content_hashes: dict[str, str] = field(default_factory=dict)
    # ADR-0258 active-project scoping: the operator's selected Project (a stable ``Project.pid``
    # from engine.projects). When MORE THAN ONE Project is loaded, the analysis populations
    # (:meth:`ordered` / :meth:`ordered_versions`) restrict to the ACTIVE project's versions —
    # no page but Portfolio ever mixes Projects. None = not explicitly chosen (resolution
    # auto-heals to the most recently loaded file's Project). Population-only: the per-key
    # analysis/summary caches stay valid across a switch. Cleared on wipe.
    active_project: str | None = None
    # ADR-0259 duplicate/revision review: session keys the operator EXCLUDED from analysis
    # (the Portfolio toggle). Reversible, never deletes — an excluded version stays loaded and
    # listed (badged) but leaves every analysis population. Cleared on wipe.
    excluded_keys: set[str] = field(default_factory=set)
    # F3a/3b confirmed schedule-margin overlay: key -> the operator-confirmed margin-task UniqueIDs
    # for that loaded version (set on the analysis-page margin panel via POST /margin/confirm).
    # When a
    # key has an entry, every margin computation for it uses that set instead of the name-based
    # default
    # (is_margin_task); absent => name-based. Cleared on wipe. Margin-task UIDs are stable across a
    # project's versions, so the cross-version dashboard/trend use the union
    # (confirmed_margin_union).
    margin_overlay: dict[str, frozenset[int]] = field(default_factory=dict)
    # v4 Feature 2: the loaded-schedule RAM estimate above which an ingest WARNS (never blocks). The
    # tool keeps parsed schedules resident for instant comparative analysis; on a big folder of
    # thousands this can be many GB. Operator-configurable (POST /session/ram-threshold).
    ram_warn_bytes: int = DEFAULT_WARN_BYTES
    # optional session-wide target activity: every view that can focus on a UniqueID
    # (report trace, trend focus, compare movement) defaults to this when set.
    target_uid: int | None = None
    # DCMA Acumen parity mode (ADR-0280): when True, the DCMA-14 checks use Acumen Fuse's exact
    # definitions from the NASA metric library — baselined population (Baseline Duration >= 1 day,
    # milestones kept), whole-day float, Resources on Baseline Cost/Work, stored-float CPLI,
    # two-term
    # BEI. Verified UID-exact on the operator's Large Test File / File2. Part of the analysis cache
    # signature so a toggle re-keys, never serving a stale audit. Supersedes the former
    # milestone-scope + CPLI toggles (0277/0278/0279).
    #
    # ON by default since ADR-0287: the tool's headline promise is that its DCMA-14 ribbon
    # reconciles
    # with Acumen Fuse on the same file, and a default-OFF toggle made a fresh session silently
    # report
    # the pure-logic numbers instead — read as "the tool disagrees with Acumen" twice by the
    # operator.
    # Unchecking restores the independent pure-logic forensic view; the ENGINE default stays False,
    # so
    # every golden/parity test (which passes the flag explicitly) is untouched. This is a session
    # PRESENTATION default only.
    dcma_acumen_parity: bool = True
    # F3c: operator-settable NASA Gold-Rule margin-requirement rate (work-days per program year) the
    # dashboard measures effective margin against. 30/yr (the Schedule Management Handbook default)
    # is
    # the initial value; set via GET /margin?rate=. The burn-down requirement line, the per-version
    # "NASA rqmt" column, the trigger flag, and the Excel/Word export all follow this one rate.
    margin_rate: float = GOLD_RULE_DAYS_PER_YEAR
    # F3c-fuller (ADR-0254): the operator's Fig 5-30 guideline band — four ISO phase-boundary
    # dates (Confirmation Review, I&T start, delivery to launch site, launch; program facts the
    # engine cannot derive — None until entered, the band simply absent) + the three (low, high)
    # wd/yr rates prefilled from the cited Fig 5-30 defaults. Set via POST /margin/band.
    margin_band_dates: tuple[str, str, str, str] | None = None
    margin_band_rates: tuple[tuple[float, float], ...] = FIG_5_30_DEFAULT_RATES
    # F3c-fuller: the §7.3.3.2.3 sufficiency-read percentile thresholds (Watch, Corrective
    # Action) — the handbook's EXAMPLE values 70/50 prefilled, operator-editable (program-set per
    # the SMP, §7.3.3.1.6 Thresholds).
    margin_risk_pcts: tuple[float, float] = (DEFAULT_WATCH_PCT, DEFAULT_CORRECTIVE_PCT)
    # v4 F4 (ADR-0255): the operator's selected audience role — a curated ENTRY POINT only
    # (home "Start here" strip, nav highlight, post-upload landing). None = "Show everything",
    # byte-identical to the pre-F4 behavior. Never hides a page, never touches a number.
    role: str | None = None
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
    polished: _LRUCache[tuple[Schedule, str, Narrative]] = field(
        default_factory=lambda: _LRUCache(_ANALYSIS_CACHE_MAX)
    )
    # the cross-check second model, cached like backend_cache (None = off/unreachable).
    second_cache: tuple[AIConfig, float, AIBackend | None] | None = None
    # session-wide group/filter (ADR-0104): when set, EVERY metric on EVERY page — and every loaded
    # file — is scoped to the tasks matching ALL criteria. Empty tuple = no filter (full schedules).
    active_filter: tuple[Criterion, ...] = ()
    # identity-stable cache of filtered schedules, id(original) -> (original, filtered), so a scoped
    # schedule keeps one identity across a request and the analysis cache below still hits. Cleared
    # whenever the filter changes (set_filter) or the session is wiped.
    _scoped: dict[int, tuple[Schedule, Schedule]] = field(default_factory=dict)
    # --- feature #10: session-wide SAVED (MS Project) filters & groups + HIGHLIGHT mode ----------
    # The session-wide SAVED FILTER — a faithful MS Project criteria tree (the reproduction
    # counterpart of the flat, field-based `active_filter` above). MUTUALLY EXCLUSIVE with it:
    # setting one clears the other (two ways to name one session scope). None = no saved filter.
    active_saved_filter: SavedFilter | None = None
    # Operator answers for an interactive saved filter ("Date Range..." → 2 prompts), keyed by the
    # prompt label; passed straight to the evaluator. Empty until the operator answers.
    saved_filter_prompts: dict[str, FieldValue] = field(default_factory=dict)
    # Filter MODE, applying to BOTH filter sources. "reduce" = today's behaviour (drop non-matching
    # tasks). "highlight" = keep the FULL population and only MARK the matches — scope() does not
    # reduce; the match set is carried to grids/gantt via highlight_uids().
    filter_mode: str = "reduce"
    # The session-wide SAVED GROUP (multi-clause) — ordering/banding only, never a population
    # change.
    # None = file order.
    active_saved_group: SavedGroup | None = None
    # match-set memo, id(original) -> (original, matched-UIDs | None). None value = "no filter" for
    # that object. Same identity-stability contract as `_scoped`; cleared by every filter setter +
    # wipe (grouping does NOT clear it — grouping never changes the match set).
    _matched: dict[int, tuple[Schedule, frozenset[int] | None]] = field(default_factory=dict)
    # SRA manual inputs (ADR-0106, manual path). The global triangular multipliers applied to every
    # activity's REMAINING duration when no per-activity override is set (defaults = the industry
    # "Quick Risk" screening values, Deltek Acumen "Realistic" 90/100/110).
    sra_low: float = 0.9
    sra_ml: float = 1.0
    sra_high: float = 1.10
    # per-activity 3-point overrides: uid -> (optimistic, most_likely, pessimistic) WORKING MINUTES.
    sra_overrides: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    # UNIFIED risk register (entered once): each risk carries BOTH an additive-days (SSI) and a
    # multiplicative-% (legacy) magnitude + per-model lock flags. At the compute boundary it derives
    # the engine's ScheduleRisk (additive) and RiskEvent (multiplicative). Set via POST
    # /sra/risk-register.
    sra_risks: list[UnifiedRisk] = field(default_factory=list)
    # monotonic id counter so each registered risk keeps a stable, unique id across removals.
    sra_risk_seq: int = 0
    # probabilistic branches (ADR-0273, Hulett #8): rework fragnets inserted onto an FS tie in p% of
    # SSI iterations → bi-modal finish. Durations stored in working minutes. Set via POST
    # /sra/branch.
    sra_branches: list[ProbabilisticBranch] = field(default_factory=list)
    sra_branch_seq: int = 0  # stable unique-id counter across removals
    # conditional branches (ADR-0274, Hulett #9): contingency switching — a condition on a monitored
    # activity picks primary Plan A vs contingency Plan B each iteration. Set via POST
    # /sra/conditional.
    sra_conditionals: list[ConditionalBranch] = field(default_factory=list)
    sra_conditional_seq: int = 0  # stable unique-id counter across removals
    # which loaded file the SRA runs against (operator choice). None / unknown key => the latest
    # solvable version (the historical default). Set via GET /sra?file=<key>.
    sra_file: str | None = None
    # --- SSI Schedule Risk & Opportunity Analysis inputs (ADR-0123) ---
    # the focus event whose finish the SSI run/OAT report (SSI "Flag for Analysis"); None =>
    # project.
    sra_focus_uid: int | None = None
    # the Risk Factors table: (factor 1..5, Best Case as a % OF the ML, % to add for Worst Case).
    sra_factor_rows: tuple[tuple[int, float, float], ...] = field(
        default_factory=lambda: RiskFactorTable().rows
    )
    sra_factors: dict[int, int] = field(default_factory=dict)  # uid -> Risk Ranking Factor 1..5
    sra_bcwc: dict[int, tuple[int, int]] = field(default_factory=dict)  # uid -> (BC, WC) minutes
    # (the SSI + legacy registers are unified into `sra_risks` above — both magnitudes per risk)
    sra_occurrence_mode: str = "random_each"  # "random_each" | "exact_overall"
    sra_use_risk_register: bool = True
    sra_correlation: float = 0.0  # 0 = independent; 0.3-0.5 typical blanket correlation
    # Monte-Carlo vs Latin Hypercube sampler (ADR-0271). "mc" is the byte-frozen default; "lhs"
    # stratifies the copula draws for tighter convergence at the same iteration count. Centered
    # LHS uses the stratum midpoints (fully deterministic, no within-stratum jitter).
    sra_sampling: str = "mc"  # "mc" | "lhs"
    sra_lhs_centered: bool = False
    # full pairwise/shared-driver correlation MATRIX inputs (ADR-0270). Empty → the scalar
    # blanket correlation above drives the run; non-empty over ≥2 uncertain tasks OVERRIDES it
    # and drives a multivariate Gaussian copula (a distinct mode). Pairwise rho may be negative.
    sra_corr_pairs: tuple[tuple[int, int, float], ...] = ()
    sra_corr_groups: tuple[tuple[tuple[int, ...], float], ...] = ()
    #: the last SSI run's per-activity Criticality Index (ADR-0272): uid -> fraction of iterations
    #: the activity was critical, cached so the SSI grid Gantt can tint bars by "how often critical"
    #: (the grid is a separate fetch from the run). Empty until the operator runs the simulation.
    sra_criticality: dict[int, float] = field(default_factory=dict)
    sra_criticality_iters: int = (
        0  # the iteration count of the run that produced the tint (provenance)
    )
    #: one-shot feedback from an Excel round-trip import (ADR-0211), rendered once on /sra
    sra_import_msg: str | None = None
    # JCL joint cost-&-schedule confidence settings (ADR-0269). Blank targets (None) mean
    # "use the run's deterministic finish / EAC"; td_share is the time-dependent cost share
    # τ; the 1/1/1 multipliers mean cost-estimating uncertainty is OFF (duration-driven
    # cost only); confidence is the frontier's joint target (NPR 7120.5F anchor 0.70).
    jcl_target_date: str | None = None  # ISO date
    jcl_target_cost: float | None = None
    jcl_td_share: float = 1.0
    jcl_cost_low: float = 1.0
    jcl_cost_ml: float = 1.0
    jcl_cost_high: float = 1.0
    jcl_confidence: float = 0.70
    # Routes are sync `def` (Starlette threadpool = real concurrency); this reentrant lock makes
    # the scope/analysis caches and the filter/wipe invalidations atomic, so a render can never
    # iterate a dict another request is clearing (QC audit D18 — live-reproduced KeyError on
    # /trend under concurrent filter+render). Single-operator tool: contention is negligible.
    _lock: threading.RLock = field(default_factory=threading.RLock)
    # ADR-0263 store guards. ``wipe_gen`` bumps on every wipe: a compute that started BEFORE the
    # wipe must never store its result (in-memory OR into the on-disk CUI cache) AFTER it — the
    # wipe's contract is "nothing of the operator's data survives the reset", and a late
    # put_summary/put_schedule would silently re-insert derived operator data on disk.
    # ``_scope_gen`` additionally bumps on every scope epoch change: the identity-keyed P3 memo
    # must die with its epoch, so a store computed under an older epoch is skipped (a plain-dict
    # orphan would otherwise pin the dead scoped schedule until the next flip/wipe).
    wipe_gen: int = 0
    _scope_gen: int = 0
    # ADR-0281 single-flight: 64 fixed striped locks so N concurrent COLD requests for one epoch
    # key compute ONCE (the winner computes; the rest wait, then hit the just-filled cache) —
    # without serialising unrelated keys (a different key almost always maps to a different stripe;
    # a rare collision only serialises two unrelated cold computes, never yields a wrong number).
    # Bounded count, never a per-key lock map. Deadlock discipline: a stripe is ALWAYS taken
    # OUTSIDE ``_lock`` (stripe → ``_lock`` ordering, never the reverse), and never nested.
    _stripes: tuple[threading.Lock, ...] = field(
        default_factory=lambda: tuple(threading.Lock() for _ in range(64)), repr=False
    )

    def _match_uids(self, sch: Schedule) -> frozenset[int] | None:
        """The UIDs of ``sch`` matching the active filter — the faithful saved-filter tree OR the
        flat field criteria — or ``None`` when no filter is set (⇒ every task). Memoised by the
        original's identity (the tree walk can be called several times per request); invalidated by
        every filter setter and by wipe. Callers hold ``self._lock``."""
        cached = self._matched.get(id(sch))
        if cached is not None and cached[0] is sch:
            return cached[1]
        matched: frozenset[int] | None
        if self.active_saved_filter is not None:
            matched = frozenset(
                _select_saved(sch, self.active_saved_filter, self.saved_filter_prompts)
            )
        elif self.active_filter:
            matched = frozenset(select(sch, self.active_filter))
        else:
            matched = None
        self._matched[id(sch)] = (sch, matched)
        return matched

    def scope(self, sch: Schedule) -> Schedule:
        """``sch`` reduced to the active filter AND truncated to the target endpoint — the single
        point every page funnels through.

        Returns ``sch`` unchanged when nothing narrows the population. A filter narrows only in
        **reduce** mode: in **highlight** mode the matches are merely marked (see
        :meth:`highlight_uids`), so ``scope()`` leaves the population whole and only the Target UID
        can still truncate it. In reduce mode the matching tasks (plus their summary ancestors when
        the saved filter asks to "show related summary rows") are kept, then — when a Target UID is
        set and present — the result is restricted to that activity plus everything that drives it
        (:func:`subschedule_to_target`). A version that does not contain the target keeps its
        (filtered) population. Memoised by the original's identity so repeated calls in one request
        share one object (keeping the per-key analysis cache valid); the memo resets on the filter/
        target setters and wipe."""
        with self._lock:
            matched = self._match_uids(sch)
            reducing = matched is not None and self.filter_mode == "reduce"
            if not reducing and self.target_uid is None:
                return sch  # nothing changes the population
            cached = self._scoped.get(id(sch))
            if cached is not None and cached[0] is sch:
                return cached[1]
            if reducing and matched is not None:
                kept = matched
                if self.active_saved_filter is not None and (
                    self.active_saved_filter.show_related_summary_rows
                ):
                    kept = with_ancestors(sch, kept)
                scoped = filter_to_uids(sch, kept)
            else:
                scoped = sch
            if self.target_uid is not None and any(
                t.unique_id == self.target_uid and not t.is_summary for t in scoped.tasks
            ):
                # target present in this version → truncate to it + its drivers; a version that
                # doesn't contain the target keeps its full (filtered) population.
                scoped = subschedule_to_target(scoped, self.target_uid)
            self._scoped[id(sch)] = (sch, scoped)
            return scoped

    def highlight_uids(self, sch: Schedule) -> frozenset[int] | None:
        """When a filter is active in **highlight** mode, the UIDs of ``sch``'s matching tasks (to
        shade rows / outline bars). ``None`` when no filter is active or the mode is ``reduce`` —
        reduce already dropped the non-matches, so there is nothing to mark."""
        with self._lock:
            if self.filter_mode != "highlight":
                return None
            return self._match_uids(sch)

    def _scope_signature(self) -> str:
        """Canonical token for everything that can change an analysis POPULATION (ADR-0261 P1).

        ``""`` when nothing narrows — the default epoch, whose cache keys stay the bare session
        key (byte-identical key shape to the pre-P1 cache for the common case). Mirrors
        :meth:`scope`'s own branches exactly: a filter contributes only in **reduce** mode
        (highlight marks rows, never narrows the population), via the saved filter's full
        canonical dump + the operator's prompt answers, or the flat criteria tuple's repr; the
        Target UID contributes whenever set. Always the FULL canonical text, never a hash — a
        hash collision could serve a wrong number, so there is nothing to collide. Callers hold
        ``self._lock``."""
        parts: list[str] = []
        if self.filter_mode == "reduce":
            if self.active_saved_filter is not None:
                parts.append("S=" + self.active_saved_filter.model_dump_json())
                if self.saved_filter_prompts:
                    prompts = sorted((k, repr(v)) for k, v in self.saved_filter_prompts.items())
                    parts.append("P=" + repr(prompts))
            elif self.active_filter:
                parts.append("F=" + repr(self.active_filter))
        if self.target_uid is not None:
            parts.append(f"T={self.target_uid}")
        # DCMA Acumen parity mode (ADR-0280): contributes only when ENABLED, so the default epoch's
        # key shape is byte-identical to before — an analysis's audit differs under this flag, so it
        # must live in its own cache epoch (never serve a stale audit across a toggle).
        if self.dcma_acumen_parity:
            parts.append("A=1")
        return "\x1f".join(parts)

    def scope_signature(self) -> str:
        """The current scope signature (public, lock-taking) — for epoch-keyed caches that live
        outside this class (the polished-narrative cache)."""
        with self._lock:
            return self._scope_signature()

    def _cache_key(self, key: str, sig: str) -> str:
        """The epoch-aware cache key: the bare session key in the default epoch (sig ``""``),
        else ``key␟sig``. Callers hold ``self._lock`` (or pass a sig they took under it)."""
        return key if not sig else f"{key}\x1f{sig}"

    def _invalidate_scope(self) -> None:
        """Reset the scope MEMOS — the shared body of the filter/target setters.

        ADR-0261 P1: this is now SURGICAL. Only the cheap identity memos (``_scoped`` /
        ``_matched``) reset; the expensive ``analyses`` / ``summaries`` / ``polished`` caches are
        keyed by ``(key, scope-signature)`` and simply stop being consulted for the old epoch —
        so toggling a filter or target ON and back OFF returns to resident results instead of
        recomputing every loaded version twice. Stale service is impossible by construction: a
        different population ⇒ a different signature ⇒ a different cache key (proven by
        tests/web/test_scope_epoch_cache.py). A wipe still clears everything explicitly."""
        self._scoped.clear()
        self._matched.clear()
        self._perf_memo.clear()  # identity-keyed (P3): must never outlive the scope epoch
        self._scope_gen += 1  # ADR-0263: a store computed under the old epoch must be skipped

    def set_filter(self, criteria: Sequence[Criterion]) -> None:
        """Set (or clear, with ``()``) the session-wide FIELD filter and invalidate the scope/
        analysis caches. Clears any active saved filter (mutual exclusivity — one scope at a
        time)."""
        with self._lock:
            self.active_filter = tuple(criteria)
            self.active_saved_filter = None
            self.saved_filter_prompts = {}
            self._invalidate_scope()

    def set_saved_filter(
        self, saved: SavedFilter | None, prompts: dict[str, FieldValue] | None = None
    ) -> None:
        """Set (or clear) the session-wide SAVED (MS Project) filter. Clears any field filter
        (mutual
        exclusivity). ``prompts`` supplies the operator's answers for an interactive filter."""
        with self._lock:
            self.active_saved_filter = saved
            self.saved_filter_prompts = dict(prompts or {})
            if saved is not None:
                # mutual exclusivity applies only when actually SETTING a saved filter; clearing one
                # (saved is None) must not also drop an unrelated active field filter.
                self.active_filter = ()
            self._invalidate_scope()

    def set_filter_mode(self, mode: str) -> None:
        """Switch the filter MODE between ``reduce`` and ``highlight``. Reduce↔highlight changes the
        population, so the full scope cache is invalidated."""
        with self._lock:
            self.filter_mode = "highlight" if mode == "highlight" else "reduce"
            self._invalidate_scope()

    def set_saved_group(self, group: SavedGroup | None) -> None:
        """Set (or clear) the session-wide SAVED group. Grouping is ordering/banding only — it does
        NOT change any metric population, so it deliberately does not invalidate the
        analysis/summary
        caches (a regroup stays cheap)."""
        with self._lock:
            self.active_saved_group = group

    def set_target(self, uid: int | None) -> None:
        """Set (or clear) the session-wide Analysis Target and invalidate the scope/analysis caches
        so every metric, audit, and visual recomputes against the target's driving sub-network (or
        the full schedule again when cleared). The one global target also drives the SRA/SSI focus
        event (ADR-0196), so the header selector and the SRA focus never disagree; an analyst can
        still override the SRA focus in-panel afterward."""
        with self._lock:
            self.target_uid = uid
            self.sra_focus_uid = uid
            self._invalidate_scope()

    def set_dcma_acumen_parity(self, enabled: bool) -> None:
        """Toggle the single Acumen-parity DCMA mode (ADR-0280). The flag is part of the analysis
        cache signature (``_scope_signature`` adds ``A=1`` when enabled), so flipping it re-keys the
        analysis epoch — the DCMA audit recomputes on next access and a toggle can never serve a
        stale
        audit; the scoped population itself is unchanged, so nothing else invalidates."""
        with self._lock:
            self.dcma_acumen_parity = enabled

    def set_margin_rate(self, rate: float) -> None:
        """Set the NASA Gold-Rule margin-requirement rate (work-days per program year) the margin
        dashboard measures against (F3c). Accepted only in a sane ``(0, 365]`` band; anything else
        is
        ignored, keeping the current rate (fail-soft — a bad query value never wipes the setting).
        The
        rate feeds only the freshly-computed requirement line / trigger, not the analysis or summary
        caches, so nothing needs invalidating."""
        with self._lock:
            if 0 < rate <= 365:
                self.margin_rate = rate

    def set_margin_band(
        self, dates: tuple[str, str, str, str] | None, rates: tuple[tuple[float, float], ...]
    ) -> None:
        """Set the operator's Fig 5-30 guideline band (F3c-fuller, ADR-0254) — fail-soft like
        ``set_margin_rate``: dates must be four strictly-increasing ISO dates (or None to clear),
        each rate ``0 < low <= high <= 365``; an invalid piece is IGNORED, keeping the current
        value (a bad form value never wipes the setting). No cache invalidation — the band feeds
        only the freshly-computed overlay, never the analysis/summary caches."""
        with self._lock:
            if dates is None:
                self.margin_band_dates = None
            else:
                try:
                    parsed = [dt.date.fromisoformat(s) for s in dates]
                except ValueError:
                    parsed = []
                if len(parsed) == 4 and all(b > a for a, b in itertools.pairwise(parsed)):
                    self.margin_band_dates = dates
            if len(rates) == 3 and all(0 < lo <= hi <= 365 for lo, hi in rates):
                self.margin_band_rates = rates

    def set_margin_risk_pcts(self, watch: float, corrective: float) -> None:
        """Set the §7.3.3.2.3 Watch / Corrective-Action percentile thresholds (fail-soft: must
        satisfy ``0 < corrective < watch < 100``, else the current values are kept)."""
        with self._lock:
            if 0 < corrective < watch < 100:
                self.margin_risk_pcts = (watch, corrective)

    def set_role(self, role: str | None) -> None:
        """Set (or clear) the audience role (v4 F4, ADR-0255). Fail-soft: an unknown role id is
        ignored, keeping the current selection. Pure wayfinding — no cache is invalidated because
        the role can never change a computed figure."""
        with self._lock:
            if role is None or role in _ROLE_BY_ID:
                self.role = role

    def confirmed_margin_union(self) -> frozenset[int] | None:
        """The union of every loaded version's operator-confirmed margin-task set, or ``None`` when
        no
        version carries a confirmed overlay (⇒ the name-based default). Margin-task UniqueIDs are
        stable across a project's versions, so a UID confirmed on any version is treated as margin
        wherever it appears in the cross-version burn-down / trend (the per-version panel still uses
        that key's own set). Once ANY overlay exists this returns a concrete frozenset — even the
        empty
        set (operator unchecked everything) — so the dashboard honors a deliberate zero, never
        silently
        reverting to name-based."""
        with self._lock:
            if not self.margin_overlay:
                return None
            union: set[int] = set()
            for uids in self.margin_overlay.values():
                union |= uids
            return frozenset(union)

    def ordered(self) -> list[Schedule]:
        """ANALYSIS-population schedules — the ACTIVE project's versions (ADR-0258) minus
        operator-EXCLUDED versions (ADR-0259), **scoped to the active filter**, ordered by data
        date (oldest first). With a single Project loaded and nothing excluded this is every
        loaded file — byte-identical to the pre-scoping behavior. Manifest views (home list,
        Portfolio) use :meth:`all_versions` / :meth:`projects` instead.

        This is what the multi-version views that call engine functions directly (bow-wave, S-curve,
        month curves) iterate, so the filter reaches them too. Views that go through
        :meth:`analysis_for` pass the raw schedule from :meth:`ordered_versions` (it scopes)."""
        with self._lock:
            keys = self._analysis_population()
            pool = [s for k, s in self.schedules.items() if keys is None or k in keys]
            return [self.scope(s) for s in order_versions(pool)]

    def ordered_versions(self) -> list[tuple[str, Schedule]]:
        """(key, UNSCOPED schedule) pairs of the ANALYSIS population (active project only,
        exclusions dropped — see :meth:`ordered`), oldest first. Callers either hand the schedule
        to :meth:`analysis_for` (which scopes it) or, for the filter UI, need the full field/value
        set — so this stays raw. Use :meth:`ordered` / :meth:`scope` when you need the filtered
        tasks; use :meth:`all_versions` for the every-loaded-file manifest."""
        with self._lock:
            keys = self._analysis_population()
            pool = [s for k, s in self.schedules.items() if keys is None or k in keys]
            by_obj = {id(s): k for k, s in self.schedules.items()}
            return [(by_obj[id(s)], s) for s in order_versions(pool)]

    def all_versions(self) -> list[tuple[str, Schedule]]:
        """EVERY loaded (key, UNSCOPED schedule) pair, oldest first — the session MANIFEST
        (home's loaded-schedules list), which must keep showing every Project and excluded
        versions. Analysis populations use :meth:`ordered` / :meth:`ordered_versions`."""
        with self._lock:
            by_obj = {id(s): k for k, s in self.schedules.items()}
            return [(by_obj[id(s)], s) for s in order_versions(list(self.schedules.values()))]

    def populations(self) -> list[tuple[str, str, tuple[str, ...]]]:
        """The ANALYSIS populations as ``(pid, display title, version keys)`` (ADR-0258).

        Each IDENTIFIED Project (folder or document-title origin) is its own population —
        identified Projects never mix. Title-less loose files carry no project-identity signal,
        so ALL of them pool into one explicit ``(untitled files)`` population (Portfolio still
        lists each individually as needs-attention per ADR-0225): the classic
        drop-N-untitled-exports version-series workflow keeps working, loudly labeled, instead
        of shattering into N single-file "projects". Callers hold ``self._lock``."""
        pops: list[tuple[str, str, tuple[str, ...]]] = []
        untitled: list[str] = []
        for p in self.projects():
            if p.origin == "filename":
                untitled.extend(v.key for v in p.versions)
            else:
                pops.append((p.pid, p.title, tuple(v.key for v in p.versions)))
        if untitled:
            pops.append((_UNTITLED_PID, "(untitled files)", tuple(untitled)))
        return pops

    def _analysis_population(self) -> frozenset[str] | None:
        """Session keys allowed into analysis populations, or ``None`` = no restriction.

        Two narrowings, both population-only (per-key analysis/summary caches stay valid, nothing
        is invalidated): operator-EXCLUDED versions always drop (ADR-0259); with more than one
        population loaded, only the ACTIVE one's versions remain (ADR-0258 — no cross-project
        mixing anywhere but Portfolio). With zero or one population and nothing excluded this
        returns ``None`` — the fast path, and the proof single-project behavior is unchanged.
        Callers hold ``self._lock``."""
        pops = self.populations()
        if len(pops) <= 1:
            if not self.excluded_keys:
                return None
            return frozenset(k for k in self.schedules if k not in self.excluded_keys)
        _pid, _title, keys = self._resolve_active(pops)
        return frozenset(k for k in keys if k not in self.excluded_keys)

    def _resolve_active(
        self, pops: list[tuple[str, str, tuple[str, ...]]]
    ) -> tuple[str, str, tuple[str, ...]]:
        """The ACTIVE population resolved against the current grouping: the stored pid when it
        still exists, else healed to the population holding the most recently loaded file
        (upload order), else the last-listed one. A pure read — render paths never write
        session state. Callers guarantee ``pops`` is non-empty."""
        if self.active_project is not None:
            for pop in pops:
                if pop[0] == self.active_project:
                    return pop
        last_key = next(reversed(self.schedules), None)
        if last_key is not None:
            for pop in pops:
                if last_key in pop[2]:
                    return pop
        return pops[-1]

    def active_population(self) -> tuple[str, str, tuple[str, ...]] | None:
        """The resolved ACTIVE ``(pid, title, keys)`` population (``None`` when nothing is
        loaded) — what the banner and the project switcher display."""
        with self._lock:
            pops = self.populations()
            if not pops:
                return None
            return self._resolve_active(pops)

    def set_active_project(self, pid: str) -> bool:
        """Select the ACTIVE population by its stable pid (ADR-0258; ``untitled:`` selects the
        pooled title-less files). ``False`` for an unknown pid (a stale form) — state unchanged.
        Selection changes WHICH keys analysis iterates; the per-key caches stay valid, so
        nothing is invalidated. A session-wide Target UID that does not resolve inside the newly
        selected population is cleared through :meth:`set_target` (so its scope memo resets); a
        target that resolves is kept."""
        with self._lock:
            pop = next((p for p in self.populations() if p[0] == pid), None)
            if pop is None:
                return False
            self.active_project = pid
            if self.target_uid is not None:
                present = any(
                    t.unique_id == self.target_uid
                    for key in pop[2]
                    if (s := self.schedules.get(key)) is not None
                    for t in s.tasks
                )
                if not present:
                    self.set_target(None)
            return True

    def set_excluded(self, key: str, excluded: bool) -> bool:
        """Mark/unmark one loaded version as EXCLUDED from analysis (ADR-0259) — the operator's
        duplicate/revision resolution. Reversible, never deletes; Portfolio keeps listing it,
        badged. Population-only (no cache invalidation). ``False`` for an unknown key."""
        with self._lock:
            if key not in self.schedules:
                return False
            if excluded:
                self.excluded_keys.add(key)
            else:
                self.excluded_keys.discard(key)
            return True

    def projects(self) -> tuple[Project, ...]:
        """Loaded files grouped into Projects (v4 grouped ingestion). Folder uploads → one Project
        per top folder (all files beneath it, any depth, its versions); loose files → grouped by
        their real document Title; a title-less loose file → its own needs-attention Project.
        Derived from ``schedules`` + ``file_meta`` on each call — pure and cheap (no engine
        math)."""
        with self._lock:
            records = [
                IngestRecord(
                    key=key,
                    project_title=sch.project_title,
                    filename=sch.source_file or key,
                    status_date_ordinal=(
                        sch.status_date.timestamp() if sch.status_date is not None else None
                    ),
                    folder=self.file_meta.get(key, (None, None))[0],
                    mtime=self.file_meta.get(key, (None, None))[1],
                    content_hash=self.content_hashes.get(key),
                    excluded=key in self.excluded_keys,
                )
                for key, sch in self.schedules.items()
            ]
            return group_into_projects(records)

    def _stripe_for(self, ck: str) -> threading.Lock:
        """The single-flight stripe for epoch key ``ck`` (ADR-0281) — stable within a process. A
        bounded-collision hash, never a per-key map: it serialises duplicate COLD computes of the
        SAME epoch key, and at worst two unrelated keys share a stripe (they serialise; the result
        is still byte-identical to computing them apart)."""
        return self._stripes[hash(ck) % len(self._stripes)]

    def analysis_for(self, key: str, sch: Schedule) -> _Analysis:
        """The cached analysis for ``key`` over the active scope.

        ADR-0261 P1: keyed by ``(key, scope-signature)`` with the RAW schedule as the identity
        anchor — toggling a filter/target flips between resident epochs (clearing a filter is a
        cache hit again), while a re-upload under the same key still recomputes (new object).
        ADR-0261 P4: the heavy engine compute runs OUTSIDE the session lock, so one long
        analysis never serialises every other request. ADR-0281 single-flight: on a miss the
        compute runs under the key's STRIPE, so N concurrent cold callers compute ONCE (the rest
        wait, then hit the just-filled cache) — with ``ck`` / ``gen`` / ``parity`` re-derived under
        ``_lock`` INSIDE the stripe (a scope flip while queued recomputes under the CURRENT key,
        never a stale one). An exception propagates to every waiter's caller (the ``with``-scoped
        locks release) and a later call recomputes cleanly; a wipe between unlock and store leaves
        at most one orphaned LRU entry that is never consulted again and is evicted normally."""
        with self._lock:  # fast path: a resident hit needs no stripe (the common warm case)
            ck = self._cache_key(key, self._scope_signature())
            cached = self.analyses.get_lru(ck)
            if cached is not None and cached[0] is sch:
                return cached[1]
        # miss: single-flight on the key's stripe (taken OUTSIDE _lock — stripe → _lock ordering)
        with self._stripe_for(ck):
            with self._lock:
                ck = self._cache_key(key, self._scope_signature())
                gen = self.wipe_gen
                cached = self.analyses.get_lru(ck)
                if cached is not None and cached[0] is sch:
                    return cached[1]  # a prior stripe holder already filled this epoch
                scoped = self.scope(sch)  # memoised; cheap next to the engine pass below
                pre = self.cpms.get_lru(ck)
                cpm = pre[1] if pre is not None and pre[0] is sch else None
                parity = self.dcma_acumen_parity  # captured under the lock with the cache key
            analysis = _compute_analysis(scoped, cpm=cpm, dcma_acumen_parity=parity)
            with self._lock:
                if self.wipe_gen == gen:  # ADR-0263: never re-populate a wiped session
                    self.analyses.put(ck, (sch, analysis))
                    self.cpms.put(ck, (sch, analysis.cpm))  # P2 tier reuses the solve either way
            return analysis

    def cpm_scoped_for(self, key: str, sch: Schedule) -> tuple[Schedule, CPMResult]:
        """The ``(scoped schedule, CPM solve)`` pair for ``key``, captured CONSISTENTLY in one
        lock window (ADR-0263). The pre-fix pattern — ``cpm_for(key, sch)`` then a separate
        ``st.scope(sch)`` — left a gap between two lock windows where a concurrent filter/target
        change could pair an old-epoch solve with a new-epoch population (and the P3 memo would
        then re-serve that poisoned pairing for the rest of the epoch). Here the scoped object
        is resolved in the SAME window that resolves the epoch key, and a cache-miss solve runs
        on exactly that object, so an inconsistent pair is unrepresentable. ADR-0281: the solve
        is single-flighted on the key's stripe (it also serves :meth:`dashboard_core_for`), so N
        concurrent cold callers solve the network ONCE."""
        with self._lock:  # fast path: a resident solve (or a resident full analysis') — no stripe
            ck = self._cache_key(key, self._scope_signature())
            scoped = self.scope(sch)
            pre = self.cpms.get_lru(ck)
            if pre is not None and pre[0] is sch:
                return scoped, pre[1]
            full = self.analyses.get_lru(ck)
            if full is not None and full[0] is sch:
                self.cpms.put(ck, (sch, full[1].cpm))
                return scoped, full[1].cpm
        # miss: single-flight the solve on the key's stripe (taken OUTSIDE _lock — stripe → _lock)
        with self._stripe_for(ck):
            with self._lock:
                ck = self._cache_key(key, self._scope_signature())
                gen = self.wipe_gen
                scoped = self.scope(sch)
                pre = self.cpms.get_lru(ck)
                if pre is not None and pre[0] is sch:
                    return scoped, pre[1]  # a prior stripe holder already solved this epoch
                full = self.analyses.get_lru(ck)
                if full is not None and full[0] is sch:
                    self.cpms.put(ck, (sch, full[1].cpm))
                    return scoped, full[1].cpm
            cpm = compute_cpm(scoped)
            with self._lock:
                if self.wipe_gen == gen:  # ADR-0263: never re-populate a wiped session
                    self.cpms.put(ck, (sch, cpm))
            return scoped, cpm

    def cpm_for(self, key: str, sch: Schedule) -> CPMResult:
        """Just the CPM solve for ``key`` over the active scope (ADR-0261 P2).

        The multi-version population pass (``_solvable_versions``) needs only dates/float for
        every version — building the full monolithic analysis (audit + baseline + float-bands +
        completion + findings + narrative + activity grid) per version just to read ``.cpm`` was
        the recorded P2 lag. Reuses a resident full analysis' solve when one exists; otherwise
        solves the network alone (outside the lock, P4) and caches it — and a later
        ``analysis_for`` reuses THIS solve instead of re-running it. Same epoch keying and
        identity anchor as ``analysis_for``; a ``CPMError`` propagates exactly as before.
        Callers that also need the schedule the solve was computed from MUST use
        :meth:`cpm_scoped_for` (one consistent pair) instead of pairing this with a separate
        ``scope()`` call."""
        return self.cpm_scoped_for(key, sch)[1]

    def dashboard_card_cached(self, key: str, sch: Schedule) -> dict[str, object] | None:
        """The memoised dashboard CARD for ``key`` over the active scope, or ``None`` (ADR-0291).

        Epoch-keyed by the same ``(key, scope-signature)`` as ``dash_cores``/``cpms``, so a filter /
        target / parity change re-keys automatically and a stale card can never be served. The
        identity guard (``hit[0] is sch``) is the same one ``dashboard_core_for`` uses: a
        re-uploaded
        version is a NEW frozen ``Schedule`` object, so it misses and re-projects."""
        with self._lock:
            hit = self.dash_cards.get(self._cache_key(key, self._scope_signature()))
            return hit[1] if hit is not None and hit[0] is sch else None

    def dashboard_card_store(
        self, key: str, sch: Schedule, card: dict[str, object], gen: int
    ) -> None:
        """Memoise a projected dashboard card, under the ``wipe_gen`` guard (ADR-0291).

        ``gen`` is the wipe generation the caller captured BEFORE building the card. If a wipe
        landed in between, the card describes a session that no longer exists and is dropped rather
        than resurrecting dead state — the same ADR-0263 rule ``dashboard_core_for`` follows. The
        key is re-derived inside the lock so a scope flip during the build stores under the CURRENT
        epoch, never a stale one."""
        with self._lock:
            if self.wipe_gen == gen:
                self.dash_cards[self._cache_key(key, self._scope_signature())] = (sch, card)

    def dashboard_core_for(self, key: str, sch: Schedule) -> _DashCore:
        """The tiny dashboard-card core for ``key`` over the active scope (ADR-0281).

        Three tiers, cheapest first: (1) a resident dash-core (epoch-keyed) is returned as-is;
        (2) a resident FULL analysis is projected down with no engine work; (3) otherwise only the
        two metrics the card needs — the DCMA audit and the zero-float band — are computed off the
        shared, single-flighted CPM solve (:meth:`cpm_scoped_for`), never the whole 8-field
        analysis. Epoch-keyed by the same ``(key, scope-signature)`` as ``analyses`` / ``cpms`` (a
        filter / target / parity change re-keys automatically), with ``parity`` captured under the
        lock alongside the key; stored under the ``wipe_gen`` guard. ``CPMError`` propagates exactly
        as :meth:`analysis_for` — the unschedulable-card path is unchanged."""
        with self._lock:
            ck = self._cache_key(key, self._scope_signature())
            gen = self.wipe_gen
            parity = self.dcma_acumen_parity  # captured under the lock with the epoch key
            hit = self.dash_cores.get(ck)
            if hit is not None and hit[0] is sch:
                return hit[1]
            full = self.analyses.get_lru(ck)
            if full is not None and full[0] is sch:
                core = _dash_core(full[1].cpm, full[1].audit, full[1].float_bands["float_total_0"])
                self.dash_cores[ck] = (sch, core)  # under the lock, same epoch as the full analysis
                return core
        # tier 3: not resident anywhere — compute ONLY the two metrics the card needs, off the
        # single-flighted solve. A concurrent request may fill the tier while this one solves.
        scoped, cpm = self.cpm_scoped_for(key, sch)
        with self._lock:
            resident = self.dash_cores.get(ck)
            if resident is not None and resident[0] is sch:
                return resident[1]
        audit = audit_schedule(scoped, cpm, acumen_parity=parity)
        fb0 = compute_float_bands(scoped, cpm)["float_total_0"]
        core = _dash_core(cpm, audit, fb0)
        with self._lock:
            if self.wipe_gen == gen:  # ADR-0263: never re-populate a wiped session
                self.dash_cores[ck] = (sch, core)
        return core

    def summary_for(self, key: str, sch: Schedule) -> VersionSummary:
        """The cached rollup summary for ``key`` (v4 Feature 2 lazy tier) — the Portfolio's cheap
        path: finish, effective margin, DCMA-14 pass/fail, without holding the full analysis.

        In-memory first (epoch-keyed like ``analysis_for`` — ADR-0261 P1); then, only when the
        version is UNSCOPED (no active filter/target changes the numbers, so ``scope`` returned
        the schedule unchanged), the on-disk SQLite summary keyed by the file's content hash —
        surviving a session restart. A scoped version, or one with no content hash (loaded
        outside /upload), computes fresh and is memoised for the session only. A summary equals
        the fully-computed row (test-enforced), so this only ever changes speed. The compute and
        the SQLite I/O run OUTSIDE the session lock (ADR-0261 P4)."""
        with self._lock:
            ck = self._cache_key(key, self._scope_signature())
            gen = self.wipe_gen
            cached = self.summaries.get(ck)
            if cached is not None and cached[0] is sch:
                return cached[1]
            scoped = self.scope(sch)
            # ADR-0263: the operator's confirmed margin set (ADR-0230 overlay; same
            # per-version-else-union precedence as the margin dashboard/SRA) changes the margin
            # number, so an overlaid version computes fresh — the content-hash disk blob holds
            # the name-based default and must be neither consulted nor overwritten for it.
            overlay = self.margin_overlay.get(key, self.confirmed_margin_union())
            on_disk = scoped is sch and overlay is None  # whole-file, name-based default only
            chash = self.content_hashes.get(key) if on_disk else None
        summary: VersionSummary | None = None
        computed = False
        if chash is not None:
            blob = get_default_cache().get_summary(chash)
            if blob is not None:
                try:
                    summary = VersionSummary.from_json(blob)
                except (ValueError, KeyError, TypeError):
                    summary = None  # a stale/corrupt blob is a miss, never an error
        if summary is None:
            summary = compute_summary(scoped, margin_uids=overlay)
            computed = True
        with self._lock:
            # ADR-0263: both stores (in-memory AND the on-disk CUI cache) are guarded by the
            # wipe generation captured before the compute, and the disk put happens under the
            # lock — so a wipe's clear() (which now also runs under this lock) can never be
            # followed by a late re-insert of the operator's derived data.
            if self.wipe_gen == gen:
                self.summaries[ck] = (sch, summary)
                if computed and chash is not None:
                    get_default_cache().put_summary(chash, summary.to_json())
        return summary


def _iso_date(value: object) -> str:
    return value.date().isoformat() if hasattr(value, "date") else ""


def _activity_rows(sch: Schedule, cpm: CPMResult) -> list[dict[str, object]]:
    """Per-activity rows for the interactive grid + Gantt (float in days, citable metadata).

    Scheduled activities carry their CPM floats; WBS summary rows (which the CPM excludes)
    are included too so the Gantt reads like the source plan, with null floats. Every row also
    carries the FULL Task-Information payload (operator 2026-07-10, ADR-0183): actuals,
    constraint + deadline, work/cost, predecessors/successors with type + lag, resource
    assignments with units/work, the task note, and the mode flags — everything MS Project's
    Task Information dialog shows, so the row-click popup never has to guess.
    """
    by_id = sch.tasks_by_id
    per_day = sch.calendar.working_minutes_per_day or 480
    res_by_id = {r.unique_id: r for r in sch.resources}
    # Each task's GOVERNING calendar name, so the Gantt can shade non-working time per the
    # calendar that task actually runs on (ADR-0243): a 24-hour task shows no weekend gray, a
    # Mon-Fri task still does. A task with no own calendar inherits the project calendar (MSP
    # semantics). The name matches one registered client-side by `SFTimescale.setCalendars`.
    _cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
    _proj_cal_name = sch.calendar.name

    def _task_calendar_name(task: Task) -> str:
        uid = task.calendar_uid
        if uid is not None and uid in _cal_name_by_uid:
            return _cal_name_by_uid[uid]
        return _proj_cal_name

    preds: dict[int, list[dict[str, object]]] = {}
    succs: dict[int, list[dict[str, object]]] = {}
    for rel in sch.relationships:
        lag_days = round(rel.lag_minutes / per_day, 1)
        p_t = by_id.get(rel.predecessor_id)
        s_t = by_id.get(rel.successor_id)
        preds.setdefault(rel.successor_id, []).append(
            {
                "uid": rel.predecessor_id,
                "name": p_t.name if p_t else "",
                "type": rel.type.value,
                "lag_days": lag_days,
            }
        )
        succs.setdefault(rel.predecessor_id, []).append(
            {
                "uid": rel.successor_id,
                "name": s_t.name if s_t else "",
                "type": rel.type.value,
                "lag_days": lag_days,
            }
        )
    # file order (the task list order MS Project displays) so the Gantt nests parents above
    # their children regardless of UID numbering; the indent itself comes from outline_level.
    order = {t.unique_id: i for i, t in enumerate(sch.tasks)}

    def _days(minutes: int | None) -> float | None:
        return None if minutes is None else round(minutes / per_day, 2)

    def _row(task: Task) -> dict[str, object]:
        assignments = []
        for a in task.resource_assignments:
            res = res_by_id.get(a.resource_id)
            assignments.append(
                {
                    "resource": res.name if res else f"Resource {a.resource_id}",
                    "units": a.units,
                    "work_days": _days(a.work_minutes),
                    "remaining_work_days": _days(a.remaining_work_minutes),
                }
            )
        return {
            "unique_id": task.unique_id,
            "name": task.name,
            "wbs": task.wbs or "",
            "start": _iso_date(task.start),
            "finish": _iso_date(task.finish),
            "baseline_start": _iso_date(task.baseline_start),
            "baseline_finish": _iso_date(task.baseline_finish),
            "actual_start": _iso_date(task.actual_start),
            "actual_finish": _iso_date(task.actual_finish),
            "deadline": _iso_date(task.deadline),
            "constraint_type": task.constraint_type.value,
            "constraint_date": _iso_date(task.constraint_date),
            "duration_days": round(
                task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
            ),
            "remaining_duration_days": _days(task.remaining_duration_minutes),
            "baseline_duration_days": _days(task.baseline_duration_minutes),
            "work_days": _days(task.work_minutes),
            "actual_work_days": _days(task.actual_work_minutes),
            "cost": task.cost,
            "actual_cost": task.actual_cost,
            "budgeted_cost": task.budgeted_cost,
            "percent_complete": task.percent_complete,
            "physical_percent_complete": task.physical_percent_complete,
            "complete": task.is_complete or task.actual_finish is not None,
            "is_milestone": task.is_milestone,
            "is_summary": task.is_summary,
            "is_manual": task.is_manual,
            "is_active": task.is_active,
            "is_estimated_duration": task.is_estimated_duration,
            "duration_is_elapsed": task.duration_is_elapsed,
            "outline_level": task.outline_level,
            "order": order[task.unique_id],
            "calendar": _task_calendar_name(task),
            "resource_names": ", ".join(task.resource_names),
            "assignments": assignments,
            "predecessors": preds.get(task.unique_id, []),
            "successors": succs.get(task.unique_id, []),
            "notes": task.notes,
            "source_file": sch.source_file,
            # mapped .mpp custom/extended fields populated on this task (label -> value); the
            # grid offers each as an optional column (ADR-0088 mapping -> ADR-0093 display)
            "custom": dict(task.custom_field_map),
        }

    rows: list[dict[str, object]] = []
    for fr in analyze_floats(sch, cpm):
        task = by_id[fr.unique_id]
        row = _row(task)
        row["is_summary"] = False
        row["total_float_days"] = float(fr.total_float_days)
        row["free_float_days"] = float(fr.free_float_days)
        # progress-aware effective critical (stored flag first, ADR-0150) — what MS Project
        # shows; the pure-logic fr.is_critical collapses on a progressed file
        row["is_critical"] = is_effective_critical(task, float(fr.total_float_days) * per_day)
        rows.append(row)
    for task in sch.tasks:
        if not task.is_summary:
            continue
        row = _row(task)
        row["total_float_days"] = None
        row["free_float_days"] = None
        row["is_critical"] = False
        rows.append(row)
    rows.sort(key=lambda r: cast(int, r["order"]))
    return rows
