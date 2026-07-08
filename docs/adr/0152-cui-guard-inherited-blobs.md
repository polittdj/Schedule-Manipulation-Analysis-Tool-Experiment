# ADR-0152 — CUI pre-commit guard: allow blobs inherited byte-identical from origin/main

## Status

Accepted. Operator-approved 2026-07-08 (explicit choice from three offered options).

## Context

The operator committed the reference export suite (`00_REFERENCE_INTAKE/*.mpp/.xlsx/.aft`) to
`main` through the GitHub web UI ("Add files via upload", five commits feeding the ADR-0151
ENGINE==FUSE parity flip). Web uploads never pass through the local pre-commit hook, so the
repo's default branch now permanently carries files matching the guard's blocked extensions.

Consequence: every local `git merge origin/main` stages those files (they are new relative to
the branch), and the guard blocked the merge commit — wedging every PR branch behind main, as
happened resolving PR #289's conflicts. Blocking added zero protection: the identical bytes are
already public history on the default branch.

Per CLAUDE.md's CUI boundary, these build/reference inputs are **operator-confirmed NOT CUI**;
they were kept out of git as defense-in-depth only. Real CUI remains the operator's production
schedules inside the deployed tool, which never touch git or a build session.

## Decision

`.githooks/pre-commit` gains one narrowly-scoped exception (`inherited_from_main`): a staged
file with a blocked extension passes **only when its staged blob hash is byte-identical to
`origin/main`'s blob at the same path**. Everything else about the guard is unchanged:

- a **new** schedule/Office/pickle artifact anywhere outside `tests/fixtures/` → still blocked;
- a **modified** copy of an intake file (same path, different bytes) → still blocked;
- a blocked-extension file at a path that does not exist on `origin/main` → still blocked;
- if `origin/main` is unfetched/absent, the check fails closed → blocked.

Pinned by three scratch-repo tests in `tests/guards/test_precommit_blocklist.py` that execute
the real hook (identical → pass; tampered → block; new → block).

## Consequences

- Merges of `main` flow again; the guard still stops every genuinely new leak from a build
  session, which is the threat it exists for.
- The inherited-blob rule keys on `origin/main` specifically — content must already have been
  accepted onto the default branch (by the operator or a reviewed merge) before it is inheritable.
- The "reference binaries stay out of git" defense-in-depth posture is now formally superseded
  by the operator's decision to keep them in-repo; `.gitignore` entries remain for local scratch
  copies at other paths.
