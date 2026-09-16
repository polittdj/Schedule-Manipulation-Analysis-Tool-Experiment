# ADR-0498 — The exported `.pptx` DOES load: the register's "LibreOffice refuses it" was an install with no PresentationML filter, which refuses a PowerPoint-authored deck identically (R-52 CLOSED; PowerPoint still UNVERIFIED)

- **Status:** Accepted — 2026-09-15 (audit roadmap §3, R-52, worked as its own unit).
- **Version:** 1.0.266
- **Extends:** ADR-0473 (which recorded the finding), ADR-0465 (the compare deck), ADR-0446 (the one-pager), ADR-0393 (QC-1 / QC-2 — the rules that caught this).
- **Shipped:** `tests/reports/test_pptx_libreoffice_interop.py` (new — the load gate, with its instrument control), `tests/reports/test_onepager.py` (`test_the_package_carries_the_three_parts_powerpoint_always_writes`), `src/schedule_forensics/reports/pptx.py` (`presProps` / `viewProps` / `tableStyles` + their content-type overrides and relationships), `.github/workflows/ci.yml` (the `browser` job installs `libreoffice-impress` and fails on a skip).

## Context

The audit register has carried, since 2026-09-07 (ADR-0473):

> R-52 — the exported `.pptx` — the one-pager AND the compare deck — does not load in
> LibreOffice 7 headless ("source file could not be loaded"); PowerPoint UNVERIFIED.

with a repair step that named a mechanism: *diff the package against a minimal PowerPoint-authored
`.pptx` (presProps / viewProps / tableStyles parts, the content-type overrides, the master's
relationships); fix the writer.* Under QC-2 a register's "first executable step" is a **hypothesis
about the mechanism**, not a finding — this repo has paid for that lesson twice already (R-46's
step asked us to re-derive a series the file already recorded). So the unit began by reproducing
the refusal, not by editing the writer.

### What was measured

**Red, reproduced (2026-09-15, this container).** Both decks were built from the routes' own
renderers and handed to `soffice --headless --convert-to pdf`:

```
red/onepager.pptx (7,706 B)   Error: source file could not be loaded    rc=0
red/compare.pptx  (8,532 B)   Error: source file could not be loaded    rc=0
```

`rc=0`. **LibreOffice exits 0 when it refuses a file** — a gate that reads the exit code would
have called this a pass. Nothing in the new test reads it; the question is always whether the
converted artifact exists.

**Then the control, which is what the original finding never ran.** The same install, the same
command, on a deck **PowerPoint wrote** — `00_REFERENCE_INTAKE/mpp/Politte Schedule Tool.pptx`
(53 parts, `presentationml.presentation.main+xml`, six slides; committed and non-CUI per
ADR-0152):

```
ctl/ref.pptx                  Error: source file could not be loaded    rc=0
```

and on a Microsoft-authored workbook (`00_REFERENCE_INTAKE/P2-P5 - Detailed Metric Report.xlsx`):

```
ctl/ref.xlsx                  Error: source file could not be loaded
```

**The install explains it.** `dpkg -l | grep libreoffice` listed `libreoffice-common`,
`libreoffice-core`, `libreoffice-style-colibre`, `libreoffice-uiconfig-common` — **no
`libreoffice-impress`, no `libreoffice-calc`, no `libreoffice-writer`**. The registry held
`main.xcd`, `Langpack-en-US.xcd`, `lingucomponent.xcd`, `pdfimport.xcd`, `xsltfilter.xcd` and no
`impress.xcd`; `/usr/lib/libreoffice/program/` carried no Impress filter library. "Error: source
file could not be loaded" is that installation saying **it has no import filter for this document
class** — it is not a statement about the bytes it was handed.

**Green, with the instrument repaired.** After `apt-get install -y --no-install-recommends
libreoffice-impress`, LibreOffice 24.2.7.2 420(Build:2) converts all three:

```
ctl/ref.pdf       150,219 B      red/onepager.pdf   48,275 B      red/compare.pdf   56,460 B
```

The PDFs carry the content (`pdftotext`: the CUI marking, the title, the month grid, every
activity label with its date, the compare deck's `+12 cal d` deltas), and the PNG render was read
by eye: title, subtitle, CUI banner top and bottom, year band, month ticks, three swimlane bands,
activity bars with in-bar labels, milestone diamonds, the red TODAY line with its label, the
legend and the provenance footer. Converted instead to flat ODF — LibreOffice's own object model
as plain XML — the one-pager comes back as **1 `draw:page`, 54 `draw:custom-shape`, 10
`draw:frame`, 18 `draw:connector`**, with every label present *and* our selection-pane shape names
(`CUI marking (top)`) intact.

The finding was the instrument. Its version number ("LibreOffice 7") is not the mechanism and was
not re-measured — the mechanism is a missing filter, and it reads the same at any version.

**The register's repair step, run anyway.** A part-list diff of our package against the
PowerPoint-authored deck, with that deck's own content set aside (extra slides, layouts, media,
thumbnail, label info, changes-info), leaves exactly three parts it carries and we did not:
`ppt/presProps.xml`, `ppt/viewProps.xml`, `ppt/tableStyles.xml`. All three are optional — both
decks loaded without them — so they are **not** the cause of anything, and this ADR does not
pretend otherwise.

## Decision

1. **R-52's premise is refuted and the row is CLOSED**, with the mechanism named: an install
   without `libreoffice-impress` refuses every presentation, ours and PowerPoint's alike.
