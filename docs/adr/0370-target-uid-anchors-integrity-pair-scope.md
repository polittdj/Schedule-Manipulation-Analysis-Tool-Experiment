# ADR-0370 — The Target UID anchors /integrity's measurement; it no longer truncates the pair

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0268 (target-as-endpoint scope),
ADR-0358 (integrity family), ADR-0369 (integrity disclosure) · **Drivers:** operator report
2026-08-08 — "When you select a target UID it is not correctly calculating the change effects if
reversed to that UID and telling me what the effect would have been to that target UID correctly.
Find the root cause and fix the issue." — plus the same message's detail asks (durations shown
was→now with days removed, logic changes shown visually with specifics, the underlying change
data exportable).

## Context — the root cause, confirmed then demonstrated

Setting a session Target UID makes `SessionState.scope()` truncate EVERY version to
`subschedule_to_target(sch, target)` — the target plus its transitive predecessors **under that
version's own logic** (`path_trace.py`). `/integrity` (via `_solvable_versions`) then diffed two
DIFFERENTLY-truncated cones as if they were the files. The Target UID has two meanings — the
ADR-0268 population cut for single-version metric views, and the measurement anchor
`compute_change_effects(..., target_uid=)` was designed around — and on /integrity both landed
at once, with the cut derived from the very logic network the diffed changes rewire.

Three distinct lies follow, all demonstrated by
`tests/web/test_integrity_target_scope.py::test_truncated_pair_fabricates_and_zeroes_the_control`
on a 4-task pair (Dig 5d → Pour 5d → Roof 1d, Wire 1d → Roof; comparison removes Pour→Roof and
cuts Dig to 3d; target = Roof):

| # | lie | mechanism | control measurement |
| --- | --- | --- | --- |
| 1 | false "no effect" | restoring the genuinely-removed link dangles — its predecessor left the comparison cone and `cpm.py` keeps only edges with BOTH endpoints (cpm.py:968-972) | true **+7 wd** on the target reads **0** |
| 2 | fabricated change | `diff.py` compares populations; a link present in BOTH real files reads "removed" when only cone membership differs | `restore removed FS link 1→2` appears — the file never lost it |
| 3 | missed change | an edit on a task outside the comparison cone is invisible (`cur_by_id.get(uid)` misses) | the Dig duration cut produces **no row** |

The same truncated pairs fed `detect_manipulation` (the findings table), the counterfactual
panel (`path_counterfactual.py` restores prior links only when both endpoints exist in the
current set — starved identically), `/export/{fmt}/integrity`, and both Ask-the-AI
`manipulation_forensics_facts` call sites.

**Why every gate stayed green:** the only "target set" /integrity tests called `GET /target` —
a POST-only route. The silent 405 left the target unset, so the "+21 wd" golden pin rode the
NO-target path for its whole life (UID 155 happens to be the auto-chosen last-critical task).
This was the handoff's queued "3 web tests calling GET /target" item; the operator found in
production what the suite structurally could not see.

## Decision

Separate the two meanings:

- **Single-version metric views** keep the ADR-0268 semantics unchanged — the target truncates
  the population to its driving sub-network (`scope()`).
- **Version-PAIR forensics** (/integrity's findings + per-change effects + counterfactual, its
  export, the AI manipulation facts) run on `SessionState.scope_pair()` — the active reduce-
  FILTER still applies; the target NEVER truncates. The target reaches the engines only as the
  measurement anchor (`target_uid=`).

Machinery: `scope_pair` (filter-only twin of `scope`, own `_pair_scoped` memo cleared wherever
`_scoped` is), `_scope_signature(include_target=False)` (the PAIR epoch — byte-identical to the
full signature whenever no target is set, so the pair cache entries ARE the ordinary epoch's,
and setting a target re-serves the resident full-network solves instead of re-solving),
`cpm_pair_for` (the ADR-0263 one-lock-window + ADR-0281 stripe single-flight discipline,
verbatim), and app.py's `_pair_versions()` used by `/integrity`, `/export/{fmt}/integrity`, and
both `manipulation_forensics_facts` call sites.

### The operator's detail asks (same session)

- `ChangeEffect` carries structured before→after fields — `link_type`, `lag_minutes`,
  `prior/current_duration_minutes`, `prior/current_constraint`, `percent_complete` — computed,
  never persisted (SCHEMA stays 2.11.0), every field defaulted so existing constructions are
  untouched.
