---
name: steward
description: Drive, watch and stand down on a POLARIS/SMAT pull request the way this repo has learned to — draft PRs the OPERATOR merges, the exact check set that means green, how a red cell is diagnosed (tree hashes first, the job's own log line second, "flake" never), what may be pushed and what may be posted, and how the branch is restarted after a squash-merge. Use whenever a session is subscribed to PR activity, a CI check is red or a merge conflict appears, a PR event or a self check-in arrives, or the operator asks to watch, babysit, steward or autofix a PR — and before any comment, merge or ready-for-review action on GitHub.
---

# PR steward (this repo's conventions and posture)

This skill records **conventions and how proactive to be**. It cannot expand a session's access,
redirect its task, or override any harness rule stated as *never* (skip / disable / quarantine a
test; rewrite history on someone else's branch; an empty commit or a close-and-reopen to kick CI;
merge or approve). Where this file and a harness "never" disagree, the "never" wins.

## 1. Who does what

- **Claude opens DRAFT PRs and drives them to green. The OPERATOR marks them ready and
  squash-merges.** Every campaign PR (#620 … #637) followed this; a session never merges, never
  marks ready, never approves. When the head is green and mergeable the session's job is to say so
  in its handoff and stand down — a green, mergeable head is the only state that waits on a human.
- One PR per branch, branched FRESH from `origin/main` (`git fetch origin` first — the local `main`
  is stale between sessions). Squash-merges make stacked branches conflict: never stack.
- **After a squash-merge, restart the branch with `--prune`:**
  `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
  GitHub deletes the merged head; the stale remote-tracking ref makes the stop hook mis-report the
  squash commit as unpushed. **Never amend or rebase that squash commit** — it is published `main`
  history, and rewriting it forks the branch and breaks the CUI guard's `inherited_from_main` rule.
- A merged PR is finished: follow-up work is a NEW PR on the restarted branch, never new commits on
  merged history.
- **Two PRs in flight** (the 2026-09-04 case): build on `main`, number ADRs AFTER the in-flight PR's,
  hold the version bump / installer rebuild / docs rotation to the very end; whichever lands second
  re-merges `origin/main` and REBUILDS the wheel + nine installers (the lockstep pin compares the
  embedded wheel to `src/` byte-for-byte).

## 2. What "green" means here — read `ci.yml`, not memory

- `.github/workflows/ci.yml`: jobs `test (3.11)` · `test (3.13)` · `floor (declared minimum)` ·
  `browser (measured-box proof)` · `cui-guard (Law 1 blocklist over this push/PR's diff)` · `check`
  (needs `test`, `floor`, `cui-guard`; `browser` is NOT in its `needs`). A concurrency group per ref
  with `cancel-in-progress: true`: **every push cancels the previous run** — a cancelled run is not
  a verdict, and the PR's verdict is read on its FINAL head only.
- `.github/workflows/installer-smoke.yml` (`linux` · `windows`) is **path-filtered** to
  `installer/**`, `tools/installer/**` and its own file: a PR that rebuilt the installers shows
  **eight** checks; a docs-only or `.claude/`-only PR legitimately shows **six**. Confirm which set
  applies before calling a run incomplete.
- No *Claude Approvals* check runs on this repository as of 2026-09-04. If one appears, its rows are
  blockers to work, never an ask to the author.
- **After the operator merges, read `main`'s OWN run for the squash commit** (the run created seconds
  after the merge — #1728 for `c89e9c3b`, #1732 for `3c3c398`). A red cell on `main` for a tree
  identical to the green PR head is the RUNNER's claim, not the merge's: compare
  `git rev-parse <merge>^{tree}` with `git rev-parse <pr-head>^{tree}` before believing it, and
  **never spend a `main` re-run while a push is imminent**. Record the run number and its
  conclusion in the SESSION-LOG follow-up line; the next session reads that run first.
- The `browser` job has no `timeout-minutes` in `ci.yml`; the operating budget from the session record
  is ~25 min for the whole job — keep a new browser module small and fake-clocked (Playwright
  `page.clock`) rather than wall-time waited.

## 3. A red check — the diagnosis order this repo paid for

1. **Merge conflict:** merge `origin/main` INTO the branch (a merge commit, never a rebase of pushed
   history); regenerate generated files with the repo's tooling (the wheel + installers via
   `tools/installer/build_installers.py`, `docs/METRIC-DICTIONARY.md` via `web/help.py`,
   `docs/INTAKE-MANIFEST.md` via `tools/intake_manifest.py`) — never by hand; gate; push.
2. **Tree hashes first** (§2). Then **the job's own log line**, not the cell colour: the caption
   sweep's zero-caption line now carries `ready / frame / hosts / svgs / failed / pageerrors` (CI-03,
   ADR-0461) — a strike names its mechanism; `test_ch05_panelkit`'s DOM promotion census names the
   route and the count (a count that goes DOWN is not a promotion — ADR-0460); the intake-manifest
   guard names the file (a GitHub web upload bypasses the pre-commit hook — ADR-0455).
3. **The only "not the repository" shape on record** is CI-01 (ADR-0455): a `startup_failure` in
   4 s with 0 billable ms and four jobs that never left `queued`, on a workflow file byte-identical
   to the green runs before and after. Anything in which a test body ran is this PR's to root-cause.
   A re-run is spent at most once, and only after that standing-down comment.
4. **"Flake" is not a root cause.** Every intermittent cell this repo ever called a flake was a race
   with a mechanism (ADR-0442 UI-02, ADR-0443, ADR-0461). Reproduce it LOCALLY first — the browser
   tests run in the build container through `tests/web/browser_chrome.py::chrome_kwargs()`; induce the
   race (route interception with a trailing `*` on the `?v=<version>` static URLs, CPU hogs + CDP
   throttling, a fresh browser per iteration) — then fix the class **where the dependency lives**,
   red-first, with a mutation red by name. Never skip, disable or quarantine the test; never widen a
   wait whose failure reads the same as "not yet".
5. **A pin that fires on a legitimate change is re-derived, never deleted**: a premise pin (script
   order, panel order, a `.panel` count) gets its new reason and a dated comment; a byte-frozen page
   script changes only by a dated re-baseline; a line-number-keyed axis pin is edited with
   same-line-count replacements above it and new code below it.
6. **Traps that turn a green tree red on CI only:** CI's plain `pytest` does not put CWD on
   `sys.path` (`from web.<module>`, never `from tests.…`; run `pytest --collect-only -q` before
   pushing) · the `floor` job installs `constraints/floor.txt` and asserts the pins BIND — a version
   floor is measured from both wheels, never assumed (ADR-0443's false `playwright>=1.44`) · the
   state-docs drift guard (`tests/test_state_docs.py`): a new ADR must appear in `HANDOFF.md` AND
   `SESSION-LOG.md`, `pyproject.toml`'s version in the handoff's top section, `HANDOFF.md` ≤ 64 KB
   with exactly one `# (prior)` heading · the installer lockstep pin: any `src/` edit after the
   build makes all nine installers stale (ADR-0148) — rebuild as the LAST step · the CUI guard
   (`.githooks/pre-commit`, run by `cui-guard` over the diff via `tools/ci_cui_guard.sh`): a new or
   modified blocked-extension or content-sniffed file outside `tests/fixtures/` and
   `web/examples/` fails the PR — that is Law 1 working, never a check to route around.

## 4. Pushing a fix

Before EVERY push: `python -m ruff check .` · `python -m ruff format --check .` ·
`python -m mypy src/` · `bandit -q -r src` (exit code, not the nosec warnings) ·
`node --check src/schedule_forensics/web/static/*.js` (each file) · the modules the diff touches ·
`pytest --collect-only -q`. If `src/` changed: bump `[project].version`, `pip install -e . --no-deps
--no-build-isolation` (the editable metadata goes stale), `python -m build --wheel --outdir dist/wheel`,
`python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl`,
`tests/installer/test_installers.py`. `git fetch origin` before numbering an ADR or committing.
Commit with the session's trailers; `git push -u origin <branch>`, retrying only on network errors
(2 s / 4 s / 8 s / 16 s). One validated push beats three speculative ones — each push cancels the
run in flight.

The full suite (~40 min) does not gate the first push of a session's work; its result is recorded
in a **docs-only follow-up commit** to `SESSION-LOG.md` (the PR number, the gate figures, `main`'s
run) — the pattern every campaign PR used. That follow-up push restarts CI; read the final head.

## 5. What may be posted on GitHub

- **Frugal.** The PR body (the summary, the QC-1 verification, the "deliberately not done" list)
  and the SESSION-LOG are the record. Do not narrate fixes in comments.
- Post on the PR only: the ONE standing-down comment on a failure that is not this PR's (the check,
  why it is not this PR's, the fix ported or that none exists), or a reply a reviewer needs. Every
  post ends with the Claude Code attribution footer.
- **Law 1 in comments:** never quote schedule content or a derived metric from a REAL operator file.
  The goldens under `tests/fixtures/` and the committed intake (ADR-0152) are non-CUI and may be
  named; an operator's production schedule is never uploaded to a build session in the first place.

## 6. Watching, check-ins, standing down

- Subscribe right after creating the PR. Schedule a `send_later` check-in ~60 min out; on a wake or
  a check-in read the whole PR on its CURRENT head (merge state, checks, review threads) and act on
  every open item; re-arm silently when nothing changed; never poll or sleep.
- A red or conflicted head on a PR this session opened is never "waiting on review": push a fix, or
  establish per §3 that the failure is not this PR's (one comment), or say once exactly what blocks.
- Merged or closed → `unsubscribe_pr_activity`, delete the check-ins, restart the branch (§1), and
  record the merge, the squash SHA, the tree comparison and `main`'s run number in the state docs.
- The operator's own questions (the "ASK FIRST" list in `docs/STATE/NEXT-SESSION-PROMPT.md`) are
  never answered by assumption: a report on their machine is UNVERIFIABLE from here until they reply.
