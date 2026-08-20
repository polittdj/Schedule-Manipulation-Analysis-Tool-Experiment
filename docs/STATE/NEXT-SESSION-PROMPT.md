# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue.
As of last close: v1.0.220, highest ADR 0436, SCHEMA 2.11.0; PR #607 (ADR-0431..0435,
v1.0.219) MERGED @ a91fbfba and was verified end-to-end on the operator's PC; the POLARIS²
rename (ADR-0436, v1.0.220) shipped on top from the restarted branch. **git fetch origin before you branch, number an ADR, or commit — and RE-fetch before
writing the docs** (this arc has had ADR numbers taken mid-session by concurrent merges three
times).

⇢ WHAT'S DONE — do not re-open. The program is named **POLARIS²** (ADR-0436, v1.0.220):
displayed name only (U+00B2 everywhere, hand-set wordmark glyph, installer banners/shortcuts
with legacy cleanup); package/CLI/paths deliberately unchanged. Before that, the 2026-08-20
operator asks CLOSED as ADR-0431..0435 /
v1.0.219 (PR from `claude/polaris-installer-version-h3qy0v`): multi-.xer version grouping (XER
project_title = root PROJWBS name; POST /project/combine; Mission Control names other-project
files) · /path whole-schedule default + UID-click retarget + Dur column + the ~1in data-date
seat · Resources on P6 (RSRCRATE max units at the DD, real Assignments, whole roster,
Utilization-by-resource panel) · /compare a/b any-two picker (page + export, one resolver) ·
installer banner prints its embedded version + README "Updating an install you already have".
Queue item 1 (INSTALLER VERSION VISIBILITY) is that last piece — DONE. Also check whether PR
#606 (the parity sweep's docs-only close) merged; its kickoff content is SUPERSEDED by this
file, and it overlaps docs/STATE — whichever merged second needed a re-resolve.

⇢ OPERATOR FOLLOW-THROUGH (ask, don't assume): re-load the JUICE UVS .xer update set on
v1.0.219 — the wall should light up; if their per-update exports rename the project NAME too,
use Portfolio → Combine Projects. And re-check the /path timescale on the NEW build before
believing any screenshot from the old one — their previous install was v1.0.148 (ADR-0435's
whole story).

⇢ RESUME ORDER — start at 1.

1. **PAGE MODULES A/B and DOCS/CONFIG/CI — still NEVER audited.** The last two whole dimensions
   with zero coverage (unchanged from the 2026-08-16 ledger).
2. **The AI figure-gates ADVERSARIAL pass** — `ai/qa.py::_figure_roles`, `_classify_figures`
   (`handled` added on the first non-value occurrence), `_MAX_GATED_FIGURES = 24`,
   `ai/derivation.py` Layer B. Fold in the f.text-never-f.rendered() finding (Ask prompt
   assembly, ai/qa.py ~910/931/942). Annotate-mode gap: gate scores against `model_evidence`
   while the analyst sees `relevant_facts`.
3. **The 25-route adverse gap** (19 are `POST /sra/*`; `/sra/factor-table` never touched at
   all). Report coverage as the bracket 25 <= gap <= 66.
4. Remaining REPORTED ledger rows: CPM-01..04 · MF-02/03/04/06..10 · MC-02..08 · IMP-02..06 ·
   MAN-01..03 · REC-02 · JS-02..06 · TST-02/03.
5. Smaller carried-forward items: sibling degrade notes (/trend /cei /evolution /volatility
   /integrity) could gain ADR-0431's other-projects tail · consider a browser assertion for the
   Utilization panel rows (currently server+probe-verified) · ADR-0424's leftover:
   `engine/pair_series.py` + `ai/pair_facts.py` never audited.

⇢ DO-NOT-FIX-BLIND LIST (unchanged from the ledger): MF-05 (empty-population PASS may be
correct Acumen parity) · MC-01's parity leg UNVERIFIED by design (ADR-0414) · ADR-0417 needs a
non-degenerate SRA fixture · ADR-0419's MinutesPerDay leg needs an operator file ·
`citations.reattach` drops `pinned` — measured unreachable; fix only if made reachable.

⇢ MEASURED-FALSE / BLOCKED — do NOT re-chase. Insufficient Detail V05/V06 and TP2's 6-vs-7:
six hypotheses measured and refuted (ADR-0430); blocked on ONE operator artifact — the named
activities behind Fuse's "Insufficient Detail — 5" cell (click it in the Fuse Starlight
workbook or export the ribbon to Excel), then re-upload. The /path timescale screenshot:
NOT reproducible on ≥ v1.0.219; property-guarded in chromium.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
New last session: **a screenshot is testimony about a VERSION** — establish which build produced
the evidence before chasing a render bug · **an "identity" must survive the workflow that
produces the files** — per-EPS-unique means per-copy-renamed (proj_short_name), and the stable
analogue was the root PROJWBS name · **seat scrolls from LIVE geometry** (rect delta after
double-rAF + fonts.ready), never from mid-paint layout numbers (280px drift) · **a new sentinel
sweeps the existing pins** (target=0 vs the UID-0 summary contract; move the pin to a nonzero
class member) · **contract growth is a NAMED re-baseline** (r10 3→4 panels, r11 path.js digest)
with the load-bearing sub-digests proven unchanged · a div-list chart must not wear
`.chart-host` (chartframe bolts a zoom bar on) · ruff B008 rejects `Form([])` AND
`Form(default_factory=…)`; `Form(())` passes · **a first-run green is a twin or a vacuum** —
decide by what the fixture set can express.
Standing: a bounded sweep looks exhaustive and is not · a fix can be wrong in the direction you
did not test · the product is often its own oracle · a refuted hypothesis is a result · a count
may be counting the SYMPTOM · an oracle giving the same verdict in both worlds is BLIND · a red
for the WRONG REASON is not a red · monkeypatch per CALL SITE · never measure a tree a battery
is mutating · use `python -m ruff` · `ruff format` also formats python inside MARKDOWN — re-run
the WHOLE gate after the LAST file change · `| tail` masks exit codes · fetch before numbering
AND committing · wc decides.

⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` +
`pip install build playwright` first. Full suite ~27-32 min; `pytest -m parity` ~9 min; browser
census `pytest $(python tools/browser_modules.py)` ~6-7 min. CI budget ~75 min for a full
verdict; `cancel-in-progress: true` — never push while you need a run's signal. Installer build
needs an UNSHALLOW clone (`git fetch --unshallow origin`); `python -m build --wheel --outdir
dist/wheel && python tools/installer/build_installers.py` ~2 min, rewrites all nine.

⇢ OPERATOR-OWNED, not agent work: the Fuse Insufficient-Detail artifact (above) · V-1/V-2/V-3
gateway verification · DISC-01 · the CEI/HMI vendor export blocking PO-04/05 · an SSI export
showing a fired negative-impact register entry (ADR-0414) · an MSPDI DayWorking=1-no-times file
(ADR-0419) · branch cleanup · re-loading the JUICE set on v1.0.219.

⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
QC-1 / QC-2 (CLAUDE.md; ADR-0393, pinned by tests/test_standing_rules.py) · ADR-0240 model
protocol (the LEAD re-verifies every finding)
· full gate before every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same
commit · wheel + nine installers ONCE per shipped-code change (ADR-0148) — check
`git status src/` before assuming you owe one.
Skills: full-gate, prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change,
session-close.
