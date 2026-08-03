# Handoff — 2026-08-03c (The standing rituals become invoked skills; ADR-0344; v1.0.159)

> ## STATUS (current) — **IN FLIGHT.** Seven project skills committed under `.claude/skills/`.
> Branch `claude/repo-audit-skills-vbm0ka`, from `origin/main` at **`1119162`**. ADR-**0344**,
> **v1.0.159** (unchanged — nothing under `src/` was touched, so no wheel/installer rebuild;
> the ADR-0148 lockstep test was run to confirm it).
>
> ## What landed — and what the search actually found
> The ask was "find and install skills that would help this project." **Both catalogs were searched
> first and both came back empty of anything new**: the account skill catalog already has
> `schedule-forensics`, `session-token-guardian` and `docx`/`xlsx`/`pptx`/`pdf` enabled, and the only
> plugin marketplace is `knowledge-work-plugins` (data · marketing · design · operations), whose
> `engineering` and `design` plugins are already on. **There was nothing to install.** That empty
> result is recorded in ADR-0344 so the next session does not repeat the search.
>
> The real gap is the one `LESSONS-LEARNED.md` Part III already named — **"prose reminders decayed;
> tests didn't."** Where a ritual is expressible as a test it already is one (drift guard, wheel
> lockstep, dictionary sync, DD-line ledger). The residue governs *session conduct*, not tree
> contents, and a test can only catch it after it was done wrong. Seven skills now carry it:
>
> | skill | what it prevents recurring |
> | --- | --- |
> | `full-gate` | a piped exit code hiding a real failure · `node --check` on a glob checking only file 1 · reporting a suite nobody read |
> | `prove-able-to-fail` | ADR-0304's class — a green assertion over a control that moves nothing; a `-k` filter deselecting the target |
> | `render-verify` | ADR-0343's class — "I did not execute the rendered page"; source call sites read as rendered charts |
> | `metric-parity` | stored-vs-recomputed float triage · hard-coded 480 · a golden re-pinned silently |
> | `ui-change` | the Mission Ops DoD, the one-mechanism table, `--bad` (not `--danger`), the literal `—` |
> | `cui-guard` | Law 1 — the blocklist's two exceptions, std-lib-only runtime, fail-closed AI, no remote asset |
> | `session-close` | this rotation's exact shape · ADR-0148's stale-wheel class · the twice-repeated doc drift |
>
> ## Verification — the recipe was EXECUTED, not drafted
> `render-verify`'s Tier-1 renderer was run before it was written down: `/cei` against the five
> committed `TP4_DataCenter` fixtures → **200, 25,850 bytes**, and the real takeaway `h1` read back
> from the response. Its launch-nonce normalisation (`sf-launch` content + `?v=` cache-bust) is what
> makes a two-tree render diff mean anything. `full-gate`'s prerequisites were executed in this
> container: `pip install -e ".[dev]"` resolves **1.0.159**, and the vendored chromium the browser
> tier globs for is present at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. All seven files
> parse as YAML with `name` == directory name; descriptions are 488–567 chars against a 1,536 cap;
> none shadows a bundled skill (`/review`, `/code-review`, `/security-review`, `/simplify`, `/run`).
>
> ## The limitation, recorded rather than papered over
> **This session cannot observe the skills loading.** Claude Code watches skill directories for live
> edits, but a *newly created* top-level skills directory needs a restart to be watched, and this
> session's skill listing was built before `.claude/skills/` existed. The load rests on the
> documented mechanic plus the files' validity — not on an observation. Committing them (rather than
> `~/.claude/skills/`) is deliberate and verified: **cloud/web sessions and routines load project
> skills from the cloned repo and ignore `~/.claude/skills/` entirely**, which is how this project is
> actually driven.
>
> ## Next — Phase 4 continues, unchanged by this
> **CC-01's rendering half** — *"74 sites" is an approximate grep, **RE-DERIVE it** before touching
> anything*; ADR-0240 reserves it for a **Fable 5 Max** deep dive · **SRA-LEGACY**
> (`audit/SRA-ROOTCAUSE-20260730.md`) · **V3** (`engine/msp_filters.py` hard-codes `"d": 480`;
> ADR-0310 made it a conformance fix, but it MOVES saved-filter populations — it needs its
> migration-report gate). Then **Phase 5** monolith split 2–3 (`app.py` **21,333** lines, `state.py`
> **1,479**) and **Phase 6** docs/operator queue. OR-03 and OR-06's launch-sequence half remain in
> `OPERATOR-REQUESTS.md`; OR-04 stays with the operator.
>
> ## The gate, measured — and the one red triaged by VARYING COUNT
> `ruff check` pass · `ruff format --check .` **867 clean** (0.16.1) · `mypy --strict` **117 files** ·
> `bandit` **exit 0** · `node --check` **60/60** · full suite **3400 passed, 3 skipped, 1 failed
> (16:33)** · `pytest -m parity` **49 passed**. The red was `test_float_tip_scroll` — the documented
> `/analysis` focus→tip family. Four samples of the same 19 tests: **1 failed** (suite, with changes) ·
> **2 failed** (targeted, with changes) · **0 failed** (targeted, PRISTINE at `1119162`) · **1 failed**
> (targeted, with changes). The diff is markdown-only so it cannot be causal, and **the proof is the
> varying count on an identical tree, NOT the pristine pass** — *a pristine-tree pass is not a
> discriminator when the difference cannot be causal; it is just another sample of a flaky test.*
> **Verified why it ran here at all:** `playwright` is its own `[browser]` extra, NOT `[dev]`; CI's
> `test (3.11)`/`(3.13)` install `.[dev]` (so every playwright-gated test SKIPS) and the `browser` job
> installs `.[dev,browser]` but runs **only** `test_r11_panel_contract.py`. This family **never
> executes on CI** — the mechanism behind "has NEVER failed on CI." Both facts are now in `full-gate`.
>
> ## Carried forward, unchanged
> `/groups`' breakdown "Activities" column still counts summary rows (`len(uids)`) — measured,
> deliberately NOT fixed (ADR-0343). `/briefing`, `/path`, `/compare` render a bare takeaway h1 with
> NO `page-lede`. **Known intermittent: the `/analysis` focus→tip family** — adjudicated,
> pre-existing, has NEVER failed on CI. Do NOT chase. `pgrep -f <pat>` self-matches like `pkill -f`.
> pytest stdout to a FILE is block-buffered (use `python -u`). `cd` in a Bash call persists — use
> absolute paths. `pytest --timeout=` is NOT installed and its usage error exits **0** through a
> `| tail` pipeline. `--bad` is the red token; `--danger` does not exist. Source call sites ≠ rendered
> charts. Never `git checkout <file>` to undo a temporary test mutation — `cp` from a scratchpad copy.
>
> ## The skills caught a defect in their own commit — with the trap they document
> `ruff format --check .` read **green, 458 files**, before commit. That was a stale **0.15.8** in
> `/root/.local/bin` shadowing the **0.16.1** `pip` had just installed to `/usr/local/bin`. They differ
> in SCOPE, not style: 0.16.x also formats fenced `python` blocks **inside markdown** — the same tree is
> **458** files to one binary and **867** to the other — so `render-verify/SKILL.md`'s python recipe
> would have gone red on CI (which resolves `ruff>=0.6` to latest). Reformatted; **867 clean** under
> the explicit `/usr/local/bin/ruff`. `which -a ruff` vs `pip show ruff` is now step 0 of `full-gate`,
> with the measured counts. **This is 2026-07-29 cont.3 — "a green gate proves nothing if the binary
> isn't the one CI runs" — in a new costume: a stale wheel then, a shadowed linter now.**
>
> **New this session:** an empty search result is a deliverable, not a dead end — it is what converts
> "install a skill" into "the knowledge already exists here, unindexed." And the ladder from Part III
> has a middle rung: law (CLAUDE.md) → **invoked procedure (a skill)** → executable guard (a test).
> Reach for the highest rung that fits; a ritual about *how to verify* cannot be a test, because the
> test is the thing it is telling you to distrust.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
