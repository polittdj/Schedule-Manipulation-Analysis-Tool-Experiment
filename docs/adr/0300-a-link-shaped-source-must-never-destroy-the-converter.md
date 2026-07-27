# ADR-0300 — A link-shaped MPXJ source must never destroy the converter, and Windows must prove it by running

- **Status:** Accepted
- **Date:** 2026-07-27
- **Promotes:** ADR-0299 Addendum 2, which first recorded this defect. Thirteen sites in the shipped
  installers, the templates and the test suite already cite **ADR-0300** for it; the addendum stands
  as the original reproduction record and this ADR is its home.
- **Related:** ADR-0299 (the one-file installer delivers `.mpp` support; rule 1 = never destroy an
  installed converter), ADR-0298 (mutation-test with file backups, never `git checkout --`),
  ADR-0249 (encode the claim as an executable assertion), ADR-0192 (never a false `[ok]`)

## Context

`SF_MPXJ_HOME` pointing at a **symlink** to the installed converter printed
`[ok] MPXJ converter deployed (native .mpp import enabled)`, exited 0, and **the converter was
gone**. `sf_realpath` used a *logical* `pwd`, which reports the symlink's own spelling, so the link
compared unequal to the destination, the self-copy skip missed it, and the copy step `rm -rf`'d the
real directory and copied from the link it had just broken. Reproduced end-to-end on `main` before
anything changed; found by the parallel PR #449 investigation.

Two independent defences shipped in #450:

1. **`pwd -P`** — the physical path, so the detection is correct. PowerShell's `Resolve-Path`
   normalises but does not dereference on 5.1, so `Resolve-SfPath` follows one reparse point too;
   best-effort, never throws.
2. **Stage the source completely before touching the destination** — read and verify a full copy,
   then swap. `$MPXJ_SRC/.` copies the *contents*, so a link is dereferenced into a real directory
   rather than staged as a link that breaks moments later.

Their independence was proved, not asserted: with the `pwd -P` guard mutated back to a logical
`pwd`, the converter **still survived** and only the message degraded. **A detection has to be right
on every platform to protect anything; staging protects even when the detection is wrong.**

### The part that was still owed

All of that was executed **in bash**. The operator is on **Windows**. So was the drive-root abort in
ADR-0299's first addendum. Both PowerShell fixes rested on:

- the executed *bash* logic, plus
- a static text guard over the `.ps1` (`test_no_candidate_path_is_built_from_a_possibly_empty_base`,
  `test_the_local_copy_is_staged_before_the_destination_is_touched`).

That is a claim about **text**, offered as evidence about **Windows** — and "proven by parity" had
already been wrong twice in the same session (the drive-root abort and the symlink destruction were
both PowerShell-side, both shipped as parity-verified, both real). `installer-smoke.yml`'s windows
job ran the *download* and *from-checkout* branches only. Neither shape had ever executed on
Windows, so the two most recent destructive edges were the two least verified.

## Decision

**The windows job executes both shapes. A static assertion about PowerShell does not close a
PowerShell defect.**

### 1. A link-shaped source, on real Windows, in both reparse-point flavours

Install once so a converter sits where a real earlier install would have left it, then re-run with
`SF_MPXJ_HOME` pointing at a `Junction` and at a `SymbolicLink` to that copy. Two properties are
asserted, because they can fail independently:

- **Survival** — the class file is **byte-identical** and the tree has the **same file count**
  afterwards. Not merely present: a half-copied tree is data loss too.
- **Detection** — the run reports `already installed`. Staging keeps survival green *even with the
  self-copy skip broken*, so survival alone would pass while the installer announced a deploy that
  never happened. Rule 2 of ADR-0299 (report the capability of the deployed tool, not the outcome of
  the copy step) is what this second assertion protects.

Three details are load-bearing:

- **The installer is copied out of the checkout and run from a bare directory.** Launched by its
  in-repo path, `$PSScriptRoot`'s parent is the workspace, whose real `tools\mpxj` is a perfectly
  good source — it would be chosen, deploy happily, and the link would never be reached. The link
  must be the *only* candidate.
- **`SF_MPXJ_OFFLINE=1` is not a speed-up.** With the fetch reachable, a destroyed destination would
  simply be re-downloaded and the leg would go green over real data loss. Offline is what lets this
  leg *fail*.
- **The leg deletes the link with `[IO.Directory]::Delete($link, $false)`**, never
  `Remove-Item -Recurse`, which has been known to empty the target — the very accident under test.

The leg also prints what **Windows PowerShell 5.1** — the shell the installer actually runs under —
reports for `LinkType`, `Target` and `Resolve-Path` on each shape. pwsh 7 resolves reparse points
differently, so probing from the orchestrating shell would describe a platform the operator never
runs on.

### 2. A real drive root

