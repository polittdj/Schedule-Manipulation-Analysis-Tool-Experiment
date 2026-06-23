# ADR-0114 — Driving-path answers: inject engine facts ("skill"), don't let the model traverse

- Status: accepted
- Date: 2026-06-22
- Supersedes/relates: ADR-0011 (driving-slack SSI parity), ADR-0091 (driving path between two UIDs)

## Context

The operator reported that the local Ollama model "keeps messing up" questions like *"what is the
driving path to UID X?"* and *"how many activities drive UID X with zero days of driving slack?"*.
This is expected: multi-hop path + slack traversal over hundreds of activities is exactly what a
small (8B) model is unreliable at. The engine, however, already computes these **exactly** and
SSI-parity-validated (`engine/driving_slack.py` — `compute_driving_slack`, `driving_path`).

The operator asked, in effect, for a "skill the model can reference" so it does the program's work
correctly.

## Decision

Do **not** teach/coax the model to compute the traversal. Instead:

1. **Inject the engine's answer as cited facts.** A new `ai/driving_facts.py` exposes
   `driving_path_summary(schedule, cpm, uid)` (the deterministic, cited driving-path + near-driving
   facts for one focus UID) and `driving_path_facts(schedule, cpm, question)` (parse a keyword-named
   UID + driving intent from the question, then summarise). Ask-the-AI appends these to the fact
   sheet, so the model **narrates** the engine's numbers. The existing citation figure-gate
   (`ai.citations`) already discards any figure the model didn't get from a fact, so a wrong count
   cannot survive.

2. **Offer a one-click, no-AI answer.** `GET /api/driving-path?uid=&scope=` returns the same
   deterministic summary as plain text + citations, surfaced by a "Show driving path (exact, no AI)"
   control in the Ask panel. The operator never has to trust the model for path/slack at all.

UID parsing is **keyword-anchored** (`UID 143`, `task 143`, `activity #143`) so unrelated numbers in
the question ("0 days", "300 iterations") are never mistaken for a focus UID. The conceptual
reference ("skill") already lives in `web/help.py` (`driving_slack`, `driving_path`).

## Consequences

- Driving-path/zero-slack-driver answers are now **exact regardless of the model** (or with no model
  at all). The model's role is narration, not computation — consistent with the project's
  "every AI-emitted figure is re-verified against engine citations" law.
- The injection is scoped to questions that name a UID with driving intent, so it adds no cost to
  unrelated questions.
- Future: a name→UID resolver (answer "driving path to the roof milestone" without a UID), and the
  same pattern for other graph questions (longest path, merge hotspots).
