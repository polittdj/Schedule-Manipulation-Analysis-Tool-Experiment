# ADR-0455 — CI event triggers fire (the 2026-08-26 `startup_failure` was a GitHub-side anomaly), the route-coverage instrument is committed, and Law 1's blocklist runs in CI

- **Status:** Accepted — 2026-09-03 (WP4 of the POLARIS² audit campaign)
- **Version:** 1.0.233
- **Extends:** ADR-0347 / ADR-0399 (the pre-commit CUI guard), ADR-0421..0423 (the 2026-08-18 route × test census), ADR-0418 (the browser census computed at the moment of use)
- **Shipped:** `tools/route_coverage.py` (NEW — inventory · passive recorder · gap analysis · CLI), `tests/conftest.py` (the opt-in `SF_ROUTE_COVERAGE` plugin), `tests/guards/test_route_coverage_instrument.py` (11, NEW), `tools/ci_cui_guard.sh` (NEW), `tests/guards/test_ci_cui_guard.py` (8, NEW), `.github/workflows/ci.yml` (job `cui-guard`, now in `check`'s `needs`), `.github/workflows/installer-smoke.yml` (`workflow_dispatch`), `tests/guards/test_workflow_action_pins.py` (+2), `.gitignore` (`/route_coverage*.json`)

## Context — three claims the ledger carried as testimony

**1. "Event-triggered CI is still NOT firing."** The 2026-08-25/26 handoff recorded it as a
standing condition ("push/PR runs not created; `workflow_dispatch` works — dispatch manually per
push"); the campaign plan time-scoped it to one observable — the 2026-08-26T15:31:22Z push run
ended `startup_failure` — and queued the root cause for WP4.

**2. The route-coverage instrument that settled the population was never committed.** The
2026-08-18 census (137 endpoints; 3 never answered 2xx; 25 with no adverse coverage) was measured
with a pytest plugin hooking `FastAPI.build_middleware_stack` that lived in a session scratchpad:
`git log -S build_middleware_stack -- '*.py'` is empty. Its two headline numbers could not be
re-derived, and the population moved (137 → 139 by 2026-08-27) with nothing measuring it.

**3. A GitHub web upload bypasses the pre-commit guard.** On 2026-09-03 six operator web-UI
uploads landed four `.docx` and a copy of the tool's own Save-format `house_build.json` under
`00_REFERENCE_INTAKE/src/` — paths the hook refuses — and the only instrument that noticed was the
intake-manifest guard, one PR later (#627). CLAUDE.md also states the other half of the gap: a
clone that never ran the SessionStart hook has **no** hook protection at all.

## What was measured (QC-1)

### The 2026-08-26 `startup_failure` — GitHub-side, ~70 minutes, not a repository fault

| evidence | value |
| --- | --- |
| run | #1656 (id 32985375962), `push` on `main` @ `30f90f1c` (the #612 squash-merge) |
| created → updated | 15:31:22Z → 15:31:26Z; `run_duration_ms` **4000**; billable **0 ms** |
| jobs | 5 created; `test (3.11)`, `test (3.13)`, `floor`, `browser` never left `queued`; `check` skipped 15:32:45Z; job logs 404; check-run output empty |
| workflow file | `ci.yml` byte-identical between the green run before (#1655, 08-25), this run, and the green run after (#1659, 08-26 16:42Z); last `ci.yml` change 08-17 (#598); #612 touched no `.github/` file |
| event → run latency, `main`, 2026-08-13 → 09-03 | **2–4 s** for 48 of 50 push runs (15 s worst, on 09-03's six-upload burst) |
| the two exceptions, both on 08-26 | **247 s** to create the run that then died in 4 s; **1,281 s (21 min)** to create the next push's run (`05abadc5` committed 16:20:55Z, run 16:42:16Z) |
| the "manual dispatch works" observation | the session on duty dispatched `ci.yml` at 16:22:33Z (#1657) — inside the 21-minute gap — and the late-arriving push run cancelled it through the `ci-CI-refs/heads/main` concurrency group |

A workflow-file fault is deterministic per file content; the same bytes ran green on both sides of
the failure. Zero billable milliseconds and four jobs that never left `queued` put the failure
before any runner was assigned. The delayed creation of the next run is the same window seen from
the other side. **Verdict: a ~70-minute GitHub-side Actions anomaly (15:27–16:42Z), not a
repository fault; the standing "triggers are not firing" claim is REFUTED — every one of the 50
`main` commits since 2026-08-01 has a push run, and every merged PR head had a `pull_request`
run.** Whether GitHub posted an incident for that hour is **UNVERIFIABLE from the build
container** (`githubstatus.com` is egress-blocked); the operator can settle it from the status
history for 2026-08-26.

A second finding rode along: `main`'s run for `b631b41f` (the #626 merge, run #1700) concluded
`failure` — the intake-manifest guard the six web uploads broke, repaired by #627 — while the six
upload commits' own runs were all `cancelled` by the next push. *A green PR head is not a green
`main`; read the merge commit's own run.*

### The route population, re-derived by a committed instrument

`tools/route_coverage.py::inventory` reads the live app: one endpoint per declared
``(method, path)`` pair (a path serving GET and POST counts twice — the 2026-08-18 convention that
made `/settings` two endpoints) plus one per mount; Starlette's implicit `HEAD` beside a GET is
not a declared endpoint and is not counted (`/openapi.json` is the one route that declares it).

| | 2026-08-18 | 2026-08-27 | **2026-09-03 (this instrument)** |
| --- | --- | --- | --- |
| population | 137 | 139 | **148** — 71 page · 34 api · 42 export · 1 static |

The floor the CLI and the guard enforce is **139** — the campaign's recorded figure — so an
inventory below it means the instrument stopped seeing the app, never that the app shrank
quietly. The recorder is installed by patching `FastAPI.build_middleware_stack` (a **class**
attribute, so an app built before OR after the patch is caught at its first request — the
import-timing defeat a `create_app` patch suffers), resolves the template **before** dispatch on a
copy of the scope (a `Mount` rewrites the scope it handles — the first run of the guard test lost
the `/static` hit to exactly that), records the status and the session's loaded-schedule count at
entry (a 200 empty state is adverse coverage, the census's own definition), and keeps three
buckets: full matches (coverage), partial matches (path known, method not served — a 405 credits
no endpoint) and unmatched requests (a 404 by absence). It is **passive**: the guard compares a
wrapped and an unwrapped response byte-for-byte.

The gap **by name** — the endpoints the whole suite never reaches, never answers 2xx/3xx on, or
never answers adversely — is the ledger's row (`docs/STATE/AUDIT-2026-08-27.md`, "WP4"), written
from the instrumented full run of this tree and re-derivable with two commands.

### Law 1 in CI

`tools/ci_cui_guard.sh` runs **the hook itself** (one blocklist in the tree, never a copy) over
exactly what a push or PR adds or changes: `git reset --soft <base>` stages the `base..HEAD` diff
the hook already scans, and `refs/remotes/origin/main` is aimed at the base first, because on a
push to `main` that ref *is* the pushed commit and every blob would exempt itself through the
inherited-blob exception. HEAD is restored whatever the verdict.

## Decisions

1. **The outage claim is closed as REFUTED; the 08-26 anomaly is CONFIRMED and attributed
   GitHub-side.** No dispatch-per-push discipline is owed. The check that stays: after a push,
   look at the run's *conclusion* — `cancelled` and `startup_failure` are not green.
2. **The instrument is committed, opt-in and passive.** `SF_ROUTE_COVERAGE=1 python -m pytest`
   writes `route_coverage.json`; `python tools/route_coverage.py route_coverage.json --floor 139`
   names the gap and exits non-zero below the floor. It is never on in the plain gate.
3. **Law 1 runs in CI, with an event-shaped policy.** On a `pull_request` every violation fails
   the job, and the job is in `check`'s `needs` — a build session cannot bypass the blocklist by
   never activating the hook. On a `push` to `main` a violation **under `00_REFERENCE_INTAKE/`** is
   a warning with a job summary: that tree is the operator's sanctioned web-upload intake channel
   (ADR-0152), the commit is already on `main`, and a permanently red `main` for sanctioned
   intake would only teach everyone to ignore red. A schedule file **anywhere else** is an error on
   both events. The job's last step stages a probe `.mpp` and requires the hook to refuse it
   (ADR-0300's rule: a guard that cannot fail proves nothing).
4. **Every workflow offers `workflow_dispatch`**, pinned by a guard that reads the `on:` block
   (a trigger hiding elsewhere in the file does not count).

## Verification (QC-1)

- Instrument guard: 11 tests. Mutation — the matcher forced to `UNMATCHED` → **3 red by name**
  (template resolution, partial-match, passivity), 8 green; the floor check on `FLOOR - 1` raises
  by name; tree restored byte-for-byte from a scratch copy.
- CI guard: 8 scratch-repo tests, each running the real script and the real hook; the dead-hook
  mutation (`exit 0` in place of the hook) is a test of its own and reddens the self-test. The
  self-test against the real tree refused a staged `.mpp` (exit 1).
- Dispatch guard: `workflow_dispatch:` deleted from `installer-smoke.yml` → exactly
  `test_every_workflow_offers_a_manual_trigger[installer-smoke.yml]` red, 7 green; restored.
- Both workflow files parse as YAML; every `uses:` stays SHA-pinned (the existing guard).

## Deliberately NOT done

- **No attribution of the 08-26 hour to a named GitHub incident** — unverifiable from here; the
  evidence above stands on the repository's own run history.
- **No coverage floor on the gap itself.** The census's own reading holds: traffic is not
  assertions, so "reached" is a lower bound on tested and the by-name list is a work queue, not
  a pass/fail. The only hard floor is the population's.
- **No hard failure on a push to `main` for intake uploads** — see decision 3; the operator can
  flip the policy in `tools/ci_cui_guard.sh` in one line if disclosure proves too quiet.
- **The instrument is not run by CI.** A ~45-minute instrumented run is a measurement to take
  when the queue asks for it, not a per-push cost; the population floor is the cheap standing
  guard.
