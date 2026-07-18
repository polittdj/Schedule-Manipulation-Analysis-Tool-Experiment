# ADR-0259 — Duplicate resolution: hash-first collapse, same-date review, reversible excludes

## Status

Accepted. Companion to ADR-0258 (same session); extends ADR-0225/0226's content-hash machinery
from a parse-speed cache into the duplicate-integrity layer the master prompt's §2.2 specified:
hash first, never silently drop or merge, the operator decides everything non-provable.

## Context

Re-uploading identical bytes hit the ADR-0226 parse cache (fast) but still entered the session as
a **second version** under a suffixed key — a re-scanned folder doubled every version, and the
version count lied. Two files statused the same day could be the same file copied, a genuine
same-day revision pair, or unrelated — the mtime tiebreak (ADR-0225) ordered them silently and
nothing surfaced the conflict or offered a resolution.

## Decision

- **Byte-identical, same grouping context → collapse loudly.** In `/upload`, a file whose content
  hash already exists in the session *in the same grouping context* (same top folder, or both
  loose) is skipped — with a manifest notice naming both filenames and a log line, never
  silently. Identical bytes in a *different* context are kept: they can legitimately be a version
  of two different Projects. Re-uploading a folder is now idempotent. A flash that carries ONLY
  notices now renders (`_flash_html` previously showed nothing without accepted/errors — an
  all-duplicates or all-unreadable upload landed silently; fixed).
- **Same data date + provably different content → pending review.** `IngestRecord`/
  `ProjectVersion` carry `content_hash` and `excluded`; `group_into_projects` flags a Project
  `pending_review` when non-excluded versions share a data date with ≥2 distinct known hashes,
  with a notice naming the files ("two revisions statused the same day, or a stray copy").
  Files without hashes are never flagged (difference unprovable — only the ordering-tiebreak
  notice applies; no false accusations).
- **The operator resolves in Portfolio — reversibly.** Each version row shows its
  differentiators (report link, data date, activity count) plus an Exclude/Restore toggle
  (`POST /project/exclude` → `SessionState.excluded_keys`). Excluded versions leave every
  analysis population (`ordered()`/`ordered_versions()`) but stay loaded, listed, and badged;
  the Project headline moves to the latest *included* version; excluding one copy of a flagged
  date resolves the review flag (recomputed from the surviving population). Nothing is ever
  deleted or merged. Portfolio headlines the pending-review and excluded counts; the banner
  strip shows the pending-review count session-wide. Population-only: no cache invalidation.

## Consequences

- The master prompt's §2.2 resolution order holds end-to-end: hash-identical handled
  automatically (logged, loud), non-identical surfaced with differentiators, the user chooses,
  nothing silent. Encoded in `tests/engine/test_projects.py` (review/exclude/no-hash cases) and
  `tests/web/test_upload_cache.py` + `test_project_scope.py` (collapse contexts, round-trip);
  browser-verified live.
- The old "re-upload = second entry" behavior is gone by design; the cache-hit speed contract
  (identical bytes parse once) is preserved and still pinned.
- Version 1.0.66 → 1.0.67 (with ADR-0258/0260).
