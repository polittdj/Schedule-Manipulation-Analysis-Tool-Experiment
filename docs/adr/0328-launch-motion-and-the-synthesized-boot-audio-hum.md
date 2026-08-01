# ADR-0328 — Launch motion + the synthesized Boot Audio Hum (OR-03)

Status: accepted (2026-08-01)
Implements: OPERATOR-REQUESTS.md OR-03 · PLAN-20260730 row 10 (decisions recorded there
2026-07-30 — WebAudio synthesis, gesture-only priming, CSS-only motion; this ADR executes,
it does not re-ask)
Builds on: ADR-0227 (the fetch-upload flow the hum rides), ADR-0195/DESIGN-SYSTEM (tokens,
reduced-motion posture), the theme.js/persist.js localStorage house pattern

## Context

OR-03 asked for two things on the Launch Sequence (the load overlay): visuals that keep moving
for the whole load — "something flying around", so a long import is unmistakably working and not
frozen — and a full-length Boot Audio "Hum" spanning the entire load, seamlessly mixed if
anything loops, at least a minute of material, never one repeating sound: *a series of similar
sounds, a pattern of the Hum*. No audio existed anywhere in the tool (verified this round:
zero `AudioContext`/`<audio>`/asset references in `src/`) — the Boot Audio Hum is **defined**
here, not extended.

The load ends in `window.location` (home.js navigates to the server's `{redirect}` after the
POST resolves), so cross-page audio is structurally out of scope: the browsing context that owns
the AudioContext dies at navigation. The plan recorded that honestly rather than hiding it — the
hum's scope IS the load phase (red-team R4).

## Decision

1. **The hum is synthesized WebAudio — no asset ships** (`static/launch_audio.js`, ~230 lines).
   A ≥60s OGG would have added ~10MB across the wheel + nine installers and still needed a
   seam-mixed loop; synthesis has **no loop point at all**, so "mix the audio correctly" is
   satisfied by construction. The sound: a low two-oscillator bed (55/55.7Hz, slow beating)
   under hum swells whose pitches come from a **shuffled bag** over an A-rooted consonant set
   (8 pitches, A2–A3) — every pitch sounds before any repeats, a refill never repeats the last
   pitch back-to-back, and swell spacing jitters 1.5–2.4s. That is the operator's "series of
   similar sounds, a pattern of the Hum": generative, indefinitely long (a minute-long load hums
   the whole minute; an hour-long one, the whole hour), never an audible cycle. A lookahead
   scheduler queues swells on the audio clock (~0.8s ahead) so timer jitter can never gap or
   stack the sound. **Every** level change — master fade-in, swell attack/release, mute/volume
   moves, every stop — is a `linearRampToValueAtTime` ramp; nothing steps (a stepped gain
   clicks). The vendored-ogg fallback stays HELD, per the plan, in case the operator's ear
   rejects the synthesis (their ear is the acceptance, red-team R6).

2. **Priming is gesture-only; the hum spans gesture → POST resolution; the fade is capped at
   200ms.** `prime()` (create/resume the AudioContext) is called from exactly four genuine
   gesture handlers in home.js — the pick button, the folder button, the example submit, and a
   window drop — and deliberately NOT from `input.onchange` (browsers may not treat `change` as
   user activation; a programmatic change therefore runs a fully silent load, asserted in
   chromium). `start()` refuses to create a context. On the fetch path the hum fades
   (`fadeOut(180)`, hard-capped at `FADE_CAP_MS = 200`) **before** `window.location` navigates —
   the redirect cuts silence, not sound; every error path (`preread` failure, nothing readable,
   upload failure) fades the hum down with the overlay; a BFCache restore hard-kills any revived
   graph on `pageshow`. The `/example` path is a native form navigation: its hum plays while the
   server imports and ends at unload — recorded, not hidden (the fade guarantee is a fetch-path
   property). All audio calls route through one guarded `hum()` helper so a missing/broken audio
   module can never block or break a load.

3. **Visible mute + volume live on the load card, persisted, audible-by-default.** `#humMute` +
   `#humVol` sit on `.load-card` (reachable the moment the overlay shows), persisted as
   `sf-hum-mute` / `sf-hum-vol` under the theme.js localStorage pattern (try/catch, `sf-*`
   keys). The default is LOW but audible gain (slider 40/100 into a squared perceptual curve,
   master ceiling 0.32) — the operator asked for audible-by-default, and WCAG 1.4.2 asks for a
   visible control, not silence. Moving the volume unmutes (OS convention). DESIGN-SYSTEM gains
   **§8 Audio** (synthesized-only · gesture-primed · fade-before-navigation · visible persisted
   controls · ramped gains · generative-over-loops) plus a DoD bullet pointing at it.

4. **The motion is CSS-only orbiting craft dots — zero JS.** Three dots (`--accent`/`--ok`/
   `--warn`, radii 56/42/61px, periods 2.8/4.6/6.7s, one reversed, one phase-shifted) orbit the
   existing spinner inside a new `.load-orbit` wrapper on the load card. The animation is
   **transform-only** (`rotate(...) translateX(var(--orbit-r))`), colors are theme tokens only,
   and neither JS file knows the orbit exists — so the pinned `_AUTOPLAY_JS` stepper list stays
   untouched (audio is not a motion stepper) and reduced-motion gets its own
   `@media (prefers-reduced-motion: reduce){.orbit-dot{animation:none}}` line BESIDE the pinned
   `.load-spinner{animation:none}` literal, which is unchanged.

## Consequences

* `launch_audio.js` joins `test_axis_titles.py`'s `EXEMPT` census bucket (a utility rendering
  no data visual) — the census forces that triage; nothing else in the freeze/census family
  moved (PAGE_SCRIPTS digests, the 18 axis call sites, `_AUTOPLAY_JS` all hold as-is).
* Cross-page audio (a hum that survives into the report pages) stays out of scope by the
  navigation boundary; if ever wanted it is a new operator decision (likely a persistent
  SPA-shell question, far beyond audio).
* The synthesis constants (pitch set, spacing, gains, envelope) are taste, pinned only loosely
  by tests (set size ≥6, jittered spacing, ramps present) — the operator's ear on the deployed
  build is the real acceptance; the held fallback is the recorded escape hatch.
* The `/example` path's at-unload cut is accepted (native navigation; a sub-second local import
  barely sounds regardless). If it ever grates, converting /example to the fetch path is the
  fix — a flow change deliberately NOT bundled into this round.

## Verification (all watched this round)

`tests/web/test_launch_sequence.py` (8 content tests: markup/CSS/JS text, transform-only
keyframes, token-only colors, the two reduced-motion lines side by side, assetlessness, the
shuffled-bag/lookahead markers, prime-count == 4 with onchange excluded, fade-before-navigation
ordering, the `_AUTOPLAY_JS` invariant, the DESIGN-SYSTEM §8 pin) +
`tests/web/test_launch_audio_chromium.py` (6 behavioral tests under the bundled chromium:
zero contexts pre-gesture and a silent programmatic-change load; one context per gesture with
the hum RUNNING across a held POST and an orbit dot measurably moving between samples;
`fadeOut(99999)` resolving <1.5s proving the 200ms cap; mute/volume persisting across a
navigation and a reload; card geometry in 4 themes × 2 viewports with scrollbars visible).
**Proved able to fail: 13 of 14 FAIL on the stashed pre-change tree; the one both-tree pass is
the `_AUTOPLAY_JS` pin equality (an invariant guard). Post-change: 14 passed.**
