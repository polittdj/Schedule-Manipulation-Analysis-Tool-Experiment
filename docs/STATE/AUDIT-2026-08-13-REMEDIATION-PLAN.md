# Forward remediation plan — validated findings only

Ground rule (from the task): **no code was changed and nothing was fixed in this session.** Every item
below is a *future* prompt. Each carries a red/green test (already written and proven in
`test_audit_findings.py`, or specified) that must be RED before the fix and GREEN after — the fix is
not "done" until its own test flips and a mutation proves the test has teeth (QC-1).

Ordering is by risk-to-close ratio, matching the repo's Band-1 posture. **P0 is not a code fix** — it is
an organizational determination the code cannot make.

---

### P0 — DISC-01: public disclosure of gateway host + ITAR model + workstation ops
- **Owner:** NASA authorizing official / ISSO / export control (NOT engineering alone).
- **Prerequisite:** a releasability determination for `<gateway-host>`,
  `<itar-model-id>`, and the patched-workstation description in a *public* repo.
- **Action if non-releasable:** the tokens are in git *history* (since `a19b969`), so removal is not a
  single edit — it needs history rewrite (filter-repo) + force-push + invalidation of forks/caches, OR
  making the repo private. Engineering executes only after the official decides.
- **Failure modes:** a naive file edit leaves the tokens in history/​forks (false remediation).
- **Rollback:** N/A (determination, not code).
- **Negative test:** `git grep -n <gateway-host> $(git rev-list --all)` returns 0 after remediation;
  a test asserting the tokens are absent from tracked files (red now, green after redaction).
- **Closure evidence:** signed releasability memo + clean history grep.

### P1 — GW-02: make the sovereignty banner OBSERVED, not config-derived
- **Owner:** engineering. **Prereq:** none (pure view change; do not touch engine/).
- **Action:** render the `Banner` that `route_backend()` returns (thread it to `_banner_html`) instead of
  `banner_for(state.ai_config)`. Update the six user-visible strings + i18n; the two that print inside
  exported exhibits (`ai/brief.py`, `web/sra.py`) must reflect the observed backend too.
- **Failure modes:** caching the routed banner staler than the backend probe; missing the exhibit copies.
- **Rollback:** revert the view commit (no data migration).
- **Negative test:** `test_gw02_shown_banner_matches_routed_backend` (currently xfail/red) → green;
  add a fake non-local backend and prove the banner goes cloud (mutation).
- **Closure evidence:** the test flips; `render-verify` on the settings + a page shows the observed state.

### P2 — SEC-01: pin `_ALLOWED_HOSTS` contents (Host-header allowlist)
- **Owner:** engineering. **Prereq:** none. **Action:** add the exact-value pin + a behavioural sweep
  (mirror `test_loopback_allowlist.py`), so a widened entry fails CI.
- **Failure modes:** pinning by importing the constant (an oracle that reads what it judges — forbidden);
  use a test-side literal.
- **Negative test:** `test_sec01_allowed_hosts_pinned_to_exact_loopback_set` + a sandbox mutation adding a
  gateway host must go red.
- **Closure evidence:** mutation caught by name.

### P3 — TEST-01: stop hard-coding the chromium build number in 22 test modules
- **Owner:** engineering. **Prereq:** none. **Action:** replace `chromium-1194/...` with r11's globbed
  resolver (`chromium*/chrome-linux/chrome`) or playwright's own resolution; centralize in one helper.
- **Failure modes:** leaving skip-on-missing so a bump still silently skips; a whole-module skipif that
  hides real failures.
- **Negative test:** `test_test01_no_test_hardcodes_a_chromium_build_number` (xfail/red) → green; simulate
  a bumped build dir and confirm tests still resolve a browser (not skip).
- **Closure evidence:** the scan test flips; a build-dir rename doesn't reduce collected browser tests.

### P4 — HOOK-01: broaden the CUI pre-commit content detector
- **Owner:** engineering + operator policy. **Prereq:** decide the acceptable false-positive cost.
- **Action:** add magic-byte content detection for image/PDF/ZIP/DOCX renames (sniff by bytes, not
  extension), covering `blocked.ext.png` double-extensions and PDF/ZIP schedule artifacts.
- **Failure modes:** firing on legitimate committed PNG/PDF/DOCX (120+ tracked PNGs) → guard gets disabled
  → guards nothing. Must sniff for *schedule signatures inside* the container, not block all images.
- **Negative test:** `test_hook01_precommit_sniffs_image_and_doc_renames` (xfail/red) → green; scratch-repo
  battery: `data.mpp.png`, `report.pdf`(schedule), `sched.mpp.zip` must BLOCK while a real screenshot PNG ALLOWs.
- **Closure evidence:** battery flips for schedule-bearing renames, stays ALLOW for genuine assets.

### P5 — DOC-01: correct FINAL-REPORT overclaims
- **Owner:** docs. **Action:** reconcile "COMPLETE / CI green / parity-green" with the current open-item
  list, the "RECORDED NOT BUILT" gateway, and the placeholder license; state parity precisely (CPM exact;
  Fuse transcribed; SRA within tolerance).
- **Negative test:** a doc-lint asserting FINAL-REPORT does not claim "complete/parity-green" while
  HANDOFF lists open Band-1 items (red now).
- **Closure evidence:** the doc-lint passes; wording matches §8 of the audit.

### P6 — NUM-01: language + provenance for "parity"
- **Owner:** numerical. **Action:** relabel tolerance-accepting SRA/SSI results as "within documented
  tolerance," not "parity"; annotate the Fuse oracle as transcribed-from-reference (independence caveat).
- **Negative test:** a grep-guard that fails if a parity doc says "delta = 0" for a family whose test uses `abs(... ) <= tol`.

### P7 — LIC-01: choose a license
- **Owner:** rights-holder + counsel. Not engineering. Closure: a real LICENSE committed.

### P8 (low) — ENG-DEAD-01: consume or document `actual_start_driven`
- **Owner:** engineering. Either surface it in a view (its documented purpose is the "anchored to reported
  progress" disclosure) or annotate it as an intentionally-exposed-but-unconsumed channel. Test: a consumer
  assertion, or a docstring pin.

---

## Test artifacts produced this session (no repo code touched)
- `test_audit_findings.py` — 21 tests, 17 pass / 4 xfail(strict), each with a proven red AND green mode.
- Scratch-repo pre-commit batteries (`hooktest/`, `hooktest2/`) — 19 red/green cases.
- CPM hand-oracle probe, XXE probe, secret-scan negative control, magic-byte reconciliation.
All live under `/tmp/.../scratchpad/audit-2026-08-13/`. The next session moves the test module into
`tests/audit/` and drives each xfail to green per the plan above.
