# ADR-0358 — Phase 3 slice 4: the integrity family, and the slice where the render diff finally earned its keep

- **Status:** Accepted
- **Date:** 2026-08-06
- **Continues:** ADR-0350 (the shared kernel), ADR-0351 (driving), ADR-0352 (evolution — the
  pre-flight coverage check this slice ran to the letter)
- **Related:** ADR-0297 (the monkeypatch trap), ADR-0349 (the source-text trap)

## Decision

**Extract the /integrity page family — verbatim — into `web/integrity.py` (446 lines):**
`_integrity_header` (the Chapter-02 beat header) and `_integrity_body` (the A/B pair picker, the
findings table + drill, the per-change effects panel, the counterfactual panel). `app.py`
**18,311 → 17,910** (−401 net: −406 moved lines and their blanks, +5 re-export block/comment,
−1 import `ruff --fix` dropped, +1 separator). `LAYER_ORDER` becomes `state → chrome →
components → driving → evolution → integrity → app`.

**The closure IS the prefix pair, and that was measured, not assumed.** Seeding by behaviour
(the `/integrity` route's body builder) and walking the AST transitive closure over `app.py`'s
274 top-level symbols gives exactly **2 names / 402 lines** — `_integrity_header` +
`_integrity_body` — with `create_app` as the sole external referrer. Both serving routes
(`/integrity`, `/export/{fmt}/integrity`) otherwise use only shared machinery
(`_solvable_versions`, `_page`, `_export_response`). Nothing descends into `components.py` this
slice — the first cut since the kernel came out where the pair-descent rule had nothing to do.
One import line left `app.py` with the code: `ruff --fix` dropped
`engine.change_effects import ChangeEffect, compute_change_effects` because `_integrity_body`
was its last consumer; the same line lives verbatim in the new module's preamble, so the
non-blank multiset shows it in NEITHER direction.

## The pre-flight coverage probe — first slice where the render diff covers the whole family

ADR-0351's family rendered on **no** fixture (0/60 moved); ADR-0352's counterfactual pair
rendered on none (two members at 0). This family is the opposite, and it was measured BEFORE
the cut, span-scoped per ADR-0352's corrected method:

| member | routes moved (of 79) |
| --- | ---: |
| `_integrity_header` (54 ln) | 6 — every /integrity page, both oracles |
| `_integrity_body` (348 ln) | 6 — the same six |

The oracle was widened for the purpose: **Oracle A** is the Project2/Project5 golden pair
(74 routes incl. the three ADR-0352 /evolution variants); **Oracle B** loads the five-version
`TP4_DataCenter` fixture family and renders `/integrity` five ways — default, `?a=0&b=4`,
`?a=3&b=1` (the base>cur order-normalisation branch), `?a=9&b=99` (the out-of-range re-pick
guard), and `?file=` (the route-side back-compat). Between the two oracles the family renders:
the findings table + drill + `vb-watch` band (A), the empty-findings `vb-on-track` branch, the
`vb-at-risk` band, the n>2 `<select>` picker, and the change-effects + counterfactual panels
(B). Determinism was verified by double-render before anything was trusted (79/79 stable;
`/api/whoami`'s launch token needed the ADR-0350 normalisation, found exactly as phase 3 slice 1
found it).

**The one named gap:** the `artifact-cluster` collapsible — the MS Project
"reschedule uncompleted work" SNET-at-data-date branch inside the effects panel — renders on
no oracle input. Its guard is the per-definition byte-identity below, same as ADR-0352's
counterfactual pair. A fixture that stamps SNET constraints at the data date would close it.

## Proof

- **Per-definition byte-identity vs the pre-move source: 2/2 IDENTICAL** (`_integrity_header`
  2,654 bytes, `_integrity_body` 19,996 bytes), AST-extracted from both trees.
- **Verbatim at file level.** Non-blank multiset over pristine `app.py` vs `app.py +
  integrity.py`: **38 added, 0 removed** — entirely the new module's preamble (docstring +
  imports) and the 5-line re-export block.
