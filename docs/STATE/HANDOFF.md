# Handoff — 2026-08-14 (b) (three verification gaps closed: the Fuse transcription oracle, the own-calendar floor guard, the Host-allowlist closure; ADR-0400; v1.0.201 unchanged)

> ## STATUS (current) — ADR-0400 unit complete on `claude/polaris-kickoff-handoff-v8qu96`,
> branched from `main` **58bf9ed** (= #587's squash; local HEAD == origin/main at branch time).
> Highest ADR now **0400**. **NO shipped code changed** — tests + docs only, so the version
> stays **v1.0.201**, SCHEMA stays 2.11.0, no wheel/installer rebuild (ADR-0395/0399
> precedent). The audit's PO-03 `xfail(strict)` flipped loudly and its marker is REMOVED —
> `tests/audit` now has **1** live xfail (TEST-01).
>
> ## What landed — ADR-0400: three tests-only closures, every claim measured before adoption
> **(1) PO-03 — `tests/parity/test_fuse_transcription_oracle.py`** (parity-marked, std-lib
> zipfile+xml.etree): re-derives every derivable value of `fuse_exports_2026-06.json` from the
> four load-bearing vendor workbooks — label-addressed Metric History rows (EVERY occurrence
> must agree; the `Logic Density™` two-scope trap handled via `CP Logic Density™` adjacency),
> DCMA offender lists (UID-exact, sorted — file order is not UID order), and per-activity
> Forensic re-derivations ×2 reports incl. v1==v2 row-identity and the exact finish serials as
> raw stored strings. A three-agent investigation fan-out mapped all 115 value-locations first
> (115/115 MATCH — the transcription is CLEAN); the lead re-verified with a second hand-rolled
> parser. Battery vs the FINAL module, md5-restored: JSON value drift → 1 named red; UID-list
> drift → 3 named red; WORKBOOK-cell drift (byte-patched zip) → 1 named red — the workbook side
> is genuinely read. Key workbook facts: SpreadsheetGear omits `r=` coords (the SSI reader
> pattern would see EMPTY sheets — not reused, on purpose); MH `Project Finish` is the
> day-FLOOR serial; `HSD10` sits on two adjacent rows (match by name, never code).
> **(2) exec_cal floor — `tests/engine/test_actual_start_floor_own_calendar.py`**: the
> ADR-0391 own-calendar floor (`cpm.py:1134-1140`) was deletable with `tests/engine` (963
> passed) AND the full parity gate (52 passed, 909 s) staying green — re-measured, import
> origin proven. Root causes: zero exec_cal tasks in the whole synthetic battery; the fidelity
> test steps over own-calendar tasks; ADR-0391's own mutation battery only ever covered the
> project-axis half. Stakes: on Large_Test_File the floor binds on 19 own-calendar UIDs; UID
> 5230 pulls back SIX YEARS (2023-08-08 → 2017-09-05) with `project_finish` byte-identical —
> which is why every suite was blind. New module: hand-derived synthetic (walls, offsets,
> float/criticality, the `actual_start_driven`/`date_driven` split) + a golden test whose
> expectation is DERIVED from the file (`early_start_wall ==` stored `ActualStart`, five named
> UIDs). Proven 3/3 red vs branch-deleted, 3/3 green intact, and 3/3 green vs the PROJECT-AXIS
> floor deleted — the isolation control: it cannot be satisfied by the guarded sibling.
> **(3) SEC-01 completion — `tests/web/test_sec01_host_allowlist_closure.py`**: QC-2 narrowed
> the premise — `test_sec_hardening.py` DOES behaviourally test both consumers; what was
> missing (measured in mutant sandboxes): the samples are M1-BLIND to a named widening (only
> the data pin fires), and the `_origin_allowed` scheme conjunct (M3) was caught by NOTHING —
> dropping it left tests/audit + tests/guards + hardening all green while `ftp://`/`file://`
> Origins passed the CSRF fallback. New module: ADR-0394-recipe closures through the HTTP layer
> (M5 is why), curated populations both directions, the Origin-scheme closure, raw-ASGI
> absent-Host, and deliberate pins: bare `::1` REFUSED (bracketed-only reachability,
> fail-closed), `[::1` = the ValueError branch (does NOT flip under return-True — the
> check-disabled vs check-unwired discriminator), `http://testserver` passes the fallback
> (shared frozenset, pinned so it cannot widen silently), homograph rides as punycode
> `xn--lcalhost-nbh` (raw non-ASCII cannot ride an HTTP Host header — measured, httpx refuses).
> Lead battery vs the FINAL module, control-subtracted, canaried: M1→6+audit pin BY NAME,
> M2→24 (all but `[::1`), M3→4, M4→10, M5→25 (incl. `[::1` + no-Host). Zero unexpected flips.
>
> ## Adversarial round (ADR-0240)
> Four refuters vs the mutation-green first revision (~50 sandboxed attacks): ELEVEN
> in-scope findings, all lead-re-verified, all fixed in-unit and re-proven red by named
> mutant — the HOOK-01 pattern repeated (batteries by name, gaps between them). Highlights:
> **(exec_cal, HIGH)** flooring from the stored Start instead of actual_start survived
> module + engine + parity (both populations had start==actual_start or None) — closed with
> a disagreeing stored Start on UID 2; false-positive disclosure (>=/append-always) and
> snap-drop closed with an equal-instant control and a Tue-Sat void-start test (m1/m2/m5→1
> red each, m7→2). **(PO-03)** an UNSTAGED workbook deletion silently disarmed all 20
> guards (manifest reads the git INDEX) — now a loud 20-error FAIL, skip only for a missing
> intake dir; int(float()) truncation (34.6 passed as 34) → _int_cell integrality;
> activities_added was the 1 of 77 leaves nothing read → tied to the pinned header;
> row-identity claim scoped honestly to the read columns. **(SEC-01, MEDIUM)** a
> METHOD-conditional host bypass was caught by NOTHING — the sweep was GET-only and the
> pre-existing hardening POST test was LAUNDERED by follow_redirects=True (the mutant ran
> the foreign-Host POST, mutated state, and the followed redirect GET produced the 400 the
> assert saw) — closed with a POST row on the non-redirecting /api/heartbeat +
> follow_redirects=False in test_sec_hardening; empty-Origin fail-open pinned; two dead
> oracle constants made load-bearing. Final battery vs the FINAL module: M1→8+audit pin,
> M2→25, M3→4, M4→11, M5→26, A5→2, A7→2, A4→1 — zero unexpected flips. Consistency
> refuter: DISC-01 sweep clean, Law-1 clean, pre-commit hook exit 0 with a blocked canary
> proving teeth, all drift guards green.
>
> ## Next — in order
> **DISC-01 release determination** (operator / authorizing official: the strings are in git
> HISTORY since `a19b969`; private visibility mitigates but does not decide releasability) →
> **001c** the operator's cloud/gateway decision (`APPROVED-GATEWAY-INTEGRATION.md` §6 steps
> 4–6; ADR-0396's chain makes honest gateway wiring mechanical) → **PO-04/05** (CEI/bow-wave +
> HMI: BLOCKED on a missing primary oracle — no vendor reference exists in the repo to guard
> against; needs an operator-delivered export, not engineering) → `actual_start_driven`
> consumed nowhere (ENG-DEAD-01; the ADR-0391-promised disclosure surface — a SHIPPED-code
> change: version bump + wheel + nine installers when taken) → TEST-01 chromium build-number
> pins (22 modules; the audit module's last live xfail) → FINAL-REPORT overclaims (condition on
> `_observed_banner`, do not weaken) → 8 stale branches (DoD 091).
> **Operator:** DISC-01 · the 001c decision · a CEI/HMI reference export (unblocks PO-04/05) ·
> FX-03/04 re-run · sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0400 closed — do not re-open. NEW lessons this session: **a transcription oracle
> must be proven to read the SOURCE side** — mutate the workbook bytes, not just the JSON (a
> guard comparing the JSON to itself stays green under B3); **an engine branch can be
> load-bearing on the golden and invisible to every pin** — the exec_cal floor moved UID 5230
> six years while `project_finish` stayed byte-identical; pin the member, not just the
> aggregate; **a population row must be TRANSPORTABLE** — the raw-Unicode homograph Host
> errored (httpx refuses to encode it) instead of failing; sweep the punycode form a browser
> actually sends; **an isolation control belongs beside every red/green pair** — the new
> exec_cal module was also run against the SIBLING branch deleted to prove it cannot be
> satisfied by the already-guarded half. Standing traps unchanged (a data pin guards the
> literal, not the guarantee · mutation-green is not adversarially verified · a guard's input
> plumbing is attack surface · monkeypatch repoint is per CALL SITE · never MEASURE a tree a
> battery is mutating · never MUTATE an instrument a measurement is using · `grep -c` exits 1
> on zero · two ruffs on PATH, use `python -m ruff` · `pytest -m parity` alone exceeds 900 s ·
> the container starts with NO deps installed · `git fetch origin` before taking an ADR number
> and again before committing · a number written mid-session is not a measurement, `wc`
> decides). QC-1/QC-2 are ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> ruff check . / ruff format --check . (1,001 files) / `python -m mypy src/` (152 files) /
> bandit (exit 0) / node --check: all green. **Full suite ON THE FINAL TREE (post-adversarial
> revision): 3951 passed, 47 skipped, 1 xfailed (TEST-01), exit 0, 29:28** — every skip an
> environment-gated playwright skip. Touched-module set together: 122 passed + the TEST-01
> xfail. Batteries: exec_cal 4/4 red on deletion + 1/1/1/2 partial-mutant reds + isolation
> green; PO-03 B1/B2/B3 + R1/R2/R3 named reds, instruments md5-restored; SEC-01 final
> M1→8+audit-pin / M2→25 / M3→4 / M4→11 / M5→26 / A5→2 / A7→2 / A4→1, zero unexpected.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
