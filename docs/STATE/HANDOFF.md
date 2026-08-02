# Handoff — 2026-08-01l (Phase 1b: the launcher claims the port before it serves; ADR-0334; v1.0.150)

> ## STATUS (current) — **Phase 1b MERGED as `e0b0fcf` (#511), ADR-0334.** Phase 2 merged as
> `1e51079` (#510), ADR-0333. `main` is at **v1.0.150** and its installers embed the 1.0.150 wheel
> (verified). Working tree clean, branch restarted from `origin/main`; no check-ins armed.
> **THE OPERATOR MEASUREMENT ARRIVED** and is banked verbatim in
> `docs/STATE/OPERATOR-REQUESTS.md` (OR-06) — committed on its own first (`3eb317b`) so it can
> never be lost or need re-collecting. **THE ANSWER IS ONE PID.**
>
> Deployed box, v1.0.149: 1st launch ⇒ listener **18664** (18664 + 39740, both 19:33:17); closing
> **only the browser** leaves 18664 alive (correct — `idle_grace=600`, a server legitimately
> outlives its browser by ten minutes); **2nd launch ⇒ still 18664, same 19:33:17, process list
> byte-identical.** The second launch produced **no listener and no fourth process even
> transiently** — it exited mute (uvicorn bind failure ⇒ `sys.exit` into the `os.devnull` sink
> `_ensure_streams` installs under `pythonw`) while its **already-armed browser timer** opened a
> window onto the OLD server with the previous session's schedules in memory. Handoff branch ONE,
> confirmed; Windows `SO_REUSEADDR` double-binding did NOT occur. It also defeats ADR-0324's launch
> token (same process ⇒ same token). **This is the SERVER-side half of OR-06** — the stale fields
> were never only browser memory, which is why they survived ADR-0324/0332.
>
> **Fix:** `launcher.claim_port()` runs **before the browser timer is armed and before uvicorn
> binds** — connect-probe → `GET /api/whoami` → not-us ⇒ **refuse visibly** · ours ⇒
> `POST /api/shutdown`, poll 20 s → released ⇒ serve fresh · still held ⇒ **refuse visibly, naming
> the pid**. "Always start clean": a predecessor is REPLACED, never reused. **The browser timer is
> NOT moved after `serve_fn`** — `serve_fn` blocks for process life, so a timer after it never
> fires; the fix is ordering *within* the pre-serve phase. **Connect-probe, never bind-probe** — on
> Windows a second bind can succeed against a served port. New **`/api/whoami`** is deliberately
> not `/api/heartbeat`: a probe must not refresh `last_beat` or set `browser_seen` on the process
> it is replacing, so `_liveness` now exempts that one path. Version **1.0.150**, highest ADR
> **ADR-0334**.
>
> ## Verification (all read from runs this session)
> `tests/test_launcher_single_instance.py` + `tests/test_launcher.py`: **21 passed**. **Nine new
> gates, all proved able to fail by reverting the CALLER and keeping the API**, watched: removing
> the claim from `main` ⇒ `assert ['browser','serve'] == ['claim','browser','serve']` — **the
> measured bug verbatim**; dropping the `/api/whoami` middleware exemption ⇒ *"the probe refreshed
> the predecessor's heartbeat"*; letting a stranger be stood down ⇒ *"a stranger's port was sent a
> shutdown request"*; a default opener ⇒ the environment's proxy map printed. Statics: ruff clean ·
> format clean (452) · mypy --strict clean (117) · **bandit EXIT=0**. **Full suite on the FINAL tree:
> 3276 passed, 2 skipped, 0 failed in 17m39s** — test count up by exactly 11 (9 launcher gates +
> 2 `/api/whoami` contracts); the carried /analysis focus→tip intermittent passed and stays
> adjudicated either way.
>
> **LAW 1 CATCH, from bandit's B310 on the new `urlopen`:** urllib's DEFAULT opener reads the
> machine's proxy settings, so on a corporate-managed Windows laptop even `http://127.0.0.1:8321`
> can be routed through the company proxy — the probe would be refused (a live predecessor misread
> as "not ours") or **sent off-machine**. The launcher now builds its opener with an **empty
> `ProxyHandler`**, the same hardening `ai/ollama.py` already applies. Pinned by its own gate.
> **Note the assertion is ABSENCE:** `ProxyHandler({})` installs no `<scheme>_open` methods, so
> `OpenerDirector.add_handler` never registers it — a hardened opener carries NO `ProxyHandler` at
> all. A first attempt asserted the opposite (a present-but-empty one) and failed on correct code;
> corrected rather than worked around.
>
> ## ⇢ NEXT — the approved plan (HANDOFF ⇢ NEXT is the queue; the plan file is GONE from disk)
> 1. **Phase 1b REMAINDER — the disk cache. NOT done, deliberately deferred, not forgotten.**
>    Clear on **clean shutdown + atexit, NEVER at launch** (launch-clearing leaves data at rest over
>    the whole between-sessions window), plus a **size and age cap** as the belt for a hard kill
>    that never cleared. `engine/cache.py` already has `clear()`; it needs a `prune(max_bytes,
>    max_age)` and shutdown/atexit wiring (`_trigger_shutdown` + `launcher.main`'s `finally`).
>    **It was held back on purpose:** it is a CUI-at-rest policy decision with a real cross-session
>    warm-start trade-off, and it deserves its own round rather than riding a change whose evidence
>    is a launcher measurement. **Confirm the intent with the operator first** — clearing on every
>    quit does discard the warm start.
> 2. **Phase 3 — UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas).** The four
>    unconverted Act III pages (`/sra`, `/risks`, `/briefing`, `/brief` — zero
>    panelkit/`_panel_head`/`_shell_tools`/`sf-take`), then `DOM_PENDING`'s 7, then the DoD ledgers.
>    The DD-line ledger must EXCLUDE non-time-axis charts (`histogram.js`, `scatter.js`,
>    `sra_jcl.js` cost axis).
> 3. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
>    half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5**
>    monolith split 2–3 (`app.py` is 20.9k lines, 2.8k LARGER than ADR-0297 left it) · **Phase 6**
>    docs/operator queue. The OR-04 collection run stays with the operator.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** · **SPLIT-23** · **A0293-UI** · Project5's SSI export
> contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass packing ·
> ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase · ADR-0332 scope note (within-session `sf-story-visited`) · ADR-0333
> scope note (`sysmon.js`'s interval still ticks while hidden; its `poll()` early-returns).
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus:** the caption/halo
> set; "listing the fields to reset is maintainable"; a blanket `sf-` localStorage sweep;
> "`tooltips.js` is one of the observer defects" (it is the EXEMPLAR); "querySelectorAll CALL COUNT
> measures observer cost" (measure NODES RETURNED); "a shared observer helper module is the clean
> fix" (ADR-0316 load-order); "`sysmon.js` is an unfixed idle pump" (the cost was the SERVER loop);
> **NEW — "two servers bound 8321 simultaneously"** (MEASURED false: the second launch produces no
> listener at all) · **"the surviving server is itself the bug"** (false: `idle_grace=600` is by
> design; the bug is relaunching ONTO it) · **"a bind-probe answers 'is the port taken?'"** (false
> on Windows — connect-probe) · **"a hardened opener contains an empty ProxyHandler"** (false:
> urllib never registers a handler that installs no methods — assert ABSENCE).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary test
> mutation — it discards UNSTAGED real work in that file; `cp` from a scratchpad copy instead**
> (cost a full re-apply of `launcher.py` this session). **A hash-for-hash `sed` does NOT update
> abbreviated `bc18307…` digests quoted in prose — grep the prefix too.** `pkill -f` with the
> pattern in the killer's own command line kills the killer. CI can take ~11 min to register check
> runs. `TestClient` follows 303 and CONSUMES one-shot banners. Parity marker ≈2m38s. Headless
> Chromium hides scrollbars. `caplog` needs `logger="schedule_forensics.<module>"`. **Playwright
> `bounding_box` / `page.screenshot(clip=…)` are VIEWPORT-relative.** **localStorage is
> per-ORIGIN.** Bundled chromium: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Containers
> RESTART mid-run: statics FOREGROUND first, reinstall pip after resume. After a squash-merge:
> `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
> origin/main` — **NEVER amend the merged commits.** **Version-bump sequencing:** bump BEFORE the
> suite. Never sleep in a sync-Playwright route handler. Never `from tests.web...` in a test.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** (ADR-0316).
> **A stray `*/` makes CSS error-recovery swallow the NEXT rule silently.** **`cd` in a Bash call
> persists across calls — use absolute paths.** **When reverting to prove able-to-fail, revert the
> CALLER not the API.**
>
> **Standing rule:** do not put a test result in prose unless the number appeared in output you
> read that turn. **A launched run is not a result, and a piped exit code is not the command's.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
