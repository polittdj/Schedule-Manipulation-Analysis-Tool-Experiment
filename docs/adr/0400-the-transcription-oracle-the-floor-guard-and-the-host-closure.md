# ADR-0400 — The Fuse transcription gets its oracle, the own-calendar floor gets its guard, and the Host allowlist gets its closure

**Status:** Accepted · **Date:** 2026-08-14 · **Extends:** ADR-0151 (Fuse export parity), ADR-0391
(actual-start floor), ADR-0394 (the allowlist-pinning recipe) · **Closes:** audit PO-03; the
own-calendar-floor queue item; the SEC-01 behavioural half

## Context

Three verification gaps from the 2026-08-13 audit queue, all tests-only, all re-derived from
measurement this session before any fix was written (QC-2: the queue is testimony):

1. **PO-03 (audit table, VALIDATED).** Every number `tests/parity/test_fuse_export_parity.py`
   calls "Fuse's value" flows through a hand transcription
   (`tests/fixtures/golden/project2_5/fuse_exports_2026-06.json`, ADR-0151) — and no test read
   the source vendor `.xlsx` workbooks, so a transcription error or a silent JSON edit would
   leave ENGINE==FUSE green while the oracle no longer said what the vendor tool said. The
   audit landed this as `xfail(strict=True)` in `tests/audit/test_audit_findings.py`.
2. **The ADR-0391 own-calendar floor was behaviorally unguarded** (queued in the 2026-08-13
   SESSION-LOG; it predates the audit table — the audit's own doc never names it, a provenance
   fact worth recording). Re-measured this session: deleting the floor block inside the
   `tid in exec_cal` forward-pass branch (`engine/cpm.py:1134-1140`) left `tests/engine`
   green (963 passed; the 3 errors reproduce identically on the intact tree and are
   MPXJ-path environment artifacts) **and the full parity gate green** (52 passed, 0 failed,
   909 s, import origin proven). Three measured root causes: no
   `tests/fixtures/test_projects` battery file has *any* exec_cal task; the floor-invariant
   test (`test_progressed_finish_fidelity.py:120-121`) deliberately steps over own-calendar
   tasks; and ADR-0391's own "deleting the floor (8 failures)" battery exercised only the
   project-axis half (`_actual_start_bounds`, `cpm.py:1176-1180`) — an exec_cal task
   `continue`s past it. The stakes on the primary golden (Large_Test_File, 2,126 tasks): the
   floor binds on 19 own-calendar UIDs, and deleting it pulls UID 5230's early start from
   2023-08-08 back to 2017-09-05 — a ~6-year understatement in the direction a delay tool
   must never err — while `project_finish` and every value the SSI/parity pins read stay
   byte-identical. That is *why* every existing suite was blind.
3. **SEC-01's behavioural half (audit table, VALIDATED — scope corrected here).** The audit
   xfail-era premise "no behavioural coverage" needed narrowing (QC-2):
   `tests/web/test_sec_hardening.py` DOES exercise both `_ALLOWED_HOSTS` consumers. What was
   actually missing, measured in mutant sandboxes with import-origin canaries:

   | Mutation of `web/app.py` | data pin | `test_sec_hardening` | anything else |
   |---|---|---|---|
   | M1 — `"evil.example"` **added** to the frozenset | catches | **blind** (9 passed — its samples are other literals) | nothing |
   | M2 — `_host_allowed` → `return True` | **blind** | catches | — |
   | M3 — scheme conjunct dropped from `_origin_allowed` | blind | **blind** | **NOTHING in tests/audit + tests/guards + the hardening suite** |
   | M5 — middleware call site gated off | blind | catches | — |

   M3 is the ADR-0394 lesson verbatim: a data pin guards the literal, not the guarantee, and
   sampled negatives cannot see a named widening — or, here, a dropped conjunct that leaves
   the literal untouched while `ftp://127.0.0.1` / `file://localhost/...` Origins pass the
   CSRF fallback.

## Decision

Three test modules, one xfail flip, one report sentence. **No shipped code changed** — the
version stays v1.0.201, SCHEMA stays 2.11.0, no wheel/installer rebuild (ADR-0395/0399
precedent for guards+docs-only units).

