# Handoff — 2026-09-25 (b) (the launcher's relocation notice names the port it tried, never "port None" (ADR-0534) — **v1.0.294**)

STATUS (current) — branch **`claude/determined-cray-beuym5`**, restarted with `--prune` on `main` @ **`6bc3138b`** (#718, ADR-0532 / 0533, v1.0.293) after the operator squash-merged PR #718 on 2026-09-25 13:04 UTC. The squash tree `b74fb3cc…` is **byte-identical** to the green PR head `b226b856`; `main`'s own runs for it read green (CI #1996 success, installer-smoke #830 success). A new draft PR carries this unit (the operator merges; never marked ready here). `src/` changed (`launcher.py`): wheel + nine installers rebuilt LAST, so **EIGHT checks**. Highest ADR **0534**. Version **1.0.294**. Schema **2.17.0** (unchanged). QC-1 / QC-2 / QC-3 bind every session.

## What landed — the "launcher wart" from the kickoff's also-open list, measured first

**The claim was half right.** A probe of the pristine `launcher.main` with a claim that refuses the first port: on the **console entry point** (`schedule-forensics` / `python -m schedule_forensics`, both `main()` with no port) the notice read **"port None was busy and would not release"** — it interpolated the caller's argument instead of the port it tried. On the **desktop icon** (all nine installers launch `pythonw … main(port=8321)`) the text was already correct (8321), but it goes to the devnull sink `_ensure_streams` installs, so nobody sees it. Fix: `tried_port = chosen_port` recorded before `resolve_port`, printed by the notice. Test `test_the_relocation_notice_names_the_port_that_was_actually_tried` (console + icon twin): red-first on the console case with the verbatim "port None", icon twin green; mutant (capture after the relocation) red on both; module 16 / 16. QC-3: 4 assumptions, 1 fell (L2 — the icon's defect is visibility, not content).

## Not done (measured, left) · carried forward

**The icon-path visibility** — under `pythonw` the relocation notice and both log lines reach no one; the browser still opens on the live port, so nothing dead-ends, but a stale 8321 bookmark gives no warning. Surfacing it in the page is a UI decision (banner, wording, design-system placement) — open, not taken. Everything in the prior handoff's list is unchanged: R-68 (operator's MS Project reading) · the raw-flag question (ADR-0531) · R-21 (the last priced OPEN row; its criterion needs a named sequence and box) · R-71's clamp (UID 187) · R-32's product finding (the 60-day extension on open) · DCMA-13's pure-branch min · the STAT row's every-status flag census (ADR-0533 decision 4) · the stale remote branch `test/ch04-stability-oracle` (the operator's to delete). **Gate on the final tree:** statics clean on `/usr/local/bin/ruff` 0.16.9, mypy strict, bandit exit 0, node per script; guards + installer + launcher + docs modules 511 passed / 2 skipped. **The full local suite was NOT re-run** for this one-line change — CI's test and floor jobs on the PR head are the gate; read them to conclusion.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
