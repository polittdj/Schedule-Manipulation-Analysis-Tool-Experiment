# ADR-0392 — The Ask panel could not see the workbook (population facts, no question cap, exportable answers)

Status: accepted (2026-08-13)

## Context

The operator loaded **31 `.mpp` versions of one project** and asked the Ask-the-AI panel:

> "Look at the S-Curve for each of the 31 .mpp files and then tell me if the project is improving
> or not over time. The target UID is 152."

The model answered, at length and confidently:

> "I can't actually build or compare 31 S-curves from what's been loaded here — the data set in
> front of me contains information from only **two** file versions, not 31, and it contains **no
> cumulative-progress time series** … So I cannot honestly tell you the 31-file improving-or-
> declining trend."

The operator read this as the tool failing to see 31 loaded files. It is worse and more interesting
than that: **the model was describing its evidence accurately.** The files were loaded, parsed, and
solved; the panel simply never told the model they existed.

### Measured, before any change

A synthetic 31-version workbook through `build_workbook_fact_sheet` (the exact path
`POST /api/ask` takes for workbook scope):

| measure | value |
|---|--:|
| versions loaded | 31 |
| facts produced | 23 |
| facts naming **more than one** version | **1** |
| facts carrying a per-version series of any kind | **0** |
| facts stating the loaded-version count | **0** |

