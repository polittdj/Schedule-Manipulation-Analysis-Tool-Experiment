# Handoff — 2026-09-16 (c) (R-61 **SETTLED** on the repository's own 29 `.mpp` files (ADR-0501) — twice the golden population; ADR-0474's type rule upheld, ADR-0500's deferred residual **discharged** and its refutation witness **corrected**; `engine/` untouched, **v1.0.267 unchanged**)

STATUS (current) — `main` @ **`ed977f29`** (#689, R-61 SETTLED / ADR-0501, merged 18:21Z; the squash is **TREE-IDENTICAL** to the reviewed head `c6f762d9`, tree `947d59b3…` on both, compared with `git rev-parse <sha>^{tree}` — steward §2's tree-hashes-first rule). #689 was **SIX OF SIX GREEN** on that head (CI run 35125259344: `cui-guard` 16:58:45Z · `browser` 17:16:02Z · `floor` 17:23:30Z · `test (3.11)` 17:44:53Z · `test (3.13)` 17:44:56Z · `check` 17:45:01Z), zero review threads. Before it `6288ef16` (#688, R-61 CLOSED / ADR-0500, merged 15:45Z, tree-identical to `0a25715a`). **`main`'s own runs for `ed977f29` were NOT read before this session closed — READ THEM FIRST.** No `installer-smoke` run should exist for it (docs+tests only; the workflow is path-filtered to `installer/**`) and that absence is CORRECT. The branch was restarted on the squash (`--prune` + `remote set-head` + `checkout -B`, upstream unset, tree clean) and the session unsubscribed automatically. `chatgpt-codex-connector` posted its usage-limit notice on #689 — **review cover remains ABSENT**. Highest ADR **0501**. Version **1.0.267**, unchanged — this unit touched no `src/`. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**The operator's instruction was "use the `.mpp` files in the repo to settle the rule", and it
exposed a scoping error in ADR-0500 that is the main lesson of this unit.** ADR-0500 closed R-61
on **15 goldens** and deferred a residual reading *"only a production IMS can settle it"*. The
repository carries **29 `.mpp` files** — roughly twice that population, including files no golden
was ever made from (`24Hour Calendar.mpp`, `Hard_File_updated4 24 hour calendar.mpp`, `Jacked Up
Schedule 1/2`, `Project3/4`, the `Project5_FX0*` and `TP4_DataCenter` tamper sets, the
`Large Test File*.mpp` family). **The residual was a claim about the goldens wearing the clothes
of a claim about the world.** All 29 were converted through the vendored MPXJ converter into the
scratchpad (never the repo — Law 1), every artifact asserted to EXIST rather than the exit code.

**The wider census upholds ADR-0474 and discharges the residual.** 483 tasks are placed by an
off-pattern ratio-1.0 crew leg:

| | count |
| --- | --- |
| window **byte-identical** to the engine's occupancy (duration + ADR-0491 gaps) | **369** |
| differ, adjudicating, margin **1–28 minutes** | most of the remainder |
| leg-alone probe matches neither rule | 18 UIDs — **shipped solve within a day on 17** |
| **decisive** disagreement | **exactly one: UID 5263** |

The minutes are **gap-arithmetic granularity**, not a rule: UID 5342 occupancy 2,757 vs window
2,758 (**one minute**), UID 5316 9,329 vs 9,333 (**four**). Registered as **R-65**.

**The one decisive case adjudicates FOR the engine.** `Large_Test_File2` UID 5263 is *started*
(86 %, no `ActualFinish`) so its stored `Finish` really is MS Project's scheduled output. Its
window runs **9,600 min past** the duration and the leg alone lands **four weeks early** — and
the **shipped solve is exact**, disclosed on **`date_driven`**: a stored date places it, not the
leg. The mechanism was measured: the first explanation offered (ADR-0391's actual-start floor)
was cut in the battery and the task did not move, so it was refuted before it was written down.

**Two corrections to ADR-0500, both measured.** Its refutation witness `Large_Test_File` UID 5231
is **recorded-COMPLETE**, so its stored `Finish` IS its `actual_finish` — a record, not a
schedule — and by ADR-0476's own reasoning it adjudicates a scheduling rule in neither direction.
And the engine's leg does **not** "get it right" there: alone it lands 2024-10-01 17:00, **eighty
days** past the file's date, the solve being exact only through ADR-0476's pin. ADR-0500's
headline *"315 away / 0 toward"* **stands** (a different, valid measurement — the window rule
inside a full solve); the sentence explaining UID 5231 does not.

**Shipped:** the test module's witness renamed and re-reasoned
(`test_uid_5231_is_a_completed_task_so_its_leg_never_places_it`), a new
`test_uid_5263_the_corpus_only_decisive_counter_case_is_exact_in_the_solve` pinning
`date_driven` as the mechanism, the corrected module docstring, **ADR-0501**, the amended R-61
row and the new **R-65** row. **`engine/` untouched.**

## How it was verified

* **Four cuts of the census, each correcting the last — and the corrections ARE the finding.**
  Cut 1 counted co-bookings as masking (masking is whichever leg finishes **LAST**, computed).
  Cut 2 paired a leg to its booking by **calendar identity** and silently reported "no window"
  for all 483 — a leg on a TASK calendar matches no resource's calendar object; the fix pairs by
  index and **asserts `len(pairs) == len(legs)`** so the instrument detects its own failure.
  Cut 3 compared a **gapless** leg against a window that spans the gaps, handing every split
  booking to the window by construction. Cut 4 is the engine's real occupancy.
* **Mutation battery, control green:** N1 (ADR-0476's pin cut) → the 5231 correction red by name;
  N2 (R-61's window rule) → the 5263 pin and three others red by name.
* **N3 is recorded as a NON-MUTATION on its first cut** — the stub was inserted BEFORE the real
  definition so the real one won the name. Re-cut so the stub wins, it SURVIVES, and that is how
  `date_driven` was found.
* Statics green on both ruff binaries, `ruff format`, `mypy --strict`, `bandit`; 11 pins green.

**Gate on the final tree: 5,490 passed / 0 failed / 7 skipped in 35:41**, and **`-m parity` 142 passed / 0 failed** in 4:36. Both deltas ATTRIBUTED, not assumed: the previous unit's 5,489 and 141 plus this module's one new pin — it collects **exactly 11** under `-m parity`, up from 10 (`pytest -m parity tests/parity/test_r61_fixed_duration_leg_oracle.py --collect-only`). The 7 skips are the documented set (the urlparse pair, three INCIDENTAL_SVG axis cases, and the two `test_pptx_libreoffice_interop` skips that are correct in this container — CI installs the filter and treats a skip there as a FAILURE, ADR-0498). Statics green on both ruff binaries, `ruff format`, `mypy --strict`, `bandit`.

**PR [#689](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/689) — SIX OF SIX GREEN on head `86a13a72`** (CI run 35120093272: `cui-guard` 16:09:56Z · `browser` 16:27:40Z · `floor` 16:38:59Z · `test (3.13)` 16:52:02Z · `test (3.11)` 16:57:13Z · `check` 16:57:19Z); base `6288ef16`, unmoved. Six is the correct set: no `installer/**` path is touched and `installer-smoke.yml` is path-filtered, so the absence of `linux` / `windows` is correct and not a missing check. **No record of THIS commit's own CI will be pushed** — that treadmill (each record moving the head it describes and restarting CI) was named in the previous unit.

## Deliberately NOT done

No `engine/` change, no version bump, no wheel/installer rebuild. ADR-0500's "315 away / 0
toward" is not withdrawn — only the sentence that mis-explained its witness. R-65 is registered,
not taken.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then the report's §3 in order:
**R-57** (an assignment's OWN leveling delay — `Hard_File` UID 398's RA 277 is a split ON a
delayed assignment: its gap is honoured since ADR-0491, its delay is not; UID 188 on updated2) ·
**R-58** · **R-59** · **R-64** · **R-63** · **R-62** · **R-65** (this unit's granularity
residual) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The
design queue is 19 artboards.

**Review cover is still absent** — Codex quota EXHAUSTED; the mutation batteries and the full
gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
