# Handoff — 2026-08-07 (phase 3 slice 6: the trend family out of the monolith; ADR-0364; v1.0.175)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0364, **v1.0.175** (shipped code changed:
> `app.py`, `components.py`, new `web/trend.py` — wheel + nine installers REBUILT after the
> bump), SCHEMA 2.11.0. Slice 5 (#550, ADR-0363) squash-merged by the operator earlier the
> same day; the queue continued at `trend`.
>
> ## ADR-0364 — phase 3 slice 6: /trend out of the monolith; the sweep's first real candidate
> The stale "trend 348" census RE-MEASURED: the behaviour-seeded closure gives 7 names /
> 502 lines partitioned THREE ways — a 3-name / 424-line CLOSED move set
> (`_how_it_moved_header` · `_trend_body` · `_trend_data`) into **`web/trend.py`** (483
> lines); the `_focus_rows`/`_focus_panel` pair DESCENDED into `components.py` (2-family:
> `_trend_body` embeds it AND the /compare route calls it — and unlike every earlier
> descent, BOTH consumers are render-proven: `/trend?target=3` + the new
> `/compare [target-set]` pseudo-route, a set-target POST sequenced AFTER the target-less
> sweep); `_parse_uid` (10 families) and `_sources_line` (8) stay. `export_trend` stays
> whole (builds from `compute_quality_trend` directly — that import stays in app.py while
> trend.py imports it independently). `app.py` 17,681 → 17,197. NOTE: `web.trend` sorts
> AFTER `web.state` — the re-export block lands at the END of the import section, unlike
> every previous page module. Proof: 5/5 per-definition byte-identity; multiset 57 added /
> 1 removed (the one removal = components' cpm import line re-added widened with
> `offset_to_datetime`, the pair's single genuine dependency); **80/80 routes
> byte-identical**; falsified in BOTH new locations, both EXACT; five guard mutations
> red→restored md5-verified (enumeration guard's fifth consecutive live catch). **Sweep 1
> found its first REAL candidate**: `test_manifest_projection_memo` patches
> `app_mod.non_summary` — cleared by verification (the spied path is /api/dashboard's
> projection, which never crosses a moved member; app.py still binds it, 41 usages).
> Process note: a 300s-timeout Bash call that gets "moved to background" RESTARTS its
> command — the falsification harness ran twice concurrently until caught (backups verified
> clean by anchor-grep, strays killed, both cases re-run serially foreground).
>
> ## Next
> Phase 3 resumes at **ssi 335** (stale census — RE-MEASURE first; margin's "379" measured
> 417+21 three ways, trend's "348" measured 424+55+shared). Then: driving-corridor fixture ·
> the three page-lede-less pages (/briefing, /path, /compare) · /groups Activities counting
> summary rows (ADR-0343) · installers vs known-good constraints · the P80/P90
> recurring-calendar-exception residual (own unit) · Phase 6 docs. **Operator:** license ·
> branch-protection · proprietary reruns · OR-04 · whether the July mpp/ oracle should
> re-export under replace semantics.
>
> ## Carried forward
> ADR-0353..0363 closed — do not re-open. The slice recipe held for its sixth outing; new
> permanent additions: (1) a member at 0 moved may be an ORACLE gap — ask what would
> EXECUTE it (an export, a POST-lit branch, a query param) and widen the oracle before
> calling it unreachable (margin's `_wmpd_label`, trend's `/compare [target-set]`);
> (2) long-running mutate-then-restore harnesses must NOT ride a foreground Bash call that
> can be timeout-backgrounded — the restart runs the mutation twice; keep each
> mutate→snapshot→restore cycle its own short call. A number written mid-session is not a
> measurement (slice 6's "482" was pre-I001-fix; wc says 483). The workbook Mean/StdDev
> cells are UNWEIGHTED. A parity delta is a claim about INPUTS first. `pydantic>=2` NOT a
> safe floor (2.6); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). `ruff check .`
> whole tree as `python -m ruff` (stale 0.15.8 shadows PATH). `grep -c` exits 1 on zero —
> chain with `;`. The /analysis focus→tip family is load-sensitive — do NOT chase. bandit
> B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`. Full suite >
> 10-min foreground timeout — background with `python -u` and READ the tail; never mutate
> the tree (docs included) while it runs.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
