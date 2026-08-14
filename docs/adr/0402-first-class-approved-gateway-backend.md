# ADR-0402 — The approved gateway becomes a first-class backend: 001c closes the plan's steps 4–6, and the operator gets the ITAR-model option the shipped build never had

**Status:** Accepted · **Date:** 2026-08-14 · **Extends:** ADR-0394 (allowlist pins), ADR-0396
(observed banner) · **Closes:** DoD 001c (`docs/PLAN/DEFINITION-OF-DONE-V2.md` Band 1;
`docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md` §6 steps 4–6) · **Supersedes:** the settings form's dead
`Cloud (UNCLASSIFIED only)` option.

## Context

The operator's report, verbatim: *"when I double click on the desktop icon to open the program … I
don't get the option to use the NASA approved AI models that are itar approved. Fix this."* 001c was
sized `human` — "decide the cloud option's fate: delete it, or build a first-class GatewayBackend" —
and this report **is** that decision: build it.

The pre-fix state was exactly the one the plan doc recorded (measured again here, QC-1 — a 7-check
acceptance probe run against the unpatched tree came back **7/7 RED**): no gateway option on the
settings page, no `ai/gateway.py`, no gateway allowlist, no `route_backend` branch, no transaction
log, no `kind=gateway` model probe, and the dead `cloud` option still rendering — the option that
falls closed to Null, which is why the only working route to the operator's NASA-approved gateway
(`proxy.fast.luna.nasa.gov`, serving ITAR-authorized Claude models) was an **unversioned local patch
that widens the loopback validator** — the exact edit ADR-0394's pins exist to catch. Steps 1–3 of
the plan's honest-integration sequence were already done (ADR-0394/0396); ADR-0396's consequences
section explicitly promised that a `GatewayBackend` with `is_local = False` would be "honest by
construction … no further plumbing" — a promise this ADR cashes.

## Decision

Build the gateway as its **own taxonomy** — never a widening of anything local, never a fallback,
never unrecorded, and always presented as remote:

1. **`net_guard.APPROVED_GATEWAY_ENDPOINTS`** — a new frozenset of exact `https` base URLs (one
   entry: the NASA gateway), with `is_approved_gateway_endpoint()` doing exact normalized-string
   match plus two structural re-checks (https-only; never loopback — a "local gateway" is a category
   error). The loopback sets are untouched; their ADR-0394 pins stay green unmodified.
2. **`ai/gateway.py` `GatewayBackend`** — OpenAI `/v1` wire format over the same stdlib
   no-proxy/no-redirect opener as the local backends; construction **raises `CUIEgressError`** for
   any endpoint off the allowlist; `is_local` and `is_approved_gateway` are **instance measurements**
   (ADR-0396 discipline), so every banner/export derived from the object reports the measured truth.
3. **`ai/txlog.py`** — the AI transaction log (plan step 5): every gateway HTTP request appends
   JSON-lines records (`*.sent` **before** transmission, `*.done` after) with timestamp, endpoint,
   model, classification, and for generations the prompt **SHA-256 + byte count — never the text**
   (the log must not itself become CUI). A failed `*.sent` write **aborts the transmission with the
   opener never invoked** (an unrecorded egress must not happen), and the same failure makes the
   availability probe read DOWN, so routing falls closed to Null end-to-end. Location:
   `$SF_AI_LOG_DIR` else `~/.local/state/schedule-forensics/ai-transactions.jsonl` — deliberately
   NOT the clear-on-quit cache dir (an audit record must outlive its session).
