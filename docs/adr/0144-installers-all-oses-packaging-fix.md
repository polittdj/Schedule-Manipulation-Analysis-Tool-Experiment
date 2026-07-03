# ADR-0144 — Installers for all three OSes, a wheel-packaging fix, and real-OS smoke CI

## Status

Accepted. Extends the ADR-0143-session Windows installers; the packaging fix is a **deployment
blocker found by actually executing an installer**.

## Context

The Windows installers shipped untested-by-execution (no Windows in the build container). Two gaps
remained: the spec's macOS/Linux variants, and any *executed* verification. Executing the new Linux
installer end-to-end in the build container immediately caught a real defect:

**The wheel never packaged the non-Python runtime data.** `pyproject.toml` had no
`[tool.setuptools.package-data]`, so `web/static/*` (the vendored, air-gapped JS/CSS) and
`web/examples/*` were absent from the wheel. A wheel-based install **crashed at startup** mounting
`/static` — while every dev environment worked, because `pip install -e` reads the source tree.
Every prior "installer verified" claim covered structure, not execution; this is exactly the class
of gap the operator's "assume nothing, verify everything" directive exists for.

## Decisions

1. **Packaging fix.** `[tool.setuptools.package-data] schedule_forensics = ["web/static/*",
   "web/examples/*"]`. A regression test asserts the declaration AND that the embedded wheel in
   every installer actually contains ≥30 static assets + the bundled example.
2. **Linux (`install-tierN.sh`) and macOS (`install-tierN.command`) installers**, generated from
   bash templates by the same `tools/installer/build_installers.py` (now 3 tiers × 3 OS families,
   one embedded wheel shared byte-identically — test-enforced). Same contract as Windows:
   check-before-install, tool from the embedded wheel (no internet for the tool itself), optional
   Ollama + tier model, Start/Stop launchers (`~/.local/bin` + `.desktop` entries on Linux;
   Desktop `.command` files on macOS), uninstaller, first-run README.
3. **Smoke mode everywhere** (`SF_INSTALLER_SMOKE=1` + `SF_INSTALL_ROOT`): non-interactive, temp
   root, AI/Java skipped, no shortcuts — the hook that makes installers CI-executable.
4. **Real-OS smoke CI** (`.github/workflows/installer-smoke.yml`, path-triggered):
   *windows-latest* parses all three `.ps1` with the PowerShell language parser and executes the
   tier1 smoke install (embedded wheel → venv → import → wheel-static-assets assertion);
   *ubuntu-latest* syntax-checks the bash family and runs tier1 through the **full lifecycle** —
   install → launcher serves the dashboard → `/static/app.js` HTTP 200 **from the wheel** →
   graceful stop via the generated stop script → uninstall removes everything.
5. **In-container execution evidence (this session):** the Linux tier1 installer ran end-to-end —
   venv created, embedded wheel installed, `import schedule_forensics` OK, launcher served
   `http://127.0.0.1:8321` with static assets HTTP 200, `stop-schedule-forensics.sh` shut it down
   gracefully, the uninstaller removed the install dir. The first run (pre-fix) reproduced the
   startup crash; the second (post-fix) is the passing run.

## Consequences

- A recipient's install is now backed by an executed lifecycle on Linux (in-container + CI) and an
  executed smoke install on real Windows (CI) — the "first run is the operator's test" caveat now
  applies only to the interactive extras (winget prompts, shortcuts, Ollama pulls).
- The wheel is deployable, and the introspection-style tests keep it that way (package-data
  declaration + wheel-content assertions per installer family).
- installer/ grows to nine generated files (~600–800 KB each) plus the distributable README.

## Alternatives considered

- **Ship Windows-only and wait for the operator's first run.** Rejected: executing the Linux
  variant here found a deployment blocker *before* any recipient hit it — the cost of the extra
  variants paid for itself immediately.
- **MANIFEST.in + include-package-data.** Equivalent outcome; explicit `package-data` globs are
  narrower and self-documenting.