The single multi-version fact was the briefing's *"How to Verify Every Number"* boilerplate, which
lists the file names inside a **verification procedure** ("open the source schedule … show the
Unique ID column"), not as data. Every substantive fact named either the newest version
(`build_briefing`'s subject) or the newest two (`detect_manipulation` /
`compute_path_counterfactual`, both explicitly latest-pair). Two named files, no series — so "two
file versions, no cumulative-progress series" was a correct reading, not a hallucination.

The S-curve itself was never the problem: `engine/s_curve.py` had computed per-version cumulative
planned/actual curves since the animated `/scurve` page shipped. Nothing routed them to the Q&A.

### Two more defects the same report exposed

* **The question was silently truncated at 500 characters.** `web/app.py` did
  `question.strip()[:500]` in both `/api/ask` routes, and `chrome.py` set `maxlength=500` on the
  input. A long forensic question reached the model as a fragment, with nothing on screen to say
  half of it had been discarded.
* **An answer could be read and not exported.** The answer arrives on a POST that streams straight
  into the panel; nothing survived the response, so there was no GET route for an export to render.
  A full cited forensic answer could only leave the tool via the clipboard.

## Decision

### 1. The population is a fact, and the series is evidence

New `engine/version_series.py` reduces every loaded version to one comparable row: its S-curve
point at **its own data date** (cumulative % of non-summary activities finished, actual vs
baseline) and its **schedule-logic finish (CPM)** — plus the mechanical first-to-last movement of
the plan-vs-actual gap and the per-step narrowed/widened/unchanged counts.

New `ai/version_facts.py` turns that into four cited facts — the population (count + every data
date), the S-curve series, the trend verdict, the finish series — inserted into
`build_workbook_fact_sheet` immediately behind the frame fact.

**Why the series recomputes rather than reading `compute_s_curve`.** The animated curve shares one
month axis across versions and caps it at 60 months, shedding the oldest months on a long
programme. A version whose data date lands in a shed month has `status_index is None` and no
readable point — with 31 monthly updates over a multi-year programme that silently drops the early
versions from any series read off that axis. Evaluating each version at its own data-date month
needs no shared axis, so the cap cannot reach it.

The values are nevertheless **identical** wherever the animated curve can be read, because
`_cumulative_pct` folds every pre-window finish into its running count — the cumulative value at a
month does not depend on where the axis starts.
`tests/engine/test_version_series.py::test_matches_the_s_curve_at_every_on_axis_status_month` pins
that equivalence and was **mutation-proved** (`<=` → `<` in the cumulative predicate fails it). Two
evaluation paths, one definition of "the S-curve" — the alternative is the tool quoting different
numbers for the same curve on the page and in the fact base, which is precisely the parity failure
Law 2 exists to prevent.

That test also caught its own vacuity first: the synthetic data dates sat outside golden Project5's
own window, so every version was off-axis and the equivalence loop iterated **zero** times. The
`compared >= 2` guard is what surfaced it.

A version is reported **unreadable** rather than measured in two distinct cases, and the series
says which: it carries **no data date** (no status point to read the curve at), or it has **no
activities in scope** (a filter scoped it to nothing). Both would otherwise render as `0% vs 0%,
gap +0.0`, which reads as "exactly on plan" for a version that was never measured at all — Law 2's
"—" never 0, at the fact boundary.

### 2. Pinned facts

`CitedStatement` gains `pinned: bool = False`. `relevant_facts` and `model_evidence` keep the frame
fact **and every pinned fact** ahead of the ranked evidence and never cut them.

Both selectors rank by question overlap and truncate at a cap (12 shown, 48 to the model). That is
right for evidence and wrong for the frame: a question phrased without the series facts' vocabulary
could rank them out, leaving the model to describe a 31-version workbook from newest-version
evidence — which is the original defect, reintroduced by the selector. Nothing else reads the flag;
it does not touch the citation gate, the figure gate, or the role gate.

### 3. No question length limit

Both `[:500]` truncations and the `maxlength=500` attribute are gone. The input is now a
**textarea** (Enter sends, Shift+Enter newlines) so a long question is readable while it is typed.
No replacement cap was introduced: a silent truncation the operator cannot see is the defect class
this ADR closes, and a loopback-only single-operator tool has no reason to cap its operator. The
empty-question rejection is unchanged.

### 4. The answer exports

`SessionState.last_ask` holds the latest exchange (`_AskRecord`) — question, scope, mode, model,
answer, second answer, cross-check, and the cited facts as shown. `GET /export/{fmt}/ask` renders it
as three sheets, and the split is the point:

* **Answer** — what the model wrote, with the standing "AI can err" disclaimer;
* **Cited facts** — what the engine computed and handed it;
* **Citations** — every fact resolved to file + UniqueID + activity, so a reader can verify each
  one in MS Project.

An AI answer that leaves this tool travels with its evidence, or it is an assertion. With no live
model the Answer cell **states why it is empty** rather than being blank (Law 2: "—" never 0). The
`⤓ EXCEL` / `⤓ WORD` links stay hidden until an answer exists, so the panel never offers a dead
link. The deterministic driving-path result records the same way — one output box, one export
button. The record is in-memory and dies with `SessionState.reset()`.

## Consequences

* A cross-version question now has cross-version evidence. The 31-version case yields facts naming
  all 31 files, with a point per version and a stated trend.
* The trend fact carries its own forensic caveat: each version is measured against **its own**
  baseline, so a re-baseline can narrow the gap with no work completed — read the counterfactual
  facts before reading a narrowing gap as progress. The engine states arithmetic; it does not
  conclude the project improved.
* Past 60 versions the series line shows both edges and **states** the elision. A truncation the
  reader cannot see is the thing being fixed; one that announces itself is a rendering choice.
* `tests/guards/render_oracle_labels.txt` regenerated: +14 labels, exactly the two new routes
  across seven stages.
* Not addressed here: the briefing itself still reports on the newest version and the latest pair.
  That is the right scope for a leadership memo; it is only the **Q&A fact base** that needed the
  whole population.

## Lessons

* **A model that says "I only see two files" may be reporting a fact about its evidence.** The
  instinct is to distrust the model; the measurement was that its evidence really did describe two
  files. Read the prompt before blaming the answer.
* **A capability the tool has is not a capability the AI has.** The S-curve had been computed
  per version for a long time. Nothing routed it to the panel that was asked about it, and no test
  could notice, because every test asserted on what was *there* rather than on what was *missing*.
* **Relevance ranking will drop the frame.** Any selector that ranks by question overlap will
  eventually rank out the fact that defines the population, and the resulting answer is confidently
  scoped to the wrong universe.
* **Silent truncation is the defect, not the limit.** Both halves of this report — the 500-char
  question cut and the two-version evidence — are the same failure: something was dropped and
  nothing said so.
