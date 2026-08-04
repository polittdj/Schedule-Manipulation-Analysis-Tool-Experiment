# ADR-0347 — The intake gets a manifest, and three guards get teeth

**Date:** 2026-08-03
**Status:** Accepted
**Supersedes:** nothing. **Closes:** the 2026-08-03 external audit's **P1** queue (§3 intake
provenance, §4 stale risk register, §5 CUI hook coverage, §7 action pinning).
**Follows:** ADR-0346 (P0 — the dependencies are bounded).

## Context

ADR-0346 closed P0 and left four hygiene items. Each was a *documented* control that had never
been *measured*, which is the same shape as the defect ADR-0346's `floor` job found: a correct
guard and a correct requirement that had never been introduced to each other.

The audit reported the committed reference intake (ADR-0151/0152) had arrived from its bulk upload
with a **name/content rotation** — files whose extension their bytes contradict — and that the
risk register still described a world that ADR-0152 had ended.

## Decision

### 1 — `docs/INTAKE-MANIFEST.md`, generated and gate-pinned

`tools/intake_manifest.py` walks the git-tracked files under `00_REFERENCE_INTAKE/` and records
path / size / SHA-256 / declared extension / detected content family for each.
`tests/guards/test_intake_manifest.py` (10 tests) re-derives the scan and fails on any added,
removed or byte-changed file and on any **new** mismatch.

Three design choices carry the weight:

* **The manifest hashes the committed BLOB, not the working tree.** `.gitattributes` sets
  `* text=auto`, so **128** intake files check out CRLF on Windows and LF on Linux. Hashing the
  working tree would have passed CI (all pytest jobs are `ubuntu-latest`) and failed on the
  operator's own machine — a guard that only works where nobody runs it.
* **Classification is decisive-or-silent.** A family is asserted only from a magic signature, an
  OOXML part name, an OLE2 stream name, or a *complete* JSON/XML parse. `binary` means "no
  decisive signal" and is never called a mismatch. A fabricated mismatch would be worse than the
  drift it chases (Law 2).
