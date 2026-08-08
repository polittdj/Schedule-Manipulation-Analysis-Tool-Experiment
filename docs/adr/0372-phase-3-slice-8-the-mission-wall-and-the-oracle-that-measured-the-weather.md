# ADR-0372 — Phase 3 slice 8: the mission wall, and the oracle that measured the weather

- **Status:** Accepted
- **Date:** 2026-08-08
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule + per-definition byte-identity),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0364/0365 (the re-measure discipline; the
  ran-signature rule)
- **Related:** ADR-0262 (the wall's degrade notes), ADR-0268/0371 (the export's pair scope),
  ADR-0349 (the source-text trap this slice re-checked and did not trip)

## Decision

**Extract the Mission Control wall body — verbatim — into `web/mission.py` (329 lines):**
`_mission_body`, the whole family. `app.py` **16,685 → 16,384**. `LAYER_ORDER` becomes
`… → trend → ssi → mission → app`; the re-export lands mid-list (margin < **mission** <
offload < ssi). The E501 exemption travels with the tiles' HTML f-strings and hover-hint
one-liners, exactly as it did for chrome/driving/evolution/integrity/margin/trend.

## The re-measure: the first census the closure fully confirms

The queue's numbers were stale (ADR-0365 §Consequences predicted it), so the census was
re-measured before cutting (`ast`-derived spans, wc-truth): `mission` **304 =
`_mission_body` alone** — the prefix census and the closure AGREE exactly, the first slice
where they do. The behaviour-seeded closure over `/mission` + `/export/{fmt}/mission`:

1. **Move set: 1 name / 304 lines.** `_mission_body`'s sole external referrer is the
   `/mission` route — a `create_app` closure, which imports downward and stays put.
2. **Descents: none.** The body's only externals are `_e` (already in `web/chrome.py`,
   ADR-0349), `Schedule` (model) and `ExecutiveBriefing` (ai) — the smallest closure of
   any slice so far.
3. **The export route contributes NO movers**: `/export/{fmt}/mission` builds its tables
   from engine functions (`trend_tables`, `path_evolution_tables`, the ADR-0371 pair
   scope) and the multi-family stays (`_bad_format` / `_solvable_versions` /
   `_pair_versions` / `_export_response`).

The same re-measure re-prices the queue (prefix census; each family still owes its own
closure before cutting): `sra` **840** by prefix — and the closure will pull
`_ssi_panel` (235) + `_ssi_export_tables` (248) + `_file_stored_risks` + both risk-field
constants from the measured-out ssi census (ADR-0365 §2), so expect ~1,300+ · `forecast`
**391** · `what` **289** · `portfolio` **253** · `evm` **239** · `where` **235** ·
`how` **214** (the stale "290" is superseded).

## The oracle — 151 labels, and the label that measured the weather

The route oracle was rebuilt and grown 96 → **151 labels**: every parameterless GET route
(pages AND APIs), both export formats over all 25 parameterless exports, eight
`{name}`-parameterized exports on TP4 v5, the established variant set (three `/evolution`
variants, `/trend?target=17`, `[ssi-api]` seeded-MC, `[ssi-grid]`, `[ssi-save]`), and a
`[target-set]` sequence that POSTs a REAL TP4 UID (17 — never 0, `_parse_uid` maps 0 to
"clear") and re-renders the ten target-sensitive pages plus seven exports before clearing.
Double-render determinism was proven across two separate processes **before** any number
was quoted; three normalizers earned their place by evidence:

| normalizer | evidence |
| --- | --- |
| launch token `{hex16}.{wipe_gen}` | ADR-0365's 48-label flap, inherited |
| `/api/whoami`'s `"pid"` | the server's own process id — per-process by design |
| `/api/system` VALUES (shape kept) | the weather, below |

