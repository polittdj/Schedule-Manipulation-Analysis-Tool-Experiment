# ADR-0479 — The driving path to a focus UID is computed for EVERY version (OR-11a)

Status: accepted (2026-09-08)

## Context

The operator asked, of a 32-version workbook: *"do you see signs of an intentional effort to
prevent UID 152 from slipping to the right? … You also need to calculate the driving path for UID
152 for each version."* ADR-0478 made the panel say why it had no written answer. It did not make
the question answerable, and the reason was recorded as **OR-11a**.

Two surfaces, one defect:

* `POST /api/ask` (multi-version branch) called `driving_path_facts(schedules[-1], cpms[-1], text)`;
* `GET /api/driving-path` with no `scope` fell through to `schedules[-1], cpms[-1]`.

**Measured**, not inferred — 32 synthetic versions of golden Project5, the focus UID named in a
driving-intent question, the real endpoint:

| | before |
| --- | --- |
| driving-path facts reaching the model | **1** |
| files those facts cite | **1** of 32 (`IPMR_v32.mpp`, the newest) |
| versions the deterministic button answers for | **1** of 32 |

So "for each version" was unanswerable *from the evidence*, whatever the model. The remaining 31
versions were loaded, parsed and CPM-solved — and then not asked.

## Three measurements decided the design

1. **The engine was never the problem.** `compute_driving_slack` reproduces the operator's own SSI
   Directional Path export for UID 152 on the real 2,126-task master IMS **exactly** — 76 of 76
   members, membership identical, checked against `golden/ssi_uid152/case.json`. A per-version
   series inherits that parity by construction; nothing new computes a schedule figure.
2. **The loop is affordable.** One `compute_driving_slack` on that 2,126-task file costs **0.039 s**,
   so 32 versions × 2 focus UIDs is **≈2.5 s** — on top of the 32 CPM solves the ask already pays
   for, and only when a driving-intent question names a UID.
3. **One fact per version would have broken the evidence budget.** The full 32-version sheet is 32
   facts today and `model_evidence`'s cap is 48, so nothing is dropped now; adding 32 more would
   have crossed it and started silently evicting the frame. Hence **one pinned series line**, not
   N facts — the shape `version_facts.py` already uses for the S-curve and finish series.

## Decision

`ai/driving_facts.py` gains `driving_path_series(schedules, cpms, uid)` and its question-gated
wrapper `driving_path_series_facts(...)`, emitting **two pinned facts**:

* **DRIVING-PATH SERIES** — every loaded version, ordered oldest data date first, each carrying
  *that version's own* driver count and the focus's own computed finish. A version the focus is
  absent from says so; a version whose slack could not be computed says *that*, separately. Never
  a fabricated `0` (Law 2: missing shows as missing).
* **DRIVING-PATH MOVEMENT** — first-to-last driver count, the focus's finish movement in calendar
  days, and the step census: how many version-to-version steps changed *which* activities drive
  the focus, and how many of those left its computed finish on the same date. That last number is
  the pattern the operator is hunting, and it is stated as a **count of what changed, never a
  motive** — the sentence says so explicitly, because the engine does not get to allege intent
  (the same line `ai.citations.introduces_loaded_terms` holds an AI rephrase to).

Both surfaces are wired: the workbook ask appends the series alongside the existing newest-version
detail, and `/api/driving-path` with **no scope** now answers for the workbook. Naming a scope
still means that one file exactly, and a single-version session is byte-identical to before.

`version_facts._elide` is promoted to the public `elide_series` and shared, rather than copied: two
implementations of "how long may a series line be" would drift, and both would look right alone.

**After, same measurement:** 32 of 32 versions named inside the series fact, on both surfaces, in
0.2 s / 0.1 s. On the real `Project2 → Project5` pair the series detects UID 35's driving path
collapsing from **6 drivers to 0**.

## Consequences

* A cross-version driving-path question is now answerable from cited engine facts, with or without
  a model: the series is pinned, so it survives both selectors and appears in the panel's own fact
  list when no model is active.
* The traversal is paid only on a driving-intent question naming a UID (`_INTENT` + `_named_uids`,
  capped at `_MAX_UIDS`), so ordinary questions cost nothing.
* Not addressed here: **OR-11b** (the 48-fact cap — measured today as non-binding at 32 versions,
  and it is now nearer), **OR-11c** (`num_ctx` is never sent), **OR-11d** (an unanswered ask
  exports without its reason).

## Evidence

* **Red first.** 18 new tests (11 unit + 7 endpoint) written against the pristine tree; the unit
  file failed on the absent API and 3 of the 7 endpoint tests failed on the behaviour. The other
  4 were green from the start **by design** — they assert what must NOT change (a scoped request,
  a single-version session, a question without driving intent, an unknown UID).
* **The fixture was verified against the engine before it was trusted**: v1's path is `{1, 2}`,
  v2's is `{3}` — zero overlap — while the focus's early finish is 12,000 working minutes in both.
  A re-wire with the date held, which is the whole point, measured rather than asserted.
* **Teeth: 12 of 12 mutations RED by name** — newest-version-only; CPMs re-paired positionally
  after ordering; series left unordered; an absent focus reported as zero; facts unpinned; the
  re-wire census stuck at never / always; the held-finish census never firing; each surface losing
  the series; the question gate removed; a single version emitting a series anyway. The first run
  returned **11 RED / 1 GREEN**, and the green was a finding about the TEST: the movement check
  asserted the sentence's *wording*, which a census hard-wired to zero still produces. It now
  asserts the *values* (`1 changed WHICH activities drive it`) and is paired with a **zero
  control** — two identical-logic versions must count 0 — so a constant in either direction fails.
