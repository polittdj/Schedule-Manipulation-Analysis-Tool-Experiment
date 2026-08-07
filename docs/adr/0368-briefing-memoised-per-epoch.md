# ADR-0368 — the Executive Briefing is memoised per epoch and audits once per build

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0281 (precomputed audits, single-flight stripes)

## Context

Audit P1 (2026-08-07): every request to `/briefing`, Mission Control (`/`) or
`/export/{fmt}/briefing` rebuilt the deterministic Executive Briefing from scratch — a full
DCMA audit plus a findings pass, ~0.56 s with two 9 MB files loaded. Worse, the audit ran
**twice** per build: `build_briefing` computed `audit_schedule(subject, cpm, parity)` for the
verdict, then called `recommend()` WITHOUT ADR-0281's `precomputed_audit` parameter, so the
recommender recomputed the identical audit — and each audit run embeds the DCMA-12
delay-injection CPM re-solve. The document is deterministic (Null backend) and depends only on
the solvable set, the scope epoch, the parity toggle and the report day.

## Decision

1. **`build_briefing` hands its audit to `recommend(precomputed_audit=audit)`** — the ADR-0281
   contract guarantees byte-identical findings; one DCMA audit per build, ever.
2. **`SessionState.briefing_for(schedules, cpms)`** memoises the deterministic build:
   - keyed by `scope_signature()` (which already folds in the Acumen-parity toggle), the
     report day, and the **identity** of the exact ordered solvable set (the same
     identity-check discipline as every cache tier — a re-upload creates new Schedule
     objects; a byte-identical re-upload is ADR-0259-deduped and legitimately keeps the memo);
   - **single-entry** (the current epoch only), so epoch flips can never accumulate retained
     schedule lists; wiped by default (not in the wipe keep-set);
   - cold builds run under the ADR-0281 single-flight stripe (`briefing\x1f<sig>`).
3. `/briefing`, `/` and `/export/{fmt}/briefing` call `briefing_for`; **`/api/ai/briefing`
   keeps building directly** — the live-model polish is non-deterministic by design and must
   never be cached.

## Verification

`tests/web/test_briefing_memo.py`: cold and warm `/briefing` renders are **byte-identical**
(the render-diff guard — the memo changes cost, never a byte of output) with exactly one build
across `/briefing`×2 + `/` + the export; a parity toggle re-keys (1→2→3 builds); an identical
re-upload keeps the memo while changed bytes force a rebuild.
`tests/ai/test_briefing.py::test_build_briefing_runs_exactly_one_dcma_audit` counts
`audit_schedule` at BOTH from-import bindings. Proven able to fail: memo bypassed → 2 named
failures (byte-identity stayed green — both sides fresh); signature dropped from the key → the
toggle test alone; `precomputed_audit` dropped → the one-audit test alone.

## Deliberately NOT done

- `ai/qa.py`'s workbook fact sheet still calls `build_briefing` directly (it runs in the
  ai layer with no session handle); Ask-the-AI cost is a separate concern.
- No cross-day cache: the document stamps "today", so the memo dies at midnight by key.
- The ~150 MB-per-loaded-file RSS finding (no per-file unload) is untouched — separate queue
  item.
