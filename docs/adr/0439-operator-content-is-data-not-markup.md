# ADR-0439 — Operator file content is DATA, not markup: the page-modules dimension gets its first census

- **Status:** Accepted
- **Date:** 2026-08-25
- **Context:** the 2026-08-16 deep-dive audit ledger, resume item 1 — **page modules A/B** and
  **docs/config/CI**, the last two dimensions with *zero* coverage.
- **Supersedes/relates:** ADR-0411 (MF-02, the fabricated `0.0` export) · ADR-0416 (JS-01, a
  client-side contract that rotted while every server test stayed green) · ADR-0420 / ADR-0421
  (the standing computed censuses this one is modelled on).

## The question this dimension had never been asked

Every activity name, resource name and project name POLARIS² prints comes out of an operator's
schedule file. A real MS Project activity may legally be called `Pour slab <2m> & cure`. Nothing
in the repo had ever measured what happens to such a name on its way to a served page or an
exported workbook — the page-module dimension had received no audit at all.

Two properties matter, and they fail differently:

* a **served page** must render such a name as TEXT. Under the tool's strict CSP an injected
  handler would not execute, so the realistic damage is not script — it is **markup corruption**:
  a name carrying `</td></tr><tr><td>` silently restructures a table, and a table that
  restructures itself can hide or misattribute a figure. In a testimony deliverable that is a
  Law 2 defect whether or not anything "executes".
* an **exported workbook/document** must stay **well-formed XML**. An export leaves the tool and
  gets quoted; a corrupt part is either unopenable or, worse, opens with the wrong cells. This is
  the MF-02 family — an artifact that contradicts the screen.

## Decision

Ship two standing computed censuses, and record the dimension's verdict as *measured*, not
assumed.

* `tests/web/test_operator_content_escaping.py` — poisons the shipped example's names, walks
  **every GET route enumerated from the live app object**, and requires that no success HTML
  response contain the injected marker verbatim; then requires every export archive to parse as
  XML with a real parser under an XML-hostile name.
* `tests/web/test_operator_content_dom_browser.py` — the DOM leg, in real Chromium. This is the
  half that matters most and the half no server test can reach: most of this UI's data arrives as
  JSON, and a JSON payload carrying `<img …>` verbatim is *correct*. The string only becomes
  dangerous when a renderer hands it to `innerHTML`, and only the DOM says which happened.

