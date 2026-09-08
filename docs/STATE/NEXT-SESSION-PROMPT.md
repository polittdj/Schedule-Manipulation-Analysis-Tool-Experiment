# Kickoff prompt — next session

PR state (2026-09-08): **#649, #650 and #651 are all MERGED** → `main` @ **`f3dfd32a`** (#651's squash,
ADR-0475, v1.0.246), whose tree is **byte-identical to the PR's final head `8d2f6bfb`**
(`bfb1866b5a066ab08e5c80360a7475e442c91ec7` on both). **Read `main`'s own CI run #1794 (34173243277) +
installer-smoke #678 (34173243278) for the squash FIRST** — a red cell on a tree identical to a green PR
head is the runner's claim: compare tree hashes before believing it. The branch
`claude/handoff-next-session-q74ju8` was restarted on `origin/main` and carries only this docs-only merge
record (its draft PR number is in the SESSION-LOG). Then **R-55**.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read
`docs/STATE/HANDOFF.md` FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the
roadmap by testimony tier, pinned by `tests/guards/test_audit_report_wp8.py` (every row priced or
owned, tier order, a nine-figure census recomputed by method — re-measure, never edit by hand).
QC-1/QC-2 bind every session (ADR-0393). `git fetch origin` before you branch, number an ADR, or
commit. The container may have NO project install: `python3 -m pip install -e '.[dev,browser]'` and
`pip install build`; the installer builder needs the MPXJ history (`git fetch --deepen=400` on a
shallow clone).

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01, the multi-project Fuse
oracle) · ADR-0474 (R-44 CLOSED: resource calendars + leveling delay in the base CPM, MS Project's
stored dates as the oracle; + the latency amendment and the floor job's seven pins) · **ADR-0475 —
the design page, owed twice, delivered first and alone:** `/standards` wears the Control "Standards
and Execution Indices" artboard (`setScreen('sd')`, executed over loopback in four themes, zero page
errors). The mock's `· 16 / · 14 / · 10` were measured to BE the page's own live counts. The selector
row is ported as NAVIGATION that hides nothing (`.viz-controls.cd-cursor#standardsFamilies`, anchor
chips with live counts, a `cd-note` saying nothing is hidden); all three families gained the take the
mock gives each; the REF column carries the ENGINE's `metric_id`. Refused and named: the tab-hiding,
`⤓ EXCEL · ALL FAMILIES` (no covering export — ADR-0327), the mock's `INFO` status, its `01a`/`01b`
split of DCMA-01, the Continue footer. **The design queue: 9 done, 21 artboards remain; /scorecards
(`setScreen('sk')`) is next by cost.**

⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → mutation proofs by name →
the full gate → an ADR → the state docs → a draft PR): **R-55** FIRST — progress semantics: a STARTED
activity is floored (ADR-0391), not pinned, at its actual start, so logic still pushes it later
(Hard_File_updated3's completed UIDs 291–298 land 36 days after their actual finish) and a completed
milestone's actual instant is snapped to the project calendar; updated3 reads −6 d, updated3_24hr
+17 d; a scratch-copy pin read −13 d / −2 d — the rest is UID 403's contour (R-56) and the milestone
snaps; the SSI driving-slack goldens and ADR-0391's TP4 v5 / TP1 pins are the arbiter, `pytest -m
parity` unmoved · **R-49** — MPXJ omits a ZERO `TotalSlack` (62 of Fuse's 66 zero-float activities on
LTF2 carry none): the importer infers 0 when the file carries the element elsewhere and the task
carries `Critical`; red-first on Fuse's Zero Days Float 66 / 2 · R-46 (BCWS +150 — prorate the
straddling activity on its crew calendar) · R-47 (SPI(t) 8.24 vs 8.22) · R-52 (the `.pptx` LibreOffice
refuses) · R-50 (expose the History variants) · R-57 / R-58 / R-59 (ADR-0474's residuals) · then R-03 ·
R-04 · R-09 · R-13 · R-18 · R-20 · R-21 · R-22 · R-32 · R-39. PLUS the design page owed each session —
**now CURRENT, not owed**: deliver **/scorecards** (`setScreen('sk')`) as its own unit, recipe in
ADR-0471/0475.

⇢ Traps paid for, by name (2026-09-07 d first): **a mutation that comes back GREEN is a finding about
the TEST** — a count that is structurally constant on every fixture (DCMA always 16, SEM always 10)
cannot be distinguished from a hardcode; aim the pin at the value that VARIES (Fuse reads 9 with one
file, 14 with two) and record the rest UNVERIFIABLE · **verify a literal against the RENDER, not
memory** (two of my own probe strings were wrong before the tree was) · **the container's pip
playwright may demand a browser build the container does not vendor** (`-1234` vs the vendored
`-1194`) — use `tests/web/browser_chrome.py::chrome_kwargs()` in scratch probes too, never
`playwright install` · **a helper added to an extracted page module is red on the monolith split
contract until `app.py` carries its `X as X` re-export** · **do not leave a scratch script in the repo
root** — `ruff check .` is whole-tree · a design mock's status word, decomposition and export label
are claims about the ENGINE: check each before drawing it · a mock that HIDES is proposing a
functionality change, not a layout. (Earlier, still live: MS Project's stored Start/Finish/Early/Late/
TotalSlack/Critical are a per-activity CPM oracle in every MSPDI · `LevelingDelay` is tenths of a
minute · a booking rule proven on one file breaks another — tally by task `Type` on every golden · the
full suite is ~40 min, start it in the background the moment the engine settles · MPXJ writes no zero ·
`Large_Test_File.mpp` ≠ `Large Test File.mpp`.)

⇢ Measured-false / deliberately held — do NOT re-chase: the ribbon tiles' scopes · TP3's ribbon 8 /
Lags 3 (R-53) · the DCMA08 baseline basis (R-48) · Fuse's ACWP-to-time-now and updated3's BAC (R-45) ·
the four Hard_File bookings the MSPDI cannot explain (R-56) · **the /standards strip's
`document.scrollingElement.scrollWidth` 1719 → 1734** — the chrome-wide UI-03 condition (R-20), already
1719 pristine, and the IDENTICAL +15 ADR-0471 recorded for the identical strip on /wbs · the HELD and
CLOSED rows of the report · the S-curve & finish-window residuals of earlier sessions.

⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; read a verdict on the FINAL head; a red cell on
`main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
after a squash-merge restart the branch with `--prune` + `remote set-head` + `checkout -B`, never amend
the squash.
