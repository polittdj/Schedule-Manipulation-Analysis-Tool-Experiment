# ADR-0344 — The standing rituals become invoked skills, not remembered prose

**Status:** Accepted · **Date:** 2026-08-03 · **Relates to:** ADR-0240 (model/audit protocol),
ADR-0246 (handoff size guard), ADR-0304/0305 (the measured-box proof), ADR-0343 (settled by rendering)

## Context

The operator asked for skills that would help this project. Two searches were run first:

| Source | Result |
| --- | --- |
| account skill catalog (`SearchSkills`, 8 keyword sets) | nothing new — `schedule-forensics`, `session-token-guardian`, `docx`/`xlsx`/`pptx`/`pdf` are already enabled |
| plugin marketplace (`SearchPlugins`, `ListPlugins`) | only `knowledge-work-plugins` (data · marketing · design · operations); the `engineering` and `design` plugins are already enabled |

So there was **nothing to install from a marketplace.** The gap is not a missing third-party skill; it
is that this repo's own standing rituals live as prose in five places — `CLAUDE.md`,
`docs/STATE/HANDOFF.md`, `docs/DESIGN-SYSTEM.md`, `docs/STATE/NEXT-SESSION-PROMPT.md`, and 3,028 lines
of `docs/STATE/LESSONS-LEARNED.md` — and are re-derived, or missed, session by session.

`LESSONS-LEARNED.md` Part III already diagnosed this: **"Prose reminders decayed; tests didn't."** The
countermeasure it prescribes — *turn every process failure into an executable guard* — is the right one
and has been applied wherever a guard is expressible as a test (the drift guard, the wheel↔source
lockstep, the metric-dictionary sync, the DD-line ledger). But several of the most expensive rituals
are **not expressible as a test**, because they govern *how a session works*, not what the tree
contains:

- how to run the gate so a piped exit code cannot hide a failure;
- how to prove a new test can fail before trusting that it passes;
- when to render the page instead of reading the source that produces it;
- the handoff rotation's exact shape (which a test can only check *after* it was done wrong).

A skill is the missing rung: an **invoked procedure** whose body loads on demand, rather than a
paragraph a session hopes to recall.

## Decision

Commit seven project skills under **`.claude/skills/<name>/SKILL.md>`**, one per documented recurring
failure class, each citing the ADR or lessons-log date that bought it:

| Skill | Scope | Bought by |
| --- | --- | --- |
| `full-gate` | the complete gate + real-vs-environment triage | the piped-exit-code miss (2026-07-30 cont.4); `node --check` on a glob; "I reported a green suite I never read" (cont.2) |
| `prove-able-to-fail` | falsify a test/guard/census before trusting it | ADR-0304, ADR-0305, 2026-08-01i, 2026-08-02b/e |
| `render-verify` | render and measure the real page | ADR-0343, ADR-0317, 2026-08-02g |
| `metric-parity` | Law 2 — numbers vs the oracles | ADR-0045→0116, 0108, 0150/0220, 0185, 0221/0224 |
| `ui-change` | the Mission Ops DoD | ADR-0195, 0298/0326, 0340, 0342 |
| `cui-guard` | Law 1 — egress, git, air-gap, fail-closed AI | ADR-0144, 0152, 0241, 0264→0268 |
| `session-close` | ADR + rotation + logs + wheel/installers + PR | ADR-0148, ADR-0246, the twice-repeated state-doc drift |

`.claude/skills/README.md` records why they exist, what each prevents, and how they relate to the
existing `qc-checker` subagent and the SessionStart hook.

**Committed, not personal.** Verified from the Claude Code skills reference: cloud/web sessions and
routines load project skills from the cloned repository's `.claude/skills/`, and ignore
`~/.claude/skills/` on any machine. Since this project is driven largely from web sessions, a personal
skill would have been invisible exactly where it is needed.

### Verification

- All seven files parse as YAML frontmatter with `name` == directory name; descriptions are 488–567
  characters, well inside the 1,536-character listing cap.
- No name shadows a bundled skill (`/review`, `/code-review`, `/security-review`, `/simplify`, `/run`,
  `/init`, `/loop`), so nothing bundled is silently replaced.
- `render-verify`'s Tier-1 recipe was **executed**, not drafted: it rendered `/cei` against the five
  committed `TP4_DataCenter` fixtures (200, 25,850 bytes) and read back the real takeaway `h1`. The
  launch-nonce normalisation it prescribes is the one that makes a two-tree render diff meaningful.
- `full-gate`'s prerequisite list was executed in this container: `pip install -e ".[dev]"` resolves to
  1.0.159, and the vendored chromium the browser tier globs for is present at
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.

## Consequences

- Every future session — local, web, or routine — starts with these procedures one invocation away,
  and `CLAUDE.md` stays a statement of *law* rather than growing further into a *runbook*.
- The claims inside a skill are load-bearing, so they carry the same obligation as an ADR: each rule
  names its source, and a future session can verify it against the code instead of trusting it.
- Per ADR-0240, anything parity-, engine-, testimony- or CUI-relevant that a skill asserts is still
  re-validated by the lead before it lands. A skill is a checklist, never an oracle.

### Deliberately NOT done

- **No marketplace install.** Nothing relevant existed; recording the empty search result is the
  honest outcome and stops the next session repeating it.
- **`.claude/settings.json` untouched.** Skills need no registration, and the assistant is barred from
  editing its own startup/hook config (`.claude/agents/README.md`); the `qc_session_start.sh` hook is
  still unregistered and still needs a human.
- **No version bump, no wheel/installer rebuild.** Nothing under `src/` changed, so the ADR-0148
  lockstep test is unaffected. Verified by running the installer suite.
- ~~This session cannot observe the skills loading.~~ **Superseded by measurement, same session.**
  The caveat above was written from the documented mechanic ("a *newly created* top-level skills
  directory requires a restart to be watched"). It did not hold here: **all seven appeared in this
  session's live skill listing with no restart**, and the listed `cui-guard` text was the *edited*
  description — written minutes after the file was first created — so the loader was demonstrably
  re-reading the files from disk, not a cached snapshot. The documented restart caveat evidently
  applies to a skills directory created outside a watched parent; `.claude/` already existed here and
  only `.claude/skills/` was new. **Recorded as measured, not as assumed** — and left visible rather
  than quietly deleted, because the sequence *(state the limitation → then measure it away)* is the
  behaviour ADR-0240 asks for.
- **The rituals are not converted to tests.** Where a guard *is* expressible as a test it already is
  one; these seven are the residue that governs session conduct. If any of them later becomes
  testable, the test wins — Part III's ladder still ends at executable guards.