`subst` maps one (falling back to the real `C:\`, logged as a warning, if the mapping is invisible
to child processes). `$PSScriptRoot` has to *be* a root for `Split-Path -Parent` to return `""`, so
nothing short of a real drive root reproduces the empty-base `Join-Path` abort.

**Exit 0 is not proof it got past 3b.** The abort landed after the venv and before the shortcut,
uninstaller and README, so the leg asserts the artefacts written *after* the candidate loop —
`Uninstall-ScheduleForensics.ps1`, `FIRST-RUN-README.txt`, `Start-ScheduleForensics.cmd` — plus the
final `SMOKE INSTALL OK`. Those are exactly what the operator was left without.

### 3. Each leg carries a mutation step, permanently

A green leg that could never fail proves nothing, and the previous session shipped two legs that
passed while hiding the thing they existed to prove. So each new leg is followed by a step that
breaks the guard in a **scratch copy** of the installer and requires the leg's own assertion to
fire:

| mutation | required outcome |
| --- | --- |
| self-copy skip → `if ($false)`, source **is** destination | converter still byte-identical (staging held), report degrades to `deployed` |
| `if ($base)` guard removed, run from a drive root | the install **dies** (non-zero exit) |

The first one earns something the bash mutation could not: it establishes **on Windows** that the
two layers of ADR-0299 rule 1 are genuinely independent, rather than inferring it from the bash
twin.

Each mutation **asserts that it actually applied**. A needle that no longer matches would turn the
step into a re-run of the *unmutated* installer that reports success — a silent failure mode, which
is the class of defect this whole family started as. Because both needles are verbatim text,
`test_every_windows_mutation_still_bites_the_real_installers` checks every one of them against all
three `install-tier*.ps1` in milliseconds, instead of after a ~20-minute windows round trip that
only happens when something under `installer/` changed.

### What was deliberately NOT done

- **No linux symlink leg.** The bash 3b block is already *executed* against a real symlink by
  `test_a_symlinked_source_neither_destroys_nor_falsely_claims_success`, on every CI run. The gap
  was Windows-only; adding a linux leg would restate covered ground.
- **No standalone PowerShell harness for the 3b block** (the twin of `_run_mpxj_block`). It would
  make mutation cheaper, but running the *whole* installer is what caught the `java -version` probe
  abort — a block harness would have missed it. Possible future work, not a substitute.
- **No change to `engine/`, `src/`, or any installer.** The fixes were already correct; what was
  missing was evidence. The embedded wheel stays in lockstep at 1.0.105.

## What the runner actually reported (first green run, PR #452)

Measured, not predicted — and one measurement settles a question the addendum could only assert.

**Windows PowerShell 5.1 resolves a reparse point to its own spelling, for a junction *and* for a
symlink:**

```
5.1 sees: LinkType=Junction          5.1 sees: LinkType=SymbolicLink
5.1 sees: Target=D:\a\_temp\SFLink\tools\mpxj      (same)
5.1 sees: Resolve-Path=D:\a\_temp\mpxj-as-Junction  ...mpxj-as-SymbolicLink
```

`Resolve-Path` hands back the *link*, so a comparison built on it can never see a self-copy — the
bash-side defect, confirmed present in PowerShell's semantics too. `.Target` does give the real
destination, and does so **without** the `\??\` device prefix that would have broken the string
compare. `Resolve-SfPath`'s one-hop reparse follow is therefore both necessary and sufficient.

- **Both shapes were creatable on `windows-latest`** — no `::warning::` was emitted, so neither was
  skipped for want of elevation. Zero annotations across the whole job.
- **Both re-runs reported `already installed — native .mpp import stays ON (existing copy kept)`**
  against a 28-file converter whose class hash matched the shipped manifest byte for byte.
- **`subst X:` produced a usable drive root** visible to the child `powershell` process; the `C:\`
  fallback was not needed.
- **Both mutations behaved as required:** detection broken → `deployed`, converter byte-identical;
  `if ($base)` removed → `Join-Path : Cannot bind argument to parameter 'Path' because it is an
  empty string.`, exit 1.
- The job's MPXJ lines now read as a complete branch census — `deployed` (checkout) ·
  `downloaded and SHA-256 verified` (one-file) · `deployed` (python-only) · `deployed` (link setup) ·
  `already installed` ×2 (the two link shapes) · `deployed` (mutation) · `no MPXJ converter found`
  (drive root, offline). Every branch of section 3b is now exercised at least once on Windows.
- Ten steps and **nine installer runs** — the eight above plus the drive-root mutation, which aborts
  before reaching 3b and so prints no MPXJ line at all. (Counted from the log's outcome lines, not
  from the YAML: grepping `-File` over the workflow gives 14, because `Get-ChildItem -Recurse -File`
  and the 5.1 link probe match too.)
- **The four new steps cost ~63 s.** Per-step, from the job API: link leg **31 s**, its mutation
  **9 s**, drive root + its mutation **23 s**. Whole windows job **3 m 06 s – 3 m 40 s** across three
  green runs on this branch. They are cheap because each re-uses the venv the step before it created
  — which is also why the link mutation had to run *after* the link leg rather than as a fresh
  install.
- **Three consecutive green runs** (`833760f`, `e73aa70`, `4fe6d13`), each executing both shapes and
  both mutations. Not one green run treated as proof of a stable leg.

## Consequences

- The windows job grows four steps (two legs + two mutations) and its `timeout-minutes` goes 15 → 30.
  Two of the four re-use an existing venv, so the added wall-clock is modest.
- **Every push to a PR that has ever touched installer content re-runs this workflow.** A
  `pull_request` `paths:` filter matches the **cumulative base…head diff**, not the pushed commit —
  observed here, when a docs-only commit re-ran the whole windows job. Good for confidence (the legs
  re-validate on the head commit) and worth knowing when batching commits (each push costs a windows
  run). The `push:` trigger on `main` still filters per commit.
- The installer suite goes **50 → 52**: the two shapes must keep executing on windows, and every
  mutation needle must still match the shipped installers verbatim.
- **Both new tests were mutation-verified with file backups (ADR-0298), and the first draft of one
  was wrong in this repo's recurring way.** The shape guard **passed** with the reparse-point loop
  gutted to `@("Directory")`, and **passed again** with every `subst` call removed: the explanatory
  comments and a `::warning::` string satisfied it. Six mutations now fail as required. **A guard
  that greps prose measures the documentation, not the behaviour** — pin an invocation, and read
  comments out of the text before asserting on it.
- The `ADR-0300` citations already shipped in nine installers, three templates and the test suite
  now resolve to a real document. A dangling citation on a testimony tool is the same defect class
  as an uncited figure.
