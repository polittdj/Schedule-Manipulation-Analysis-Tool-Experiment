# UI-INVENTORY — Schedule Forensics web UI, as built

Report only — no repo file was created or modified to produce it.

- **Source** `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ tree `10b2cc1b0625` (`main`), read 2026-07-24T21:20Z. `app.py` = **19,081 lines / 969,729 B**, above GitHub's 512 KB search cap, so it was parsed line-by-line rather than searched.
- **Governing law, read first:** repo `CLAUDE.md` and `docs/DESIGN-SYSTEM.md`. The two design laws they impose are the acceptance bar used in §2 — *nothing styles itself* (tokens only; a hex in page markup is a build failure) and *every visual is an instrument* (takeaway headline + labelled data-date line + legend + ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE toolbar, or it is not done).
- **INFERRED** marks anything derived by heuristic rather than read directly. Do not promote an INFERRED cell to a contract without eyes on the rendered page.

---

## 1. Every route in `web/app.py` — 133 total

**41** EXPORT · **1** EXPORT (POST) · **32** HTML · **27** JSON · **32** MUTATION

Classifier (re-derivable): the span from each `@app.*` decorator to the next one is inspected. `FileResponse`/`StreamingResponse`/`Content-Disposition`/`openpyxl`/`Workbook(` in the span, **or** an export-shaped path (`export|download|xlsx|csv|docx`) → EXPORT. Otherwise non-GET → MUTATION; `HTMLResponse` or a `_page()/_html()/_shell()` return → HTML; `JSONResponse`, `-> dict/list` or an `/api/` path → JSON. **INFERRED** where a handler delegates its response class to a helper this parser cannot follow.

### 1.1 HTML pages — 32

| Route | line | Handler |
|---|---|---|
| `GET /` | 3192 | `home()` |
| `GET /analysis/{name}` | 3522 | `analysis()` |
| `GET /card/{name}` | 3561 | `schedule_card()` |
| `GET /wbs/{name}` | 3582 | `wbs_breakdown_view()` |
| `GET /standards` | 3671 | `standards_view()` |
| `GET /portfolio` | 3700 | `portfolio()` |
| `GET /mission` | 3712 | `mission_view()` |
| `GET /compare` | 3736 | `compare()` |
| `GET /path` | 3814 | `path_view()` |
| `GET /trend` | 3983 | `trend_view()` |
| `GET /margin` | 4050 | `margin_view()` |
| `GET /evm` | 4295 | `evm_view()` |
| `GET /resources` | 4306 | `resources_view()` |
| `GET /cei` | 4316 | `cei_view()` |
| `GET /scurve` | 4358 | `scurve_view()` |
| `GET /ribbon` | 4403 | `ribbon_view()` |
| `GET /volatility` | 4444 | `volatility_view()` |
| `GET /performance` | 4691 | `performance_view()` |
| `GET /evolution` | 4752 | `evolution_view()` |
| `GET /integrity` | 4806 | `integrity_view()` |
| `GET /driving-path` | 4875 | `driving_path_view()` |
| `GET /groups` | 4941 | `groups_view()` |
| `GET /forecast` | 5026 | `forecast_view()` |
| `GET /curves` | 5114 | `curves_view()` |
| `GET /workbench` | 5446 | `workbench_view()` |
| `GET /scorecards` | 5840 | `scorecards_view()` |
| `GET /brief` | 6462 | `brief_view()` |
| `GET /risks` | 6481 | `risks_view()` |
| `GET /sra` | 6529 | `sra_view()` |
| `GET /briefing` | 7572 | `briefing_view()` |
| `GET /settings` | 7647 | `settings()` |
| `GET /help` | 7762 | `help_page()` |

### 1.2 JSON APIs — 27

| Route | line | Handler |
|---|---|---|
| `GET /api/system` | 3176 | `system_snapshot()` |
| `GET /api/dashboard` | 3285 | `dashboard_json()` |
| `GET /api/wbs/{name}` | 3604 | `wbs_json()` |
| `GET /api/analysis/{name}` | 3612 | `analysis_json()` |
| `GET /api/driving/{name}` | 3624 | `driving_json()` |
| `GET /api/driving-path` | 3935 | `driving_path_answer()` |
| `GET /api/trend` | 4007 | `trend_json()` |
| `GET /api/margin` | 4016 | `margin_json()` |
| `GET /api/margin/dashboard` | 4064 | `margin_dashboard_json()` |
| `GET /api/margin/risk` | 4280 | `margin_risk_json()` |
| `GET /api/cei` | 4346 | `cei_json()` |
| `GET /api/scurve` | 4380 | `scurve_json()` |
| `GET /api/evolution` | 4849 | `evolution_json()` |
| `GET /api/group-values` | 5011 | `group_values_json()` |
| `GET /api/forecast` | 5106 | `forecast_json()` |
| `GET /api/workbench` | 5457 | `workbench_json()` |
| `GET /api/workbench/drill` | 5532 | `workbench_drill_json()` |
| `GET /api/scorecards/buffer` | 5865 | `scorecards_buffer_json()` |
| `GET /api/activities/drill` | 5940 | `activities_drill_json()` |
| `GET /api/sra` | 6838 | `sra_json()` |
| `GET /api/sra/ssi` | 7003 | `sra_ssi_json()` |
| `GET /api/sra/jcl` | 7098 | `sra_jcl_json()` |
| `GET /api/sra/oat` | 7146 | `sra_oat_json()` |
| `GET /api/sra/grid` | 7207 | `sra_grid_json()` |
| `GET /api/ai/narrative` | 7602 | `api_ai_narrative()` |
| `GET /api/ai/briefing` | 7623 | `api_ai_briefing()` |
| `GET /api/ai/models` | 7708 | `ai_models()` |

### 1.3 Exports — 42

**37 of these are one family** — `GET /export/{fmt}/<panel>` with `fmt` = xlsx|csv — which is the "everything is exportable to Excel" law expressed in code, one endpoint per panel/grid/matrix. **Three rows are context false positives** to correct by hand: `GET /api/curves`, `GET /healthz` and `GET /sra/ssi/save` were flagged only because `Content-Disposition` appears inside the parsed span; the first two are JSON, the third is the SSI grid save/export path. Corrected counts: **39 exports, 28 JSON APIs**.

| Route | line | Handler |
|---|---|---|
| `GET /download/{name}` | 3299 | `download_json()` |
| `GET /export/{fmt}/volatility` | 4470 | `export_volatility()` |
| `GET /export/{fmt}/evm` | 4507 | `export_evm()` |
| `GET /export/{fmt}/scurve` | 4536 | `export_scurve()` |
| `GET /export/{fmt}/resources` | 4565 | `export_resources()` |
| `GET /export/{fmt}/risks` | 4627 | `export_risks()` |
| `GET /export/{fmt}/mission` | 4656 | `export_mission()` |
| `GET /export/{fmt}/performance` | 4717 | `export_performance()` |
| `GET /export/{fmt}/field-forecast` | 5050 | `export_field_forecast()` |
| `GET /api/curves` | 5137 | `curves_json()` |
| `GET /export/{fmt}/analysis/{name}` | 5182 | `export_analysis()` |
| `GET /export/{fmt}/path/{name}` | 5210 | `export_path()` |
| `GET /export/{fmt}/ribbon` | 5281 | `export_ribbon()` |
| `GET /export/{fmt}/float-band/{name}` | 5335 | `export_float_band()` |
| `GET /export/{fmt}/ribbon-drill/{name}` | 5382 | `export_ribbon_drill()` |
| `GET /export/{fmt}/workbench` | 5561 | `export_workbench()` |
| `GET /export/{fmt}/margin` | 5587 | `export_margin()` |
| `GET /export/{fmt}/workbench-drill/{name}` | 5768 | `export_workbench_drill()` |
| `GET /export/{fmt}/scorecards` | 5919 | `export_scorecards()` |
| `GET /export/{fmt}/activities-drill` | 5960 | `export_activities_drill()` |
| `GET /export/{fmt}/resource-drill` | 5989 | `export_resource_drill()` |
| `GET /export/{fmt}/activities/{name}` | 6060 | `export_activities()` |
| `GET /export/{fmt}/driving-tiers/{name}` | 6111 | `export_driving_tiers()` |
| `GET /export/{fmt}/whatif` | 6200 | `export_whatif()` |
| `GET /export/{fmt}/whatif-added` | 6259 | `export_whatif_added()` |
| `GET /export/{fmt}/integrity` | 6308 | `export_integrity()` |
| `GET /export/{fmt}/trend` | 6354 | `export_trend()` |
| `GET /export/{fmt}/cei` | 6366 | `export_cei()` |
| `GET /export/{fmt}/evolution` | 6382 | `export_evolution()` |
| `GET /export/{fmt}/forecast` | 6397 | `export_forecast()` |
| `GET /export/{fmt}/curves` | 6413 | `export_curves()` |
| `GET /export/{fmt}/wbs/{name}` | 6431 | `export_wbs()` |
| `GET /export/{fmt}/compare` | 6446 | `export_compare()` |
| `GET /sra/ssi/save` | 7288 | `sra_ssi_save()` |
| `GET /export/{fmt}/sra` | 7313 | `export_sra()` |
| `GET /export/{fmt}/sra-registry` | 7384 | `export_sra_registry()` |
| `GET /export/xlsx/risk-register-template` | 7429 | `export_risk_register_template()` |
| `GET /export/xlsx/task-risk-template` | 7440 | `export_task_risk_template()` |
| `GET /export/{fmt}/brief` | 7519 | `export_brief()` |
| `GET /export/{fmt}/briefing` | 7547 | `export_briefing()` |
| `GET /healthz` | 7931 | `healthz()` |
| `POST /api/ask` | 3906 | `ask_workbook()` |

### 1.4 POST mutations — 32

| Route | line | Handler |
|---|---|---|
| `POST /api/heartbeat` | 3170 | `heartbeat()` |
| `POST /api/shutdown` | 3186 | `shutdown()` |
| `POST /example` | 3289 | `load_example()` |
| `POST /upload` | 3313 | `upload()` |
| `POST /api/ask/{name}` | 3886 | `ask()` |
| `POST /margin/confirm` | 4072 | `margin_confirm()` |
| `POST /margin/band` | 4112 | `margin_band()` |
| `POST /sra/risk` | 6548 | `sra_risk()` |
| `POST /sra/risk-register` | 6602 | `sra_risk_register()` |
| `POST /sra/branch` | 6666 | `sra_branch()` |
| `POST /sra/conditional` | 6727 | `sra_conditional()` |
| `POST /sra/ssi-run-config` | 6892 | `ssi_run_config()` |
| `POST /sra/correlation-matrix` | 6912 | `sra_correlation_matrix()` |
| `POST /sra/factor-table` | 6951 | `ssi_factor_table()` |
| `POST /sra/factor` | 6971 | `ssi_set_factor()` |
| `POST /sra/auto-calc` | 6980 | `ssi_auto_calc()` |
| `POST /sra/jcl-config` | 7045 | `sra_jcl_config()` |
| `POST /sra/grid` | 7225 | `sra_grid_save()` |
| `POST /sra/ssi/load` | 7299 | `sra_ssi_load()` |
| `POST /sra/import/risk-register` | 7451 | `sra_import_risk_register()` |
| `POST /sra/import/task-risk` | 7485 | `sra_import_task_risk()` |
| `POST /settings` | 7652 | `update_settings()` |
| `POST /settings/ai-off` | 7744 | `ai_off()` |
| `POST /target` | 7786 | `set_target()` |
| `POST /dcma/scope` | 7799 | `set_dcma_scope()` |
| `POST /project/select` | 7810 | `select_project()` |
| `POST /project/exclude` | 7823 | `exclude_version()` |
| `POST /role` | 7831 | `set_role_route()` |
| `POST /language` | 7839 | `set_language()` |
| `POST /api/translate` | 7848 | `translate_api()` |
| `POST /session/wipe` | 7866 | `wipe()` |
| `POST /session/ram-threshold` | 7922 | `ram_threshold()` |

---

## 2. Every chart and visualization — the regression contract

One row per module under `src/schedule_forensics/web/static/`. **INFERRED (grep-derived):** each cell is a source-token test on the real file — (a) `axisTitle|xTitle|axisLabel`, (b) `yTitle|rotate(-90)`, (c) `legend`, (d) `takeaway|headline|howToRead|hint`, (e) `ENLARGE|EXCEL|cf-bar|chartFrame|▦|⤓|⛶`. A **yes** proves the token exists somewhere in the module, **not** that every chart in it renders the element; a **no** on (a)/(b) is a genuine gap to close.

| Module | lines | Page(s) | Chart kinds | (a) X title | (b) Y title | (c) legend | (d) takeaway | (e) toolbar | DD line | `<text>` |
|---|---|---|---|---|---|---|---|---|---|---|
| `gantt.js` | 512 | `/healthz` | gantt/bar/column/line | no | no | no | yes | no | yes | 0 |
| `histogram.js` | 270 | `/healthz` | gantt/bar/column/line | no | no | no | no | yes | no | 0 |
| `curves.js` | 486 | `/healthz` | bar/line/box | no | no | yes | no | yes | yes | 0 |
| `scurve.js` | 350 | `/healthz` | bar/column/line/area | no | no | yes | yes | yes | yes | 0 |
| `drift.js` | 202 | `/healthz` | line/box | no | no | yes | no | no | yes | 0 |
| `path.js` | 708 | `/healthz` | gantt/bar/column/line | no | no | no | no | no | yes | 0 |
| `path_evolution.js` | 517 | `/healthz` | gantt/bar/column/line | no | no | yes | no | no | yes | 0 |
| `driving_path.js` | 260 | `/healthz` | gantt/bar/column/line | no | no | no | no | no | yes | 0 |
| `driving_tiers.js` | 200 | `/healthz` | gantt/bar/column/line | no | no | no | no | yes | no | 0 |
| `cei.js` | 280 | `/healthz` | bar/line/area/box | no | no | yes | no | no | yes | 0 |
| `performance.js` | 532 | `/healthz` | bar/line/area/hist | no | no | yes | no | yes | yes | 0 |
| `resources.js` | 257 | `/healthz` | gantt/bar/column/line | no | no | yes | no | yes | no | 0 |
| `margin_dashboard.js` | 414 | `/healthz` | bar/line/area/box | no | no | yes | no | yes | no | 0 |
| `margin.js` | 272 | `/healthz` | bar/line/box | no | no | yes | no | yes | no | 0 |
| `scorecards.js` | 109 | `/healthz` | — | no | no | no | yes | no | no | 0 |
| `scatter.js` | 160 | `/healthz` | bar/line/scatter/box | no | yes | yes | no | yes | no | 0 |
| `globe.js` | 282 |  | line | no | no | no | yes | no | no | 0 |
| `ribbon_drill.js` | 203 | `/healthz` | gantt/bar/column/line | no | no | no | no | yes | no | 0 |
| `drilldown.js` | 235 |  | bar/column/line | no | no | no | no | yes | no | 0 |
| `findings_drill.js` | 182 | `/healthz` | gantt/bar/column/line | no | no | no | no | yes | no | 0 |
| `workbench.js` | 285 | `/healthz` | bar/column/box | no | no | no | no | yes | no | 0 |
| `volatility.js` | 486 | `/healthz` | bar/line/area/hist | no | no | no | no | no | no | 0 |
| `trend.js` | 1165 | `/healthz` | bar/line/box | no | no | yes | yes | yes | yes | 0 |
| `trend_drill.js` | 235 | `/healthz` | bar/column/line/box | no | no | yes | yes | yes | no | 0 |
| `sra.js` | 515 | `/healthz` | bar/line/area/hist | no | no | no | no | yes | no | 0 |
| `sra_grid.js` | 506 | `/healthz` | gantt/bar/column/line | no | no | yes | yes | yes | yes | 0 |
| `sra_jcl.js` | 283 | `/healthz` | bar/line/scatter/box | no | no | no | no | yes | no | 0 |
| `sra_risk.js` | 81 | `/healthz` | — | no | no | no | no | no | no | 0 |
| `sra_ssi.js` | 433 | `/healthz` | gantt/bar/column/line | no | no | yes | no | yes | no | 0 |
| `wbs.js` | 145 | `/healthz` | bar/line/box | no | no | yes | no | no | no | 0 |
| `whatif.js` | 177 | `/healthz` | gantt/bar/column/hist | no | no | no | no | yes | no | 0 |
| `timeaxis.js` | 104 | `/healthz` | line | no | no | no | no | no | no | 0 |
| `chartframe.js` | 336 |  | gantt/bar/area/hist | no | no | no | yes | yes | no | 0 |
| `legend_toggle.js` | 148 |  | bar/line | no | no | yes | no | yes | no | 0 |
| `vizhints.js` | 637 |  | gantt/bar/column/line | no | no | yes | yes | yes | yes | 0 |

### 2.1 What the shared frame already provides

- **`chartframe.js`** (336 lines) owns the ▦ / ⤓ / ⛶ strip and the play-all coordinator `window.SFPlayAll` (ADR-0275). Modules rendering through it inherit (e) even when their own source shows `no`.
- **`legend_toggle.js`** (148 lines) — interactive legend show/hide (ADR-0276).
- **`vizhints.js`** (637 lines) — the "how to read this" copy; the largest UI text asset in the repo.
- **`timeaxis.js`** (104 lines) + `timescale.js` — the shared time ruler and the stacked Year/Quarter/Month/Week/Day dialog. `taskinfo.js` — the 7-tab Task Information dialog.

### 2.2 Read this before any restyle

The count of modules that draw their own `<text>` nodes (right-hand column) is how much axis labelling is hand-rolled per module rather than inherited. That is the surface area of the "every chart needs a titled X and Y axis" requirement.

---

## 3. Tests that fail if the dashboard JSON payload changes shape

**Primary gate — `tests/web/test_dashboard_perf_contract.py`** (478 lines, 14 tests). Canonical payload hashed at line 134 with `hashlib.sha256(canonical.encode()).hexdigest()`; three pinned constants:

| Constant | SHA-256 | line |
|---|---|---|
| `_SHA_TWO_VERSION` | `d62a4f9e791783701eacc6aeb47ee9b69e0ff80abf4cfeb9bfeddf7b998a58d1` | 358 |
| `_SHA_UNSOLVABLE` | `8d7bcc386168f0e9c3e384bde6beb0789be5beb4b1485a81f0d96138038afc16` | 359 |
| `_SHA_TWO_VERSION_PARITY` | `51691cb7edb1d510ab5a189d989d010ebc93344e182c5adb0a8767c292c504cb` | 364 |

Fixtures the file runs against: `first.json`, `second.json` (the two-version session behind `_SHA_TWO_VERSION` and `_SHA_TWO_VERSION_PARITY`), `cyclic.json` and `r.json` (the unsolvable-network case behind `_SHA_UNSOLVABLE`), plus `Large_Test_File.mspdi.xml` / `Large_Test_File_v2.mspdi.xml`. **INFERRED:** the constant→fixture pairing is by name proximity; confirm with `pytest tests/web/test_dashboard_perf_contract.py -q`.

Tests present: `test_dashboard_builds_zero_full_analyses`, `test_warm_dashboard_is_cache_served_past_the_cap`, `test_concurrent_cold_requests_compute_once`, `test_single_flight_exception_propagates_then_recovers`, `test_distinct_keys_are_not_serialized`, `test_cold_analysis_computes_each_dependency_once_default`, `test_cold_analysis_parity_mode_computes_each_dependency_once`, `test_findings_and_narrative_follow_the_active_audit_per_mode`, `test_dashboard_payload_two_versions_is_byte_identical`, `test_dashboard_payload_parity_mode_is_byte_stable`, `test_dashboard_payload_with_unsolvable_card_is_byte_identical`, `test_mid_flight_wipe_does_not_repopulate`, `test_scope_epoch_key_prevents_cross_epoch_service`, `test_target_control_and_banner_scope_to_active_project`.

**Secondary payload-shape gates (INFERRED from suite layout — run to confirm):** `tests/web/` (136 files, golden dashboard payloads) · `tests/exhibits/test_exhibits.py:194` (SHA-256 digest per emitted exhibit, fixture `tests/exhibits/fixtures/payload_small.json`) · `tests/parity/` (7 files, `pytest -m parity`) · `tests/guards/` (3 files) · `tests/test_state_docs.py` (docs/state sync).

---

## 4. Regenerating the wheel and the 9 installers

**9 = 3 tiers × 3 families.** `tools/installer/build_installers.py` writes `installer/install-tier{1,2,3}.{ps1,sh,command}` from `tools/installer/template.{ps1,sh,command}` with the wheel base64-embedded. Tier config is the only per-tier content: tier1 16 GB / no GPU / `llama3.2:3b` / 2 GB · tier2 64 GB / GPU / `llama3.1:8b` / 5 GB · tier3 128 GB / GPU / `llama3.3:70b` / 43 GB.

```bash
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl
```

**Lockstep enforcement — `tests/installer/test_installers.py` (11,954 B):**

| Test | line | What it enforces |
|---|---|---|
| `test_embedded_wheel_is_in_lockstep_with_the_source_tree` | 120 | every packaged `schedule_forensics/**` file in the embedded wheel byte-matches the source tree (ADR-0148); the assertion message is the regenerate command. This is the gate that catches "reinstalled and got the OLD JS" |
| `test_embedded_wheel_decodes_byte_exact_with_static_assets` | 68 | CRC-valid zip · version matches `pyproject.toml` · **≥30** `/web/static/` entries · a `/web/examples/` file present |
| `test_shared_body_is_identical_across_tiers_no_drift` | 60 | no tier drift inside a family |
| `test_all_families_embed_the_same_wheel` | 86 | ps1/sh/command carry the same wheel |
| `test_three_tiers_exist_with_the_specced_configs` | 45 | tier configs match `docs/PLAN/INSTALLER-SPEC.md` |
| `test_no_cui_or_secret_shaped_content_in_installers` | 112 | no CUI/secret-shaped strings in the script head |
| `test_installers_deploy_mpxj_and_a_single_self_stopping_icon` | 204 | MPXJ deployed; one self-stopping icon (ADR-0193) |

CI: `.github/workflows/ci.yml` — ruff check → ruff format --check → mypy (strict) → `pytest --cov=schedule_forensics --cov-fail-under=70` → engine coverage ≥85% → `pytest -m parity -p no:cacheprovider` → bandit → pip-audit, on Python 3.11 + 3.13, aggregate branch-protection context `check`. Plus `.github/workflows/installer-smoke.yml`.

---

## 5. Typography audit

`base.css` 517 lines / 67 custom-property declarations · `app.css` 1114 / 16 · `hud.css` 170 / 26.

### 5.1 Distinct px font-sizes, with rule counts (all three files)

| size | rules | verdict |
|---|---|---|
| 8px | 3 | **BELOW 11px — FLAGGED** |
| 9px | 10 | **BELOW 11px — FLAGGED** |
| 10px | 15 | **BELOW 11px — FLAGGED** |
| 11px | 41 | base — operator compact standard |
| 12px | 66 |  |
| 12.5px | 1 |  |
| 13px | 25 |  |
| 14px | 11 |  |
| 15px | 5 |  |
| 16px | 9 |  |
| 17px | 1 |  |
| 18px | 2 |  |
| 19px | 1 |  |
| 20px | 1 |  |
| 22px | 3 |  |
| 26px | 1 |  |
| 34px | 1 |  |

Relative sizes (they compound with the 11px base **and** the 90–125% UI-scale control, so effective px varies): `.92em` ×1 · `.8em` ×2 · `.9em` ×1 · `.88em` ×1 · `.85em` ×1 · `0.85rem` ×1 · `1.05em` ×1 · `0.85em` ×1.

**3 distinct sizes are below 11px — 8px, 9px, 10px — across 28 rules.** DESIGN-SYSTEM §1 allows an 8px floor for **mono labels only**; every non-label rule in that set is a violation candidate, and at 90% UI scale an 8px rule renders ~7.2px.

### 5.2 Font stacks, and whether the font exists in the repo

**The base type is set with the `font:` shorthand, not `font-family`** — `base.css` carries `font:11px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif`, so the entire UI face is the **OS system stack**, and the 11px base size does not appear in the `font-size` histogram above. Everything else inherits (`font:inherit` is the only other shorthand in all three files).

| `font-family` stack | rules |
|---|---|
| `ui-monospace,"IBM Plex Mono",Consolas,monospace` | 2 |

- `@font-face` blocks across the three files: **0**. `url(...)` asset references: **0**. Font binaries anywhere in the repo (tree scan for `.woff`/`.woff2`/`.ttf`/`.otf`): **0 files**. Remote font references: **none** — no CDN and no Google Fonts, so the air-gap law currently holds.
- DESIGN-SYSTEM §1 specifies **Barlow** (400/600/700), **Barlow Semi Condensed 700** and **IBM Plex Mono**. Grepping all three stylesheets: **"Barlow" appears 0 times** and **"Barlow Semi Condensed" 0 times**; `IBM Plex Mono` appears only as a *name inside the mono stack* (`ui-monospace,"IBM Plex Mono",Consolas,monospace`) with no `@font-face` behind it. So two of the three specified faces are not merely un-vendored — they are **not referenced at all**, and the display/UI face is the system stack. Vendoring them is simultaneously the fidelity fix, the air-gap prerequisite, and the highest-leverage available answer to "everything looks fussy".

---

## 6. What "Jarvis"/high-tech theming already exists

- **`hud.css`** — 170 lines, 26 custom properties, scoped to `[data-theme=jarvis]`. The HUD skin exists today; it is not a new idea.
- **`base.css`** carries token blocks for `console`, `apollo`, `jarvis` with `daylight` as the `:root` set — all four appearance modes named in DESIGN-SYSTEM §1 are implemented in tokens.
- **`theme.js`** (107 lines) — the header View dropdown, `localStorage` keys `sf-theme` / `sf-theme-dark`, legacy migrations `light→daylight` and `dark→console`, and the #themeToggle daylight↔last-dark mapping.
- **`globe.js`** (282 lines) — the wireframe-globe insignia that doubles as the AI status light (DESIGN-SYSTEM §2). **`sysmon.js`**, **`heartbeat.js`**, **`hints.js`**, **`a11y.js`** supply the live telemetry, hints and focus behaviour a HUD page would read from.
- **`sf-themes.css` is not committed** — the tokens live in `base.css`. Any instruction that says "drop in sf-themes.css" is out of date; treat `base.css` as the token file.
- Consequence for anything new: `jarvis` is a **token remap of the same markup**, and law 1 forbids hand-styling over it. A new high-tech view must be a page built from those tokens, not a second theme system.

---

## 7. What this report could not settle without running the app

1. Per-chart truth for columns (a)–(e) — needs rendered pages, not grep. 35 modules to walk, 32 HTML routes to open.
2. Which of the 27 JSON endpoints are fetched by more than one page (duplicate full-analysis fetches are the scale risk ADR-0281 addresses).
3. Whether any of the 28 sub-11px rules apply to non-label text at 90% UI scale.
4. The constant→fixture pairing in §3, and whether the parity SHA is regenerated by `pytest -m parity`.
5. `installer/` currently commits only `README-DISTRIBUTABLE.md` — the 9 generated scripts are build output, so confirm whether they are expected in-tree or produced per release.
