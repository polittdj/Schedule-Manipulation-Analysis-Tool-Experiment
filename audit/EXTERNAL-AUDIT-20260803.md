# External audit adjudication — 2026-08-03

**Reviewed commit:** `1119162` (v1.0.159) · **Method:** measurement only. Every number below was
produced by running something in this container; none is transcribed from the audit under review.
**Model:** Opus 5 (Fable 5 unavailable until 2026-08-06 01:00; per ADR-0240 the engine/CPM items
this audit touches were *not* worked, only measured).

An external review submitted 13 "independently revalidated leads" and asked that each be
reproduced or refuted. All 13 were tested.

## Headline

**No product-correctness defect was found.** No computed number, metric, parity value, or rendered
figure is implicated by any of the 13. The genuine findings are **CI reproducibility** (#1, #2) and
**repository hygiene / provenance** (#3, #4, #5, #7).

The audit's three "VERIFIED CONTROL" items all reproduced exactly. The one HIGH it was most
specific about (#2) was **17× larger** than reported.

---

## 1 — Dependency specification / reproducibility · structure CONFIRMED, stated failure REFUTED

**Refuted as stated.** A clean `pip install -e '.[dev]'` succeeded in fresh venvs on **both**
interpreters the audit asked for:

| | result | resolution |
|---|---|---|
| Python 3.11.15 | `rc=0` | fastapi 0.141.1 · starlette 1.3.1 · httpx 0.28.1 · httpx2 ABSENT · pytest 9.1.1 |
| Python 3.13.12 | `rc=0` | identical |

On 3.13 the web suite collects **1488 tests**. The audit's "collection of 147 web-related modules
failed" is an environment with *neither* `httpx` nor `httpx2` installed — the audit flagged that
caveat itself.

**Structure confirmed.** Starlette 1.3.1's `testclient` tries `httpx2`, falls back to `httpx` with
a `StarletteDeprecationWarning`, and raises `RuntimeError` only if neither is present (source read
verbatim). There are **no upper bounds anywhere** and **no lock or constraints file**. Two
aggravating facts found while checking:

* `pyproject.toml` already carries
  `filterwarnings = ["ignore:Using \`httpx\` with \`starlette.testclient\`:DeprecationWarning"]` —
  the upstream deprecation was **silenced rather than bounded**.
* `[tool.pytest.ini_options] minversion = "8.0"`, and `dev = ["pytest>=8"]` — see #2, which is the
  existence proof that the same commit passes or fails on resolver choice alone.

## 2 — Test pollution · CONFIRMED, and 17× larger than reported

Mechanism confirmed by direct state probe, not inference: `configure_logging()` sets
`propagate = False` on the `schedule_forensics` logger (correct for the shipped tool — Law 1) and
nothing restored it. `caplog` captures by propagation to the root logger.

**Polluters — per-test bisect, each run immediately before a known victim:**

| module | polluting tests |
|---|---|
| `tests/exhibits/test_cli_guards.py` | **1** (the one reported) |
| `tests/test_launcher.py` | **12** |
| `tests/test_logging_redaction.py` | **4** |

**Victims (4, all `caplog`-based):** `test_mspdi.py::test_a_dangling_project_calendar_uid…`,
`::test_a_missing_project_calendar_uid…`, `test_xer.py::test_an_unmatched_project_clndr_id…`,
`::test_a_missing_calendar_table…`.

**Version-sensitive — the audit's own question, answered.** Same tree, only pytest changed:

| pytest | victim alone | after a polluter | full suite |
|---|---|---|---|
| 9.1.1 | pass | **pass** | 3400 passed, 3 skipped |
| 8.4.2 | pass | **FAIL** | **5 failed**, 3301 passed, 42 skipped, 2 errors |
| 8.0.2 | pass | **FAIL** | — |

pytest 9.1.x also attaches its capture handler to the `schedule_forensics` logger, masking the
leak; the leak is nonetheless **live on 9.1.1** (probe: `propagate = False` after the polluter).
**Hosted CI does not currently reproduce it** — `pytest>=8` resolves to 9.1.1 and #525/#526 merged
with six green checks.

**Of the pytest-8 "5 failed / 2 errors": 4 are this defect. The other 1 failure + 2 errors are
`ModuleNotFoundError: playwright`** in a lean venv — `tests/perf/test_observer_storm.py:136` and
`tests/web/test_launch_invalidation.py` use a bare `from playwright.sync_api import …` where
`tests/web/test_r11_panel_contract.py:817` correctly uses `pytest.importorskip`. Not a pytest
incompatibility; a skip-vs-error gap. (An earlier reading of mine called it a pytest-8
incompatibility — wrong, corrected here.)

Fixed under **ADR-0345**.

## 3 — Mislabeled tracked intake files · CONFIRMED (89), but scoped to non-product files

Magic-signature + SHA-256 sweep over all **1452** tracked files: **89 extension/content
mismatches**, of which **86 are in `00_REFERENCE_INTAKE/`** and 3 were **false positives of my own
sniffer** (a 64-byte decode window splitting a multi-byte UTF-8 character in three `.py` files —
all decode cleanly in full).

Every specific example in the audit reproduced:

| audit claim | measured |
|---|---|
| an `.mp4`, `.html`, two `.txt` are one DOCX ZIP | `Recording 2026-07-27 150631.mp4`, `Mission Ops Redesign v2.dc (1).html`, `concepts_b.txt`, `int02_advanced.txt` — all sha256 `272662cf43015e28…`, all ZIP/OOXML |
| `concepts_a.docx` is a PDF | yes — byte-identical to `INT-02-Advanced-Schedule-Analysis.pdf` (`859faf30473a…`) |
| `.png` screenshots are HTML | yes (several), plus many `.png` that are JPEG |
| another `.png` is a PDF | `draw-54db3784-….png` |
| `a11y.js` is JSON | yes (starts `{`) |
| `heartbeat.js` is the favicon ICO | yes (`\x00\x00\x01\x00`) |
| `base.css` is the a11y JavaScript | yes — content is *"chart accessibility helpers (Section 508 / WCAG 1.1.1)"* |

Intake also holds **24 duplicate-content groups over 54 files**. The pattern is a bulk-upload
**name/content rotation**, not random corruption: `Concepts, Methods & Techniques-272662cf.docx`
literally carries the correct hash prefix of a *different* file's content.

**Scope — the decisive measurement.** Everything the product depends on is intact:

| asset class | result |
|---|---|
| shipped `src/schedule_forensics/web/static/*` | **65/65 self-consistent** |
| `.aft` metric libraries ("the Bible") | both parse as XML — **1443** and **1403** `<Metric>` |
| golden MSPDI fixtures | **16/16** valid XML |
| golden XER | **1/1** |
| intake `.mpp` | **20/20** valid OLE2/ZIP |

So this is a provenance and documentation problem, not a correctness one. No test reads a
mislabeled file (the parity/formula tests read the `.aft` and the goldens, all verified above).

## 4 — Stale risk register · CONFIRMED

* **R-03** — *"**Open item:** the two source `.mpp` schedules not yet in the provided set"*, status
  `Open (mitigating)`. Both are tracked, **twice each**: `00_REFERENCE_INTAKE/Project2.mpp`,
  `00_REFERENCE_INTAKE/mpp/Project2.mpp`, and the same for `Project5_TAMPERED.mpp`.
* **R-12** — *"deposited `.mpp`/golden files are gitignored (Law 1) and live only in the depositing
  session's ephemeral container, so a fresh session's `00_REFERENCE_INTAKE/` is empty."* Directly
  contradicted by ADR-0151/0152, which committed the intake suite.

## 5 — CUI commit-hook coverage · CONFIRMED, with more gaps than listed

Scratch-repo test of the real `.githooks/pre-commit`, schedule-bearing synthetic content in every
file (no real CUI used):

| path | result |
|---|---|
| `root.mpp`, `sub/deep.mpp`, `schedule.MPP`, `export.xlsx` | **BLOCKED** |
| `tests/fixtures/real.mpp` | ALLOWED — unconditional fixture allowance |
| `schedule.json` | ALLOWED |
| `notes.txt` | ALLOWED |
| `data.mpp.bak` | ALLOWED — the regex anchors on `$` |
| `sched.p6xml` | ALLOWED — a real Primavera format, absent from the denylist |

`.gitignore` covers `*.mpp` and `*.mpp.bak` but **deliberately not `*.json`** (documented choice,
so tracked config stays visible) — and `.json` is **the tool's own Save format**. The hook is
extension+path based: correct as defense-in-depth behind `.gitignore`, **not** a content-aware
boundary. Consistent with the audit's framing; no claim of actual CUI exposure is made.

## 6 — License / provenance · CONFIRMED verbatim

`LICENSE` reads *"PLACEHOLDER (to be finalized)"*, *"No grant of rights is made"*, *"Do not
redistribute"*, and ends with *"TODO (tracked for a later session): choose and commit the final
license text"*. It scopes itself to source code only and explicitly disclaims any rights over CUI.
Vendored assets (MPXJ jars, the NASA `.aft` libraries, reference exports) need qualified
legal/procurement review — an operator decision, not an engineering one.

## 7 — Supply chain · CONFIRMED

* Actions on **mutable major tags**: `actions/checkout@v5` (×2), `actions/setup-python@v6`,
  `actions/checkout@v4` (×2), `actions/setup-python@v5`. No SHA pins.
* `curl -fsSL https://ollama.com/install.sh | sh` at 8 installer sites, **no checksum**. Correctly
  *not* silent: it sits behind `read -r -p "Install Ollama + pull '$OLLAMA_MODEL'…? [Y/n]"`. But
  the guard is `[[ ! "$ans" =~ ^[Nn] ]]`, so bare Enter proceeds.
* Worth noting: the **MPXJ download immediately above it in the same file *is* SHA-256 verified**.
  The pattern already exists; ollama just doesn't use it.

## 8 — Browser aggregation · mechanism CONFIRMED, policy half UNVERIFIABLE here

`.github/workflows/ci.yml`: `check:` has `needs: test` only. `browser:` (line 88) is a sibling with
no edge into `check`. So the aggregate context genuinely does not depend on the browser job.

**Whether that permits merge depends on branch-protection required contexts, which I cannot read
from this environment** (no branch-protection tool available). One datum: **PR #526 merged while
`linux` and `windows` never registered at all** — only 4 of 6 checks ran. Operator action:
Settings → Branches → required status checks.

## 9 — MPXJ Java source/class · REPRODUCED exactly

`javac --release 17 -cp "tools/mpxj/classes:tools/mpxj/lib/*"` (javac 21.0.10) on
`tools/mpxj/MpxjToMspdi.java`:

```
committed   1a2c05dc0d4e038a3cb99d57cec3f2fc2a33fbe9993ab4d14069a9a7016363cd
recompiled  1a2c05dc0d4e038a3cb99d57cec3f2fc2a33fbe9993ab4d14069a9a7016363cd
```

Exact match. The audit's control holds; no source/class mismatch is reported.

## 10 — Installer source lockstep · REPRODUCED exactly

`tests/installer` **52** + `tests/test_packaging.py` **4** + `tests/test_operator_kit.py` **6** =
**62 collected, 62 passed**, matching the audit's figure. Native Windows/macOS behaviour remains
unverified here, as the audit said.

## 11 — Egress guards · REPRODUCED

`tests/guards` — **68 collected, 68 passed**. No reachable bypass was searched for beyond the
existing suite; per the audit's instruction, the mere existence of a finite denylist is not
reported as an exploit.

## 12 — Parity · REPRODUCED, with the oracle limitation intact

`pytest -m parity` — **49 collected, 49 passed**. Provenance audit of what those assertions read:
**13** references to `case.json` (a human transcription of Acumen output) against **2** to
committed reference artifacts — `test_sra_ssi_oracle_uid152.py`, which reads SSI's own exported
results *and* the `.mpp` carrying SSI's input set, and the committed Acumen EVM exports.

The audit is right that 49 green ≠ independent equivalence to Acumen / SSI / MS Project. **This is
already documented in-repo**, not a hidden gap: `audit/PATH-FORWARD.md` §C-7 ("the oracle itself
may be wrong") and §A-1 (de-circularization) state the same limitation, and `PARITY-REPORT.md`
marks the formerly engine-pinned §E subset explicitly. Upgrading any row from "engine == golden" to
"engine == Fuse" requires the operator's proprietary tools.

## 13 — Status classification

| category | items |
|---|---|
| **Release blockers** | none |
| **Numerical defects** | none found by this audit (CC-01 / SRA-LEGACY pre-date it, are tracked, and are reserved for a Fable 5 Max deep dive per ADR-0240) |
| **CI reliability** | #2 (fixed, ADR-0345), #1 (next unit) |
| **Repo hygiene / provenance** | #3, #4, #5, #7 |
| **Legal** | #6 — operator only |

The audit's closing caution is endorsed: an open task does not disprove "built". The open items are
maintainability, presentation debt, and two tracked engine questions — none of which changes a
number the tool reports today.

---

## Remediation order

**P0** — logging isolation (**done**, ADR-0345) · constraints file + upper bounds + a floor-version
CI leg · `importorskip` in the two bare-import modules.
**P1** — intake manifest with an extension↔content regression test · reconcile R-03/R-12 · harden
the CUI hook (`.json` content sniff, `.p6xml`, `*.mpp.*`) · pin Actions to SHAs.
**P2 (Fable 5)** — CC-01 · SRA-LEGACY · V3.
**Operator only** — license selection · branch-protection required contexts · intake re-upload ·
proprietary-tool reruns for #12.
