# Recommended `.claude/settings.json` (curated allowlist + SessionStart hook)

This is the M1 Claude Code project configuration called for by `SETUP-DIRECTION.md` §2-§3.
It is documented here (not written as the live file) because creating
`.claude/settings.json` **widens the agent's own permission rules**, which the Claude Code
safety classifier reserves for an explicit **user** decision (see ADR-0006).

**To activate:** create `.claude/settings.json` with the content below (the user, or the agent
once you approve it). The companion script `.claude/hooks/session_start.sh` and the git guard
`.githooks/pre-commit` are already in the repo and working; this file only *registers* the
SessionStart hook and grants the curated, non-destructive tool allowlist.

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git branch:*)",
      "Bash(git checkout:*)",
      "Bash(git switch:*)",
      "Bash(git merge:*)",
      "Bash(git push:*)",
      "Bash(git fetch:*)",
      "Bash(git pull:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git show:*)",
      "Bash(git restore:*)",
      "Bash(git stash:*)",
      "Bash(git config:*)",
      "Bash(git ls-files:*)",
      "Bash(git rev-parse:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(python -m pytest:*)",
      "Bash(pytest:*)",
      "Bash(coverage:*)",
      "Bash(pip:*)",
      "Bash(pip install:*)",
      "Bash(python -m pip:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(bandit:*)",
      "Bash(pip-audit:*)",
      "Bash(ollama list)",
      "Bash(ollama ps)",
      "Bash(ollama show:*)",
      "Bash(ollama pull:*)",
      "Bash(ollama run:*)",
      "Bash(java:*)",
      "Bash(javac:*)",
      "Bash(node:*)",
      "Bash(npm:*)",
      "Bash(npx:*)"
    ],
    "deny": [
      "Bash(git push --force:*)",
      "Bash(git push -f:*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/session_start.sh" }
        ]
      },
      {
        "matcher": "resume",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/session_start.sh" }
        ]
      }
    ]
  }
}
```

## Notes
- The allowlist is intentionally **curated** (the §7 "avoid skip-all-permissions" rule):
  destructive operations (`rm -rf`, force-push) are not allowed and still prompt; force-push is
  explicitly denied.
- `ollama list/ps/show/pull/run` are scoped (no arbitrary `ollama` subcommands).
- The SessionStart hook is fail-soft (verification only; always exits 0) and re-activates the
  CUI git pre-commit guard each session.
- If the live tool invokes the toolchain via `.venv/bin/<tool>` rather than the bare name, add
  the corresponding `Bash(.venv/bin/<tool>:*)` entries, or activate the venv so the bare names
  match.
