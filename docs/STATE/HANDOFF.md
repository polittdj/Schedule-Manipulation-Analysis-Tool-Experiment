# Handoff — 2026-08-13 (the Ask panel could not see the workbook; ADR-0392; v1.0.200)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-gateway-handoff-ggy2h9`,
> branched from `main` **a19b969** (#579 squash-merged; `git fetch --prune` + `checkout -B`, per
> the post-squash-merge rule). Highest ADR **0392**. Version **v1.0.199 → v1.0.200**; wheel + nine
> installers rebuilt. SCHEMA stays 2.11.0.
>
> This was an **operator-reported defect session**, not the planned Band-1 gateway work. Band 1
> (001a/001b/001c) is **untouched and still first in the queue** — see below.
>
> ## WHAT THE OPERATOR REPORTED
> They loaded **31 `.mpp` versions of one project** and asked the Ask panel to read the S-curve
> across all 31 and say whether the project is improving. The model answered that it could see
> "**only two file versions, not 31**" and "**no cumulative-progress time series**". Two more asks
> rode with it: remove the question-box character limit, and make the results exportable to Excel.
>
> ## THE DIAGNOSIS — the model was right about its evidence
> Measured before any change, on a synthetic 31-version workbook through the exact
> `build_workbook_fact_sheet` path `POST /api/ask` takes:
>
> | measure | value |
> |---|--:|
> | versions loaded | 31 |
> | facts produced | 23 |
> | facts naming **more than one** version | **1** |
> | facts carrying a per-version series of any kind | **0** |
> | facts stating the loaded-version count | **0** |
>
> The one multi-version fact was the briefing's *"How to Verify Every Number"* boilerplate, which
> lists the file names inside a verification **procedure**, not as data. Everything substantive came
> from `build_briefing` (subject = NEWEST version) and `detect_manipulation` /
> `compute_path_counterfactual` (explicitly the latest PAIR). So "two file versions, no
> cumulative-progress series" was an **accurate description of the evidence**, not a hallucination.
> The files were loaded, parsed and solved throughout — the panel simply never said they existed.
> The S-curve was never missing either: `engine/s_curve.py` has computed per-version curves since
> `/scurve` shipped. **Nothing routed them to the Q&A.**
>
> ## SHIPPED (ADR-0392)
> * **`engine/version_series.py`** (new) — every loaded version as one comparable row: its S-curve
>   point at ITS OWN data date + its schedule-logic finish (CPM), plus the mechanical first→last gap
>   movement and per-step narrowed/widened/unchanged counts.
> * **`ai/version_facts.py`** (new) — four cited facts (population + S-curve series + trend verdict
>   + finish series), inserted into `build_workbook_fact_sheet` right behind the frame fact.
> * **`CitedStatement.pinned`** — `relevant_facts`/`model_evidence` rank by question overlap and cut
>   at a cap (12 shown / 48 to the model). Right for evidence, WRONG for the population frame: a
>   question phrased without the series facts' words could rank them out and reintroduce the exact
>   defect. Pinned facts ride ahead of the ranked evidence and are never cut. Nothing else reads the
>   flag — not the citation gate, not the figure gate, not the role gate.
> * **No question length limit** — both `question.strip()[:500]` truncations and `maxlength=500` are
>   gone; the input is a textarea (Enter sends, Shift+Enter newlines). No replacement cap: a silent
>   truncation the operator cannot see is the defect class being closed. Empty-question 422 unchanged.
> * **`GET /export/{fmt}/ask`** — three sheets (Answer / Cited facts / Citations), xlsx + docx, off
>   `SessionState.last_ask`. `⤓ EXCEL` / `⤓ WORD` hidden until an answer exists (never a dead link);
>   the driving-path result records the same way. With no live model the Answer cell **states why**
>   it is empty. Wiped by `SessionState.reset()`.
>
> ## THE ONE THING TO KNOW IF YOU TOUCH THE SERIES
> `compute_version_series` **recomputes** each version's S-curve point instead of reading it off
> `compute_s_curve`. That is deliberate: the animated curve shares one month axis capped at 60
> months and sheds the oldest months on a long programme, so a version whose data date lands in a
> shed month has `status_index is None` — with 31 monthly updates over a multi-year programme the
> early versions silently vanish from any series read off that axis. Evaluating at each version's own
> data-date month needs no shared axis. The two paths are **required to agree** wherever the animated
> curve is readable (`_cumulative_pct` folds pre-window finishes into its running count, so the value
> at a month is independent of where the axis starts), and
> `test_matches_the_s_curve_at_every_on_axis_status_month` pins it — **mutation-proved** (`<=` → `<`
> fails it). Two evaluation paths, ONE definition of "the S-curve"; the alternative is the page and
> the fact base quoting different numbers for the same curve.
>
> That test also caught its own **vacuity first**: the synthetic data dates sat outside golden
> Project5's own window (2026-03 → 2028-01), so every version was off-axis and the equivalence loop
> iterated ZERO times. The `compared >= 2` guard is the only reason that surfaced.
>
> ## VERIFIED, NOT ASSUMED
> Full gate green (ruff whole tree, ruff format, mypy strict 151 files, bandit exit 0, node --check
> all vendored JS), and `pytest -m parity` green (52 passed). New tests, counted by collection:
> `tests/engine/test_version_series.py` (14), `tests/ai/test_version_facts.py` (12),
> `tests/web/test_ask_panel.py` (13) = **39**. **Five mutations run and reverted** to prove they can
> fail: cumulative `<=`→`<`; series facts not inserted; pinning disabled in both selectors; the
> exchange not recorded; the empty population reporting 0.0 instead of unreadable.
> `tests/guards/render_oracle_labels.txt` regenerated — +14 labels, exactly the two new routes
> across seven stages, nothing else moved.
>
> ## NEXT — Band 1 is still first, in dependency order
> **001a** pin `net_guard._LOOPBACK_HOSTNAMES` contents + mutation proof (land FIRST, alone) →
> **001b** observed (not config-derived) banner → **001c** the operator's cloud/gateway decision,
> then ADR-0393. Read `docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md` before starting: POLARIS is in use
> against `https://proxy.fast.luna.nasa.gov` on the operator's Windows machine via a local patch that
> exists nowhere in this repo. Then the audit's other confirmed items: `actual_start_driven` computed
> but consumed nowhere · ADR-0391's own-calendar floor branch behaviorally unguarded · `mpxj_ref()`
> shallow-clone guard (DoD 117, FIRED) · the pre-commit guard has no image detector (120 tracked
> PNGs) · 22 playwright modules hard-pin a chromium BUILD NUMBER · FINAL-REPORT's parity and
> no-egress cells overclaim · 8 stale remote branches (DoD 091).
> **Operator:** the 001c decision · FX-03/04 re-run · the sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0392 closed — do not re-open. NEW lessons: (1) **a model that says "I only see two
> files" may be reporting a fact about its evidence** — read the prompt before blaming the answer;
> (2) **a capability the TOOL has is not a capability the AI has** — the S-curve was computed per
> version for months and no test could notice it never reached the panel, because every test asserted
> on what was there, not on what was missing; (3) **relevance ranking will drop the frame** — any
> overlap-ranked selector eventually ranks out the fact that defines the population, and the answer
> is then confidently scoped to the wrong universe; (4) **silent truncation is the defect, not the
> limit** — the 500-char question cut and the two-version evidence are the same failure. Standing
> traps unchanged (a guard is only as strong as the test that pins its DATA · an architecture that
> offers no legitimate path to a real need will get the dangerous path taken · a claim derived from
> CONFIG describes intent, not behaviour · verify the SCOPE of a doc-truth finding · a fixture
> generated by a rule cannot validate that rule · the corroborating oracle may already be in a doc
> nothing cross-references · an ADR's observation can be right and its diagnosis wrong · a new
> disclosure needs its own channel when the existing one carries a JUDGEMENT · a sweep's
> glob/population/pattern are part of its claim · `| head -N` can SIGPIPE-kill a build mid-way · the
> MPXJ pin drifts in a shallow clone · never MEASURE a tree a battery is mutating · never MUTATE an
> instrument a measurement is using · monkeypatch repoint is per CALL SITE · `grep -c` exits 1 on
> zero · two ruffs on PATH, use `python -m ruff` · bare `pytest` does not prepend CWD ·
> `pytest -m parity` alone exceeds 900 s · the container starts with NO deps installed ·
> `git fetch origin` before taking an ADR number and again before committing). A number written
> mid-session is not a measurement (`wc` decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
