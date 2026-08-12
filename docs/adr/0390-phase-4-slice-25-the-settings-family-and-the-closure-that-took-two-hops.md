# ADR-0390 — Phase 4 slice 25: the `settings` family, the closure that took two hops, and the repoint that is per call-site

- **Status:** Accepted
- **Date:** 2026-08-12
- **Continues:** ADR-0350 (the kernel), **ADR-0351 (the descent rule — two remedies, and this slice
  is the one that exercises the second)**, ADR-0352 (the span-scoped pre-flight probe), ADR-0365
  (closure-before-cut; the named-failure rule), ADR-0372 (the oracle recipe), ADR-0374 (a
  render-conditional member needs its condition IN the oracle), ADR-0378 (sweep by bare NAME;
  route-only referrers never force a descent), ADR-0382 (the oracle committed), ADR-0386 (a spy
  that asserts ZERO must be forced), ADR-0387 (prove an instrument can FAIL first), ADR-0388 (a
  priced table is a snapshot), **ADR-0389 (the finding this slice was asked to test — and the
  lesson it taught, re-earned one hop deeper)**
- **Related:** **ADR-0297 (the monkeypatch trap — live at scale here, for the first time)**,
  ADR-0343 (`groups` stays fenced), ADR-0315 (the AI runtime notes)

## Decision

**Extract the `settings` page family into `web/settings.py` — verbatim, twelve names, zero forced
descents** — and **extend the render oracle with an eighth stage** so the five members the
committed corpus could not witness are measured rather than assumed.

This is the **last page family to leave `app.py`**. Outside `groups` (fenced, ADR-0343), the
monolith no longer holds a page family.

| | movers | ast lines | app.py span |
| --- | ---: | ---: | --- |
| the page family proper | 7 | 347 | (within both) |
| the AI-backend closure it drags | 5 | 90 | (within both) |
| **`web/settings.py`** | **12** | **437** | **799–1033 · 8128–8356** |

