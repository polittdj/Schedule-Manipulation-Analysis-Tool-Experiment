# Handoff — 2026-08-15 (a) (AI settings persist across launches: armed once, the desktop icon just works; DPAPI-wrapped key at rest; ADR-0404; v1.0.204, wheel + nine installers rebuilt)

> ## STATUS (current) — ADR-0404 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`
> (restarted from `main` **8c823d8** = #591's squash after its merge). Highest ADR now
> **0404**. **SHIPPED code changed** — version **v1.0.204**, SCHEMA 2.11.0 unchanged, wheel
> + nine installers rebuilt (lockstep 64/64). xfails unchanged: TEST-01 + JCL-BR-01.
>
> ## What landed — ADR-0404 (operator directive: "I do not want to have to put in the NASA
> ## API KEY everytime I open the program. I want it to work when I click on the desktop icon.")
> ADR-0402's "per-launch acknowledgment IS the consent model" carried an explicit
> revisit-on-operator-ask clause — exercised now, and the ask is broader than the key: five
> re-arming steps per launch is not "it works when I click the icon". Built
> **`ai/config_store.py`**: the WHOLE AI config (backend, endpoints, model, qa/second/
> timeout, gateway endpoint + acknowledgment + key) persists at `$SF_SETTINGS_DIR` else
> `~/.local/state/schedule-forensics/ai-settings.json` (beside the txlog, OUTSIDE the
> clear-on-quit cache; no schedule content ever). Key at rest: **DPAPI-wrapped on Windows**
> (user scope, ctypes, stdlib-only, `gateway_api_key_dpapi`); a FAILING protector omits the
> key entirely (fail closed on the credential — never a silent plaintext downgrade); POSIX
> stores honestly-named `gateway_api_key_plain` in a 0600 file (same protection class as
> the still-working SF_GATEWAY_API_KEY env var, config-first). **Loading is a trust
> boundary**: POST sanitizers re-applied — an off-allowlist gateway endpoint in a
> hand-edited file clears to "", non-loopback local endpoints fall to defaults, enums safe,
> timeout clamps, unprotectable key -> keyless; missing/corrupt file -> pure defaults.
> Wiring: `create_app(state=None)` (the launcher path) loads; injected states untouched;
> POST /settings + ai-off + wipe persist their result (OFF is a setting too — a stale file
> can never re-arm past an explicit off). Consent stays explicit/recorded/revocable —
> recorded DURABLY instead of re-asked; the banner still renders every armed launch; every
> transmission still logged. conftest gained SF_SETTINGS_DIR + SF_AI_LOG_DIR isolation (no
> test touches the operator's real state dir). Settings-page copy updated (no more
> "quit forgets the key").
> **Verification:** store tests written first; 6-mutant sandboxed battery **6/6 caught by
> name** (`launch_does_not_load` · `post_does_not_persist` · `load_skips_allowlist` ·
> `protector_failure_stores_plain` · `chmod_dropped` · `disk_overrides_injected_state`);
> instruments md5-identical. Operator acceptance test: two independent app instances
> sharing only the settings file — arm in the first, the second (no injected state = the
> desktop path) comes up routed to the gateway, acknowledgment checked, key held and never
> rendered.
>
> ## Next — in order
> **Operator: reinstall v1.0.204, arm ONCE (endpoint + acknowledgment + key + model), then
> confirm a plain double-click launch comes up armed with the catalog populated.** If the
> catalog still 401s WITH the key, the AI Hub's scheme is not Bearer — capture their
> documented auth header and a follow-on ADR adds it on evidence → **DISC-01 release
> determination** (operator / authorizing official) → **PO-04/05** (BLOCKED on an
> operator-delivered CEI/HMI reference export) → `actual_start_driven` consumed nowhere
> (ENG-DEAD-01) → TEST-01 chromium build-number pins → **JCL-BR-01** (strict xfail flips
> loudly when fixed) → FINAL-REPORT overclaims (condition on `_observed_banner`) → JCL
> docs follow-ups (help.py τ term; EAC gloss scope) → 8 stale remote branches (DoD 091) →
> SMAT-SANDBOX branch-name cleanup (operator UI).
>
> ## Carried forward
> ADR-0353..0404 closed — do not re-open. NEW lessons this session: **"revisit only on
> operator ask" clauses get exercised — write them so the successor knows exactly what to
> flip** (ADR-0402's clause named the field and the consent rationale; the flip took one
> unit); **read the ask's GOAL, not its noun** — "the API key every time" named the key,
> but the goal ("works when I click the icon") required the whole config to persist;
> **a persistence feature turns every POST test into a filesystem writer** — add the
> conftest isolation IN THE SAME UNIT or the suite pollutes the operator's real state dir.
> Standing traps unchanged (see the archive — data pins vs guarantees · mutation-green vs
> adversarial · monkeypatch per CALL SITE · never measure a mutating tree · never mutate a
> measuring instrument · two ruffs, use `python -m ruff` · parity >900 s · container
> starts with NO deps · fetch before numbering and before committing · `wc` decides).
> QC-1/QC-2 are ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green: `python -m ruff check .` (All checks passed) / `python -m ruff format
> --check .` (1,012 files) / `python -m mypy src/` (155 files, no issues) / bandit exit 0 /
> node --check per file, 0 fails. **Full suite on the FINAL tree: 4064 passed, 47 skipped,
> 2 xfailed (TEST-01 + JCL-BR-01), 0 failed, exit 0, 29:17** — 4064 = the (e) close's 4054
> + the 10 new persistence tests; every skip an environment-gated playwright skip.
> **Parity gate: 72 passed, 15 skipped (env-gated), exit 0, 14:40.** Installer lockstep
> 64/64 against the final v1.0.204 wheel. Drift guards green (rotation shape verified).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
