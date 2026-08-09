"""The /portfolio page family: every loaded project across the session, one ledger row each.

Monolith split, phase 3 slice 11 (ADR-0375), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry point, seeded by behaviour (the
``/portfolio`` route): THREE names / one contiguous block - the cross-project rollup ledger
(``_portfolio_body``), the resident-memory panel and the version-history row renderer. The
body's sole external referrer is the route - a ``create_app`` closure, which imports downward
and stays put - and the two helpers are body-only. No descents: the family's externals live in
``web/components.py`` / ``web/chrome.py`` / ``web/state.py``, the engine and the model
(``estimate_resident_bytes`` / ``format_bytes`` stay imported by ``app.py`` too - the upload
flash quotes the same estimate, a route concern, not a page-family one).

Layering: ``app`` -> ``portfolio`` -> ``components`` -> ``chrome`` -> ``state`` ->
engine/model. Nothing here imports ``web.app``.
"""

from __future__ import annotations

from urllib.parse import quote

from schedule_forensics.engine.memory import estimate_resident_bytes, format_bytes
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.projects import ProjectVersion
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import _mdY, _panel_head, _prov_chip, _shell_tools
from schedule_forensics.web.state import _UNTITLED_PID, SessionState


def _portfolio_memory_panel(st: SessionState) -> str:
    """A compact resident-memory readout + the operator's warn-threshold control (v4 Feature 2).

    Estimate only, and a warning only — the tool never blocks a load. Lets an operator loading a
    folder of thousands see roughly how much RAM the loaded schedules occupy and tune when the tool
    should flag it."""
    est = estimate_resident_bytes(st.schedules.values())
    warn = st.ram_warn_bytes
    over = est > warn
    cls = "notice warn" if over else "muted"
    warn_gb = warn / 1024**3
    tail = " — over your threshold; you can keep working" if over else ""
    # rank 7: the SHELL around the readout wears the panel contract (headline strip + ⛶ only —
    # no export endpoint serves this estimate, so no ⤓ EXCEL; the readout, the threshold form's
    # field names/action, and the footnote are byte-identical to the pre-shell render).
    return (
        f"<div class=panel>{_panel_head('Memory', tools=_shell_tools())}"
        f'<p class="{cls}">'
        f"{len(st.schedules)} schedule(s) loaded &middot; estimated resident memory "
        f"<b>{format_bytes(est)}</b> (warn at {format_bytes(warn)}){tail}.</p>"
        "<form method=post action=/session/ram-threshold class=inline-form>"
        "<label>Warn above <input type=number name=gb min=1 step=1 "
        f'value="{warn_gb:g}" style="width:6em"> GB</label> '
        "<button type=submit>Update</button></form>"
        "<p class=muted>Schedules stay in memory for instant comparative analysis. This is an "
        "estimate; on a large workstation even a big portfolio fits.</p></div>"
    )


