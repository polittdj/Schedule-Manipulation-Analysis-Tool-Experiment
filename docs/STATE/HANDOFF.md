# Handoff — 2026-07-29 (an absent figure is not a zero; ADR-0306; v1.0.122)

> ## STATUS (current) — **NOTHING IN FLIGHT.** The falsy-zero correctness pass MERGED as **#479** (`6e5761f`). Version **1.0.122**, wheel + nine installers regenerated. Highest ADR **ADR-0306**. Redesign tail rank 12 (the Library/Setup sweep — `/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`, `/wbs/{name}`) is **still next**: this round was an out-of-band correctness fix, not a UI round, so the tail queue is untouched.
>
> ### What happened
> An outside auditor (ChatGPT Codex) reported seven defects at `9a1e560`. An adversarial verification
> pass re-ran all seven **by execution**, swept the repo for the same idiom (67 sites), and opened the
> five engine modules the outside audit never read. Evidence lives in four committed files:
> `audit/VALIDATION-20260729.md`, `audit/FALSY-ZERO-SWEEP-20260729.md`, `audit/CC-FINDINGS-20260729.md`,
> `audit/LAW2-IMPACT-20260729.md`. **All scripts and their verbatim output are quoted in those files.**
>
> ### Verdicts on the seven (nothing taken on trust)
> V1 CONFIRMED · V2 CONFIRMED · V3 CONFIRMED-in-substance (its "contradicts the docstring" framing is an
> overstatement) · V4 CONFIRMED · V5 **PARTIAL** · V6 CONFIRMED · V7 CONFIRMED.
>
> **The pass corrected itself twice, and both corrections matter more than the verdicts:**
> - **V5** — an adversarial verifier refuted the lead's own first reading. Removing the `or 1.0` on
>   `resources.py:171` *alone* makes reported over-allocation **worse**: the zero-capacity bucket it
>   produces is then skipped by `over_allocated`'s `capacity_minutes > 0` guard, and a real flag flips
>   `True → False`. **The two lines are one decision.**
> - **V6** — a verifier's refutation was itself wrong. Its 5,000-trial probe varied calendars and
>   offsets but **not the project start's time of day**, so it concluded a reachable case was
>   unreachable. Direct probe: **8 of 120 (start-hour, offset) pairs land on a Saturday.** The lead's
>   three end-to-end reproductions stood.
>
> ### Shipped in ADR-0306 (five changes, 13 regression tests)
> 1. **`engine/manipulation.py` (CC-02 — the big one).** `(cur.actual_cost or 0.0) < (prior.actual_cost or 0.0)`
>    read a **dropped export column** as a rollback. An update that merely stopped carrying Actual Cost
>    produced four findings, **two HIGH**, telling the analyst to investigate *"expenditure being hidden
>    or moved"* — byte-identical to a real rollback. Both snapshots must now carry the figure.
>    **This is not a wrong number, it is a wrong allegation**, in the one module whose output accuses.
> 2 + 3. **`engine/resources.py` (V5 + V6, together).** A declared `max_units = 0.0` is preserved
>    instead of coerced to 1.0, and `over_allocated` no longer requires `capacity_minutes > 0`, so work
>    booked against **no** capacity is finally reported.
> 4. **`importers/json_schedule.py` (V7).** `hours_per_day: 0` / `work_weekdays: []` now reach
>    `Calendar`'s own fail-closed validators instead of being guessed. An **absent** key still defaults;
>    only a **provided** malformed value fails. Ends the contradiction where `working_minutes_per_day: 0`
>    raised but `hours_per_day: 0` quietly became 480.
> 5. **`importers/mspdi.py` + `xer.py` (V4).** An *unresolvable* project calendar now logs a specific
>    warning (it only ever logged the *unreadable* case). The Law-2 tolerance posture is unchanged —
>    the 8h/Mon-Fri default still applies, it is just no longer silent.
>
> ### Law 2 status
> **`pytest -m parity` green — no golden moved.** Full suite 2929 passed / 24 skipped (all skips are the
> deliberate playwright gate). No displayed number moves on a well-formed schedule; every defect needs a
> malformed or incomplete input. ruff · ruff format · mypy --strict · bandit (exit 0) · node --check all clean.
>
> ### ⚠️ NEXT — four findings deliberately NOT fixed (documented in ADR-0306, do not "just patch" them)
> - **CC-01 (HIGH) — `offset_to_datetime` returns non-working dates** (`cpm.py:255-281`). Fixes a working
>   *date*, then adds the intraday remainder in *minutes*, crossing midnight onto a weekend. **74 call
>   sites**; it is the **root cause of the V6 hard case**; a 20h/24h calendar reaches it from an ordinary
>   08:00 start. Needs a **Fable 5 Max** deep dive on the CPM date machinery — the fix is a design
>   decision about the function's unenforced precondition, not an edit.
> - **CC-05 — negative sub-day slack** (`driving_slack.py:172`). `//` floors, so `+479` min of float reads
>   0 days but `−479` reads `−1` day. Whether SSI floors or truncates decides code-fix vs docstring-fix;
>   the goldens carry exact day multiples so **parity cannot tell them apart**. Needs a reference compare.
> - **V3 — elapsed literals** (`msp_filters.py:60`). `"2 ed"` == `"2 d"`; the executed example moves a
>   filtered population from 2 tasks to 6. Needs a **product decision** (elapsed axis, or reject with a message).
> - **V1 / V2 — SRA magnitude entry.** A typo'd impact-days stores `0.0` **and locks it**, suppressing the
>   derivation from a valid percent; a risk on a **milestone** (`avg_rem == 0`) stores 0% so the two
>   Monte-Carlo models disagree (SSI applies 10 days, legacy applies none). Fixing it means an
>   operator-visible error → **the five standing UI requirements apply** → its own round.
>
> ### Harness notes worth keeping
> - **Run the gate as `python -m ruff`, never bare `ruff`.** A stale `/root/.local/bin/ruff` (0.15.8)
>   shadows the pip-installed one (0.16.0, what CI resolves from `ruff>=0.6`), and **ruff 0.16 formats
>   fenced ```python blocks inside Markdown** while 0.15 does not. A locally-green
>   `ruff format --check .` therefore went red on CI (#479, first run). Same trap applies to any
>   `>=`-pinned dev tool: `which -a <tool>` before trusting a green gate.
> - `[tool.ruff.format] exclude = ["audit/*.md"]` exists because of that: audit reports quote engine
>   source and pasted output **verbatim**, and letting a formatter rewrite a quotation makes the
>   evidence disagree with the code it cites. A formatter must never edit evidence.
> - This container ships **no** runtime deps. `pip install -e ".[dev]"` gets the gate running; `httpx` is
>   a declared **dev-only** dep (`pyproject.toml:80-82`) that backs `TestClient` and must never enter
>   runtime `dependencies`. `python -m build` also needs installing.
> - Full `pytest -q` here is ~9m20s. `pytest -m parity` alone is ~25s — run it first.
> - The installer lockstep test (ADR-0148) fires on ANY packaged-file change; bump `pyproject.toml`,
>   rebuild the wheel, then the nine installers, **once**, after all code edits and any reformat.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
