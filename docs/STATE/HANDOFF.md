# Handoff — 2026-08-21 (two operator asks: multi-folder drop → one Project per folder; /driving-path opens on the complete schedule of ANY loaded file; ADR-0437/0438, v1.0.221)

> ## STATUS (current) — both 2026-08-21 operator asks are CLOSED on branch `claude/polaris-resume-audit-40up77` (draft PR pending merge), based on d3044bb1 (the #609 squash).
> Highest ADR now **0438**; version **1.0.221** (shipped code changed: `web/app.py`,
> `web/driving.py`, `web/path.py`, `static/home.js`); wheel + all nine installers rebuilt,
> installer suite 68/68 (lockstep green). Docs-only close PR **#609 MERGED @ d3044bb1**
> mid-session (main moved under this branch at close): the branch was restarted onto that
> squash and this rotation re-done on top of #609's final docs — its updated 2026-08-20 (d)
> section is what the archive now holds, verbatim. No conflict is left for the merger.
>
> ## Ask 1 — several folders at once, EACH its own Project (ADR-0437)
> The server already grouped per-file top folder (probed green, mutation-proved, now pinned);
> the gaps were client-side: Chromium's folder-picker DIALOG cannot multi-select
> (webkitdirectory overrides multiple — WICG entries-api #24), and a DROPPED folder never
> loaded at all (the bare directory File failed its read and was misreported as OneDrive
> online-only). home.js now captures entries SYNCHRONOUSLY in the drop handler and walks
> directories (readEntries drained until the empty batch — Chrome hands ≤100/call) into
> preread()-shaped File-likes carrying rel = "Folder/sub/file.ext", so N dropped folders land
> as N Projects through the unchanged server pipeline; loose files keep rel ''. preread() is
> byte-untouched (the ADR-0289 harness extraction window holds). Proven END TO END in chromium:
> real home.js, patched webkitGetAsEntry fakes, real fetch('/upload'), asserted on the live
> SessionState — observed RED pre-feature (only the loose file loaded), recursion-mutant RED by
> name. Dashboard copy states the contract (drop several folders; the dialog picks one).
>
> ## Ask 2 — /driving-path shows the complete schedule of ANY loaded file (ADR-0438)
> No-target state now EMBEDS the same workspace /path renders (`_path_body` + path.js — same
> columns BY CONSTRUCTION, one FIELDS table serves both; browser test asserts /driving-path's
> header row EQUALS /path's, never retyped). Its Schedule select spans every loaded key,
> preselecting the chosen file else the active project's latest. The trace form's File picker
> spans every loaded schedule too — optgrouped by Project, option value = session KEY (labels
> collide across folders), ?file= accepts key OR legacy label via _find_schedule (pinned).
> Cross-project trace resolves via cpm_scoped_for(key,…) and the tiers export carries that key.
> Workspace renders ONLY when no target is traced (panelkit single-include pinned both ways;
> the r11 absence census now names the ?target=absent branch). DELIBERATE re-baseline:
> r11 /driving-path form freeze bee3c73c…/1905 → ccd40241…/1925 (option values + select title).
> Four-theme measured render green (grid box, rows/bars, optgroups in all four).
>
> ## Traps paid for THIS session — check by name
> Reverting a mutation with `git checkout <file>` on a file carrying UNCOMMITTED feature work
> destroys the work (app.py re-applied from context; the home.js mutation used a scratch .bak —
> use that shape ALWAYS) · this remote clone is SHALLOW: the installer build refuses at the
> graft boundary (mpxj_ref) — `git fetch --unshallow` first · a new no-trace panel on
> /driving-path flips the r11 "panelkit absent" census: that census is now the ?target=absent
> branch only.
>
> ## Next
> The audit ledger stands (page modules A/B, docs/config/CI never audited; AI figure-gate
> adversarial pass; 25-route adverse gap). Operator follow-through: has the JUICE UVS .xer set
> been re-loaded on v1.0.220+? (wall should light; per-update NAME renames → Portfolio →
> Combine). Sibling degrade notes (/trend /cei /evolution /volatility /integrity) could take
> ADR-0431's other-projects tail. Insufficient-Detail V05/V06 + TP2 stay BLOCKED,
> operator-owned — do NOT re-chase.
>
> ## Gate at close
> Statics green whole-tree (ruff · format · mypy 158 files · bandit · node --check per file);
> installer suite 68/68 with the v1.0.221 wheel in all nine; full suite + parity numbers in the
> SESSION-LOG 2026-08-21 entry (recorded AFTER the runs finished, per QC-1).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
