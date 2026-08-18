# ADR-0421 — Ask-the-AI silently lost the engine's driving-path facts under a filter

**Status:** Accepted · **Date:** 2026-08-18 · **Closes:** `AI-DRIVE-01` (audit 2026-08-16, the
never-audited **AI figure-gates** dimension) · **Extends:** ADR-0263, ADR-0417, ADR-0420 ·
**Ships:** `web/app.py`

## Context

`ai/driving_facts.py` exists for one reason, stated in its own module docstring: the local 8B
model "keeps getting *what is the driving path to UID X?* wrong, because multi-hop path + slack
traversal over hundreds of activities is exactly what a small LLM is unreliable at". So the engine
computes the answer — SSI-parity-validated, ADR-0011 — and injects it as **cited** facts that the
model may only narrate.

ADR-0420 closed eight sites where a scoped `_Analysis.cpm` was paired with the RAW session
schedule. Its census enumerated route functions that read a raw population directly. Two calls
launder the raw population through a **function argument** instead, so that census could not see
them, and they sit one line below ADR-0420's own fix:

- `/api/ask/{name}` — `driving_path_facts(sch, st.analysis_for(name, sch).cpm, text)`
- `/api/ask` (the **single-file** branch only) — the same shape

## What actually happens — and it is not what the row predicted

The hypothesis on entering was "the AI will answer about an activity the analyst filtered away".
That was **refuted**: a filtered-out UID is absent from the scoped CPM, so nothing is emitted for
it either way. The real behaviour is worse and silent.

`compute_driving_slack` traverses the RAW network while reading timings from a CPM solved on the
SCOPED one. The first raw-only task it reaches raises `KeyError`, and
`driving_path_summary`'s `except (KeyError, ValueError)` swallows it and returns `()`. So with any
active filter, **every** engine driving-path fact disappears — for in-scope activities too — and
the route still answers `200`.

The model is then left doing the traversal the module exists to prevent, and the figure gate can
only make the loss visible, never repair it: strict discards the whole answer, annotate flags the
model's counts as AI-derived. The operator loses the engine's exact answer with no notice.

Measured on the shipped example (9 activities, 1 milestone) under an `Activity Type: Normal`
reduce filter (9 → 8), asking for the driving path to UID 5 — which **stays in scope**:

| session | `/api/ask/{name}` | `/api/ask` |
| --- | --- | --- |
| unfiltered, 1 file | 2 driving facts | 2 driving facts |
| **filtered**, 1 file | **0** | **0** |
| unfiltered, 2 files | 2 driving facts | 2 driving facts |
| **filtered**, 2 files | **0** | **2** |

## The product supplied its own oracle

The last row is the finding. `/api/driving-path` — the deterministic one-click answer — already
pairs `a.scoped` with `a.cpm` and says so in a comment citing ADR-0263; `/api/ask`'s multi-version
branch already goes through `_solvable_versions` → `cpm_scoped_for`. So with two files loaded and
a filter on, **the same session answered the same question with contradictory evidence depending
on which panel was used**. That is an independent oracle for which semantic was intended, and it
is why no reference export was needed to settle this.

## Decision

Pass the population the CPM was solved from. Both sites now take `analysis = st.analysis_for(...)`
once and hand `analysis.scoped` alongside `analysis.cpm` — which also drops a redundant second
`analysis_for` call. `scope()` is the identity when nothing narrows, so both edits are literal
no-ops in an unfiltered session; that is what the unfiltered controls pin.

## Consequences

`tests/web/test_ask_driving_facts_scope.py` — 6 tests. The unfiltered baselines are load-bearing:
they prove the fixture, the question, the UID and the intent parsing are all correct, so the
filtered failures are red for the RIGHT reason rather than a mis-parsed question. Mutation
**4/4 by name**, each mutant confirmed landed; the mutant that empties `driving_path_facts`
reddens the baselines too, proving they are not vacuous.

**A standing computed census replaces the prose count** (`tests/web/test_scoped_pairing_census.py`).
Naming the surfaces in prose has now under-counted this class three times, so the guard computes
it: it wraps every engine callable whose signature takes both a `Schedule` and a `CPMResult` (61
of them) and asserts at call time that `set(schedule.tasks_by_id) == set(cpm.timings)`, then drives
every parameterless GET route plus the Ask routes. Against the unfixed tree it reports exactly the
two violations above and names them; against the fixed tree, zero — and zero unfiltered in both,
so it is differential rather than blind.

Two of its own properties are asserted rather than assumed, because neither is free:

- **the instrument has teeth** — a knowingly mispaired call must be recorded, else a clean report
  could mean "never looked";
- **the sweep reaches import-time call sites** — `ai/driving_facts.py` binds
  `compute_driving_slack` with a module-level `from … import`, so patching only the defining
  module leaves the real caller pointing at the original. The sweep rebinds every loaded
  `schedule_forensics` module holding a reference, and blinding it to the defining module alone
  reddens that test by name.

**A surviving mutant fixed the guard, not the story.** The census first drove `/api/ask` with two
files only, so reverting the single-file site left it green while the dedicated module caught it.
Rather than explain that away, the census is now parametrized over one- and two-file sessions —
`/api/ask` branches on `len(st.schedules) == 1` and only the multi-version branch is scoped — and
both mutants now redden it by name.

**Scope of the claim.** The census covers routes reachable by a parameterless GET plus the Ask
routes; POST-configured surfaces (SRA setup, margin confirmation) are not driven by it, so this
ADR does not claim the class is empty there. `/briefing` and `/api/ai/narrative` were checked by
hand and are correctly paired.
