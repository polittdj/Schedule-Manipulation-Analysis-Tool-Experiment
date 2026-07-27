# ADR-0300 — The self-copy guard compares PHYSICAL paths; a symlinked source cannot destroy the converter

- **Status:** Accepted
- **Date:** 2026-07-27
- **Fixes:** a P1 in ADR-0299's shipped bash block, raised by the Codex reviewer on PR #447 and
  **reproduced against the shipped installer before anything was changed**
- **Related:** ADR-0299 (report the deployed capability; never destroy an installed converter),
  ADR-0289 (execute the behaviour, do not pin the source)

## Context

ADR-0299 states two rules for the `# --- 3b.` block, in the block's own comment:

> 1. **NEVER DESTROY AN INSTALLED CONVERTER.**
> 2. **REPORT THE CAPABILITY OF THE DEPLOYED TOOL, NOT THE OUTCOME OF THIS COPY STEP.**

The self-copy skip that enforces rule 1 compared paths through

```sh
sf_realpath() { (cd "$1" 2>/dev/null && pwd) || printf '%s\n' "$1"; }
```

`pwd` without `-P` reports the **logical** path — the spelling you arrived by, symlinks intact. So
a candidate that is a **symlink to the already-installed converter** carries a different spelling
from `MPXJ_DEST_REAL`, compares unequal, and is selected as the source. The block then `rm -rf`s
the real converter and copies the now-dangling link into its place.

`tests/installer/test_installers.py::test_a_re_run_never_destroys_the_installed_converter` did not
catch it because it passes `SF_MPXJ_HOME` as the destination's **own spelling**, which a logical
`pwd` compares equal. The guard worked for the case it was written against and failed for the case
one indirection away.

### Reproduced against the shipped block, before the fix

`SF_MPXJ_HOME` a symlink to `$INSTALL_ROOT/tools/mpxj`, running the 3b section lifted verbatim out
of the shipped `install-tier2.sh`:

```
BEFORE: converter present = YES
        OK:MPXJ converter deployed (native .mpp import enabled)
AFTER:  converter present = NO
        mpxj -> …/InstallRoot/tools/mpxj          # a dangling self-referential symlink
```

**Both rules broken by one path**, in the direction that costs the operator data *and* lies about
it: the converter is gone and the installer reports `enabled`. Every subsequent `.mpp` import would
fail with `MPXJ runner not found` on a machine whose installer had just declared native `.mpp`
working.

### Scope: bash and `.command` only

The PowerShell family runs `New-Item -Force` then `Copy-Item -Force` and **never removes the
destination**, so the same mis-compare there costs a redundant copy, not data. `Resolve-SfPath`
remains imprecise for junctions; that is not a defect worth a blind fix in a language this
container cannot execute, and it is recorded here rather than patched on speculation.

## Decision

**`pwd -P`.** The guard compares physical paths, so any spelling of the destination — direct,
symlinked, or reached through a symlinked parent — is recognised and skipped. The upgrade is then
correctly reported as `already installed — native .mpp import stays ON (existing copy kept)`.

**`cp -RL`.** What lands beside the venv must be real files. A source reached through a link
previously deployed *the link*, so a converter could silently vanish later when the source tree
moved, unmounted, or was cleaned up — a deployed tool whose capability depends on a path outside
its own install directory.

## Consequences

- **Two executed regression tests**, alongside the existing harness rather than replacing it:
  `test_a_symlinked_source_cannot_destroy_the_installed_converter` (the P1) and
  `test_a_symlinked_source_deploys_real_files_not_a_link` (the `-L` guarantee). Both run the real
  shipped block from the generated installer.
- **Both mutation-verified:** reverting `pwd -P` → `pwd` fails the first and only the first;
  reverting `cp -RL` → `cp -R` fails the second and only the second.
- **The source pin was widened, not deleted.** `test_installers_deploy_mpxj_and_a_single_self_stopping_icon`
  now also asserts `pwd -P` is present, with a comment pointing at the executed tests for what it
  actually guarantees — a pin is a revert-detector, never the proof.
- **A pin cannot catch a lie, twice over.** ADR-0299 was itself occasioned by a source pin that
  asserted the wrong sentence was present. This defect sat inside the fix for that defect, in the
  guard the ADR called load-bearing, and was found by review rather than by any test in the suite.
- **A finding this ADR flagged as unverified has since been SETTLED by someone else.** The draft
  of this change noted that `template.ps1` built its four candidates eagerly inside `@(...)`,
  where `Join-Path` throws on the empty string `Split-Path -Parent` returns for a drive root —
  and declined to fix it, because this container cannot execute PowerShell. **PR #448 confirmed
  it and shipped exactly that fix.** Flagging a suspicion with enough detail to act on was worth
  more than a speculative patch would have been; the flag is now closed.
- Version 1.0.105 → **1.0.106**; wheel + 9 installers regenerated **from the merged templates**
  (this change was merged with `origin/main` `b643a91`, which carries #448's PowerShell fix —
  generated base64 blobs must be rebuilt after a merge, never auto-merged).
