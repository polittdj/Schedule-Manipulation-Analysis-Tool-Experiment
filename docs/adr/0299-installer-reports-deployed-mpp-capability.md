# ADR-0299 — The installer reports the deployed tool's `.mpp` capability, not its own copy step

- **Status:** Accepted
- **Date:** 2026-07-27
- **Implements:** `docs/PLAN/MPXJ-CAPABILITY-REPORT.md` (the diagnosis, staged in PR #445)
- **Related:** ADR-0193 (the converter ships beside the venv), ADR-0293 (the runtime `.mpp`
  capability probe), ADR-0289 (execute the behaviour, do not pin the source)

## Context

The operator upgraded an existing install by running the downloaded `install-tier2.ps1` and saw:

```
[!!] tools\mpxj not found next to this installer — native .mpp import stays OFF
```

on a machine where native `.mpp` import was **ON** — confirmed directly with
`Test-Path "$env:LOCALAPPDATA\ScheduleForensics\tools\mpxj\classes\MpxjToMspdi.class"` → `True`.

Nothing was broken. The `else` branch only warns; it never deletes. But **the installer asserted
the opposite of the truth about the tool it had just installed.** On a tool whose output is meant
to be defensible in testimony, an install step that misreports a capability is a correctness
defect, not a cosmetic one: an operator who believes `.mpp` ingest is unavailable will work around
it needlessly, or distrust a later successful import.

The defect had survived because the guard was a **source pin** — `assert "native .mpp import stays
OFF" in tpl_ps1`. It asserted that the wrong sentence was present, and passed for months. A pin
cannot catch a lie; it can only catch a rewording.

### Diagnosed by execution

The `# --- 3b.` section was lifted verbatim out of the generated `install-tier2.sh`, stubbed only
for `ok`/`warn`/`INSTALL_ROOT`, and run under the installer's own `set -euo pipefail`:

| scenario | installer said | `.mpp` actually available after | agreed? |
| --- | --- | --- | --- |
| run from a checkout, fresh machine | "enabled" | yes | ✅ |
| run from Downloads, fresh machine | "stays OFF" | no | ✅ |
| **run from Downloads, upgrading an existing install** | **"stays OFF"** | **yes** | ❌ |
| `SF_MPXJ_HOME` set to a real converter | "stays OFF" | no | ⚠️ ignored |

Four defects: the report described the *copy step* rather than the deployed tool; one source path
only (`<installer dir>/../tools/mpxj`, i.e. `C:\Users\<user>` when run from `Downloads`);
`SF_MPXJ_HOME` was named in the advice and never read by the code; and "run it from the repository
checkout" presumes a clone this operator does not have.

## Decision

**Report the capability of the deployed tree, not the outcome of the copy.** The installer's last
act is to look where the runtime's walk-up discovery will look (`importers/mpp_mpxj.py::_mpxj_home`)
and say what it finds:

| condition | message |
| --- | --- |
| a source converter was found and copied | `MPXJ converter deployed (native .mpp import enabled)` |
| no source, but one is already installed | `MPXJ converter already installed — native .mpp import stays ON (existing copy kept)` |
| neither | `no MPXJ converter found — native .mpp import is OFF` + the ZIP remedy |

**Search four layouts, not one:** `$SF_MPXJ_HOME` → `<installer dir>/../tools/mpxj` →
`<installer dir>/tools/mpxj` → `<cwd>/tools/mpxj`. `SF_MPXJ_HOME` is now honoured rather than
merely named, and being `cd`-ed into an extracted ZIP works even with the installer left in
`Downloads`.

**Make the remediation actionable.** The not-found branch now says: download the repository ZIP
(**Code → Download ZIP**), extract, and re-run from inside. Verified before recommending it — all
28 files under `tools/mpxj` (the converter class and 24 jars) are git-tracked with no LFS, so the
ZIP genuinely carries them. That check is itself a test, so the advice cannot rot silently.

### The destructive edge this opened, and closed

Widening the search made the **already-installed** copy selectable as the *source*, and the copy
step `rm -rf`s the destination first — so a re-run would have **deleted the operator's only
converter**. A self-copy guard (`sf_realpath` in bash, `-ieq $destReal` in PowerShell) skips any
candidate resolving to the destination. Mutation-verified:

```
GUARDED : MPXJ converter already installed — native .mpp import stays ON (existing copy kept)
          converter still present afterwards: True
MUTANT  : cp: cannot stat '.../InstallRoot/tools/mpxj': No such file or directory
          converter still present afterwards: False
```

The guard is a necessary companion to the widening, not a pre-existing bug — the shipped code had
one candidate and it was never the destination.

**A second self-inflicted hazard was caught while writing the PowerShell.** `$ErrorActionPreference`
is `"Stop"`, and `Join-Path` throws on an empty base — `Split-Path -Parent` of a drive root returns
`""`. Building four candidates eagerly widened that exposure, and a throw there aborts the entire
install. The candidate list is now assembled with an explicit non-empty check per base.

### Explicitly rejected: embedding MPXJ in the installers

Recorded so it is not re-litigated. The converter is 17 MB; base64 in a one-file installer is
~23 MB, times nine installers, regenerated on every version bump — roughly 200 MB of git per
release. The installers are self-contained *for the Python tool* (that is what the embedded wheel
is for); the Java converter is an optional add-on the ZIP route already delivers in one download.

## Consequences

- **The guard is now an invariant, not a string.** `tests/installer/test_mpxj_capability_report.py`
  extracts the `# --- 3b.` section **verbatim from the generated installer** and executes it,
  asserting that whatever the installer claims about native `.mpp`, the filesystem agrees — checked
  where `_mpxj_home()` looks. It also asserts `SF_MPXJ_HOME` is honoured, that a re-run never
  destroys an installed converter, and that the ZIP remedy is still real.
- **Proved to bite:** reverting the two bash installers to the old block fails **10 of 14** cases,
  including the operator's exact scenario. The run-from-a-checkout case still passes — it was never
  broken.
- **Why the harness is load-bearing:** `installer-smoke.yml` runs the installer *from the checkout*,
  so real-OS CI only ever exercised the one scenario that already worked. Every other layout had no
  coverage at all.
- **PowerShell parity is structural, and said so plainly.** `pwsh` is absent from the build
  container; the Windows family is held to the same four sources, three outcomes, self-copy guard
  and empty-base guard as the bash logic that *is* executed. The windows-latest smoke job parses
  all three `.ps1` files.
- **Documentation drift fixed in the same change:** `README-DISTRIBUTABLE.md` promised "give the
  recipient **one** file" while never mentioning `tools/mpxj` (so the documented distribution model
  could not deliver native `.mpp`) and claimed Start/Stop icons — true on Linux/macOS, wrong on
  Windows since ADR-0193; `template.ps1`'s own §6 header repeated that stale two-icon claim while
  its code ~260 lines below deletes those two and creates one.
- **Version 1.0.104 → 1.0.105**; wheel + 9 installers regenerated (the lockstep test requires it).
