# ADR-0149 — Windowless subprocess spawns (the "continuous popup" root cause)

## Status

Accepted.

## Context

After two rounds of overlay-focused fixes (ADR-0130 F-06 adjacent work in PR #284; deployment
freshness in ADR-0148), the operator still reported a "popup error" that "starts as soon as I open
the tool and continues until I quit it," resembling "the same image I see when I am loading files."

The real culprit was never the browser overlay. The deployed desktop app runs **windowless**
(`pythonw.exe`). The ADR-0147 telemetry layer runs GPU/CPU-temp probes on a **5-second background
loop** from tool open to quit, and on Windows those probes bottom out in `nvidia-smi` and
`powershell` **subprocess spawns with no `CREATE_NO_WINDOW`** — each spawn flashes a black console
window. A flash every ~5 seconds for the whole session is the reported symptom exactly, and the
"same image when loading files" is the Java (MPXJ) console window — a failure mode
`importers/mpp_mpxj.py` had already fixed for the converter, with the pattern documented in-file.
The telemetry code (verified only in this Linux container and via Linux browser automation, where
console-window flashes are invisible) never applied it. A sixth unsuppressed spawn — the Quit-time
`taskkill` in `ai/ollama_process.py` — flashed once at shutdown.

## Decision

1. **Every spawn carries `creationflags=CREATE_NO_WINDOW` (0/no-op on POSIX) and
   `stdin=DEVNULL`.** Five sites in `web/system.py` (sysctl, vm_stat, nvidia-smi, powershell ×2)
   and the `taskkill` in `ai/ollama_process.py`. `stdin=DEVNULL` also prevents a console child
   hanging on an inherited invalid console handle (the same hang `mpp_mpxj.py` documents).
2. **Repo-wide AST guard** — `tests/test_windowless_subprocess.py` walks every
   `subprocess.run/Popen/check_*` call in `src/schedule_forensics/` and fails if any lacks explicit
   `creationflags` + `stdin`. (It immediately caught the `taskkill` site the manual sweep missed.)
3. **Version 1.0.1 → 1.0.2**, wheel + all nine installers regenerated (the ADR-0148 lockstep gate
   forces this), embedded `system.py` verified to carry the flags.

## Consequences

- The operator-visible symptom (continuous black window flashes from open to quit) ends with the
  1.0.2 install; the Quit flash ends too. No behavioral change to the probes themselves — same
  cadence, same data, same fail-closed nulls.
- Any future subprocess use must state its window/stdin posture explicitly or the gate fails —
  Windows-only presentation bugs can no longer ship invisibly from this Linux build environment.
- Diagnostic humility recorded: the first two fixes addressed a real but different bug (the
  overlay + its deployment path). The lesson — "popup" reports from a windowless Windows install
  should be checked against subprocess spawns FIRST — is now encoded in the guard test's docstring.

## Alternatives considered

- **`startupinfo` with `SW_HIDE`** — equivalent effect for console children but wordier at each
  site; `creationflags` matches the existing `mpp_mpxj.py`/`ollama_process.py` precedent.
- **Disabling the telemetry probes outside JARVIS** — would mask, not fix; the dock is default-ON
  by ADR-0147 decision and the probes are useful.
- **Windows CI execution of the probe loop** — the installer smoke workflow runs on
  `windows-latest`, but console-window flashes aren't observable in CI either; the AST guard is
  the reliable enforcement point.
