# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins.)

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` FIRST** — its top
section is the current state and the NEXT queue. As of this file's last refresh that meant:
`main` green at **v1.0.46**, highest ADR **0234**, full gate green (ruff / ruff format --check /
mypy --strict / bandit exit 0 / node --check / full pytest incl. the `parity` gate).

**Two non-negotiable laws (CLAUDE.md):** (1) **Data sovereignty (CUI)** — no schedule content or
derived metric leaves the machine; AI loopback-only, fails closed; runtime I/O std-lib only; never
commit a real CUI schedule (the pre-commit guard blocks blocked-extension files outside the
allowlists). (2) **Fidelity over speed** — numbers must match the reference tools (Acumen Fuse
v8.11.0 / SSI / MSP) on the same inputs; never fabricate (NA reads "—", never a placeholder 0);
parity is gate-locked (`pytest -m parity`); never weaken a test or guard.

**Per-PR workflow:** fresh branch off `origin/main` (always `git fetch origin` first; squash-merges
make stacked branches conflict) → make the change → full gate (ruff / ruff format --check / mypy
--strict / bandit **exit code read directly** / `pytest -q` / `node --check` for JS) → 4-theme
Chromium check for any UI change → bump `pyproject.toml` + rebuild the wheel
(`python -m build --wheel --outdir dist/wheel`) + the 9 installers
(`python tools/installer/build_installers.py dist/wheel/schedule_forensics-<v>-py3-none-any.whl`)
→ new ADR + refresh `HANDOFF.md` and `SESSION-LOG.md` in the same commit (drift guard) → commit
with the required trailers → push → **draft PR** → `subscribe_pr_activity`. After a merge, restart
the branch fresh from `origin/main`. Never put the model id in any commit/PR/code.

**The work queue (rationale + goldens in HANDOFF's NEXT section and the approved plan):**

1. **#10 PR-D — `/groups` UI:** saved filter/group pickers (A–Z via `saved_*_union`), interactive
   prompt inputs ("Date Range…"), highlight toggle + `data-highlight-uids` + `static/highlight.js`,
   extended filter banner, per-page group banding. Design pre-written in
   `docs/STATE/msp-filters-research/03-plumbing-integration.md`.
2. **PR-U1 — operator UI directives (NEXT-PROMPT 07/16):** fix the non-working Gantt filter
   buttons; find-task-by-name(/part) on every Gantt; a per-file/version selector on the
   critical-path page, "Where We Stand," and other multi-file pages — never mix files' data.
3. **PR-M1 — `/standards` metrics page** (DCMA-14 + NASA/Fuse indices re-projection, SEM rows
   showing "—" until built) and **PR-M2 — `engine/metrics/sem.py`** (the 9 unbuilt Schedule
   Execution Metrics; verbatim goldens exist for TWO pairs — P2/P5 and Large Test File/File2 —
   in the Fuse DCMA reports' `Industry-Standards` sheets; each metric needs a MetricDoc + AUDIT
   row, the 1:1 test enforces it).
4. **PR-R1/R2/R3 — validated-audit remediation:** R1 AI figure-gate (gate `_ai_translate` with
   `preserves_figures`; number-word lexicon in `figure_tokens`; stem matching in `_LOADED_TERMS`);
   R2 wire the dead Law-1 defenses (`configure_logging` + `assert_local_only` at startup + test),
   air-gap test enumerates `app.routes`, version-pin guard in state docs; R3 margin-erosion
   single-basis fit, XER worked-weekend exceptions, egress-set additions, and the 24h-calendar
   MPXJ golden (SSI pair: updated3 UID-155 slack 32d ↔ updated4 24h slack 18d).
5. **PR-P1 — validated perf items** (CoPilot #3/#4/#8/#9/#10 + summary-logic edge guard; the
   refuted claims #1/#5/#6/#7-race are documented, do not "fix" them).
6. **#13** XER per-task calendars (operator will re-add real `.xer`) → **F3c** parameterized
   expected margin → **roles front-end** (v4 F4).

Work autonomously: full gate before every commit, draft PR per increment, pause only for genuinely
operator-only decisions.
