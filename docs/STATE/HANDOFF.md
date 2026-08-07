# Handoff — 2026-08-07 (battery phase 2: the seven queued families, measured then pinned; ADR-0362; v1.0.173 unchanged)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0362, **v1.0.173** (tests-only — no
> rebuild; the shipped tree is byte-identical to merged #548), SCHEMA 2.11.0.
> The operator merged #548 and said "Continue" → the standing queue resumed at its first
> line, battery phase 2 (the seven families ADR-0361 queued).
>
> ## ADR-0362 — battery phase 2: cei · hmi · fei/bri · evm · schedule_quality · forecast · SRA-readiness
> Every figure MEASURED before pinned (probe first, assert second). Two structural facts
> drove the design: (1) the bare 25-task program CANNOT honestly pass two families —
> Acumen Missing Logic has a 2/N structural floor (the first task + terminal milestone are
> always open ends: 8% on N=25) and Insufficient Detail divides by the STORED-finish span
> (span 1 day on a fixture with no stored dates → everything flags). Not engine defects —
> enriched variants instead: `_dated` (stored dates = actuals-else-baselines + WBS) and
> `_wide` (N=41 → floor 4.9%). (2) cei/hmi/fei-bri are informational (status always NA) —
> their pairs pin VALUES + offender uids, not status flips. EVM pins all THIRTEEN
> thresholds PASS on clean and four seeds flip EXACTLY their declared sets (set equality —
> stronger than phase 1: an expected flip that fails to happen also fails). Forecast: the
> four methods answer (CPM 2026-12-04 · stored 2026-12-06 · rate 2026-08-26 · ES
> 2026-08-14); un-finishing two tasks pushes rate/IEAC out a YEAR while logic/stored stand
> still — the divergence IS the finding; missing inputs answer None with honest bases.
> Readiness: 7 gates flip one-for-one; the hard-constraint seed's critical-path collateral
> mirrors phase 1's DCMA05→DCMA12. Two PERMANENT discriminators pinned: work that NEVER
> STARTS fails SPI/SPI(t) at 0.5 but leaves SPI(t)-Acumen PASSING at 1.44 (the per-activity
> average only sees STARTED work — ADR-0176); a late-vs-baseline start fails Started Late
> but leaves Baseline Start Compliance at 100% (Half-Step numerator compares to baseline
> FINISH — ADR-0083). Battery now 41 tests; 8 targeted engine mutations each went red on
> exactly their pair and every module restored byte-identical (cp, never git checkout).
>
> ## Next
> Phase 3 monolith split resumes at **margin 379** (re-measure the closure first;
> ADR-0350/0351/0352/0358 rules). Then: driving-corridor fixture · the three page-lede-less
> pages · /groups Activities counting summary rows (ADR-0343) · installers vs known-good
> constraints · the P80/P90 recurring-calendar-exception residual (own unit; ADR-0359's OAT
> match says the effect did NOT surface there) · Phase 6 docs. Battery future-work (not
> queued as a unit): a stored-slack fixture would let `cei_critical` leave NA. **Operator:**
> license · branch-protection · proprietary reruns · OR-04 · whether the July mpp/ oracle
> should re-export under replace semantics for a tighter v1 band.
>
> ## Carried forward
> ADR-0353..0361 closed — do not re-open. The battery discipline is now: probe FIRST, pin
> the measured value, mutation-prove, restore from scratchpad cp. A synthetic fixture that
> "fails" a population-floor or span-derived metric is telling you about the FIXTURE (2/N
> open ends; stored-finish span) — enrich the fixture, never weaken the metric. The
> workbook Mean/StdDev cells are UNWEIGHTED; the occurrence-weighted histogram is the only
> SRA oracle. A parity delta is a claim about INPUTS first. `pydantic>=2` NOT a safe floor
> (2.6); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). `ruff check .` whole tree
> as `python -m ruff`. `grep -c` exits 1 on zero — chain with `;`. The /analysis focus->tip
> family is load-sensitive — do NOT chase. bandit B608 on HTML f-strings with "from" → the
> house `# nosec B608 (HTML, not SQL)`. The full suite now exceeds a 10-min foreground
> timeout — run it `python -u` in the background and READ the tail.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
