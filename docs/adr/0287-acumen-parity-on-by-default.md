# ADR-0287 — Acumen Fuse parity mode is ON by default for a new session

Status: accepted (2026-07-24) — operator directive ("find the root cause and correct it")

## Context

The operator loaded `Large_Test_File2.mpp` into the deployed tool, compared the DCMA-14 ribbon with
Acumen Fuse's on the same file, and reported: *"the tool gives the exact same measures … and those
values are still different than what Acumen Fuse provides."*

Re-verified against the operator's own evidence this session:

- The `.mpp` and Acumen's **Analysis Metrics** detail export were **byte-identical** to the copies
  supplied that morning (md5 match); a freshly re-exported **MS Excel Metrics** ribbon differed in
  bytes but carried **identical numbers**. So neither the input nor the oracle had changed.
- The operator's screenshot showed the toggle reading **"Acumen Fuse parity mode ☐ OFF — pure-logic
  / forensic view"**, and every value on it reproduced the engine's **default-mode** output exactly
  (Logic 3, High Float 717/998, Negative Float 123/998, Invalid Dates 182/1722, Resources 864/919,
  Missed 1221/1357, CPLI 1.0, BEI 0.51).
- With the box **checked**, the same file already reproduces Acumen **UID-exact** on every check
  with a Fuse detail list (ADR-0280, ADR-0283): 660 / 112 / 173 / 842 / 1095, CPLI 0.59, BEI 0.53.

So there was no engine defect. The root cause is a **defaulting** problem: the tool's headline
promise is that its DCMA-14 ribbon reconciles with Acumen Fuse on the same file, but a fresh session
silently answered a *different question* (the independent pure-logic read) until the operator found
and ticked a checkbox. That mismatch was reported as a tool defect **twice in one day** — the
strongest possible signal that the default is wrong for the primary workflow.

## Decision

**`SessionState.dcma_acumen_parity` defaults to `True`.** A new session reconciles with Acumen Fuse
out of the box; unchecking the box restores the independent pure-logic / forensic view.

This is a **session presentation default only**:

- The **engine** default is unchanged — `compute_dcma14`, `audit_schedule`, `compute_bei` and
  `recommend` all keep `acumen_parity: bool = False`. Every golden and parity test passes the flag
  explicitly, so none of them shift.
- The flag is already part of the analysis cache signature (`A=1`), so the toggle re-keys and can
  never serve a stale audit.
- Since ADR-0285 the toggle applies **end-to-end** (ribbon, findings, narrative, risk matrix,
  briefing), so defaulting it ON leaves every surface mutually consistent.

## Consequences

- Out of the box the tool now answers *"what would Acumen Fuse report on this file?"* — which is what
  the operator, and a DCMA scorecard reviewer, expect when comparing against an Acumen report.
- The pure-logic forensic read is one click away and remains fully supported; `docs/ACUMEN-PARITY-MODE.md`
  documents both and when to use each. Its "default" language is updated accordingly.
- Tests that pinned pure-logic payloads now **state their mode explicitly**
  (`st.dcma_acumen_parity = False`) instead of inheriting the session default — better hygiene, and
  it makes each golden say which question it answers. Affected: the two default-mode dashboard SHA
  goldens, the scope-epoch guard, and the LRU-residency perf gate (whose cache key would otherwise
  carry `A=1`).
- `tests/web/test_dcma_scope.py` now asserts the checkbox renders **checked** on a fresh session and
  exercises the toggle in the order off→on.

## Alternatives considered

- **Keep OFF, add a prominent "these will not match Acumen" banner.** Rejected: it documents a
  surprising default instead of removing it, and the operator had already read past the existing
  inline explanation twice.
- **Remove the toggle and ship parity only.** Rejected: the pure-logic recomputation is a genuinely
  different and legitimate forensic instrument (it is independent of the file's stored dates), and
  ADR-0280 deliberately kept both. Defaulting is enough.
