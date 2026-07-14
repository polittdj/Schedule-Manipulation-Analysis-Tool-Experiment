# ADR-0225 — Group files into Projects + Portfolio Manager view (v4 Feature 1)

## Status

Accepted. First increment of the **SMAT v4** feature build (grouped ingestion → scale/RAM → NASA
margin → roles), delivered incrementally one PR per feature. This PR is Feature 1; it adds a grouping
layer + a portfolio rollup **on top of** the existing single-schedule engine — no engine math changes,
parity untouched.

The v4 plan was **red-teamed before building**: ten candidate faults were each verified multiple ways
and the risky ones sandbox-tested in isolated worktrees. Two findings shaped this PR (see Decision):
a browser `<input webkitdirectory>` does **not** reliably carry a file's folder path in the multipart
`filename`, and a plain multipart upload carries **no** last-modified time — both are solved with an
explicit client-sent companion field. A third (pydantic `model_dump_json` round-trips a `Schedule`
byte-deterministically with identical analysis) is banked for Feature 2's cache.

## Context

The tool loaded many files but treated them all as versions of one schedule; there was no notion of a
**Project**, no folder ingest, and a 100-file cap. Operators actually hold many projects, each with a
version history, often filed in nested folders (e.g. `Project/2023/Jan/…`). Operator rules
(confirmed): loose files group by document Title; **a folder — any nesting depth — is exactly one
Project named by its top folder**, every schedule beneath it a version (sub-folders are just filing and
are ignored); **no file-count cap**.

`Schedule.name` already held the document Title but conflated it with a filename fallback
(`mspdi.py` `_text(root,"Title") or _text(root,"Name") or source_file`), so grouping could not tell a
real Title from a filename. Version ordering already existed (`engine/trend.py::order_versions`, by
`status_date`, no mtime tiebreak). No portfolio view existed.

## Decision

- **Model:** add `Schedule.project_title: str | None` — the **real** document Title only (`None` when
  absent), populated from MSPDI `<Title>` (only), XER `proj_short_name`, and the tool's own JSON.
  Additive, picklable, `name` unchanged → zero parity impact.
- **Grouping (`engine/projects.py`, pure/deterministic):** `group_into_projects(records)` →
  `Project(title, origin, versions, needs_attention, notices)`. Loose files group by trimmed
  case-insensitive `project_title`; a title-less loose file is its own **needs-attention** Project by
  filename; a **folder** (its `IngestRecord.folder` = the top folder name) is one Project regardless of
  internal titles, with a **non-blocking notice** when internal titles disagree. Versions are ordered
  oldest-first by `status_date` (reusing the `order_versions` contract) with a **file last-modified
  tiebreak** that is a strict no-op when no mtime is present (sandbox-verified: existing ordering
  unchanged), flagging when the tiebreak decided the order so the UI can say "verify the order".
- **Ingestion (web):** the dropzone gains a **folder picker** (`webkitdirectory`) beside the file
  picker. Because a strict CSP blocks inline scripts and `form.submit()` drops appended FormData, the
  vendored `home.js` writes a hidden `file_meta` field — a JSON array (per file, in order) of
  `webkitRelativePath` + `lastModified`. `/upload` reads it: the relative path's **first segment is the
  folder/Title**, `lastModified` is the ordering tiebreak. The **100-file cap is removed**; non-schedule
  files inside a folder are **skipped** (not errored); per-file failures are still recorded and skipped
  (fail loud). `SessionState.file_meta` records each file's (folder, mtime); `SessionState.projects()`
  derives the grouping on demand.
- **Portfolio Manager view (`/portfolio`, in the OVERVIEW spine):** one row per Project — version
  count, latest data date, computed finish, effective schedule margin, DCMA-14 pass/fail — with an
  expandable version history linking each version to its full report. Reuses `analysis_for` +
  `compute_margin`; a Project whose latest version won't solve shows "—" (never a 500).

## Consequences

- Files/folders now organize into Projects; the Portfolio view is the new top of the OVERVIEW nav.
  Chromium-verified in all four themes (console/daylight/apollo/jarvis): the rollup + drill render,
  tokens-only, no console errors.
- **Scale caveat:** F1 removes the cap and does recursive folder ingest, but still holds full parsed
  schedules in RAM and converts `.mpp` per-file. **Feature 2** (next PR) makes thousands cheap — a
  single persistent JVM, a lazy summary tier, and a SQLite cache — and adds the explicit "load into
  RAM" action. F1 is memory-correct for realistic counts; F2 is the performance layer.
- No engine/metric change; **parity untouched**. `tests/guards/test_egress.py` unaffected (no new dep).
- Tests: grouping unit cases (title/folder/needs-attention/notice/tiebreak); web ingestion
  (loose-by-title, folder-by-top-name, no-cap, non-schedule-skip, disagreeing-titles notice); the
  Portfolio rollup render; `project_title` across MSPDI/XER/JSON; the no-cap test replaces the old
  batch-cap test; `/portfolio` added to the air-gap scan. Version 1.0.36 → 1.0.37; wheel + 9 installers
  in lockstep.
