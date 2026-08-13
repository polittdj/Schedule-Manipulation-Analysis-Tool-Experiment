# Handoff — 2026-08-13 (d) (DoD 001a closed: the loopback allowlist is pinned; ADR-0394; v1.0.200)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-kickoff-ss9eb8`,
> branched from `main` **9c0c918** (clean restart: the branch was already at `origin/main`,
> 0 ahead / 0 behind). Highest ADR now **0394**. **No shipped code changed** — `src/` is
> untouched, so the version stays **v1.0.200** and **no wheel/installer rebuild was required**.
> SCHEMA stays 2.11.0. One new file: `tests/guards/test_loopback_allowlist.py`.
>
> ## What landed: DoD 001a — the Law-1 guarantee stopped being an unasserted data literal
> Every locality decision funnels through `net_guard._LOOPBACK_HOSTNAMES` (`:127`) and
> `_LOCAL_HTTP_SCHEMES` (`:234`), and through `is_loopback_host` / `is_local_http_endpoint` into
> `ai/ollama.py:130`, `ai/openai_compat.py:39`, `web/app.py:6549/6551/6590`, `launcher.py:232`
> and `web/app.py:8161`. **Nothing pinned either set's contents.** The new guard pins them in
> **two layers**, and the mutation battery — not taste — decided that both were required.
>
> * **Data pins** — both frozensets asserted *exactly* against **test-side literals never imported
>   from the module under test** (an oracle that reads the value it judges cannot refute anything).
> * **Behavioural closure sweeps** — over a curated non-loopback population (the gateway and every
>   parent domain, remote/private/link-local IPs, wildcard binds, a Cyrillic-`о` homograph, the
>   decimal-packed `2130706433`, and generated confusables like `localhost.evil.com` /
>   `notlocalhost` / `localhost.nasa.gov`), asserting **what is actually accepted**, both directions,
>   plus a scheme sweep pinning acceptance to exactly `{http, https}`.
>
> ## The premise was RE-MEASURED, not inherited (QC-2)
> The audit's "226 green, reproduced at 854" is testimony about a selection I did not run. Re-derived
> in a sandbox copy with `proxy.fast.luna.nasa.gov` added to the allowlist — verified in-process that
> `is_loopback_host("proxy.fast.luna.nasa.gov")` returned `True` — the guard/AI/air-gap/startup/
> launcher/exhibit-CLI suites ran **336 passed, 0 failed** with the new module deselected. Different
> population, same conclusion: **the pre-existing suites are blind to a named allowlist entry.**
>
> ## Verification (QC-1) — 9/9 caught BY NAME
> Battery mutates a **sandbox copy of `src/`**, never the instrument, and carries two self-checks
> that make a meaningless result impossible to report as a real one: a **canary** that aborts unless
> a sandbox mutation actually changes the outcome (proving `PYTHONPATH` really shadows the editable
> install's `.pth`), and a **control** run that must be green. Mutations: `widen_gateway` (8 tests
> red) · `widen_other` (2) · `narrow_drop_ip6` (4) · `scheme_widen_ftp` (2) · `suffix_bypass` (6) ·
> `substring_bypass` (4) · `always_true` (6) · `drop_scheme_check` (1) · `drop_host_check` (2).
> `net_guard.py` md5 `ff76e70c…` **identical** before and after. Re-run in full against the final
> file after lint fixes, so the reported result is the one that ships.
>
> **The finding that shaped the design:** `suffix_bypass`, `substring_bypass` and `always_true`
> leave **both frozensets provably untouched** — the data pins stayed GREEN on all three, and only
> the behavioural sweeps caught them. A data pin guards the literal; it does not guard the
> guarantee. Neither layer subsumes the other.
>
> ## NEW FINDING — the same defect, second surface, NOT fixed here
> `web/app.py:1076` holds `_ALLOWED_HOSTS = frozenset({"127.0.0.1","localhost","::1","testserver"})`,
> the DNS-rebinding Host-header guard. **No test file names it.** Measured: with the gateway hostname
> added in a sandbox, `tests/web/test_sec_hardening.py` + `tests/test_launcher.py` = **23 passed, 0
> failed**. Same class as 001a, different security property (request admission, not egress). Left
> alone deliberately — 001a was specified to land ALONE — and it is the next cheap, high-value pin.
>
> ## Doc corrections made in passing (QC-2)
> `APPROVED-GATEWAY-INTEGRATION.md` §2's `web/app.py` anchors had drifted (`6406/6408/6447`, `8018`
> recorded against `cacd769`); re-derived to `6549/6551/6590` and `8161`. The `net_guard.py` anchors
> it cites were re-checked and **still hold exactly**. §6 step 1 marked DONE; §7 carries the
> `_ALLOWED_HOSTS` finding. Note also: the kickoff prompt says the standing rules are "ADR-0392" —
> they are **ADR-0393** (`CLAUDE.md` is right, the kickoff was stale).
>
> ## Next — Band 1 continues, in dependency order
> **001b** make the sovereignty banner OBSERVED, not config-derived (`route_backend`'s Banner is
> dead code; `chrome.py:175` renders `banner_for(state.ai_config)`, so a DOWN gateway still displays
> as up; six user-visible claims + four i18n translations, two of which print inside EXPORTED
> exhibits at `ai/brief.py:625` and `web/sra.py:1076`; prove it can go red by routing a non-local
> fake) → **001c** the operator's cloud/gateway decision, then its ADR (**0395** now — take the next
> free number after `git fetch origin`, never one a doc predicted).
> Then: pin `_ALLOWED_HOSTS` · `actual_start_driven` consumed nowhere · ADR-0391's own-calendar floor
> unguarded · `mpxj_ref()` shallow-clone guard (DoD 117) · pre-commit has no image detector vs 120
> tracked PNGs · 22 playwright modules pin a chromium BUILD NUMBER · FINAL-REPORT overclaims · 8
> stale branches. **Operator:** the 001c decision · FX-03/04 re-run · sub-day-negative-float Fuse
> run · license.
>
> ## Carried forward
> ADR-0353..0394 closed — do not re-open. NEW lesson: **a data pin guards the literal, not the
> guarantee** — pin the CONSTANT *and* sweep the BEHAVIOUR, because a bypass added above the lookup
> leaves the constant pristine. Second: **when a battery mutates a sandbox, prove the sandbox is the
> tree being measured** — a canary that must go red, or every "CAUGHT" below it is unfalsifiable.
> Standing traps unchanged (a standing rule is DATA, and unpinned data is not a guarantee · scope a
> substring assertion to the region that BINDS · a fixture generated by a rule cannot validate that
> rule · the corroborating oracle may already be in a doc nothing cross-references · an ADR's
> observation can be right and its diagnosis wrong · a new disclosure needs its own channel when the
> existing one carries a JUDGEMENT · a sweep's glob/population/pattern are part of its claim ·
> `| head -N` can SIGPIPE-kill a build mid-way · the MPXJ pin drifts in a shallow clone (FIRED) ·
> never MEASURE a tree a battery is mutating · never MUTATE an instrument a measurement is using ·
> `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` · `pytest -m parity` alone
> exceeds 900 s · the container starts with NO deps installed · `git fetch origin` before taking an
> ADR number and again before committing). A number written mid-session is not a measurement
> (`wc` decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
