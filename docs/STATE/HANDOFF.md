# Handoff — 2026-08-27 (POLARIS² audit campaign opened; WP0 live-defect chase CONFIRMED + FIXED: the Timescale config loaded unvalidated; ADR-0440, v1.0.222)

> ## STATUS (current) — **WP0 of the POLARIS² campaign is COMPLETE on branch `claude/polaris2-full-tool-audit-948whg` (draft PR open — VERIFY a pull_request CI run appears after each push; dispatch manually only if none does, see the WP4 ledger note).**
> Highest ADR **0440**; version **1.0.222** (shipped code changed: `static/timescale.js`);
> wheel + all nine installers rebuilt in lockstep. The campaign ledger is
> **docs/STATE/AUDIT-2026-08-27.md** — appended per-WP, never batch-written; every row cites its
> executable proof. Gate numbers at close: see the SESSION-LOG 2026-08-27 entry (recorded AFTER
> the runs finished, QC-1). The campaign runs under QC-1/QC-2 —
> ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## The operator's multi-folder ask is ANSWERED — a decision, no longer a question
> The 2026-08-27 kickoff carries the operator's choices for the whole campaign: **SOLO lead** ·
> **fix-as-verified** · **BOTH folder-ask builds** (clearer labels AND the parent-folder →
> one-Project-per-sub-folder confirm flow). The #611 carried-forward item is therefore CLOSED as
> a question and queued as **WP5** (client-side in `home.js`, extends
> `test_multi_folder_drop_browser.py`'s fake-entry machinery; the three measured folder-gesture
> facts from 2026-08-21 still govern — do NOT re-derive them).
>
> ## What closed — WP0: the live defect the operator reported on v1.0.221 is root-caused and dead
> Report: /path, /driving-path, /evolution — "controls do nothing" + "renders wrong".
> **CONFIRMED-PLAUSIBLE-ROOT-CAUSE, mechanism CONFIRMED-FIXED (ADR-0440):** timescale.js merged
> `localStorage["sf.timescale.v1"]` unvalidated (the 25–1000 Size clamp existed only on dialog
> EDITS), every consumer guards only non-positive factors, and persist.js exempts the key from
> every wipe BY DESIGN — so a persisted `size: 1` / `100000` / `"600000"` zoomed all three Gantt
> pages 0.01×–6000× with ZERO console errors, invisible to a fresh-profile probe, surviving
> Reset-view. A 13-cell × 3-page Playwright matrix (A0 baseline calibrated the oracles first)
> reproduced BOTH symptoms on exactly those pages; a second defect fell out: a garbage tier
> `units` CRASHED the render (`labelDef` lacked the fallback `UNITS` has) and /evolution
> swallowed that crash into a misleading "Failed to load the path-evolution data." box.
> **Fix:** load-path sanitizer (ranges coerce-then-clamp, enums must be members, color pinned to
> `#rrggbb(aa)`) + the labelDef months-fallback belt; healing is in-memory, the dialog opens
> showing the healed value. **Whether the operator's machine holds that state stays UNVERIFIABLE
> until their reply** — the three-line ask (screenshot · console ·
> `localStorage.getItem("sf.timescale.v1")`) is in the ledger's Phase-0 section.
>
> ## New instrument — M2, the Timescale dialog's first behavioral coverage
> `tests/web/test_timescale_dialog_browser.py` (16 tests, ~37s, auto-joins CI's browser job via
> `tools/browser_modules.py`): open/tabs/preview · OK-commits-MEASURED-on-the-page-behind ·
> Cancel-discards · Reset-restores · Escape · persistence + cross-page · corrupt-JSON fallback ·
> the 8 load-path hardening pins including the A1/A2 matrix cells as FAIL-side tests. QC-1 chain:
> all 8 observed RED on the pre-fix tree by name → 16/16 green → mutation battery red by name
> (size clamp · tier sanitize · the labelDef belt separately — the belt mutation reproduced the
> EXACT original pageerror text through the committed test · show/fy). Seed vacuity excluded by
> the pre-fix reds themselves.
>
> ## Measured and deliberately NOT changed (do not "fix" these blind)
> **Legal 25% renders a 120px-floor /path track** — the dialog's own smallest choice, identical
> geometry measured when chosen IN-dialog; a UI-map observation for WP1, not a defect ·
> **`path_evolution.js:515`'s catch misattributes a render crash as a load failure** — with B2
> fixed it is measured-unreachable; reported in the ledger, unrepaired · **/driving-path on TP4
> opens on v5's legitimately empty corridor** with no "step back" hint — UI-map candidate.
>
> ## Traps paid for THIS session — check by name
> **/driving-path opens on the NEWEST version, and TP4 v5's corridor for 11→26 is EMPTY** — the
> matrix's first run flagged its own baseline until the probe learned to step back one version; a
> red for the wrong reason is not a red · **the B2 crash lives in the tier REBUILD, not reliably
> in first paint** — the hostile-tier test had to force a zoom reflow before asserting
> `errors == []`, or the crash-channel assert passes vacuously · **localStorage is read at script
> PARSE time** — only `context.add_init_script` seeds early enough; post-load seeding is vacuous
> · **`Number("") === 0`** — an empty-string size would clamp to 25 instead of defaulting without
> the explicit empty-string guard.
>
> ## Next — the campaign queue (full plan in the kickoff + ledger skeleton)
> **WP1** M1 control-effect census (population harvested from the served DOM; unknown
> zoom/fit/pan/stepper control with no driver spec = RED; the 27-row UI map) → **WP2** M3
> stateful flows + M5 theme/language → **WP3** M4 SRA grid/paste/save → **WP4** committed
> route-coverage instrument + the CI event-trigger outage (dispatch manually per push until
> root-caused) → **WP5** BOTH folder-ask builds → **WP6** ledger verify-or-refute (highs first:
> CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** thin dimensions (`ai/txlog.py`
> first, Law 1) → **WP8** consolidated report + repair roadmap. Do-not-fix-blind rows unchanged
> (MF-05, MC-01 parity leg, ADR-0417/0419 fixtures, `citations.reattach` pin, 6 dead E501s,
> evolution 0% cell). Insufficient-Detail V05/V06 + TP2 stay BLOCKED and operator-owned — do NOT
> re-chase.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
