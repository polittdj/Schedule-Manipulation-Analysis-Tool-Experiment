# Handoff — 2026-07-19e (probabilistic-branching hardening per Codex review — #331 Hulett #8; v1.0.80; highest ADR 0273)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode". Probabilistic branching (ADR-0273, Hulett #8) shipped as **PR #415, MERGED**; then a **Codex bot review** flagged three real issues, all verified against the code and fixed in a follow-up (this PR). No new ADR (hardening of ADR-0273); v1.0.79 → 1.0.80.
>
> - **Fix 1 (Codex P1, `app.py::_apply_ssi_setup`) — branch-id collision on Save/Load:** the restore
>   set `sra_branch_seq` to the loaded COUNT, not the highest suffix, so a gapped id set (only "B3"
>   survives) → counter=1 → a later add recreates "B3", and `_augment_with_branches` keys
>   `fragnet_uids` by id → one overwrites the other → both loops modify the same fragnet (wrong tie).
>   FIX: **regenerate ids densely (B1..Bn) on load** → `sra_branch_seq == len` is collision-free.
> - **Fix 2 (Codex P2, `sra.py::_augment_with_branches`) — two branches on the SAME tie:** the first
>   consumed the FS tie, the second went inert (order-dependent). FIX: a `chain_pred` map so same-tie
>   branches **CHAIN in series** (`after → F1 → F2 → before`), each firing independently → both apply.
> - **Fix 3 (Codex P1, `app.py::_ssi_export_tables` + `_sra_report_blocks`) — export didn't disclose
>   branches:** the `/export/{fmt}/sra` call passes `branches=`, so exported percentiles are
>   branch-shifted, but the XLSX/DOCX listed only the risk register (unreproducible / Law-2 honesty
>   gap). FIX: a **"Probabilistic branches"** table (defs + outcomes) + a "Run setup" row + the DOCX
>   assumptions mention. (Also added the "Sampling" row while there.)
> - **Verified:** `tests/engine/test_sra_branching.py` (+2: same-tie chain additive; independent
>   firing → 4 finishes); `tests/web/test_sra_ssi_web.py` (+2: gapped save/load → 3 distinct ids all
>   applied; XLSX export names the branch). Full local gate green (ruff, format, mypy 116, bandit,
>   node, pytest). v1.0.79 → **1.0.80**, wheel + 9 installers in lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **Also this session:** closed **PR #413** (duplicate lessons-learned log; superseded by the
>   merged #412; stale base + ADR-0271 collision) at the operator's request.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258).
>   #13 XER per-task calendars PARKED.
> - **State:** v1.0.80; **ADR-0273** highest (no new ADR — hardening); wheel + 9 installers in
>   lockstep. Branch `claude/handoff-continuation-vistlu`. This session merged #411 (LHS) + #414
>   (tint) + #415 (branching); **#416 (branching hardening) carries this handoff and was merged by
>   the operator to close the session** — so **START HERE:** `git fetch --prune origin && git
>   checkout -B claude/handoff-continuation-vistlu origin/main` to restart the branch from the merged
>   main before any new work. (If #416 shows still-open, drive it to green/merge first.)
> - **NEXT (file-free):** Hulett **#9 conditional branching** — Alt-A/Alt-B contingency switching
>   (stick with plan A vs fall to plan B when a condition trips; report which plan wins how often).
>   It builds on #8's `_augment_with_branches` (sra.py) and is a larger design than #8;
>   **prototype-verify the switching semantics against the real compute_cpm BEFORE building** (as #8
>   did in `scratchpad/branch_verify.py`). This is the **last** non-deferred Hulett-deck item (#13
>   resource-leveled iterations is deferred/out-of-scope). If #331 has nothing else after it, the
>   file-free backlog is DONE — say so and await the 3 OWED operator inputs (ADR-0261 PowerShell
>   crash log + large dataset; ADR-0258 Claude-Design portfolio prompt). Keep the daily
>   LESSONS-LEARNED Part VIII entry every session that changes code.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
