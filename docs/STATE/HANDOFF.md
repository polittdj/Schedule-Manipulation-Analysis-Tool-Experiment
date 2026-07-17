# Handoff — 2026-07-17 (ignore-toggle copy truth + page-family alignment, the ADR-0250 queued decision resolved; v1.0.60; highest ADR 0251)

> ## STATUS (current) — ADR-0251: the ADR-0250 queued finding (`ignore-toggles-noop-on-dated`) resolved by OPERATOR DECISION (option 3: fix the copy + align the page families — NO behavior change). Lead re-verified the finding and both candidate fixes empirically before asking. Version 1.0.59 → 1.0.60 (wheel + 9 installers in lockstep). Full gate green incl. `parity`.
>
> - **The evidence that drove the decision (lead-verified, executable):** on fully-dated files the
>   `compute_driving_slack` ignore flags change **0/43** traced slacks (Project5) and **6/783**
>   (leveled Large Test File — a calendar-basis artifact, driving path byte-identical 61/61).
>   Option (a) — genuinely clearing stored dates + re-solving CPM — **destroys the SSI anchor**:
>   driving path 61→328, **58/60 SSI-critical tasks fall off**, slack error up to ~922 d,
>   exact 777/783 → 2/783. The operator's SSI UID-152 export was captured with SSI's OWN ignore
>   options **ON** and matches the **stored-date** trace — SSI never discards stored dates, so the
>   current behavior IS the correct semantics and option (a) would violate Law 2.
> - **Two page families share the toggle labels but diverge (route-verified):**
>   **A — SSI-parity trace** (`/path`, `/api/driving`, `/export/…/path/…`): flags → stored dates
>   govern; fully-dated file traces identically. **B — counterfactual re-solve** (`/driving-path`
>   page + tiers + its Excel, `/evolution` + corridor): `_optioned_versions` strips constraints +
>   clears incomplete tasks' dates + re-runs CPM (leveled: driving tier 60→1 under il, →327 both) —
>   a deliberate, bannered "pure logic" view that will NOT match SSI/MSP.
> - **What changed (copy + tests only, no behavior):** family-A docstrings/tooltips
>   (`engine/driving_slack.py`: `compute_driving_slack` / `strip_constraints` / `endpoint`;
>   `web/app.py`: `/path` toggle titles, `_driving_data`) now state the stored-date-first truth;
>   family-B copy (`_optioned_versions` docstring + banner, `_trace_options_form` +
>   `_driving_path_body` titles) now names itself a counterfactual that diverges from SSI's
>   same-named options by design. Regression pins:
>   `test_ignore_flags_are_stored_date_noops_on_a_fully_dated_file` (engine) +
>   `test_ignore_options_diverge_by_page_family_as_documented` (routes: API rows byte-identical
>   under every flag combo; `/driving-path` tiers genuinely move + banner discloses).
> - **Adversarial verify (ADR-0240):** 7-agent orchestrated pass over the diff — 6 refuters
>   (engine no-op / SSI anchor / mechanism / routes / copy sweep / state docs) re-derived every
>   claim, **0 refuted, all high-confidence** (58/60, 921.95 d, 61→328, 777/783 reproduced
>   exactly). The completeness critic surfaced **4 pre-existing mixed-basis surfaces** (lead-
>   confirmed): `/evolution` stepper fetches `/api/evolution` (no option params → stored schedule
>   even with toggles on); `/driving-path`'s full-trace Excel is the family-A stored-date route;
>   `_completed_on_path_panel` docstring claimed stepper-parity; drill-added field columns come
>   from base `/api/analysis`. All four got **disclosure fixes** (scoped banner, export-link
>   title, docstring, drill caption) — the behavior unification is QUEUED, not guessed.
> - **State:** v1.0.60; **ADR-0251**; wheel `dist/wheel/schedule_forensics-1.0.60-py3-none-any.whl`
>   rebuilt + all 9 installers regenerated (lockstep test green); `REPO-INVENTORY.md` stamp/census
>   and `NEXT-SESSION-PROMPT.md` refreshed; full gate green (ruff / ruff format --check / mypy
>   --strict / bandit exit 0 / node --check / full pytest incl. the `parity` gate).
> - **NEXT — the standing queue, unchanged order:** **#13** XER per-task calendars → base-CPM
>   single-calendar fail-soft disclosure (**#26**) → **F3c** parameterized expected margin → roles
>   front-end (v4 F4). Deferred perf (parked in ADR-0249's harness): import peak memory rides MSPDI
>   streaming, AI-cancellation rides its own PR — deterministic gates only, never wall-clock.
>   Optional: extend per-task Gantt shading to the path-evolution + SRA grids. New from the
>   ADR-0251 verify (behavior, own PR each): unify family-B option plumbing — forward the toggles
>   to `/api/evolution`, decide the full-trace export's basis, option-solve or hide drill field
>   columns (each needs golden re-validation). If a true un-leveled
>   SSI comparison is ever wanted, that is a NEW option validated against a NEW SSI export
>   (ADR-0251 consequences), never a redefinition of the existing toggles. Operator-side (no code):
>   the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI + the §4 root-vs-mpp
>   `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
