# Handoff — 2026-08-03g (P1 closed: the intake gets a manifest and the guards get teeth; ADR-0347; v1.0.162)

> ## STATUS (current) — **MERGED, nothing in flight.** PR #533 squash-merged as `ef1ce1f`.
> ADR-0347, **v1.0.162**. The audit's whole **P1** queue in one unit: intake manifest +
> extension&harr;content regression test · R-03/R-12 reconciled (R-14 opened) · CUI hook hardened ·
> nine actions pinned to SHAs. It started as a docs+tests unit needing no bump; **the full suite
> proved otherwise** — see the third headline. Wheel + nine installers rebuilt at **v1.0.162**.
> **All SIX checks green** on `546c502`: `test (3.11)` · `test (3.13)` · `floor (declared minimum)` ·
> `browser (measured-box proof)` · `windows` · `linux`. The nine SHA-pinned action references all
> resolved — every job started, which is the practical proof the pins are valid.
>
> ## THE CI ROUND THIS UNIT COST — the documented gate was a SUBSET of CI's
> The first push went red on **both** `test` jobs. CLAUDE.md and `.claude/skills/full-gate/SKILL.md`
> both prescribed **`ruff check src/ tests/`**; CI runs **`ruff check .`**. `tools/` is in neither,
> so the entire local gate was green while CI found **6** errors in `tools/intake_manifest.py` — two
> dead `# noqa: S101`/`S314` (this repo does not enable ruff's flake8-bandit rules, so the
> suppressions were themselves RUF100 violations), two >100-col rows in the generated preamble, and
> two U+2212 MINUS SIGN literals. Fixed in `546c502`, and **both docs now say `ruff check .`** —
> the root cause, not the symptom. *A local gate that cannot see a directory CI lints is not a
> gate, it is a subset* — ADR-0346's "two correct controls that never meet" landing on the gate
> itself, and it only surfaced because CI happened to be the BROADER of the two.
>
> ## THE HEADLINE — a divergence the audit did not report, on the authoritative parity input
> The two tracked copies of **`Project5_TAMPERED.mpp`** are the **same size with different bytes**
> — 102 of 817,152 (0.0125%). The audit said "tracked twice" and stopped. Measured, not assumed:
> the differing runs sit entirely in the OLE2 **VBA-project storage**; through MPXJ both yield
> MSPDI identical but for `<CurrentDate>` (the conversion clock); through the product importer both
> yield an **equal `Schedule`** — 145 tasks, identical calendars, identical CPM timings, the same
> 4-task critical path (ADR-0112), the same project finish. **No parity exposure.** Both hashes
> are now pinned. `mpp/Project5.mpp` is byte-identical to `mpp/Project5_TAMPERED.mpp`.
>
> ## THE SECOND HEADLINE — the new content detector failed OPEN on its first real-sized input
> `git show ":$path" | head -c 65536 | grep -qaE "$sig"` passed every small fixture and was WRONG.
> `set -o pipefail` takes the last non-zero status, and a truncating reader SIGPIPEs its upstream,
> so the pipeline reports FAILURE even when grep MATCHED. Measured: a **281 KB** saved schedule was
> **ALLOWED** while a 4 KB one was blocked — failing open at exactly the size a real schedule is.
> Fixed with a process substitution (`git show` leaves the pipeline status, and the truncation
> window goes with it). **Falsifying the regression test taught a second thing:** reverting to the
> two-stage `git show | grep -q` does NOT reproduce it — that form wins the same race — so the test
> is only honest against the exact three-stage original. Both facts are recorded in the hook.
>
> ## THE THIRD HEADLINE — hardening the hook exposed a LEAK in a different subsystem
> Adding `.p6xml`/`.xlsm` to the guard turned `tests/test_logging_redaction.py` red, and it was
> **RIGHT**: that test pins the redactor's `SENSITIVE_EXTENSIONS` to the hook's blocklist, and the
> redactor covered neither. `redact("import failed for Runway Program.p6xml")` returned the file
> name **VERBATIM** — a Law 1 leak into logs. Both are now redacted (`<file:p6xml#…>`). Only the
> test's *extraction* was stale (it read the old `blocked_re='\.(exts)$'` shape); its claim was
> sound. **`tests/guards/` was green through every iteration** — this lives in a module reading the
> hook from an entirely different subsystem, and only the FULL suite knew they were wired together.
> Because `src/` changed, this became a **shipped** change: v1.0.162 + wheel + nine installers.
>
> ## THE TRAP THIS SESSION PAID FOR — the documented gate was NARROWER than CI
> CLAUDE.md and the `full-gate` skill both said **`ruff check src/ tests/`**. CI runs
> **`ruff check .`**. `tools/` is in neither, so the entire local gate went GREEN and CI came back
> red with **6** errors in `tools/intake_manifest.py` (two dead `# noqa: S*` for rules this repo
> does not enable, two >100-col table rows, two U+2212 MINUS SIGN literals). **Both docs now say
> `ruff check .`** — run the CI command, not a subset of it. ADR-0346's lesson landing on the gate
> itself: *two correct controls that never meet prove nothing.*
>
> ## The numbers, re-derived — and the audit's 89 reconciled to the file
> **406 tracked intake files, 332,633,606 bytes, 99 mismatches, 27 duplicate-content groups over
> 63 files.** The audit reported 89 and 24/54. `99 − 7 − 3 = 89` **exactly**: the 7 are `.XLS`
> files holding OOXML packages, the 3 are `.json` files holding prose. Neither count is wrong —
> this one states its rule and a test re-derives it. **The rotation reached neither the product nor
> the oracles**: both `.aft` at 1443/1403 `<Metric>`, 20/20 `.mpp` OLE2, 65/65 statics clean, every
> golden well-formed — all asserted from the BYTES, never from the manifest.
>
> ## What landed
> * **`docs/INTAKE-MANIFEST.md`** + `tools/intake_manifest.py` + `tests/guards/test_intake_manifest.py`
>   (10). Hashes the committed **BLOB**, not the working tree: `.gitattributes` sets `* text=auto`,
>   so **128** intake files check out CRLF on Windows. Working-tree hashing would have passed CI
>   (every pytest job is `ubuntu-latest`) and failed on the operator's own machine.
> * **`docs/risks.md`** — R-03 residual re-scoped to what is actually open (**no `.pbix` has ever
>   been deposited**; `pbix/` and `metrics_library/` hold only `.gitkeep`), R-12 **Resolved**,
>   **R-14** opened for intake provenance.
> * **CUI hook, second detector.** `.p6xml`/`.xlsm` added; the `$` anchor replaced by a **closed**
>   backup-suffix set; and a **content sniff** of the STAGED bytes of `.json`/`.txt`/extension-less
>   files for three decisive signatures (Save-`.json`, MSPDI root, XER header). `.json` is the
>   tool's own Save format and is deliberately not in `.gitignore` — extension alone never covered
>   it. `src/schedule_forensics/web/examples/` joins `tests/fixtures/` as an allow-prefix.
> * **Nine actions pinned to commit SHAs**, each with a `# vX.Y.Z` note;
>   `tests/guards/test_workflow_action_pins.py` (5) requires **both**, and carries a vacuity guard.
> * Test delta: `test_precommit_blocklist.py` **21 → 46**, plus 10 + 5 new = **+40**.
>
> ## Verification
> * **All 40 new assertions proved able to fail**, across 16 targeted mutations — including a REAL
>   rotation of a shipped static (`sf-themes.css` given the favicon's bytes) and a corrupted golden.
>   Every tree restored **byte-identical** from a scratchpad copy; never `git checkout`.
> * **Two new tests failed on their first run and BOTH were right.** One caught that the intake
>   legitimately tracks blocked-extension files under ADR-0152's `inherited_from_main` rule (my
>   assertion was wrong, not the hook); the other caught that the repo tracks `*.mspdi.xml.gz`
>   goldens, which the new `gz` suffix newly matched. Both were narrowed to the real claim.
> * **One mutation silently did NOTHING and nearly passed as evidence** — a `python3 -c "..."` in
>   double quotes let the shell expand `$signature_re` before Python saw it, so the replace never
>   matched and the suite went green, indistinguishable from "this test cannot fail". Mutate by
>   heredoc with `assert anchor in source`, and re-read the file to confirm it changed.
> * Hook verified end-to-end in a scratch repo against the audit's exact gap table.
>
> ## Deliberately NOT done
> * **The 99 mislabelled files are NOT renamed** — `FILE-NAMES.md` says "tests probe these literal
>   paths". This is a provenance record, not a cleanup.
> * **`tests/fixtures/` keeps its unconditional allowance** (CLAUDE.md documents it as intent; the
>   goldens legitimately hold schedule JSON). Narrowing it is an operator policy call.
> * **Actions pinned, not upgraded** — `checkout` v7 / `setup-python` v7 exist; that is its own unit.
>
> ## Next
> **Phase 4 continues:** CC-01's rendering half (*"74 sites" is an approximate grep — RE-DERIVE it*;
> ADR-0240 reserves it for a **Fable 5 Max** deep dive on the CPM date machinery) · **SRA-LEGACY**
> (`audit/SRA-ROOTCAUSE-20260730.md`) · **V3** (`engine/msp_filters.py` hard-codes `"d": 480` and
> discards the elapsed marker from regex group 2 — ADR-0310 made it a conformance fix, but it MOVES
> saved-filter populations and needs its migration-report gate). Then **Phase 5** monolith split 2–3
> (`app.py` 21,333 lines, `state.py` 1,479) and **Phase 6** docs/operator queue.
> **Operator only:** license selection (LICENSE grants no rights) · branch-protection required
> contexts · intake re-upload · proprietary-tool reruns (engine==golden → engine==Fuse) · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — not intermittent, not deterministic.
> Pre-existing, never red on CI. Do NOT chase. `/briefing`, `/path`, `/compare` still carry no
> `page-lede`; the `/groups` "Activities" column still counts summary rows (ADR-0343). The nine
> installers still do not install with `-c constraints/known-good.txt` (62 lockstep tests; own unit).
> `pgrep -f` self-matches. pytest stdout to a FILE is block-buffered (`python -u`). Never
> `git checkout <file>` to undo a test mutation — `cp` from a scratchpad copy.
> **`ruff` on PATH may be a STALE 0.15.8 shim** (`/root/.local/bin/ruff`) shadowing the 0.16.1 that
> `.[dev]` installs — run the gate's ruff as **`python -m ruff`**.
>
> **New this session:** *the obvious implementation of a guard is where the false positive lives* —
> "blocked extension followed by any dot" silently claimed `jakarta.xml.bind-api-3.0.1.jar`, whose
> **Java package name** merely contains `.xml.`, and would have wedged every MPXJ upgrade. And:
> **a test that fails on its first run is not necessarily a bug in the code** — two of these were
> the test over-claiming, and reading the failure beat rewriting the subject.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