- The /integrity effects tables gain a **"Was → is now"** column ("was 5 wd → now 3 wd (-2 wd
  removed; 0% complete)"); `_shortened_durations` names each cut (UID, name, was→now wd, wd
  removed, % complete; first 6 verbatim + counted remainder — the ADR-0369 magnitude shape);
  `_deleted_logic` / `_added_logic` name their links ("Removed: FS 2→3", lag rendered whole-day
  bare / sub-day fractional per ADR-0366).
- A new **"Logic changes — before → after"** panel draws every removed/added relationship
  predecessor —TYPE lag—▶ successor with UIDs AND names, struck-red (removed in B) / green
  (added in B), plus the measured revert-effect chip — built from the SAME `ChangeEffect` rows
  as the table (one truth, never a second diff). Tokens-only CSS (`.logic-*`, all ten tokens
  present in all four themes), measured by a 4-theme computed-style chromium test.
- `/export/{fmt}/integrity?a=&b=` adds **"Change ledger"** (kind, label, was/now/delta/%
  complete, effects in wd AND exact working minutes, artifact flag, citations, the aggregate
  row, every skipped revert NAMED) and **"Logic changes"** sheets; a legacy call without a/b
  keeps the findings-only shape byte-for-byte. All three /integrity panels' ⤓ EXCEL target the
  pair-pinned URL.

## Verification

New guards: `tests/web/test_integrity_target_scope.py` (10 tests, including the truncated-pair
POSITIVE CONTROL above and a pair whose target/project effects differ — link +7/+1 wd, duration
0/+2 wd, aggregate +9/+3 wd — so a measurement made on the wrong network cannot coincide) and
`tests/web/test_integrity_logic_diagram_chromium.py` (4-theme computed-style measurement,
skip-gated like the act3 suite). Mutation matrix — every guard proven able to fail with a
NARROW, NAMED set and green twins, tree restored byte-identical from scratchpad copies (cmp ×5):

| mutation (at the caller) | landed-proof | result (whole module, unfiltered) |
| --- | --- | --- |
| /integrity route → `_solvable_versions()` | grep shows the old call restored | **3 fail by name** (page truth · was→now · diagram); 7 pass |
| `cpm_pair_for` → full signature + `scope()` | 0 `include_target=False` call sites left | **5 fail by name** (state mechanism + all four riding surfaces) |
| `_shortened_durations` detail → generic | needle-assert | **1 fail by name** |
| removed-link call site loses `link_type` | needle-assert | **3 fail by name** |

The GET→POST repairs make `test_integrity_two_file_picker_compares_the_chosen_pair` a REAL
target-set probe (the +21 wd pin holds with 155 explicitly set, measured on the raw pair) and
assert the 303 so a silently-failing setup can never again green the pin; the summary-target
test derives a real ≥1 summary UID (`_parse_uid` maps 0 → "clear" by design) and asserts the
ADR-0369 banner. Renders verified in chromium (4-theme probe green; console + daylight
screenshots read correctly, including the counterfactual line "Target UID 3 (Roof): would have
finished 2026-01-19 instead of 2026-01-08").

## Consequences

- v1.0.177 → v1.0.178; wheel + nine installers rebuilt after the last code change.
- `integrity.py`'s new names are re-exported by `web.app` per the monolith-split contract.
- The pair epoch shares cache entries with the ordinary epoch whenever no target is set —
  no second cache, no cold-start cost, and the no-target /integrity render is byte-stable
  (golden pins "+21 wd" / "33 of 33 have no effect" hold unchanged).

## Deliberately NOT done (measured, left alone)

- `/compare`, `/trend`'s findings roll-up (web/trend.py:162), `/evolution`'s counterfactual
  (evolution.py:505) and app.py's other `detect_manipulation` / `compute_path_counterfactual`
  call sites still receive target-truncated pairs — the same exposure class, queued; the
  operator's scope this session was /integrity and its effects/AI surfaces.
- The reduce-FILTER can in principle fabricate pair-diffs the same way (a task whose filtered
  field value changes between versions leaves the population). The filter is an operator-visible
  population choice applied everywhere by design (ADR-0104/0261), so it is documented here as a
  known caveat rather than silently changed.