Both regions are **contiguous runs of settings-only definitions** — no unrelated module-level
definition is interleaved with either, which is what makes the cut two whole-line slices (235 +
229 = 464 physical lines) rather than twelve separate splices. `app.py` **8,482 → 8,037**
(wc-truth), from 17,197 when phase 3 began. `settings.py` is 525 lines. `LAYER_ORDER` becomes
`… → volatility → settings → app`; `settings.py` joins pyproject's per-file E501 list, `EXTRACTED`,
`LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples.

## ADR-0389's finding was right, and its count was short by two

ADR-0389 asked slice 25 to test whether `settings`' three descent **candidates** are *forced*. Both
halves of the answer moved:

**The candidates are not three. They are five, and the second pair is one hop further out.**
`_settings_body` calls `_second_backend`; `_second_backend` reads `_BACKEND_PROBE_TTL` and
constructs `_UseMarking`. Both of those are *also* read by `_active_backend`, which stays — so they
have the **identical sharing shape** the record used to flag the other three. The record simply did
not follow the second hop. Cutting to the recorded price would have produced a module that does not
import, or a `settings` → `app` import, which is a cycle.

| candidate | reached from | blocking referrer that STAYS | where it lives | forced? |
| --- | --- | --- | --- | --- |
| `_ollama_or_none` | `_ai_status_note`, `_settings_body` | `_active_backend` | `app.py`, module level | **no** |
| `_openai_or_none` | `_ai_status_note`, `_settings_body` | `_active_backend` | `app.py`, module level | **no** |
| `_second_backend` | `_settings_body` | `_ask_response` | `app.py`, nested in `create_app` | **no** |
| `_BACKEND_PROBE_TTL` | **`_second_backend`** (hop 2) | `_active_backend` | `app.py`, module level | **no** |
| `_UseMarking` | **`_second_backend`** (hop 2) | `_active_backend` | `app.py`, module level | **no** |

**And no descent is forced.** A blocker is forced into `components.py` only if some *already
extracted* module references it — such a module cannot import sideways or up.

**Population: 32 modules** — the 31 already-extracted view modules (list read from `EXTRACTED`,
never hand-typed) **plus `state.py`**, which is in `LAYER_ORDER` but *not* in `EXTRACTED` and is the
BOTTOM layer, so a referrer there would force a descent too. Leaving it out would have been a
population defect, not a measurement. Four channels per module, so nothing hides in an aggregate:
`ImportFrom` alias, `ast.Name`, `ast.Attribute.attr` (the `app_mod._foo` reach), and `ast.Constant`
strings (the `getattr` dispatch an ast-only scan would miss).

Result: **0 referrers, across all twelve names.** Positive control, same scan: **`_e` in 29 of 32**
— and all three that lack it (`ssi.py`, `volatility.py`, `state.py`) are exactly the modules that
carry no HTML, so the control's *shortfall* is explained rather than tolerated. Independently
re-derived by an adversarial verifier over a deliberate superset — **all 91 names bound at `app.py`
module level** — also **0 referrers**, so no subset of those 91 can be reachable either.

`components.py` was rejected on **its own charter**, not on layering. Its membership was MEASURED
(ADR-0350) at *three or more page families* of shared **presentation** primitives. AI-backend
construction is reached by one family plus two `app.py` stayers, and is not presentation. So the
five move into the family module and `app.py` reaches them through the `X as X` re-export — which is
what the top layer is for, and what ADR-0351's rule permitted all along.

Checked forward as well as backward: the still-fenced `groups` family (8 movers, 430 ast lines)
has **zero** overlap with this cut and **zero** blockers of its own, so placing `settings` directly
below `app` cannot force a descent when `groups` is eventually cut.

## The corpus had never rendered a configured AI — so five members were dark

The span-scoped pre-flight probe was run **twice, against two instruments**, so "this member is
dark" and "the extension lit it" are two measurements rather than one measurement and a story.
Both runs used a dedicated worktree that nothing else touched, and both open with a
**reproducibility control**: the probe tree, unmutated, must reproduce the baseline exactly, or
every zero below is noise. It did — 948/948, then 1096/1096.

**Probe A, against the committed seven-stage oracle: 7/12 render-proven, 5 DARK.** Control `_page`
**263**, reproducing ADR-0389's value exactly, and decomposing as `[empty]` 29 + 6 × 39.

The five dark members were not five unrelated branches. Every stage in the corpus runs on the
**shipped default** `AIConfig`, so the corpus had never rendered a session with a primary backend
other than Ollama, a cross-check second model configured, a launcher manager attached to
`app.state`, or any `OLLAMA_*` tuning environment set. That is ADR-0389's lesson one hop deeper —
*ask what the corpus has never rendered, not what the member needs* — and the answer was again a
whole **class** of ordinary session state: what the operator's machine looks like the moment they
open AI Settings and change anything.

**`[aiconfig]`** is that render condition. Every key in `AI_CONFIG_FORM` is a field
`update_settings` *declares* (checked against the signature, not inferred from prose — ADR-0381),
`classification` stays **CLASSIFIED** so no cloud path is exercised, and both endpoints stay
loopback, so the constructors build real backends whose availability probe fails against a closed
port: deterministic, and **no egress** — Law 1 is not something an oracle stage gets to relax. The
stage is **last** because it mutates session config, `app.state` and process environment; `render()`
now snapshots and restores `os.environ` around the whole run so the mutation cannot escape.

Corpus **948 → 1096**; the pinned label list was regenerated in this commit. `[aiconfig]` renders
the full 148-label surface with the **same status histogram** as every other loaded stage
(`{200:125, 404:4, 422:19}`).

**Probe B, against the eight-stage oracle.** Its control was a **forward prediction, not a fitted
number**: if `[aiconfig]` is structurally an ordinary loaded stage, `_page` must move 29 + 7 × 39 =
**302**. It moved exactly 302, 39 of them in `[aiconfig]` — two instruments agreeing on a number
neither was told. `_openai_or_none` then moves **exactly one label, `[aiconfig] GET /settings`, and
nothing else** — reported as *which label*, not as a count.

**Two members remain dark, and they are dark by construction, not by omission.** `_UseMarking`
wraps a backend only when a `record_use` hook is set *and* routing yields a live Ollama, which no
offline corpus can produce; `_BACKEND_PROBE_TTL` is a cache lifetime, and a cache lifetime cannot
change rendered bytes. Both are covered by unit tests instead, and that is stated as the named gap
rather than smoothed over (the ADR-0373 precedent).

## THE MONKEYPATCH TRAP, LIVE — and the repoint is per CALL SITE, not per name

ADR-0297 named this trap fourteen slices ago; this is the slice where it actually fires, at scale.

Sweep population **518** `.py` files post-cut, 517 before it (`build/`, `dist/`, `.venv`, caches
excluded — `build/` is a stale copy of `src/` and sweeping it once produced a wrong answer in
ADR-0386; it is absent here). Over the names `settings.py` **binds** (25 = 12 defined + 13
imported — ADR-0387's population, not the moved names), **187** `X.setattr(<module>, "<name>", …)`
calls yield **21 hits**.

**The first sweep of this slice was WRONG, and the battery's own baseline control is what caught
it.** That sweep's regex was anchored on the fixture's name (`monkeypatch.setattr`), and
`test_coverage_app.py` binds `mp = monkeypatch` first. Four sites — all four feeding
`_ai_status_note` — were invisible to it, and the miss surfaced only because the battery refuses to
score a mutation unless its selection is **green beforehand**: the "baseline" run went red on
`test_ai_status_note_branches` before a single mutation was applied. Re-swept with a
receiver-agnostic pattern, the hits go 17 → 21 and the repoint 10 → 14. **A sweep's PATTERN is part
of its claim, exactly as its population is** — and the pre-mutation control is not a formality.

Splitting the hits was not a matter of listing names, because **the same name lands on both sides**:

- `monkeypatch.setattr(app_mod, "_ollama_or_none", …)` then driving `/settings` → the consumer is
  `_ai_status_note` / `_settings_body`, now in `settings.py`. **The patch stops reaching it.**
- `monkeypatch.setattr(app_mod, "_ollama_or_none", …)` then driving `/api/ask` → the consumer is
  `_active_backend`, still in `app.py`. **The patch still works, and repointing it would break it.**

Measured, not argued: **14 call sites repointed, 7 deliberately left alone.** `_ollama_or_none` and
`_second_backend` each appear on both sides of that line.

Eleven of the fourteen fail LOUDLY when forgotten. **Three would have passed SILENTLY** — the
defect class this whole apparatus exists for:

| site | what breaks | if forgotten |
| --- | --- | --- |
| `test_coverage_app_extra.py` `OpenAICompatBackend` | the `except` arm of `_second_backend` | still asserts `None` — **green, testing nothing** |
| `test_coverage_app_extra.py` `route_backend` (list_models raises) | the raising fake never installs | real routing also yields "none available" — **green** |
| `test_ai_wiring.py` `_ollama_or_none` (marking) | the reachable backend never installs | `recorded == []` either way — **green** |

A green run cannot adjudicate a spy that asserts zero (ADR-0386), so the non-zero case was
**forced**: patch the old target and the new one in turn with counting spies and drive the same
path.

```
A. _second_backend -> OpenAICompatBackend    app.py globals 0x   settings globals 1x
B. _settings_body  -> route_backend          app.py globals 0x   settings globals 1x
C. _ai_status_note -> _ollama_or_none        app.py globals 0x   settings globals 1x
CONTROL (caller that STAYED)
   _active_backend -> _ollama_or_none        app.py globals 1x   settings globals 0x