**The falsification run moved FOUR labels where the pre-flight said three.** The fourth
was `GET /api/system` — and the payload diff showed exactly one key: `memory.percent`
4.6 → 4.7. The endpoint reports LIVE host telemetry; it had been byte-stable across three
runs by luck (1-dp rounding) and crossed the boundary during the falsification render. A
mutation in `mission.py` cannot change the machine's memory — this is the env-defect
masquerade (the standing trap), caught by diffing the payload instead of believing the
label. Values normalized (shape kept), all four runs re-adjudicated from their SAVED
bodies: determinism 0 flapping · pristine-vs-cut **151/151 byte-identical** · falsify
**exactly** the pre-flight set. *Stability observed n times is not determinism — an
oracle label serving live telemetry must be normalized up front, and every unexpected
mover adjudicated by payload diff before a dependency is believed.*

## Pre-flight probe

| member | labels moved (of 151) |
| --- | ---: |
| `_mission_body` | 3 — `GET /mission`, `[target-set]`, `[target-cleared]` |

The `/export/{fmt}/mission` labels did NOT move — the export never calls the body. No
oracle-dark members this slice (the first with none): the single mover is render-proven
in all three session states.

## Proof

- **Per-definition byte-identity vs the pre-move source: 1/1 IDENTICAL** (asserted inside
  the cut script, before anything else ran).
- **Multiset: 28 added / 0 removed** — the additions are `mission.py`'s preamble + import
  block and `app.py`'s 4-line re-export block; the first slice with ZERO removals (no
  import narrowed — all three of the body's externals remain used by `app.py`'s own code).
- **151/151 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in the new location**: the span-scoped `id=missionGrid` anchor mutation in
  `mission.py` moved exactly its pre-flight set; restore md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 4 names `mission.py` binds:
  `_mission_body`, `_e`, `Schedule`, `ExecutiveBriefing`): **zero hits**, with the
  standing `app_mod.non_summary` projection-memo patch re-run as the live positive
  control (the pattern finds it; the four names' emptiness is therefore meaningful).
- **Source-text sweep**: every string literal (≥6 chars) of all 12 `app.py`-source-reader
  test files checked against `_mission_body`'s exact text, positive-controlled
  (`mission.js` ∈ `test_axis_titles`'s literals ∩ the body). Every hit adjudicated: the
  `EXEMPT`/`NO_SVG_AXES` static-JS lists, rendered-page assertions, or generic words —
  no reader greps `app.py` for text that moved. `test_axis_titles`'s `app.py` read counts
  `_TS_CAPTION_MARK`, which never appears in the body.
- **Dropped-import sweep**: the multiset's 0-removed IS the proof — `app.py` dropped
  nothing.

## Verification

Six mutations, each landed-count-asserted in-script, each run against the WHOLE module
(no `-k`), each producing exactly ONE named failure with the twins green, each restored
from a scratchpad copy (never `git checkout`) and md5 + anchor-grep verified:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[mission.py]` | 1 / 22 |
| deferred upward import in `_mission_body` | `…imports_downward[mission.py]` | 1 / 22 |
| `"mission.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 22 |
| `"mission.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 22 |
| `"&mdash;"` sentinel planted in `mission.py` | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `mission.py` | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 5–6 are the true-positive proof that the two widened guards actually READ the
new module — without this slice's tuple edits both sentinels would have passed silently
(the ADR-0350 near-miss, now seventh and eighth consecutive live catches for the
enumeration guard).

## Deliberately NOT done

- The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle:
  they exist to execute `_apply_ssi_setup`'s branch families, which this cut does not
  touch; the `[ssi-api]`/`[ssi-grid]`/`[ssi-save]` labels still render the ssi module's
  main lines. The sequences remain named in ADR-0365 for the /sra slice, whose closure
  WILL touch that machinery.
- `CLAUDE.md`'s stale phase-3 ("still queued") and single-E501 lines stay queued under
  the standing doc-drift sweep — not silently patched here.

## Consequences

- Seven page families remain, re-priced above; each still owes closure-before-cut, the
  span-scoped probe, and this battery. When `sra` is cut, its descents are already at the
  right layer (ADR-0365) and the slice-7 setup-load oracle sequences must return.
- The oracle recipe now carries three normalizers; any future label that serves live
  system state joins `/api/system` under value-normalization BEFORE its first
  byte-identity claim.
