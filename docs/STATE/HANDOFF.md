# Handoff — 2026-08-07 (phase 3 slice 5: the margin family out of the monolith; ADR-0363; v1.0.174)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0363, **v1.0.174** (shipped code changed:
> `app.py`, `components.py`, new `web/margin.py` — wheel + nine installers REBUILT after the
> bump), SCHEMA 2.11.0. The standing queue's first line resumed: phase 3 monolith split,
> `margin`.
>
> ## ADR-0363 — phase 3 slice 5: /margin out of the monolith, first fully-covered render diff
> The stale "margin 379" census was RE-MEASURED first: the behaviour-seeded closure gives
> 19 names / 494 lines partitioned THREE ways by referrers — a 10-name / 417-line CLOSED move
> set (every external referrer `create_app`) into **`web/margin.py`** (490 lines with
> preamble); a 2-family trio (`_HB` / `_HB_MARGIN_SEC` / `_margin_terminology`) DESCENDED into
> `components.py` (shared with `_margin_panel`, which is the /analysis family's and stays —
> the ADR-0351 first-slice-forces-the-descent rule); and the SRA-side names untouched (only
> the create_app-nested `_margin_risk_data` reaches them). `_HB_CONSUME_SEC` stays in app.py:
> dead constant, no closure claims it (adjacency is not cohesion). `app.py` 18,134 → 17,681.
> LAYER_ORDER … → integrity → **margin** → app. Proof: 13/13 per-definition byte-identity;
> multiset 60 added / 0 removed (preamble + re-exports + descent comment only — even the five
> ruff-dropped app.py imports cancel against margin.py's); **76/76 routes byte-identical** on
> the golden-pair oracle. First slice where the probe covers the WHOLE family: the oracle
> gained `POST /margin/band` (else `_band_payload` returns None on line one) and the
> instantiated `/export/{xlsx,docx}/margin` (proven deterministic — and the ONLY path that
> executes `_wmpd_label`: 0 moved without them, 2 with). Falsified in BOTH new modules, both
> EXACT vs the pre-flight map. All three sweeps empty WITH a self-test (harness first found
> the 4 known drvmod/evomod sites). Five guard mutations red→restored (md5-verified, cp never
> git checkout); the enumeration guard's fourth consecutive live catch.
>
> ## Next
> Phase 3 resumes at **trend 348** (stale census — RE-MEASURE the closure first; this slice's
> "379" measured as 417+21 split three ways). Then: driving-corridor fixture · the three
> page-lede-less pages (/briefing, /path, /compare) · /groups Activities counting summary rows
> (ADR-0343) · installers vs known-good constraints · the P80/P90 recurring-calendar-exception
> residual (own unit) · Phase 6 docs. Battery future-work: a stored-slack fixture would let
> `cei_critical` leave NA. **Operator:** license · branch-protection · proprietary reruns ·
> OR-04 · whether the July mpp/ oracle should re-export under replace semantics.
>
> ## Carried forward
> ADR-0353..0362 closed — do not re-open. The slice recipe held for its fifth outing:
> behaviour-seeded closure (the prefix finds, the closure DEFINES — and here it also
> partitions) · span-scoped pre-flight probe BEFORE quoting any render diff (widen the oracle
> when a member's only consumer is an export or a POST-lit branch) · verbatim cut + `X as X`
> re-exports · contract/guard widening · the three sweeps (empty is evidence only with a
> self-test) · per-definition byte-identity + multiset + falsified render diff · five guard
> mutations restored from scratchpad cp. A number written mid-session is not a measurement —
> the 17,688 in the draft ADR was pre-`ruff --fix`; wc says 17,681 (caught by the re-read
> rule). The workbook Mean/StdDev cells are UNWEIGHTED. A parity delta is a claim about INPUTS
> first. `pydantic>=2` NOT a safe floor (2.6); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2
> floor). `ruff check .` whole tree as `python -m ruff` (a stale 0.15.8 shadows PATH). `grep
> -c` exits 1 on zero — chain with `;`. The /analysis focus→tip family is load-sensitive — do
> NOT chase. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not
> SQL)`. Full suite > 10-min foreground timeout — run `python -u` in background and READ the
> tail; never mutate the tree (docs included — test_state_docs reads them) while it runs.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
