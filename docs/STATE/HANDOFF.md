# Handoff — 2026-08-25 (page modules audited for the first time: operator content is DATA, not markup; ADR-0439, v1.0.221)

> ## STATUS (current) — audit resume item 1 is PARTLY CLOSED on branch `claude/polaris-resume-audit-ndwcc5` (draft PR pending), based on dfa09ac (the #610 squash).
> Highest ADR now **0439**; version stays **1.0.221** — **`src/` is untouched** (tests + one
> pyproject comment block + state docs only), so **no wheel/installer rebuild is owed** (ADR-0148)
> and there is no version bump. The 2026-08-21 feature PR **#610 MERGED @ dfa09ac** before this
> branch was cut, so nothing was in flight.
>
> ## What closed — PAGE MODULES, the dimension that had never been audited at all
> Question: what happens to an operator's activity name — legally `Pour slab <2m> & cure` — on the
> way to a served page and to an exported workbook? **Verdict: CLEAN, and measured.** 81 scored
> server responses · 33 rendered pages in real Chromium · 44 export archives — zero leaks. The
> vendored JS builds its DOM with `createElement` + `textContent` (structurally immune); the NINE
> non-clearing `innerHTML` sinks are static literals, already-escaped text (`home.js`'s `skipHint`),
> host telemetry, or server-built HTML. Two standing censuses now hold it —
> `tests/web/test_operator_content_escaping.py` and `tests/web/test_operator_content_dom_browser.py`
> (auto-discovered by `tools/browser_modules.py`, so CI carries it with no workflow edit).
>
> **Believe the clean verdict only because both instruments were proven able to dirty it.** Both
> first drafts said "clean" and both were WRONG to: the page census hand-wrote its route list, so
> `/analysis` and `/wbs` (really `/{name}` routes) 404'd and **scored as escaped**, and every
> parameterized route was skipped; the browser oracle's positive control injected into a `<td>`'s
> own `innerHTML`, which cannot produce a row break at all. Mutation battery, all on the REAL
> product, all red by name: `_e()` removed on the `analysis.py` activity row → `/analysis/{name}` ·
> `path.js` `el()` `textContent`→`innerHTML` → `/path` + `/driving-path` (`img=5, onerror=5`) ·
> `_esc()` neutered in both report writers → 6 unparseable archives · `_export_cell`'s status gate
> removed → `0.0/0.0/0.0` back in the EVM sheet.
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
> cried "enumerator broken"; a red for the wrong reason is not a red.
>
> ## Next
> **docs/config/CI is still the open dimension** — it got only a partial pass here (CLAUDE.md's gate
> verified against `ci.yml` and `[tool.mypy]`; two stale pyproject comments fixed). The hooks, the
> installer workflow, `constraints/` and the docs guards are untouched. Then: the AI figure-gate
> adversarial pass · the 25-route adverse gap (19 are `POST /sra/*`; report as 25 <= gap <= 66) ·
> the remaining REPORTED rows (MF-02 now removed from that list). Operator follow-through unchanged:
> has the JUICE UVS .xer set been re-loaded on v1.0.220+? Insufficient-Detail V05/V06 + TP2 stay
> BLOCKED and operator-owned — do NOT re-chase.
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
