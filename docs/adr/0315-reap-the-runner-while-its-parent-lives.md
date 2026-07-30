# 0315 — Reap the runner while its parent lives: the three-tier Ollama exit (OR-04)

Date: 2026-07-30
Status: accepted (amends ADR-0122 — its engaged-path "fully stop Ollama on close" choice stands
unchanged; this ADR fixes HOW that path reaches the memory holder, adds a softer tier below it,
and adds recovery for exits that never ran)

## Context

Operator report (2026-07-30, `docs/STATE/OPERATOR-REQUESTS.md` OR-04): after open→use→close of
the deployed Windows tool, `llama-server.exe` (Ollama's model runner) stays alive holding
~10.9/12 GB dedicated VRAM and ~30 GB committed shared GPU memory. In the operator's own
reproduction (enable Ollama in AI Settings → ask → wipe → quit), both of the tool's cleanup
commands — `taskkill /F /T /IM "ollama app.exe"` and `taskkill /F /T /IM "ollama.exe"` — reported
**"process not found"** while the runner survived.

An operator-gated, report-only adversarial audit
(`audit/VERIFICATION-REPORT-ollama-lifecycle.md`, run against `d508250`, committed at `cac0991`)
confirmed every code-verifiable hypothesis:

- **F-7 (Critical): the engaged path manufactured the orphan itself.** `shutdown()` ran
  unverified-unload → `Popen.terminate()` (Windows: `TerminateProcess` — children NOT terminated)
  on the parent `ollama serve` → an image sweep that by then could only find dead processes. The
  reparented runner was unreachable: no runner image is in the kill list, and the runner's
  ephemeral-port server sits behind the parent's proxy (F-9) — no code path can address it.
- **F-1..F-4: the cross-session orphan hole.** `_engaged` was in-memory only and set solely by
  the AI-Settings POST, so Ask-the-AI on the DEFAULT config (backend `ollama`) never set it —
  shutdown no-opped entirely; nothing reconciled at startup; a hard kill ran no cleanup at all.
- **F-5/F-6: every failure was invisible.** The unload's return value counted successful POSTs
  (not freed memory), listing failures silently returned 0, and `check=False` discarded the
  taskkill results — total cleanup failure was indistinguishable from success.
- **F-17: orphans compound** per enable→ask→quit cycle (each cycle spawns a fresh serve on the
  again-free port and strands a fresh runner).
- **UNVERIFIED, parked on operator artifacts (audit §8):** the `/api/ps` schema on the installed
  Ollama version (#2); whether a per-request `keep_alive: 0` overrides a server-level
  `OLLAMA_KEEP_ALIVE=-1` — confirmed set at User scope on the operator's machine (#3, the
  severity fork); the runner's unwind timing (#3); the model identity behind the resident blob
  (#4); the on-machine dangling-PPID signature and orphan count (#5).

Operator behavior ruling (2026-07-30, recorded verbatim in OPERATOR-REQUESTS): **free the GPU on
exit** — stop the runtime if the tool started it; if it is an external service the tool merely
used, unload the model (`keep_alive: 0`); **never kill a process the tool didn't start**.

## Decision

`OllamaLauncher.shutdown()` becomes a **three-tier** exit decided by what the session provably
did, with a durable marker and startup reconciliation behind it:

| Tier | Condition | Action |
|---|---|---|
| (a)/(b) engaged | `ensure_running()` ran (Settings) | unload ALL loaded models, then **verify** via a bounded `/api/ps` re-probe (~3 s; `status="unload-incomplete"` + WARNING if it doesn't drain); **tree-kill the serve WE spawned by pid while our un-reaped handle still pins it** (`taskkill /F /T /PID` on Windows, `killpg` on POSIX — the spawn already creates its own session/group; the POSIX branch refuses a target sharing THIS process's group); then the ADR-0122 image sweep for adopted servers (tray first), with returncodes read — 0/1/128 is "done / nothing to stop", anything else logs at WARNING |
| (c) used, never engaged | `record_use()` fired, `_engaged` False | unload ONLY the models this session generated with (tolerant base-name match, per recorded endpoint), verify, and **touch no process** |
| (d) never used | neither | total no-op — a bystander Ollama is never disturbed |

Supporting mechanisms:

- **`record_use(model, endpoint)`** marks real use on **generate success only**, via a
  `_UseMarking` wrapper applied to routed Ollama backends in `_active_backend`/`_second_backend`
  (`web/app.py`). Probes, model lists, and the settings render construct backends but load
  nothing into VRAM — they never mark (pinned by test). `create_app` wires the hook with a
  `getattr` guard, so managers/fakes without `record_use` work unchanged.
- **Durable engagement marker** — `ollama-engagement.json` under `$SF_CACHE_DIR` else
  `~/.cache/schedule-forensics` (the same resolution `engine/cache.py` uses; duplicated because
  `ai/` must not import `engine/`). Endpoint + model names + timestamp only — never schedule
  content; outside the repo and the CUI boundary. Written on engagement/first use, cleared only
  on a **verified-clean** exit (an unclean exit leaves it for the backstops).
- **`reconcile_at_startup()`** — spawned off-thread by the launcher on every start, TCP-gated
  (1.5 s probe), all HTTP bounded: with a marker and a listening endpoint it unloads the
  marker-named models (all, if the marker predates any use) and verifies; with a marker and a
  dead endpoint it surfaces `orphan-suspected` — the orphaned runner sits behind a dead proxy no
  code path can reach, so the tool *says so* instead of pretending; with no marker it touches
  nothing (the marker is the proof of ownership).
- **Visibility (F-5/F-6/F-16):** unload listing/per-model failures log at WARNING;
  `_default_stop_server` reads and reports returncodes; `manager.status` — previously write-only
  — now renders in AI Settings diagnostics, alongside the four `OLLAMA_*` environment values the
  spawned server would inherit (`OLLAMA_KEEP_ALIVE` / `OLLAMA_CONTEXT_LENGTH` /
  `OLLAMA_MAX_LOADED_MODELS` / `OLLAMA_NUM_PARALLEL`) — **reported, never overridden**.
- **`keep_alive: "5m"` on every generate** (`ai/ollama.py`) — equals Ollama's stock default (no
  added latency between asks) and bounds post-hard-kill residency *if* a per-request value
  overrides a server-level `-1`. That override is **UNVERIFIED** (F-13) — this is a hardening
  layer and is never relied on as the cleanup mechanism.

## Rejected alternatives

- **Image-name kill of the runner** (`llama-server.exe` / `ollama_llama_server.exe`): runner
  binary names vary across Ollama versions (the installed version's name is UNVERIFIED), and
  `llama-server` is llama.cpp's generic server binary — exactly what the tool's own supported
  OpenAI-compat backend (LM Studio / llamafile) runs, so a name sweep can kill a server the tool
  doesn't own. The pid-rooted tree-kill reaches the runner by ancestry without knowing its name.
  A test pins the exclusion so a future "helpful" addition trips it.
- **Unconditional startup auto-unload:** evicts models the operator's own work loaded, without
  proof of ownership. The durable marker *is* that proof.
- **Relying on per-request `keep_alive: 0`:** its override behavior against `OLLAMA_KEEP_ALIVE=-1`
  is unverified (F-13); on the spawned path the tree-kill reaps the runner regardless, and on the
  adopted path a failed unload is now visible instead of silently counted as success.
- **A durable marker inside the repo:** wrong lifetime, wrong boundary (CUI posture).
- **Windows Job objects:** correct-by-construction child reaping, but a larger platform-specific
  change than the defect requires; reconsider only if a park artifact shows the tree-kill missing.

## Consequences

- The operator's reproduced scenario now ends with the runner reaped (spawned path) or the used
  models unloaded (external path), and a session that dies hard leaves a marker the next launch
  acts on. Cleanup failures are visible in the log and on the settings page.
- Shutdown gains a bounded ≤~3 s verification window when the AI was engaged/used.
- The in-app teardown sites (settings save away from Ollama, `POST /settings/ai-off`, session
  wipe) inherit the new tiers automatically — a default-config user who hits "Turn AI off" now
  gets their model unloaded, which is those controls' stated intent.
- Residuals, stated: a Task-Manager hard kill still bypasses the in-process exits (answered by
  the marker + reconciliation at next launch, and — pending F-13 — the `keep_alive` bound);
  another local app sharing the exact model we unload pays one reload; the engaged path unloads
  at the manager's construction endpoint (pre-existing quirk, unchanged).
- Operator verification: the four-scenario smoke script in the PR body (A: the bug path — ask
  without Settings, quit → `ollama ps` empty, runner gone, Ollama itself still running; B:
  ADR-0122 intact — enable in Settings, ask, quit → Ollama fully stopped; C: never used — quit
  changes nothing; D: hard-kill backstop). Park artifacts #1/#3/#5 (+#4) remain open in the
  audit's §8 and refine, not gate, this fix.
