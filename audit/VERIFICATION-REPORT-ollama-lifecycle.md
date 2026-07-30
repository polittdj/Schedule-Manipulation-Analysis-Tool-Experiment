# VERIFICATION REPORT — Ollama VRAM orphan / lifecycle reconciliation audit

**REPORT-ONLY.** Nothing in this pass was committed, pushed, or applied. The proposed diff, tests,
and ADR below are deliverables for a human-gated apply. This report fixes nothing on the operator's
laptop — the resident VRAM there is machine state, cleared by the operator's separate PowerShell
steps. The two are not conflated anywhere below.

## 1. Roles assumed

Application-lifecycle engineer · adversarial verification engineer · Windows process/GPU-runtime
reviewer · software QA/QC engineer · CM auditor. No additional role was required.

## 2. Commit audited and evidence commands

**Commit:** `d508250b3c82ea6af9abc3c8abe3f957535d0b1b` (`origin/main` tip == local HEAD at audit
time; working tree clean, verified `git status --porcelain | wc -l` → 0 before this file was
created).

Every claim below traces to output produced **in this session** by these commands (ripgrep via the
harness Grep tool; file reads via the Read tool). The repo's own tests, docstrings, HANDOFF, and
ADRs were treated as claims, not evidence.

```
git fetch origin && git rev-parse origin/main HEAD          # tip identity
Read src/schedule_forensics/ai/ollama_process.py            # full file (1–299)
Read src/schedule_forensics/launcher.py:80-111
Read src/schedule_forensics/ai/backend.py                   # full file
Read src/schedule_forensics/ai/ollama.py                    # full file
Read src/schedule_forensics/web/app.py:676-846, 2130-2190, 6940-7025
Read tests/ai/test_ollama_process.py, tests/ai/test_coverage_ollama_process.py (full)
rg -n 'OLLAMA_KEEP_ALIVE|OLLAMA_CONTEXT_LENGTH|OLLAMA_MAX_LOADED_MODELS|OLLAMA_NUM_PARALLEL|OLLAMA_HOST|OLLAMA_MODEL'  (all *.py,*.ps1,*.sh,*.command)
rg -n 'ensure_running|unload_loaded_models|_loaded_models|api/ps'  src/
rg -n 'signal\.signal|atexit'  src/
rg -n 'SF_CACHE_DIR|\.cache/schedule'  src/
rg -in 'nvidia|gpu|smi|vram'  src/schedule_forensics/web/system.py
rg -n 'no-binary|manager\.status|ollama\.status|app\.state\.ollama'  src/
rg -n 'open\(|json\.dump|pickle|\.write|Path\('  src/schedule_forensics/ai/ollama_process.py
rg -in 'llama[-_]server'  (repo-wide)
```

This container has **no Ollama, no Windows, no GPU** (session preflight: `ollama not installed`).
Everything that requires the operator's machine is marked UNVERIFIED and parked in §8 with the
exact artifact that unlocks it. No Ollama API field, env var, endpoint, or binary name was
invented; where the schema could not be probed it is marked UNVERIFIED per instruction.

## 3. Findings