def _portfolio_body(st: SessionState) -> str:
    """The Portfolio Manager rollup: one row per Project (grouped from the loaded files/folders),
    each showing its latest INCLUDED version's headline — computed finish, effective schedule
    margin, DCMA-14 pass/fail — plus its Site/Company (ADR-0260) and an expandable version history
    (each version links to its full report, with the ADR-0259 exclude/restore toggle). Every
    number traces to the engine's cached per-version summary (v4 Feature 2 lazy tier); a Project
    whose latest version won't solve shows "—". The ONLY cross-project page (ADR-0258): analysis
    pages show one Project at a time — the "Analyze" action selects it. No new engine math
    (reuses ``compute_summary``).

    Mission Ops rank 7 (prototype screen 'pf', Program Portfolio): the page wears the panel
    contract — a takeaway header, pf-style KPI tiles (the 3px LEFT-edge ``.ctl-kpi.k-edge``
    variant), the ledger panel shelled with ``_panel_head``/``_shell_tools`` (⤓ EXCEL wired to
    the EXISTING quality-ribbon export; ▦ DATA omitted — the table IS the data), a per-project
    ``_prov_chip`` on every row, and the DCMA/review/excluded chips restyled to the prototype
    pill vocabulary. PRESENTATION ONLY: every figure is one this page already computed/rendered
    (session counts + the cached summaries), and the version-history / exclude-restore /
    memory-threshold forms keep their field names and actions byte-identical."""
    projs = st.projects()
    active = st.active_population()
    with st._lock:
        n_pops = len(st.populations())
    pending = sum(1 for p in projs if p.pending_review)
    excluded_total = sum(1 for p in projs for v in p.versions if v.excluded)
    # Session bookkeeping the page already renders, gathered once for the pf header/KPI tiles
    # (rank 7): loaded-file/version COUNTS only — no engine figure is computed here.
    n_projects = len(projs)
    n_files = len(st.schedules)
    included_total = sum(1 for p in projs for v in p.versions if not v.excluded)
    head_notes = ""
    if pending:
        head_notes += (
            f'<div class="notice info">{pending} Project'
            f"{'s have' if pending != 1 else ' has'} an unresolved duplicate/revision decision "
            "&mdash; expand the row and exclude one copy, or keep both as revisions.</div>"
        )
    if excluded_total:
        head_notes += (
            f'<div class="notice info">{excluded_total} version'
            f"{'s are' if excluded_total != 1 else ' is'} excluded from analysis "
            "(still loaded &mdash; restore any time).</div>"
        )
    # ── pf screen header (rank 7): a complete-sentence takeaway + lede quoting counts the page
    # already renders; the chapter kicker ("PORTFOLIO") comes from _page's spine resolution. ──
    proj_noun = "project" if n_projects == 1 else "projects"
    file_noun = "file" if n_files == 1 else "files"
    takeaway = (
        f"{n_projects} {proj_noun} across {n_files} loaded {file_noun} — one row per project, "
        "headline figures quoted from its latest included version's engine summary and the "
        "DCMA-14 average pooled across its included, solvable versions."
    )
    header = (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        '<p class="page-lede">The one cross-project page: projects are grouped from the files '
        "and folders you loaded, and each row quotes the engine&rsquo;s cached per-version "
        "summary &mdash; computed, never typed.</p>"
    )
    # ── pf-style KPI tiles (prototype 'pf' headline stats — the 3px LEFT-edge variant of the
    # same .ctl-kpi vocabulary). Values are the session counts computed above, nothing new. ──
    pend_cls = " k-warn" if pending else ""
    kpis = (
        "<div class=ctl-kpis>"
        '<div class="ctl-kpi k-edge"><div class=k-label>Projects</div>'
        f"<div class=k-value data-no-i18n>{n_projects}</div>"
        "<div class=k-sub>grouped from your files and folders</div></div>"
        '<div class="ctl-kpi k-edge"><div class=k-label>Schedule files</div>'
        f"<div class=k-value data-no-i18n>{n_files}</div>"
        "<div class=k-sub>loaded versions across every project</div></div>"
        f'<div class="ctl-kpi k-edge{pend_cls}"><div class=k-label>Pending review</div>'
        f"<div class=k-value data-no-i18n>{pending}</div>"
        "<div class=k-sub>duplicate/revision decisions to resolve</div></div>"
        '<div class="ctl-kpi k-edge"><div class=k-label>Excluded</div>'
        f"<div class=k-value data-no-i18n>{excluded_total}</div>"
        "<div class=k-sub>versions set aside &mdash; restore any time</div></div>"
        "</div>"
    )
    # ── the ledger panel shell: headline strip + ⤓/⛶ tools + a one-line takeaway. ▦ DATA is
    # deliberately omitted (the table IS the data); ⤓ EXCEL reuses the EXISTING quality-ribbon
    # endpoint (one row per loaded file) — the home-shell precedent, never a dead link. ──
    take = (
        f"<p class=sf-take data-no-i18n>{n_projects} {proj_noun} · {included_total} version"
        f"{'' if included_total == 1 else 's'} in the analysis"
        + (f" · {excluded_total} excluded" if excluded_total else "")
        + (f" · {pending} pending review" if pending else "")
        + " — expand a row for its version history.</p>"
    )
    tools = _shell_tools(
        export_title="Export the quality ribbon for every loaded file — opens in Excel"
    )
    intro = (
        '<div class=panel data-export="/export/xlsx/ribbon">'
        + _panel_head("Portfolio ledger &mdash; one row per project", tools=tools)
        + take
        + "<p class=muted>Every project loaded in this session, grouped from your files and folders. "
        "Each row is one Project; the headline is its latest included version by data date. The "
        "DCMA-14 average is the view's arithmetic mean of each included, solvable version's "
        "engine-computed pass count &mdash; the one cross-version figure on this table. Expand "
        "a row for the version history, or open any version's full report. Analysis pages show ONE "
        "Project at a time &mdash; pick it here (Analyze) or from the banner.</p>"
        + head_notes
        # OR-01 (ADR-0321): every roll-up heading states the aggregation rule the view actually
        # applied — latest included version vs an average — so the title alone tells the analyst
        # which they are reading. The average column is the ONLY non-latest figure.
        + "<table><tr>"
        "<th scope=col>Project</th><th scope=col>Site / Company</th><th scope=col>Versions</th>"
        "<th scope=col>Latest data date</th><th scope=col>Computed finish — latest version</th>"
        "<th scope=col>Effective margin — latest version</th>"
        "<th scope=col>DCMA-14 — latest version</th>"
        "<th scope=col>Avg DCMA-14 passes — included, solvable versions</th></tr>"
    )
    em = "—"  # the literal U+2014 sentinel (ADR-0219 M2: never the &mdash; entity)
    rows: list[str] = []
    for p in projs:
        # the headline version is the latest NON-excluded one — excluding a stray copy flips the
        # row to the kept file (ADR-0259); a project with every version excluded shows "—"
        latest = next((v for v in reversed(p.versions) if not v.excluded), None)
        sch = st.schedules.get(latest.key) if latest is not None else None
        data_date = finish = margin = dcma = site = em
        if sch is not None:
            if sch.company:
                site = _e(sch.company)
            # the lazy summary tier (v4 Feature 2): finish/margin/DCMA without a fresh CPM per row —
            # cached in-memory and, for uploads, on disk. Equals the fully-computed row (never a
            # different number); an unsolvable version leaves the headline as "—", never a 500.
            summary = st.summary_for(latest.key, sch) if latest is not None else None
            if summary is not None:
                if summary.status_date_iso is not None:
                    data_date = _mdY(summary.status_date_iso)
                if not summary.unsolvable:
                    finish = _mdY(summary.finish_iso)
                    if summary.effective_margin_days is not None:
                        margin = f"{summary.effective_margin_days:g} d"
                    # rank 7: prototype pill vocabulary AROUND the engine's own pass/fail
                    # counts (the values are the summary's, verbatim — only the chip restyles).
                    cls = (
                        "rib-pass sf-pill p-ok"
                        if summary.dcma_fail == 0
                        else "rib-fail sf-pill p-bad"
                    )
                    dcma = (
                        f'<span class="{cls}">{summary.dcma_pass} pass / '
                        f"{summary.dcma_fail} fail</span>"
                    )
        # OR-01 (ADR-0321): the ONE aggregate column — a VIEW-LAYER arithmetic mean over the
        # engine's own per-version pass counts (no new engine math). The pool is every included
        # (non-excluded), SOLVABLE version: an unsolvable audit never ran, so counting its 0
        # would poison the mean with a fake figure (Law 2 — "—" never 0). The cell states the
        # pool size, so a solvability drop is visible right in the figure.
        pass_pool = [
            vsum.dcma_pass
            for v in p.versions
            if not v.excluded
            and (vsch := st.schedules.get(v.key)) is not None
            and not (vsum := st.summary_for(v.key, vsch)).unsolvable
        ]
        avg_dcma = em
        if pass_pool:
            n_pool = len(pass_pool)
            avg_dcma = (
                f"{sum(pass_pool) / n_pool:.1f} of 14 · {n_pool} "
                f"version{'' if n_pool == 1 else 's'}"
            )
        pooled = p.origin == "filename"  # title-less loose file: analyzed as the untitled pool
        select_pid = _UNTITLED_PID if pooled else p.pid
        chips = ""
        if p.needs_attention:
            chips += " <span class=muted>(needs attention)</span>"
        if p.pending_review:
            chips += ' <span class="rib-fail sf-pill p-bad">review</span>'
        if active is not None and select_pid == active[0] and n_pops > 1:
            chips += " <span class=muted>(analyzing)</span>"
        analyze_label = "Analyze the untitled files together" if pooled else "Analyze this project"
        analyze = (
            '<form method=post action="/project/select" style="display:inline">'
            f'<input type=hidden name=pid value="{_e(select_pid)}">'
            '<input type=hidden name=next_url value="/portfolio">'
            f"<button type=submit class=btn-link>{analyze_label} &#8599;</button></form>"
        )
        included = sum(1 for v in p.versions if not v.excluded)
        excluded_n = len(p.versions) - included
        version_count = str(included) + (
            f" <span class=muted>(+{excluded_n} excluded)</span>" if excluded_n else ""
        )
        versions_html = "".join(_portfolio_version_li(st, v) for v in p.versions)
        notices = "".join(f'<div class="notice info">{_e(n)}</div>' for n in p.notices)
        # rank 7: per-project provenance — ONE chip per row, carrying THIS project's latest
        # included file + data date (the multi-project variant of the same _prov_chip
        # vocabulary; i18n-inert so filenames/dates are never translated).
        row_prov = f" {_prov_chip(sch)}" if sch is not None else ""
        rows.append(
            f"<tr><td><details><summary><b>{_e(p.title)}</b>{chips}{row_prov}</summary>"
            f"<ul>{versions_html}</ul>{notices}{analyze}</details></td>"
            f"<td>{site}</td><td>{version_count}</td><td>{data_date}</td><td>{finish}</td>"
            f"<td>{margin}</td><td>{dcma}</td><td>{avg_dcma}</td></tr>"
        )
    return (
        header
        + kpis
        + intro
        + "".join(rows)
        + "</table></div>"
        + _portfolio_memory_panel(st)
        + '\n<script src="/static/panelkit.js"></script>'
    )


