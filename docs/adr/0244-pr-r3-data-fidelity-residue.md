# ADR-0244 — PR-R3: data-fidelity residue (erosion basis, XER worked weekends, egress set, 24h golden)

## Status

Accepted. The queued "PR-R3 — data-fidelity residue" bundle from the validated prior audits, all
four items in one change (each independently verified; the 24h golden's engine parity confirmed
cell-for-cell before pinning).

## Context

Four small data-fidelity gaps remained after the Law-1 remediation PRs (R2/R2.1):

1. **Margin-erosion mixed-basis fit.** `margin_dashboard._erosion` fits effective margin (work
   days) vs status date across versions, but each version's `effective_margin_wd` is computed with
   *its own* `working_minutes_per_day`. Across a calendar change (e.g. `Hard_File_updated3` Standard
   480-min days → `updated4` 24-hour 1440-min days) the regression conflates two different
   day-length units into one slope — a fast wrong number (Law 2).
2. **XER worked-weekend exceptions dropped.** `xer._parse_clndr_data` mapped `DayWorking=0`
   exceptions to holidays but *skipped every exception with a working span*, discarding worked
   weekends (a Sat/Sun made working) that the MSPDI path already models as `Calendar.working_days`
   (the ADR-0118 driving-slack parity input).
3. **Egress forbidden-set omissions (audit L4).** The net-egress guard listed first-wave provider
   SDKs but not the 2024-2026 LLM clients/gateways (google-genai, groq, together, litellm,
   langchain*) or phone-home telemetry (sentry, posthog, datadog, otel).
4. **Missing the 24h-calendar SSI driving-slack golden.** The operator's `updated3`/`updated4`
   Directional-Path exports demonstrate the per-successor-calendar effect — the SAME predecessors
   carry **32 days** of driving slack on the 8h file and **18 days** on the 24h file — but no gate
   pinned it.

## Decision

1. **Erosion single-basis (item 1).** `MarginMonth` records its `basis_wmpd`. When the dated
   versions do not all share one basis, `compute_margin_dashboard` **suppresses** the fit
   (`erosion_wd_per_month`/`zero_margin_date`/`erosion_r2` → None) and exposes
   `erosion_mixed_basis` (the distinct bases) + `erosion_basis_wmpd` (the single basis otherwise).
   The `/margin` takeaway and the Excel/Word export disclose the basis change ("8h/day vs 24h/day")
   instead of a conflated rate; per-version displayed margin is unchanged. Consistent-basis
   projects (the norm) behave exactly as before.
2. **XER worked weekends (item 2).** `_parse_clndr_data` now returns a fourth set — dates of
   working-time exceptions — and `_project_calendar` keeps those falling on a non-working weekday
   as `Calendar.working_days` (a changed-hours exception on a working weekday is still dropped, out
   of the single-block model). Mirrors the MSPDI `DayWorking=1` handling.
3. **Egress set additions (item 3).** The modern LLM/telemetry distributions join
   `FORBIDDEN_RUNTIME_DISTRIBUTIONS` (zero false-positive risk — it checks only the shipped tool's
   *declared* runtime deps). The import-check set `FORBIDDEN_CLOUD_MODULES` gains only modules that
   can never be a build-toolchain transitive dep (the LLM clients + `sentry_sdk`), each verified
   absent from the dev venv at authoring time; the broader observability packages stay
   distribution-only to keep the import check false-positive-free.
4. **24h SSI golden (item 4).** New `tests/fixtures/golden/ssi_hardfile_24h_uid155/` — gzipped
   MSPDI fixtures for both snapshots + a `case.json` whose driving-slack-days-by-UID map is read
   straight from the SSI exports (no hand-transcription). `tests/parity/test_ssi_hardfile_24h_uid155.py`
   asserts `compute_driving_slack` reproduces **all 100 rows** of each export within 0.01 day
   (verified at build time: 0 mismatches, fractional and negative slacks included) and pins the
   headline 32-day → 18-day calendar effect.

## Consequences

- The margin-erosion trend can no longer report a misleading slope across a calendar change; it
  discloses the basis instead — consistent with the tool's "NA reads '—', never a fabricated
  number" posture.
- The XER path now feeds worked weekends into the same driving-slack parity the MSPDI path does;
  full end-to-end verification waits on the operator re-adding a real worked-weekend `.xer` (the
  synthetic fixture proves the parse).
- The egress guard covers the current LLM/telemetry landscape; the transitive-closure blind spot
  (direct-requires only) remains documented future work, not addressed here.
- The 24h golden locks the ADR-0118 per-task-calendar driving slack cell-for-cell, so a future
  engine change that broke the 24-hour effect fails the parity gate.
- v1.0.54 → 1.0.55; wheel + 9 installers rebuilt in lockstep; HANDOFF/SESSION-LOG refreshed in the
  same commit.
