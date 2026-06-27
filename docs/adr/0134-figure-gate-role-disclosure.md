# ADR-0134 — The Ask-the-AI figure gate guards presence, not role (audit F-11): disclose, don't set-gate

## Status

Accepted.

## Context

The re-audit's F-11 finding: the Ask-the-AI strict/annotate figure gate
(`ai/qa.answer_question` → `ai/citations._FIGURE_RE`) compares the *multiset of digit tokens* in the
model's answer against the digit tokens in the cited facts. It verifies a number is **present** in the
evidence, not that it is used in the same **role**. Because a fact's text legitimately carries activity
**names** and **UIDs** — e.g. the driving-path finding title
`recommendations.py:478`: *"… activities drive the path to 'Milestone 2099' (UID 6077)"* — the digits
`2099` and `6077` enter the sourced set. A model could then re-role one (the name-digit `2099` as a
finish year, a UID as a count) and pass the strict gate. Interpretive mode is ungated entirely.

The operator asked to address F-11.

## Decision

**Disclose the limitation precisely at the point of use; do not attempt to close it with set
arithmetic.** A token-subtraction gate (exclude name/UID digits from the allowed set) was rejected
because identifier digits collide with legitimate figures — a UID `5` is indistinguishable from a
count `5`, so subtracting identifier digits would discard real engine figures and make strict mode
reject valid answers (a false positive in the rigour mode). Token matching cannot tell a number's role;
only contextual/semantic comparison can, which is the `AI-DERIVED-METRICS-SCOPE.md` **Layer B**
direction (deferred).

Disclosure was added in three places:
1. **Ask-the-AI panel** (`web/app.py`) — a standing note: *"Figure check guards presence, not role …
   a digit that occurs in an activity name or ID (e.g. 'Milestone 2099', UID 6077) counts as present,
   so the model could re-use it in a different role … Interpretive mode is not figure-gated at all."*
2. **`ai/qa.py`** — the module docstring and `answer_question` docstring spell out the presence-not-role
   scope and why it is disclosed rather than set-gated.
3. **CLAUDE.md** — the figure-gate paragraph records the F-11 scope and the token-collision rationale.

A guard test (`tests/ai/test_qa.py`) pins the documented behaviour — strict **accepts** a re-roled
name-digit (`2099`) yet still **discards** a genuinely-invented number (`2031`) — so any future
tightening is a deliberate, semantic change, not an accident; and `tests/web/test_ask_everywhere.py`
asserts the panel caveat renders on every page alongside the standing disclaimer.

## Consequences

- The limitation is now **disclosed at the point a reader sees an AI figure** (testimony-defensible:
  the reader is told to check the figure's *meaning*, not just that the number appears), rather than
  silently relied upon. No behaviour changed; no parity number moves.
- Strict mode keeps its property — *no number absent from the cited facts reaches the analyst* — without
  the false positives a blunt identifier-exclusion gate would cause.
- A true role-aware gate remains future work (Layer B): contextual comparison of a figure's role against
  the engine fact it came from, not bare token matching.

## Alternatives considered

- **Exclude name/UID digits from the allowed set.** Rejected: token collision with legitimate figures
  (UID `5` vs count `5`) → strict false positives; annotate would flag every legitimate UID citation as
  "AI-derived" (UX regression).
- **Strip names/UIDs from the fact text that feeds the gate.** Rejected: names and UIDs are useful to
  the analyst in the fact text, and stripping is fragile.
- **Default to strict.** Out of scope here; the mode default (annotate) is an ADR-0129 decision.
