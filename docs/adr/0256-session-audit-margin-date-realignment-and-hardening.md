# ADR-0256 — 2026-07-17 session audit: margin-risk date realignment + band/notice/i18n/EOL hardening

## Status

Accepted. The operator-requested ADR-0240 audit of the day's work (ADR-0254 margin panel,
ADR-0255 roles) and the repo: a 4-agent orchestrated sweep (margin-panel / roles / state-docs /
security-CUI) with adversarial verification of major findings and lead re-validation of
everything against executable evidence, followed by this fix PR.

## Audit outcome

**Extensively clean.** The auditors independently re-derived the Fig 5-30 band arithmetic
(exact match at 9 probe dates), swept the CDF reads to exact `bisect_right` equality across
adversarial sample sets, pinned `deterministic_margin_bounds` == the SSI anchor in five
configurations, verified export-vs-panel byte parity and the cross-route covered-percentile
pin, proved the roles contract (nothing hidden; `role=None` upload behavior identical to
pre-F4 across all 32 input combinations; all interpolations `_e()`-escaped with a live
hostile-key probe), and confirmed state-doc/lockstep/ADR-continuity integrity.

**One CONFIRMED major, fixed here — F1, margin-risk dates unrealigned.** On a progressed
schedule, `/api/margin/risk` and the margin export printed D/E/percentile dates on the raw
pure-CPM axis (completed work packs at the project start — dates months before the stored
plan), while `/sra` showed the SAME seeded run realigned to the stored finish. Fix: additive
`sra.stored_finish_correction(schedule, target_uid, deterministic)` exposing the engine's own
constant realignment (same anchor selection as `_build_ssi_result`); `_margin_risk_data`
converts every displayed date through it. Pinned by a progressed-fixture regression test:
risk-D == `/api/sra/ssi`'s deterministic date, E == the stored predecessor finish, P50 ==
the SRA page's P50.

**Minors fixed here:**
- **F3** — a single dated month drew a zero-area band polygon while the legend advertised the
  band; now a bar-width segment renders.
- **F2** — the `MarginMonth` offset fields' comment claimed the risk panel reads them (it
  deliberately does not — different axis); comment corrected.
- **F4** — `margin_risk_read`'s docstring overclaimed a display-level iff (1-dp rounding can
  show `margin_needed == margin_wd` on a not-covered row); docstring now states the raw-offset
  `covered` flag is authoritative.
- **ROLES-1** — advisory ingest notices (no-title grouping, the mtime version-order tiebreak,
  the RAM warning) render only on the dashboard flash, so they now GATE the role landing
  (disclosure outranks the landing, same as errors); the pre-F4 no-role paths are untouched.
- **ROLES-2 (partial)** — the role strip's two headings dropped `data-no-i18n` so the AI
  translation path can reach them; full catalog entries for the role labels/blurbs are queued.
- **STATE-1** — REPO-INVENTORY body lines were stale (v1.0.51 / "through ADR-0251"); fixed.
- **SEC-1** — `.gitattributes` (`* text=auto`) left 16 tracked blobs — including both committed
  `.aft` references, a parity `.xer` fixture, and the generated installers — one
  renormalization away from byte-rewrites that would break the CUI guard's
  `inherited_from_main` byte-identity rule and the installer lockstep test. Guarded sets are
  now `-text` (`*.aft/*.xer/*.mpp/*.xlsx/*.docx`, `00_REFERENCE_INTAKE/**`, `installer/**`,
  `tests/fixtures/**`); verified the attribute change dirties no tracked file.

**Recorded, deliberately NOT fixed here (own ADR + operator approval required):**
- **SEC-2** — the loopback app's state-mutating POSTs carry no CSRF/Origin protection (a
  cross-site form POST can silently change operator-set parameters; probes confirmed fail-soft
  limits the blast radius, but the surface is real).
- **SEC-3** — no Host allowlist (`TrustedHost`): the classic DNS-rebinding read vector for
  loopback apps — on a production machine that means schedule content (real CUI). Both touch
  every route; a hardening design goes to the operator before build (queued).

## Consequences

- New additive `sra.stored_finish_correction` (pinned; nothing else changed in `sra.py`);
  `_margin_risk_data` realigned; JS band single-month fallback; notices gate the role landing
  (+ regression tests for both behavior changes); doc-truth corrections; `.gitattributes`
  hardening. v1.0.64 → v1.0.65 (wheel + 9 installers in lockstep).
- The audit's clean-area evidence (band arithmetic, CDF sweeps, XSS probes, 32-combination
  upload matrix) lives in the session log for future reference.
