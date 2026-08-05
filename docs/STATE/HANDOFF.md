# Handoff — 2026-08-05 (monolith split phase 3 opens: the shared kernel comes out first; ADR-0350; v1.0.165)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0350, **v1.0.165**.
> **Phase 3 is OPEN, and its queued order was WRONG — measured, not guessed.** The plan said
> "slice by page family, largest first (`driving` 585)". `driving`'s AST closure drags
> **`_panel_head` (reached by 47 families, 62 direct referrers)** and **`_shell_tools` (41/52)**
> with it — so cutting a page first would have moved the shared panel strip *into a page module*
> and left 60-odd unrelated helpers importing their panel header from `web/driving.py`. Every
> later slice would have inherited that inversion. So phase 3 opens with the shared layer:
> **`web/components.py` (308 lines)**, `app.py` **20,192 → 19,944** (−248). Wheel + nine
> installers rebuilt at **v1.0.165**.
>
> ## MEMBERSHIP IS THE CLOSURE'S VERDICT
> A symbol is in iff **≥3 page families** reach it — then no page can own it. That set is
> **16 names / 233 lines of moved code and it is CLOSED** (calls nothing left behind). The
> **≥2** band was rejected on inspection, not on size: it is **page-PAIR machinery**, not
> primitives. `_conditional_section` / `_unified_risk_section` / `_branch_section` / `_OCC_*` are
> all "sra, ssi" with **`_ssi_panel` as their only direct referrer**; `_render_counterfactual`
> (179 ln) is "counterfactual, evolution" via `_counterfactual_panel` alone. Those travel with
> their pages. Left behind on purpose: `_SRA_XLSX_TITLE` / `_BRIEFING_XLSX_TITLE`, the two
> sibling ⤓ EXCEL strings sitting *immediately beside* `_ANALYSIS_XLSX_TITLE` — **adjacency is
> not cohesion**, and this time it cuts against tidiness.
>
> ## THE TRAP WAS PHASE 2'S, ONE MODULE WIDER
> Not "the subject moved out of the file the guard reads" but **"the view layer grew a module the
> guard does not read."** `test_presentation_fixes`'s `&mdash;` sentinel guard read `app.py` +
> `chrome.py`; **`_stat_cards` — the function the very next test exercises for that exact
> double-escape — moved to `components.py`.** It would have stayed green over a shrunken subject.
> `test_bar_drill`'s once-only `drilldown.js` count had the same shape. Both now read **all three**
> view modules, and the module list is no longer left to the next cutter: the contract test pins
> `VIEW_MODULES` / `LAYER_ORDER` and **fails** when a view module is added without widening them.
>
> ## PROOF — AND THE ORACLE WAS BROKEN BEFORE IT WAS TRUSTED
> **60/60 routes byte-identical**, including the parametrized `/analysis/{name}`, `/card/{name}`,
> `/wbs/{name}` — where this kernel is used most and which a page-list oracle would have missed.
> But two runs of the **unchanged** tree first disagreed on **34 of 61**: a per-process launch
> token (`<meta name=sf-launch>` / `/api/whoami`) + pid, stable only *within* one interpreter —
> which is exactly why ADR-0349 said "in the SAME interpreter". Normalized those two; excluded
> `/api/system` (live uptime) by name; only then is 60/60 evidence. Oracle then falsified: one
> char in `_panel_head` moves **20 of 60**, and the 40 that hold were **checked** (zero
> `class=panel-head` in their HTML) with `/margin` (4, moved) as positive control. Verbatim proved
> mechanically: non-blank multiset **19,100 → 19,100**; the 52 added lines are entirely the
> re-export block (25) + preamble (27), the 1 removed is `field_or_metric_doc`.
>
> ## Verification
> **Five mutations, each proved to fail the right test**, each verified-mutated by re-reading the
> file and restored from a scratchpad copy (never `git checkout`): dropped re-export → names
> `_panel_head`; **deferred** `from …web import app` inside a `components` function → fails the
> layering test *and imports cleanly*, which is the whole point; `"components.py"` dropped from
> `test_bar_drill`'s tuple → enumeration test fails; `"&mdash;"` planted in `components.py` and a
> second `drilldown.js` include planted there → both repointed guards fail, which is what proves
> the repointing widened their reach rather than just moving it.
>
> ## Next
> **Phase 3 continues, now genuinely per-page** — with the kernel out, `driving`'s closure is its
> own 5 entry points + `_task_iso_dates` + `_corridor_chips`. Order by size: `driving` 585 ·
> `evolution` 429 · `integrity` 402 · `margin` 379 · `trend` 348 · `ssi` 335 · `mission` 304 ·
> `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208 · `forecast` 204.
> Phase 4 MUST add its module to `LAYER_ORDER` + `VIEW_MODULES` (the contract test says so by
> failing). Two 2-family names (`_task_name_across`, `_EVO_TIER_LABEL`) stay in `app.py` until
> both owners have moved. Then: the three pages with no `page-lede` (`/briefing`, `/path`,
> `/compare`); `/groups` "Activities" counting summary rows (ADR-0343); the nine installers not
> installing with `-c constraints/known-good.txt` (62 lockstep tests, own unit); Phase 6 docs.
> **Reserved for Fable 5 Max (ADR-0240), do NOT start on Opus:** **SRA-LEGACY**
> (`audit/SRA-ROOTCAUSE-20260730.md`) · ADR-0348's **`tod + per_day == 1440`** residual (no oracle
> in the corpus) · **V3** (`engine/msp_filters.py` — moves saved-filter populations).
> **Operator only:** license selection · branch-protection required contexts · intake re-upload ·
> proprietary-tool reruns (engine==golden → engine==Fuse) · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — passes in isolation, never red on CI.
> Do NOT chase. Do NOT re-derive CC-01's "74 call sites" (ADR-0348 records it). `pydantic>=2` is
> NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2 is the floor).
> **Run `ruff check .` — the WHOLE tree**, as **`python -m ruff`** (a stale 0.15.8 shim at
> `/root/.local/bin/ruff` shadows the 0.16.1 `.[dev]` installs). Never `git checkout <file>` to
> undo a test mutation — `cp` from a scratchpad copy.
>
> **New this session:** *a stated number carries the timestamp of the tree it was measured from.*
> ADR-0349's `20,255` was honestly measured — before `ruff --fix`/`format` ran. The merged file
> was **20,192**; corrected in all three docs. Same failure one step further in than ADR-0348's:
> not a recollection, a measurement taken too early. And: **settle the tree, `md5sum` what you
> touched, run, then re-verify the md5s** — step four is what turns "I don't think I edited
> anything" into evidence.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
