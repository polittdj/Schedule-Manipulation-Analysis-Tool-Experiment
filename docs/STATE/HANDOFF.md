# Handoff — 2026-08-14 (e) (the gateway learns to authenticate: field-reported HTTP 401 → Bearer key support, credential-grade handling; ADR-0403; v1.0.203, wheel + nine installers rebuilt)

> ## STATUS (current) — ADR-0403 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`
> (restarted from `main` **175a744** = #590's squash after its merge). Highest ADR now
> **0403**. **SHIPPED code changed** — version **v1.0.203**, SCHEMA 2.11.0 unchanged, wheel
> + nine installers rebuilt (lockstep 64/64). xfails unchanged: TEST-01 + JCL-BR-01.
>
> ## What landed — ADR-0403 (field report, minutes after v1.0.202 deployed)
> The operator's screenshot from the real NASA machine: the ADR-0402 UI rendering exactly
> as designed, and the armed probe answered **HTTP 401** — DNS/TLS/network all fine, the
> gateway demands a credential the integration never sent. The plan doc §1 recorded the old
> unversioned patch as endpoint+model env vars ONLY; how it authenticated is UNVERIFIED —
> the auth dimension was missing from the recorded spec and only the field could reveal it.
> Built: **(1)** `AIConfig.gateway_api_key` (`field(repr=False)`; still in equality so a
> new key busts the routed cache). **(2)** `GatewayBackend(api_key=…)` sends
> `Authorization: Bearer <key>` on EVERY gateway request via a new 4-arg `GatewayOpener`
> contract (the local 3-arg `Opener` untouched); empty key sends NO header, never a bare
> `Bearer `. **(3)** the key never leaves the header: not in txlog, not in any page (input
> `type=password`, `value=""` always; placeholder discloses only whether a key is held),
> not in a repr, never in a URL (`/api/ai/models?kind=gateway` authenticates with the
> SESSION's resolved key server-side). **(4)** blank-means-keep in POST /settings (the
> masked field posts blank on every ordinary re-save; blank must not de-authenticate);
> ai-off/wipe/quit forget it. **(5)** `SF_GATEWAY_API_KEY` env fallback
> (`factory.resolve_gateway_api_key`, config-first) — a CREDENTIAL for the allowlisted
> destination, never a destination/model/consent (ADR-0402's no-seeding posture intact).
> **(6)** the 401/403 diagnostic now says what to DO (paste the organization-issued key —
> e.g. NASA AI Hub — into the Gateway API key field), not just the code.
> **Verification:** new tests RED first (17 failed by name on the pre-fix tree) → the
> affected sweep 242 passed; 8-mutant sandboxed battery **8/8 caught by name**
> (`header_dropped` · `header_always_sent` · `key_echoed_into_form` ·
> `blank_clears_instead_of_keeps` · `key_written_to_txlog` · `repr_leaks_key` ·
> `models_probe_unauthenticated` · `env_fallback_dropped`); instruments md5-identical.
>
> ## Next — in order
> **Operator: paste the AI Hub key into the new Gateway API key field (or set
> SF_GATEWAY_API_KEY) on the v1.0.203 install and confirm the catalog populates** — if it
> STILL 401s with a key, the gateway's auth scheme is not Bearer; capture what the AI Hub
> documents and a follow-on ADR adds that scheme on evidence → **DISC-01 release
> determination** (operator / authorizing official) → **PO-04/05** (BLOCKED on an
> operator-delivered CEI/HMI reference export) → `actual_start_driven` consumed nowhere
> (ENG-DEAD-01) → TEST-01 chromium build-number pins → **JCL-BR-01** (strict xfail flips
> loudly when fixed) → FINAL-REPORT overclaims (condition on `_observed_banner`) → JCL
> docs follow-ups (help.py τ term; EAC gloss scope) → 8 stale remote branches (DoD 091) →
> SMAT-SANDBOX branch-name cleanup (operator UI).
>
> ## Carried forward
> ADR-0353..0403 closed — do not re-open. NEW lessons this session: **a field 401 is a
> POSITIVE transport result** (DNS+TLS+answer) — diagnose the missing dimension, not the
> network; **an integration built faithfully to a recorded spec inherits the spec's
> gaps** — the plan doc recorded endpoint+model and never auth; record credentials'
> EXISTENCE (never their value) when documenting a working system; **a masked form field
> forces blank-means-keep POST semantics** — echo-never + blank-clears would silently
> de-authenticate on every unrelated save. Standing traps unchanged (see the (d) section
> in the archive for the full list — data pins vs guarantees · mutation-green vs
> adversarial · monkeypatch per CALL SITE · never measure a mutating tree · never mutate a
> measuring instrument · two ruffs, use `python -m ruff` · parity >900 s · container
> starts with NO deps · fetch before numbering and before committing · `wc` decides).
> QC-1/QC-2 are ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green: `python -m ruff check .` (All checks passed) / `python -m ruff format
> --check .` (1,009 files) / `python -m mypy src/` (154 files, no issues) / bandit exit 0 /
> node --check per file, 0 fails. **Full suite on the FINAL tree: 4054 passed, 47 skipped,
> 2 xfailed (TEST-01 + JCL-BR-01), 0 failed, exit 0, 22:34** — 4054 = the (d) close's 4043
> + the 11 new gateway-auth tests; every skip an environment-gated playwright skip.
> **Parity gate: 72 passed, 15 skipped (env-gated), exit 0, 10:51.** Installer lockstep
> 64/64 against the final v1.0.203 wheel. Drift guards green (rotation shape verified).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
