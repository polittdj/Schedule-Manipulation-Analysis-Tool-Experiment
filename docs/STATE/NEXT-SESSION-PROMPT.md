# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. **Re-attach the files listed at the
bottom** — uploads from the previous session do not carry over to the new one. The reference
schedules and Acumen exports themselves are on disk under git-ignored `00_REFERENCE_INTAKE/audit/`
and will already be there, but the kickoff still needs to know they exist.

---

We're mid-stream on a multi-PR **Acumen validation campaign** on the Schedule-Manipulation-Analysis
tool. `main` is green at PR **#204** (`8949a34`, `fix(dcma): High Float scores on stored Total Slack
— exact Acumen parity (ADR-0109)`). PR #203 (`056020d`, EVM goldens + ADR-0108) is also in. **Read
`docs/STATE/HANDOFF.md` first** — the post-#204 "STATUS (current)" block is the full picture.

**My mandate (verbatim):** "The tool must generate the same results as SSI and Acumen Fuse when
completing analysis on `.mpp` files. Analyze everything. Assume nothing. Validate all aspects of the
tool and make sure the tool is generating the same values as Acumen Fuse. Fix all fidelity gaps. Do
1 and 2 after auditing everything else." (1 = MS Project in-progress data-date scheduling /
progress-scheduler, ADR-0108. 2 = cost/value-based Earned Schedule.)

**What was validated last session (all on the authoritative `.mpp` files I supplied):**
- **Project2 / Project5_TAMPERED** vs `P2-P5 - Metric History` — engine matches Acumen across the
  ribbon. **DCMA-06 High Float fix shipped (#204)** → exact 44/44. **Key finding:** the committed
  `tests/fixtures/golden/project2_5/Project5.mspdi.xml` is **STALE** (4 stored-critical in the
  current `Project5_TAMPERED.mpp` vs 37 in the golden). Refreshing it is a 37-test re-baseline.
- **EVM1 / EVM2** vs `EVM- Metric History Report` (PR #203). Residuals = #1 and #2.
- **Large Test File (1723 non-summary activities)** vs `Large Test File - Metric History` —
  **matches Acumen on every metric checked** (Missing Logic 22, Logic Density™ 3.14, Critical 33,
  Hard Constraints 1, Negative Float 31, Insufficient Detail™ 43, Lags 8, Leads 1).
- The `.aft` "Bible" (`NASA Metrics_Complete_20260423.aft`, 763 verbatim NASA formulas) arrived and
  is on disk — it settled an apparent Missing-Logic inconsistency (the formula is period-windowed:
  full-project when run normally, to-go when run from status; the tool already produces both).

**Reference corpus on disk (git-ignored under `00_REFERENCE_INTAKE/audit/` — DO NOT MOVE OR DELETE):**
- `p2p5/` — `Project2.mpp` + `Project5_TAMPERED.mpp` + full Acumen exports.
- `cei/` — **the biggest delivery**: `Large Test File.mpp` + reports, CEI cross-version report, the
  `.aft` Bible, copies of every prior source `.mpp` plus `TP1..TP4_DataCenter_v1..v5`.
- `evm_hist2/` — `EVM1 Forensic Analysis Report.xlsx` carries Acumen's **per-task** Start / Finish /
  Early-Start / Early-Finish — exactly what the progress-scheduler (#1) needs to validate against.
- Fresh MPXJ conversions already on disk: `p2p5/Project2_fresh.xml`, `p2p5/Project5_fresh.xml`,
  `cei/LargeTestFile.xml`. Re-convert any other `.mpp` with
  `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in.mpp> <out.xml>`.

**Build next, in this order — one PR each, fully gated:**

1. **`.aft` formula audit** (safe, read-only, highest value). For each metric the tool documents in
   `src/schedule_forensics/web/help.py`, parse the matching `<Metric>` from
   `00_REFERENCE_INTAKE/audit/cei/NASA Metrics_Complete_20260423.aft`, normalize both formulas, and
   assert they match. New file `tests/engine/test_aft_formula_audit.py` (NOT marked parity — this is
   a definitional check). Mismatches get written into a single ADR with each gap classified
   (notation difference vs real definitional drift). No engine changes in this PR.

2. **CEI / HMI cross-version validation** against `cei/CEI - Metric History Report.xlsx` (LTF →
   LTF2, the first cross-version reference on disk). Add a `test_cei_acumen_reference.py` modeled on
   the existing `tests/engine/test_evm_acumen_reference.py`. Pin matches; document residuals.

3. **Refresh the stale Project5 golden** — a **deliberate re-baseline PR** titled
   `chore(golden): refresh Project5 to authoritative Acumen export — re-pin 37 tests`. Swap in
   `cei/Project5_TAMPERED.mpp` → MSPDI → golden + update `case.json`; re-pin every failing test
   against the current Acumen values. Tighten DCMA-06 Project5 from documented residual to exact
   (ADR-0109 already anticipates this). Update HANDOFF + new ADR.

4. **Progress-scheduler (#1, ADR-0108)** — now buildable. Model MS Project's data-date scheduling
   for in-progress work, validate task-by-task against `evm_hist2/EVM1 Forensic Analysis
   Report.xlsx` (Start / Finish / Early-Start / Early-Finish sheets), and re-run EVM1/EVM2 + the
   refreshed Project5 to ensure no parity regression. Prior attempts broke parity because the P5
   golden was stale — that excuse is gone after step 3.

5. **Cost / value-based Earned Schedule (#2)** — closes the SPI(t) residual on EVM2 (engine 0.27 vs
   Acumen 0.56). Use `EVM3- Detailed Metric Report.xlsx` as the cost-ES reference.

6. **SSI parity** if any SSI export shows up.

**Optional inputs I asked for last session (still useful but not blocking):**
- Source `.mpp` for **Large Project2** (have its Acumen reports, no schedule).
- Acumen reports for **Project3, Project4, Project2(Duration Bomb)**, the **TP1..TP4** suite —
  ideally as snapshot chains (`P2→3→4→5` in one workbook; `TP4_v1→v5` in one workbook → Metric
  History Report; TP1/TP2/TP3 as separate-project runs).
- **Any SSI export** — the mandate names SSI explicitly; only Acumen is on disk so far.

**Workflow:** branch from `main` (squash-merges make stacked branches conflict; branch fresh and
merge-resolve rather than stacking). One PR per piece. Full gate green before each push: `ruff
check src/ tests/`, `ruff format --check .`, `python -m mypy src/`, `bandit -q -r src`,
`python -m pytest -q` (parity included). Update `docs/STATE/HANDOFF.md` + append to
`docs/STATE/SESSION-LOG.md` with the new ADR number appearing in both (the drift guard
`tests/test_state_docs.py` enforces this — highest ADR on disk must show up in both files).

**Two non-negotiable laws (CLAUDE.md):** (1) **Data sovereignty** — no schedule content leaves the
machine; the AI is loopback-only and fails closed; never commit `.mpp/.xlsx/.aft/.docx/.xer`; the
pre-commit guard catches them; runtime I/O is std-lib only. (2) **Fidelity over speed** — numbers
must match Acumen/SSI on the same inputs; parity is gate-locked (`pytest -m parity`).

**Please re-attach these files to this new session** (they're already on disk under
`00_REFERENCE_INTAKE/audit/`, but the upload mechanism doesn't carry across sessions):
- `Large_Project2_Acumen__DCMA_Report1.zip`
- `TP1_Library_Progressed.zip`
- `EVM_Metric_History_Report.zip` (the EVM hist-2 bundle with the Forensic report)
- `Workbook1__DCMA_Report.xlsx`
- `P2P5__DCMA_Report.zip`
- `CEI__Metric_History_Report.zip` (the biggest bundle — contains the `.aft` Bible)

---

## Quick reference (entry points already on `main`)

- **Engine:**
  - CPM: `src/schedule_forensics/engine/cpm.py` (`compute_cpm`, `offset_to_datetime`).
  - Metrics: `src/schedule_forensics/engine/metrics/` — one module per family. `_common.py` has the
    canonical `effective_total_float` / `is_effective_critical` (prefer stored Total Slack /
    Critical when the source carries them; this is what closed DCMA-06 in #204).
  - DCMA-14: `dcma14.py`. Schedule quality: `schedule_quality.py`. EVM: `evm.py` (count-based ES —
    this is what step 5 replaces with value-based).
- **Importers:** `mspdi.py` (the rich path); `xer.py`; `json_schedule.py`. `.mpp` requires the
  vendored MPXJ Java tool — see CLAUDE.md for the conversion command.
- **AI:** `src/schedule_forensics/ai/` — loopback-only `route_backend`; never reaches cloud.
- **Web UI:** the entire app is in `src/schedule_forensics/web/app.py` (E501 exempted in
  `pyproject.toml`); CSS/JS are vendored under `web/static/`. `SessionState.scope()` is the
  session-wide filter funnel.
- **Help / metric dictionary:** `src/schedule_forensics/web/help.py` (definition + formula + source
  per metric — regenerate `docs/METRIC-DICTIONARY.md` from it with the one-liner in CLAUDE.md after
  any change; a test enforces sync).

## Files most likely to be touched next
- `tests/engine/test_aft_formula_audit.py` (NEW, step 1).
- `src/schedule_forensics/web/help.py` (read-only for step 1; possibly updated `formula=` strings).
- `tests/engine/test_cei_acumen_reference.py` (NEW, step 2).
- `tests/fixtures/golden/project2_5/Project5.mspdi.xml` + `case.json` (step 3 — refresh).
- `src/schedule_forensics/engine/cpm.py` forward pass (step 4 — careful; gate-locked).
- `src/schedule_forensics/engine/metrics/evm.py` (step 5 — add value-based ES path).