| ID | Severity | Verdict | File:line | Finding + evidence |
|----|----------|---------|-----------|--------------------|
| F-1 | High | CONFIRMED | `ai/ollama_process.py:228,240` | `_engaged` is a plain per-instance attribute (`self._engaged = False` in `__init__`; only assignment to True at :240 inside `ensure_running()`). Zero persistence primitives in the module — the only `open(` hits are urllib opener calls (:99,:129,:182,:187); no file write, no pickle, no Path. |
| F-2 | High | CONFIRMED | `web/app.py:6967`; `launcher.py:98-101` | No startup reconciliation exists. `ensure_running()` has exactly one production call site (the AI-Settings POST, daemon thread). `unload_loaded_models` / `_loaded_models` / `/api/ps` are referenced nowhere outside `ai/ollama_process.py` (repo grep). The launcher comment is explicit: "Do NOT start Ollama here… only register the stop side now." Nothing probes `/api/ps` at boot. |
| F-3 | High | CONFIRMED* | `src/` (absence); `launcher.py:101,107-109` | Cleanup exists only as `atexit` + the `finally` around `serve_fn`. Zero `signal.signal` anywhere in `src/` (grep). *The OS half — `TerminateProcess`/`taskkill /F`/bugcheck/forced reboot run no Python `atexit` handlers — is standard documented CPython/Windows behavior, not live-probeable in this Linux container; the **code** evidence is that no mitigation for it exists in the repo. A hard kill of SMAT therefore strands a loaded model with zero cleanup. |
| F-4 | High | CONFIRMED | `ai/ollama_process.py:276-277` | `shutdown()` opens `if not self._engaged: return`. With F-1 (no persistence) + F-2 (no reconciliation), a subsequent session that does not enable AI never touches a stranded model. **Task 1 hypothesis overall: CONFIRMED — the cross-session orphan hole is real.** |
| F-5 | High | CONFIRMED | `ai/ollama_process.py:175-178,180-192` | The unload can report success while freeing nothing, and its count is not evidence. `unloaded += 1` counts **successful HTTP POSTs** (:189), not verified unloads — a 200 whose `keep_alive:0` is ineffective (F-13) still counts. `_loaded_models` failure hits a bare `except Exception: return 0` (:175-178) — **completely silent, no log at any level**. Per-model failure logs at `debug` only (:190-191). Return-0-while-resident paths enumerated: endpoint dead (F-9); `/api/ps` schema mismatch (F-12); listing exception; per-model timeout (4.0 s default) against a busy runner. |
| F-6 | High | CONFIRMED | `ai/ollama_process.py:153-167` | Cleanup failure is invisible. `_default_stop_server` runs `subprocess.run(..., check=False)` and **discards the CompletedProcess** — taskkill's "process not found" (the operator's captured output; nonzero exit) produces no log at any level; exceptions log at `debug`. Combined with F-5, total cleanup failure is indistinguishable from success in every log and every code path. The tool believes it cleaned up. |
| **F-7** | **Critical** | **CONFIRMED (code)** | `ai/ollama_process.py:278-296,110-117,86-107,147-150` | **`shutdown()` orphans the model runner by killing its parent first — the root cause the operator hypothesized, proven in the code.** Order at :278-296: (1) unload → (2) `_terminate(proc)` → (3) `_stop_server()`. `_terminate` calls `Popen.terminate()`, which on Windows is `TerminateProcess` on **that one process** — children are not terminated, and the spawn (:86-107) creates no Job object tying the runner's lifetime to the parent (only `CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP`). Step 3 then tree-kills by **image name** — `ollama app.exe`, `ollama.exe` (:147-150) — but by then our `ollama.exe` is already dead (step 2) and no tray exists on this configuration, so both report "process not found" (exactly the operator's captured output) while the reparented runner survives. No runner image is in the list (repo-wide grep: **zero** `llama-server`/`llama_server` hits). The tool manufactures the orphan inside its own cleanup, then runs a cleanup that cannot reach it. The on-machine dangling-PPID signature is parked (§8-5) — the code-side proof does not depend on it. |
| F-8 | High | CONFIRMED | `ai/ollama_process.py:279-287` | No post-unload verification: between the unload (:279) and `_terminate` (:287) there is no `/api/ps` re-probe, no wait, no readback. Even a fully successful unload is given zero time before its proxy is killed. |
| F-9 | High | CONFIRMED | `ai/ollama_process.py:170,126-132` | Once the parent dies, the unload path reaches nothing. `unload_loaded_models` talks only to the configured endpoint (default `127.0.0.1:11434`); the runner listens on its own ephemeral port (operator-captured cmdline: `--port 61165`) behind the parent's proxy, and **no code path can address a runner directly** (grep: no other endpoint construction exists). Post-orphan, the POST gets connection-refused → F-5's silent `return 0`. The orphan is permanently unreclaimable by the tool as shipped. |
| F-10 | Medium (Critical if F-13 fails) | CONFIRMED | `ai/ollama_process.py:88`; repo grep | The tool neither reads nor reports the environment that governs residency: **zero** references to `OLLAMA_KEEP_ALIVE`, `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL` anywhere in `.py/.ps1/.sh/.command`. The spawn env is `{**os.environ, "OLLAMA_HOST": host_port}` — the child inherits the operator's full user scope, including the confirmed `OLLAMA_KEEP_ALIVE=-1`, invisibly. |
| F-11 | Low (opportunity) | CONFIRMED | `web/system.py:280-348,351+,276` | A dependency-free GPU/VRAM reader already exists: `_probe_gpu` runs `nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu` (PATH + known Windows locations, :303-315), with a vendor-neutral WDDM perf-counter fallback, background-refreshed into `_slow_cache`. AI Settings could show total VRAM used/total today with zero new dependencies. Per-process attribution ("N GB held by Ollama") would add `--query-compute-apps=pid,process_name,used_memory` on the **same local binary** — fixed argv, no network client, egress-guard-clean. `matplotlib`/`pandas`/`parquet` are not needed and not proposed. |
| F-12 | — | **UNVERIFIED** | `ai/ollama_process.py:131-132` | `/api/ps` response schema on the operator's Ollama version. Code fact (confirmed): `_loaded_models` keeps only entries carrying key `"name"` and silently yields `[]` otherwise. No Ollama in this container and no vendored Ollama API docs in the repo → the actual field name is not asserted. Parked (§8-2). |
| F-13 | — (severity fork) | **UNVERIFIED** | `ai/ollama_process.py:182` | Whether per-request `keep_alive: 0` overrides server-level `OLLAMA_KEEP_ALIVE=-1`. Not asserted in either direction (no live probe possible here; no vendored docs). **If it does not override, the tool's entire unload strategy is inoperative on this machine and F-5/F-8 escalate to Critical.** Parked (§8-3). The proposed fix is deliberately structured so it does not depend on this answer. |
| F-14 | — | **UNVERIFIED** | `ai/ollama_process.py:180-188` | Whether a `keep_alive:0` POST to `/api/generate` unloads an **embedding** model. Code fact: the unload loop POSTs `/api/generate` for every `/api/ps` entry regardless of model kind. Parked (§8-6). |
| F-15 | — | **UNVERIFIED** | `ai/ollama_process.py:279-287` | Whether the runner process exits synchronously with a successful unload, or needs unwind time. Code fact: shutdown gives it zero time either way (F-8). Parked (§8-3, same probe). |
| F-16 | Medium | CONFIRMED (code) / **UNVERIFIED (branch)** | `ai/ollama_process.py:40-51,54-62,246-247`; `web/app.py:6967,722-776` | `_candidate_paths()` covers only `%LOCALAPPDATA%\Programs\Ollama`, `%ProgramFiles%\Ollama`, `%ProgramFiles(x86)%\Ollama`, and three POSIX paths — **`C:\Tool\Ollama` is in none of them**, so resolution relies solely on `shutil.which("ollama")` (PATH). Which branch holds — (a) on PATH / (b) not — is machine state: parked (§8-1). Consistency note (not proof): the 4C reproduction implies an `ollama.exe` existed and died before the taskkills ran, which is consistent with branch (a). **The silent-downgrade half is CONFIRMED regardless:** `ensure_running()` runs on a daemon thread with its return value discarded (app.py:6967); `self.status` (:229/:247) has **zero readers** in `src/` (grep); "no-binary" reaches only `logger.info`. Partial mitigation exists — `_ai_status_note` (app.py:722-776) tells the operator the *server* is unreachable — but nothing ever says "the tool tried to start Ollama and could not find the executable." No existing install-path override setting exists (verified: `find_ollama_executable` takes only a `which` injectable; no env var, no settings field). |
| F-17 | Critical (multiplier) | CONFIRMED (mechanism) / UNVERIFIED (magnitude) | `ai/ollama_process.py:241,255-256` | Orphans compound. After F-7 orphans a runner and its parent dies, `127.0.0.1:11434` is free again, so the next engage's prober finds nothing listening and spawns a **new** `ollama serve`; its first ask spawns a **new** runner; quit orphans it again. Nothing in the code prevents N orphaned runners coexisting on distinct ephemeral ports. The operator's observations (shared GPU commit ~16.6 → ~30.6 GB; runner working set ~19.4% → ~32% of 128 GB) are consistent with ≥2 concurrent stranded allocations; the instance-count proof is parked (§8-5). A per-cycle compounding leak, not a plateau. |
| F-18 | — | **UNVERIFIED** | operator machine | Identity of the model behind blob `sha256-4824460d29f2…`. The manifests live under `C:\Tool\Ollama\models\manifests\` on the operator's machine; not present in this repo; not guessed, per instruction (and `ollama list` must not be run there — it would respawn the server and destroy the process state). Parked (§8-4). Once identified: if its weights exceed ~11.5 GB VRAM, weight-straddling into system RAM under `--no-mmap` is a **configuration** finding, separate from the orphan defect — no lifecycle fix changes it. |

**Overall verdict on the operator's hypotheses:** Task 1 CONFIRMED (all four links). Task 4C's
root cause CONFIRMED in code — the kill ordering is exactly as hypothesized, plus F-6 explains why
its failure was invisible. Task 4E's environmental findings are consistent with the code evidence
(F-9, F-10); the context-length theory stays dead and was not pursued. Nothing in the operator's
prompt was refuted; one nuance: the "ollama app.exe → not found" output also shows the winget
tray auto-start is **not** active on this machine, so the tray-respawn defense (:140-145's
rationale) is dormant on this configuration — the docstring's confidence about tray behavior is a
claim about a process that wasn't there.

**Prior in-session design revision (CM note):** this audit supersedes parts of the PR-1 design
drafted earlier today. Kept: the used-but-never-engaged unload tier (`record_use`), never killing
a process the tool didn't start, and the refusal to image-kill `llama-server.exe` (it is llama.cpp's
generic server name — the tool's own supported OpenAI-compat backend runs under it). Changed: the
teardown order (the earlier design retained the broken unload→terminate→sweep order and would NOT
have fixed F-7). Added: verified unload, startup reconciliation, durable marker, env surfacing.
Demoted: `keep_alive:"5m"` on generate from load-bearing to hardening-pending-F-13.

## 4. Proposed diff (UNAPPLIED — human gates the apply)

Scope: minimal root-cause change per Task 5. Line anchors are HEAD anchors; offsets may shift at
apply time. Ordering of the fix: **verify-unload while the proxy lives → PID-rooted tree-kill of
the serve WE spawned while our handle still pins the PID → image sweep for the ADR-0122 adopted
case, with results made visible.** No runner image name is hardcoded anywhere (version-tolerant by
construction: ancestry, not names).

```diff
--- a/src/schedule_forensics/ai/ollama_process.py
+++ b/src/schedule_forensics/ai/ollama_process.py
@@
 import json
 import logging
 import os
 import shutil
