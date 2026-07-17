# Handoff — 2026-07-17 (deep-audit remediation: CUI-log leak, DOM-XSS embed, cache lock, parity + fail-soft; v1.0.59; highest ADR 0250)

> ## STATUS (current) — ADR-0250: full deep-dive orchestrated audit (10 dimensions × adversarial verify, 22 agents, 12 findings, 0 refuted). 10 code/doc fixes landed + regression tests; 1 finding QUEUED for an operator product decision. Version bumped 1.0.58 → 1.0.59 (wheel + 9 installers regenerated in lockstep). Full gate green incl. `parity`.
>
> - **Law-1 (HIGH) — spaced INTERMEDIATE-directory CUI leak (`logging_redaction.py`).** ADR-0247's
>   `_SPACED_FILE_PATH_RE` tolerated spaces only in the FINAL file name; a spaced *interior* directory
>   (`C:\Users\John Smith\…`, `\\server\CUI Share\…`, `/mnt/My Projects/…` — the near-universal Windows
>   profile / OneDrive / UNC case) broke the whole-path match and the fallback regexes stop at the first
>   space, leaking surname/share/project words (UNC: the whole file name) in clear text. Interior
>   segments now use a separator-bounded, length-capped space-tolerant class (`[^\n\\/]{1,120}`); a
>   space-free path with no sensitive-extension file name still falls through (trailing prose safe).
>   Regression: `test_spaced_INTERMEDIATE_directory_does_not_leak` (4 cases) + idempotence.
> - **Security — DOM-XSS embed (`web/app.py`).** `SF_RIBBON_DRILL` JSON embed now `<`-escapes
>   (`<`) like every sibling embed — `drill_json` + new `labels_json`.
> - **Law-2 (parity) — driving-path walked THROUGH inactive tasks (`engine/path_trace.py`).**
>   `_scheduled_ids` now excludes `not is_summary AND is_active`, byte-matching `cpm._scheduled_tasks`
>   (ADR-0128). Was a parity break + latent `KeyError`. Test: `test_trace_excludes_inactive_tasks`.
> - **Fail-soft (`importers/json_schedule.py`).** (a) malformed `day_segments` len ≠ 2 raised a raw
>   `IndexError` → now `len(s) == 2` guarded; (b) `parse_json` read unwrapped → now
>   `try/except OSError → ImporterError` with `errors="replace"`, like MSPDI/XER. Two new tests.
> - **Supply-chain (`pyproject.toml`).** Runtime floors raised past published CVEs: `jinja2>=3.1.6`,
>   `python-multipart>=0.0.18` (matches the `setuptools>=83.0.0` posture).
> - **Test-quality (`tests/reports/test_xlsx_zip_bomb.py`).** The "budget spans every part" test used
>   ONE part; rewritten with TWO parts each under the cap but summing over it, so it fails if the budget
>   resets per part (genuinely exercises cross-part accumulation).
> - **Concurrency (`web/app.py`).** Polished-narrative LRU `get`/`put`/`clear` now under `state._lock`
>   (NOT across the slow `backend.generate`), closing the D18 race with `ai_off`/scope-invalidation.
> - **Doc-truth.** `REPO-INVENTORY.md` ADR census 241→251 (0000..0250), MPXJ 25→24 jars, top stamp
>   v1.0.59/ADR-0250, runtime-floor line updated; `NEXT-SESSION-PROMPT.md` fully refreshed (its old
>   queue — PR-R2/R3/P1 — had all merged).
> - **State:** v1.0.59; **ADR-0250**; wheel `dist/wheel/schedule_forensics-1.0.59-py3-none-any.whl`
>   rebuilt + all 9 installers regenerated (installer lockstep test green); full gate green (ruff / ruff
>   format --check / mypy --strict / bandit exit 0 / node --check / full pytest incl. the `parity` gate).
> - **NEXT — OPERATOR DECISION first (the 1 QUEUED finding, `ignore-toggles-noop-on-dated`):** the
>   `/driving-path` "Ignore constraints" / "Ignore leveling delay" toggles do NOT use recomputed CPM
>   dates for tasks that carry stored dates, so on a dated schedule the toggle is a no-op while the
>   docstring/UI implies it re-derives the path. **Two honest fixes — a product call, do NOT guess:**
>   **(a)** recompute dates under the toggle (behavior change, re-validate parity vs Acumen/SSI), or
>   **(b)** correct the docstring + UI copy to what it actually does. Ask the operator, then
>   implement + regression-test. Then the standing queue: **#13** XER per-task calendars → base-CPM
>   single-calendar fail-soft disclosure (**#26**) → **F3c** parameterized expected margin → roles
>   front-end (v4 F4). Deferred perf (parked in ADR-0249's harness): import peak memory rides MSPDI
>   streaming, AI-cancellation rides its own PR — deterministic gates only, never wall-clock. Optional:
>   extend per-task Gantt shading to the path-evolution + SRA grids. Operator-side (no code): the
>   `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI + the §4 root-vs-mpp
>   `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
