# ADR-0002: Do Phase 0 greenfield work on the assigned feature branch

- **Status:** Accepted
- **Date:** 2026-06-05 (session A1)
- **Relates to:** §0.5 (greenfield on a branch + draft PR; preserve `.git`), §4.1

## Context

The build prompt §4.1 suggests creating a fresh branch named like
`claude/greenfield-init-YYYY-MM-DD`. The session's harness instructions, however, pin
development to the branch **`claude/intelligent-fermat-3MBqk`** and forbid pushing to a
different branch without explicit permission. The greenfield *wipe* itself was already
performed upstream (commit `882dec3`), so no destructive wipe needs to happen on a new
branch now.

## Decision

Perform Phase 0 scaffolding on the assigned branch `claude/intelligent-fermat-3MBqk`
and open the Phase 0 draft PR from it. The prompt's branch name was illustrative ("e.g.");
the binding constraint is the harness branch assignment + "never push to a different
branch."

## Consequences

- We honor both the prompt (greenfield on a branch, draft PR, preserve history) and the
  harness branch pin. `.git` history is fully preserved; `main` is untouched.
- The PR for `claude/intelligent-fermat-3MBqk` is the Phase 0 deliverable for Gate 1.
- Future sessions continue on this same branch unless the user reassigns it.
