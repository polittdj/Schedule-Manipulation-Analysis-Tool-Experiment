# ADR-0137 — The Ask-the-AI figure gate is now role-aware (audit F-11): value vs. identifier

## Status

Accepted. Supersedes the *disclose-don't-set-gate* posture of ADR-0134.

## Context

Audit F-11 found that the strict/annotate figure gate guarded a figure's **presence** in the cited
facts, not its **role**. A digit carried by an activity **name** or **UID** (e.g. "Milestone 2099",
UID 6077) is "present", so a model could re-use it in another role — a name-digit `2099` re-emitted as a
finish *year*, a UID `6077` re-emitted as a *count* — and strict would accept it. ADR-0134 chose to
**disclose** the limitation (Ask-the-AI panel, docstring, CLAUDE.md) rather than close it, because a
blunt set-exclusion of every identifier digit is wrong: a UID `5` is indistinguishable from a count `5`,
so excluding identifier digits wholesale would discard real engine values.

The insight that unblocks a real gate: **don't exclude identifier digits — distinguish them by where
they appear.** A digit that appears in a fact's text *outside* every cited activity name / `UID n`
reference is a genuine engine **value**; one carried *only* by a citation's task name or unique id is an
**identifier**. A digit that is *both* counts as a value. That split is collision-safe (the count-`5`/
UID-`5` case resolves to "value"), so it closes F-11 at the value level without the false positives that
made a set-gate unacceptable.

## Decision

1. **Role split (`ai/qa.py::_figure_roles`).** Over the evidence facts, build `(value_figures,
   identifier_figures)`: `identifier_figures` are the digit tokens in each citation's `task_name` and
   `unique_id`; `value_figures` are the digit tokens in the fact text **after** blanking every cited
   `task_name` and `UID n` occurrence. A digit present as a value is a value even if it is also some
   identifier.

2. **Classification (`_classify_figures`).** An answer's figures are split, in priority order, into
   **value** (literally a cited value — untouched), **verified derivation** (reconstructed from the
   cited *values* by a standard operation — Layer B, ADR-0135), **identifier-reused** (matches only a
   name/UID — the F-11 role case), and **unverified** (none of the above).

3. **Strict discards a re-roled identifier.** Strict now returns `None` if the answer contains any
   unverified figure, any additive-only reconstruction, **or any identifier-reused figure**. No
   invented *or re-roled* number reaches the analyst.

4. **Annotate flags it.** A new `_ROLE_NOTE` footer ("Figures matching an activity name or ID, not an
   engine value — confirm the role, not just the number: …") is appended when an identifier-reused
   figure is present, alongside the existing verified-derivation and AI-derived footers.

5. **Interpretive stays ungated** by design (raw model output, operator opt-in).

6. **Disclosure updated** to describe the gate as role-aware: the Ask-the-AI panel ("Figure check is
   role-aware"), the `ai/qa.py` module + `answer_question` docstrings, and CLAUDE.md.

## Consequences

- F-11 is closed for strict/annotate at the value level: a name/UID digit re-used as a value is
  discarded (strict) or flagged (annotate) instead of silently accepted.
- Collision-safe: a genuine engine value that happens to coincide with some UID is never discarded, so
  no real figure is lost — the concern that kept ADR-0134 disclosure-only.
- No engine/metric math changed and no parity number moves — the gate operates on already-computed
  cited facts. The change is additive to the AI layer; full gate green.
- A fuller **semantic** role model (a figure's meaning, not just value-vs-identifier) remains future
  work — the `docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` direction.

## Alternatives considered

- **Keep ADR-0134 disclosure-only.** Rejected now that a collision-safe split exists: the limitation is
  closeable without the false positives that originally blocked it.
- **Exclude all identifier digits from the sourced set.** Rejected (the original F-11 reasoning): a UID
  `5` is indistinguishable from a count `5` by value alone, so this discards real figures. The
  positional split (value = outside the name/UID span) is what makes closure safe.
- **Close it for interpretive too.** Rejected: interpretive is the operator's explicit opt-in to raw,
  ungated model analysis; the standing "AI can err — verify against the citations" disclaimer governs it.