1. **`tests/parity/test_fuse_transcription_oracle.py`** (parity-marked, std-lib zipfile +
   xml.etree — openpyxl is not a dependency and runtime I/O law aside, the SRA oracles set the
   convention). Three tiers re-derive every derivable transcribed value from the four
   load-bearing committed workbooks: label-addressed Metric History rows where **every
   occurrence** of a label must agree (self-cross-checking); DCMA Report offender lists
   (Newly Critical / No Longer Critical / CEI-Incomplete, UID-exact, sorted — the file order
   is not UID order); and per-activity re-derivations from BOTH Forensic Analysis Reports
   (no-longer-critical = P→O − summaries − P5-complete; float erosion; both
   duration-increase sets; the exact finish serials `46644.708333333336` /
   `46778.708333333336` as raw stored strings), plus the v1==v2 row-identity the JSON's
   `_source` asserts. Workbook traps measured and encoded in the module docstring: the
   SpreadsheetGear writer omits `r=` coordinates (a reader requiring them sees empty sheets —
   the SSI test's `_cells` has exactly that requirement, which is why the reader is NOT
   reused); `Logic Density™` appears at two scopes and the wrong row's Project2 value equals
   the right row's Project5 value (the guard uses the `CP Logic Density™` adjacency);
   Metric History's `Project Finish` stores the day-FLOOR serial (46644, not round's 46645);
   `HSD10` sits on two adjacent rows (match by name, never by code). The audit module's
   PO-03 `xfail(strict)` flipped loudly (observed XPASS-fail before touching it) and its
   marker is removed in this unit — the test stands as the permanent pin. `tests/audit` now
   has **1** live xfail (TEST-01).
2. **`tests/engine/test_actual_start_floor_own_calendar.py`** — a minimal synthetic
   (Mon-Fri/480 project calendar; a 2,880-minute task on its own 24/7 calendar, FS-chained,
   `actual_start` a week past its logic start; every expectation hand-derived in comments)
   pinning the floored walls, the project-axis projections, the propagation to successor /
   project finish / float / criticality, and the `actual_start_driven == (2,)` +
   `date_driven == ()` disclosure split; plus a golden-anchored test on Large_Test_File
   asserting, for five named own-calendar UIDs, `early_start_wall ==` the task's **stored**
   `ActualStart` (the expectation is derived from the parsed file at test time, never
   transcribed) and membership in `actual_start_driven`.
3. **`tests/web/test_sec01_host_allowlist_closure.py`** — the ADR-0394 recipe applied to
   `_ALLOWED_HOSTS`, through the HTTP layer (M5 is why unit tests on `_host_allowed` are not
   enough): hand-curated populations swept in both directions plus one whole-population
   closure per consumer; the Origin-scheme closure (the M3 hole); a raw-ASGI absent-Host
   request (httpx cannot send one); and the measured oddities pinned deliberately — bare
   `::1` is REFUSED (the frozenset's entry is reachable only via the bracketed HTTP form,
   fail-closed), `[::1` exercises the `urlsplit` ValueError branch and does NOT flip under a
   return-True mutation (the free discriminator between check-disabled and check-unwired),
   `http://testserver` passes the CSRF fallback (the shared frozenset, pinned so it cannot
   widen silently), and the IDN homograph rides as its punycode form `xn--lcalhost-nbh`
   because raw non-ASCII cannot ride an HTTP/1.1 Host header at all (measured: httpx refuses
   to encode it — the first draft carried the raw literal and the test errored instead of
   failing).
4. **`docs/PARITY-REPORT.md`** gains one sentence: the transcription step is now
   machine-guarded (the report's "re-checkable from the repo" claim previously leaned on an
   unguarded transcription).

## Verification (QC-1 — every instrument observed failing first)

* **exec_cal guard (final revision, 4 tests):** whole module vs the branch-deleted sandbox —
  **4/4 failed** (ES wall back at 2026-01-05 16:00; project finish offset 1920; UID 5230 at
  2017-09-05; the void start unsnapped); intact — 4 passed; **isolation control:** vs the
  project-axis-floor-deleted sandbox — 4 passed, so the module aims at the own-calendar
  branch specifically and cannot be satisfied by the already-guarded sibling. Partial-mutant
  reds (adversarial round): m1 `>=` → 1, m2 snap-drop → 1, m5 append-always → 1, m7
  floor-from-stored-Start → 2 — narrow named sets each. Import origin printed per run;
  intact sandbox diffed byte-identical to HEAD src/ first.
