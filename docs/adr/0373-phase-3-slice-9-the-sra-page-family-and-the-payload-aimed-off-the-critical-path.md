# ADR-0373 — Phase 3 slice 9: the /sra page family, and the payload aimed off the critical path

- **Status:** Accepted
- **Date:** 2026-08-08
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule + per-definition byte-identity),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (the ssi cut whose census measured this
  family; the setup-load oracle sequences), ADR-0372 (the 151-label oracle recipe + the three
  normalizers)
- **Related:** ADR-0307/0308 (the v2-setup recompute branch the oracle re-lights), ADR-0360 (the
  run-reuse cache the export labels ride), ADR-0326 (the `_TS_CAPTION_MARK` mechanism this slice
  descends)

## Decision

**Extract the /sra page family — verbatim — into `web/sra.py` (1,848 lines): 30 names in 22
regions** (`_sra_body`, `_sra_data`, `_ssi_panel`, `_ssi_export_tables`, `_sra_report_blocks`,
the four chart builders, `_correlation_matrix_panel`, `_jcl_panel`, `_sra_explainers`,
`_sra_overrides_table`, the branch/conditional/unified-risk sections, `_file_stored_risks` with
both risk-field constants, the NASA 5x5 constant block, `_OCC_*`, `_CONSEQUENCE_HINT`,
`_SRA_EXPORT`/`_SRA_XLSX_TITLE`). **Two 2-family names DESCEND into `components.py`**
(`_TS_CAPTION_MARK` — the /path, /driving-path and /evolution routes serve the same marker;
`_schedule_risks` — `_margin_risk_data` and five /api routes derive the same ScheduleRisks).
`app.py` **16,384 → 14,597**. `LAYER_ORDER` becomes `… → ssi → mission → sra → app`; the
re-export block lands between offload and ssi (o < sr < ss); the E501 exemption travels.
`_ssi_three_point`, `_risk_events`, `_schedule_branches`, `_schedule_conditionals` stay —
shared route machinery no page owns. Notably `sra.py` imports **nothing from `web.ssi`**: the
panel/data split keeps the run machinery upstream of the routes, not of the page family.

## The re-measure: ADR-0365's prediction, priced

The stale queue said "sra 840; expect ~1,300+ once the measured-out ssi members return". The
re-measured census (ast spans, wc-truth): prefix **847 lines / 13 names**; the behaviour-seeded
closure over `/sra` + `/api/sra` + the sra exports: **32 names / 1,756 lines**, partitioned
30 movers / 1,741 + 2 descents / 15. `_ssi_panel` (235) and `_ssi_export_tables` (248) are here,
exactly as ADR-0365 §2 ruled ("the prefix is a finder, the closure is the definition").
Constants carry their `#:` doc-comment blocks with them (the ast span does not see a comment —
five regions were extended by eye before any byte was moved).

## The oracle — 294 labels, and the payload aimed off the critical path

