# ADR-0509 — QC-3, the third standing working rule: the plan is wrong until it survives its author's attempt to refute it

Status: accepted (2026-09-18). Standing operator directive — binding on every session, no exceptions.

## Context

The operator directed, mid-session on 2026-09-18, while the R-67 unit was between its research and
its first edit:

> after you have done your research and investigation and come up with your plan assume its all
> wrong and double check it and prove that you are correct before making changes. Make this a rule.

`CLAUDE.md` already carried two standing working rules (ADR-0393): QC-1 binds a *claim* — prove or
refute it before you report it — and QC-2 binds the *reading* — read everything, verify everything.
Neither names the **plan**. A plan is where the two meet: it is assembled from claims that were each
verified, and it is still a hypothesis, because the plan asserts something none of its parts do —
that THIS mechanism, at THIS seam, on THIS population, is what the change must be. The repo's own
campaign supplies the failures of exactly that shape, every one after ADR-0393 was in force:

- **R-64's plan** (ADR-0491's row) named an external predecessor link, `PredecessorUID -65535`, as
  the mechanism. Every step of the plan was executable; the premise was false — the number was a
  `ResourceUID`, MS Project's unassigned-work placeholder, and the day was lost nine links higher
  (ADR-0505).
- **R-58's plan** named UID 14 as its witness; the activity on the intersected calendar was UID 94
  (ADR-0503). **R-61's plan** carried a premise ("the window is the rule") that was 315-to-0 wrong
  once generalised (ADR-0500). **R-65's plan** quoted a residual range, 1–28 minutes, that was the
  range the last census had happened to print; the population read 1 to 62 (ADR-0508).
- **R-63's plan** began "write the availability tables" — the vendored writer already wrote them;
  the plan's first step was already true and the fix lived two layers away (ADR-0506).

Each was caught, but each was caught *inside* the unit, by a session that happened to measure
before it edited. Nothing in the standing rules required that measurement to happen before the
first change; QC-1 required the *fix* to be proven, and a plan that survives no attack still
produces a fix that passes its own tests.

