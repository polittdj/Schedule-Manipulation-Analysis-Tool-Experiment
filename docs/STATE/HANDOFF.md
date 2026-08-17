# Handoff — 2026-08-17 (e) (IMP-01 + the three MIXED-POPULATION rows, which were one CLASS of eight; ADR-0419/0420, v1.0.212)

> ## STATUS (current) — audit CONTINUING on `claude/polaris-audit-continuation-i1cxqq`.
> Highest ADR now **0420**. Shipped code DID change (`importers/mspdi.py`, `web/app.py`), so
> **v1.0.211 → 1.0.212** and the wheel + all nine installers were rebuilt (ADR-0148). SCHEMA
> 2.11.0 unchanged. Branch started clean from `origin/main` at 9cd9b02. The live audit ledger is
> `docs/STATE/AUDIT-2026-08-16.md`. **Ran entirely SOLO** (the kickoff's standing advice), so say
> plainly which dimensions got depth: importers and web-scope got deep treatment; the route × test
> gap-fill and the never-audited dimensions got NONE this session.
>
> ## First: two stale docs were corrected, as the kickoff instructed
> The injected STATUS pointed at `claude/polaris-browser-orphan-01-3824ij` (merged as #598, branch
> deleted) and `NEXT-SESSION-PROMPT.md` was the pre-merge draft. Both verified stale by reading and
> refreshed in this commit — a merged PR cannot carry the correction, which is why this keeps
> happening.
>
> ## IMP-01 — real mechanism, LATENT reach (ADR-0419)
> The row's detail was lost with the round-3 pool, so it was **re-derived from source**.
> `mspdi.py::_parse_calendar` reads a `DayWorking=1` weekday with no usable `<WorkingTimes>` **two
> ways four lines apart**: `if minutes > 0` drops it from the census, while
> `dominant_day_minutes(...) or MINUTES_PER_DAY` declares that exact construct worth 480. The two
> agree on a uniform calendar and diverge the moment one MIXES — the minority explicit day wins
> outright. Measured: Mon 4 h + Tue-Fri default → **240 min/day, an 80 h task displaying as 20.00
> days instead of 10.00** (a 2× error on every duration-in-days figure). A second route reaches the
> same hole (`08:00 → 08:00` is a documented zero-length span).
> **But it is LATENT, and that was measured, not assumed**: a census of **56 real MSPDI documents**
> (every committed MSPDI-rooted file + 25 MPXJ conversions of the reference `.mpp`s) finds **zero**
> occurrences — MPXJ always emits `WorkingTimes`. Fixed anyway (cheap, and two readings cannot both
> be right); **proven a no-op on the corpus** by diffing the parsed calendar of all 83 documents
> patched vs pristine — **identical** — and `pytest -m parity` **72 passed**. Mutation **5/5 by
> name**. The residual "is the default really 480 or the file's `MinutesPerDay`?" is **UNVERIFIED
> and unchanged** by the fix; it needs a real MS Project file carrying the construct.
>
> ## The three MIXED-POPULATION rows were EIGHT sites in one class (ADR-0420)
> All three confirmed by one differential probe (flip the scope, diff two surfaces — ADR-0417's
> technique), with `analysis.scoped` as the **control** proving the filter bit. On the shipped
> example under an `Activity Type: Normal` reduce filter (9 → 8):
> one filtered `/analysis` page rendered `<div class="stack-foot">9 activities</div>` **and**
> `8 activities in the grid`; `/api/analysis` shipped `tasks=9` beside 8 `activities[]` in ONE
> payload; **`/ribbon` did not move at all** ("Missing logic: 2 / Logic wired 7" filtered and
> unfiltered alike) where the honest scoped figure is **5 of 8**; and the exported workbook's
> Schedule-quality sheet shipped **2 of 9** where the page's own population gives 5 of 8.
> **A computed AST census found five MORE route functions the ledger never named** —
> `schedule_card` ×2, `standards_view`, `_schedule_facts` ×2 (**the fact sheet the AI is allowed to
> cite**), `export_ribbon`, `export_ribbon_drill`. All eight fixed by passing `analysis.scoped`;
> safe because `filter_to_uids` preserves file identity and `scope()` is the identity when nothing
> narrows, so every change is a literal no-op unfiltered. Mutation **5/5 by name**; the standing
> computed census guard separately proven to fire against the real tree **2/2 by name**.
>
> ## Next — the audit is STILL NOT finished
> **The route × test gap-fill.** The re-derivation WAS attempted: a third independent instrument
> **confirms 137 routes** (65 page · 34 api · 38 export) but gives **7 no-success / 66 no-failure**
> against the ledger's 5 / 16. **Do not bank 7/66** — it only counts a literal `status_code == 4xx`
> as a failure assertion, so a failure test asserting on an error body is invisible to it; and its
> first version over-reported 39/73 until a method-blind resolver bug was found. **The route
> population is settled; the coverage gap is UNVERIFIED in both directions** and needs a better
> oracle before anyone fills it. · **never audited at all: page modules A/B
> · docs/config/CI · AI figure-gates** · the remaining REPORTED rows: CPM-01..04 · MF-03/04/06..10 ·
> MC-02..08 · `ASK-UNRESTRICTED-WRONG-VERSION` · `ISDIGIT-INT-500` · IMP-02..06 · MAN-01..03 ·
> REC-02 · JS-02..06. **MF-05 stays do-not-fix-blind** (needs the Acumen export as oracle).
>
> ## Carried forward
> ADR-0353..0420 closed — do not re-open. NEW lessons: **a ledger row naming N surfaces may be
> naming N instances of a CLASS** — a computed census turned "three MIXED-POPULATION rows" into
> eight sites, and the three named ones were not the worst (the AI fact sheet was) · **a test that
> re-derives what the route SHOULD compute cannot fail** — this session's export test passed
> against the broken route until it was repointed at the shipped workbook bytes · **a red for the
> wrong reason is not a red** — that same test's first failure was a `StopIteration` from a
> mis-cased label, and only the mutant proved it now fails on the assertion · **"is it reachable?"
> is a separate measurement from "is it wrong?"** — IMP-01 is genuinely wrong and genuinely
> unreachable from the whole corpus, and saying only one of those would misinform. Standing traps
> unchanged (a count may be counting the symptom · an oracle giving the same verdict in both worlds
> is BLIND · compute a call-site list, never hand-maintain it · never measure a tree a battery is
> mutating · monkeypatch per CALL SITE · `python -m ruff` · **`| tail` masks exit codes** — paid
> AGAIN this session, a piped web-suite run buffered to 0 bytes for 20 min · fetch before numbering
> AND committing). QC-1/QC-2 are ADR-0393.
>
> ## Gate at close
> Statics green whole-tree (ruff/format/mypy/bandit/node). Parity **72 passed**. Full suite in a
> detached worktree: **4243 passed / 1 failed / 5 skipped (27:52)** — the 5 skips are pre-existing,
> and the 1 failure is a **sandbox artifact**, diagnosed in both worlds rather than waved away:
> ADR-0148's `test_embedded_wheel_is_in_lockstep_with_the_source_tree` fired because that worktree
> held patched `src` against HEAD's installers. In the live tree (wheel + nine installers rebuilt
> for v1.0.212) `tests/installer` + `tests/test_packaging.py` are **68 passed**.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
