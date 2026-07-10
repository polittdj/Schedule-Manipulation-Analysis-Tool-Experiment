# ADR-0191 — Windows installer: survive machines with only python.exe (no py launcher)

## Status

Accepted. Operator 2026-07-10 (live install transcript): `install-tier1.ps1` died at venv
creation with `The term 'p' is not recognized` on a machine whose only Python was
`python.exe` (no `py` launcher).

## Context

`Find-Python` returns the discovered interpreter as an array (`@("py","-3.11")` or
`@("python")`) so the caller can invoke it with or without a version flag. PowerShell,
however, **unrolls a returned 1-element array into its bare element** — so on a
python-only machine `$py` became the *string* `"python"`, `$py.Count` was still 1
(PS 3.0+ gives scalars a Count), and `& $py[0]` invoked the first **character** `'p'`.
Machines with the `py` launcher returned a 2-element array (not unrolled), which is also
why the windows-latest CI smoke — whose runners always carry the launcher — never walked
this branch.

## Decisions

1. **Unary comma on the returns** (`return ,@($exe)` / `return ,@($exe, $flag)`) so the
   array survives the function boundary, plus a defensive `$py = @($py)` at the call site
   so no future refactor can put a bare string in front of the indexed invocation.
2. **CI now walks the operator's exact path**: the windows-latest smoke gained a second
   tier1 run with a failing `py.cmd` stub ahead of PATH (masking the launcher) and a
   setup-python 3.12 `python.exe` first on PATH — forcing the single-candidate discovery
   branch end-to-end (install → venv → import).
3. Static regression pin in `tests/installer`: the unary commas + defensive re-wrap must
   be present in the template AND all three generated .ps1 installers, and the smoke
   workflow must keep the launcher-masking leg.

## Consequences

- The operator's failed install is recoverable by re-running the fixed installer as-is —
  the venv step is idempotent (`venv already present (re-using)` / fresh create).
- sh/command families are unaffected (they pass `"$PY"` as a single string by design).
