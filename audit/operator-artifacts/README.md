# Operator artifacts — the OR-04 park list, turnkey

This folder is the **deposit location** the Ollama-lifecycle audit names in
`audit/VERIFICATION-REPORT-ollama-lifecycle.md` §8: the operator-run probes whose outputs
unlock the parked findings (F-12 · F-13 · F-15 · F-16 · F-17 · F-18). Nothing here gates the
shipped ADR-0315 fix — these **refine** it. The outputs contain **no schedule content** (paths,
process lists, Ollama server JSON, model manifests only) and are safe to commit; review each
file before committing anyway, then add them via the GitHub web UI or paste them into a session.

## One-command collection

On the **deployed Windows box**, right after asking the AI one question (so a model is loaded),
open PowerShell **in this folder** and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\collect-ollama-artifacts.ps1
```

The script is **read-only and loopback-only**: it never starts, stops, installs, or kills
anything; it deliberately never runs `ollama list` or `ollama run` (either would respawn the
server, poisoning probes #2/#3/#5 — the audit's explicit DON'T). It writes every output into
this folder:

| File | §8 item | Unlocks |
|---|---|---|
| `00-collection-log.txt` | — | the run transcript (what ran, what failed) |
| `01-where-ollama.txt` | #1 | F-16 branch (a)/(b) — can SMAT manage `C:\Tool\Ollama` at all |
| `02-api-ps.json` | #2 | F-12 — the real `/api/ps` schema for the installed version |
| `03-keepalive-override.txt` | #3 | F-13/F-15 — does per-request `keep_alive:0` override `OLLAMA_KEEP_ALIVE=-1`, and how fast the runner exits |
| `04-manifest/` | #4 | F-18 — model identity / quantization / fits-in-11.5-GB verdict |
| `05-runner-ppid.txt` | #5 | F-7 dangling-PPID signature + F-17 accumulation count |

For **F-17 accumulation proof**, run the collector once after a fresh enable→ask→quit cycle,
rename `05-runner-ppid.txt` to `05-runner-ppid-cycle1.txt`, do a second cycle, and run it again.
The optional §8 item #6 (the same #3 probe against an **embedding** model) is manual — re-run
the script right after an embedding call if you want F-14 too.

## The four-scenario smoke (ADR-0315 acceptance on the deployed build — from #490)

First note the deployed version on the settings page (must be **≥ 1.0.133**; current is 1.0.144).

- **A — the bug path:** open the tool → load a schedule → Ask-the-AI one question **without ever
  opening AI Settings** → wait for the answer → in-page Quit. Within ~10 s: `ollama ps` shows
  **no models**, Task Manager shows your `ollama.exe`/tray **still running**, `llama-server.exe`
  **gone**, dedicated GPU memory back to idle.
- **B — ADR-0122 intact:** open → AI Settings → backend Ollama → Save → ask → Quit. `ollama ps`
  refuses connection; `ollama.exe` and `ollama app.exe` both gone.
- **C — never used:** open → load → never ask → Quit. `ollama ps` unchanged, same PIDs as before
  launch.
- **D — hard-kill backstop:** ask once, then End-task `pythonw.exe` in Task Manager → at next
  tool launch the startup reconciliation reclaims (or names) the leftovers; independently,
  `ollama ps` should drain within ~5 min if the per-request keep_alive overrides your
  `OLLAMA_KEEP_ALIVE=-1` (that override is exactly probe #3 above).

Deposit the four verdicts (pass/fail + anything surprising) as `smoke-results.md` here.
