# Handoff — 2026-08-20 (b) (ADR-0429 + ADR-0430 MERGED; v1.0.218 verified on the operator's PC; the stale-installer trap)

> ## STATUS (current) — nothing in flight. `origin/main` == local HEAD == `9dda7ea` (the PR #605 squash).
> Highest ADR **0430**; `pyproject` version **1.0.218**. The Starlight parity sweep — **ADR-0429**
> (two same-named metrics) and **ADR-0430** (the pattern-less calendar + stored-slack Negative Float)
> — is **merged**; `claude/multi-schedule-comparative-analysis-vmh5ei` was restarted from
> `origin/main`, its remote head auto-deleted, working tree clean. Its pre-merge section is archived
> VERBATIM — that section's STATUS still read "on `<branch>`", which is exactly the stale-kickoff
> shape this rotation exists to prevent. This close is **docs-only**: no `src/` change, so no
> bump, no wheel, no installer rebuild.
>
> ## 1. The tail — v1.0.218 reached the operator's machine, but only on the second attempt
> The operator re-ran the `install-tier2.ps1` already in their Downloads and got **1.0.148** — ~70
> versions stale — from a run that looked entirely successful (tier checks ok, venv reused, Java
> found, model ready, DONE). Root cause, read off their transcript: **each installer is a
> self-contained snapshot with the wheel base64-embedded inside it.** It installs exactly the version
> it was built from and never consults the repo; the stale file sat under the current name. Fix:
> re-download over it, then re-run —
> `Invoke-WebRequest ".../main/installer/install-tier2.ps1" -OutFile .\install-tier2.ps1`. The repo is
> **public again** (verified via the API this session), so the anonymous raw fetch works; ADR-0398's
> token-aware path was written when it was private. Operator-verified after the second run:
> `Installed schedule_forensics-1.0.218-py3-none-any.whl`, and `pip show` against the venv's own
> python → `Version: 1.0.218`.
> **Measured this session, not inferred:** the banner is
> `Write-Host "Schedule Forensics installer — $TierLabel"` — **no version**, so the one number that
> would have caught this appears only after the tier/Python/venv steps; and
> `installer/README-DISTRIBUTABLE.md` covers tiers, offline mode and the converter but has **no
> "updating an install you already have" section**. A repo test already enforces that the three tiers
> embed the *current* version — nothing tells the operator whether the installer they are *running*
> is current. **Deliberately NOT fixed here**: it regenerates all nine installers, and the session was
> being closed at the operator's request. Queued as §3(a).
>
> ## 2. Still blocked, still one artifact away — Insufficient Detail (V05/V06, and TP2's 6-vs-7)
> Fuse 5×6; the tool reads 0/4 on V05/V06 and is exact on V07–V10 — the last 2 of 54 ribbon cells.
> Six hypotheses were each refuted by measurement against committed pins (see the archived section
> for the list; do **not** re-chase the span hypotheses). **UNBLOCK = one operator artifact:** click
> the V05 "Insufficient Detail — 5" cell in the Fuse Starlight workbook (or export the ribbon to
> Excel) so the five counted activities are **NAMED**, then re-upload. The same artifact settles
> TP2's 6-vs-7.
>
> ## 3. Next
> (a) **installer version visibility** — print the embedded version in the banner + an "updating an
> existing install" section in `README-DISTRIBUTABLE.md` (§1; nine-installer regeneration, no `src/`
> change if the templates alone move — check before assuming a wheel is owed) ·
> (b) the blocked Insufficient-Detail leg (§2, operator-gated) · (c) consider pinning the ribbon
> nf/id columns in `test_ribbon._FUSE` once (b) settles · (d) the audit ledger stands and is the
> standing queue: page modules A/B and docs/config/CI (never audited), the AI figure-gate adversarial
> pass, the 25-route adverse gap · (e) reported-not-fixed: the Ask prompt uses `f.text`, never
> `f.rendered()` (belongs with (d)'s figure-gate pass).
>
> ## Gate at close
> Docs-only, so the gate was scoped to what this commit can move and that scope is stated rather than
> implied: `ruff check .` · `ruff format --check .` (it formats python inside MARKDOWN too, so it is
> not a no-op here) · `tests/test_state_docs.py` · `tests/test_standing_rules.py` · `tests/guards/`
> (the whole-tree census reads these very files). The full suite's last measured run is in the
> preceding SESSION-LOG entry; CI re-runs it on the PR.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