* **SEC-01 closure (final revision, 56 tests):** five-mutation battery run by the lead
  **against the final committed module**, fresh `copytree` sandbox per mutant, exact-string
  patch with occurrence==1 abort, import canary asserted, control run green on the module,
  failures diffed against the control: M1 widen → **8** module flips **plus the audit data
  pin by name** (incl. the new in-module pin); M2 host-check-true → **25** (every refused
  host except `[::1`, exactly as the ValueError-branch analysis predicts, plus the new POST
  row); M3 scheme-dropped → **4**; M4 origin-check-true → **11**; M5 middleware-unwired →
  **26** (M2's set **plus** `[::1` and absent-Host). Zero unexpected flips. The 4
  control-run failures in the audit module are PYTHONPATH-sandbox path artifacts
  (repo-relative tests resolving REPO from the sandbox's `__file__`), identical under every
  mutant, subtracted as noise.
* **PO-03 oracle:** 20 tests green; three-leg battery against the final module,
  mutate-run-restore with md5-verified restores of the JSON, the workbook, and the instrument:
  **B1** one transcribed value drifts (logic_density 2.79→2.8) → **1** named failure;
  **B2** one UID swapped in `no_longer_critical_uids` (96→97) → **3** named failures (the
  DCMA offender-list test + both Forensic re-derivations); **B3** the WORKBOOK cell drifts
  (every stored `2.79` → `2.83` in the Metric History sheet, byte-patched zip) → **1** named
  failure — the workbook side is genuinely read; a guard comparing the JSON to itself would
  have stayed green. Lead independently re-verified the dossier's 115/115 location map by
  re-running its locator and spot-checking two cells (row-347 adjacency pair; the raw
  Forensic E10/E11 serial strings) with a hand-rolled second parser.
* The investigation itself was a three-agent fan-out re-verified by the lead (ADR-0240): the
  dossiers' sandboxes were diffed, their scenarios re-run, and their measured tables
  reproduced before any module was written.

## Adversarial round (ADR-0240 — mutations prove the tests see the detectors; adversaries probe between them)

Four refuters ran against the mutation-green first revision (~50 sandboxed attacks, every
sandbox import-origin-proven, no repo file touched). **Eleven in-scope findings survived
lead re-verification; all are closed in this revision, each re-proven red against its named
mutant.** The HOOK-01 pattern repeated exactly: 8/8 and 5/5 mutation batteries by name,
and the attack round still found the gaps *between* them.

**exec_cal guard (3):** *(F1, HIGH)* flooring from the stored `Start` instead of
`actual_start` survived the module, all of `tests/engine` AND the parity gate — in both
populations the two sources were indistinguishable (synthetic `start=None`; every golden
row `start == actual_start`). Closed: UID 2 now carries a stored Start that DISAGREES with
its actual start (a week apart) — the substitution mutant fails 2 tests by value. *(F2)*
the false-positive direction was unguarded: `>=` and append-always mutants added the same
8 equal-instant UIDs to `actual_start_driven` on the golden, green. Closed: a UID 4
equal-instant control plus the kept exact-tuple asserts — each mutant now fails 1 named
test. *(F3)* dropping `_snap_to_working` was invisible (the synthetic's own calendar is
24/7 where snap is identity; every golden actual start already sits at a working 08:00).
Closed: a Tue-Sat own-calendar task whose actual start is recorded in the void (Sunday
03:00 → must snap to Tue 08:00). The refuters also *failed* to refute: the golden test
cannot pass vacuously (a task leaving `exec_cal` makes `early_start_wall` None → red), and
the clamp-drop mutant was proven EQUIVALENT (0 diffs; `ps ∈ cands` + forward-monotone
snap), so no test pretends to catch it.

**PO-03 oracle (4):** *(F1, medium)* the docstring's "absence is not a silent hole" was
measurably false for an UNSTAGED working-tree deletion — the intake manifest reads the git
INDEX, so `rm` one workbook left the manifest green while the oracle skipped 20/20: every
guard silently disarmed on exactly the operator's machine. Closed: skip only when the whole
intake directory is absent; a missing individual workbook now FAILS (measured: 20 loud
errors). *(F2)* "row-identical" overclaimed — the grid compares the value-bearing columns
(UID/type/P2/delta/P5), and a prose-column drift passed. Closed by scoping the claim to the
read columns (the unread cells carry no transcribed value — honest wording, not a wider
read). *(F3)* `int(float(...))` truncation let a drifted banner count `34.6` and offender
id `34.4` compare green. Closed: `_int_cell` requires integrality (the same `34.6` mutant
now fails by name). *(F4)* `activities_added` was the ONE of 77 JSON leaves no assertion
read (exhaustively enumerated). Closed: tied to the pinned `Activities - 0 (0%)` header +
144/144 basis (JSON 0→3 now fails 2 named tests). ~20 further attacks failed to refute:
coordinated two-report tampering, anchor-label removal, banner-title removal, serial
drift, corrupt shared-string indices — all red or loudly erroring.

**SEC-01 closure (4):** *(F1, medium)* a METHOD-conditional host-check bypass (gate only
GETs) was caught by NOTHING in the repo — this module swept hosts via GET only, and the
existing hardening POST case was laundered by `follow_redirects=True`: under the mutant
the foreign-Host POST executed and mutated session state, then the followed redirect GET
returned the 400 the assertion saw. Closed: a POST row against the non-redirecting
`/api/heartbeat` (mutant → 2 named failures) plus `follow_redirects=False` in the
pre-existing hardening test (a defect fix in its own right). *(F2)* `_UNSAFE_METHODS`
narrowed to `{"POST"}` escaped every test; no PUT/PATCH/DELETE route exists to probe, so
it is pinned as DATA with the reason documented. *(F3)* empty-string Origin was unpinned —
an `if not origin_header` fail-open escaped everything; a `""` row now kills it (2 named).
*(F4)* `EXPECTED_ALLOWED_HOSTS` was a dead oracle (declared "in lockstep", asserted by
nothing); it is now consumed by an in-module data pin. The refuters also verified: every
odd population row reaches the middleware byte-exact (instrumented — httpx does NOT strip
` 127.0.0.1 `), 14 exotic host encodings all refuse, and `asyncio.run` co-runs cleanly.
**Final battery vs the FINAL module** (fresh sandboxes, control-subtracted, canaried):
M1→8 flips + the audit pin by name · M2→25 · M3→4 · M4→11 · M5→26 · plus A5→2, A7→2,
A4→1. Zero unexpected flips.

**Unit consistency (everything measured green, 4 lows fixed):** DISC-01 sweep of the full
1,583-line diff — zero gateway/model-id strings; Law-1 — no forbidden client, no writes,
all four workbooks git-tracked; the CUI pre-commit hook accepts the staged unit (exit 0)
with teeth proven in the same sandbox (a planted MSPDI-rooted `.md` canary blocks, exit 1);
drift guards 91 + census 83 + report-sync 8 all pass; the PO-03 flip was red-first *by
population* (with the new module excluded, the audit scan matches nothing). Fixed from its
list: the stale "xfail above" comment in the audit module, the "fictional hosts"
overclaim (`evil.com` is a real domain — reworded to inert-literals-nothing-resolves), and
this ADR's own placeholder section (flagged by the round; this text closes it).

## Deliberately NOT done (measured, not forgotten)

* **`actual_start_driven` is still consumed by no product code** (queue item 4, ENG-DEAD-01) —
  wiring the disclosure into a view is a shipped-code change and stays queued so this unit
  keeps the no-rebuild property. The new engine test asserts the field's *content*, which
  tightens its contract without surfacing it.
* **`test_progressed_finish_fidelity.py` still steps over own-calendar tasks.** Extending its
  floor invariant to wall-bearing tasks would duplicate the new module's coverage at higher
  fixture cost; the named-branch guard is the load-bearing closure. If the invariant is ever
  extended, the new module is the red-first instrument to check it against.
* **`start_cei_by_status_dates` stays count-level** in the oracle — the export suite carries
  no per-activity start-slip list (measured; the JSON's provenance says the same).
* **DCMA-04/10/12/13 and the composite scores stay transcription-basis** — not in the
  delivered suite (ADR-0151's residue, unchanged).
* **PO-04/PO-05 stay open** — CEI/bow-wave and HMI have no independent reference oracle in the
  repo to guard against; blocked on a missing primary oracle, not on engineering.
* **TEST-01 stays the audit module's one live xfail** — 22 playwright modules still pin a
  chromium build number; next in the queue.

## Consequences

* A transcription error, a silent edit of `fuse_exports_2026-06.json`, drift in a committed
  workbook, deletion of the own-calendar floor, and a widening/bypass/unwiring of the Host
  allowlist now all fail CI **by name**.
* `tests/audit` carries 1 live xfail (TEST-01); PO-03's test remains as a permanent pin.
* The queue after this unit: DISC-01 determination (operator) → 001c (operator decision) →
  PO-04/05 (blocked on primary oracles) → `actual_start_driven` wiring → TEST-01 →
  FINAL-REPORT overclaims → stale branches.