+import signal
 import socket
 import subprocess  # nosec B404 — used only to spawn/stop a fixed, local `ollama serve` (no shell)
 import sys
 import threading
 import time
 import urllib.request
 from collections.abc import Callable
 from urllib.parse import urlparse
@@
 Finder = Callable[[], "str | None"]
 Prober = Callable[[str], bool]
 Spawn = Callable[[str, str], "subprocess.Popen[bytes]"]
 Unloader = Callable[[str], int]
 Stopper = Callable[[], None]
+TreeKiller = Callable[[int], None]
+PsReader = Callable[[str, float], "list[str]"]
@@ def _terminate(...)
+
+def _kill_tree(pid: int) -> None:
+    """Force-stop the process TREE rooted at ``pid`` — used only on the ``ollama serve`` WE
+    spawned, and only while our un-reaped Popen handle still pins the PID (Windows: the open
+    handle prevents PID recycling; POSIX: the un-waited child is a zombie holding its PID), so
+    it can never reach a recycled PID or a process the tool did not start. This reaps the
+    model-runner child by ANCESTRY, not by image name — runner binary names vary across Ollama
+    versions, and a name sweep could hit an unrelated llama.cpp server (the tool's own supported
+    OpenAI-compat backend runs one). Failure is LOGGED VISIBLY — a cleanup that fails silently
+    is indistinguishable from one that worked (this module's original defect)."""
+    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
+        res = subprocess.run(  # nosec B603 B607 — fixed OS utility, no shell, our own child pid
+            ["taskkill", "/F", "/T", "/PID", str(pid)],
+            capture_output=True, text=True, timeout=10, check=False,
+            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
+        )
+        if res.returncode != 0:
+            logger.warning("tree-kill of spawned ollama (pid %d) reported: %s",
+                           pid, (res.stderr or res.stdout or "").strip())
+    else:
+        try:
+            pgid = os.getpgid(pid)  # spawn used start_new_session=True -> group == our child
+            os.killpg(pgid, signal.SIGTERM)
+            time.sleep(0.5)
+            with contextlib_suppress(ProcessLookupError):
+                os.killpg(pgid, signal.SIGKILL)
+        except ProcessLookupError:
+            pass  # already gone — that is success, not failure
+        except Exception as exc:
+            logger.warning("tree-kill of spawned ollama (pid %d) failed: %s", pid, exc)
```
*(apply-time detail: use `contextlib.suppress` via a module import, not the placeholder name
above; shown compressed here for review.)*

```diff
@@ def _default_stop_server() -> None:
-    for cmd in cmds:
-        try:
-            subprocess.run(  # nosec B603 B607
-                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
-                stdin=subprocess.DEVNULL, timeout=10, check=False,
-                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
-            )
-        except Exception as exc:
-            logger.debug("could not stop Ollama process(es) via %s: %s", cmd[0], exc)
+    for cmd in cmds:
+        try:
+            res = subprocess.run(  # nosec B603 B607
+                cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL,
+                timeout=10, check=False,
+                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
+            )
+            # taskkill: 0 = killed, 128 = no such process (fine — nothing to stop). Anything
+            # else is a REAL failure and must be visible (F-6: silence looked like success).
+            if res.returncode not in (0, 128):
+                logger.warning("stop-Ollama %s exited %d: %s", cmd[-1], res.returncode,
+                               (res.stderr or res.stdout or "").strip())
+            else:
+                logger.info("stop-Ollama %s: %s", cmd[-1],
+                            "done" if res.returncode == 0 else "no such process")
+        except Exception as exc:
+            logger.warning("could not stop Ollama process(es) via %s: %s", cmd[0], exc)
```

```diff
@@ def unload_loaded_models(endpoint..., *, timeout: float = 4.0) -> int:
-    try:
-        names = _loaded_models(endpoint, timeout)
-    except Exception:
-        return 0
+    try:
+        names = _loaded_models(endpoint, timeout)
+    except Exception as exc:
+        # Not reaching the server at unload time is a REPORTABLE state, not a silent zero —
+        # post-orphan this is exactly how an unreclaimable runner hides (F-5/F-9).
+        logger.warning("could not list loaded Ollama models at %s: %s", endpoint, exc)
+        return 0
@@
-        except Exception:  # one model failing to unload must not block the rest / the exit
-            logger.debug("could not unload Ollama model %s", name)
+        except Exception as exc:  # one model failing to unload must not block the rest / the exit
+            logger.warning("could not unload Ollama model %s: %s", name, exc)
```

```diff
@@ class OllamaLauncher.__init__
         spawn: Spawn | None = None,
         unloader: Unloader | None = None,
         stopper: Stopper | None = None,
