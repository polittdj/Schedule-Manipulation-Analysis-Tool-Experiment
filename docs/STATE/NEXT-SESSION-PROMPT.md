# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS² (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue.
As of last close: **v1.0.220 · highest ADR 0436 · SCHEMA 2.11.0 · `main` = e3b2f133** (the PR
#608 squash). **Nothing is in flight** except the docs-only close PR named below. **git fetch
origin before you branch, number an ADR, or commit — and RE-fetch before writing the docs**
(the 08-20 arc had ADR numbers taken mid-session by concurrent merges repeatedly).

⇢ FIRST: check whether the docs-only close PR from 2026-08-20 (branch
`claude/polaris-installer-version-h3qy0v`, "session close (e)") merged; its content is THIS
file plus the handoff/log close-out lines. If it is still open, it overlaps docs/STATE —
whichever merges second needs a trivial re-resolve.

⇢ WHAT'S DONE — do not re-open. 2026-08-20 shipped and MERGED three releases, all verified by
the operator on their own machine:
- **v1.0.219 / #607 (ADR-0431..0435):** multi-.xer version grouping (XER project_title = root
  PROJWBS name; POST /project/combine + Portfolio panel; Mission Control names other-project
  files) · /path whole-schedule default + UID-click retarget + Dur column + the ~1in data-date
  seat · Resources on P6 (RSRCRATE max units at the DD, real Assignments, whole roster,
  Utilization-by-resource panel) · /compare a/b any-two picker (page + export, one resolver) ·
  installer banner prints its embedded version + "Updating an install you already have".
- **v1.0.220 / #608 (ADR-0436):** the program is named **POLARIS²** — displayed name only
  (U+00B2 everywhere: wordmark's hand-set ² glyph, titles, exports, installer banners
  "Polaris² (Schedule Forensics) installer — vX.Y.Z", shortcuts with legacy cleanup); the
  schedule_forensics package/CLI/paths deliberately unchanged (the ADR records the boundary).

⇢ OPERATOR FOLLOW-THROUGH (ask, don't assume): have they re-loaded the JUICE UVS .xer update
set on v1.0.220? The Mission Control wall should light; if their per-update exports rename
the project NAME too, Portfolio → Combine Projects is the remedy. Any operator report about a
render must be checked against the BUILD they run (the v1.0.148 lesson, ADR-0435).

⇢ RESUME ORDER — start at 1.

1. **PAGE MODULES A/B and DOCS/CONFIG/CI — still NEVER audited.** The last two whole
   dimensions with zero coverage (unchanged from the 2026-08-16 ledger).
2. **The AI figure-gates ADVERSARIAL pass** — `ai/qa.py::_figure_roles`, `_classify_figures`
   (`handled` added on the first non-value occurrence), `_MAX_GATED_FIGURES = 24`,
   `ai/derivation.py` Layer B. Fold in the f.text-never-f.rendered() finding (Ask prompt
   assembly, ai/qa.py ~910/931/942). Annotate-mode gap: gate scores against `model_evidence`
   while the analyst sees `relevant_facts`.
3. **The 25-route adverse gap** (19 are `POST /sra/*`; `/sra/factor-table` never touched at
   all). Report coverage as the bracket 25 <= gap <= 66.
4. Remaining REPORTED ledger rows: CPM-01..04 · MF-02/03/04/06..10 · MC-02..08 · IMP-02..06 ·
   the sibling degrade notes (/trend /cei /evolution /volatility /integrity) that could take
   ADR-0431's other-projects tail.

⇢ BLOCKED, OPERATOR-OWNED — do NOT re-chase. Insufficient Detail V05/V06 (tool 0/4 vs Fuse 5)
and TP2's 6-vs-7 are the SAME question; six hypotheses were measured and refuted (ADR-0430).
Unblock = the operator clicks the V05 "Insufficient Detail — 5" cell in the Fuse Starlight
workbook (or exports the ribbon to Excel) so the five counted activities are NAMED.

Binding: CLAUDE.md's QC-1 (prove or refute before reporting — red before green, mutation-prove
the teeth, sandbox it, say UNVERIFIED rather than assert silently) and QC-2 (read everything,
assume nothing; inherited claims — including this prompt — are testimony, not evidence) —
standing rules per ADR-0393, pinned by tests/test_standing_rules.py.
