# ADR-0395 — The sovereignty banner is observed, not config-derived: every locality claim now rides one derivation

Status: accepted (2026-08-13). Closes **DoD 001b** (`docs/PLAN/DEFINITION-OF-DONE-V2.md`;
`APPROVED-GATEWAY-INTEGRATION.md` §6 steps 2 and 3). `src/` changed — **v1.0.201**, wheel and
installers rebuilt. Extends ADR-0394 (001a pinned the validator's data; this makes the *claims*
consult the validator's verdict).

## Context

POLARIS's on-screen sovereignty assurance — `Local-only — no data leaves this machine.` — was
**derived from configuration, never from observation**. Four defects, each *measured by an executed
probe on the pre-fix tree* (QC-1; not inherited from the audit):

| # | Defect | Measured on `main` @ 5a8003f |
| --- | --- | --- |
| D1 | `route_backend` returned the literal local Banner for whatever object arrived through its `ollama`/`openai` parameters — no locality inspection, no read of `is_local` | a fake with `is_local=False`, `endpoint=https://proxy.fast.luna.nasa.gov` routed on **both** paths under the banner `Local-only — no data leaves this machine.` |
| D2 | The rendered page banner was `banner_for(config)` — config only (`chrome.py:175`); `route_backend`'s Banner was discarded by both production callers (`web/app.py:838`, `web/settings.py:346`) — dead code, exactly as the audit said | the same fake sitting in `SessionState.backend_cache` still rendered `<div class="banner local">Local-only — …</div>` |
| D3 | `brief_blocks` printed "Generated locally by POLARIS…" into the exported Word exhibit with **no parameter that could carry a locality verdict** | `signature = (brief)` — one positional, nothing else |
| D4 | `is_local` was a **class constant** `True` on both HTTP backends — an assertion, not a measurement; the only read anywhere was `_UseMarking` copying it | `"is_local" in vars(OllamaBackend)` and `vars(OpenAICompatBackend)` — both true |

The audit's claim table was re-verified line by line (QC-2): all six user-visible claim sites hold,
with two anchors drifted (`web/app.py` 1299→1305 and 1396→1402; content intact). One refinement to
the audit's wording: `is_local` **is** read once — `web/settings.py:99`, the `_UseMarking` wrapper
copying it for protocol conformance — but nothing ever *branched* on it, which is the defect that
matters. The two exported-exhibit sites (`ai/brief.py:625`, `web/sra.py:1076`) print locality
*prose*, not the banner literal — "Generated locally by POLARIS…" and "All computation is local and
offline…" — unconditional assurances inside documents built to leave the machine.

Why this matters is ADR-0394's scenario: in a patched install with the gateway armed, every one of
these sentences renders while schedule content transits `proxy.fast.luna.nasa.gov`. As shipped the
claims are true; they were **unconditional where they should be conditional**, and no in-repo test
could make any of them go red.

## Decision

**One derivation, consulted by every claim.** The chain, bottom-up — each link observes the link
below rather than asserting independently:

1. **`is_local` is a measurement** (`ai/ollama.py`, `ai/openai_compat.py`): the constructor records
   the loopback validator's verdict on the *actual endpoint* as an instance attribute; the class
   constants are gone. Post-guard it is always `True` today — the point is *provenance*: if the
   fail-closed raise is ever weakened, every banner derived from that object reports the measured
   truth instead of a label. `NullBackend` keeps `is_local = True` — no endpoint, no transport;
   local by construction is honest for it.
2. **`banner_for_backend(backend, config)`** (`ai/backend.py`) is the single derivation core: a
   backend is local **only if it itself proves it** (`is_local` literally `True`; a missing or
   falsy attribute is presumed NON-local — fail closed). Non-local ⇒ a warning naming the endpoint,
   with a distinct, harsher wording when the project is CLASSIFIED. The §0.2 *intent* warning
   (UNCLASSIFIED + cloud ⇒ "AI **may** send…") survives as `_intent_cloud_warning` — the warning
   direction may over-fire; the assurance may not.
3. **`route_backend` returns that derivation over the backend it actually chose** on every path —
   its Banner stopped being dead code and became the same claim the page makes. One deliberate
   behaviour change: UNCLASSIFIED + cloud with **no** cloud backend previously returned the *local*
   banner from routing (while the page showed the warning — the two disagreed and nobody could see
   it); both now warn.
4. **`banner_for(config)` constructs and observes.** The backend constructors moved DOWN from
   `web/settings.py` to a new **`ai/factory.py`** (`ollama_or_none`, `openai_or_none`,
   `second_or_none`, `session_candidates`) so the ai layer — and the chrome above it — can build
   the exact candidates the router uses. `banner_for` derives over every constructible candidate,
   **including the cross-check second model** (it receives every prompt too). Availability is
   deliberately not consulted: a configured-but-down non-local endpoint must keep warning, and
   among local backends availability only changes *which* local backend serves, never the banner's
   truth.
5. **`_observed_banner(state)`** (`web/chrome.py`) is the page-level chokepoint: the candidate
   derivation **plus** a veto from the session's actually-routed backend
   (`SessionState.backend_cache`, config-matched) re-derived through `banner_for_backend` — so a
   non-local object that reached the routing cache by *any* path can never sit behind a local-only
   banner. The assurance renders only when both observations agree.
6. **Every absolute claim now rides `_observed_banner`**: the persistent banner (`_banner_html`),
   the CUI drawer sentence (now a `{{ drawer_locality }}` template variable), the home hero
   ("entirely on your machine" / "nothing leaves this computer"), the empty-state takeaway, the
   settings tip, and both exported exhibits. `brief_blocks` takes a **required** keyword
   `ai_is_local` — no default may quietly assume local — and `_sra_report_blocks` derives from the
   `st` it already receives. In the local state every string is byte-identical to before (the i18n
   catalog key and its four translations are untouched and now pinned); the non-local texts
   disclose the split honestly — engine computations local, AI endpoint external.

### Verification (QC-1) — red first, then 15/15 mutations caught by name

*Red:* an executed probe on the pre-fix tree confirmed all four defects by assertion (the table
above), and the new guard module cannot even collect there (`ai.factory` does not exist). *Control:*
the unmutated fixed tree runs the guard **18/18 green**.

*Teeth:* a mutation battery on a sandbox copy of the fixed `src/` (PYTHONPATH shadow; canary proved
a sandbox mutation changes the measured outcome; the instrument files md5-identical before/after;
**re-run against the final post-format tree** so the reported result is the one that ships) broke
each link one at a time — **15/15 caught by the named test**:

`route_constant_banner` · `bannerfor_config_only` · `getattr_default_true` (fail-open presumption) ·
`intent_warning_dropped` · `islocal_class_constant` · `second_dropped` · `cache_veto_dropped` ·
`drawer_unconditional` · `hero_unconditional` · `takeaway_unconditional` · `brief_default_true` ·
`brief_ignores_flag` · `sra_unconditional` · `tip_unconditional` · `literal_reworded` (the exact
literal + the i18n-catalog-key pin).

One pre-existing test moved with its call site: `test_second_backend_caches_and_handles_openai_construction`
patched `settings.OpenAICompatBackend`; construction now lives in `ai/factory.py`, so the patch
follows (monkeypatch repoint is per CALL SITE) — verified live by a probe showing the patched
constructor is called exactly once. `tests/ai/test_brief.py` gained the required
`ai_is_local=True` argument.

## Consequences

- A future `ai/gateway.py` `GatewayBackend` with `is_local = False` (001c, if the operator chooses
  to build it) is **honest by construction**: routed through any parameter, it gets a warning
  banner naming its endpoint on every page and a disclosure in every export — no further plumbing.
- The patched-install scenario is now *architecturally* covered to the validator's boundary: the
  banner chain trusts `is_local`, `is_local` records the validator's verdict, and ADR-0394 pins the
  validator's data and behaviour. What remains out of reach in-repo is a patch that hardcodes
  `is_local = True` on a remote-pointing class — no in-repo test can see a patched install by
  definition; the honest path now existing is the defense (§3 of the gateway doc).
- The layering holds: `chrome → state → ai` only (`ai/factory` sits below the whole view layer);
  `settings.py` re-binds the constructor names so every historic import path and per-call-site
  monkeypatch keeps working; `app.py` re-exports `_observed_banner` with the `X as X` idiom
  (`test_monolith_split_contract` green).
- The i18n catalog is untouched: the local literal (and its es/fr/de/pt translations) survive
  byte-identical, now pinned by `test_the_local_literal_is_still_the_i18n_catalog_key`.

## Deliberately NOT done

- **The non-local warning texts have no catalog translations.** Every non-local state is
  unreachable in-repo (the constructors refuse remote endpoints), so the strings can only render in
  a patched install or after 001c wires a gateway; the AI-fallback translation path covers them
  until 001c adds proper keys. Adding catalog entries for unreachable strings now would pin wording
  001c is likely to revise.
- **`screen_head`'s "Every file parses on this machine; nothing is uploaded" and the brief's
  "How to verify" sentence stay unconditional** — both were read and judged TRUE regardless of AI
  backend: parsing and every brief figure are engine-local; the AI never computes them.
- **`web/settings.py:328`'s "Data LEAVES this machine." cloud explainer stays** — static education
  copy about an option, correct as written.
- **`_active_backend` / `_settings_body` still discard `route_backend`'s Banner** at the call
  sites. It is no longer dead *code* — the same derivation now feeds the renderer, and
  `test_route_banner_agrees_with_the_config_banner_for_every_local_state` pins the two ends
  together — but threading the tuple through the TTL cache was measured as pure churn: the
  page-level chokepoint reads the cached *backend* and re-derives, which is strictly stronger
  (it also sees an injected object the router never blessed).
- **001c is untouched**: the dead `cloud` settings option, `ai/gateway.py`, the gateway allowlist,
  the classification gate and the AI transaction log remain the operator's decision (§6 steps 4–6).
- **The `_ALLOWED_HOSTS` pin (`web/app.py:1076`)** — same defect class, different property
  (request admission) — remains the next cheap pin, unchanged from ADR-0394's finding.