+        tree_killer: TreeKiller | None = None,
+        ps_reader: PsReader | None = None,
+        marker_dir: "str | None" = None,
         start_timeout: float = 20.0,
     ) -> None:
@@
         self._spawn = spawn or _default_spawn
         self._unload = unloader or (lambda ep: unload_loaded_models(ep))
         self._stop_server = stopper or _default_stop_server
+        self._kill_tree = tree_killer or _kill_tree
+        self._ps = ps_reader or _loaded_models
+        # Durable engagement marker (survives a hard kill): $SF_CACHE_DIR else
+        # ~/.cache/schedule-forensics — the SAME resolution engine/cache.py:57-61 uses,
+        # duplicated here because ai/ must not import engine/ (cross-reference comment there).
+        # Deliberately OUTSIDE the repo and the CUI boundary; contents are endpoint + timestamp
+        # only — never schedule content.
+        self._marker = os.path.join(marker_dir or _default_marker_dir(), "ollama-engagement.json")
```

```diff
@@ def ensure_running(self) -> str:
         self._engaged = True  # the tool is now managing Ollama -> shutdown will tidy up
+        self._write_marker()  # durable: a hard-killed session leaves proof for reconciliation
```

```diff
@@ def shutdown(self) -> None:
-        if not self._engaged:
-            return
-        try:
-            freed = self._unload(self.endpoint)
-            if freed:
-                logger.info("freed %d in-memory Ollama model(s) on shutdown", freed)
-        except Exception as exc:
-            logger.warning("could not unload Ollama models on shutdown: %s", exc)
-        with self._lock:
-            proc = self._proc
-            self._proc = None
-        if proc is not None:
-            try:
-                _terminate(proc)
-                logger.info("stopped the local Ollama we started")
-            except Exception as exc:
-                logger.warning("could not stop the Ollama we started: %s", exc)
-        try:
-            self._stop_server()
-        except Exception as exc:
-            logger.warning("could not stop running Ollama server(s): %s", exc)
+        if not self._engaged:
+            return
+        # (1) Unload while the parent/proxy is STILL ALIVE, then VERIFY it took (F-8): the old
+        #     code trusted a POST count that proved nothing (F-5) and then killed the proxy.
+        clean = True
+        try:
+            freed = self._unload(self.endpoint)
+            if freed:
+                logger.info("freed %d in-memory Ollama model(s) on shutdown", freed)
+            for _ in range(6):  # bounded re-probe (~3 s): resident -> not clean, say so
+                try:
+                    if not self._ps(self.endpoint, 1.0):
+                        break
+                except Exception:
+                    break  # endpoint gone == nothing listed to hold
+                time.sleep(0.5)
+            else:
+                clean = False
+                self.status = "unload-incomplete"
+                logger.warning("Ollama still reports loaded models after unload — "
+                               "VRAM may remain held (see AI Settings diagnostics)")
+        except Exception as exc:
+            clean = False
+            logger.warning("could not unload Ollama models on shutdown: %s", exc)
+        # (2) Reap the serve WE spawned as a TREE, while our un-reaped handle still pins its
+        #     pid — this reaches the model-runner child by ancestry (F-7). Only then reap the
+        #     parent handle itself.
+        with self._lock:
+            proc = self._proc
+            self._proc = None
+        if proc is not None:
+            try:
+                if proc.poll() is None:
+                    self._kill_tree(proc.pid)
+                _terminate(proc)  # now mostly a reap; still the graceful path if tree-kill missed
+                logger.info("stopped the local Ollama we started (tree-killed while alive)")
+            except Exception as exc:
+                clean = False
+                logger.warning("could not stop the Ollama we started: %s", exc)
+        # (3) ADR-0122 unchanged for the ENGAGED path: sweep any server still running (tray
+        #     first — it would respawn the server), with results now visible (F-6).
+        try:
+            self._stop_server()
+        except Exception as exc:
+            clean = False
+            logger.warning("could not stop running Ollama server(s): %s", exc)
+        if clean:
+            self._clear_marker()  # verified-clean exit -> nothing for reconciliation to do
```

```diff
@@ new OllamaLauncher members (after shutdown)
+    def _write_marker(self) -> None:
+        """Best-effort durable proof the tool engaged Ollama (endpoint + timestamp only)."""
+        try:
+            os.makedirs(os.path.dirname(self._marker), exist_ok=True)
+            with open(self._marker, "w", encoding="utf-8") as fh:
+                json.dump({"endpoint": self.endpoint, "ts": time.time()}, fh)
+        except Exception as exc:  # marker is a backstop — never break engagement over it
+            logger.debug("could not write Ollama engagement marker: %s", exc)
+
+    def _clear_marker(self) -> None:
+        try:
+            os.remove(self._marker)
+        except FileNotFoundError:
+            pass
+        except Exception as exc:
+            logger.debug("could not clear Ollama engagement marker: %s", exc)
+
+    def reconcile_at_startup(self) -> str:
+        """Reclaim what a PRIOR session provably left behind (F-2/F-4). Runs off-thread from the
+        launcher; never blocks serving. Touches Ollama ONLY when the durable marker proves the
+        tool engaged it (an Ollama the operator runs for their own work is never touched).
+        Returns a status string for diagnostics: ``no-marker`` | ``reclaimed`` |
+        ``nothing-loaded`` | ``unreachable`` | ``unload-incomplete``."""
+        if not os.path.isfile(self._marker):
+            return "no-marker"
+        endpoint = self.endpoint
+        try:
+            with open(self._marker, encoding="utf-8") as fh:
+                endpoint = str(json.load(fh).get("endpoint") or self.endpoint)
+        except Exception:
+            pass  # unreadable marker: still reconcile against our configured endpoint
+        if not endpoint_up(endpoint):
+            # A dirty prior exit with nothing listening: an orphaned RUNNER (if any) has no
+            # reachable proxy and no code path can address it (F-9) — surface, don't pretend.
+            logger.warning("prior session engaged Ollama but nothing listens at %s now; if "
+                           "llama-server-style processes persist from that session they must "
+                           "be ended from the OS (see AI Settings diagnostics)", endpoint)
+            self.status = "orphan-suspected"
+            return "unreachable"
+        freed = unload_loaded_models(endpoint)
+        try:
+            still = self._ps(endpoint, 2.0)
+        except Exception:
+            still = []
+        if still:
+            self.status = "unload-incomplete"
+            logger.warning("startup reconciliation: %d model(s) still resident after unload", len(still))
+            return "unload-incomplete"
+        self._clear_marker()
+        logger.info("startup reconciliation: freed %d model(s) left by a prior session", freed)
+        return "reclaimed" if freed else "nothing-loaded"
+
+
+def _default_marker_dir() -> str:
+    env = os.environ.get("SF_CACHE_DIR")
+    return env if env else os.path.join(os.path.expanduser("~"), ".cache", "schedule-forensics")
```

```diff
--- a/src/schedule_forensics/launcher.py
+++ b/src/schedule_forensics/launcher.py
@@ main(): after atexit.register(manager.shutdown)
         atexit.register(manager.shutdown)
