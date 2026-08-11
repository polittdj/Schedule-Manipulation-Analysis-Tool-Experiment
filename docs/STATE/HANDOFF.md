# Handoff — 2026-08-10 (f) (parity: the record understated the gate, and the gate could stop measuring; ADR-0385; v1.0.192 unchanged)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-jmti4s`
> (this container's designated branch, restarted from `main` bb4035a after #569 squash-merged).
> **NO version bump and NO installer rebuild** — `src/` is untouched; this is evidence, tests and
> CI only, so the wheel + nine installers stay at **v1.0.192** and remain in lockstep. Highest ADR
> now **ADR-0385**. SCHEMA stays 2.11.0.
>
> **Operator asked for whatever most improves accuracy/consistency vs Acumen, SSI and MS Project.**
> The big levers are operator-gated (licences), so the question became: what is reachable from
> here that actually moves *measured* fidelity? Measuring first found TWO things.
>
> **(1) The parity record claimed an SSI gap that had been CLOSED for a month.** Both
> `case.json._deltas.ssi_driving_slack_golden` AND `docs/PARITY-REPORT.md` said SSI driving slack
> had a stale golden and a live **`xfail`** "pending a fresh SSI export". Every clause was false:
> `tests/fixtures/golden/ssi_uid143` **does not exist**, `test_ssi_driving_slack_exact` **does not
> exist**, and the replacement export **arrived 2026-07-08** (ADR-0154/0155). What replaced it —
> both IN the parity gate, both **exact by UniqueID** on the authoritative `Project5_TAMPERED.mpp`
> — is `ssi_uid67` (Directional Path, Driving Slack ≤ 0 d: the exact **20-task** Path-01
> membership, all at 0 days) and `ssi_uid145` (all-dependencies: **108 UIDs** + tiers 2/3/8/95).
> So the tool's own record **UNDERSTATED measured SSI fidelity** — the expensive direction to be
> wrong in for a testimony artifact. Corrected in both places.
>
> **(2) The Law 2 gate could silently stop measuring.** The `browser` job has carried a
> *"Fail loudly if the proof silently skipped"* step since ADR-0305; **the parity gate had no
> equivalent**, while being conditional three ways (`needs_java` on the SSI SRA Monte-Carlo
> oracles via vendored MPXJ, `needs_mpp`/`needs_artifacts` on `00_REFERENCE_INTAKE/`, and a
> `pytest.skip` inside `_oracle_workbook()`). Measured, not hypothesised: with `java` hidden,
> **8 of the 52 parity tests vanish in 0.25 s and `pytest -m parity` exits 0** — a green badge
> over a run that compared nothing to Acumen or SSI. Both the `test` and `floor` jobs' parity
> steps are now the guarded form (run · `tee` · fail on ANY skip), **scoped to the parity PATHS**
> because a bare `-m parity` also collects-and-skips the playwright modules and would
> false-positive forever. Runtime unchanged — the guarded step REPLACES the old one.
>
>
> **(3) A GUARD WAS PINNING THE STALE CLAIM.** Correcting the report turned
> `tests/web/test_docs.py::test_parity_report_states_the_headline_results` RED: it asserted
> `"107" in parity`, and `107` appeared **only** in the two retired `ssi_uid143` lines. A doc guard
> was holding the false statement up — the easy "fix" was to put the stale number back. Repointed
> to the live oracles, made stronger (2 assertions where there was 1), then tightened again because
> bare `"108"` is satisfied by the string **`ADR-0108`**; it now asserts `"108 UIDs"`, falsified by
> gutting the SSI row with every `ADR-0108` mention left intact.
>
> **(4) THE GUARD'S OWN FIRST VERSION TRADED ONE SILENCE FOR ANOTHER — caught on this PR's CI.**
> GitHub's default `run:` shell is `bash -e {0}`, `-e` WITHOUT pipefail, so `pytest … | tee` takes
> **tee's** exit code. Replacing the bare `pytest -m parity` with a piped step meant a genuine
> parity FAILURE would have exited 0 — hardened against the oracles silently not running, opened to
> them silently failing. `set -o pipefail` added to both jobs and commented as load-bearing.
> Three-branch truth table on the exact block: clean → 0 · skipped → 1 · **failed → 1** (was 0).
> The `browser` job lacks this hole only because its tee'd check is preceded by an un-piped run —
> **replacing a bare run rather than adding to it is what removed that protection.**
>
> **CI ANSWERED THE EXPERIMENT: `floor` PASSED with the skip guard live** ⇒ the runner HAS Java and
> the 8 SSI/Acumen Monte-Carlo oracles HAVE been running on every PR all along. They are now
> protected. `setup-java` is therefore NOT needed — do not add it.
>
> ## Verification
> Parity gate full: **52 passed, 0 failed, 12m35s**; every skip in the unscoped run is
> playwright/UI, **no parity test skipped**. Scoped: **52 passed, 0 skipped**. The two new guards
> **proven able to fail**, each by a NAMED test, restores md5-verified (cite `golden/ssi_uid999`
> → `…never_cites_a_golden_that_does_not_exist`; resurrect the `⚠ stale, xfail` row →
> `…xfail_claim_stays_retired`). The **CI guard proven end-to-end**: java hidden → 8 oracle tests
> skip → its own `grep` FIRES; against the real clean run it stays SILENT (no false positive).
> `case.json` edit is ONE line, structurally verified that only that `_deltas` key changed.
> Report numbers were READ from the goldens first (uid67 = 20 UIDs / 20 at zero slack;
> uid145 = 108 UIDs / tiers 2-3-8-95), never transcribed from prose.
>
> ## Next
> **Deliberately NOT done, and it is the honest next step: `setup-java` is NOT pinned into CI.**
> Action pins require a 40-hex SHA (`tests/guards/test_workflow_action_pins.py`), and adding the
> JDK *with* the guard would have MASKED the answer. If CI has been running the oracles all along
> the guard passes; if it has not, **this PR's CI is where that surfaces** — and the fix is a
> SHA-pinned `actions/setup-java` in the `test` and `floor` jobs. **Watch this PR's parity step.**
> Then: the in-tool metric dictionary still does not warn an analyst about the two *scope*
> differences vs Acumen that `PARITY-REPORT.md` documents correctly — `SN01` (engine 126
> schedulable vs Acumen's §E header 144 incl. 18 WBS summaries) and `missing_logic` (engine
> all-activity 6/7 vs Acumen's report-scoped incomplete = DCMA01 4/5). Both are EXACT at their own
> scope, so this is a consistency fix for side-by-side comparison, not an accuracy one: add the
> reference-tool scope note to `web/help.py` and regenerate `docs/METRIC-DICTIONARY.md`.
> Then phase 4 slice 21 (`wbs` 110, `brief` 44 zero-descent; re-price by referrer walk) and the
> standing queue: stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less
> pages · /groups Activities (ADR-0343) · installers vs known-good constraints · P80/P90 residual ·
> doc-drift sweep (PARITY-REPORT's git-ignored claim + Project2 "CUI intake" are STILL unfixed —
> this session only corrected the SSI section; FINAL-REPORT blanket "exact match"; CLAUDE.md
> phase-3/E501 lines) · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator (the only remaining ways to raise measured fidelity vs the three tools):** one Acumen
> run on a crafted sub-day-negative-float schedule (closes the Negative-Float O1 gap the `.aft` has
> NO formula for) · re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse ·
> license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0385 closed — do not re-open. **The oracle no longer needs rebuilding: import it**
> (`python tests/web/oracle_corpus.py --out <dir>`, `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures`). NEW lessons this session: (1) **a residual ledger is
> a CLAIM, not a fact** — it was true when written and nobody re-read it when the gap closed; an
> evidence record needs a guard exactly like code does; (2) **string-pinning a correction only
> catches that instance** — pin the property that generalises (every golden cited BY PATH must
> exist; a historical mention is a bare name, because a path is an instruction to go and look);
> (3) **a conditional gate is a gate that can stop being one** — `needs_java` + green + 0.25 s is
> indistinguishable from "passed" unless something asserts nothing skipped; (4) **do not fix and
> mask in the same change** — adding `setup-java` beside the guard would have hidden whether CI
> ever ran the oracles. Standing traps unchanged (a quiescence guard can match its own shell — it
> did again here, adjudicate by scanning `/proc` for real python processes · `ast` col_offset is a
> BYTE offset · a page-only anchor understates an export-feeding member · route-only referrers
> never force a descent · sweep by BARE NAME · a diff is the wrong surface for an import question ·
> fingerprints carry their SCOPE · a normalizer that fails silently is a flap factory · never
> MEASURE or MUTATE a tree a suite is running against · patch the patcher with landed-count
> discipline · named-failure rule and its own parser · empty sweep needs a positive control ·
> `grep -c` exits 1 on zero · three-tier parity evidence · stored-vs-recomputed float is the
> single most-repeated engine ambiguity — triage a slack variance there FIRST · B608 house nosec ·
> pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing, CI-invisible ·
> `python -m pytest` prepends CWD to `sys.path` and bare `pytest` does NOT — CI runs the bare one ·
> two ruffs on PATH, run `python -m ruff`). A number written mid-session is not a measurement.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
