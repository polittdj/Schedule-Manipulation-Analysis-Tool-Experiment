# ADR-0365 — Phase 3 slice 7: the SSI run machinery, and the census flagship that left the family

- **Status:** Accepted
- **Date:** 2026-08-07
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule + per-definition byte-identity),
  ADR-0352 (the pre-flight probe), ADR-0363/0364 (widen-the-oracle; the re-measure discipline)
- **Related:** ADR-0356 (the stale-setup root cause this machinery exists to prevent), ADR-0307/0308
  (the v2-setup migration branch), ADR-0313 (the bounded setup read), ADR-0360 (the run-reuse cache)

## Decision

**Extract the SSI run machinery — verbatim — into `web/ssi.py` (644 lines):** the
`/api/sra/ssi` dataset builder (`_ssi_data`), the SSI factor-grid rows (`_ssi_grid_rows`),
and the setup Save/Load cluster (`_SSI_SETUP_VERSION`, `_ssi_setup_dict`, `_apply_ssi_setup`,
`_setup_vintage_warning`, `_schedule_sra_fingerprint`, `_file_stored_sra_inputs`, and the
three stored-field-name constants). **Three 2-family names DESCEND into `components.py`**
(`_REMAIN_DAYS_DP`, `_affected_avg_remaining_days`, `_ssi_matrix_counts`). `app.py`
**17,197 → 16,581**. `LAYER_ORDER` becomes `… → margin → trend → ssi → app`; note `web.ssi`
sorts BEFORE `web.state` in the import block (s-s-i < s-t-a), so the re-export block lands
mid-list again, unlike trend's end-of-section position.

## The re-measure: the census's flagship member is not in the family

The stale "ssi 335" census was `_ssi_panel` (235) + `_ssi_data` (102) — the strict
body/panel/data pattern. The behaviour-seeded closure over the SSI routes
(`/sra/ssi-run-config`, `/sra/factor-table`, `/sra/factor`, `/sra/auto-calc`,
`/api/sra/ssi`, `/api/sra/grid`, `/sra/grid`, `/sra/ssi/save`, `/sra/ssi/load`) gives
**15 names / 611 lines, partitioned three ways**:

1. **The move set: 11 names / 576 lines** — every external referrer is a `create_app`
   route, which imports downward and stays put.
2. **Three descents / 34 lines** — each needed by a mover AND by an sra-family member that
   stays (`_apply_ssi_setup` vs `_unified_risk_section`/`_import_risk_register`;
   `_ssi_data` vs `_sra_matrix_chart`/`_ssi_export_tables`). ADR-0351's rule, fourth
   consecutive application.
3. **`_ssi_panel` (235) is NOT in the family.** Its sole referrer is `_sra_body` — it is
   /sra page family and moves when that family does. Same verdict for
   `_ssi_export_tables` (248; `_sra_report_blocks` + the sra export routes). The
   prefix-census put the panel IN the family it names; the closure puts it out. This is
   the strongest case yet for "the prefix is a finder, the closure is the definition."
4. **Stays:** `_ssi_three_point` (7 route families), `_correlation_spec` (6),
   `_schedule_risks`/`_schedule_branches`/`_schedule_conditionals` (multi-handler),
   `_MAX_SETUP_BYTES` (handler-only, and one of the three sibling upload caps),
   `_file_stored_risks` + the two risk-field constants (sra-family).

## The pre-flight probe — and an oracle grown around a seeded Monte-Carlo

The 80-route oracle grew to **96 labels**: the established set (evolution variants,
`/trend?target=3`, margin band POST + margin/trend exports, `/compare [target-set]`) plus
this slice's additions — the four sra exports + two templates, bare `[ssi-api]` (the MC is
seeded: `SRAConfig.seed=12345`, per-iteration `random.Random(seed+i)`, so
`/api/sra/ssi?iterations=300` is byte-stable), `[ssi-grid]`, `[ssi-save]`, a **crafted v4
setup load** (exact_overall + LHS + correlation + a days-only risk + a branch + a
conditional + droppable unknown UIDs) with four after-renders, and a **crafted v2 setup
load** lighting the ADR-0307/0308 stale-factor-derived recompute branch. Double-render
determinism was proven across two separate processes before any number was quoted (the
launch token is `{hex16}.{wipe_gen}` — a hex-only normalizer misses it, and 48 labels flap
until it is right).

| member | routes moved (of 96) |
| --- | ---: |
| `_apply_ssi_setup` | 5 — the whole v4 chain incl. the post-load export |
| `_ssi_matrix_counts` (descent) | 5 — **both sides**: `[ssi-api]` via the mover `_ssi_data`, bare `/export/{xlsx,docx}/sra` via the stayer `_ssi_export_tables` |
| `_schedule_sra_fingerprint`, `_SSI_SETUP_VERSION`, `_ssi_setup_dict` | 3 — every save render |
| `_ssi_grid_rows` | 3 — every grid render |
| `_affected_avg_remaining_days` (descent) | 3 — the v4 days-only-risk derive |
| `_ssi_data` | 2 — both api renders |
| `_setup_vintage_warning` | 2 — both load paths (the early-return anchor) |
| `_SRA_FACTOR_FIELD` / `_SRA_BC_FIELD` / `_SRA_WC_FIELD` / `_file_stored_sra_inputs` | 0 |
| `_REMAIN_DAYS_DP` (descent) | 0 |