2. **Pin the property that was assumed and never measured.**
   `tests/reports/test_pptx_libreoffice_interop.py` renders both decks, loads each through
   LibreOffice, and asserts the slide comes back with its page count, its words and its shape
   names. It converts to **flat ODF rather than PDF** on purpose: a passing assertion then says
   *Impress parsed these shapes and this text*, not merely *a file opened*, and it needs no
   text-extraction dependency.
3. **The gate may never again accuse the writer of the environment's fault.** Before it judges
   anything, the module loads the PowerPoint-authored control deck. Missing `soffice`, missing
   control deck, or a control deck the install refuses → **skip, with the reason named**. Only
   "the control loaded and ours did not" is a failure.
4. **A skip is a failure where it matters.** The `browser` job installs `libreoffice-impress` and
   runs the module with any skip treated as a failure — the same discipline as the browser census
   and the parity gate. A skip there would mean nothing was measured, which is exactly how the
   original finding survived eight days.
5. **Write the three parts.** Not as a fix — as the removal of a variable. PowerPoint itself is in
   no container a session can reach, so the one lever available is to match what the reference
   implementation writes. Each is the measured minimum of what that deck carries; PowerPoint's own
   MRU colours, window geometry and 2010/2012 extensions are editor state, not document content,
   and are not copied. The empty table-style list's `def` GUID is read out of that deck, not
   remembered.

## Verification (QC-1)

**Red before green, by name.** `test_the_package_carries_the_three_parts_powerpoint_always_writes`
was written first and observed to fail on the pristine writer:
`AssertionError: ppt/presProps.xml is missing from the package`. It went green only after the
writer changed.

**The three parts change nothing LibreOffice reads** — measured, not asserted: the flat ODF of the
one-pager is **byte-identical before and after** (181,935 bytes both; 1 page / 54 custom shapes /
10 frames / 18 connectors both). The deck grows 7,706 → 8,636 B (one-pager) and 8,532 → 9,462 B
(compare).

**Mutation battery — 8 of 8 by name, on a shadow copy of `src/`** (a `-p mutcheck` plugin asserts
the module under measurement IS the copy; the working tree is never mutated):

| # | mutant | verdict |
| --- | --- | --- |
| C0 | none (control) | 2 passed |
| M1 | the package's main content type corrupted | both FAIL — *"LibreOffice refused … while loading the PowerPoint-authored control deck in the same run — the package is the problem, not the instrument"* |
| M2 | every CUI marking emptied | both FAIL — *"LibreOffice loaded the deck but lost 'Controlled Unclassified Information • CUI'"* |
| M3 | every shape loses its name | one-pager FAILS on the selection-pane names |
| M4 | the compare deck's delta annotation emptied | compare FAILS — *"lost '+12 cal d'"* |
| M5 | **the 2026-09-07 instrument** — a `soffice` that refuses everything with rc=0 | **SKIP**, naming the missing PresentationML filter — never a red against the writer |
| M6 | no `soffice` on PATH | SKIP, naming PATH |
| M7 | the PowerPoint-authored control deck absent | SKIP, naming the control deck |
| M8 | the presentation lists the slide twice | both FAIL on the ONE-slide assertion |

M2 took three cuts to land and both earlier runs were recorded as **non-mutations, not
survivors**: the first patched one call site of two, the second left the bottom CUI strip intact
so the probe still found its text. A mutant that does not change the thing under test proves
nothing about the test.

**The CI step, exercised both ways under GitHub's shell semantics** (`bash -e`, `set -o
pipefail`): with a crippled `soffice` on PATH the step prints its `::error::` and **exits 1**;
with the real one it exits 0. An earlier attempt at this proof exited 0 on a collection error
because the local subshell lacked `-e` — the harness was wrong before the step was.

**The full gate** and `-m parity` are reported in the session log with their counts.

## Consequences

- The exported decks are now known to load in an independent implementation, and stay known: the
  claim is re-measured on every push, in a job that cannot silently stop measuring.
- One new apt install (~1 min) in the `browser` job. The check count is unchanged — this rides an
  existing job by the register's own instruction, rather than adding a ninth check.
- The three parts make our package structurally equal to a PowerPoint-authored one, so if
  PowerPoint ever refuses a deck, the cause is in the content and the search space is small.

## Deliberately NOT done (measured, registered, left alone)

- **PowerPoint is UNVERIFIED and is stated as such** — in the register row, in the writer's own
  comment, in the test's docstring and as **V-5** in `OPERATOR-REQUESTS.md`. No container a
  session can reach has PowerPoint; the operator double-clicking either export settles it in a
  minute, and if it complains, its wording names the part.
- **PowerPoint's editor state was not copied** into the three parts (MRU colours, window geometry,
  `p14`/`p15` extensions). It is not document content and nothing measurable argues for it.
- **`python-pptx` was not adopted** as a second reader. It would be a new dev dependency for one
  test, it is not PowerPoint, and it cannot settle the only question left open.
- **The original container's LibreOffice version was not re-created.** The mechanism is a missing
  import filter; the version is not load-bearing, and claiming a re-measurement of "LibreOffice 7"
  would be testimony, not evidence.

## Evidence

Session scratch: `make_decks.py`, `battery.sh` (+ `mutcheck.py`), `battery_C0..M8.log`,
`red/` and `green/` decks, `fodp_cmp/{before,after}/onepager.fodp`, `png/onepager.png`,
`lo_install.log`. The durable form is the two test modules and the `browser` job's two new steps.
