# Handoff — 2026-08-17 (c) (audit units 5–9: REC-01 corrects ADR-0407 · MC-01 · TST-01 · JS-01 · SRA-EXPORT-STALE-SCOPE; ADR-0413..0417; v1.0.211 shipped)

> ## STATUS (current) — audit CONTINUING on `claude/polaris-audit-resume-3ubkxc`.
> Highest ADR now **0417**. **SHIPPED code changed** (`recommendations.py`, `briefing.py`,
> `sra.py`, `jcl.py`, `analysis.py`, `app.py`, `static/chrome.js`) — version **v1.0.210 →
> v1.0.211**, SCHEMA 2.11.0 unchanged, wheel + nine installers rebuilt. ADR-0409/0410/0411
> **and now 0412** are MERGED on main (PR #595, #596) — the branch started clean from
> `origin/main` at ff89731. The live audit ledger is `docs/STATE/AUDIT-2026-08-16.md`.
>
> ## What landed — five defects, every one measured before and after
> **ADR-0413 · REC-01 — the audit audited its own output, and ADR-0407 was wrong.** ADR-0407
> justified the `actual_start_driven` disclosure's OPPORTUNITY category by claiming it could
> never become "a threat row or a recovery action". True of `web/risks.py`; **false of the
> tree** — `ai/briefing.py` has no category gate and `_quantify` quantifies every finding
> uniformly. Measured: the note reached briefing §5.2's **"Potential recovery" = 20 wd**, §6's
> **"Expected effect" = 20 wd**, §6.2's *"up to about 20 workday(s) … potentially recoverable"*
> and the `/risks` card at **20/25 `rk-extreme`** — on a finding whose own text says re-tying
> logic "cannot and should not move a date that already happened", i.e. recovery zero. Fixed by
> `Finding.is_disclosure` (declared, not inferred — `driving_path` is INFO/OPPORTUNITY too and
> IS a real lever). ADR-0407 carries a correction note; its false sentence is struck through.
> **ADR-0414 · MC-01 (critical)** — `max(0, impact)` zeroed a fired **opportunity**: a −5 d
> opportunity on a 20 d driver moved P50 to 5 wd, a **15-working-day optimistic error**. Now
> branches on the sign of the summed impact: net risk REPLACES (ADR-0359 untouched, and the
> `+5 d → 10 wd` control proves it), net opportunity SUBTRACTS, floored at 0. **Both engines**
> (`sra.py` + the `jcl.py` twin — the twin was independently confirmed defective).
> **The parity leg is UNVERIFIED and the ADR says so**: no committed SSI export exposes a fired
> negative impact (they carry the aggregate distribution under an `Includes
> Risks/Opportunities?` toggle only), so this ships the documented-additive semantic.
> **ADR-0415 · TST-01** — the single-CPM gate was blind: `web.state` (the PRIMARY solve) was
> absent from `_CPM_HOLDERS` and `web.app` was listed but no longer binds the name, silently
> skipped. 24 modules bind `compute_cpm`; the tuple named 10. Now a **computed sweep**
> (ADR-0352's promised standing sweep, prose until today). **The finder's diagnosis was wrong**
> and the lead caught it: with the sweep repaired the injected solves ARE counted (2→4) yet the
> test still passed, because `after_page` is a **self-baseline**. Two defects, not one; the
> build is now pinned as a ceiling.
> **ADR-0416 · JS-01 (critical)** — the Acumen-parity checkbox was a **dead control**. Verified
> in real Chromium: clicking it changed nothing, and the browser logged *"Refused to execute
> inline event handler … `script-src 'self'`"*. ADR-0268 had already built the cure; its
> selector was `select[data-sf-autosubmit]`, so a checkbox fell through. Widened to
> `[data-sf-autosubmit]`, **plus a real submit button** so the toggle works with no JS at all.
> A view-layer census confirms this was the only inline handler in the tree.
> **ADR-0417 · SRA-EXPORT-STALE-SCOPE** — `_sra_reuse_key` omitted the scope, while
> `_sra_selected` returns `analysis.scoped`. Observed: `scope_signature()` moved `A=1` →
> `F=(…)A=1`, the key stayed **identical**, and the export served **the same result object**.
> Fixed. **One leg UNVERIFIED**: the shipped example is degenerate for SRA (all percentiles on
> one date), so "a filter visibly moves the exported percentiles" is not reproduced.
>
> ## Next — the audit is STILL NOT finished
> The kickoff's queue items 0–4 are closed. Remaining: **IMP-01** + the three MIXED-POPULATION
> claims (one scoped-vs-raw probe settles all three) · **MF-05 do-not-fix-blind** (needs the
> Acumen export as oracle) · the remaining ~40 REPORTED rows · the route × test gap-fill
> (**137 routes, 5 with no success test, 16 with no failure-mode test**) · **never audited at
> all: page modules A/B · docs/config/CI · AI figure-gates**.
>
> ## Carried forward
> ADR-0353..0417 closed — do not re-open. NEW lessons: **a claim verified against one module is
> a claim about that module** (ADR-0407 generalised `web/risks.py` to "ever") · **a mutant that
> misses its subject proves nothing** — REC-01's M7 and MC-01's M5 both first SURVIVED because
> the mutation and the assertion were aimed at different files/observables; both were re-aimed
> and then caught · **a control the CSP kills is invisible to every markup test** — for a
> control, the evidence is that clicking it changes something · **a hand-maintained list of
> call sites is a stale list waiting to happen** — compute it. Standing traps unchanged
> (defence-in-depth twins hide layer deaths · a suggested fix is a hypothesis · "measured, then
> pinned" fixtures inherit the bug · compare two surfaces against each other · never measure a
> mutating tree · never mutate a measuring instrument · `python -m ruff` · parity >900 s ·
> fetch before numbering and before committing · `wc` decides). QC-1/QC-2 are ADR-0393.
>
> ## Gate at close — READ THE FULL-SUITE LINE, IT IS NOT CLEAN
> Statics green (`python -m ruff check .` whole tree · `ruff format --check` 1033 files · mypy
> strict 155 files · bandit · `node --check`). Parity: **72 passed, 15 skipped, exit 0, 11:30**
> — unchanged by MC-01, so no parity value moved. Drift guards 12/12. Installers rebuilt
> against the v1.0.211 wheel.
> Full suite: **5 failed, 4224 passed, 5 skipped, 30:54**. The 5 failures are **NOT MINE and
> NOT NEW** — all five reproduce on a pristine worktree of `origin/main` (ff89731) with none of
> this session's changes. They surfaced only because installing `playwright` (to settle JS-01)
> switched ON four modules that had been skipping. That is **BROWSER-ORPHAN-01**, a new
> LEAD-VERIFIED ledger row: `test_ch05_panelkit`, `test_r10_cei_panelkit`,
> `test_axis_titles_visual` and `test_ribbon_scorecards_panelkit` hardcode
> `/opt/pw-browsers`, which does not exist on a GitHub runner, so they SKIP in the CI matrix —
> and CI's dedicated `browser` job runs **only** `test_r11_panel_contract.py`. Neither CI path
> ever executes them. ADR-0406 fixed exactly this chromium-path pattern in ONE module.
> **Pick this up next**: the four panelkit failures look like a stale assertion (the download
> now arrives as a client-side `blob:` URL with the right `suggested_filename`, so it WORKS),
> but that is diagnosed for one test only and the histogram failure is undiagnosed. Do not
> loosen assertions before diagnosing each, and fix the CI orphaning too or they rot again.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