* **The live assertions do not consult the manifest.** A manifest that only agreed with itself
  would prove nothing, so the guard reads the bytes: both `.aft` Bibles parse at **1443**/**1403**
  `<Metric>`, all **20** `.mpp` are OLE2 MS Project documents, all **65** shipped `web/static/`
  assets match their extensions, every golden fixture is well-formed XML.

**Measured: 406 tracked files, 332,633,606 bytes, 99 mismatches, 27 duplicate-content groups over
63 files.** The audit said 89 and 24/54. The mismatch gap reconciles exactly — `99 − 7 − 3 = 89`,
the 7 being `.XLS` files holding OOXML packages and the 3 being `.json` files holding prose.
Neither count is wrong; this one states its rule, and a test re-derives it.

**The rotation never reached the product or the oracles.** That is the finding that matters.

### 2 — A divergence the audit did not report

The two tracked copies of `Project5_TAMPERED.mpp` are the **same size with different bytes** —
102 of 817,152 (0.0125%). The audit recorded the file as "tracked twice" and stopped there. This
is ADR-0112's authoritative parity input, so it was measured rather than assumed: the differing
runs sit entirely in the OLE2 **VBA-project storage**; through MPXJ both yield MSPDI identical but
for `<CurrentDate>` (the conversion clock); through the product importer both yield an equal
`Schedule` — 145 tasks, identical calendars, identical CPM timings, the same 4-task critical path,
the same project finish. **No parity exposure.** Both hashes are now pinned.

### 3 — R-03 and R-12 reconciled; R-14 opened

R-03's "**Open item:** the two source `.mpp` schedules not yet in the provided set" was stale —
both are tracked, twice each. R-12's entire premise ("a fresh session's `00_REFERENCE_INTAKE/` is
empty") was ended by ADR-0151/0152 and is **Resolved**. R-03 keeps a real, correctly-scoped
residual: no `.pbix` has ever been deposited (`pbix/` and `metrics_library/` hold only
`.gitkeep`), and the proprietary-tool reruns remain with the operator. **R-14** now carries the
intake-provenance risk with the manifest as its mitigation.

### 4 — The CUI hook gets a second detector

The audit's gap table is closed. Two changes:

* **Extension:** `.p6xml` and `.xlsm` added; the pattern no longer anchors hard on `$`, so
  `data.mpp.bak`, `export.xlsx.1`, `sched.mpp~` and `plan.csv.gz` are caught.
* **Content:** `.json` is deliberately *absent* from `.gitignore` (tracked config must stay
  visible) and **is the tool's own Save format**, so extension alone could never cover it. The
  hook now sniffs the **staged** bytes of `.json` / `.txt` / extension-less files for three
  decisive signatures — the tool's Save format, an MSPDI root, a P6 XER header.

`src/schedule_forensics/web/examples/` joins `tests/fixtures/` as an allow-prefix: the shipped
demo schedule the app itself loads is synthetic and non-CUI, and would otherwise be blocked by the
new detector.

**The obvious implementation was wrong, and measuring caught it.** "A blocked extension followed
by any dot" silently claims `tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar`, whose *Java package
name* merely contains `.xml.` — every future MPXJ upgrade would have been blocked with a nonsense
reason. The suffix set is therefore **closed**. A test now sweeps the tracked tree and fails if
the clause ever widens again.

### 5 — The log redactor gains the same two extensions

Adding `.p6xml`/`.xlsm` to the guard turned `tests/test_logging_redaction.py` red, and it was
**right**. That test pins the redactor's `SENSITIVE_EXTENSIONS` to the hook's blocklist — every
extension the guard treats as CUI must also be redacted from logs — and the redactor covered
neither. `logging_redaction.redact("import failed for Runway Program.p6xml")` returned the file
name **verbatim**. Both extensions are now redacted (`<file:p6xml#…>`), which makes this a
**shipped** change: hence **v1.0.162**, and the wheel plus nine installers rebuilt.

Only the test's *extraction* was stale — it read `blocked_re='\.(exts)$'`, a shape the new
backup-suffix clause ended. It now reads the extension alternation itself, in either shape.

### 6 — Nine actions pinned to commit SHAs

All nine references were on mutable `@v4`/`@v5`/`@v6`, including the two ADR-0346's `floor` job
had just added (recorded there deliberately, so this sweep would be one mechanical commit).
Pinned to the commit each major currently resolves to, each carrying a `# vX.Y.Z` note.
`tests/guards/test_workflow_action_pins.py` requires **both** the SHA and the note — a bare
40-hex pin is unmaintainable, and an unmaintainable pin gets reverted. It deliberately does not
assert *which* SHA: pinning is hygiene, not a version policy.

## Verification

### The content detector failed OPEN on its first real-sized input

The obvious implementation — `git show ":$path" | head -c 65536 | grep -qaE "$signature_re"` —
passed every small fixture and was **wrong**. `set -o pipefail` makes a pipeline's status the last
non-zero one, and a truncating reader SIGPIPEs its upstream, so the pipeline reports failure *even
when grep matched*. Measured: a **281 KB** saved schedule was **ALLOWED** while a 4 KB one was
blocked — the guard failing open on precisely the size a real schedule produces. Fixed by reading
through a process substitution, which keeps `git show` out of the pipeline status and removes the
truncation window at the same time.

It was found by testing at realistic size, not by reading the line. And falsifying the regression
test taught a second thing: reverting to the *two-stage* `git show | grep -q` does **not**
reproduce it — that form happens to win the same race — so the test is only honest against the
exact three-stage original, which is now recorded in both the hook and the test.

* **All 40 new assertions proved able to fail**, each on its own mutation (16 mutations: manifest
  edits, a real rotation of a shipped static, a corrupted golden, a guessing classifier, six hook
  regressions, three workflow regressions). Every tree touched was restored **byte-identical**
  from a scratchpad copy — never `git checkout`.
* **Two of the new tests failed on their first run and both were right.** One caught that the
  intake legitimately tracks blocked-extension files under ADR-0152's `inherited_from_main` rule
  (my assertion, not the hook, was wrong); the other caught that the repo tracks
  `*.mspdi.xml.gz` goldens, which my new `gz` suffix newly matched. Both assertions were narrowed
  to the claim actually being made.
* **One mutation silently did nothing and nearly passed as evidence.** A `python3 -c "..."` in
  double quotes let the shell expand `$signature_re` before Python saw it, so the replacement never
  matched and the suite went green — indistinguishable from "the test cannot fail". Mutations are
  now applied by heredoc with an `assert anchor in source`, and the file is re-read to confirm it
  changed before the suite is trusted.
* Hook behaviour verified end-to-end in a scratch repo against the audit's exact gap table:
  every previously-allowed path now BLOCKED, and prose `.txt`, config `.json`, both allow-prefixes
  and the MPXJ jar still allowed.
* **The full suite found a coupling three targeted runs could not.** `tests/guards/` was green
  through every iteration; the redaction failure lives in `tests/test_logging_redaction.py`, a
  module that reads the hook from a completely different subsystem. Scoped runs are for the
  edit-debug loop; only the whole suite knows what a file is wired to.
* Gate: `node --check` **60/60** (per file) · ruff · ruff-format · mypy-strict (**117**) ·
  bandit **0** · installer lockstep + packaging **56 passed** · parity **49 passed**.
* **v1.0.162** — wheel rebuilt at `dist/wheel/` and the nine installers regenerated from it.

## Deliberately NOT done

* **The 99 mislabelled files are left as they are.** Renaming operator-uploaded reference files
  would break the literal paths tests probe (`FILE-NAMES.md`: "tests probe these literal paths"),
  and the manifest already makes the state legible. This is a provenance record, not a cleanup.
* **`tests/fixtures/` keeps its unconditional allowance.** The audit lists it as a gap; CLAUDE.md
  documents it as intent (synthetic, hand-authored, non-CUI fixtures), and the goldens legitimately
  contain schedule JSON. Narrowing it is a policy change for the operator, not a hygiene fix.
* **Prose `.txt` is not content-sniffed for schedule *tables*.** No decisive signature exists, and
  a guard that fires on documents gets switched off — after which it guards nothing.
* **Actions are pinned, not upgraded.** `checkout` v7 and `setup-python` v7 exist; taking them is a
  behaviour change and belongs in its own unit.
