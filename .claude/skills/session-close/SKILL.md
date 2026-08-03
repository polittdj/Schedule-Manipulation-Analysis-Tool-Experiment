---
name: session-close
description: Close out a unit of work in POLARIS/SMAT — write the ADR, rotate the handoff, append the session log and the daily lessons entry, refresh the kickoff prompt, rebuild the wheel and nine installers if shipped code changed, run the gate, commit, push and open the draft PR. Use at the end of any session that changed the repo, when asked to "wrap up", "close the session", "write the handoff", "write the ADR", "update the state docs", "commit and push", or when the drift guard (tests/test_state_docs.py) fails. The rotation has a shape that FAILS a test if done wrong.
---

# Session close (durable state + release ritual)

**Git is the memory, not the chat.** This ritual is why a months-long build survived ~130 sessions and
context compaction. `tests/test_state_docs.py` enforces most of it, so getting the shape wrong is a
**red gate**, not a style nit.

## 1. Write the ADR — one per significant decision

`docs/adr/NNNN-<kebab-slug>.md`, where `NNNN` = highest existing number + 1 (zero-padded to 4):

```bash
ls docs/adr | sort | tail -3
```

Structure that matches the house style: a title line naming the *finding*, then
`**Status:** Accepted · **Date:** YYYY-MM-DD · **Extends/Supersedes:** ADR-NNNN`, then **Context**
(with the measured evidence, in tables where there are numbers), **Decision**, **Consequences**, and —
where it applies — a **"Deliberately NOT done"** section recording what was measured and consciously
left alone. That section is load-bearing: it is how a future session distinguishes a stale audit row
from a deliberate exception, which look identical from a table.

## 2. Rotate the handoff — MOVE, do not stack

`docs/STATE/HANDOFF.md` holds **only** the current STATUS section plus a single
`# (prior) handoffs — archived` pointer (ADR-0246). The SessionStart hook auto-injects everything above
the first `# (prior)` heading, so that section is what every future session actually reads.

**The rotation, exactly:**

1. Take the current section — everything **above** the first `# (prior)` heading.
2. Demote its heading `# Handoff — …` → `# (prior) Handoff — …`.
3. **Prepend** it to `docs/STATE/HANDOFF-ARCHIVE.md`, immediately after that file's 4-line header
   (newest-first, verbatim).
4. **Replace** the section in `HANDOFF.md` with the new one. Leave the `# (prior)` pointer block
   untouched at the bottom.

**Never stack a second `# (prior)` heading in `HANDOFF.md`** — the size guard fails.

The new section must satisfy all four guards:

| Guard | Requirement |
| --- | --- |
| `test_handoff_references_latest_adr` | the highest ADR on disk appears as `ADR-NNNN` |
| `test_handoff_top_section_pins_the_current_pyproject_version` | `pyproject.toml`'s version appears in the **top** section |
| `test_handoff_stays_one_pass_readable` | file ≤ **64 KB** and exactly **one** `# (prior)` heading |
| `test_session_log_references_latest_adr` | the same ADR token appears in `SESSION-LOG.md` |

Content that earns its place: what landed · what was **measured** (with the numbers) · how it was
verified (the revert results) · what is **deliberately not fixed** · what is carried forward ·
the named traps this session paid for. Write figures you have **re-read**: *a number written
mid-session is not a measurement.*

## 3. Append the session log

`docs/STATE/SESSION-LOG.md` is **append-only, newest at the BOTTOM**. One dated entry per session with
the branch, the ADR, what changed, and how it was verified. Must contain the latest ADR token.

## 4. Append the daily lessons entry — standing rule, do not batch it

`docs/STATE/LESSONS-LEARNED.md`, **Part VIII, newest FIRST** (top of that part):

```
### YYYY-MM-DD — <one-line headline stating the lesson, not the task>
```
then 2–8 tight bullets: what happened · what was tried · what worked / what didn't · **the lesson**.

Operator directive (2026-07-19): **update this log every working day** — every session that changes the
codebase, at the moment a lesson is learned. When a lesson generalizes, promote it into the themed
sections (Parts IV–VI). Update Part VII's key numbers when they move.

## 5. Refresh the kickoff prompt

`docs/STATE/NEXT-SESSION-PROMPT.md` — a **pointer, not a status snapshot** (HANDOFF always wins on a
disagreement). Refresh it whenever the queue changes; a stale kickoff steers a fresh session at work
that is already done. Keep its four blocks current: WHAT'S DONE (do not re-open) · NEXT · the traps
this session paid for, **by name** · measured-false, do NOT re-chase.

## 6. If shipped code changed: version + wheel + nine installers, ONCE

Only when `src/` changed. Docs-only and `.claude/`-only changes need none of this.

```bash
# 1. bump [project].version in pyproject.toml BEFORE running the suite
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl
```

`tests/installer/test_installers.py::test_embedded_wheel_is_in_lockstep_with_the_source_tree` compares
**every** packaged `schedule_forensics/**` file inside the embedded wheel byte-for-byte against
`src/`. **If you touch code after building, REBUILD** — a merged fix once never reached users because
all nine installers embedded a wheel built 14 hours earlier and the version had not been bumped
(ADR-0148).

## 7. Run the full gate

See the `full-gate` skill. Statics foreground first, then the suite, then `-m parity`.

## 8. Branch, commit, push, draft PR

```bash
git fetch origin                                   # ALWAYS — local main goes stale between sessions
git switch -c <branch> origin/main                 # branch fresh from the REAL latest main
…
git push -u origin <branch>                        # retry 2s/4s/8s/16s on network errors only
```

- Branch from `main`, open a **draft PR**, get CI green, squash-merge. Squash-merges make stacked
  branches conflict — branch fresh and merge-resolve rather than stacking.
- **After a squash-merge, restart the branch with `--prune`:**
  ```bash
  git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch> origin/main
  ```
  GitHub auto-deletes the merged head branch, so the stale remote-tracking ref makes the stop hook
  mis-report GitHub's own squash commit (committer `noreply@github.com`) as an unpushed commit.
  **Never** amend or rebase that squash commit to satisfy the hook — it is published `origin/main`
  history, and rewriting it breaks the CUI guard's `inherited_from_main` rule.
- **If the PR for the designated branch is already merged**, treat follow-up work as a fresh change:
  restart the branch from the latest default branch and open a **new** PR. Never stack new commits on
  already-merged history.
- CI takes ~11 min to register checks; `test (3.11)`/`test (3.13)` run ~30 min. On a PR that touches
  the installers, **six** checks must go green: `check` · `linux` · `windows` ·
  `browser (measured-box proof)` · `test (3.11)` · `test (3.13)`. `linux`/`windows` come from
  `installer-smoke.yml`, which is **path-filtered** to `installer/**`, `tools/installer/**` and its own
  workflow file — so a PR outside those paths legitimately shows **four**. Confirm which set applies
  before calling a run incomplete.

## 9. Do not merge mid-round

Merging mid-round does not just ship unverified code — **it blinds the verifier** (2026-07-28 cont.9),
because the pristine tree the revert diffs against is gone.
