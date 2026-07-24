# ADR-0290 — the `schedule_forensics` package is NOT renamed; the display name already carries the brand

Status: accepted (2026-07-24) — operator decision, closing `00_REFERENCE_INTAKE/RENAME-PLAN.md`

## Context

`RENAME-PLAN.md` (a Claude-Design planning doc the operator committed under `00_REFERENCE_INTAKE/`)
proposed renaming the Python package from `schedule_forensics` to one of five candidate names, and
asked the operator to pick one. Its own §0 recommended **never**, for two reasons this session
verified against the tree:

1. **The user-visible name is already decoupled from the import name.** The UI brand is **POLARIS**
   (`_LAYOUT`'s `<title>`, the masthead `title=` tooltip, and the FastAPI app title). Checked this
   session: the string "Schedule Forensics" appears **zero** times in `web/app.py`'s rendered body and
   **zero** times in the exhibit exports or the executive briefing. The display-name change the plan
   offered as the cheap alternative is therefore **already complete** — there is nothing to change.
2. **The rename's cost is concentrated in the gates, not the code.** `tests/test_packaging.py`
   asserts the literal shortcut/desktop filenames and the exact `"-m schedule_forensics"` argument
   string; `tests/installer/test_installers.py` asserts the embedded wheel is named
   `schedule_forensics-{version}` and byte-compares every packaged `schedule_forensics/**` path
   against the source tree. A rename rewrites all of those at once across ~350–400 files — precisely
   the all-or-nothing failure mode that is hardest to diagnose if it goes wrong.

## Decision

**Do not rename the package.** `schedule_forensics` stays the import name and the wheel name. The
brand stays **POLARIS**, carried entirely by display strings.

The rename is revisited only if the import name must change in someone else's environment — a second
tool importing this package, an external distribution, or a legal/branding requirement. If that day
comes, `RENAME-PLAN.md` is the ready-made execution plan and its all-or-nothing gate is the
definition of done.

## Consequences

- Zero code change, zero risk, zero gate churn — the cheapest possible resolution of the question.
- `RENAME-PLAN.md` remains in `00_REFERENCE_INTAKE/` as a shelved plan, not a pending task. This ADR
  is the record that it was considered and declined on the merits.
- Any future drift where a user-visible surface says "Schedule Forensics" instead of the brand is a
  one-line copy fix, not a rename.
