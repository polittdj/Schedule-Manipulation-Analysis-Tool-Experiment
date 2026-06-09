# ADR-0000: Record architecture decisions as ADRs

- **Status:** Accepted
- **Date:** 2026-06-05 (session A1)

## Context

This tool is built autonomously across many sessions; any single context window may
be lost. Significant decisions must survive in git, not in chat history.

## Decision

We record every significant architectural/process decision as a numbered Markdown
ADR in `docs/adr/NNNN-title.md` (Michael Nygard format: Context / Decision /
Consequences / Status). ADRs are append-only; superseding decisions get a new ADR
that references the one it replaces.

## Consequences

- A new session can reconstruct *why* the build is the way it is from `docs/adr/`.
- The RTM and HANDOFF reference ADRs for rationale instead of duplicating it.
- Trivial choices are not ADR'd; only ones with lasting impact or trade-offs.
