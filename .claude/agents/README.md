# Project agents

Custom Claude Code subagents for this repo. Each `*.md` file is a subagent definition
(YAML frontmatter — `name`, `description`, `tools`, `model` — plus the system prompt).
They are available to the `Agent` tool in any session once this file is on disk.

## `qc-checker` — periodic quality control

Runs the full gate (ruff · ruff format · mypy · bandit · pytest · `node --check` · the
doc/drift guards), **triages every failure to confirm it's a real error** (not an
environment-gated skip such as a missing CUI `.mpp`/no-Java/no-Ollama, nor a flake), fixes
the genuine ones with minimal in-scope edits, re-verifies the gate is green, and reports.
It is read-and-fix only: it never commits, pushes, opens PRs, or touches CUI files.

### Run it on demand
Ask Claude: "run the qc-checker agent" (or invoke the `Agent` tool with
`subagent_type: qc-checker`).

### Run it every 3 hours while a session is active
Use the `loop` skill — it re-runs a prompt on a fixed interval for the life of the session:

```
/loop 3h Use the qc-checker agent to run a full QC sweep: run the gate, verify any
failures are real errors, fix the real ones, re-verify, and report. If clean, say so briefly.
```

The loop runs **only while the session is active** (matching the requirement). It does not
survive the session ending or the remote container being reclaimed, so re-issue the `/loop`
command at the start of a new session if you want the cadence to continue there. The agent
definition itself is committed, so it's always available to start the loop from.

### Auto-trigger at session start (throttled to ~every 3 hours)

`.claude/hooks/qc_session_start.sh` is a SessionStart hook that injects a "run the QC sweep"
directive — but only when **≥ 3 hours** have elapsed since the last run (timestamp kept in
`.git/qc-checker-last-run`, per-clone and never committed), so a burst of session resumes
won't trigger sweeps more often than the interval. Override the interval with the
`QC_INTERVAL_SECONDS` environment variable.

The script is committed, but **registering it must be done by a human** — the assistant is
deliberately barred from editing its own startup/hook config. Add the second command to both
`SessionStart` matchers in `.claude/settings.json`:

```json
"SessionStart": [
  { "matcher": "startup", "hooks": [
    { "type": "command", "command": "bash .claude/hooks/session_start.sh" },
    { "type": "command", "command": "bash .claude/hooks/qc_session_start.sh" }
  ] },
  { "matcher": "resume", "hooks": [
    { "type": "command", "command": "bash .claude/hooks/session_start.sh" },
    { "type": "command", "command": "bash .claude/hooks/qc_session_start.sh" }
  ] }
]
```

Once registered, every new/resumed session checks the throttle and, when due, asks the
assistant to run the `qc-checker` sweep before going idle.
