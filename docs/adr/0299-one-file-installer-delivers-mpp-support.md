# ADR-0299 — The downloaded installer delivers .mpp support; every download reports honestly

- **Status:** Accepted
- **Date:** 2026-07-27
- **Supersedes (in part):** ADR-0193 (which deployed MPXJ **from the repo checkout** — correct for a
  developer, structurally impossible for the operator's actual deploy path)
- **Related:** ADR-0192 (never a false `[ok]`; honest failure reporting), ADR-0148 (embedded wheel
  must stay in lockstep with source), ADR-0249 (encode the claim as an executable assertion)

## Context

The operator has **no local clone**. Every handoff since 2026-07-10 records the same deploy
instruction:

> download `installer/install-tier2.ps1` from the GitHub web UI and run
> `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`

That is a **single file in `~/Downloads`, with no repository anywhere near it**. ADR-0193 deployed
the 17 MB MPXJ Java converter by copying it out of the checkout beside the installer:

```powershell
$repoMpxj = Join-Path (Split-Path -Parent $PSScriptRoot) "tools\mpxj"    # ps1
REPO_MPXJ="$(cd "$(dirname "$0")/.." && pwd)/tools/mpxj"                 # sh/.command
```

On the documented path that resolves to `%USERPROFILE%\tools\mpxj`, which does not exist. So the
lookup missed, the installer warned once, **and then printed a green `DONE`**.

### What that cost, reproduced end-to-end

Running the shipped `install-tier2.sh` from a bare directory (the operator's exact shape):

```
[!!] tools/mpxj not found next to this installer — native .mpp import stays OFF
DONE — run "schedule-forensics-start" (or the app-menu entry) to begin.
```

and then, from the resulting install:

```
ImporterError: MPXJ runner not found under …/venv/lib/python3.13/tools/mpxj
                — run tools/mpxj/setup.sh or set SF_MPXJ_HOME
```

**Native `.mpp` is the tool's primary input.** So the documented deploy path produced an install
that could not open a single production schedule — and the remedy printed in the error
(`tools/mpxj/setup.sh`) needs **Maven and a checkout**, neither of which the operator has. The
"one-file installer" promise was true for the wheel and false for the converter.

## Decision

### 0. It reports the capability of the DEPLOYED TOOL, not the outcome of its copy step

`docs/PLAN/MPXJ-CAPABILITY-REPORT.md` (PR #445) diagnosed the same lookup from the other end: on an
**upgrade**, the source is missing but a converter is already installed, so the old code printed
`native .mpp import stays OFF` **about a machine where `.mpp` demonstrably worked**. On a testimony
tool a false claim about your own capability is a correctness defect, not a cosmetic one. Three
outcomes now, and the printed sentence must always agree with what `_mpxj_home()` will find:

| condition | message |
| --- | --- |
| a source converter was found and copied | `MPXJ converter deployed (native .mpp import enabled)` |
| no source, but one is already installed | `MPXJ converter already installed — native .mpp import stays ON (existing copy kept)` |
| neither (and no download) | `no MPXJ converter found — native .mpp import is OFF` + the ZIP remedy |

### 0b. Two destructive edges — the second one was mine

Widening the search makes the **already-installed copy selectable as a source**, and the copy step
clears the destination first, so a re-run would delete the operator's only converter. That is the
edge #445's report predicted; the `sf_realpath` / `-ieq $destReal` skip closes it, and a mutant with
the skip removed reproduces the destruction (`cp: cannot stat …`).

**The first cut of this ADR had it worse.** The download wiped the destination *before* fetching and
again in the failure branch — so an upgrade that lost the network would have destroyed a working
converter, strictly worse than the behaviour being fixed (which merely warned). The fetch now stages
into `.mpxj-incoming` and is swapped in **only after every byte verifies**; a failed download leaves
an existing install byte-for-byte untouched. **Never delete something you cannot immediately
replace.**

### 1. The converter is fetched, pinned by content, and never assumed

Embedding MPXJ was rejected: 17 MB → ~23 MB of base64 × 9 installers, re-committed on **every**
version bump. Instead each installer now, in order:

1. uses a **local copy** if one genuinely is beside it — `$SF_MPXJ_HOME`, `<dir>/../tools/mpxj`
   (the checkout), `<dir>/tools/mpxj`, `<dir>/mpxj` (offline media). No network, unchanged for
   developers and for CI;
2. otherwise **downloads** the pinned file set from this repo's public raw URL and verifies **every
   file against a SHA-256 manifest baked in at build time**;
3. otherwise says so plainly and leaves `.mpp` off.

`build_installers.py` generates the manifest from `tools/mpxj/**` and derives the base URL from
pyproject's `Repository`, so the installers cannot drift from the repo they ship out of. The
manifest pins **content, not a branch**: a swapped or corrupted jar fails loudly rather than
silently installing a converter this build was never tested against. Cost: ~3 KB per installer.

**The URL pins an immutable commit, never `main`** (PR #446 review, P1 — valid). Because the
manifest is generated from the *local* bytes, a mutable ref guarantees an eventual disagreement:
every installer already distributed starts failing its hashes the moment those bytes change, and a
PR that legitimately upgrades MPXJ regenerates the manifest with the NEW hashes while `main` still
serves the OLD jars — so CI's own no-checkout leg would download stale bytes and block the upgrade.
The reviewer's suggested "embed the build commit SHA" cannot work (the squash-merge commit does not
exist at build time), so the builder resolves `git log -1 --format=%H -- tools/mpxj` — the commit
that actually *contains* these bytes, already on `main` in the normal case. Verified that a non-tip
SHA serves byte-identical content from `raw.githubusercontent.com`. A test rejects any non-40-hex
ref. Consequence, documented in the builder: **upgrading MPXJ is a two-step — push `tools/mpxj`
first, then regenerate the installers so they pin to that pushed commit.**

This stays inside Law 1's stated posture — internet at **install** time for public prerequisites
(Python / Java / Ollama / the model), never by the running tool. `SF_MPXJ_OFFLINE=1` suppresses the
fetch for an air-gapped machine, and the header now lists the converter alongside the other
install-time downloads instead of implying the file is wholly self-contained.

### 2. An optional download may not abort the install, nor claim a success it did not get

Auditing the neighbouring download steps surfaced a second live defect. The AI step is documented
as optional — "the tool runs fully without it" — but under `set -euo pipefail`:

```bash
ollama pull "$OLLAMA_MODEL"        # fails: disk full / daemon down / network drop
ok "Model ready: $OLLAMA_MODEL"    # never reached — the INSTALLER DIES here
```

Executed with a stub whose `pull` exits 1, the script terminated at that line — **before** the
launchers, uninstaller and README were written, leaving a venv with no way to start the tool. The
PowerShell family had the mirror-image bug: `winget install` and `ollama pull` were both followed by
an unconditional `Ok`, so a failed install or pull was reported as ready and the operator only found
out when the AI features silently did nothing — exactly the dishonesty ADR-0192 removed from the
Java block. Every branch now verifies, reports what actually happened, and continues.

### 2b. On Windows, a *probe* was aborting the install — found by the new CI leg

Adding the windows no-checkout leg immediately turned it red, and the log showed the installer
printing the MPXJ line, hitting the Java check, emitting `NativeCommandError`, and **never reaching
`DONE`**. Root cause: while `$ErrorActionPreference = "Stop"`, a native program writing **anything**
to stderr raises a **terminating** error even on success — and `java -version` prints its banner to
stderr. So on any machine with `java` on PATH, the Java *detection* step killed the run before the
shortcut, uninstaller and README were created.

It had been shipping that way, invisibly: the two pre-existing Windows legs end with
`& $venvPy -c ...`, which resets `$LASTEXITCODE`, so the aborted installer's exit code was
swallowed. `winget install` and `ollama pull` stream progress to stderr and carried the same
exposure — the PowerShell twin of the §2 bash abort, at a step documented as optional.

All such calls now go through `Invoke-SfNative`, which softens the preference for the duration of
the call, **always** restores it (`finally`), and streams output so long downloads still show
progress; the caller judges `$LASTEXITCODE`. The CI leg now asserts the installer's own exit code,
so a mid-run abort can never again be masked by a later command.

### 3. `pull_model` gets a timeout a real pull can finish inside

`OllamaBackend.pull_model` issues one **non-streaming** `POST /api/pull` on the shared 120 s
`timeout`. The tier models are 2 / 5 / 43 GB; no such download completes in 120 s, so the call could
only ever time out. It now takes its own `pull_timeout` (6 h default). Nothing in `web/` calls
`pull_model` today — the app *diagnoses* a missing model and tells the operator to run `ollama pull`
— so this was latent, not a live operator symptom; it is fixed so the seam is sound if a route ever
uses it.

### What was deliberately NOT changed

- **No SHA pin for the OpenJDK download.** `aka.ms/download-jdk/...` serves a moving 17.0.x; pinning
  a hash would break on every Microsoft patch release. Its failure handling is already honest
  (ADR-0192), which is the property that matters.
- **`curl … ollama.com/install.sh | sh` stays.** It is the vendor's documented installer and is
  consent-gated; replacing it is a separate decision with real breakage risk.
- **The in-app export/download routes were swept and left alone** — all 37 `/export/{fmt}/…` routes
  across both formats plus `/download/{name}.json` (76 combinations) return 200 with a valid
  payload. No defect found; nothing to fix.

## Consequences

- The documented one-file deploy path now yields native `.mpp` support. Verified end-to-end: a bare
  directory install downloads + verifies the converter and parses a real 145-activity `.mpp`.
- A failed optional download degrades instead of destroying the install.
- New guards in `tests/installer/test_installers.py`: the manifest must cover every file under
  `tools/mpxj` with a matching hash (the MPXJ twin of ADR-0148's wheel-lockstep guard); the download
  fallback and air-gap opt-out must exist in all nine installers; and two harnesses **execute** the
  real shipped blocks — the converter step (local copy wins; honest failure leaves no partial tree)
  and the AI step (a failed pull neither aborts nor claims success).
- CI gains the operator's actual shape, **on both platforms**: `installer-smoke.yml`'s linux *and*
  windows jobs each copy one installer to a bare directory, run it, and **fail** if
  `classes/MpxjToMspdi.class` is missing afterwards. Every pre-existing leg ran from the checkout —
  so it took the local-copy branch and never exercised the download — which is precisely why this
  never surfaced. The Windows leg matters most: the operator is on Windows, so that is the fetch
  that has to work. First run of the Linux leg confirmed it live: `MPXJ converter downloaded and
  SHA-256 verified`, 24 jars, ~2 s.
- **Proved the guards bite — 5 mutants, each caught by its intended assertion:** a flipped manifest
  SHA · a manifest line removed · the raw-URL fallback removed · a false `[ok]` on the failure path ·
  the local-copy branch deleted. Per the ADR-0298 lesson, mutation testing used **file backups**, and
  the tree was verified byte-identical afterwards.
- Touching `tools/mpxj` without regenerating the installers now fails the gate — the same
  regenerate-or-fail contract the wheel already has.
