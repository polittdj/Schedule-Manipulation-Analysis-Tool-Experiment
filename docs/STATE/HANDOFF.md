# Handoff — 2026-08-20 (c) (four operator asks + the stale-installer root: multi-.xer grouping, /path whole-schedule, Resources on P6, /compare picker; ADR-0431..0435, v1.0.219)

> ## STATUS (current) — the operator's four live asks (2026-08-20) are CLOSED, plus queue item 1.
> Highest ADR now **0435**. Shipped code changed (`importers/xer.py`, `engine/resources.py`,
> `web/state.py`, `web/app.py`, `web/mission.py`, `web/portfolio.py`, `web/path.py`,
> `web/driving.py`, `web/compare.py`, `web/resources.py`, `web/i18n.py`, `static/path.js`,
> `static/resources.js`, `static/app.css`), so **v1.0.218 -> 1.0.219** and the wheel + nine
> installers were rebuilt AFTER the last src edit (lockstep test green). Branch
> `claude/polaris-installer-version-h3qy0v` from `origin/main` @ 9dda7ea. Ran SOLO after four
> read-only recon agents; every finding lead-verified against the code and by executable check.
> **PR #606 (docs-only close of the parity sweep) MERGED mid-session** (main -> bb0a659); its
> docs/STATE rotation was merge-resolved INTO this branch (its "(b)" section archived, its
> SESSION-LOG/LESSONS entries kept; this kickoff supersedes its). Mid-session the operator also
> pulled main and re-ran install-tier2.ps1 — they now run v1.0.218 (up from v1.0.148); v1.0.219
> reaches them when THIS PR merges and they repeat the pull + install.
>
> ## 1. Multi-.xer Mission Control (ADR-0431) — root cause PROVEN then fixed
> Loose files group by `_norm_title(project_title)`; XER filled that from `proj_short_name` —
> P6's per-EPS-unique Project ID, renamed by every per-update copy — so N same-project `.xer`
> updates shattered into N one-version populations and every `<2` gate fired ("1 / 1"). MSPDI
> grouped because `<Title>` survives copies. Fixed three ways: XER `project_title` = root
> PROJWBS `wbs_name` (the P6 project NAME; short-name fallback; `Schedule.name` byte-stable);
> operator combine override (`POST /project/combine` + Portfolio panel — re-labels populations
> with one shared ingestion folder, the folder-beats-title lever); Mission Control's degrade
> note now counts the other-project files and names the two remedies. Cross-format grouping
> (.mpp Title == .xer project name) works and is pinned. UNVERIFIED against the operator's own
> JUICE files (not in the repo) — if their project NAMES also differ per update, combine is the
> remedy; ask them to re-load on this build.
>
> ## 2. /path (ADR-0432) — whole schedule by default; the "broken timescale" was v1.0.148
> `target<=0` returns `_whole_schedule_data` (file order, tier/slack honestly "—"); UID cell
> click (or Enter) retargets; `Dur (d)` default-on (Columns 7->8); the data date SEATS ~96px
> right of the frozen columns via a LIVE-geometry delta deferred past layout/font settling (the
> model-number version landed 280px off — columns re-measure after first paint). The
> screenshot's timescale defect DOES NOT REPRODUCE on this tree — the operator runs a v1.0.148
> install (that's ADR-0435's whole story) — and is now property-guarded in real chromium:
> header/track DD lines coincide and the top-tier bands COVER the rightmost bar
> (test_path_whole_schedule_browser.py). path.js digest re-baselined (r11).
>
> ## 3. Resources on P6 (ADR-0433) — the page was DEAD for every .xer
> XER built no `Task.resource_assignments` and read no max units -> empty state always. Now:
> RSRCRATE rate in effect at the data date (or the RSRC row's own column) -> `max_units`
> (ratio, 1.0=100%); real Assignments (at-completion hours; MATERIAL quantities are NOT hours —
> zero work minutes by design); roster = union of declared + assigned (zero rows visible);
> `max_units_declared` so the roster prints "—" for the engine's assumed 1.0 (Law 2); a 4th
> shelled panel "Utilization by resource" (peak load / OWN capacity, worst first, plain rows —
> deliberately not a .chart-host). Hand-verified in chromium: 80h vs 0.5x20wd -> 100%; 160h vs
> 2.0x20wd -> 50%. r10 contract re-baselined 3->4; the 11-line axis-caption block digest is
> UNCHANGED. The differing-max-units engine test passed FIRST RUN — the formula was always
> right; the gap was data + roster (that twin is the proof).
>
> ## 4. /compare picker (ADR-0434) + installer banner (ADR-0435)
> `a`/`b` on /compare AND its export through ONE resolver (/integrity's guard verbatim —
> chronology can never reverse; a=1&b=0 renders byte-identical to a=0&b=1). Bare URL keeps its
> exact byte shape (ADR-0320 emit-only-non-default), picker only at n>2 (pinned ⛶ counts hold),
> oracle variant `[picked-pair] GET /compare` added + labels regenerated. Installer banners now
> print the EMBEDDED version + the "installs exactly vX.Y.Z" honesty line (rendered-banner test
> derived from each file's own wheel name, red-before-green against the committed installers);
> README-DISTRIBUTABLE gained "Updating an install you already have".
>
> ## Traps paid for THIS session — check by name
> A screenshot is testimony about a VERSION, not the tree — check what build the reporter runs
> before chasing a render bug (the v1.0.148 realization redirected half a task) · seat scroll
> from LIVE geometry after double-rAF + fonts.ready, never from model numbers (280px drift) ·
> `target=0` collided with a real UID-0 contract test — a sentinel needs the existing pins
> swept, and the fix is to move the pin to a nonzero member of the same class · a new panel on
> a contract-pinned page is a DELIBERATE re-baseline (r10 3->4, r11 path.js digest), never a
> test weakening; keep the load-bearing block digests unchanged and say so in the pin comment ·
> the util chart must NOT wear .chart-host or chartframe bolts a zoom bar onto a div list ·
> FastAPI Form: ruff B008 rejects `Form([])` and `Form(default_factory=...)`; `Form(())` with a
> tuple annotation passes.
>
> ## Next
> The audit ledger stands untouched (page modules A/B, docs/config/CI, AI figure-gate
> adversarial pass, 25-route adverse gap). NEW: operator re-loads their JUICE .xer set on
> v1.0.219 (grouping should light the wall; else Combine in Portfolio) · sibling degrade notes
> (/trend /cei /evolution /volatility /integrity) could gain ADR-0431's other-projects tail ·
> Insufficient-Detail V05/V06 + TP2 stay BLOCKED on the operator's Fuse artifact (do NOT
> re-chase — six hypotheses measured and refuted, ADR-0430).
>
> ## Gate at close
> Statics green whole-tree (ruff / format / mypy strict / bandit). Full suite + parity run at
> close — numbers in the SESSION-LOG entry. Wheel v1.0.219 + nine installers rebuilt once,
> after the last src edit; installer suite 68/68.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
