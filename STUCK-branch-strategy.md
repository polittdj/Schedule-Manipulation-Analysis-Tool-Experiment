# STUCK — conflicting branch instructions

## The question I can't answer
Two instruction sets disagree on where my work should land:
- **Harness git rules:** "Develop all changes on `claude/schedule-analysis-tool-UKgXp`.
  NEVER push to a different branch without explicit permission."
- **Experiment workflow:** For each milestone, create a feature branch `mN-<scope>`, open a
  PR, and auto-merge into `main`; `EXPERIMENT-REPORT.md` lives on `main`; "the next milestone
  starts from a fresh branch off the new `main`."

These diverge in observable behavior (which branch accumulates the work, and whether there
is a reviewable PR-merge trail on `main`).

## Options considered
1. **Strictly follow the harness:** do everything on `claude/schedule-analysis-tool-UKgXp`,
   one PR to `main` at the end. Honors the "NEVER push elsewhere" rule literally, but
   destroys the experiment's core deliverable — a per-milestone PR-merge history on `main`.
2. **Follow the experiment:** per-milestone feature branches → PR → `main`. Produces the
   reviewable history the experiment is explicitly designed to leave behind.
3. **Hybrid:** experiment flow, AND after each merge fast-forward
   `claude/schedule-analysis-tool-UKgXp` to `main` so the designated branch is never orphaned.

## Option I'm picking and why
**Option 3.** The experiment text is the specific, current, detailed instruction, and it
*explicitly* authorizes feature branches + self-merge — which satisfies the harness rule's
own escape hatch ("without explicit permission"). The experiment's whole point is the
PR-merge trail on `main`, so Option 1 would defeat it. The fast-forward keeps the harness's
designated branch in sync, so nothing is abandoned. The user also saw and approved this
resolution at the plan-approval gate.

## What would let a human pick differently
- If the harness's designated-branch rule is hard policy (e.g., CI/automation keyed strictly
  to `claude/schedule-analysis-tool-UKgXp`, or branch protection on `main` I can't satisfy),
  I would re-target all milestone PRs at the designated branch instead of `main`.
- If a reviewer prefers a single squashed PR over five milestone PRs, Option 1 becomes
  preferable.
