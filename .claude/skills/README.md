# Project skills

Committed Claude Code **skills** for this repo. Each `<name>/SKILL.md` is a skill definition (YAML
frontmatter — `name`, `description` — plus the procedure). They are auto-discovered from
`.claude/skills/<name>/SKILL.md`; **no `settings.json` registration is needed** (verified against the
Claude Code skills reference, 2026-08-03).

Three mechanics worth knowing, all verified from that reference:

- **A session started before this directory existed does not see them.** Claude Code watches skill
  directories for live changes, but a *newly created* top-level skills directory needs a restart to be
  watched. Every session after this one picks them up at startup.
- **Cloud / web sessions load project skills committed to the cloned repo's `.claude/skills/`** — which
  is why these are committed rather than kept in `~/.claude/skills/`. A personal skill is invisible to
  a cloud session or a routine.
- **The command name comes from the DIRECTORY name**, not the frontmatter `name` (which is only the
  display label for a project skill). The two are kept identical here. None of these names shadows a
  bundled skill (`/review`, `/code-review`, `/security-review`, `/simplify`, `/run`, `/init`, `/loop`) —
  a same-named project skill would silently replace the bundled one.

## Why these exist

The standing rules of this project live as prose in `CLAUDE.md`, `docs/STATE/HANDOFF.md`,
`docs/DESIGN-SYSTEM.md` and 3,000 lines of `docs/STATE/LESSONS-LEARNED.md`. `LESSONS-LEARNED.md`
Part III already names the failure mode: **"prose reminders decayed; tests didn't."** A skill is the
middle rung of that ladder — an *invoked procedure* rather than a paragraph a session hopes to
remember, for the rituals that cannot be expressed as a test.

Every skill below encodes a **documented, already-paid-for** failure class from this repo's own
history, with the ADR or lessons-log date that bought it. Nothing here is generic advice.

| Skill | Covers | The failures it exists to prevent |
| --- | --- | --- |
| `full-gate` | the complete pre-commit gate + real-vs-environment triage | a piped exit code hiding a real `bandit` failure; `node --check` on a glob checking only the first file; a green suite reported but never read; env-gated skips "fixed" as errors |
| `prove-able-to-fail` | falsifying a new test/guard/census before trusting it | ADR-0304 (a ⛶ assertion green for months while the control moved nothing); ADR-0305 (a proof job green in 59 s with every proof skipped); a `-k` filter deselecting the target test |
| `render-verify` | rendering and measuring the real page | ADR-0343 (three rows UNSURE for five weeks behind "I did not execute the rendered page"); source call sites ≠ rendered charts; `_stat_cards` emitting value-then-label |
| `metric-parity` | Law 2 — metric/CPM/importer numbers vs the oracles | ADR-0045→0116 (a span-snap spot-checked, never run end-to-end: 325/783); ADR-0150/0220 (pure-logic vs effective critical); ADR-0185 (XER keyed on a renumbering id) |
| `ui-change` | the Mission Ops design system + its Definition of Done | ADR-0195 (a forced redesign after dozens of unsystematised tweaks); ADR-0342 (a DD line on a version axis); `--danger` (which does not exist) |
| `cui-guard` | Law 1 — what may leave the machine or enter git | ADR-0152 (the guard vs the real workflow); ADR-0144 (the wheel that omitted `web/static`); the "dead defense-in-depth" class wired only at ADR-0241 |
| `session-close` | ADR + handoff rotation + logs + wheel/installers + PR | the twice-repeated silent state-doc drift; the 417 KB handoff (ADR-0246); ADR-0148 (nine installers embedding a 14-hour-old wheel) |
| `steward` | driving, watching and standing down on a PR — the check set, the red-cell diagnosis order, what may be pushed or posted, the squash-merge restart | CI-01/CI-02/CI-03 (ADR-0455/0461: a GitHub-side outage vs a race called a flake three times); a `main` re-run spent on a tree identical to the green head; the squash commit amended to satisfy a hook; nine installers stale behind a late edit (ADR-0148) |

## Relationship to the rest of `.claude/`

- **`.claude/agents/qc-checker.md`** runs the gate *autonomously* on a throttle and fixes what it
  finds. `full-gate` is the same knowledge for the session's own lead, who also commits and reports.
- **`.claude/hooks/session_start.sh`** injects the live handoff STATUS every session. `session-close`
  is what produces the section that hook will inject next time — and the rotation shape it enforces is
  the one `tests/test_state_docs.py` actually checks.

## Adding or editing a skill

Keep the `description` field concrete about **when to trigger** — that string is the only thing a
session sees before deciding to load the skill. State the repo's real paths, real commands, and the
ADR/lessons reference for each rule, so a future session can verify a claim instead of trusting it.
Per ADR-0240: anything parity-, engine-, testimony- or CUI-relevant is re-validated by the lead before
it lands.
