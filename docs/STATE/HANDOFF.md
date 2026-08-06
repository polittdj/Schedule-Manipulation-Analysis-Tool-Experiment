# Handoff — 2026-08-06 (Phase 3 slice 4: the integrity family is out of the monolith; ADR-0358; v1.0.172)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0358, **v1.0.172**, SCHEMA 2.11.0.
> Phase 3 slice 4 landed: the /integrity page family (`_integrity_header` + `_integrity_body`,
> 2 names / 402 lines) moved VERBATIM into **`web/integrity.py`** (446 lines). `app.py` 18,311
> → 17,910. `LAYER_ORDER` = state → chrome → components → driving → evolution → integrity →
> app. Behaviour-seeded closure == the prefix pair exactly; sole external referrer
> `create_app`; NOTHING descended into components (first slice where the pair-descent rule had
> no work). One import moved with the code (`change_effects` — ruff dropped it from app.py, the
> preamble carries it verbatim, multiset shows it in neither direction).
> **Proof:** per-definition byte-identity 2/2 (2,654 + 19,996 B) · multiset 38 added / 0
> removed (all preamble + re-export block) · **79/79 routes byte-identical** on TWO oracles ·
> oracle FALSIFIED (one char in the moved body moves exactly the six /integrity pages).
> **Pre-flight probe (ADR-0352's method, span-scoped): both members render — 6 routes each.**
> First slice where the render diff covers the whole family (driving covered 0, evolution left
> 2 members dark). Oracle B is new and worth keeping: TP4_DataCenter v1..v5 loaded as one
> project renders /integrity five ways (n>2 picker, both non-empty verdict bands, the
> order-normalisation and out-of-range re-pick branches). Named gap: the `artifact-cluster`
> collapsible (SNET-at-data-date reschedule artifacts) renders on NO fixture — guarded by
> byte-identity only, like evolution's counterfactual pair.
> **All three standing sweeps ran and came back EMPTY** (monkeypatch over all 18 bound names,
> alias-aware; source-text readers — every subject stayed put, `_TS_CAPTION_MARK` still 5 in
> app.py; attribute-reads of the two names app.py no longer binds). First slice with zero test
> repointing. Five guard mutations all fail/restore-green (dropped re-export · deferred upward
> import · narrowed enumeration tuple · planted `&mdash;` sentinel · planted second
> drilldown.js include).
>
> ## Absorbed in passing — the 24h oracle is now COMMITTED intake
> Main's `d0b703e` (operator web upload, 2026-08-06 13:06) committed
> `00_REFERENCE_INTAKE/mpp/24Hour Calendar.mpp` — the ADR-0357 oracle, previously "NOT
> committed (operator's call)"; the call has been exercised. The ADR-0347 census guard caught
> it in this session's full gate (4 red intake tests on an untouched intake). Absorbed:
> classifier-verified `ole2-project`, NO mismatch; manifest regenerated (407 files / 21 mpp /
> mismatches still 99); the 20→21 pin carries the provenance; CLAUDE.md census updated. The
> ADR-0357 boundary pin can now run against committed intake in a future unit if wanted.
>
> ## The trap that fired THIS session (and the harness caught it)
> The span-scoped probe's first header mutation was `page-takeaway` → `page-takeawayQ` — a
> SUFFIXED replacement, ADR-0351's substring trap in the probe's OWN tooling. The harness's
> assert-ORIGINAL-anchor-absent check (written in because of ADR-0351) refused it before any
> render was trusted; the working mutation was same-length non-superstring (`page-tekeaway`).
> The rule is now proven to belong IN the harness, not just in the checklist.
>
> ## Next
> Eleven page families remain — **`margin` 379 next**, then trend 348 · ssi 335 · mission 304
> · how 290 · sra 264 · what 257 · where 235 · portfolio 231 · evm 208 · forecast 204 (counts
> are the ADR-0350 census, three slices old — RE-MEASURE the closure before cutting; ADR-0350/
> 0351/0352/0358 rules: behaviour-seeded closure, span-scoped pre-flight probe, all three
> sweeps, five mutations). Then: driving-corridor fixture (would also light /evolution's
> counterfactual and /integrity's artifact-cluster wants its own SNET fixture) · three
> `page-lede`-less pages (/briefing, /path, /compare) · `/groups` Activities counting summary
> rows (ADR-0343) · installers vs known-good constraints (62 lockstep tests, own unit) ·
> P80/P90 recurring-calendar-exception residual (own unit + oracle) · Phase 6 docs.
> **Operator:** license · branch-protection contexts · intake re-upload (optionally the
> 2026-08-06 artifacts as a second parity oracle) · proprietary reruns · OR-04 · whether R2
> belongs in both SSI and tool runs.
>
> ## Carried forward
> ADR-0353/0354/0355/0356/0357 closed — do not re-open (SRA legacy anchor · MPXJ literal
> conformance · Codex hardenings · stale-setup exoneration + /sra/load-from-schedule · 1440
> next-midnight IS the MSP convention). Phase-3 recipe: monkeypatch sweep covers names the
> module BINDS (imported or defined) + `__file__`/getsource reads + attribute READS; render
> diff is only evidence AFTER the pre-flight probe says the family renders; assert the
> original anchor ABSENT after every mutation. `pydantic>=2` NOT a safe floor (2.6);
> `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2). `ruff check .` whole tree as
> `python -m ruff`. Never `git checkout` to undo a mutation — `cp` from scratchpad.
> `grep -c` exits 1 on zero — chain with `;`. The `/analysis` focus→tip family is
> load-sensitive — do NOT chase. bandit B608 on HTML f-strings with "from" → house
> `# nosec B608 (HTML, not SQL)`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