**Verdict: clean, on both legs.** 81 scored server responses, 33 rendered pages, 44 export
archives — zero leaks. The vendored JS builds its DOM with `createElement` + `textContent`, which
is structurally immune; the nine non-clearing `innerHTML` sinks in the tree are static literals,
already-escaped text (`home.js`'s `skipHint` runs filenames through `esc()`), host telemetry, or
server-built HTML.

A clean dimension is a result worth having only if the instrument could have said otherwise, so
each census is mutation-proven and each carries its proof as a test.

## Why the instruments are trusted — and the two ways the first versions were blind

Both first drafts returned "clean" and both were **wrong to**, which is the whole argument for
this ADR's method:

1. **The page census hand-wrote its route list.** Two of its 28 pages (`/analysis`, `/wbs`) do not
   exist as parameterless routes — they are `/analysis/{name}` and `/wbs/{name}` — so the probe
   scored **404s as escaped**. It also therefore skipped every parameterized route, which is
   exactly where the per-schedule pages live and where names render densest. Fixed by enumerating
   from the app object, filling `{name}` from the real session keys, and **refusing to score any
   non-success response**. The corrected census then went RED by name on `/analysis/{name}` the
   moment `_e()` was removed from the activity row — the site the first version could not see.
2. **The browser oracle's positive control was wrong about where an injection lands.** Assigning
   the row-break marker to a `<td>`'s own `innerHTML` does **not** corrupt the table: the HTML
   parser discards stray `</td></tr>` in that context. The symptom is only reachable when a
   renderer builds a whole table STRING and assigns it to a container — which is how it would
   really happen. The teeth test caught this; without it the third symptom would have been dead
   weight that could never fire, in a guard whose whole purpose is to fire.

Mutation proofs, all on the REAL product, all red **by name**:

| mutation | instrument | result |
| --- | --- | --- |
| `_e(task.name)` → `task.name` (`analysis.py`) | page census | RED — `/analysis/{name}` named |
| `el()` `textContent` → `innerHTML` (`path.js`) | browser census | RED — `/path` + `/driving-path`, `img=5, onerror=5` |
| `_esc()` neutered (`reports/xlsx.py` + `docx.py`) | export census | RED — 6 archives unparseable |
| `_esc()` neutered in **`docx.py` ONLY** | export census (widened) | RED — 10 docx exports named |
| `_export_cell` status gate removed (`app.py`) | MF-02 re-probe | RED — `0.0 / 0.0 / 0.0` back in the sheet |

Three further corrections landed in the guard **itself**, each found by attacking it rather than
by reading it:

* the export census originally counted only *well-formed* archives as its population, so a
  corruption shrank the population and the floor assertion fired first — reporting "the enumerator
  is broken" for a tree whose real defect was an unescaped writer. **A red for the wrong reason is
  not a red**, so `scored` now counts every archive opened and the substantive assertion runs
  before the floor.
* the census built **xlsx URLs only**, so `reports/docx.py` — which has its own `_esc` — was
  **unguarded**, and the teeth test passed anyway off the xlsx corruption. A half-covered guard
  reads exactly like a whole one. Both formats are now enumerated, the teeth test asserts the
  corrupt set contains **both** an `/xlsx/` and a `/docx/` URL, and a **docx-only** mutation was
  then observed RED naming 10 docx exports — a regression the earlier version could not have seen.
* the page census counted every success toward its floor, including the JSON APIs, so a tree whose
  every HTML PAGE had stopped rendering could still have satisfied it. The floor is HTML-only now.

The sink count in this ADR was wrong once too, and for the same kind of reason: the first sweep
filtered out `innerHTML =` lines whose value continues on the **next** line, which is precisely
where the substantial assignments live. It reported seven; there are **nine**. The two it hid
(`heartbeat.js`'s hardcoded shutdown message, `sysmon.js`'s hardcoded chip labels) carry no
operator content, so the verdict never moved — but a bounded sweep looked exhaustive and was not,
in the very document arguing against that.

## What was measured and deliberately NOT changed

* **MF-02 was already fixed and the ledger still listed it as open work.** ADR-0411 shipped
  `_export_cell`; the row read *"Not yet implemented"* and the kickoff repeated it in the standing
  queue. Re-verified against the shipped workbook bytes and corrected in the ledger. An
  ADR-vs-queue census over all 35 open row IDs found MF-02 was the **only** stale one — reported
  as a lower bound, since an ADR can close a row without naming its ID.
* **The `value is not None` class MF-02 asked about is closed.** `MetricResult.value` is declared
  `float`, so such a guard is dead by construction and therefore mechanically detectable: an AST
  census returns three sites in `src/`, all correct.
* **Six E501 per-file-ignores are dead** (`scurve`, `standards`, `brief`, `briefing`, `curves`,
  `workbench` no longer carry an over-length line — two independent oracles agree). **Not
  removed.** The stated policy is that the exemption attaches to what a module *is* — an extracted
  page module whose HTML f-strings will grow again — not to what it currently contains. Removing
  them would fight the documented intent and make the next HTML edit fail CI. Recorded as measured,
  in the do-not-fix-blind spirit of MF-05.
* **`evolution.py`'s completed-on-path table renders `0%` for an absent activity** where the cell
  beside it correctly renders `—`, in a table whose heading asserts those activities *completed*.
  Measured **unreachable**: `completed_on_path` is built with `sch.tasks_by_id.get(uid) is not
  None` against the same `schedules[i]` the view indexes, and the single caller computes `ev` from
  the same list one line above. Latent and contradictory, like `citations.reattach` dropping
  `pinned` — reported, not repaired, because no test can currently exercise it.
* **Two pyproject comments had drifted from the files they describe** — `components.py`'s said
  "Only ONE line actually needs the exemption" (measured 10) and `ssi.py`'s said "nine over-long
  COMMENT/docstring lines" (measured 10, one of which is code). Corrected, and each now carries
  the measurement date rather than a bare count.

## Consequences

* The never-audited page-modules dimension now has a verdict backed by executable, mutation-proven
  instruments rather than by reading, and the two censuses run on every suite (the browser one is
  auto-discovered by `tools/browser_modules.py`, so CI carries it with no workflow edit).
* The immunity is a property of how the renderers happen to be written today. Nothing enforced it
  before; now something does.
* No shipped code changed — tests, one config comment block, and state docs only. No version bump
  and **no wheel/installer rebuild** is owed (ADR-0148).
