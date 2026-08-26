# Handoff — 2026-08-25 (page modules audited for the first time: operator content is DATA, not markup; ADR-0439, v1.0.221)

> ## STATUS (current) — audit resume item 1 is PARTLY CLOSED on branch `claude/polaris-resume-audit-ndwcc5` (draft PR #612), merged up to ddca5d5 (the #611 squash).
> Highest ADR now **0439**; version stays **1.0.221** — **`src/` is untouched** (tests + one
> pyproject comment block + state docs only), so **no wheel/installer rebuild is owed** (ADR-0148)
> and there is no version bump. **main moved under this branch again**: docs-only **#611 MERGED @
> ddca5d5** while CI was running, conflicting all four state docs; the branch was merge-resolved
> (never rebased) and the rotation re-done on #611's final docs, so the archive holds ITS
> 2026-08-21 section verbatim — including the open operator ask below.
>
> ## CARRIED FORWARD, STILL UNRESOLVED — the operator's multi-folder ask (from #611)
> **This is the live operator item; the audit work below does not displace it.** The operator wants
> **ctrl/shift multi-select** for loading several folders. Three facts were MEASURED 2026-08-21 —
> do NOT re-derive them: (1) the folder-picker DIALOG can never multi-select (`webkitdirectory`
> overrides `multiple`, WICG entries-api #24); (2) **dropping N folders WORKS**, proven with real
> Chrome entries via CDP `Input.dispatchDragEvent`; (3) **ctrl/shift on FILES already works today**
> via "choose files…" — likely the whole answer for the .xer JUICE workflow. Two candidate builds
> were offered and **the operator has NOT chosen**: clearer labels, or parent-folder pick → one
> Project per sub-folder (which must ASK, never guess). Ask before building.
>
> ## What closed — PAGE MODULES, the dimension that had never been audited at all
> Question: what happens to an operator's activity name — legally `Pour slab <2m> & cure` — on the
> way to a served page and to an exported workbook? **Verdict: CLEAN, and measured.** 81 scored
> server responses · 33 rendered pages in real Chromium · 44 export archives — zero leaks. The
> vendored JS builds its DOM with `createElement` + `textContent` (structurally immune); the NINE
> non-clearing `innerHTML` sinks are static literals, already-escaped text (`home.js`'s `skipHint`),
> host telemetry, or server-built HTML. Two standing censuses now hold it —
> `tests/web/test_operator_content_escaping.py` and `tests/web/test_operator_content_dom_browser.py`
> (auto-discovered by `tools/browser_modules.py`; **CI's `browser` job ran it green in 9m**).
>
> **Believe the clean verdict only because both instruments were proven able to dirty it.** Both
> first drafts said "clean" and both were WRONG to: the page census hand-wrote its route list, so
> `/analysis` and `/wbs` (really `/{name}` routes) 404'd and **scored as escaped**, and every
> parameterized route was skipped; the browser oracle's positive control injected into a `<td>`'s
> own `innerHTML`, which cannot produce a row break at all. Mutation battery, all on the REAL
> product, all red by name: `_e()` removed on the `analysis.py` activity row → `/analysis/{name}` ·
> `path.js` `el()` `textContent`→`innerHTML` → `/path` + `/driving-path` (`img=5, onerror=5`) ·
> `_esc()` neutered in both report writers → 6 unparseable archives · docx.py ONLY → 10 docx
> exports · `_export_cell`'s status gate removed → `0.0/0.0/0.0` back in the EVM sheet.
>
> ## The ledger itself was carrying a week-old lie
> **MF-02 shipped as ADR-0411 and the row still read "Not yet implemented"** — and the kickoff
> repeated it in the standing queue. Re-verified against the shipped workbook BYTES (cost-free file:
> engine still `status=NA value=0.0`, cells read `''`), and corrected. An ADR-vs-queue census over
> all 35 open row IDs found MF-02 was the **only** stale entry, so the rest of the queue is honest
> — a LOWER bound, since an ADR can close a row without naming its ID.
>
> ## Measured and deliberately NOT changed (do not "fix" these blind)
> **6 dead E501 per-file-ignores** (`scurve`, `standards`, `brief`, `briefing`, `curves`,
> `workbench` — two independent oracles agree): the stated policy attaches the exemption to what a
> module IS, not what it currently contains, so removing them fights the intent and breaks the next
> HTML edit · **`evolution.py`'s completed-on-path table renders `0%` for an absent activity** where
> the cell beside it renders `—`, in a table whose heading asserts they completed — **measured
> unreachable**, latent, reported not repaired (the `citations.reattach`/`pinned` shape).
>
> ## Traps paid for THIS session — check by name
> **A hand-written route list turns 404s into "clean".** Any census over pages MUST enumerate from
> the app object and MUST refuse to score a non-success response · **a positive control can be wrong
> about WHERE the defect lands**: `</td></tr>` assigned to a `<td>`'s own `innerHTML` is discarded
> by the parser, so the symptom only exists when a whole table STRING goes into a container ·
> **a population floor placed before the substantive assertion reports the wrong cause** — the
> export census counted only well-formed archives, so a corruption shrank the population and it
> cried "enumerator broken"; a red for the wrong reason is not a red · **a half-covered guard reads
> exactly like a whole one**: the export census built xlsx URLs only, leaving `docx.py`'s separate
> `_esc` unguarded while its teeth test passed anyway.
>
> ## Next
> **The operator's multi-folder ask above comes first** (it needs a CHOICE, not a build). Then
> **docs/config/CI**, still the open audit dimension — it got only a partial pass here (CLAUDE.md's
> gate verified against `ci.yml` and `[tool.mypy]`; two stale pyproject comments fixed); the hooks,
> the installer workflow, `constraints/` and the docs guards are untouched. Then: the AI figure-gate
> adversarial pass · the 25-route adverse gap (report as 25 <= gap <= 66) · the remaining REPORTED
> rows (MF-02 now removed from that list). Insufficient-Detail V05/V06 + TP2 stay BLOCKED and
> operator-owned — do NOT re-chase.
>
> ## Gate at close
> See the SESSION-LOG 2026-08-25 entry for the numbers, recorded AFTER the runs finished (QC-1).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
