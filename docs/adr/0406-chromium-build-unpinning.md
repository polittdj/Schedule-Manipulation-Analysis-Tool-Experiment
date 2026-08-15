# ADR-0406 — TEST-01 closes: 22 chromium build-number pins become sorted-glob resolvers, the audit xfail flips, and the census that guards it survives scanning itself

**Status:** Accepted · **Date:** 2026-08-15 · **Closes:** TEST-01 (audit 2026-08-13; the audit
module's last live xfail) · **Also lands:** OR-10's operator verification ledger
(`docs/STATE/OPERATOR-REQUESTS.md`).

## Context

22 playwright test modules carried the byte-identical line
`CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")` feeding their module-level
skip conditions. A container image bump to any other chromium build would flip **every** browser
test to a silent skip — the exact "browser-gated proof that never executes" failure class
ADR-0304/0305 exist to retire. The r11 module was fixed to resolve the vendored browser by glob
(`chromium*/chrome-linux/chrome`); the fix was never propagated, and
`test_test01_no_test_hardcodes_a_chromium_build_number` recorded the debt as a strict xfail.

## Decision

- **Every offender resolves the FIRST vendored chromium by sorted glob** (r11's discipline,
  compressed to the modules' existing constant shape):
  `_PW_CHROMES = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))` with a
  digit-free `absent` fallback path — so "no vendored chromium" still reads as the same
  module-level skip, never an error, and any build the container ships is found.
- **The population was enumerated with the audit's own regex** (`chromium-\d{3,}/`), not a loose
  grep: 23 matches = 22 real offenders + the audit module's own explanatory comment, which
  **self-matched the scan it documents** (the census rglobs every test file, its own included).
  The comment is reworded to describe the pinned segment without ever writing it with its
  trailing slash — the r11 negative-control convention, now stated explicitly in the comment.
- **The strict xfail marker is removed**; the scan stands as the permanent whole-tree census.
  A mechanical applier asserted its old-strings verbatim (refusing to run blind against a
  drifted tree) and self-checked the census over the final tree: zero offenders.
- **OR-10's ledger** lands in `docs/STATE/OPERATOR-REQUESTS.md`: OR-07/08/09 (the gateway-arc
  chat directives) recorded verbatim with their shipped ADR/PR/version; the
  **pending-operator-verification table** (V-1 arm-once flow · V-2 Bearer acceptance ·
  V-3 transaction-log spot-check, each with its concrete "how"); the blocked-on-operator list;
  and the live agent queue — so "where we are / what's left / what's still to verify" has one
  operator-facing page, kept in lockstep with HANDOFF's per-unit rotation.

**Tests + docs only — no shipped code**: version stays v1.0.205, no wheel/installer rebuild
(ADR-0395/0399/0400/0401 precedent).

## Verification (QC-1)

- *The flip is real:* `tests/audit` runs **21 passed, 0 xfailed** — the module's first
  xfail-free run; repo-wide the ONE remaining strict xfail is JCL-BR-01.
- *The census has teeth (canary red-proof):* a planted `tests/zz_canary_test01.py` containing a
  pinned `chromium-9999/` path turned `test_test01_no_test_hardcodes_a_chromium_build_number`
  **RED by name**; removed (removal verified), 21/21 green again.
- *The 22 modules are undamaged:* spot-check trio collects and playwright-skips exactly as
  before (1 passed, 5 skipped — the env-gated baseline); the negative control
  (`test_test01_negative_control_globbed_module_is_clean`) still pins r11's glob.
- Full gate figures on the final tree in the handoff's Gate-at-close.

## Deliberately NOT done

- **No shared resolver module.** 22 four-line local resolvers were chosen over a by-path-imported
  helper: the modules are independently collectible under bare `pytest` (`tests/` is not a
  package — the oracle-corpus by-path pattern costs 6 lines per consumer), and the census now
  makes any future re-pin loud, which was the actual defect. Deduplication without the census was
  how 22 copies drifted in the first place; the census without deduplication is sufficient.
- **The headless-shell glob stays r11-only** — the 22 modules launch full chrome, as they always
  did; widening their resolver to headless-shell would change what they test.
