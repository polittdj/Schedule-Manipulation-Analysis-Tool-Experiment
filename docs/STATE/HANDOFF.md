# Handoff — 2026-08-14 (d) (001c CLOSED at operator direction: the approved AI gateway is a first-class backend — allowlist, consent gate, transaction log, settings option; ADR-0402; v1.0.202, wheel + nine installers rebuilt)

> ## STATUS (current) — ADR-0402 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`,
> branched from `main` **71a56d3** (= #589's squash; local HEAD == origin/main at branch
> time). Highest ADR now **0402**. **SHIPPED code changed** — version **v1.0.202**, SCHEMA
> 2.11.0 unchanged, wheel + all nine installers rebuilt AFTER the last source edit
> (lockstep suite 64/64; the first build was invalidated by post-build lint fixes — the
> ADR-0148 trap, caught by ritual order this time). xfails unchanged: TEST-01 + JCL-BR-01.
>
> ## What landed — ADR-0402 (operator-directed: "I don't get the option to use the NASA
> ## approved AI models that are itar approved. Fix this" — that message WAS the 001c decision)
> The plan doc's §6 steps 4–6, built as designed and verified QC-1: **(1)**
> `net_guard.APPROVED_GATEWAY_ENDPOINTS` (one entry, the NASA gateway) +
> `is_approved_gateway_endpoint` — exact normalized match, https-only, never-loopback; the
> loopback sets and their ADR-0394 pins are UNTOUCHED. **(2)** `ai/gateway.py`
> `GatewayBackend` — OpenAI /v1 wire over the same stdlib no-proxy/no-redirect opener,
> constructor raises CUIEgressError off-allowlist, `is_local`/`is_approved_gateway` are
> instance MEASUREMENTS (ADR-0396 discipline). **(3)** `ai/txlog.py` — the AI transaction
> log: JSONL records (`*.sent` BEFORE transmit, `*.done` after) carrying ts/endpoint/model/
> classification + prompt SHA-256 and byte count (never text); a failed sent-write ABORTS
> the transmission with the opener never invoked, and the same failure reads as gateway-down
> so routing falls closed to Null end-to-end; log lives outside the clear-on-quit cache
> (`$SF_AI_LOG_DIR` else `~/.local/state/schedule-forensics/`). **(4)** consent at every
> layer: `AIConfig.gateway_endpoint`/`gateway_approved`; `factory.gateway_or_none` refuses
> without selection+acknowledgment+allowlist; `route_backend`'s NEW `gateway_backend`
> branch re-requires the acknowledgment and never falls back to the gateway; the dead
> `cloud_backend` path is untouched (GW-01 keeps meaning). **(5)** the settings page: the
> gateway option REPLACES the dead `Cloud (UNCLASSIFIED only)` trap; endpoint is a SELECT
> over the allowlist (free text cannot express an unapproved destination; POST re-sanitizes;
> constructor re-refuses); acknowledgment checkbox arms only on its literal value;
> `_gateway_status_note` diagnostics; explainer rewritten (Data LEAVES this machine + the
> ATO-not-verified caveat); `/api/ai/models?kind=gateway` (allowlist-checked BEFORE
> construction); `settings.js` drives the live catalog dropdown. **(6)** the air-gap guard
> EVOLVED, not suppressed: the approved endpoint passes as page TEXT only (test-side
> literal — widening the product allowlist goes red in test_airgap.py until consciously
> mirrored); src/href and any path suffix still fail.
> **Verification:** 7-check acceptance probe 7/7 RED on the unpatched tree → 7/7 GREEN
> after (the red probe IS the operator's complaint, executable). Mutation battery,
> sandboxed (PYTHONPATH shadow, import-origin + observability canaries, instruments
> md5-identical, pristine-sandbox control green): **15/15 caught by name** — and round 1
> found a REAL battery gap: `models_probe_unrestricted` survived because the constructor
> (defense-in-depth) also refuses and its message contained the asserted word; closed with
> a constructor-bomb LAYER pin, re-run, caught 1-failed/15-passed. Tier-2 render-verify in
> real chromium (isolated venv; main env stays playwright-free so the gate baseline stays
> comparable): option renders, catalog probe FIRES on endpoint selection (fetch observed,
> status span measured both sides), unacknowledged save shows intent banner +
> "acknowledgment is required", full arming shows APPROVED GATEWAY banner with the local
> assurance withdrawn, and the REAL app wrote real probe.sent/done records to the default
> log. From this container the probe gets HTTP 403 (egress proxy) — the page honestly
> reports could-not-reach; on the operator's NASA network this is where the ITAR catalog
> populates (their unversioned patch already demonstrated it — plan doc §1).
> Docs: ADR-0402; plan doc header + §6 marked BUILT; DoD 001c row closed with strikethrough.
>
> ## Next — in order
> **DISC-01 release determination** (operator / authorizing official; repo is PUBLIC again)
> → **PO-04/05** (BLOCKED on an operator-delivered CEI/HMI reference export) →
> `actual_start_driven` consumed nowhere (ENG-DEAD-01; SHIPPED-code lockstep when taken) →
> TEST-01 chromium build-number pins (the audit module's last live xfail) → **JCL-BR-01**
> (shipped-code; the strict xfail flips loudly when fixed) → FINAL-REPORT overclaims
> (condition on `_observed_banner`) → JCL docs follow-ups (help.py τ term; EAC gloss
> scope) → 8 stale remote branches (DoD 091) → SMAT-SANDBOX branch-name cleanup (operator
> UI). **Gateway follow-ons recorded, not queued:** i18n template keys for the
> endpoint-interpolated warnings; config persistence across launches (deliberately NOT
> done — per-launch acknowledgment IS the consent model; revisit only on operator ask).
> **Operator:** DISC-01 · a CEI/HMI reference export · FX-03/04 re-run ·
> sub-day-negative-float Fuse run · license · SANDBOX branch-name/repo cleanup · verify
> the gateway option on the real NASA-connected machine (the catalog should populate where
> the unversioned patch's did; the local patch is now obsolete — reinstall from a fresh
> tier installer).
>
> ## Carried forward
> ADR-0353..0402 closed — do not re-open. NEW lessons this session: **a defense-in-depth
> twin can make a layer's mutation invisible to an outcome assertion** — the constructor's
> refusal message contained the word the route-layer test asserted, so the route mutation
> survived; pin the LAYER (a constructor bomb), not just the outcome; **`pkill -f`
> self-matches on the plain string elsewhere in your own command line even when the
> PATTERN is bracketed** — `[s]erve_for_pw` still killed the shell because `nohup python
> …/serve_for_pw.py` sat two lines up; kill by recorded PID; **a stateful dev server
> across browser-drive runs reproduces OR-06 in miniature** — restart clean per run;
> **install the browser driver in an ISOLATED venv** when the suite's skip-baseline must
> stay comparable (playwright in the main env executes ~19 CI-invisible tests, full-gate
> skill §4). Standing traps unchanged (a data pin guards the literal, not the guarantee ·
> mutation-green is not adversarially verified · adversaries probe BETWEEN the mutations ·
> a guard's input plumbing is attack surface · monkeypatch repoint is per CALL SITE ·
> never MEASURE a tree a battery is mutating · never MUTATE an instrument a measurement is
> using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` · `pytest -m
> parity` alone exceeds 900 s · the container starts with NO deps installed · `git fetch
> origin` before taking an ADR number and again before committing · a number written
> mid-session is not a measurement, `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green: `python -m ruff check .` (All checks passed) / `python -m ruff format
> --check .` (1,009 files) / `python -m mypy src/` (154 files, no issues) / bandit exit 0 /
> node --check per file, 0 fails. **Full suite on the FINAL tree: 4043 passed, 47 skipped,
> 2 xfailed (TEST-01 + JCL-BR-01), 0 failed, exit 0, 29:14** — every skip an
> environment-gated playwright skip; 4043 = the prior close's 3972 + the 71 new
> gateway/allowlist/txlog/settings/air-gap tests. **Parity gate: 72 passed, 15 skipped
> (env-gated), exit 0, 15:12.** Installer lockstep 64/64 against the final v1.0.202 wheel.
> The FIRST full run (pre-fix tree) failed exactly one test —
> `test_monolith_split_contract[settings.py]`, the missing `_gateway_status_note` `X as X`
> re-export — fixed, contract module 69/69, wheel + installers rebuilt, and the whole
> suite re-run on the final tree (the figures above are that re-run). Drift guards green.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
