# ADR-0271: Lessons-learned log (daily-update mandate) + an autonomous rebuild prompt

- **Status:** Accepted
- **Date:** 2026-07-19 (session 2026-07-19b — Opus)
- **Relates to:** ADR-0000 (ADR discipline), ADR-0240 (audit protocol / verify-everything),
  ADR-0246 (handoff auto-inject + archive), ADR-0249 (no flaky/time-based gates)

## Context

The project has 271 decisions on record, a 7.2K-line session log, and a 5.7K-line handoff archive.
That history holds the hard-won judgment of the build — the reversals, the wrong fixes we caught, the
footguns (the 480-minute day, monoculture goldens, the AI figure-gate laundering channel, security
controls built-but-not-wired) — but it is scattered across ADRs and logs and is not readable in one
pass by a new engineer or a fresh agent session. The operator asked for (1) a single cross-cutting
"lessons learned" log that lists what we have done, what we tried, and what did not work, kept current
**daily**, and (2) a separate deliverable: an adversarially-hardened prompt that could drive an
**autonomous** greenfield rebuild of the tool, informed by everything we have learned — explicitly
weighing framework/bundler/CSS choices (React/Vue/Bootstrap/Tailwind), architecture, security,
debugging, UI, local AI, and scalability.

## Decision

1. **Add `docs/STATE/LESSONS-LEARNED.md`** — the durable cross-cutting lessons layer that sits above
   HANDOFF (current state), SESSION-LOG (per-session diary), and the ADRs (decision record). It
   inventories what shipped (v1.0.76), the validated approaches to keep, the dead ends / reversals /
   wrong fixes (with ADR citations), the recurring process friction, the security/parity/architecture
   lessons, the open risks, and a consolidated "if we rebuilt it" section, plus a reversal index and a
   dated Change log.
2. **Standing daily-update mandate.** Every session appends a dated entry to the log's Change log before
   it ends (a one-line "verification-only" entry counts) and records any real lesson in the relevant
   Part the same day. Wired into `CLAUDE.md`'s "Durable state" section so the SessionStart-surfaced
   rules carry it into every session; part of the session Definition of Done alongside HANDOFF/SESSION-LOG.
3. **No time-based enforcement test.** A gate that fails because "today is N days after the last entry"
   is a clock-dependent flake, and ADR-0249 holds that a flaky gate is worse than none. The mandate is
   enforced by the CLAUDE.md standing rule + code review, not a brittle date check.
4. **Deliver the autonomous rebuild prompt as an MS Word document to the operator, not committed.** The
   `.docx` is (correctly) blocked by the CUI pre-commit guard; it is delivered directly. The prompt was
   drafted, then adversarially attacked by independent red-team agents (architecture, security/CUI,
   autonomy/executability), hardened, re-reviewed, and attacked again before delivery — the same
   verify-everything discipline as ADR-0240.

## Consequences

- The drift guard (`tests/test_state_docs.py`) requires ADR-0271 to appear in both `HANDOFF.md` and
  `SESSION-LOG.md`; this ADR ships with those refreshes in the same commit.
- No engine, parity, metric, AI, or UI behavior changes — this is a documentation + process decision.
  The full gate is otherwise unaffected.
- Future sessions inherit a one-pass-readable lessons layer and a standing obligation to keep it current,
  reducing the chance of re-living a already-recorded failure (the ADR-0240 lesson: a mistaken re-fix is
  worse than the drift it chases).
