# ADR-0192 — Fully no-admin Windows install: portable JDK zip, user-scope Python, shim warning

## Status

Accepted. Operator 2026-07-10 (live install transcript + "I don't have admin rights … figure
out a way to have whatever installed without admin rights"): the winget OpenJDK MSI popped a
UAC prompt the operator could not approve (exit 1602) — and the installer still printed
"[ok] Java 17 installed". Separately, typing `schedule-forensics` in the terminal ran a stale
shim from a miniforge base environment and died with ModuleNotFoundError even though the venv
install had succeeded.

## Context

Every other component was already elevation-free (venv in %LOCALAPPDATA%, Ollama's user-scope
installer, user Desktop/Start-Menu shortcuts). Java was the one admin-gated step, its result
was unchecked (false "[ok]"), and its detection was PATH-only — blind to JDKs installed in the
standard folders without a PATH entry, which the tool's own runtime discovery
(`mpp_mpxj._find_java`) already handles.

## Decisions

1. **Portable JDK zip, no MSI, no elevation**: on consent the installer downloads Microsoft's
   OpenJDK 17 portable zip (`aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip`) and
   extracts it into `%LOCALAPPDATA%\Programs\Microsoft` — user-writable AND already one of
   the folders the runtime java scan searches, so the tool finds it with zero configuration
   (no PATH edit, no JAVA_HOME, no admin).
2. **Detection mirrors the runtime** (`Find-JavaNoAdmin`): PATH first, then the user-scope
   and machine-wide install folders (Microsoft / Eclipse Adoptium / Java under both
   `%LOCALAPPDATA%\Programs` and `%ProgramFiles%`) with a >= 17 version gate on the folder
   name — so "I already have OpenJDK 17 but it's not on PATH" is recognized instead of
   re-downloaded.
3. **Honest reporting**: download/extract wrapped in try/catch, success re-verified by
   re-running the detection; failures print a warning with the MSPDI-export fallback —
   never a false "[ok]".
4. **Python fallback goes user-scope** (`winget … --scope user`) so even the no-Python path
   needs no elevation.
5. **Stale-shim warning**: if `schedule-forensics` on PATH resolves outside the install root
   (e.g. a conda/miniforge base env's leftover entry point), the installer names the impostor
   and points at the Desktop shortcut — which always launches the correct venv.
6. Runtime `ImporterError` hint updated to name the `%LOCALAPPDATA%\Programs\Microsoft`
   no-admin drop-in alongside `tools/jre`.

## Consequences

- The whole Windows install now completes with zero UAC prompts; static pins in
  `tests/installer` keep the MSI path out and the portable path + honest reporting in.
- macOS/Linux installers unchanged (already elevation-free for the tool itself).
