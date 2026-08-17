# ADR-0409 — HOOK-02: the CUI guard read staged bytes by REVISION syntax, so a git-magic filename made every content detector fail open

**Status:** Accepted · **Date:** 2026-08-16 · **Closes:** HOOK-02 (Ultracode audit round 1,
`security_cui` dimension; lead-re-verified and widened) · **Severity:** critical (Law 1).

## Context

`.githooks/pre-commit` read the **staged** bytes of every sniff candidate as
`git show ":$path"` — the path glued into a single revision argument (bash line 120) and
the identical construction in the embedded python batch (`reason_for`). Git parses that
argument as a *revision*, so the **name's leading bytes are interpreted as magic**:

| name shape | how git reads `":" + name` | result |
| --- | --- | --- |
| `!plan.json` (with any file the exclusion matches) | `:!…` exclude-pathspec | `fatal: ambiguous argument`, exit 128 |
| `^plan.json` | `:^…` negated revision | resolution failure |
| `0:plan.json` / `1:plan.json` | `:<stage>:<path>` merge-stage syntax | a stage that does not exist |
| `:(icase)plan.json` | pathspec magic | no match |

Every one yields **empty stdout**, and empty bytes read to every content detector as
*"nothing to see here."* The extension detector (name-based) still fired, so `!secret.mpp`
was caught — but the classes where the **content sniffer is the only barrier** were wide
open: `.json` (deliberately NOT gitignored, because it is the tool's own Save format),
`.txt`, extension-less, `.md`, images, PDFs and archives. A real CUI schedule committed
**silently** under `!plan.json`. Measured 2026-08-16 against the real hook; `git add -A .`
stages such names with no special flags, so this needed no exotic tooling to trigger.

This is the same **fail-open-by-name** class ADR-0399 fixed for C-quoted/trailing-space
names — the git-magic variant was missed, and no test covered it.

## Decision

**Resolve the staged blob by INDEX OID; never let a path be parsed as a revision.**
Both detectors now go through one helper (`staged_blob` in bash, `_staged_blob` in the
python batch): `git --literal-pathspecs ls-files -s -z -- <path>` → `git cat-file blob <oid>`.
The name is then only ever a *pathspec*, and `--literal-pathspecs` disarms the magic on
that side too (load-bearing, not decorative: without it a colon-leading name returns no
index entry at all — measured).

Two constraints shaped the implementation, both discovered by measurement:

- **The naive fix is not enough.** Adding the rev/path separator (`git show ":$path" --`)
  closes the `!`/`^` variants but **not** `:<stage>:<path>`, because that ambiguity lives
  *inside* the revision expression. Sandbox-measured before implementing: variant A left
  three shapes open, variant B closed all ten.
- **The bash helper parses with builtins only** (`IFS=' ' read -r -d ''`), never
  `head`/`cut`/`tr`. Detectors 1–2 are the floor that must survive a thin toolchain, and
  the first implementation — which used those three binaries — was caught by the repo's
  own `test_hook_without_python3_keeps_the_extension_and_text_floor`.

`inherited_from_main` (ADR-0152's merge exception) keeps its `git rev-parse` form: an
unresolvable name there makes it return "not inherited", which **fails closed** (the
violation stands). Measured: a magic-named blob identical to `origin/main` is still
allowed; a tampered one is still blocked; only the exotic `1:<name>` shape over-blocks,
which is the safe direction.

## Verification (QC-1) — triple, by independent instruments

1. **pytest, red-first.** Six new parametrized cases in
   `test_hook_blocks_schedule_content_under_git_magic_names` failed **by name** against the
   unfixed hook; the whole module is 90 → **98 passed** after. `_stage_literal` asserts the
   file actually reached the index, so a "never staged" case can never masquerade as
   "blocked". A negative control pins that a benign config under a magic name still commits.
2. **An independent bash battery** (three harnesses, built before the tests and not sharing
   their code): 10 hostile shapes blocked, 4 benign controls still allowed, the ADR-0152
   inherited/tampered pair intact.
3. **Mutation battery, 4/4 caught by the named test** — M1 the original bug · M2 the naive
   `--` fix · M3 the python read reverted · M4 `--literal-pathspecs` dropped. Hook restored
   md5-identical; pristine controls green on both sides.

**The layer trap, paid again.** With the outcome assertion alone, **3 of 4 mutants
survived** — including M1, the original defect — because the bash and python sniffers are
defence-in-depth twins over the same files, so breaking one leaves the other to catch it.
`test_bash_floor_blocks_git_magic_names_without_python3` runs the magic-name cases on a
PATH of only `git`+`grep`, pinning the bash layer directly; with it, all four die.
**M4 was also unkillable as first written** (a *bare* `!name` is only magic when prefixed
with `:`), so the parametrization gained a colon-leading name to make the flag's removal
reachable — the "a mutant that cannot fail is not a mutant" rule from ADR-0408, applied.

## Deliberately NOT done

- **No change to `inherited_from_main`.** It fails closed on unresolvable names; rewriting
  it would touch the merge path (ADR-0152) for no security gain.
- **No new detector.** HOOK-02 is an input-plumbing defect, not a missing signature: the
  detectors were always correct, they were being fed nothing.