```

The control is the **mirror image of the finding, on the same name** — which is what makes 0× a
measurement of the boundary rather than of a broken instrument.

## Proof

- **Byte-identity: 1096/1096**, pristine vs cut, on the extended corpus — and the `diff -r` itself
  shown to fail (one-byte append → exit 1; restored, md5-verified → exit 0).
- **Determinism ×2 separate processes on BOTH trees: 0 flapping**, and the second pair reproduces
  byte-identity independently.
- **Reproducibility control ×2 instruments** — the unmutated probe tree reproduced its baseline
  exactly both times (948/948, 1096/1096), so the probe's zeros are real zeros.
- **Probe controls:** `_page` **263** (7-stage, reproducing ADR-0389) and **302** (8-stage,
  predicted before it was run).
- **Battery 6/6 caught BY NAME**, each an exact-match splice with a landed-count assert before the
  write, each restored from a scratchpad copy and **md5-verified**, and the selection re-run GREEN
  after every restore. M6 does double duty — it changes a string the *moved* `_ai_status_note`
  renders, and it is caught by **both** of the repointed tests, so the repoint is proven to reach the
  moved code rather than merely to compile. **M7 is scored against the ORACLE, not pytest:** its
  anchor is unique in `settings.py` and asserted by **no** test file, so the unit selection stays
  **rc=0 with zero named failures** (the unit tests genuinely do not pin moved markup) while the
  oracle reports **8 differing labels** — matching the probe's independent per-member count for
  `_ai_backend_explainer` exactly. Two instruments, one number, neither told.
- **Verbatim by construction:** the moved text is a byte slice of `app.py`, never re-typed; both
  regions were re-read **from disk** and asserted present in `settings.py`, and all twelve
  definitions asserted **absent** from the post-cut `app.py`.
- **Dropped imports: ZERO.** `ruff check --fix` removed nothing — `/api/ai/models` stayed in
  `app.py` and still uses `OllamaBackend` / `OpenAICompatBackend`, and `_active_backend` still uses
  `route_backend` / `NullBackend`.
- `mypy --strict` clean over **149** source files; `ruff check .` clean whole-tree.
- The corpus was re-rendered **after** the mutation battery and is byte-identical to the
  pre-battery cut render, so nothing the battery touched leaked into the measured tree.

## The one behavioural consequence, named rather than hidden

`_UseMarking`'s exception-path debug call is `logging.getLogger(__name__)`. Its **text** moves
byte-for-byte; `__name__` is not text, so the logger name changes from
`schedule_forensics.web.app` to `schedule_forensics.web.settings`. Nothing observes it — it fires
only when a caller's `record_use` hook raises, and no test or render asserts that logger — and
rewriting it to a string literal would trade a verbatim move for a hard-coded lie. It is the only
module-identity-sensitive construct in the moved bytes (checked: no `__file__`, `__module__`,
`globals()`, `sys.modules` or `inspect` use).

**Verbatim text is not always verbatim behaviour.** Every previous slice in this phase asserted
byte-identity of the moved definitions and treated that as sufficient; it is sufficient only for
code that does not read its own module identity.

## Deliberately NOT done

- **A dedicated `web/backends.py` was considered and NOT created.** It would be more cohesive than
  parking the AI-backend kernel in a page module, but it is a *second* architectural decision, and
  conflating a kernel extraction with the last page-family cut would make neither reviewable. The
  five names are layer-legal where they are; promoting them is a clean follow-up, now queued.
- **`_active_backend` was NOT moved.** It is route-reached only, so moving it is permitted — but it
  would take four more names out of `app.py`'s globals and thereby *widen* the monkeypatch trap
  across the seven call sites that currently still work. Measured trade, declined.
- **`groups` stays fenced** (ADR-0343). It was priced (8 movers, 430 ast lines, zero blockers) only
  to prove it cannot be affected by where `settings` was placed.
- **`_UseMarking` and `_BACKEND_PROBE_TTL` were not forced into the oracle.** Lighting them would
  require a live local model, which an offline corpus must not require.
- **`mpxj_ref()`'s shallow-clone hardening is still queued, not silently patched.** The trap was
  pre-empted again — `git fetch --unshallow` ran before the build, so the nine installers pin
  `42d92dc` — but the build still trusts the operator.

## Consequences

- **A closure is not closed until it stops growing.** ADR-0365's "closure before cut" was followed
  in three prior slices and still under-delivered here, because the closure was computed to a
  fixed point *of the movers* and not *of the blockers*. The second hop is where a cut breaks.
- **A count copied forward decays even when the reasoning behind it was sound.** ADR-0389 correctly
  relabelled the column *candidates*; the number in it was still wrong. Re-walking a table is not
  optional because the last re-walk happened to hold.
- **The monkeypatch repoint is keyed on the CALLER, not the name.** A name-keyed repoint would have
  broken seven working tests while fixing ten broken ones, and the two sets share names.
- **Ask what the corpus has never rendered — again.** Two consecutive slices found a dark member
  whose real cause was a whole class of unrendered input. That is now a standing first question,
  not a slice-specific insight.
- **A control worth having is one whose shortfall you can explain.** `_e` at 29 of 31 is stronger
  evidence than 31 of 31 would have been, because the two misses are exactly the two modules with
  no HTML.