- **79/79 routes byte-identical** across both oracles, pristine tree vs cut tree.
- **The oracle was falsified, not assumed.** One character changed inside the moved
  `_integrity_body` (`integrity-file` → `integrity-fyle`, a same-length non-superstring —
  ADR-0351's substring lesson applied on the first try) moves **exactly the six** /integrity
  pages and nothing else. The probe harness itself asserts the ORIGINAL anchor is absent after
  every mutation; that assert caught a suffixed `page-takeawayQ` probe mid-session, which is
  ADR-0351's trap firing in the probe's own tooling rather than in a guard.

## The sweeps — all three ran, all three came back empty, and that is the news

- **Monkeypatch sweep** over every name `integrity.py` BINDS (18: 2 defined + 16 imported),
  alias-aware and string-form-aware: **no test patches or reads any of them through an
  app-module handle.** First slice with zero repointing (driving had 3, evolution had 4+2).
- **Source-text sweep** (`"app.py"` literals + `__file__` reads + `getsource`): every reader's
  subject stayed put — `_TS_CAPTION_MARK` still counts 5 in `app.py` (the four hosting pages
  do not include /integrity), `test_installers`' shutdown route stayed, the five
  integrity-named test files assert on RENDERED pages, which re-exports keep whole.
- **Attribute-read sweep** for the two names `app.py` no longer binds (`ChangeEffect`,
  `compute_change_effects`): no test reads either through `web.app`.

An empty sweep is only evidence if the sweep can find things: the same sweep code, pointed at
the pre-ADR-0352 tree's names, is what found evolution's four — and mutation 1 below proves the
contract half of the harness still fails loudly here.

## Verification

Five mutations, each verified-landed by re-reading the file, each restored from a scratchpad
copy (never `git checkout`), each re-run green after restore:

1. Re-export of `_integrity_body` deleted from `app.py` → contract test fails naming it.
2. A **deferred** `from schedule_forensics.web import app` inside `_integrity_header` → the
   layering test fails for `integrity.py` (the module-level spelling detonates on its own; the
   deferred form is the one worth guarding).
3. `"integrity.py"` dropped from `test_bar_drill`'s module tuple → the enumeration guard fails.
4. A `"&mdash;"` sentinel planted in `integrity.py` → the widened em-dash guard fails — the
   widening actually reaches the new module.
5. A second `drilldown.js` include planted in `integrity.py` → the widened double-load guard
   fails, likewise.

## Absorbed in passing: the operator committed the ADR-0357 oracle, and the census guard caught it

The full gate surfaced four `test_intake_manifest` failures that predate this slice: main's
`d0b703e` ("Add files via upload", 2026-08-06 13:06) added
**`00_REFERENCE_INTAKE/mpp/24Hour Calendar.mpp`** (655,872 B) — the 1440-boundary oracle
ADR-0357 recorded as "NOT committed (operator's call)"; the operator has since exercised that
call via the GitHub web UI, which bypasses the manifest ritual. The guard did precisely its
ADR-0347 job: any intake change lands there first. Absorption: the file classifies
`ole2-project` with **no** extension↔content mismatch (verified by running the classifier, not
assumed), `docs/INTAKE-MANIFEST.md` regenerated (407 files / 21 `ole2-project` / mismatches
still 99), the `len(mpp) == 20` pin consciously moved to 21 with the provenance in its
docstring, and CLAUDE.md's census sentence updated. These pins were shown able to fail in the
strongest form available — they were observed red before the fix.

## Consequences

- Eleven page families remain: `margin` 379 · `trend` 348 · `ssi` 335 · `mission` 304 · `how`
  290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208 · `forecast` 204.
  Those line counts are the ADR-0350 census, now three slices old — re-measure the closure
  before trusting any of them as a cut plan.
- The slice recipe is now stable across three consecutive page cuts: behaviour-seeded closure →
  span-scoped pre-flight probe → verbatim cut + `X as X` re-exports → contract/guard widening →
  the three sweeps → per-definition + multiset + falsified render diff → the five mutations.
- Oracle B (the TP4 five-version /integrity load) is worth keeping in the render harness: it is
  the only current fixture load that renders an n>2 version picker and both non-empty verdict
  bands on this page.
