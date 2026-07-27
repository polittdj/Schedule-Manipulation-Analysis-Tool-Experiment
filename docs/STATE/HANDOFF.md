# Handoff — 2026-07-27h (the windows CI leg now EXECUTES the symlink + drive-root shapes; ADR-0300; v1.0.105)

> ## STATUS (current) — ADR-0300 shipped. `main` at `4f3916b`. Version **1.0.105**. Highest ADR **ADR-0300**.
> Branch `claude/schedule-forensics-continue-gkju7l`, restarted from merged `main`. **PR #452 open
> (draft)** — the windows CI hardening below. #451 merged.
>
> - **THE LAST UNPROVEN CLAIM FROM THE DOWNLOADER WORK IS CLOSED.** The previous handoff's option
>   (a). `installer-smoke.yml`'s windows job ran the download and from-checkout branches only, so the
>   two most recent destructive fixes — a **link-shaped MPXJ source** and a **drive-root install**,
>   both diagnosed on the operator's own Windows — rested on the executed *bash* twin plus a static
>   text guard over the `.ps1`. Both now **execute on windows-latest**, and both legs are
>   mutation-proved to be able to fail.
> - **GREEN, AND THE LOG WAS READ, NOT TRUSTED.** Zero annotations emitted; both reparse-point
>   shapes were creatable; `subst X:` gave a usable drive root (no `C:\` fallback). The job's MPXJ
>   lines are now a full branch census of section 3b: `deployed` (checkout) · `downloaded and
>   SHA-256 verified` (one-file) · `deployed` (python-only) · `deployed` (link setup) ·
>   `already installed` ×2 (Junction, SymbolicLink) · `deployed` (mutation) · `no MPXJ converter
>   found` (drive root, offline). 3 m 40 s, eleven steps, seven installs.
> - **MEASURED, NOT ASSUMED — the fact to carry forward:** Windows PowerShell 5.1's `Resolve-Path`
>   returns a reparse point's **own spelling** for a junction *and* a symlink, while `.Target` gives
>   the real destination with **no** `\??\` prefix. So `Resolve-SfPath`'s one-hop follow is both
>   necessary and sufficient, and the bash defect's cause is confirmed present in PowerShell too.
> - **Staging's independence is now proved ON WINDOWS, not by parity:** with the self-copy skip
>   mutated to `if ($false)` and the source pointed AT the destination, the converter came back
>   byte-identical and only the message degraded to `deployed`.
> - **⚠️ MY OWN NEW GUARD WAS WRONG FIRST, and this is the lesson to keep:** the test asserting the
>   windows job still runs both shapes **passed** with the reparse-point loop gutted to
>   `@("Directory")`, and **passed again** with every `subst` call removed — the explanatory comments
>   and a `::warning::` string satisfied it. **A guard that greps prose measures the documentation,
>   not the behaviour.** Fixed by stripping comment lines and step names first and pinning an
>   *invocation*. Six mutations now fail as required (file backups, ADR-0298).
> - **ADR-0300 existed in 13 shipped citations but not on disk** — the previous session filed the
>   symlink defect as ADR-0299 *Addendum 2* while the installers, templates and tests all cite
>   `ADR-0300`. Now written; `test_state_docs` anchors on the highest ADR **on disk**, so a citation
>   pointing past the end of the record is invisible to it. **A dangling citation is a claim with no
>   reachable source.**
> - **Gate:** installer suite 50 → **52**; ruff / ruff format / mypy --strict / bandit / `node
>   --check` clean; windows `timeout-minutes` 15 → 30. No `src/` change, so the embedded wheel stays
>   in lockstep at 1.0.105.
> - **NEXT: AXIS-TITLES batch 1** — drive `PENDING` (16) toward empty, ~5 modules/PR per the spec's
>   §3 caption table in `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md`; guard/ledger is
>   `tests/web/test_axis_titles.py`. ⚠️ That spec had **five false premises** last time — verify every
>   symbol and token it names actually exists before writing a line (ADR-0298). Then **CRISPNESS 11px
>   floor ONLY** (`--sf-fs-axis-title` is already the seam; ⚠️ its §2.1 claim that `sf-themes.css`
>   "was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4), parked on the
>   operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the 11 `NO_SVG_AXES`
>   visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **STILL OWED:** AXIS-TITLES batch 0's four-theme visual pass (console / daylight / apollo /
>   jarvis at 90–125%), outstanding since 2026-07-27b. **⚠️ THE STATED BLOCKER IS FALSE IN THIS
>   CONTAINER — a headless browser IS usable, verified this session, not assumed:**
>   `pip install playwright` (PyPI is reachable), then launch with an explicit
>   `executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"`. The pip-installed
>   driver expects build 1228 and the image ships **1194**, so a bare `p.chromium.launch()` fails
>   with "Executable doesn't exist"; `executable_path` is the whole fix, and
>   `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers` is already set. Rendered a page and read back
>   `navigator.userAgent` to confirm. **What is verified is the BROWSER, not the whole pass** — the
>   rest of the chain (serve the app, load a schedule, screenshot each theme, judge it) is untested,
>   so treat the pass as unblocked-but-unproven. Prior sessions' CSP note still applies: use
>   `page.evaluate` / `eval_on_selector`, never `wait_for_function` (`script-src 'self'` blocks
>   string-eval — which is the air-gap working).
>   Also possible-but-not-done: a standalone PowerShell harness for the 3b block (the twin of
>   `_run_mpxj_block`) would make windows mutation cheap, but running the *whole* installer is what
>   caught the `java -version` probe abort, so it is an addition, never a substitute.
> - **DEPLOY NOTE (operator has no local clone):** download `installer/install-tier2.ps1` from the
>   GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   That one file fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit. An
>   existing converter is never destroyed — not by a re-run, a failed download, a self-referential
>   `SF_MPXJ_HOME`, a junction, or a symlink; and a drive root no longer aborts the install. All of
>   that is now executed on Windows in CI. Offline: Code → Download ZIP, run from inside the
>   extracted folder.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
