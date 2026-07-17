# ADR-0246 — Session-start ritual: auto-inject the live HANDOFF + archive its history

## Status

Accepted. Operator directive, 2026-07-17: "find a way to ALWAYS read the entire HANDOFF before
starting a session." Operator chose the "auto-inject current + archive rest" option when presented
with the trade-off.

## Context

`docs/STATE/HANDOFF.md` is the "read first" durable-state doc a fresh session resumes from. Two
problems had accumulated:

1. **It was optional in practice.** Nothing *guaranteed* the handoff was read — a session relied on
   the agent choosing to `Read` it. The operator wanted a hard guarantee.
2. **It had grown to 417 KB** — 76 stacked handoff sections, append-in-place. That exceeds the
   256 KB single-`Read` limit (so "read the entire HANDOFF" meant multiple chunked reads, easy to cut
   short) and would cost ~100k tokens to inject wholesale. The full append-only per-session history
   already lives in `docs/STATE/SESSION-LOG.md`, so the inline history in HANDOFF.md was redundant.

The SessionStart hook (`.claude/hooks/session_start.sh`, registered in `.claude/settings.json` for
both `startup` and `resume`) already emits its stdout as session context — that is how the toolchain
preflight appears at the top of every session. That is the natural, reliable injection channel.

## Decision

**Auto-inject + archive**, so the guarantee is cheap and sustainable rather than a 100k-token tax:

1. **Auto-inject.** The SessionStart hook now prints HANDOFF.md's *current section* — everything above
   the first `# (prior)` heading — into session context on startup and resume, right under the
   preflight. The current state and the NEXT queue are therefore always in front of the agent from the
   first turn, with no reliance on it remembering to `Read` the file.
2. **Archive.** The 76 prior handoff sections moved verbatim (newest-first) to
   `docs/STATE/HANDOFF-ARCHIVE.md`. HANDOFF.md now holds only the current STATUS section plus a single
   `# (prior) handoffs — archived` pointer to the archive. The file dropped 417 KB → ~4.5 KB and is
   trivially one-`Read`-able, so "read the entire HANDOFF" is now both literal and cheap.
3. **New invariant + guard.** `tests/test_state_docs.py::test_handoff_stays_one_pass_readable` fails if
   HANDOFF.md exceeds 64 KB or carries more than one `# (prior)` heading. This enforces the small-file
   invariant so a future session cannot silently let it grow back by stacking handoffs in place.
4. **Convention change (CLAUDE.md "Durable state").** Writing the next handoff MOVES the current
   section to the TOP of `HANDOFF-ARCHIVE.md` (demote its `# Handoff` heading to `# (prior) Handoff`)
   and REPLACES the current section in HANDOFF.md — it no longer appends a new `# (prior)` section in
   place.

The single `# (prior)` pointer is deliberate: `test_handoff_top_section_pins_the_current_pyproject_version`
uses the first `# (prior)` heading as the boundary between the "current" section and history, so the
pointer preserves that marker and the existing drift guard (highest-ADR-in-both-docs, version-in-top)
is unchanged and still enforced.

No `src/` change — docs, one hook, one test — so the wheel and the 9 installers stay in lockstep and
need no rebuild; the version stays 1.0.56.

## Consequences

- Every session — startup or resume — begins with the live handoff already in context. The
  "READ THIS FILE FIRST" instruction is now backed by a mechanism, not just discipline.
- The handoff is permanently one-pass readable; the size guard prevents regression.
- Handoff history is preserved intact in `HANDOFF-ARCHIVE.md` (and the running log stays in
  `SESSION-LOG.md`); nothing is lost, only relocated.
- Future sessions must follow the move-to-archive convention (documented in CLAUDE.md and enforced by
  the size guard) rather than appending in place.
- The hook is fail-soft: if HANDOFF.md is absent it prints nothing and still exits 0.