def _portfolio_version_li(st: SessionState, v: ProjectVersion) -> str:
    """One version row in a Portfolio project's expandable history: the report link, data date,
    activity count (the differentiators a duplicate-review decision needs), the excluded badge,
    and the ADR-0259 exclude/restore toggle (reversible, never deletes)."""
    sch = st.schedules.get(v.key)
    dd = tasks = ""
    if sch is not None:
        if sch.status_date is not None:
            dd = f" <span class=muted>&middot; data date {_mdY(sch.status_date)}</span>"
        tasks = f" <span class=muted>&middot; {len(non_summary(sch))} activities</span>"
    badge = ' <span class="rib-fail sf-pill p-bad">excluded</span>' if v.excluded else ""
    toggle = (
        '<form method=post action="/project/exclude" style="display:inline">'
        f'<input type=hidden name=key value="{_e(v.key)}">'
        f'<input type=hidden name=excluded value="{0 if v.excluded else 1}">'
        f"<button type=submit class=btn-link>{'Restore' if v.excluded else 'Exclude'}</button>"
        "</form>"
    )
    return (
        f'<li><a class=btn-link href="/analysis/{quote(v.key)}">{_e(v.filename)}</a>'
        f"{dd}{tasks}{badge} &middot; {toggle}</li>"
    )