+        # Startup reconciliation (F-2/F-4): a prior session that died hard may have left a
+        # model loaded. Off-thread + TCP-gated inside the method — serving never waits on it.
+        threading.Thread(target=manager.reconcile_at_startup, daemon=True).start()
```

**Deliberately NOT in this diff** (recorded so nobody "helpfully" adds them):
no `llama-server.exe` / `ollama_llama_server.exe` image kills (version-fragile, UNVERIFIED name
for the installed version, and collides with the supported OpenAI-compat backend's server); no
silent override of any `OLLAMA_*` env var (surface-first — the app-side diagnostics hunk below);
no auto-kill of anything without either our own child PID or the durable marker as proof of
ownership.

**App-side surfacing hunk (sketch, same PR at apply time):** AI Settings diagnostics panel adds
(a) `manager.status` line (`no-binary` / `unload-incomplete` / `orphan-suspected` finally reach
the operator — F-16), (b) the four `OLLAMA_*` env values when set (F-10, report-never-override),
and (c) optionally the existing `system.py` GPU line (F-11) as "GPU memory: used/total". Also
`ensure_running`'s discarded status (app.py:6967) gets stored on the manager (already is, via
`self.status`) and rendered by (a).

**Gate confirmation:** report-only — nothing was applied, so **no gate figures are claimed**
(standing rule: no test result in prose unless read from a run this turn). At apply time the full
gate runs in the required order: `python -m ruff check src/ tests/` → `python -m ruff format
--check .` → `python -m mypy src/` (strict) → `bandit -q -r src` (exit code read directly) →
`python -m pytest -q` → `python -m pytest -m parity` → `node --check` on touched web static JS
(none touched by this diff unless the diagnostics hunk adds any).

## 5. Proposed tests (UNAPPLIED)

All hermetic via the injectable seams (`finder`/`prober`/`spawn`/`unloader`/`stopper` + new
`tree_killer`/`ps_reader`/`marker_dir`); no real Ollama, no real subprocess. Each is stated with
its fails-before/passes-after mechanism.

Into `tests/ai/test_ollama_process.py`:

```python
def test_shutdown_reaps_the_tree_while_the_parent_is_alive(tmp_path) -> None:
    """F-7: the runner is reachable only through a live ancestor. The tree-kill must run while
    the spawned serve is still alive — the shipped order terminates the parent first, orphaning
    the runner. FAILS at HEAD (no tree-kill exists); PASSES after."""
    proc = _FakeProc()
    alive_at_kill: list[bool] = []
    launcher = OllamaLauncher(
        prober=_up_after_first_probe(),  # down -> spawn -> up (the "started" path)
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: proc,
        unloader=lambda ep: 0,
        stopper=lambda: None,
        tree_killer=lambda pid: alive_at_kill.append(proc.poll() is None),
        ps_reader=lambda ep, t: [],
        marker_dir=str(tmp_path),
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()
    assert alive_at_kill == [True]  # tree-killed exactly once, while the parent still lived

def test_shutdown_verifies_the_unload_and_reports_failure(tmp_path, caplog) -> None:
    """F-5/F-8: a POST count is not an unload. If /api/ps still lists models after the unload,
    shutdown must say so at WARNING and mark status — never silently claim success. FAILS at
    HEAD (no verification exists); PASSES after."""
    launcher = OllamaLauncher(
        prober=lambda ep: True, unloader=lambda ep: 1, stopper=lambda: None,
        ps_reader=lambda ep, t: ["qwen2.5:7b-instruct"],  # resident forever
        marker_dir=str(tmp_path),
    )
    launcher.ensure_running()
    with caplog.at_level(logging.WARNING):
        launcher.shutdown()
    assert launcher.status == "unload-incomplete"
    assert any("still reports loaded models" in r.message for r in caplog.records)

def test_startup_reconciliation_touches_ollama_only_with_a_marker(tmp_path) -> None:
    """F-2/F-4 + the ownership guardrail: no marker -> an operator's own Ollama is never
    touched; marker + reachable endpoint -> the prior session's models are unloaded and the
    marker clears. FAILS at HEAD (method does not exist)."""
    calls: list[str] = []
    kw = dict(prober=lambda ep: True, unloader=lambda ep: calls.append("unload") or 1,
              stopper=lambda: None, ps_reader=lambda ep, t: [], marker_dir=str(tmp_path))
    assert OllamaLauncher(**kw).reconcile_at_startup() == "no-marker"
    assert calls == []                      # nothing touched without proof of ownership
    engaged = OllamaLauncher(**kw)
    engaged.ensure_running()                # writes the durable marker
    fresh = OllamaLauncher(**kw)            # a NEW session (new instance, _engaged False)
    assert fresh.reconcile_at_startup() == "reclaimed"
    assert calls == ["unload"]
    assert fresh.reconcile_at_startup() == "no-marker"  # marker cleared -> idempotent

def test_marker_survives_a_hard_kill_simulation(tmp_path) -> None:
    """F-1/F-3: engagement must outlive the instance. Engage, then simply DROP the instance
    (a hard kill runs no shutdown); a new instance must still see the marker."""
    kw = dict(prober=lambda ep: True, unloader=lambda ep: 1, stopper=lambda: None,
              ps_reader=lambda ep, t: [], marker_dir=str(tmp_path))
    OllamaLauncher(**kw).ensure_running()   # no shutdown() — the simulated hard kill
    assert OllamaLauncher(**kw).reconcile_at_startup() != "no-marker"
```

Into `tests/ai/test_coverage_ollama_process.py`:

```python
def test_stop_server_failure_is_visible_not_silent(monkeypatch, caplog) -> None:
    """F-6: a real taskkill/pkill failure (returncode not in (0,128)) must produce a WARNING —
    the shipped code discards the result entirely. FAILS at HEAD."""
    monkeypatch.setattr(op.subprocess, "run",
                        lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, "", "access denied"))
    with caplog.at_level(logging.WARNING):
        op._default_stop_server()
    assert any("exited 1" in r.message for r in caplog.records)