Rebuilt per the ADR-0372 recipe and grown 151 → **294 labels**: every parameterless GET (60,
pages AND APIs, validation-4xx labels kept — they pin the routes' rejection bodies), both
formats over all 27 parameterless exports, the 8 `{name}` exports on TP4 v5, the established
variants, the `[target-set]`/`[target-cleared]` sequence now re-rendering the FULL GET+export
surface (not a hand-picked ten), and — required for this slice by ADR-0365 — the crafted
**v4/v2 SSI setup-load sequences** with 12 + 4 after-renders (`303` asserted on every POST).
Three normalizers inherited (launch token · whoami pid · `/api/system` values). Double-render
determinism across two separate processes: **0 flapping** — proven before any claim, twice
(the oracle was rebuilt mid-flight, below).

**The first crafted v4 payload was aimed off the critical path and measured two false darks.**
Factors/bcwc/risk/branch on UIDs 12–15 — tasks the TP4 v5 snapshot has COMPLETED (rem = 0):
ADR-0308's own rule made every risk inert, the focus finish never moved, the S-curve collapsed
to one point (`_sra_chart_scurve` returns None below 2), and the OAT sweep was all-zero
(`_sra_chart_tornado` returns None on no positive swing). Both chart builders probed **0 moved**
— and a first stronger-anchor re-probe (title strings instead of colors) still moved 0, which is
what separated *weak anchor* from *dark member*: the code was unreachable, not the mutation
invisible. Re-aimed at the LIVE critical chain (factor on 22, bcwc on 23, override on 24, risk
affecting 22, branch across the real 22→24 FS tie, conditional plans across 24→25, focus =
project finish), both members light: `[v4] DOCX sra` moves for each. *A crafted oracle payload
must be aimed at incomplete, finish-moving work — completed-task UIDs measure the fixture's
history, not the member's reach.*

## Pre-flight probe (32 members, in place in app.py)

| members | labels moved (of 294) |
| --- | --- |
| `_TS_CAPTION_MARK` | 11 — /path, /driving-path, /sra across all session states |
| `_OCC_RANDOM` / `_OCC_EXACT` | 7 each — /sra all states + DOCX sra both states |
| `_ssi_panel`, `_sra_body`, `_sra_explainers`, `_jcl_panel`, `_correlation_matrix_panel`, `_CONSEQUENCE_HINT`, `_SRA_EXPORT`, `_SRA_XLSX_TITLE` | 5 each — /sra in all five render states |
| `_schedule_risks` | 5 — `[v4]` ssi-api/oat/xlsx/docx/registry (the register derivation) |
| `_branch_section`, `_conditional_section`, `_unified_risk_section`, `_sra_data` | 4 each |
| `_ssi_export_tables` | 3 — the XLSX sra exports (bare/target/v4) |
| the six NASA constants, `_sra_matrix_chart`, `_sra_chart_hist`, `_sra_report_blocks` | 2 each — DOCX sra both states |
| `_sra_chart_scurve`, `_sra_chart_tornado` | 1 each — `[v4] DOCX sra` (the re-aim's yield) |
| `_sra_overrides_table` | 1 — `[v4] GET /sra` |
| `_SRA_RISK_PROB_FIELD`, `_SRA_RISK_IMPACT_FIELD`, `_file_stored_risks` | 0 — oracle-dark |

The xlsx/docx export paths diverge cleanly (xlsx → `_ssi_export_tables`, docx →
`_sra_report_blocks` + charts + NASA constants) — the probe sets are structural, not noise.
The three zeros are ADR-0365's SAME stored-fields cluster: no committed fixture file carries
the `SSI SRA` custom fields (the queued stored-SRA-fields MSPDI fixture remains the named gap),
but the cluster is **directly route-covered in Python**:
`test_ssi_grid_from_schedule.py::test_load_from_schedule_seeds_the_register_from_the_files_risk_fields`
builds the carrier schedule in code, POSTs `/sra/load-from-schedule` (303 asserted) and pins the
parsed probability/impact/pair-rule/completed-exclusion — plus the uid152 parity oracles on the
committed reference family.

## Proof

- **Per-region byte-identity: 24/24 IDENTICAL** — asserted inside the cut script, re-verified
  twice more (after `ruff --fix` import surgery, after `ruff format`).
- **Multiset (final tree): 104 added / 8 removed.** Additions: `sra.py`'s preamble + import
  block, the 30-line re-export block + comment, the two descent re-exports, components' banner
  + widened engine import. The 8 removals are all import-shape artifacts — seven parenthesized
  member lines whose names re-land in `sra.py`/`components.py` single-line imports, plus the
  superseded single-name `SSIRiskStat` line. **Zero code lines removed.** The 12 imports the cut
  dropped from `app.py` (`Chart`/`ChartText`/`DocTable`/`Heading`/`Paragraph`, `SRAResult`,
  `ScheduleRisk`, the three `conclusions_*`, `iso_duration_to_minutes`, `field_help_payload`)
  were each mover-only; the dropped-import sweep found **no test reading any of them through
  the app module**.
- **294/294 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in the new locations: 32/32 EXACT** — every member re-mutated in
  `sra.py`/`components.py` with the probe's own anchors moved exactly its pre-flight set
  (the three dark members stayed dark), restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 70 names `sra.py` binds, defined or imported, +
  the descents): **zero hits**, positive-controlled by the standing `app_mod.non_summary`
  projection-memo patch (found 2×).
- **Source-text sweep**: every ≥6-char string literal of all 15 app.py-source-reader test files
  intersected against the moved text, positive-controlled (`sra_grid.js` ∈
  `test_axis_titles`'s literals ∩ `_ssi_panel`). Every hit adjudicated: rendered-page
  assertions (`test_dom_captions`, `test_gantt_find_coverage`, `test_page_memory`,
  `test_r10_resources_contract`), readers whose subject lives in chrome.py/driving.py (already
  repointed by earlier slices), stayer subjects (`_FORECAST_METHOD_COLORS`), or generic words.
  The ONE reader whose subject moved — `test_axis_titles`'s `_TS_CAPTION_MARK` counter — is
  repointed in this same commit: definition asserted in `components.py`, three route insertions
  in `app.py`, the /sra body's one in `sra.py` (the ADR-0349 trap, not tripped).

## Verification

Six mutations, each landed-count-asserted in-script, each run against the WHOLE module (no
`-k`), each exactly ONE named failure with the twins green, each restored from a scratchpad
copy (never `git checkout`) and md5 + anchor-grep verified:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[sra.py]` | 1 / 24 |
| deferred upward import in `_sra_data` | `…imports_downward[sra.py]` | 1 / 24 |
| `"sra.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 24 |
| `"sra.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 24 |
| `"&mdash;"` sentinel planted in `sra.py` | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `sra.py` | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 3–4 are the enumeration guard's **ninth and tenth consecutive live catches**. The
first shape of mutation 2 — the upward import wrapped in a NEW top-level def — drew TWO
failures: the layering test AND the re-export guard (a name `sra.py` defines that `app.py`
does not re-export). That is the contract's tests overlapping defensively, recorded here as a
true positive of the re-export guard against accidental module-level additions; the mutation
was reshaped to the in-body form for the clean single-name proof. A separate harness lesson
rode along: the battery-script patch that reshaped it was itself first applied with an
unanchored heredoc replace that missed SILENTLY — the re-run reproduced the old failure
verbatim. Patch the patcher with the same landed-count discipline as the tree (an exact-match
edit that fails loudly), or the battery measures last hour's script.

## Deliberately NOT done

- The stored-SRA-fields MSPDI fixture (would light the three dark members end-to-end from a
  FILE) stays queued — it serves the parity surface too and deserves its own slice.
- `docs/DESIGN-SYSTEM`/`CLAUDE.md` phase-3 + E501 prose still lag by design (the standing
  doc-drift sweep owns them); `sra.py` DID join pyproject's per-file E501 list.
- `/api/sra/jcl` renders 422 in every oracle state (it requires a confidence parameter); a
  parameterized JCL variant label is future oracle work for the app.py-resident jcl data
  builder — not this family.

## Consequences

- Six page families remain by the re-measured prefix census: forecast 391 · what 289 ·
  portfolio 253 · evm 239 · where 235 · how 214 — each still owes its OWN closure before
  cutting (this slice re-proved why: the closure found 32 where the prefix saw 13).
- The 294-label oracle with the v4/v2 sequences is the widest yet; the v4 payload's
  critical-chain aim is load-bearing for the two chart members and documented in the harness.
- When a future slice pulls `_ssi_three_point` / `_schedule_branches` /
  `_schedule_conditionals`, the sra members that reference their OUTPUTS are already below
  app.py, so those stays can only descend (components) or stay put — never move upward.