The five zeros are stated, not hidden: the stored-fields cluster is **oracle-dark** (no
fixture in the corpus carries `SRA Risk Ranking Factors` / Best-Worst custom fields) but
**directly unit-covered** (`test_ssi_grid_from_schedule.py` builds the carrier schedule in
Python and exercises the parse, the fingerprint, and the vintage warning). A committed
MSPDI fixture carrying stored SRA fields would light them end-to-end — named for the /sra
slice, whose members (`_file_stored_risks`, the warning's text branch) need the same
fixture. `_REMAIN_DAYS_DP`'s 6→2dp mutation is value-invisible on whole-day fixtures (the
constant exists for sub-day tasks, audit M5); its consumption path is proven by
`_affected_avg_remaining_days`'s 3 moves (the reading line executes) and the dp
relationship is unit-pinned (`test_sra_risks.py`).

## Proof

- **Per-definition byte-identity vs the pre-move source: 14/14 IDENTICAL** (11 in
  `ssi.py` — `_apply_ssi_setup` 12,639 B, `_ssi_data` 5,034 B, `_ssi_setup_dict` 3,526 B,
  … — and 3 in `components.py`). Load-bearing for the five probe-zero members.
- **Multiset: 69 added / 1 removed.** Additions: the `ssi.py` preamble + import block, the
  two re-export insertions (11 ssi lines + 3 descent lines + comments), components'
  `SSIRiskStat` import. The single removal is app.py's parenthesized `SSIRiskStat,` member
  (its last consumer descended), re-added as components' own import; `import hashlib`
  migrated app→ssi invisibly to the multiset.
- **96/96 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in BOTH new locations**: all nine render-visible members mutated in
  `ssi.py`/`components.py` with the probe's own anchors; each moved EXACTLY its
  pre-flight set; restores md5-verified from post-cut scratchpad copies.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 34 names `ssi.py` binds, imported or
  defined): **one hit** — `test_manifest_projection_memo` patches `app_mod.non_summary`,
  which doubles as the sweep's live positive control. Cleared by the ADR-0364
  verification, unchanged: the spied path is `/api/dashboard`'s projection memo
  (app/state), never crosses a moved member; `app.py` still binds `non_summary` for its
  own callers; `ssi.py`'s own import is deliberately outside that patch's reach.
- **Source-text sweep:** zero ssi anchors across all 13 app.py-source readers (self-test:
  `drilldown.js` ×3 found in its own guard). Every reader's subject stays put.
- **Attribute-read sweep for the dropped import** (`hashlib`, app.py's only drop): no test
  reads it through the app module (machinery control: the same shape flags
  `app_mod.non_summary` live).

## Verification

Five mutations, each verified-landed, each restored from a scratchpad copy (never
`git checkout`), each md5-verified, each re-run green:

1. Re-export of `_ssi_data` deleted from `app.py` → contract test fails naming it.
2. A **deferred** `from schedule_forensics.web import app` inside `_ssi_grid_rows` → the
   layering test fails for `ssi.py`.
3. `"ssi.py"` dropped from `test_bar_drill`'s module tuple → the enumeration guard fails
   (sixth consecutive live catch).
4. A `"&mdash;"` sentinel planted in `ssi.py` → the widened em-dash guard fails.
5. A second `drilldown.js` include planted in `ssi.py` → the widened double-load guard
   fails.

**One false red was itself caught.** The first run of mutations 4–5 targeted GUESSED test
ids; pytest exited non-zero having collected NOTHING, which reads as "RED" to an exit-code
check. The harness's ran-signature assertion (the failure summary must name the test)
exposed it, and the re-run against the real ids (`test_no_mdash_entity_sentinel_values…`,
`test_drilldown_runtime_is_loaded_globally…`) produced genuine `1 failed` reds and
green-after-restore. A non-zero pytest exit is not a failing test — collection errors exit
non-zero too. Assert the test RAN.

## Consequences

- Eight page families remain by the stale census: `mission` 304 · `how` 290 · `sra` 264 ·
  `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208 · `forecast` 204 — re-measure
  before cutting, and expect the sra number to be off by ~700+: the panel (235), the
  export tables (248), `_file_stored_risks` and both risk-field constants are measured
  /sra-family now, waiting there.
- The ssi sequences (`[ssi-api]`, the v4/v2 loads, the sra exports) stay in the harness —
  they are the only execution proof for the setup machinery's branch families.
- A committed MSPDI fixture with stored SRA fields is the named oracle gap; it unlocks
  end-to-end proof for the stored-fields cluster AND the /sra slice's members.
- When the **/sra** family is cut, the descents are already at the right layer.