**The rule was applied to the unit it interrupted, before it was written down.** R-67's kickoff
plan read: carry a leveled successor's late-start need to a fast-path milestone as a wall instant,
red-first on UID 157's stored Friday 23:00 and UID 94's stored 6,360. Attacked on the pristine tree
with executable probes (the session's `attack.py`, over the 15 goldens and the 29 fresh conversions):

| assumption in the plan | attack | result |
| --- | --- | --- |
| "ADR-0474's backward arithmetic is exact when fed the stored Saturday" (testimony from the row) | run the helpers with the stored Saturday 13:00 as 157's finish need | **survived**: 157 → 07-31 23:00 / 15:00 / 2,760; 94 → 07-31 15:00 / 07-30 22:00 / 6,360 — every stored value, to the minute |
| the carried instant comes from a wall-path SUCCESSOR (the mirror of ADR-0505's gating) | read the 24-hour snapshot's chain head | **fell**: milestone 155's late instant is its **deadline**, a raw cap with no successor at all; the 24-hour crew below it read the start-role rendering fifteen hours late, and the same deadline-headed chain exists on updated2 / updated3 — a successor-gated mirror would have left the row's own witness (156's −4,320 vs −4,740) untouched |
| the row's one milestone is the class | census every zero-duration task's stored LateStart against the project calendar's working time | 155 of 2,210 sit OUTSIDE working time, 1,740 on a segment boundary; 27 fast-path milestones are bound by a raw cap on 44 files |
| the late-start arithmetic below the milestone is exact | feed 189's late start to 178 | 178's LS reads 08-04 **12:00** where MS Project writes **13:00** — a retreat that lands on a segment END where the reference tool writes the next segment's start: a second class, measured and registered, not chased in R-67's unit |

Two of four fell. The plan that was executed is not the plan that was written, and the unit's ADR
says which assumptions were replaced.

## Decision

Add **QC-3** to `CLAUDE.md`'s standing working rules, with the same standing as QC-1 / QC-2, and
retitle the section **"The three non-negotiable working rules"**:

**QC-3 — The plan is wrong until it survives your attempt to refute it.** After the research and
investigation are done and a plan exists — and before the first change is made — assume the plan is
wrong. Double-check it: write down every load-bearing assumption the plan rests on, attack each one
with an executable check or an independent reading of the artifact, and prove the plan correct
before making changes. A plan that has not survived its own author's attempt to refute it is a
hypothesis, and hypotheses do not get to change code, numbers, or documents. With five
sub-obligations: the plan is a claim and QC-1 applies to it; attack the premises, not only the
steps; a check that agrees with the plan is not the check (count the class beside the case; measure
every candidate rule on the population); record what fell; and mark an untestable assumption
UNVERIFIED rather than build on it.

**The pin test grows with it.** `tests/test_standing_rules.py` now pins three rule headings, the
section heading's new count, QC-3's binding clauses scoped to its own section (including its own
`NO EXCEPTIONS` — QC-1's copy cannot vouch for it), and the comment-out guard over every rule. The
attribution oracle is generalised: each rule group is decided by exactly one ADR whose **title**
declares the whole group (QC-1 and QC-2 together, ADR-0393; QC-3 alone, this ADR), and a doc line
that names the guard together with an ADR must cite the ADR that decided **every rule the line
names** — a line naming no rule must cite at least one deciding ADR. The pair-oracle's discipline
(a title that merely *applies* a rule must not carry the bare token) now covers QC-3's title too.

**What QC-3 adds that QC-1 and QC-2 do not.** QC-1 is triggered by a claim and QC-2 by an artifact;
QC-3 is triggered by the *moment* — research finished, nothing yet changed — and its object is the
plan as a whole: its mechanism, its seam, its witness, its population, its remedy. It also fixes the
order: the attack happens before the first edit, not as a verification of the edit afterwards.

## The rule was applied to its own creation

1. `tests/test_standing_rules.py` was extended **first**, against a `CLAUDE.md` that did not yet
   contain QC-3, and **observed to fail by name**: `test_the_working_rules_section_exists` (the
   count), `test_every_rule_keeps_its_own_heading`, `test_every_rule_carries_its_binding_clauses`
   and `test_docs_cite_the_rules_under_the_adr_that_decided_them` (the oracle found no ADR whose
   title declares QC-3) — **4 failed / 3 passed**, the three controls green.
2. QC-3 was written into `CLAUDE.md`; the module read **1 failed / 6 passed** — only the attribution
   oracle, because this ADR did not yet exist. This ADR was written; **7 / 7 green**.
3. A **mutation battery** was run — eighteen cuts on `CLAUDE.md`, this ADR's title and a doc line,
   the module run whole each time, the file restored from a scratch copy and md5-verified after
   every row — and **its first run caught a defect in the pin**: M08 (drop "refute" from the
   binding sentence) stayed green, because a bullet's "refuted" still matched the bare token. This
   is ADR-0393's own lesson, paid for a second time on the first battery of the rule that cites
   it. The clause was tightened to the phrase ("attempt to refute it") and the whole battery
   re-run: **18 / 18 red by name, control green**.

### Mutation battery (run 2, after the clause was tightened)

| cut | red test |
| --- | --- |
| M01 delete the QC-3 section · M02 its heading into prose | `test_every_rule_keeps_its_own_heading` + `test_every_rule_carries_its_binding_clauses` |
| M03 comment the section out | `test_the_rules_are_not_commented_out` |
| M04 "assume the plan is wrong" softened · M05 "before the first change is made" dropped · M06 "prove the plan correct before making changes" dropped · M07 "load-bearing assumption" dropped · M08 "attempt to refute it" dropped (the heading keeps the word) · M09 `NO EXCEPTIONS` dropped from QC-3 only (QC-1's copy survives — the per-section scope) · M10 the QC-1 interlock dropped · M11 `UNVERIFIED` dropped · M12 "hypothesis" dropped · M13 "double-check" dropped · M14 "after the research" dropped | `test_every_rule_carries_its_binding_clauses` |
| M15 the section heading's count back to "two" | `test_the_working_rules_section_exists` |
| M16 this ADR's title no longer names QC-3 | `test_docs_cite_the_rules_under_the_adr_that_decided_them` (the oracle finds no deciding ADR) |
| M17 a doc line names QC-3 and the guard but cites ADR-0393 only · M18 a doc line names the guard, no rule, and cites an unrelated ADR | `test_docs_cite_the_rules_under_the_adr_that_decided_them` |

## Consequences

- Every unit now has a named step between "the plan" and "the first edit" — the attack — and its
  ADR owes a record of which assumptions were tested, which survived and which fell. The R-67 unit
  (ADR-0510) is the first written under it.
- The rule costs time on every unit, deliberately: the failures it targets are the ones this
  campaign has already paid for five times, and each cost more than the attack would have.
- The section heading's count is part of the pin. A fourth rule changes the heading and the test
  together, as this one did — never one without the other.
- **Deliberately NOT done:** no hook enforces QC-3, for ADR-0393's reason — a hook cannot tell
  whether an attack was capable of refuting the plan, and a mechanical proxy would be theatre. The
  rule is enforced by the working discipline and pinned against silent deletion.
