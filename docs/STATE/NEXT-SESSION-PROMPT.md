# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.143**, highest ADR **0327**; **PR-9b (#501) is
MERGED** as `a0a5bbd` — the rank-12 toolbar/read-me sweep is DONE, including the codex-review
addendum (population-accurate chips; `_target_panel` converted). Verify with
`git fetch --prune origin` and restart your branch from `origin/main`. Fresh container:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build` first.

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm `a0a5bbd` (#501) is main's ancestor and check whether
   the session-close docs PR is merged; restart your branch fresh from `origin/main`.
2. Then BUILD **PR-10 — OR-03 launch motion + synthesized hum** (`docs/STATE/PLAN-20260730.md`
   row 10; decisions recorded — do NOT re-ask): WebAudio synthesis, NO audio asset (wheel +
   nine installers stay lean); hum spans gesture→POST-resolution, fades ≤200 ms before
   navigation (cross-page audio out of scope, in the ADR); primed only in genuine gesture
   handlers (pick/folder/example-submit/drop — NOT `input.onchange`); shuffled-pitch-bag
   swell scheduler, all gains ramped; visible mute+volume on `.load-card`, persisted in
   localStorage (theme.js/sysmon.js/persist.js pattern); audible-at-low-gain default + the
   DESIGN-SYSTEM audio rule; motion = CSS-only orbiting craft dots (transform-only, token
   colors, zero JS — the pinned `_AUTOPLAY_JS` list stays untouched; reduced-motion gets its
   own `animation:none` BESIDE the pinned `.load-spinner{animation:none}` literal). Tests:
   `test_launch_sequence.py` (content) + `test_launch_audio_chromium.py` (float-tip skip
   posture; no context pre-gesture; mute persists; 4-theme × 2-viewport scrollbar-visible
   geometry).
3. Behind it: OR-04 park artifacts (`audit/VERIFICATION-REPORT-ollama-lifecycle.md` §8) ·
   SVG batch 3c · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering half, 74
   sites, Fable 5 Max) · Phase 4 (P1–P6) · rank 13/14. Known intermittent: the /analysis
   focus→tip test family (dismiss + scroll siblings) fails ~half of isolated runs —
   pre-existing, adjudicated in HANDOFF's carried list; do not chase it as a regression.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a
test; a fast wrong number is worthless) · ADR-0240 model/audit protocol · READ EVERYTHING,
ASSUME NOTHING, VERIFY EVERYTHING. Full gate before every commit; statics FOREGROUND first;
proved-able-to-fail on every new behavioral test; HANDOFF rotation + SESSION-LOG +
LESSONS-LEARNED same commit; wheel + nine installers ONCE after all code lands (bump the
version BEFORE launching the full background suite, or its installer-lockstep tests
red-herring against the stale wheel).
