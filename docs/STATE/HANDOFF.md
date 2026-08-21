# Handoff — 2026-08-20 (d) (the program is named POLARIS²; #607 merged and verified on the operator's PC; ADR-0436, v1.0.220)

> ## STATUS (current) — PR #607 (ADR-0431..0435, v1.0.219) MERGED @ a91fbfba and VERIFIED end-to-end on the operator's machine; the Polaris² rename shipped on top as ADR-0436 / v1.0.220.
> **CLOSE-OUT: PR #608 (the rename) MERGED @ e3b2f133 at 23:51Z, CI 7/7 green** (floor 23:12,
> both test jobs ~23:5x); the operator ended the session; the branch was reset onto the new
> main and this close-out went out as a docs-only draft PR. Nothing else is in flight.
> Highest ADR now **0436**. The operator merged #607 at 21:39Z, pulled main, re-ran
> install-tier2.ps1, and their transcript shows the WHOLE ADR-0435 loop closing: the stale
> re-run printed no version and installed 1.0.218; the fresh file printed
> "Schedule Forensics installer — v1.0.219 —" + the exactly-this-version warning and installed
> 1.0.219. The v1.0.219 close-out gate finished clean: **full suite 4408 passed / 0 failed
> (exit 0) in 27:43**; parity 72/72 (15:28); the floor-env instrument's single failure was the
> pre-fix import artifact (4287 passed otherwise) — CI's floor job went green on the same fixes.
>
> ## The rename (ADR-0436) — displayed name only, ² as a CHARACTER
> Operator: "Polaris (squared) — like to the exponent or power of 2." Displayed name is now
> **POLARIS²** (U+00B2 — survives titles, terminal banners, docx/xlsx headings and .lnk names,
> which markup cannot). The SVG wordmark gained a hand-set worm-style ² glyph
> (`brand-sup2`, stroke 8, between the S and the star; viewBox 344→382; aspect-ratio follows)
> — verified by chromium SCREENSHOT, not inspection. Renamed: every page/boot <title>, FastAPI
> title, launcher console lines, export titles + "Generated locally by POLARIS²…", installer
> banners ("Polaris² (Schedule Forensics) installer — vX.Y.Z — Tier …"), first-run READMEs,
> uninstaller strings, and the user-facing shortcuts (Windows Polaris².lnk + Start-Menu folder,
> Linux menu entries, macOS Desktop .commands) WITH legacy-name cleanup on upgrade. NOT renamed
> (the ADR's boundary): the schedule_forensics package/CLI/venv/install-dir and in-folder
> script filenames; the ASCII-encoded .cmd internals keep the old wording (² cannot survive
> `-Encoding ASCII`); docs keep the POLARIS/SMAT codename.
>
> ## Traps paid for THIS session — check by name
> `python -m build --wheel` writes dist/, but the installer generator reads dist/wheel/ —
> the lockstep test caught a stale embed TWICE today; always run the exact two-step from its
> own error message · a banner LOCATOR is part of a rename ("Schedule Forensics installer"
> found nothing after the rename — repoint the finder with the name) · ASCII-encoded artifacts
> constrain a Unicode brand (the .cmd exception) · a rename is a RENDER claim (the ² glyph is
> hand-set coordinates — screenshot it).
>
> ## Next
> The audit ledger stands untouched (page modules A/B, docs/config/CI, AI figure-gate
> adversarial pass, 25-route adverse gap). Operator follow-through: re-load the JUICE .xer set
> on the new build (wall should light; else Portfolio → Combine); sibling degrade notes
> (/trend /cei /evolution /volatility /integrity) could take ADR-0431's other-projects tail;
> Insufficient-Detail V05/V06 + TP2 stay BLOCKED on the operator's Fuse artifact (six
> hypotheses already refuted — do NOT re-chase).
>
> ## Gate at close
> Statics green whole-tree; installer suite 74/74 with the v1.0.220 wheel embedded in all nine;
> full suite + parity re-run on the renamed tree — numbers in the SESSION-LOG (d) entry.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
