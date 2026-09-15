# Handoff — 2026-09-15 (OR-18 SHIPPED (ADR-0494): every page states the installed build — the Boot Screen first under the compliance chrome, the header beside the brand; v1.0.262. OR-17 SHIPPED IN PART (ADR-0493, #677 MERGED as `18fa3ffb`, v1.0.261))

STATUS (current) — `main` @ **`18fa3ffb`** (#677 squash-merged by the operator 2026-09-15 15:31Z; its tree == the PR head `1aacd3be`'s tree, `8402a728…`; #676 had landed before it as `447d1db1`). The branch `claude/dazzling-ptolemy-i1zig0` was restarted on that squash (`--prune`, `remote set-head`, `checkout -B`). **`main`'s own runs for `18fa3ffb` — read them first** (the steward rule; a red cell on a tree identical to the green PR head is the runner's claim: #677 read eight of eight green on `6039db1d` and again on later heads). **This session then shipped OR-18 on the restarted branch: ADR-0494, v1.0.262** — the operator's two directives of the day (*"the version number of the installed program at the top of the launch page"*, then agreement to *"the same chip in the global header so every page and every screenshot pins the build"*). **(1) The surfaces.** `/launch` (the Boot Screen, ADR-0426 — outside the story chrome, so a header chip could never reach it) carries `<div class=boot-version data-tool-version data-no-i18n>` after the CUI bar and the drawer and before `<div id=sfBoot>` — server-rendered, present when the boot script never runs; every chrome page carries `<span class=brand-ver data-tool-version data-no-i18n>` right after the wordmark's `</h1>` (`--header-muted`, `nowrap`; the brand subtitle is hidden in three themes and could not host it). The element's TEXT is the bare version; the visible "BUILD" label is CSS `::before`, so every pin and screenshot reads the same digits. **(2) Read at render time, never a literal:** `chrome.tool_version()` (re-exported from `web.app` — the monolith-split contract fired on the new name); a probe value monkeypatched into `chrome._ASSET_VERSION` flows to both surfaces. **(3) Measured:** red-first (`/launch`, `/` RED; `/settings` GREEN); 4 server pins; Chromium in four themes at 1,440 and 900 px — both chips laid out, the launch line under the CUI bar, the header chip inside the header and not left of the brand, the label rendered, **the document's scroll width identical with the chip hidden** (no sideways scroll added); **mutation battery 5 / 5 RED by name** (line dropped · chip dropped · a literal · translatable · moved below the stage); statics clean; installers 68 on the rebuilt wheel. The full suite and `-m parity` on the final head, the PR number and its checks: the SESSION-LOG follow-up. **The header never prints** (base.css hides it in print) — the chip does not reach exports; said so in the ADR (an earlier chat line claimed it would print — corrected). **What the chip means:** the version the RUNNING process reports; an older copy still on the port shows its older version — the truth. Highest ADR **0494**. QC-1/QC-2 bind every session — ADR-0393.

**CARRIED FORWARD, NOT this unit's:** OR-17's operator-owned items — a v1.0.262 screenshot after pasting the CURRENT Hub key (the receipt + the banner's quoted reason settle key vs tool), V-4, the `…/v1/chat/completions` request in OR-17 §4 (no completion-shaped probe without it), the 09-11 `"ok": false` lines; R-45; `test_driving_path_whole_schedule_browser.py:104` width-racy (#667); `/settings` sideways scroll; ADR-0488's residual. **Environment facts paid for this session:** the harness exports `GIT_AUTHOR_*` / `GIT_COMMITTER_*` as the operator — prefix commits with the `noreply@anthropic.com` identity or the stop hook flags them unverified (a rewrite + force-push of pushed commits was denied by the classifier and NOT worked around); a docs push cancels the PR's running CI (cancel-in-progress) — hold docs pushes until a run the operator is waiting on reports.

## UNVERIFIED, stated

- `main`'s own runs for `18fa3ffb` — not yet read at this close (the next session reads them first).
- The operator's machine: whether v1.0.262 is installed and what its launch screen / header shows — theirs to report.

## Traps this session paid for, by name

* **A placement pin anchored on a substring** (`id=sfBoot`) matched an earlier occurrence in the head and read the line as "after the stage"; anchor on the exact tag.
* **A new public name in an extracted module fires the monolith-split contract** — `X as X` in `web.app` before the suite, not after.
* **"It prints" was a claim about the header made from memory** — base.css hides the header in print; read the stylesheet before promising a surface.
* **A brand subtitle hidden in three themes cannot host a chip** — measure the host in all four before choosing it.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here.** **First:** this unit's draft PR (number in the SESSION-LOG follow-up) — its eight checks (installers changed); then `main`'s runs for `18fa3ffb`; then the operator's OR-17 §4 replies. Then the report's §3 in order: **R-47** · **R-52** · **R-50** · **R-61** · **R-57** · **R-58** · **R-59** · **R-64** · **R-63** · **R-62** · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards. Other residuals: ADR-0488's / 0486's / 0485's / 0483's, `/settings` sideways scroll, OR-11b, OR-11d, the working-minute axis, the hint bubble, ADR-0484's in-grid rows.

**Review cover is still absent** — Codex quota EXHAUSTED; the mutation batteries and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
