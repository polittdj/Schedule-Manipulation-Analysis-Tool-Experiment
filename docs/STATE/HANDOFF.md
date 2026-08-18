# Handoff — 2026-08-18 (a) (design handoff: Chapter 04's stability band; ADR-0427; v1.0.216 shipped)

> ## STATUS (current) — Chapter 04 now looks like the prototype.
> Highest ADR **0427**. **SHIPPED code changed** (`web/evolution.py`, `web/app.py`,
> `static/app.css`) — **v1.0.215 → v1.0.216**, SCHEMA unchanged, wheel + nine installers rebuilt.
> Third slice from the Claude Design bundle. The audit ledger and its open rows are untouched.
>
> ## What landed — ADR-0427
> `/evolution` (Chapter 04 · How stable is the path) gains the prototype's panels **① Stability
> signal · ② Flow of the path · ③ Membership matrix · ④ Transition ribbons** above its existing
> Gantt + what-if ledger (⑤), driven by one version cursor.
>
> **Reuse, not reimplementation.** The band is drawn from `_volatility_data` and mounts
> `volatility.js`'s OWN chart hosts — that module returns early on a missing host in all eight
> draw functions, so mounting four of eleven is supported. A test compares the two pages' embedded
> datasets **byte for byte**; both render the same 78% mean carry-over on the 4-version fixture.
> `/volatility` is completely unchanged.
>
> **Two populations, each labelled.** The band is ALL-VERSION; the panels below are PAIR-scoped
> (ADR-0371). That is ADR-0420's hazard shape, so every band takeaway carries
> `across all N loaded versions` and a guard fails if the phrase goes missing. Note the page
> already carried both scopes (its h1 said "Across 4 versions" above pair panels) — this makes an
> existing duality explicit rather than creating one. `DESIGN-SYSTEM.md` §7b now states the rule.
>
> ## Three things worth reading before the next UI slice
> - **A surviving mutant is not always a weak test.** M3 survived because the precondition sat at
>   a call site that is unreachable (`/evolution` returns its own empty state first) — dead code
>   with a test pointed at the wrong subject. Moving the guard INTO the function fixed both.
> - **`chartframe.js` wraps every `.chart-host` in a zoom container.** A flex rule aimed at
>   `.chart-host` targets an element that is no longer the flex child — three flex settings failed
>   to move a chart off 300px before that was understood. Use a block layout, or target the wrapper.
> - **Chart tick text is sized in CSS px and does NOT scale with the SVG.** A narrow host makes
>   labels proportionally larger; the same chart is clean at 566px and collides at 300px.
>
> ## Carried forward
> Design gaps still open: **Metric Lab** (lowest effort) · **Segment Forecast** as a page ·
> **Portfolio at Scale** · **Beyond the Schedule** · **Trend Lab + Manipulation Watch** ·
> **PDF export** · **GUIDE ME** · **SHOW UIDs** · the **MERLIN wordmark** (operator decision).
> The audit's open rows are unchanged. ADR-0353..0427 closed.
>
> ## Gate at close
> `ruff check .` · `ruff format --check` 562 files · `mypy src/` strict 158 files · `bandit` exit 0
> · `node --check` per file. Full suite **4345 passed / 5 skipped / 0 failed / 39:20**.
>
> The first run had **7 failures, all MINE**: the wheel lockstep (src edited after the build), two
> monolith-split contract rows (`_CH04_NUMERALS` un-re-exported; `evolution` importing `volatility`
> UPWARD), and four `test_r11_panel_contract` pins that legitimately moved. The upward import is
> the one worth noting — `_volatility_data` descended into `components.py` per ADR-0351's rule.
> `bandit` also failed honestly once: B608 matched my HTML prose ("per **update** … operator-**set**")
> as SQL. Reworded rather than suppressed.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
