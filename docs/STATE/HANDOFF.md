# Handoff — 2026-08-13 (f) (DoD 001b + 117 closed, then the private-repo fetch fix; ADR-0396/0397/0398; v1.0.201)

> ## STATUS (current) — **pushed, draft PR #586 open** on `claude/polaris-resume-ojz9q0`,
> branched from `main` **5a8003f**, then **merged `origin/main` 63457e7** when the parallel
> read-only audit (#585) landed mid-flight. Highest ADR now **0398**. **Shipped code changed** —
> version **v1.0.201**, wheel + nine installers rebuilt in lockstep. SCHEMA stays 2.11.0. New
> files: `src/schedule_forensics/ai/factory.py`, `tests/guards/test_observed_banner.py`, ADRs
> 0396/0397/0398. **The ADR-number collision the kickoff warned about HAPPENED**: this branch
> pushed its banner ADR as 0395 while #585 merged its own 0395 first — resolved in the merge
> commit by renumbering mine (banner 0395→**0396**, MPXJ pin 0396→**0397**; the installer-fetch
> ADR takes **0398**). Same-day section letters collided too — the audit's close is "(e)", this
> one is "(f)".
>
> ## THE REPO IS PRIVATE NOW — DISC-01's remediation, and it broke the installers' fetch
> Mid-session the repository flipped to **private** (the operator's remediation for #585's
> DISC-01: the gateway hostname + ITAR-tagged model id + patched-workstation description were
> published in a public repo; release determination REQUIRES AUTHORIZING OFFICIAL and the history
> question is still the operator's). Measured consequences: the installers' anonymous
> raw.githubusercontent MPXJ fetch 404s at EVERY ref including `main` (the identical smoke legs
> passed on #580 at 04:58Z while public), so PR #586's `linux`/`windows` legs went red on an
> unchanged code path. **Fix (ADR-0398):** the MPXJ fetch is now token-aware — with
> `SF_GITHUB_TOKEN` (operator) or `GITHUB_TOKEN` (CI's built-in) set, the download switches to
> the GitHub contents API (`Accept: application/vnd.github.raw+json`, PROVEN byte-identical
> against the manifest for the 3 MB poi jar before shipping); unset, it stays the anonymous raw
> URL (works if the repo is ever public again). `installer-smoke.yml` passes `github.token` to
> both legs. SHA-256 manifest verification is unchanged either way — bytes are proven, not
> transport. Per the audit's redaction discipline, the sensitive literals in THIS branch's new
> files were replaced with fictional placeholders (`gateway.agency.example`).
>
> ## What landed 1/3: DoD 001b (ADR-0396) — every sovereignty claim rides ONE observed derivation
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
> the page warned — and that is precisely the divergence the audit's GW-02 xfail encoded, so the
> merge FLIPPED `test_gw02_shown_banner_matches_routed_backend` from xfail-strict to a plain
> passing test, the module's designed loud flip) → `banner_for(config)` constructs the would-be
> candidates via the NEW `ai/factory.py` (constructors moved DOWN from `web/settings.py`;
> settings re-binds the names so every historic import path and per-call-site monkeypatch still
> works) and derives over primary AND cross-check second → `chrome._observed_banner(state)` adds
> the second veto: the session's actually-routed cached backend, re-derived — an injected
> non-local object can never sit behind a local banner. Consumers: the persistent banner, the CUI
> drawer (now a `{{ drawer_locality }}` template var), the home hero + empty-state takeaway, the
> settings tip, and BOTH exported exhibits — `brief_blocks(brief, *, ai_is_local)` (REQUIRED
> keyword, no default may assume local) and `_sra_report_blocks` via the `st` it already had.
> Local-state strings are byte-identical; the i18n catalog key + its four translations are
> untouched and now PINNED.
>
> ## Verification (QC-1) — 15/15 mutations caught by name, twice
> `tests/guards/test_observed_banner.py` (18 tests): route-level refusals, fail-closed
> presumption, exact-literal data pins (test-side constant + i18n-catalog-key pin),
> candidate/second/cache vetoes at page level via TestClient, export conditionals,
> instance-derivation pins. Red first: the probe confirmed all four defects by assertion on the
> pre-fix tree, and the module cannot even collect there (`ai.factory` absent). Teeth: a
> 15-mutation battery on a sandbox copy (PYTHONPATH shadow + canary + control + md5-identical
> instruments) — 15/15 caught by name, re-run against the final post-format tree so the reported
> result is the one that ships. One test moved with its call site
> (`test_second_backend_caches_and_handles_openai_construction` now patches
> `factory.OpenAICompatBackend`; verified live that the patched constructor is reached).
>
> ## What landed 2/3: DoD 117 (ADR-0397) — the MPXJ pin guard, because the trap FIRED ON THIS BUILD
> The mandatory installer rebuild's first attempt pinned **`a100184d`** — this container's own
> shallow-graft boundary (`.git/shallow` names it). The diagnosis REVERSED TWICE under
> measurement: first "my pin is right" (it was the artifact), then "the committed installers are
> broken — `poi-5.5.1.jar` didn't exist at `42d92dc`" (it did; a boundary commit's `--stat`
> invents additions), settled by tree hashes — `42d92dc`, `a100184d` and `HEAD` all carry the
> IDENTICAL `tools/mpxj` tree — and by the GitHub commits API (full history, `path=tools/mpxj`):
> the true last touch is **`42d92dc`**, exactly what the committed installers said. Nothing in
> the wild was ever broken. Fix: `mpxj_ref()` now REFUSES a graft-boundary resolution and accepts
> `SF_MPXJ_REF=<sha>` only after verifying tree-identity with the working tree (all three refusal
> paths exercised live); new `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact`
> went RED against the drifted build (3/3 families) and GREEN after the corrected rebuild. The
> shipped v1.0.201 installers pin `42d92dc` via the validated override.
>
> ## What landed 3/3: the #585 merge, reconciled
> Their audit module `tests/audit/test_audit_findings.py` rides this branch now: GW-02 un-xfailed
> (fixed here), SEC-01's `_ALLOWED_HOSTS` data pin landed BY the audit (the behavioural sweep +
> mutation proof per the 001a recipe remain open), TEST-01 / HOOK-01 / PO-03 xfails still encode
> their live defects. Both sessions' state-doc entries are preserved (theirs "(e)", this "(f)";
> both same-day letter sets collided — parallel sessions reconcile at MERGE time, not by naming
> discipline).
>
> ## Next — in order
> **DISC-01 release determination** (operator / authorizing official: the strings are in git
> HISTORY since `a19b969`; private visibility mitigates but does not decide releasability) →
> **001c** the operator's cloud/gateway decision (`APPROVED-GATEWAY-INTEGRATION.md` §6 steps 4–6;
> ADR-0396's chain makes the honest gateway wiring mechanical — a backend declaring
> `is_local=False` gets warning banners + export disclosures everywhere with no further plumbing)
> → HOOK-01's widened pre-commit boundary (renamed/double-ext/PDF/ZIP schedules; 19-case battery
> in the audit) → PO-03/04/05 parity-oracle gaps → `actual_start_driven` consumed nowhere →
> ADR-0391's own-calendar floor unguarded → TEST-01 chromium build-number pins (22 modules) →
> FINAL-REPORT overclaims (condition on `_observed_banner`, do not weaken) → 8 stale branches.
> **Operator:** DISC-01 · the 001c decision · FX-03/04 re-run · sub-day-negative-float Fuse run ·
> license.
>
> ## Carried forward
> ADR-0353..0398 closed — do not re-open. NEW lessons this session: **a diagnosis can reverse
> twice and still land — write down only what the LAST measurement proved**; **in a shallow
> clone, `git log -1 -- <path>`, `--stat` and `merge-base` can all agree on a falsehood** (the
> graft boundary owns every path; break the loop with an independent oracle — tree hashes, the
> remote commits API); **a CI failure on an unchanged code path is a question about the
> environment first** (the repo went private mid-flight; "flip it public" would have undone a
> deliberate security remediation — the installers learned an authenticated path instead);
> **condition a sovereignty claim on observation, not configuration, and route every surface
> through ONE derivation**; **the predicted ADR collision happened — `git fetch origin` before
> committing is what caught it; renumbering is merge-commit work**. Standing traps unchanged (a
> data pin guards the literal, not the guarantee · a standing rule is DATA · monkeypatch repoint
> is per CALL SITE · never MEASURE a tree a battery is mutating · never MUTATE an instrument a
> measurement is using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` ·
> `pytest -m parity` alone exceeds 900 s · the container starts with NO deps installed · `git
> fetch origin` before taking an ADR number and again before committing · a number written
> mid-session is not a measurement, `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> ruff check . / ruff format --check . / mypy --strict src / bandit / node --check: all green.
> Full suite on the SETTLED merged tree: see the final gate line in SESSION-LOG's (f) entry —
> re-run after the merge + fetch fix, reported from the run that ships. Installer suite green
> including the new pin-artifact test; `tests/audit` 21 tests with GW-02 now a plain pass.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
