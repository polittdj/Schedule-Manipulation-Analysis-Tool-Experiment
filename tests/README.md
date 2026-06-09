# tests/

Test suite for the schedule-forensics tool. Built test-first (TDD) across Phase 2
milestones; see `docs/PLAN/RTM.md` for the requirement → test mapping.

## Hard rule — synthetic fixtures only (CUI)

`tests/fixtures/` is the **only** place a schedule-format file may live in this
repo, and every such file MUST be **synthetic / hand-authored** with no real
NASA or CUI content. `.gitignore` blocks all schedule formats repo-wide and
re-allows them *only* under `tests/fixtures/`. Never copy a real `.mpp`, Acumen
export, or SSI export into the repo — golden/real reference cases stay outside
the repo (or in the git-ignored `local_parity/`), per LAW 1.

## Planned structure (filled during Phase 2)

- `tests/fixtures/` — synthetic schedules + expected-value tables.
- `tests/unit/` — engine units (CPM, float, driving slack, metrics).
- `tests/parity/` — parity suite vs. Acumen Fuse v8.11.0 and SSI golden numbers.
- `tests/guards/` — CUI/egress guard tests (e.g. fail if a forbidden network
  client library is importable).