4. **Consent gates routing at every layer.** `AIConfig` gains `gateway_endpoint` (default `""`) and
   `gateway_approved` (default `False` — the operator's recorded assertion that the endpoint is
   organization-approved for the session's classification, ITAR/CUI included). `factory.gateway_or_none`
   returns `None` without selection + acknowledgment + allowlisted endpoint; `route_backend`'s new
   `gateway_backend` parameter/branch **re-requires** the acknowledgment and never serves the gateway
   for any other backend selection. The dead `cloud_backend` path is untouched and stays dead
   (`test_gw01_no_production_caller_wires_cloud_backend` still passes — the gateway is a separate
   parameter precisely so that scan keeps meaning something).
5. **The banner never softens by accident.** `banner_for_backend` emits the APPROVED-GATEWAY wording
   (endpoint named; "approval is operator-asserted, not verified by this tool; every transmission is
   recorded") only when the backend *measures* `is_approved_gateway` AND the config carries both
   arming fields; anything less falls through to the harsher generic non-local warning. An unarmed
   `backend == "gateway"` config warns under **every** classification via the extended intent
   warning (§0.2's over-fire direction — the operator one unchecked box away from egress must
   already be looking at a warning). `factory.session_candidates` includes the armed gateway, so a
   configured-but-unreachable gateway keeps warning.
6. **The settings page offers the option** (the operator's literal complaint): backend option
   "Approved AI gateway (remote — organization-approved, e.g. NASA ITAR-authorized models)"
   **replaces** the dead `cloud` option; the endpoint is a **select over the committed allowlist**
   (free text cannot even express an unapproved destination; the POST handler re-sanitizes; the
   constructor re-refuses — three layers, one source of truth); an acknowledgment checkbox that
   starts unchecked and arms only on its literal value; `_gateway_status_note` diagnostics for every
   non-serving state plus an honest ON state naming the egress and the log path; the explainer's
   Cloud section replaced with the gateway's (keeping "Data LEAVES this machine", adding the
   ATO-not-verified caveat); `/api/ai/models` gains `kind=gateway` (allowlist-checked **before** the
   backend is constructed); `settings.js` drives the live catalog dropdown for the gateway kind.
   `second_backend` can never be the gateway (the cross-check stays local-only by design).
7. **The air-gap guard evolves instead of being suppressed**: `test_airgap.py` exempts the approved
   endpoint as page **TEXT only** — a test-side literal, so widening the product allowlist goes red
   there until consciously mirrored — while the same URL in any fetchable position (src/href), or
   with any path suffix, stays an offender (`_REMOTE_ASSET` + the new two-edge test). CSP
   `connect-src 'self'` is unchanged: the browser never talks to the gateway; only the server does.

**Shipped code changed → v1.0.201 → v1.0.202**, wheel rebuilt, all nine installers regenerated
(ADR-0148 lockstep suite green, 64/64).

## Verification (QC-1) — red first, then 15/15 mutations caught by name

*Red:* the 7-check acceptance probe (above) 7/7 RED on the unpatched tree → 7/7 GREEN after.
*Teeth:* a sandboxed mutation battery (PYTHONPATH shadow of `src/`; import-origin canary; a canary
mutation proven observable; instruments md5-identical before/after; pristine-sandbox control green)
broke each protected property one at a time — **15/15 caught by the named test**:

`allowlist_widened` · `allowlist_narrowed` · `predicate_suffix_bypass` (data pin stays green — the
behavioural layer catches it) · `http_entry_added` · `consent_dropped_factory` ·
`consent_dropped_router` · `gateway_auto_fallback` · `log_after_send` (record order is *measured* by
the test's opener, not assumed) · `log_failure_swallowed` · `prompt_text_logged` ·
`is_local_hardcoded_true` · `wording_ignores_consent` · `post_sanitize_dropped` ·
`models_probe_unrestricted` · `airgap_exemption_prefix`.

One battery round found a real gap: `models_probe_unrestricted` initially **survived**, because the
backend constructor (defense-in-depth) also refuses off-list endpoints and its message contains the
word the assertion looked for — the outcome pin could not see the route layer's mutation. Closed with
a layer pin (`test_the_models_probe_refuses_before_constructing_the_backend`, a constructor bomb),
re-run, caught with a narrow 1-failed/15-passed split. *Lesson recorded: a defense-in-depth twin can
make a layer's mutation invisible to an outcome assertion — pin the layer, not just the outcome.*

*Render-verified (Tier 2, real chromium):* on a live server, the option renders, the Cloud trap is
gone, the endpoint select carries exactly the allowlist, the acknowledgment starts unchecked;
selecting the gateway backend + endpoint **fires** the `kind=gateway` catalog probe (fetch observed;
status span transitions measured on both sides); saving without the acknowledgment shows the intent
banner + "acknowledgment is required"; full arming through the real form shows the APPROVED GATEWAY
banner with the local assurance withdrawn, the honest could-not-reach diagnostic (this build
container's egress proxy 403s the host — on the operator's NASA-connected network this is where the
catalog populates, which their unversioned patch already demonstrated), and **the real app wrote
real `probe.sent/done` records to the default transaction log**. Console + daylight screenshots
taken; no new CSS was introduced (existing form tokens only).

## Consequences

- The operator's desktop icon now launches a build whose AI Settings offer the NASA-approved
  ITAR-model gateway behind three explicit steps, with honest banners, export disclosures
  (ADR-0396's chain needed no further plumbing, exactly as promised), and a durable local record of
  every transmission. The unversioned local patch — and the loopback-widening pressure it embodied —
  is obsolete: the honest path now exists in the product.
- Law 1's operative statement is now conditional where it was absolute: *no schedule content leaves
  the machine **except** through the operator-armed, allowlisted, logged, bannered gateway.* The
  allowlist entry remains an organizational assertion recorded in code — the tool enforces and
  records; it does not certify. DISC-01's standing exposure is unchanged in kind: the hostname this
  ADR ships in `net_guard` already appears in the public repo (plan doc §1, the ADR-0394 pin test).
- Growing the allowlist is a three-place conscious act: `net_guard` + its pin test + the air-gap
  text exemption — any partial edit is red.
- `tests/audit`'s GW-01 scan keeps its meaning (cloud stays dead); `test_route_banner_agrees…` and
  the whole observed-banner guard pass unmodified; the new gateway states get their own agreement
  pins in `tests/ai/test_gateway.py` and page-level pins in `tests/web/test_gateway_settings.py`.

## Deliberately NOT done

- **No gateway as cross-check second model** — the cross-check stays local-only by design
  (`factory.second_or_none` unchanged; pinned by `test_second_backend_can_never_be_the_gateway`).
- **No i18n catalog keys for the endpoint-interpolated warning texts** — same posture ADR-0396 took
  and for the same reason: the strings interpolate the endpoint, so they cannot be exact-match
  catalog keys; they render in English (translate.js is non-destructive) with the AI-fallback path
  available. A template-aware catalog is future work.
- **No config persistence across launches** — `AIConfig` remains per-process in-memory, so the
  acknowledgment is re-given each launch. That is the consent model working as intended, not a gap.
- **No `POLARIS_GATEWAY_ENDPOINT`/`POLARIS_GATEWAY_MODEL` env seeding** — the allowlist has exactly
  one entry and the form offers it directly; a second config channel would add attack/typo surface
  for zero clicks saved. Reconsider only if the allowlist ever grows.
- **The `cloud` plumbing in `ai/backend.py` stays** (route branch, intent warning, GW-01/GW-02
  pins): it is the generic refuse-path the tests exercise, it keeps old configs safe, and deleting
  it would churn security-adjacent history for no behavioural gain. Only the form option died.
- **The pre-existing answer-mode select overflow** on the settings page (long option text) predates
  this change and was left alone (UI-change scope discipline: one panel family per PR).