def test_unload_listing_failure_is_logged(monkeypatch, caplog) -> None:
    """F-5: the bare `except: return 0` around _loaded_models hid the exact post-orphan state
    (connection refused). FAILS at HEAD (no log record is emitted)."""
    with caplog.at_level(logging.WARNING):
        assert op.unload_loaded_models("http://127.0.0.1:1", timeout=0.2) == 0
    assert any("could not list loaded Ollama models" in r.message for r in caplog.records)
```

Existing tests: `test_shutdown_is_a_no_op_when_ai_was_never_enabled` and
`test_launcher_shutdown_without_engaging_is_a_no_op` stay green as written (row (d) semantics
unchanged this pass). `test_launcher_started_then_shutdown` and
`test_adopts_a_running_ollama_...` gain only the mechanical new-seam kwargs where needed
(`ps_reader=lambda ep, t: []`, `marker_dir=tmp_path`) — assertions untouched, nothing weakened.
The `tests/test_windowless_subprocess.py` AST guard: the new `_kill_tree` Windows branch carries
`creationflags` and no stdin inheritance concern (`capture_output`), and will be run against the
guard at apply time.

## 6. Proposed ADR (next free number: **ADR-0315**)

> # 0315 — Reap the runner while its parent lives: PID-rooted teardown, verified unload, and
> # startup reconciliation for the local Ollama
>
> **Status:** proposed (report-only audit deliverable; human-gated apply). Amends ADR-0122
> (which stands unchanged for WHAT is stopped on an engaged close; this ADR fixes HOW and adds
> recovery for exits that never ran).
>
> **Context.** Operator-reproduced defect (2026-07-30): enable Ollama in AI Settings → ask →
> wipe → quit leaves `llama-server.exe` holding ~10.9/12 GB dedicated VRAM and ~30 GB committed
> shared GPU memory, while both of the tool's own cleanup taskkills report "process not found".
> Audit `audit/VERIFICATION-REPORT-ollama-lifecycle.md` at `d508250` confirmed in code:
> `shutdown()` unloads (unverified), then `TerminateProcess`es the parent `ollama serve`, then
> image-sweeps `ollama app.exe`/`ollama.exe` — by which time the parent is already dead, the
> `/T` tree-walk has no ancestor, and the reparented model runner survives unreachable (its
> ephemeral-port server is proxied by the dead parent; no code path addresses a runner
> directly). Cleanup failures were invisible (`check=False` result discarded; listing failures
> silently `return 0`). Engagement was in-memory only, so a hard-killed session stranded a
> model no later session could reclaim. Orphans compound per enable→ask→quit cycle.
>
> **Decision.**
> 1. Teardown order becomes: verified unload (bounded `/api/ps` re-probe, `WARNING` +
>    `status="unload-incomplete"` when models remain) → **PID-rooted tree-kill of the serve WE
>    spawned, while our un-reaped handle still pins its PID** (`taskkill /F /T /PID` on
>    Windows; `killpg` on POSIX — spawn already creates the group) → the ADR-0122 image sweep
>    for adopted servers, with returncodes captured and non-(0|128) results logged at WARNING.
> 2. A durable engagement marker (`$SF_CACHE_DIR` else `~/.cache/schedule-forensics` /
>    `ollama-engagement.json`; endpoint + timestamp only — no schedule content, outside the
>    repo and the CUI boundary) is written on engagement and cleared only on a verified-clean
>    shutdown.
> 3. `reconcile_at_startup()` (launcher, off-thread, TCP-gated): with a marker and a listening
>    endpoint, unload + verify + clear; with a marker and a dead endpoint, surface
>    `orphan-suspected` — never pretend; with no marker, touch nothing.
> 4. Silent failures end: unload listing/per-model failures log at WARNING; `manager.status`
>    is rendered in AI Settings diagnostics, alongside the `OLLAMA_KEEP_ALIVE` /
>    `OLLAMA_CONTEXT_LENGTH` / `OLLAMA_MAX_LOADED_MODELS` / `OLLAMA_NUM_PARALLEL` values when
>    set (surfaced, never overridden) and (optional) the existing dependency-free
>    `system.py` GPU memory readout.
>
> **Rejected alternatives.** Image-name kill of `llama-server.exe`/`ollama_llama_server.exe`
> (runner names vary across Ollama versions — UNVERIFIED for the installed one — and llama.cpp's
> generic server name is exactly what the tool's supported OpenAI-compat backend runs; a name
> sweep can kill a server the tool doesn't own). Unconditional startup auto-unload (touches an
> operator's own models without proof of ownership — the marker is that proof). Relying on
> per-request `keep_alive:0` (whether it overrides a server-level `OLLAMA_KEEP_ALIVE=-1` is
> UNVERIFIED — F-13; the fix must not depend on it). A durable marker inside the repo (CUI
> boundary + wrong lifetime). Windows Job objects (correct-by-construction child reaping, but a
> larger platform-specific change than the defect requires — reconsider if tree-kill proves
> insufficient on an operator artifact).
>
> **Consequences.** Shutdown gains a bounded ≤~3 s verification window when engaged. A prior
> session's stranded model is reclaimed at next launch when its proxy still listens, and named
> visibly when it cannot be. An operator-owned Ollama with no marker is never touched. The
> `keep_alive:"5m"` per-generate hardening and the used-but-never-engaged unload tier
> (`record_use`) land with the same PR but are recorded as complements, not the fix.

## 7. Failure-mode attack on the proposal, and the hardened rewrite

Attacks run against my own §4 before writing it; the diff above **already is** the hardened
rewrite — each attack names the guard that answers it.

1. **Kills an Ollama the operator started for their own work.** Tree-kill is rooted at
   `self._proc.pid`, which exists only when WE spawned (:227 "set only if WE started it");
   reconciliation refuses to act without the durable marker; the image sweep is unchanged
   ADR-0122 behavior on the engaged path only. No new kill reaches an unowned process.
2. **PID recycling.** The tree-kill runs only while `proc.poll() is None` on our own un-reaped
   `Popen` — the open handle (Windows) / zombie (POSIX) pins the PID until we reap it, so the
   PID cannot have been recycled at kill time.
3. **Reconciliation blocks or slows startup.** It runs on a daemon thread after serving starts;
   its first gate is the existing 1.5 s TCP `endpoint_up` probe; all HTTP is bounded (≤4 s).
   A hung Ollama costs the thread, never the launcher.
4. **Stale/poisoned marker.** Worst case is one loopback `/api/ps` probe + unload attempt
   against the marker's endpoint; the marker is timestamped, endpoint-scoped, cleared on
   verified-clean exit, and unreadable-marker degrades to the configured endpoint. It contains
   no schedule content and lives outside the repo (CUI-clean).
5. **Fix only works when AI is enabled (the original hole reborn).** Reconciliation keys off
   the MARKER, not current settings — it runs on every launch. The in-session
   used-but-never-engaged half is closed by the `record_use` tier landing in the same PR
   (kept from the earlier design; the marker then also records first USE, not just settings
   engagement — apply-time detail flagged in the PR).
6. **Tray respawn defeats the cleanup.** The adopted-path sweep keeps ADR-0122's tray-first
   order. On the spawned path the tray is not the parent (we spawn `serve` directly), and the
   tree-kill precedes the sweep, so there is no window where killing the server invites a tray
   respawn before the sweep looks for the tray. (On this operator's box the tray was not even
   running — F-7 evidence.)
7. **Verification latency at quit.** Bounded to ~3 s, engaged sessions only, and it replaces a
   silent wrong "success" with a visible truth — accepted, recorded in the ADR.
8. **`keep_alive:0` may not beat `OLLAMA_KEEP_ALIVE=-1` (F-13 UNVERIFIED).** The fix does not
   depend on it: on the spawned path the tree-kill reaps the runner regardless; on the adopted
   path a failed unload is now *visible* (`unload-incomplete`) instead of silently counted as
   success, and the parked probe (§8-3) settles the question before any further reliance.
9. **The unload itself can still race the runner's unwind (F-15 UNVERIFIED).** The bounded
   re-probe window absorbs a slow unwind up to ~3 s and reports honestly beyond it; the parked
   probe settles the real timing.

## 8. PARK LIST — operator-supplied artifacts (exact deposit + what each unlocks)

Deposit location for all: paste into the session chat, or commit under
`audit/operator-artifacts/` via the GitHub web UI (they contain no schedule content).

1. **`where ollama` (or PowerShell `(Get-Command ollama).Source`) output** → resolves F-16
   branch (a)/(b): whether SMAT can manage `C:\Tool\Ollama` at all. Unlocks: the install-path
   override decision (AI-Settings field proposed only if branch (b) holds; no env-var name is
   invented in this report).
2. **Raw JSON of `curl http://127.0.0.1:11434/api/ps` while a model is loaded** → F-12 schema
   for the installed Ollama version. Unlocks: hardening `_loaded_models` field handling against
   the real shape instead of an assumed one.
