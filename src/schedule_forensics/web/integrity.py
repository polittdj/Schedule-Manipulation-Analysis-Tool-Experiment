"""The /integrity page family - the Schedule Integrity & Change Forensics page.

Monolith split, phase 3 slice 4 (ADR-0358), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/integrity`` route's body builder). Here the closure IS the ``_integrity_*`` prefix pair -
``_integrity_header`` + ``_integrity_body``, 2 names / 402 lines - and its only external
referrer is ``create_app``, a route, which imports downward and stays put. Both routes that
serve the family (``/integrity`` and ``/export/{fmt}/integrity``) use only shared machinery
otherwise, so nothing descends into ``components.py`` this slice.

Layering: ``app`` -> ``integrity`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import quote

from schedule_forensics.engine.change_effects import ChangeEffect, compute_change_effects
from schedule_forensics.engine.cpm import (
    CPMError,
    CPMResult,
    offset_to_datetime,
)
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.path_counterfactual import (
    compute_path_counterfactual,
)
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _pair_prov_chip,
    _panel_head,
    _shell_tools,
)


def _integrity_header(
    prior: Schedule,
    current: Schedule,
    prior_cpm: CPMResult,
    current_cpm: CPMResult,
    findings: tuple[Finding, ...],
) -> str:
    """The Chapter-02 beat header for /integrity (Mission Ops rank 6, ADR-0298), modeled on the
    other chapter-header builders: a complete-sentence takeaway h1 + muted lede (the kicker
    itself comes from _page's spine resolution — "Schedule Integrity" is a Chapter 02 title).

    Presentation only, loaded-term guard territory: the takeaway COUNTS the engine's own
    findings for the chosen pair, quotes the worst ENGINE severity verbatim, and reads the
    finish movement from the two versions' engine-computed CPM finishes with the exact
    _what_changed_header wording ("moved out" / "pulled in" / "unchanged" — never an invented
    trend word)."""
    p_label = prior.source_file or prior.name
    c_label = current.source_file or current.name
    prior_fin = offset_to_datetime(prior.project_start, prior_cpm.project_finish, prior.calendar)
    cur_fin = offset_to_datetime(
        current.project_start, current_cpm.project_finish, current.calendar
    )
    fin_delta = (cur_fin.date() - prior_fin.date()).days
    if fin_delta > 0:
        fin = (
            f"; the computed finish moved out {fin_delta} day{'s' if fin_delta != 1 else ''} "
            "between them"
        )
    elif fin_delta < 0:
        n = -fin_delta
        fin = f"; the computed finish pulled in {n} day{'s' if n != 1 else ''} between them"
    else:
        fin = "; the computed finish is unchanged between them"
    if findings:
        severities = {str(f.severity) for f in findings}
        worst = next(
            (s for s in ("HIGH", "MEDIUM", "LOW", "INFO") if s in severities),
            str(findings[0].severity),
        )
        n_f = len(findings)
        takeaway = (
            f"{n_f} manipulation-pattern finding{'s' if n_f != 1 else ''} between {p_label} "
            f"and {c_label} — highest severity {worst}{fin}."
        )
    else:
        takeaway = f"No manipulation-pattern findings between {p_label} and {c_label}{fin}."
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">Version-over-version change forensics for one chosen pair '
        "&mdash; what changed between the baseline and the comparison, what each change did "
        "to the critical / driving path, and what the finish would have been without those "
        "changes. Every statement below is engine-computed and cited (file + UniqueID + "
        "task); this is analysis for review, not an accusation.</p>"
    )


def _integrity_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target_uid: int | None,
    *,
    baseline_idx: int,
    comparison_idx: int,
) -> str:
    """Schedule Integrity & Change Forensics: cited manipulation findings for ONE chosen version
    pair + the counterfactual finish.

    The operator picks exactly TWO files to compare (baseline A vs comparison B) — previously the
    page diffed EVERY consecutive pair, which on many large files ran a counterfactual CPM sweep
    per pair and, if any single pair produced an unsolvable revert, 500'd the whole page. Now one
    pair is analyzed at a time and every heavy compute is guarded, so it never crashes."""
    n = len(schedules)
    labels = [sch.source_file or sch.name for sch in schedules]
    # resolve the chosen pair; default to the two most recent (what changed last). Order prior ->
    # current chronologically (schedules are oldest-first) regardless of pick order, and never let
    # the two collapse to the same file. The baseline guard must also catch an OUT-OF-RANGE index
    # (e.g. comparison_idx==0 makes cur-1 == -1): a negative base would wrap to schedules[-1], the
    # NEWEST file, and silently render a chronologically REVERSED diff (Law 2 fidelity bug) — so we
    # re-pick an in-range neighbour whenever base is out of range or equal to cur.
    cur = comparison_idx if 0 <= comparison_idx < n else n - 1
    base = baseline_idx if 0 <= baseline_idx < n else cur - 1
    if base == cur or not (0 <= base < n):
        base = cur - 1 if cur > 0 else cur + 1
    prior_idx, cur_idx = (base, cur) if base < cur else (cur, base)
    prior_sch, cur_sch = schedules[prior_idx], schedules[cur_idx]
    # The pair's findings are computed ONCE, up front, so the Chapter-02 beat header can restate
    # them (Mission Ops rank 6) and the findings panel below renders the same tuple — one engine
    # call, one truth (never recomputed per panel).
    try:
        findings = detect_manipulation(
            cur_sch, prior_sch, current_cpm=cpms[cur_idx], prior_cpm=cpms[prior_idx]
        )
    except (CPMError, ValueError, KeyError) as exc:  # never 500 the page on one bad pair
        logging.getLogger("schedule_forensics").warning("integrity findings failed: %s", exc)
        findings = ()
    header = _integrity_header(prior_sch, cur_sch, cpms[prior_idx], cpms[cur_idx], findings)
    # the 'A vs B' pair provenance chip (v1→v2 · SOURCE: a → b · DD d1 → d2), reused on every
    # shelled panel of this page — the same _pair_prov_chip vocabulary as /compare (rank 5)
    pair_prov = _pair_prov_chip(prior_sch, cur_sch, prior_idx + 1, cur_idx + 1)

    def _file_opts(selected: int) -> str:
        return "".join(
            f'<option value="{i}"{" selected" if i == selected else ""}>{_e(lb)}</option>'
            for i, lb in enumerate(labels)
        )

    banner_name = f"{labels[prior_idx]} → {labels[cur_idx]}"
    picker = (
        f"<label>Baseline (A) <select name=a>{_file_opts(prior_idx)}</select></label>"
        f"<label>Comparison (B) <select name=b>{_file_opts(cur_idx)}</select></label>"
        if n > 2
        else f'<input type=hidden name=a value="{prior_idx}"><input type=hidden name=b value="{cur_idx}">'
    )
    two_note = (
        "<p class=muted>Pick the <b>two</b> versions to compare — A (baseline) vs B (comparison). "
        "The analysis runs on that one pair.</p>"
        if n > 2
        else ""
    )
    # A/B picker panel wearing the panel-contract shell (rank 6): headline strip + ⛶ + the
    # pair provenance chip. The existing Excel (all findings) link stays — nothing removed.
    picker_head = _panel_head(
        "Version pair &mdash; baseline (A) vs comparison (B)",
        tools=_shell_tools(),
        prov=pair_prov,
    )
    controls = f"""
<div class=panel>{picker_head}<div class=integrity-file data-no-i18n>{_e(banner_name)}</div>
<p class=muted>Every statement below is engine-computed and cited (file + UniqueID + task) —
version-over-version changes and what each change did to the critical / driving path. This is
analysis for review, not an accusation: each finding's course of action asks the analyst to
confirm the change was authorized.</p>
{two_note}
<form method=get action=/integrity class=viz-controls>
{picker}
<button type=submit>Apply</button>
<a class=btn-link href="/export/xlsx/integrity?file={_e(labels[cur_idx])}">&#11015; Excel (all findings)</a>
</form></div>"""

    sections: list[str] = []
    pairs = [(prior_idx, schedules[prior_idx], schedules[cur_idx], cpms[prior_idx], cpms[cur_idx])]
    for i, prior, current, pcpm, ccpm in pairs:
        cur_i = (
            cur_idx  # section header uses the actual comparison index (pairs are not consecutive)
        )
        # `findings` was computed once above (the header restates the SAME tuple — one engine call)
        rows = ""
        findings_data: list[dict[str, object]] = []  # per-finding full citation UIDs for the drill
        for f in findings:
            cites = "; ".join(
                f"UID {c.unique_id} — {c.task_name}" for c in f.citations[:4] if c.unique_id
            )
            uids = [c.unique_id for c in f.citations if c.unique_id]
            fi = len(findings_data)
            findings_data.append({"title": f.title, "uids": uids})
            # clickable "view all N" opens a full, columnable, exportable chart of every cited
            # activity below the table (operator 2026-07-08) — no more truncated "(+66 more)".
            more = (
                f' <a href="#" class=cite-more data-finding="{fi}" '
                f'title="List all {len(uids)} cited activities in a chart you can add columns to '
                f'and export">(+{len(f.citations) - 4} more — view all {len(uids)})</a>'
                if len(f.citations) > 4
                else ""
            )
            rows += (
                f"<tr>"
                f'<td class="sev-{_e(f.severity)}">{_e(f.severity)}</td>'
                f"<td>{_e(f.title)}</td>"
                f"<td>{_e(f.detail)}</td>"
                f"<td class=muted>{_e(f.course_of_action)}</td>"
                f"<td class=cite>{_e(cites)}{more}</td></tr>"
            )
        findings_blob = json.dumps({"file": labels[cur_idx], "findings": findings_data}).replace(
            "<", "\\u003c"
        )
        findings_drill = (
            "<div id=findingsDrill class=findings-drill></div>"
            f'<script type="application/json" id=findingsData>{findings_blob}</script>'
            '<script src="/static/findings_drill.js"></script>'
            if findings_data
            else ""
        )
        # Per-change effect (operator 2026-07-08): revert EACH detected change one at a time and
        # re-run CPM to show its isolated working-day effect on the chosen target UID (or, when no
        # target is set, the last task on the critical path). This catches changes the path
        # counterfactual below misses — e.g. a removed predecessor link whose endpoints STAYED
        # critical (the 188→187 case), which nonetheless moves the target's finish.
        effects_html = ""
        try:
            eff = compute_change_effects(prior, current, ccpm, target_uid=target_uid)
        except (
            CPMError,
            ValueError,
            KeyError,
        ) as exc:  # defense in depth; the engine already guards
            logging.getLogger("schedule_forensics").warning("change effects failed: %s", exc)
            eff = None
        if eff is not None and (eff.per_change or eff.skipped_unsolvable or eff.skipped_capped):
            tgt_label = f"UID {eff.target_uid} ({_e(eff.target_name)})" + (
                " — the last task on the critical path" if eff.target_is_last_critical else ""
            )
            n_measured = len(eff.per_change)
            partial = bool(eff.skipped_unsolvable or eff.skipped_capped)
            # disclose any reverts we could not measure (Law 2: no silent drop)
            notes = []
            if eff.skipped_unsolvable:
                notes.append(
                    f"{eff.skipped_unsolvable} change(s) could not be measured individually — "
                    "reverting one alone reintroduces a logic cycle."
                )
            if eff.skipped_capped:
                cap_note = (
                    f"{eff.skipped_capped} further change(s) beyond the first {n_measured} were "
                    "not individually measured (large diff)."
                )
                if eff.skipped_capped_artifacts:
                    cap_note += (
                        f" {eff.skipped_capped_artifacts} of them match the MS Project "
                        "reschedule-artifact pattern (SNET stamped at the data date on an "
                        "incomplete task) — artifacts are measured last, so the cap starves "
                        "statusing noise, not deliberate changes."
                    )
                notes.append(cap_note)
            skip_note = f"<p class=muted>{' '.join(_e(x) for x in notes)}</p>" if notes else ""
            if not eff.per_change:
                # every detected revert was skipped — disclose it instead of hiding the panel
                total_skipped = eff.skipped_unsolvable + eff.skipped_capped
                effects_html = f"""
<div class="panel change-effects">{_panel_head(f"Effect of each change on {tgt_label}", tools=_shell_tools(), prov=pair_prov)}
<p class=muted>{total_skipped} change(s) were detected between these versions but none could be
measured individually — reverting any one alone reintroduces a logic cycle. (Currently
{_e(eff.target_name)} finishes {_e(eff.actual_target_finish)}.)</p>{skip_note}</div>"""
            else:

                def _eff_rows(changes: list[ChangeEffect]) -> str:
                    out = ""
                    for e in sorted(changes, key=lambda ce: -abs(ce.target_finish_delta_days)):
                        d = e.target_finish_delta_days
                        cls = "fail" if d > 0 else "ok" if d < 0 else "muted"
                        effect_txt = (
                            f"<b class={cls}>{d:+d} wd</b>"
                            if d
                            else "<span class=muted>no effect</span>"
                        )
                        cites = ", ".join(f"UID {u}" for u in e.citation_uids)
                        out += (
                            f"<tr><td>{_e(e.label)}</td><td>{effect_txt}</td>"
                            f"<td>{'+' if e.project_finish_delta_days > 0 else ''}"
                            f"{e.project_finish_delta_days} wd</td>"
                            f"<td class=cite>{_e(cites)}</td></tr>"
                        )
                    return out

                # MS Project "reschedule uncompleted work" stamps an SNET constraint at the data
                # date on every incomplete task it pushes — dozens of REAL (never hidden) but
                # tool-generated constraint rows. Cluster them under an explanatory collapsible
                # so they don't read as deliberate manual constraint edits (operator 2026-07-09).
                artifacts = [e for e in eff.per_change if e.is_reschedule_artifact]
                genuine = [e for e in eff.per_change if not e.is_reschedule_artifact]
                eff_rows = _eff_rows(genuine)
                artifact_html = ""
                n_art_total = len(artifacts) + eff.skipped_capped_artifacts
                if artifacts:
                    n_noeff = sum(1 for e in artifacts if not e.target_finish_delta_days)
                    art_note = (
                        f"{n_art_total} constraint change(s) look like the MS Project "
                        "&ldquo;reschedule uncompleted work&rdquo; statusing artifact: the later "
                        "version carries a Start-No-Earlier-Than constraint stamped exactly at "
                        "its own data date. MS Project writes these automatically when "
                        "incomplete work is pushed past the status date &mdash; they are real "
                        "file differences, but usually a statusing side effect rather than "
                        "manual constraint edits. "
                        f"{n_noeff} of {len(artifacts)} have no effect on the target finish."
                    )
                    if eff.skipped_capped_artifacts:
                        art_note += (
                            f" {eff.skipped_capped_artifacts} further artifact-pattern change(s) "
                            "were detected but not individually measured (measurement cap; see "
                            "the note above) and are not in the table below."
                        )
                    artifact_html = f"""
<details class=artifact-cluster><summary>&#9432; {n_art_total} MS Project reschedule
artifact(s) &mdash; SNET stamped at the data date (click to expand)</summary>
<p class=muted>{art_note}</p>
<table class=integrity-table><tr><th scope=col>Change (reverted)</th>
<th scope=col>Effect on target finish</th><th scope=col>Effect on project finish</th>
<th scope=col>Citations</th></tr>{_eff_rows(artifacts)}</table></details>"""
                agg = eff.aggregate_target_finish_delta_days
                agg_txt = (
                    f"<b class={'fail' if agg > 0 else 'ok' if agg < 0 else 'muted'}>{agg:+d} "
                    f"working day(s)</b>"
                )
                # "all changes together" line — the aggregate folds in ONLY the individually-
                # measured reverts, so state that count honestly and, when any change was skipped/
                # capped, say the total EXCLUDES them rather than over-claiming "every change".
                scope_txt = (
                    f"the {n_measured} individually-measured change(s) reverted together (the "
                    "skipped change(s) noted below are excluded)"
                    if partial
                    else f"all {n_measured} change(s) reverted together"
                )
                agg_line = (
                    f" With {scope_txt}, {_e(eff.target_name)} would move {agg_txt} (currently "
                    f"{_e(eff.actual_target_finish)})."
                    if eff.aggregate_solved
                    else f" (Currently {_e(eff.target_name)} finishes "
                    f"{_e(eff.actual_target_finish)}; reverting these changes together would "
                    "reintroduce a logic cycle, so only the per-change effects above are shown.)"
                )
                main_table = (
                    "<table class=integrity-table><tr><th scope=col>Change (reverted)</th>"
                    "<th scope=col>Effect on target finish</th>"
                    "<th scope=col>Effect on project finish</th>"
                    f"<th scope=col>Citations</th></tr>{eff_rows}</table>"
                    if eff_rows
                    else "<p class=muted>Every change between these versions is an MS Project "
                    "reschedule artifact (see below).</p>"
                )
                effects_html = f"""
<div class="panel change-effects">{_panel_head(f"Effect of each change on {tgt_label}", tools=_shell_tools(), prov=pair_prov)}
<p class=muted>For each change below, the tool reverts <b>only that change</b> on the later version
and re-runs CPM. A <b class=fail>positive</b> value is the working-day slip the change
<b>hid</b> from the target's finish (restoring it would push the finish out that far); a
<b class=ok>negative</b> value means the change pushed the finish out.{agg_line}</p>{skip_note}
{main_table}{artifact_html}</div>"""
        cf_html = ""
        try:
            cf = compute_path_counterfactual(prior, current, pcpm, ccpm, target_uid=target_uid)
        except (CPMError, ValueError, KeyError) as exc:
            logging.getLogger("schedule_forensics").warning("path counterfactual failed: %s", exc)
            cf = None
        if cf is not None and cf.reverted:
            delta_txt = (
                f" — <b class=fail>{cf.finish_delta_days} working day(s)</b> of apparent"
                " recovery came from the changes themselves, not from performed work"
                if cf.finish_delta_days > 0
                else ""
            )
            reverted = ", ".join(str(r.uid) for r in cf.reverted[:12])
            tgt = ""
            if cf.target_uid is not None and cf.target_counterfactual_finish:
                tgt = (
                    f"<p>Target UID {cf.target_uid} ({_e(cf.target_name or '')}): would have"
                    f" finished <b>{_e(cf.target_counterfactual_finish)}</b> instead of"
                    f" <b>{_e(cf.target_actual_finish or '?')}</b>.</p>"
                )
            cf_html = f"""
<div class="panel counterfactual">{_panel_head("Counterfactual — without these changes", tools=_shell_tools(), prov=pair_prov)}
<p>Activities left the critical/driving path after their own duration / logic / constraints
changed (UIDs {_e(reverted)}). Reverting exactly those changes and re-running CPM: the project
finish would have been <b>{_e(cf.counterfactual_finish)}</b> instead of the reported
<b>{_e(cf.actual_finish)}</b>{delta_txt}.</p>{tgt}</div>"""
        empty = (
            "<p class=muted>No manipulation-pattern findings between these two versions.</p>"
            if not rows
            else ""
        )
        # Findings panel wearing the verdict-band wash (rank 6, the /compare rank-5 precedent):
        # the tone comes from the ENGINE's own worst severity (HIGH → --bad, any → --warn,
        # none → --ok) — never re-judged here — and the takeaway line only COUNTS the engine's
        # findings (loaded-term guard territory: no wording added around the engine's titles).
        severities = {str(f.severity) for f in findings}
        if "HIGH" in severities:
            band_cls = "vb-at-risk"
        elif severities:
            band_cls = "vb-watch"
        else:
            band_cls = "vb-on-track"
        if findings:
            worst = next(
                (s for s in ("HIGH", "MEDIUM", "LOW", "INFO") if s in severities),
                str(findings[0].severity),
            )
            n_f = len(findings)
            find_take = (
                f"{n_f} manipulation-pattern finding{'s' if n_f != 1 else ''} between these two "
                f"versions &mdash; highest severity {worst}; each finding, its course of action "
                "and its citations are the engine's own output, listed below."
            )
        else:
            find_take = "No manipulation-pattern findings between these two versions."
        # ⤓ EXCEL rides the EXISTING /export/xlsx/integrity endpoint (exactly these findings —
        # never a dead link); the table is its own data drawer, so no ▦ DATA (the /evm precedent).
        find_head = _panel_head(
            f"{_e(labels[i])} &rarr; {_e(labels[cur_i])}",
            tools=_shell_tools(
                export_title="Export this pair's integrity findings — opens in Excel"
            ),
            prov=pair_prov,
        )
        export_url = f"/export/xlsx/integrity?file={quote(labels[cur_i], safe='')}"
        sections.append(f"""
<div class="panel verdict-band vb-stack {band_cls}" data-export="{export_url}">{find_head}
<p class=sf-take data-no-i18n>{find_take}</p>
{f"<table class=integrity-table><tr><th scope=col>Severity</th><th scope=col>Finding</th><th scope=col>Detail</th><th scope=col>Course of action</th><th scope=col>Citations</th></tr>{rows}</table>" if rows else empty}
{findings_drill}</div>
{effects_html}
{cf_html}""")

    if not sections:
        sections.append(
            "<div class=panel><p class=muted>No version pair matches the selected file.</p></div>"
        )
    return header + controls + "".join(sections) + '\n<script src="/static/panelkit.js"></script>'
