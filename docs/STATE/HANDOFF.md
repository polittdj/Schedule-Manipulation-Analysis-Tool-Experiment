# Handoff — 2026-08-17 (d) (BROWSER-ORPHAN-01: 94 browser tests never ran in CI, and one oracle could not fail; ADR-0418; no version bump)

> ## STATUS (current) — audit CONTINUING on `claude/polaris-browser-orphan-01-3824ij`.
> Highest ADR now **0418**. **NO shipped code changed** — this is tests + `.github/workflows/ci.yml`
> only, so v1.0.211 stands, SCHEMA 2.11.0 unchanged, and **no wheel/installer rebuild** (ADR-0148
> is per shipped-code change). Branch started clean from `origin/main` at f4eaf32. The live audit
> ledger is `docs/STATE/AUDIT-2026-08-16.md`.
>
> ## What landed — BROWSER-ORPHAN-01, and the ledger's own count was wrong
> **The row said "four browser modules". Four were the modules that FAILED; 23 never RAN.** A
> computed census (match the LAUNCH call, not the word "playwright") finds 24 browser modules; 23
> pinned `/opt/pw-browsers`, and only ADR-0406's own module resolved properly. Measured by
> bind-mounting an empty dir over `/opt/pw-browsers` in a mount namespace — a runner-shaped
> filesystem: **86 passed, 94 skipped**, against 175 passed / 5 failed with the vendored browser
> present. So **94 tests never executed in either CI path** (`playwright` is in the `browser` extra,
> not `dev`, so the matrix skips them; the `browser` job named one module by hand).
>
> **The four panelkit failures were stale, as hypothesised.** ADR-0360 replaced navigation with
> fetch+blob, so `expected_path in download.url` fails on a WORKING button. Repaired by asserting on
> the NETWORK (the export path was really requested) — stronger than the string it replaces, and
> mutation-measured. The `200` leg is documented as **secondary, not load-bearing**: against a dead
> (500) endpoint the failure actually surfaces as the download wait timing out.
>
> **The histogram failure was NOT stale, and NOT a lost halo — the hypothesis was backwards.** The
> halo is painted (computed `paint-order: stroke`, 3px white; stashing it moves pure-white pixels
> 17.6% → 1.3%) and the caption is legible at true 1×, verified visually. The defect was the
> ORACLE: `_modal_color` takes the mode of the whole caption box — the dominant REGION, not the
> glyphs' backdrop — and on a caption straddling the degenerate one-bin bar it returned **1.17:1
> with the halo AND 1.17:1 without it**. It failed a correct render and could not have detected a
> broken one. Replaced by a 1px glyph-backdrop ring: **3.06:1 haloed / 1.17:1 stashed**. A second
> defect in the same test scored captions against OTHER captions' pixels (document-wide probe joined
> to `#ssiCharts` screenshots by non-unique caption text — which is why ONE straddling caption
> reported as THREE failures); probe and screenshot now come from the same element handle.
>
> **Both halves shipped**: 23 modules repointed at one resolver (`tests/web/browser_chrome.py`)
> whose fallback is playwright's own resolution, AND CI's browser job now **computes** its
> population (`tools/browser_modules.py`) rather than naming modules, with skip-is-a-failure over
> the whole set. Guard mutation-proven **7/7 by name**, every mutant confirmed LANDED first.
>
> ## Next — the audit is STILL NOT finished
> **IMP-01** · the three MIXED-POPULATION claims (one scoped-vs-raw probe settles all three) ·
> **MF-05 do-not-fix-blind** (needs the Acumen export as oracle) · the remaining ~40 REPORTED rows ·
> the route × test gap-fill (**137 routes, 5 with no success test, 16 with no failure-mode test**) ·
> **never audited at all: page modules A/B · docs/config/CI · AI figure-gates**.
>
> ## Carried forward
> ADR-0353..0418 closed — do not re-open. NEW lessons: **a count in a ledger row may be counting the
> symptom, not the thing** (four failures ≠ four orphans; 23 modules were invisible because they
> skipped) · **an oracle that returns the same verdict in both worlds is not stale, it is blind** —
> before "fixing" a failing check, run it against a deliberately broken subject and confirm it
> CHANGES · **a mutant that never landed is not a SURVIVED verdict** — one `sed` silently applied
> nothing (delimiter collided with the pattern) and the "survival" it produced concealed a genuinely
> weak assertion of mine · **joining two populations by a non-unique key** (caption text) scores
> items against each other's evidence · **a screenshot's resolution is part of the measurement**
> (the same caption read 1.17:1 at 1× and 3.07:1 at 5×). Standing traps unchanged (a claim verified
> against one module is a claim about that module · a control the CSP kills is invisible to markup
> tests · compute a call-site list, never hand-maintain it · `python -m ruff` · `| tail` masks exit
> codes — it hid a `ruff format` failure this session · fetch before numbering and committing).
> QC-1/QC-2 are ADR-0393.
>
> ## Gate at close
> See SESSION-LOG for the full-suite line. Statics green whole-tree. The browser census (24 modules)
> is the run that matters here — it had never been green before this session.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
