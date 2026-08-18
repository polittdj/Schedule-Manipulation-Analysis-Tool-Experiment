# Handoff — 2026-08-18 (c) (design handoff: four nav rails + the Boot Screen; ADR-0425/0426; v1.0.215 shipped)

> ## STATUS (current) — the design-handoff slices, rebased onto `89cd5d8`.
> Highest ADR now **0426**. **SHIPPED code changed** (`web/launch.py` + `static/launch.js` +
> `static/launch.css` new; `web/chrome.py`, `web/app.py`, `launcher.py` edited) — version
> **v1.0.214 → v1.0.215**, SCHEMA unchanged, wheel + nine installers rebuilt. This is *design*
> work from the Claude Design bundle, not the audit line: the audit ledger
> `docs/STATE/AUDIT-2026-08-16.md` is **untouched and still open**.
>
> ## What landed — two ADRs
> **ADR-0425 — four off-spine nav rails.** The MERLIN deck groups non-story pages into
> `FORENSICS` / `LIBRARY` / `CONTROL` / `SETUP`; the repo shipped **one** rail (`SETUP`) with
> `/integrity`, `/scorecards`, `/evm`, `@wbs` and `@card` reachable only as folded **beats**.
> Schedule Integrity — the manipulation-detection surface — read as a footnote under chapter 02.
> Nav placement only: chapter membership rides `_Chapter.titles`, never `beats`, so every kicker,
> Continue segue and progress dash is unchanged. Off-spine membership is now **declared**
> (`_OFF_SPINE`), not inferred from `label != "SETUP"`, and a per-file rail entry with no file
> loaded is **skipped**, not pointed at `/`.
>
> **ADR-0426 — the Boot Screen at `/launch`.** The deck's startup lightshow: one pool of up to
> 15,600 particles morphing between helix / wave / galaxy / nebula, four hero scenes, a staged
> transit, a welcome panel. `launcher.py` now opens the browser there. It reuses ADR-0328's audio
> module rather than synthesizing a second hum.
>
> **It is the only route that does not render through `_page`** — no nav, no chapter kicker, no
> Continue segue. That is exactly where compliance chrome silently stops rendering, so
> `_cui_marking(state)` and `_compliance_drawer(state)` were extracted and BOTH pages call them.
> `_LAYOUT` no longer carries the CUI/ITAR/EAR prose inline; there is exactly **one** copy in the
> tree, and the test asserts the two renders are **byte-identical**, not merely both present.
>
> **No fabricated numbers.** The deck's tiles count "225.4 M km" down and tick off "14 pre-flight
> checks" with nothing computing either. The tiles read real session facts and render `—` when
> nothing is loaded, never `0`. No CPM pass on the boot path.
>
> **One sanctioned departure from theme-following:** an additive particle field has no light-mode
> equivalent (daylight first rendered as a grey smear with unreadable ink — measured). The stage
> carries its own `--boot-*` tokens in a stylesheet only that page loads. `DESIGN-SYSTEM.md` §7a
> records it and says plainly it is **not a precedent**.
>
> ## The mutation harness was itself the defect — read this before writing the next one
> The first battery reported **6 of 10 mutants SURVIVED**. The guards were fine; the harness was
> importing the *installed* package from the real tree (`pip install -e` wins on `sys.path`), so
> every Python mutation landed on a file nothing under test was reading. It now probes
> `module.__file__` and refuses to run unless the subject is inside the sandbox. 11/11 red after.
>
> ## Not done here, deliberately — PICK THIS UP
> **The MERLIN wordmark is NOT applied** (design gap #10). The deck's welcome copy reads "welcome
> back to Merlin"; this screen says "Welcome back." and the title stays `— POLARIS`. Renaming the
> product touches the ADR-0175 wordmark and every page in the tree — an operator decision.
> The deck's Hohmann-transfer diagram is also not ported.
>
> Remaining design gaps (`docs/DESIGN-GAP-2026-08-17.md`): **Metric Lab** (lowest effort — engine
> ships, only the single-metric ribbon view is missing) · **Segment Forecast** as a page ·
> **Portfolio at Scale** · **Beyond the Schedule** · **Trend Lab + Manipulation Watch** ·
> **PDF export** · **GUIDE ME** · **SHOW UIDs**.
>
> ## Carried forward
> The audit is **not finished** (the never-audited areas, the remaining REPORTED rows). ADR-0353..0426 closed.
>
> ## Gate at close
> See SESSION-LOG for the run and its triage.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