3. **Override probe:** with `OLLAMA_KEEP_ALIVE=-1` still set: load a model (one short
   `ollama run` prompt), then `curl -X POST http://127.0.0.1:11434/api/generate -d
   '{"model":"<name>","keep_alive":0}'`, wait 10 s, then `curl http://127.0.0.1:11434/api/ps`
   again (all loopback) → settles F-13 (does per-request `keep_alive:0` override `-1`?) and
   F-15 (runner exit timing). Unlocks: the Critical-vs-Medium severity fork on the unload
   strategy — if the model is still listed, the unload path is inoperative on this machine.
4. **The manifest file(s) under `C:\Tool\Ollama\models\manifests\` referencing
   `sha256-4824460d29f2058aaf6e1118a63a7a197a09bed509f0e7d4e2efb1ee273b447d`** (do NOT run
   `ollama list` — it respawns the server) → F-18: model identity, parameter count,
   quantization, and the fits-in-11.5-GB verdict. Unlocks: separating the configuration
   finding (weights straddling VRAM/RAM under `--no-mmap`) from the lifecycle defect.
5. **`Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" | Select ProcessId,
   ParentProcessId,CommandLine` plus `Get-Process -Id <that PPID>`** (expected: not found) →
   F-7's on-machine dangling-PPID signature; run after a fresh enable→ask→quit cycle **counting
   instances** → F-17 accumulation proof (does a second orphan coexist with the first?).
6. *(Optional)* the same §8-3 probe against an **embedding** model → F-14.

---
*Audit performed 2026-07-30 against `d508250b3c82ea6af9abc3c8abe3f957535d0b1b`. Report-only:
no commit, no push, no PR, no code applied. The plan of record
(`/root/.claude/plans/before-you-begin-any-vivid-lake.md`, PR-1) is updated to route through
this report's human gate before any implementation resumes.*
