# ADR-0404 — AI settings persist across launches: armed once, the desktop icon just works

**Status:** Accepted · **Date:** 2026-08-15 · **Extends:** ADR-0402/0403 · **Supersedes:**
ADR-0402's "no config persistence across launches — per-launch acknowledgment IS the consent
model" (an operator-revisit clause that has now been exercised).

## Context

Operator directive, verbatim: *"I do not want to have to put in the NASA API KEY everytime I
open the program. I want it to work when I click on the desktop icon. Super simple."*

Under v1.0.203 every launch started from `AIConfig()` defaults: the operator re-selected the
gateway backend, the endpoint, the model, re-checked the acknowledgment, and re-entered (or
env-var'd) the key — five steps before the first question. ADR-0402 chose that deliberately
("per-launch acknowledgment IS the consent model") and marked it *"revisit only on operator
ask"*. This is the ask, and it is broader than the key alone: persisting only the key would
still leave four re-arming steps, which is not "it works when I click the desktop icon."

## Decision

**The whole AI configuration persists on the machine** (`ai/config_store.py`), and the
desktop-launch path loads it at startup:

1. **Store:** a small JSON document — backend, endpoints, model, qa/second-model settings,
   timeout, `gateway_endpoint`, `gateway_approved` — at `$SF_SETTINGS_DIR` else
   `~/.local/state/schedule-forensics/ai-settings.json` (beside the transaction log,
   deliberately OUTSIDE the clear-on-quit cache dir). It contains **no schedule content,
   ever** — operator configuration only, so it can never become CUI and Law 1's at-rest
   rules for schedule data are untouched.
2. **The credential is never plaintext at rest where an OS protector exists.** On Windows
   the key is DPAPI-wrapped (user scope, ctypes — stdlib only, no new dependency) into
   `gateway_api_key_dpapi`; **a failing protector omits the key entirely** (fail closed on
   the credential, fail soft on convenience — never a silent plaintext downgrade). On POSIX
   it is stored under the honestly-named `gateway_api_key_plain` in a 0600 file — the same
   protection class as the `SF_GATEWAY_API_KEY` user env var it substitutes for (which
   still works, config-first).
3. **Loading is a trust boundary.** The file is operator-editable state, so loading
   re-applies the POST sanitizers: a gateway endpoint off
   `net_guard.APPROVED_GATEWAY_ENDPOINTS` clears to "" (a hand-edited file can never
   smuggle a destination), non-loopback local endpoints fall back to defaults, enums fall
   back safe, the timeout clamps, an unprotectable stored key yields keyless. Missing or
   corrupt files yield pure defaults — a launch never fails on settings.
4. **Wiring:** `create_app(state=None)` — the launcher path — builds
   `SessionState(ai_config=load_ai_config())`; an explicitly injected state (tests,
   embedders) is never touched. `POST /settings`, `POST /settings/ai-off`, and the session
   wipe persist their result (best-effort; a failed save logs and the session continues) —
   so OFF is a setting too, and a stale file can never re-arm past an explicit off.
5. **Consent remains explicit, recorded, and revocable** — it is now recorded *durably*
   instead of re-asked: the acknowledgment is checked once and stays until changed; every
   transmission is still individually recorded in the transaction log; the warning banner
   never depended on session freshness and still renders on every armed launch; unchecking,
   ai-off, or wipe persists the disarmed state. The suite's conftest gained
   `SF_SETTINGS_DIR`/`SF_AI_LOG_DIR` isolation so no test touches the operator's real state
   dir (the same contract the schedule cache has had since v4).

**Shipped code changed → v1.0.203 → v1.0.204**, wheel + nine installers rebuilt (lockstep
64/64). The settings page copy is updated (the key field no longer claims quit-forgets; the
acknowledgment names its persistence; the footer states the persistence rule).

## Verification (QC-1)

Store tests written first; a 6-mutant sandboxed battery (same rig; instruments md5-identical)
supplied the reds — **6/6 caught by the named test**: `launch_does_not_load` ·
`post_does_not_persist` · `load_skips_allowlist` · `protector_failure_stores_plain` ·
`chmod_dropped` · `disk_overrides_injected_state`. The operator acceptance test simulates two
launches as two independent app instances sharing only the settings file: arm once in the
first, and the second — built with no injected state, exactly the desktop path — comes up
routed to the gateway, acknowledgment checked, key held (and never rendered). Affected sweep
+ full gate figures in the handoff.

## Deliberately NOT done

- **No DPAPI testing in CI** (no Windows pytest job): the DPAPI branch is minimal ctypes
  around two Win32 calls, `# pragma: no cover`, and the *contract* around it — wrapped-key
  round-trip, never-plaintext, fail-closed omission — is fully tested via injected
  protectors. Field verification on the operator's machine is the acceptance path.
- **No multi-profile / per-project settings** — one machine, one operator, one file.
- **No keyring/credential-manager integration** — DPAPI covers the deployed platform with
  zero dependencies; revisit only if a non-Windows deployment materializes.
