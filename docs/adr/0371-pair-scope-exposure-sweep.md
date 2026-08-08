# ADR-0371 — The ADR-0370 exposure sweep: every version-pair forensic surface runs on the pair scope

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0370 (target anchors /integrity's
pair scope), ADR-0268 (target-as-endpoint scope) · **Drivers:** ADR-0370's "Deliberately NOT
done" queue — `/compare`, `/trend`'s findings roll-up, `/evolution`'s counterfactual and app.py's
other `detect_manipulation` / `compute_path_counterfactual` call sites still received
target-truncated pairs; the operator's scope that session was /integrity, this session closes
the class.

## Context — the same lie class, measured on the remaining surfaces

ADR-0370 separated the Target UID's two meanings for /integrity: single-version metric views
keep the ADR-0268 population truncation; version-PAIR forensics run on the real pair with the
target as measurement anchor only. A caller-by-caller census of every population call site in
`web/app.py` (plus the brief/briefing/narrative feeders) found the truncated pairs still feeding
ten surfaces. On the ADR-0370 control pair (A: Dig 5d→Pour 5d→Roof 1d, Wire 1d→Roof; B removes
Pour→Roof and cuts Dig to 3d; target = Roof, so B's cone is {Wire, Roof}), measured:

| engine (truncated pair) | says | the truth (real pair) |
| --- | --- | --- |
| `detect_manipulation` | **HIGH "2 activities deleted since the prior version"** — fabricated; the real duration cut invisible | MEDIUM removed-logic + MEDIUM shortened-duration; nothing deleted |
| `compute_path_evolution` (unanchored) | entered = Wire, left = Dig+Pour, stayed = Roof | entered = (), left = Roof, stayed = Dig+Pour |
| `compute_path_counterfactual` | **None** (the restored link dangles) | reverts Roof: "logic 1 link(s) restored" |

The fabricated finding is the single worst accusation the tool can make, and it reached the
Diagnostic Brief's HIGH-only questions section verbatim.

## Decision

**Moved wholesale to `_pair_versions()`** (pure pair-forensics surfaces; the reduce-FILTER still
applies, the target never truncates): `/compare` (the `diff_versions` header KPIs, the
manipulation signals, the focus rows) · `/export/{fmt}/compare` · `/evolution` ·
`/api/evolution` · `/export/{fmt}/evolution` · `/export/{fmt}/whatif` ·
`/export/{fmt}/whatif-added` · `/export/{fmt}/mission`'s **path-evolution tables** (its quality
trend stays on the focused scope, the same basis as `/export/{fmt}/trend`).

**Surgical dual-population** (pages mixing per-version series — which keep ADR-0268 focus — with
pair diffs): `/trend` passes `pair_schedules`/`pair_cpms` into `_trend_body` for the pairwise
signal roll-up only; `build_brief` gains `pair_*` populations feeding `_manipulation_questions` +
`_remaining_cut_questions` (both accusation surfaces; the remaining-cut per-UID diff missed cuts
outside the cone); `build_briefing` gains `pair_*` populations feeding section 3.1's
entered/left snapshot, names and citations (`_critical_path`), threaded through
`SessionState.briefing_for` from `/mission`, `/briefing`, `/export/{fmt}/briefing` and
`/api/ai/briefing`. All `pair_*` parameters default to the primary populations, so every
existing call site is unchanged.

`briefing_for`'s memo needs no new key: the pair populations are a pure function of the loaded
files and the reduce-filter, both already discriminated by the scope signature and the
schedule-identity check — a hit can never serve a stale pair.

**Stayed on the focused scope** (per-version values / value series; the focus is the feature):
the trend series, header, `/api/trend` and `/export/{fmt}/trend` · net-finish-impact (a delta of
two per-version values, not a population diff) · driving-path, forecast, evm, performance,
volatility, cei/scurve/curves families · the per-file report (its narrative is built without a
prior — no pair diff exists there).

### Behavior-invariant consistency moves, stated honestly

`/api/evolution` and `/export/{fmt}/whatif-added` compute **anchored** driving-slack chains to
the target; a chain only ever walks the target's ancestors, and the ADR-0268 cone *is* the
ancestor set — chain membership is identical on the cone and the full network. Their moves
change no observable output on the target knob (no test can fail for them); they are made for
one-basis consistency with the page they mirror, and this paragraph is the record of why the
mutation matrix has no row for them.

## Verification

`tests/web/test_pair_scope_exposure_sweep.py` (11): the tri-engine POSITIVE CONTROL above, one
page/export truth pin per moved surface (every web test POSTs `/target` and asserts the 303 —
the ADR-0370 silent-405 trap), and function-tier pins for `build_brief`/`build_briefing` whose
in-test controls assert the truncated output differs. Mutation matrix — every route wiring
proven able to fail with a NARROW, NAMED set (anchored splices, landed-count asserted before
write, tree restored byte-identical, `cmp` + anchor-grep):

| mutation (revert at the caller) | result (whole module, unfiltered) |
| --- | --- |
| /compare route → `_solvable_versions()` | **1 fail by name** (page truth); 10 pass |
| /export/compare → scoped | **1 fail by name**; 10 pass |
| /trend loses the pair kwargs | **1 fail by name**; 10 pass |
| /evolution route → scoped | **1 fail by name** (counterfactual); 10 pass |
| /export/whatif → scoped | **1 fail by name**; 10 pass |
| mission export's evolution tables → scoped | **1 fail by name**; 10 pass |
| /briefing loses the pair kwargs | **1 fail by name** (section 3.1); 10 pass |
| /brief loses the pair kwargs | **1 fail by name** (cone-blind question); 10 pass |

Statics green (ruff whole tree · format · mypy strict 125 · bandit · node per file). Full suite +
parity: see SESSION-LOG (this session). One existing pin re-pointed: ADR-0320's
`test_export_session_focus_applies_the_sessions_own_rule` faithfully recorded the OLD split
(URL focus = full population, session focus = truncated population) — that split *was* the
defect, so the pin now asserts the two spellings produce equal sheet text on the full
population (`test_export_session_focus_matches_the_url_focus`; its failure on the old wiring
in this session's first full-suite run is the able-to-fail evidence). No markup, token or
layout changed — only which populations feed existing panels — so the render evidence is the
measured page/export strings above; the no-target render is byte-stable structurally (with no
target set, `scope_pair` *is* `scope` and the pair cache entries are the ordinary epoch's, per
ADR-0370).

## Consequences

- v1.0.178 → v1.0.179; wheel + nine installers rebuilt after the last code change.
- With a target set, pages that now fetch both populations (`/trend`, `/brief`, `/briefing`,
  `/mission`) cost one extra full-network solve set, cached across requests under the pair
  epoch; with no target set there is no extra solve (identical cache keys).

## Deliberately NOT done (measured, left alone)

- **Period-over-period metric families** (CEI trend / bow-wave, HMI trend, volatility's
  per-UID movement rows) also match UIDs across versions on the focused scope; under a target,
  a task leaving the cone leaves those series. They are metric value series with parity
  oracles — not accusation surfaces — and re-basing their populations would need its own parity
  adjudication, so they stay focused and documented here, exactly like ADR-0370's reduce-FILTER
  caveat (which also stands unchanged).
- The reduce-FILTER pair-diff caveat (ADR-0370) is unchanged: an operator-visible population
  choice applied everywhere by design.
