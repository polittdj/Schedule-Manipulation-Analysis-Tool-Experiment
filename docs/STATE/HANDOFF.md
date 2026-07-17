# Handoff — 2026-07-17 (Session-start ritual: auto-inject the live HANDOFF + archive history; v1.0.56; highest ADR 0246)

> ## STATUS (current) — ADR-0246: the operator's standing directive "ALWAYS read the entire HANDOFF before starting a session" is now GUARANTEED and cheap — the SessionStart hook auto-injects this live STATUS/NEXT block every session, and the 76 stale prior handoffs moved to `HANDOFF-ARCHIVE.md` so HANDOFF.md itself stays small enough to read in full in one pass.
>
> - **Auto-inject (guaranteed, no reliance on memory).** `.claude/hooks/session_start.sh` now prints
>   HANDOFF.md's current section — everything above the first `# (prior)` heading — into session
>   context on BOTH `startup` and `resume`, right under the toolchain preflight. So "where we are /
>   what's NEXT" is always in front of the agent from the first turn, whether or not it remembers to
>   `Read` the file. (Hook stdout is surfaced as session context — the same channel the preflight
>   already used.)
> - **Archived history.** The 76 prior handoff sections moved verbatim (newest-first) to
>   `docs/STATE/HANDOFF-ARCHIVE.md`; the full append-only per-session history also still lives in
>   `SESSION-LOG.md`. HANDOFF.md dropped 417 KB → ~4 KB — now trivially one-`Read`-able, so "read the
>   entire HANDOFF" is finally both literal and cheap.
> - **New invariant + guard.** HANDOFF.md keeps ONLY the current section plus a single
>   `# (prior) handoffs — archived` pointer (that pointer preserves the drift-guard's boundary marker
>   for the version pin). `tests/test_state_docs.py::test_handoff_stays_one_pass_readable` fails if
>   HANDOFF.md exceeds 64 KB or carries more than one `# (prior)` heading — enforcing the small-file
>   invariant so future sessions can't silently let it grow back.
> - **Convention change (CLAUDE.md "Durable state").** Writing the next handoff now MOVES the current
>   section to the TOP of `HANDOFF-ARCHIVE.md` (demote its `# Handoff` → `# (prior) Handoff`) and
>   REPLACES the section here — no longer append-a-new-`# (prior)`-in-place. The drift guard
>   (highest-ADR-in-both-docs, version-in-top-section) is unchanged and still enforced.
> - **State:** v1.0.56 unchanged — docs + hook + one test only, **no `src/` change**, so the wheel /
>   9 installers stay in lockstep (no rebuild); **ADR-0246**; full gate green.
> - **NEXT (audit remainder from ADR-0245, then the queue — none of the 5 is a live leak/parity
>   break):** (1) `/driving-path` corridor Gantt not per-task shaded — the #382 wiring gap:
>   `driving_path.js` reads an `a.calendar` the server never emits (add the field + pass the per-row
>   calendar to the shading, OR drop the dead read and correct the #382/ADR-0243 "wired" claim);
>   (2) a Gantt-shading node harness (the #382 shading JS is behaviorally untested — model on
>   `tests/web/js/*.mjs`); (3) a `/margin` mixed-basis view test (the erosion-suppression disclosure
>   text/export row is untested); (4) an SRA-xlsx zip-bomb size cap (the re-import route fully
>   decompresses with no cap — parity with `/upload`'s 500 MB limit); (5) a spaced-UNC-path
>   trailing-filename leak in `redact()` (a subtle regex edge). Then **PR-P1** validated perf items
>   (CoPilot #3/#4/#8/#9/#10 + the audit-E summary-logic edge guard; the refuted claims
>   #1/#5/#6/#7-race are documented — do NOT "fix" them) → #13 XER per-task calendars → base-CPM
>   single-calendar fail-soft disclosure (#26) → F3c parameterized expected margin → roles front-end
>   (v4 F4). Operator-side (no code): apply the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the
>   GitHub web UI + the §4 root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
