# ADR-0168 — SSI driving-path golden for Hard_File focus UID 155 (base + updated)

## Status

Accepted. Closes backlog #67. Operator delivered two SSI Directional Path Tool exports on
2026-07-08 for focus UID 155 on `Hard_File.mpp` and `Hard_File_updated.mpp`; both are tracked
in-repo under `00_REFERENCE_INTAKE/ssi/` (non-CUI build inputs per CLAUDE.md / ADR-0152).

## Context

`#67` was the last open SSI-golden item. The two exports
(`Hard_File_Path_Trace_UID_155_...xlsx` and `Hard_File_Path_Updated_Trace_UID_155_...xlsx`) are
"get all dependencies" runs: SSI lists every predecessor of the focus with its Driving Slack and
buckets each row into a `Path` number by exact driving-slack value. **Path 01 is the strict 0-day
driving path** (9 tasks on both snapshots); Path 02/03 carry the sub-day / multi-day near-path
tasks.

Before pinning (Law 2), the engine was validated against the exports directly:

- The engine's **zero-driving-slack set** (`driving_slack_minutes == 0`) reproduces SSI's Path 01
  membership **EXACTLY, UID-for-UID, on BOTH snapshots**: `{9, 36, 141, 144, 145, 146, 155, 156,
  411}`, no extras, none missing.
- The engine's ordered driving chain, filtered to those members, reproduces SSI's Path 01 **row
  order exactly**: `141 → 156 → 36 → 9 → 144 → 145 → 146 → 411 → 155`.
- Every Path 01 member is `on_driving_path` at `PathTier.DRIVING` with 0 driving slack; the focus
  UID 155 terminates the chain at 0 slack.

The engine's **broader** `on_driving_path` set (22 tasks) additionally flags sub-day-slack tasks
as driving — the documented ragged-minutes rule (`test_subday_slack_is_driving_like_ssi_displays_it`)
— which SSI files under Path 02/03. We therefore gate the **strict 0-day driving path**, the same
basis as the `ssi_uid67` / `ssi_uid145` goldens, not the near-path set.

## Decision

- New golden `tests/fixtures/golden/ssi_hardfile_uid155/case.json` records, per snapshot: the SSI
  export filename, total dependency-row count, per-Path row counts, the ordered Path 01 driving
  path, the 0-day driving-slack map, and the SSI Drag column **for provenance only** (the engine
  does not compute drag; ADR-0158). The schedule fixtures are reused from
  `tests/fixtures/golden/fuse_hardfile/*.mspdi.xml.gz` (no duplicate binaries).
- New parity test `tests/parity/test_ssi_hardfile_uid155.py` (4 cases, `@pytest.mark.parity`)
  asserts the exact set, per-member 0 slack + DRIVING tier, exact ordered chain, and the
  all-zero whole-day slack map — for both `Hard_File` and `Hard_File_updated`.

No engine or `src/` change: the engine already reproduced the export exactly, so this is a
validation + pin only (no wheel/installer lockstep rebuild).

## Consequences

- `#67` closed with a second SSI driving-path oracle (the first is `ssi_uid67`/`ssi_uid145` on
  Project5, and `ssi_uid152` on the large master IMS), now covering a two-snapshot base→updated
  pair on the Hard_File case.
- The Drag column is recorded but deliberately ungated, consistent with ADR-0158 (gating engine
  logic to an SSI convention the engine does not model would be curve-fitting).
