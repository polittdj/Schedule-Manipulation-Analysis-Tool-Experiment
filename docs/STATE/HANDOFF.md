# Handoff — 2026-08-06 (ADR-0355: four Codex findings on the literal fix, all confirmed, all hardened; v1.0.170)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0355, **v1.0.170**, SCHEMA 2.11.0.
> The operator relayed four Codex review comments on merged #545 (ADR-0354); ALL FOUR verified
> real and fixed the same session: **C1** the literal day scale is the DECLARED
> `Project/MinutesPerDay` SETTING, not the calendar's derived day length (new
> `Calendar.declared_minutes_per_day`, absent → MPXJ's 480 — the absent-property fallback for
> `d`/`mo` deliberately CHANGED from derived to 480); **C2** `selection_migration_delta` now
> takes RAW prompt answers and coerces under EACH parser inside the ContextVar scope, so
> prompt-only movement surfaces (pinned: `((1,), ())` on a 1,500-min border task); **C3** the
> importer sanitizes non-positive duration-scale properties BEFORE `model_copy` (which bypasses
> `gt=0`); **C4** ADR-0354's "fails closed" was HALF-TRUE — `None` rides the null-ordering
> rules, so `Duration < 5xyz` / `!= 5xyz` matched EVERY task; a `_Malformed` sentinel now fails
> any touching leaf on every operator, `EQUALS <null>` untouched. Wheel + nine installers at
> **v1.0.170**.
>
> ## THE DISCRIMINATOR LESSON FIRED A THIRD TIME IN ONE DAY
> C1's end-to-end pin PASSED under its own mutation — the population made the 480 and 600
> thresholds select identically. A 600-minute discriminator task fixed it. Three scales in one
> day: a whole SUITE of identity fixtures (ADR-0353), one test's identity CALENDAR (ADR-0354),
> one test's identity POPULATION (here). The question is always: do the fixtures make the two
> readings equal by construction? **Run the mutation BEFORE trusting any new pin.**
>
> ## OPEN — the 1440 boundary (last ADR-0240 reserved item) WAITS ON THE OPERATOR'S FILE
> The operator is supplying a reference `.mpp` with tasks on a 24-hour calendar. When it
> arrives: convert via MPXJ, read MS PROJECT'S OWN stored Start/Finish spellings at whole-day
> boundaries (the corpus's `_24h` files are off-boundary — 17:00/09:00 anchors, weekend-working
> calendars — measured, insufficient), then either bless current next-midnight rendering as
> MSP-conformant or build the finish-spelling mirror of `offset_to_start_datetime`. Current
> measured behavior: EVERY whole-day finish on a midnight-anchored 24h Mon-Fri calendar renders
> as next-day 00:00 ("end of Friday" = Sat 00:00); starts already correct; inverse property
> intact; no committed schedule reaches it. Do NOT repair toward the intuitive 23:59 without
> the oracle — MSP may match current behavior and the "fix" would CREATE the parity break.
>
> ## Next
> The 1440 unit on the operator's file · twelve page families (`integrity` 402 first, per
> ADR-0350/0351/0352 rules) · a driving-corridor fixture · the three `page-lede`-less pages ·
> `/groups` "Activities" counting summary rows (ADR-0343) · nine installers vs
> `-c constraints/known-good.txt` · Phase 6 docs. **Operator only:** license ·
> branch-protection contexts · intake re-upload · proprietary-tool reruns · OR-04 · the 24h
> reference `.mpp` upload.
>
> ## Carried forward
> ADR-0353/0354/0355 closed — do not re-open. `%`/`e%` pass-through, the 364-day elapsed year,
> and (new) the 480 absent-property day default are MPXJ's OWN behaviour — do NOT "fix" toward
> intuition. **DATE literals still share C4's None shape** (pre-existing, recorded in ADR-0355,
> deliberately not expanded into this unit — a future unit needs its own adjudication).
> EVALUATOR_VERSION stays 2 (corrections to an unexposed v2, not a v3). The `/analysis`
> focus→tip family is load-sensitive — do NOT chase. `pydantic>=2` is NOT a safe floor (2.6
> is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2 floor). Run `ruff check .` — WHOLE
> tree — as `python -m ruff`. Never `git checkout` to undo a mutation — `cp` from scratchpad.
> `grep -c` exits 1 on zero count — chain absence checks with `;`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
