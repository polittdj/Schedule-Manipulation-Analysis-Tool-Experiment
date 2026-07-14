# Kickoff prompt for the next session

Paste the block below verbatim to start the next session.

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` first**, then the fresh
findings in **`docs/STATE/AUDIT-2026-07-14.md`** — a read-only, falsification-oriented re-audit (3
parallel deep-read passes + operator re-validation) was just completed. **No fixes were applied** in the
audit session; it only wrote the report and refreshed the state docs.

**Current state:** `main` is green at **v1.0.34** (HEAD `869a8d0`), highest ADR **0222** (0000–0222
contiguous), gate fully green (ruff / ruff format / mypy --strict / bandit exit 0 / **2117 tests** /
doc-drift guard / metric-dictionary in sync). Your designated branch `claude/smat-audit-remediation-eeckdi`
sits at `origin/main` — **always `git fetch origin` and branch fresh from `origin/main`** for each new
theme (squash-merges make stacked branches conflict). Model id `claude-opus-4-8` — never put it in any
commit/PR/code, chat replies only.

**Two non-negotiable laws (CLAUDE.md):** (1) **Data sovereignty** — no schedule content leaves the
machine; AI is loopback-only and fails closed; runtime I/O is std-lib only; never commit real
`.mpp/.xlsx/.aft/.xer/.docx`. (2) **Fidelity over speed** — numbers must match Acumen/SSI; never
fabricate (an NA/undefined value must read "—", never a placeholder 0); parity is gate-locked
(`pytest -m parity`). Do **not** touch `engine/` for a presentation-only fix. Confirm each fix against
the evidence in the audit report before changing code; several findings carry a "verify X first" caveat.

**Per-PR workflow:** fresh branch off `origin/main` → make the fix → full gate (ruff / ruff format
--check / mypy --strict / bandit **read the exit code directly, not through a pipe** / `pytest -q` /
`node --check` for JS) → four-theme Chromium check for any UI change → if code changed, bump
`pyproject.toml` version + rebuild the wheel (`python -m build --wheel --outdir dist/wheel`) + the 9
installers (`python tools/installer/build_installers.py dist/wheel/schedule_forensics-<v>-py3-none-any.whl`)
so the version-lockstep test stays green → new ADR + refresh `HANDOFF.md` and `SESSION-LOG.md` with the
new ADR token in **both** (the drift guard checks it) → commit (with the required `Co-Authored-By` /
`Claude-Session` trailers) → push `-u origin claude/smat-audit-remediation-eeckdi` → open a **draft PR**
→ `subscribe_pr_activity`. After merge: restart the branch fresh from `origin/main`.

**Your mandate:** work the remediation backlog **one PR per theme, most value-per-risk first**, in the
order below. Nothing is a CRITICAL/egress defect — these are fidelity, dead-defense-in-depth,
test-false-confidence, and doc-drift fixes.

1. **NEW-1 (Medium, fidelity — do first).** The metric-catalog `applicable` flag (ADR-0219) marks the
   two float ribbon extras `avg_float_days`/`max_float_days` as a real value even when their incomplete-
   float population is empty (`metric_catalog.py:192-200` defaults `applicable=True`; `ribbon.py:216-217`
   returns `0.0` on empty) → a fully-complete schedule shows "Avg/Max Float 0.0 days" in the Metric
   Workbench + Excel instead of "—". Fix: mark those two NA when the population is 0; pin with an
   all-complete-schedule fixture. Small, contained.

2. **PR 5 — H3 + L8 (24-hour calendar parse).** The last High. **VERIFY-FIRST:** convert a 24h `.mpp`
   through the vendored MPXJ path and inspect whether it emits `00:00→00:00` or `00:00→24:00` BEFORE
   fixing. If `00:00→00:00`, fix `working_time_span` (`importers/_common.py:189-203`) to treat
   `from==0 and to==0` as `(0,1440)`; add an MSPDI 24h fixture + test; re-run parity; do the sibling
   XER fix (L8, `importers/xer.py:621-663`, shared root).

3. **PR 6 — H1 + M4 + M5 (AI figure-gate hardening — highest care, Law 2).** (a) gate `_ai_translate`
   with `citations.preserves_figures`, fall back to source on mismatch; (b) extend `figure_tokens`
   (`ai/citations.py:38-49`) with a bounded number-word lexicon; (c) add the missing accusatory terms +
   stem matching to `_LOADED_TERMS` (`ai/citations.py:58-89`). Adversarial tests for each.

4. **PR 7 — M6 + L3 (+ L4) (wire the dead CUI defenses).** Call `configure_logging()`
   (`logging_redaction.py`) and `assert_local_only()` (`net_guard.py:146`) once at process start
   (`launcher.main()` + top of `create_app()`); add a startup-assertion test. Optionally extend the
   egress forbidden-set (L4).

5. **PR 8 — M7 + M8 + L5/NEW-3 + M11 + NEW-2 (test harnesses + guards).** Chartframe/scurve/curves
   hover-callout node harness (M7); the workbench.js numeric-vs-lexical **sort** harness (M8 remainder);
   enumerate `app.routes` in `tests/web/test_airgap.py` instead of the hard-coded list (L5/NEW-3, covers
   the new `/scorecards` + `/margin`); a durable version-sync guard asserting the pyproject version
   appears in HANDOFF (M11); and fit the margin-dashboard erosion only over a consistent target basis
   with disclosure (NEW-2).

6. **PR 9 — low/nit cleanup, batched.** L6 (pre-commit archive extensions / magic-byte sniff), L7 (MSPDI
   decode ladder like XER's), L9 (XER `target_*`→`baseline_*` — needs a P6 reference check + an ADR),
   N1 (`xlsx_read` decompression cap), N2 (stored-slack ROUND_HALF_UP).

**Do NOT** re-report the 16 resolved 2026-07-13 findings (H2, M1, M2, M3, M9, M10, M12, M13, M14, L1,
L2, L10, L11, L12, L13, N3), the VERIFIED-CLEAN items, or the dismissed pip-audit noise. If the operator
provides new reference files or a live-testing request instead, that takes priority over the roadmap.
