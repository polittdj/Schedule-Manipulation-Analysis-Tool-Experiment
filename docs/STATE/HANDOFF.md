# Handoff — 2026-08-13 (e) (DoD 001b closed: the banner is observed; ADR-0395 + ADR-0396; v1.0.201)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-resume-ojz9q0`,
> branched from `main` **5a8003f** (0 ahead / 0 behind at start). Highest ADR now **0396**.
> **Shipped code changed** — version **v1.0.201**, wheel + nine installers rebuilt in lockstep
> (55/55 installer tests green). SCHEMA stays 2.11.0. New files: `src/schedule_forensics/ai/factory.py`,
> `tests/guards/test_observed_banner.py`, ADRs 0395/0396. Full local gate at close:
> ruff + format + mypy --strict + bandit + `node --check` green; full suite re-run after the
> state-doc rotation — see the gate line at the bottom of this section.
>
> ## What landed 1/2: DoD 001b (ADR-0395) — every sovereignty claim now rides ONE observed derivation
> Pre-fix, measured by an executed probe (QC-1, red first): `route_backend` returned the literal
> `Local-only — no data leaves this machine.` for a fake with `is_local=False` on BOTH the ollama
> and openai paths; the page banner was `banner_for(config)` — config only — and rendered
> "Local-only" with that same fake sitting in `SessionState.backend_cache`; `brief_blocks` had no
> parameter that could carry locality; `is_local` was a class constant read only by `_UseMarking`.
> The fix, bottom-up, each link observing the link below: `is_local` became an INSTANCE value
> recording the loopback validator's verdict on the actual endpoint (`ollama.py` /
> `openai_compat.py`; class constants deleted) → `banner_for_backend(backend, config)` is the one
> derivation core (missing/falsy `is_local` = presumed NON-local, fail closed; CLASSIFIED +
> non-local gets its own harsher wording; the §0.2 UNCLASSIFIED+cloud *intent* warning survives —
> over-warn is allowed, over-assure is not) → `route_backend` returns that derivation over the
> backend it actually chose (its Banner stopped being dead code; one deliberate change:
> UNCLASSIFIED+cloud with no backend now warns from routing too, where it used to say local while
> the page warned) → `banner_for(config)` constructs the would-be candidates via the NEW
> `ai/factory.py` (constructors moved DOWN from `web/settings.py`; settings re-binds the names so
> every historic import path and per-call-site monkeypatch still works) and derives over primary
> AND cross-check second → `chrome._observed_banner(state)` adds the second veto: the session's
> actually-routed cached backend, re-derived — so an injected non-local object can never sit
> behind a local banner. Consumers: the persistent banner, the CUI drawer (now a
> `{{ drawer_locality }}` template var), the home hero + empty-state takeaway, the settings tip,
> and BOTH exported exhibits — `brief_blocks(brief, *, ai_is_local)` (REQUIRED keyword, no default
> may assume local) and `_sra_report_blocks` via the `st` it already had. Local-state strings are
> byte-identical; the i18n catalog key + its four translations are untouched and now PINNED.
>
> ## Verification (QC-1) — 15/15 mutations caught by name, twice
> `tests/guards/test_observed_banner.py` (18 tests): route-level refusals, fail-closed presumption,
> exact-literal data pins (test-side constant + i18n-catalog-key pin), candidate/second/cache
> vetoes at page level via TestClient, export conditionals, instance-derivation pins. Red first:
> the probe confirmed all four defects by assertion on the pre-fix tree, and the module cannot
> even collect there (`ai.factory` absent). Teeth: a 15-mutation battery on a sandbox copy
> (PYTHONPATH shadow + canary + control + md5-identical instruments) — `route_constant_banner` ·
> `bannerfor_config_only` · `getattr_default_true` · `intent_warning_dropped` ·
> `islocal_class_constant` · `second_dropped` · `cache_veto_dropped` · `drawer_unconditional` ·
> `hero_unconditional` · `takeaway_unconditional` · `brief_default_true` · `brief_ignores_flag` ·
> `sra_unconditional` · `tip_unconditional` · `literal_reworded` — **15/15 caught**, and the
> battery was RE-RUN against the final post-format tree so the reported result is the one that
> ships. One test moved with its call site (`test_second_backend_caches_and_handles_openai_construction`
> now patches `factory.OpenAICompatBackend`; verified live that the patched constructor is reached).
>
> ## What landed 2/2: DoD 117 (ADR-0396) — the MPXJ pin guard, because the trap FIRED ON THIS BUILD
> The mandatory installer rebuild's first attempt pinned **`a100184d`** — this container's own
> shallow-graft boundary (`.git/shallow` names it). The diagnosis REVERSED TWICE under measurement:
> first "my pin is right" (it was the artifact), then "the committed installers are broken —
> `poi-5.5.1.jar` didn't exist at `42d92dc`" (it did; the boundary commit's `--stat` invents
> additions), settled by tree hashes — `42d92dc`, `a100184d` and `HEAD` all carry the IDENTICAL
> `tools/mpxj` tree (`2001032…`) — and by the GitHub commits API (full history, `path=tools/mpxj`):
> the true last touch is **`42d92dc`**, exactly what the committed installers said. Nothing in the
> wild was ever broken. Fix: `mpxj_ref()` now REFUSES a graft-boundary resolution and accepts
> `SF_MPXJ_REF=<sha>` only after verifying tree-identity with the working tree (all three refusal
> paths exercised live); new `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact`
> went RED against the drifted build (3/3 families) and GREEN after the corrected rebuild. The
> shipped v1.0.201 installers pin `42d92dc` via the validated override.
>
> ## Next — Band 1's last item, then the queue
> **001c** is the OPERATOR's decision (delete the dead `cloud` option, or build a first-class
> `ai/gateway.py` with `is_local=False`, its own named allowlist, a classification gate, and an AI
> transaction log — `APPROVED-GATEWAY-INTEGRATION.md` §6 steps 4–6). ADR-0395's chain makes the
> honest gateway wiring mechanical: a backend declaring `is_local=False` gets warning banners and
> export disclosures on every surface with no further plumbing. Take the next free ADR number
> after `git fetch origin` — never one a doc predicted. Then: pin `web/app.py` `_ALLOWED_HOSTS`
> (the one remaining unpinned security frozenset) · `actual_start_driven` consumed nowhere ·
> ADR-0391's own-calendar floor unguarded · pre-commit has no image detector vs 120 tracked PNGs ·
> 22 playwright modules pin a chromium BUILD NUMBER · FINAL-REPORT overclaims · 8 stale branches.
> **Operator:** the 001c decision · FX-03/04 re-run · sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0396 closed — do not re-open. NEW lessons: **a diagnosis can reverse twice and still
> land — write down only what the LAST measurement proved** (the MPXJ chain above; each step
> looked conclusive); **in a shallow clone, `git log -1 -- <path>` attributes the tree to the
> graft boundary** — the pin guard now refuses it, and tree-identity beats ancestry as the
> verifiable property; **condition a sovereignty claim on observation, not configuration** — and
> when a claim spans surfaces (page, drawer, exports, i18n), route every surface through ONE
> derivation so they cannot disagree. Standing traps unchanged (a data pin guards the literal, not
> the guarantee · a standing rule is DATA · monkeypatch repoint is per CALL SITE — it moved a test
> again this session · never MEASURE a tree a battery is mutating · never MUTATE an instrument a
> measurement is using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` ·
> `pytest -m parity` alone exceeds 900 s · the container starts with NO deps installed ·
> `git fetch origin` before taking an ADR number and again before committing · a number written
> mid-session is not a measurement, `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> ruff check . / ruff format --check . / mypy --strict src / bandit / node --check: all green.
> Full suite on the SETTLED tree (re-run after every edit including the doc rotation): **3805
> passed, 47 skipped, 0 failed** in 23:13 — skips are the known environment-gated set (playwright
> absent, loopback-URL round-trip). Parity ran inside it. Installer suite 55/55 including the new
> pin-artifact test.
# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
