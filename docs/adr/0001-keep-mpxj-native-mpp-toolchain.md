# ADR-0001: Retain the vendored MPXJ native-`.mpp` toolchain through greenfield

- **Status:** Accepted
- **Date:** 2026-06-05 (session A1)
- **Relates to:** §6.B (parse native `.mpp` without converting first), §0.3 (no CUI in git)

## Context

The build prompt's Phase 0 says to "wipe the repo to clean greenfield (remove all
tracked files; keep `.git`)." The repo was already reset upstream (commit `882dec3`,
"Reset main to greenfield (remove prior build, keep MPXJ toolchain)"), which
**deliberately kept** `tools/mpxj/`: the vendored MPXJ **16.2.0** library jars, the
compiled `MpxjToMspdi.class`, the `MpxjToMspdi.java` source, and `setup.sh`/`setup.ps1`.

MPXJ is the enabler for the single hardest core requirement — reading **native `.mpp`**
(and `.mpx`, `.xer`, MSPDI) **without conversion**, using only a Java runtime (JDK ≥ 17),
no Maven and no build step, via a subprocess that emits MSPDI XML for the Python layer.

## Decision

Keep `tools/mpxj/` exactly as vendored. Do **not** delete it as part of the greenfield
wipe. Re-acquiring it (Maven resolution + compile) would consume an entire session and
risks network/build failure, with no benefit.

This is consistent with the spirit of "greenfield": the wipe removes the *prior
application code*, not a clean, build-critical, non-CUI toolchain.

## Consequences

- Native `.mpp` parsing is available from session one of Phase 2 (no toolchain rebuild).
- **CUI check:** the vendored jars and the tiny converter contain **no schedule data**
  (verified: only open-source libraries + a format-converter). They are safe to keep in
  git under §0.3. The ~14 MB P6 SQLite JDBC driver remains git-ignored (only used for P6
  SQLite, never `.mpp`).
- A JDK ≥ 17 is a runtime prerequisite for the native-`.mpp` path (recorded in the gap
  list / setup direction). The pure-Python MSPDI/XER paths need no JDK.
