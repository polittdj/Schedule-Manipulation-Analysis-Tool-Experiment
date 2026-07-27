# VOICE-DECISION — how the welcome greeting speaks (DECISION DOC, awaiting approval)

**Nothing has been built.** PROMPT 4 §1 requires the comparison and a stop. Governing law: repo `CLAUDE.md` Law 1 — air-gap absolute, no remote asset, no network call, std-lib-only runtime I/O. That applies to audio identically to fonts.

Every one of the three named hazards is addressed by name in §4. All figures in §2 are computed, not estimated; the arithmetic is shown so you can audit it.

---

## 1. What has to be true

The greeting is: *"Hello and welcome back to Astrolabe. How may I serve you today?"* — ~3.4 s at conversational pace — in **four selectable voices**: Australian female (default), Australian male, Latin-American-accented English female, Latin-American-accented English male. Picker persisted, **default OFF**, greeting **only ever behind an explicit click**.

---

## 2. Option (a) — runtime Web Speech API

Zero payload. `speechSynthesis.getVoices()` at runtime, one utterance per click.

**This has already been tested, in the prototype, and it failed the accent requirement outright.** On the machine the ASTROLABE prototype was exercised on, the browser reported **three** installed voices — *Microsoft Zira*, *Microsoft Mark*, *Microsoft David*, all `en-US`. **Zero `en-AU` voices. Zero `es-*` voices.** With a scoring-and-claiming allocator (best locale → gendered-name → each voice claimed once) the four options resolved to three distinct voices, and the two Latin-American options had to share one, differentiated only by pitch/rate. The Australian option was an American voice at pitch 1.34.

That is the honest ceiling of option (a): **on a stock Windows install you get American English, and the requested accents do not exist.** Additional Windows voices are an OS-level install (Settings → Speech), not something the app may fetch — fetching would break Law 1.

| | |
|---|---|
| Installer cost | **0 bytes** |
| Accents guaranteed | **No.** Availability is a per-machine lottery; `en-AU` and `es-419` are absent from a default Windows 11 install |
| Air-gap | Clean — OS-local synthesis, no network. (Note: some Edge/Chrome voices are *cloud* voices; those must be filtered out by `voice.localService === true`, or the app leaks text off-machine — a Law 1 violation hiding in this option) |
| Consistency | None — a briefing sounds different on every workstation |
| Failure mode | Silent, or a caricature (an American voice pitched up and called "Australian") |

## 3. Option (b) — four pre-generated clips, vendored

Four short files under `web/static/audio/`, played by `<audio>` on click. Guaranteed to sound exactly as approved, on every machine, forever.

### 3.1 Exact size, computed

Per clip = 3.4 s × bitrate ÷ 8. Base64 inflation in each installer = ×4/3. The wheel is a zip, but already-compressed audio does not compress further, so treat the wheel delta as the raw size.

| Encoding | per clip | 4 clips on disk | base64 in one installer | **across 9 installers** |
|---|---|---|---|---|
| **Opus 24 kbps mono** | 10.0 KB | **39.8 KB** | 53.1 KB | **0.47 MB** |
| Opus 32 kbps mono | 13.3 KB | 53.1 KB | 70.8 KB | 0.62 MB |
| AAC-LC 32 kbps mono (`.m4a`) | 13.3 KB | 53.1 KB | 70.8 KB | 0.62 MB |
| MP3 64 kbps mono | 26.6 KB | 106.3 KB | 141.7 KB | 1.25 MB |
| WAV 16-bit 22.05 kHz mono | 146.4 KB | 585.7 KB | 780.9 KB | **6.86 MB** |
| **Dual-encode: Opus 24k + AAC 32k (8 files)** | — | **93.0 KB** | 124.0 KB | **1.09 MB** |

Sanity check against the hazard as stated: 1 MB of audio → **12.0 MB** across nine installers. The rule of thumb holds; the point is that **speech at 3.4 s does not cost megabytes.** Dual-encoded for codec safety the whole feature is **93 KB on disk and ~1.1 MB across all nine installers** — about 0.1 % of a wheel that already embeds the entire application.

Why dual-encode: Chrome/Edge/Firefox play Opus in `.ogg`; Safari's Opus support is unreliable and the macOS installer (`install-tier{1,2,3}.command`) means Safari is a real target. AAC-LC in `.m4a` covers Safari. Ship both, let `<audio>` pick via two `<source>` elements. If you decide macOS is out of scope, drop to Opus-only: **39.8 KB / 0.47 MB across installers.**

### 3.2 The open question in (b): who records the four clips

This is the only real cost, and it is a licensing question, not a technical one.

| Source | Sounds right? | Redistribution licence | Verdict |
|---|---|---|---|
| **Human speakers** (2 AU, 2 LatAm-accented English) reading one 12-word line | Best — genuinely accented, warm | Clean with a one-page performer release for perpetual internal + product use | **Recommended.** 4 × 3-second lines; a single short session, or four colleagues on their phones |
| **Local open-source TTS at build time** (e.g. Piper) | Good; depends entirely on whether an `en_AU` and a Spanish-accented-English model exist at acceptable quality | Model-by-model — most Piper voices derive from CC-BY / public-domain corpora; **each model's licence must be checked individually before it ships** | Acceptable fallback if no speakers are available; needs a licence check per voice |
| **Windows SAPI / macOS `say` rendered at build time** | Same American voices as option (a) | **Blocked** — Microsoft and Apple voice EULAs restrict redistributing rendered output | **Do not use** |
| **Cloud TTS** (any vendor) rendered at build time | Excellent | Vendor-specific; several forbid redistribution or require attribution in-product | Only with your legal sign-off; also uncomfortable next to a CUI-marked air-gapped tool |

Runtime is air-gap clean in every case — the file is played from `/static/`, same origin, no network.

---

## 4. The three hazards, addressed explicitly

1. **Autoplay is blocked without a gesture.** Neither option ever plays on load. The picker defaults to **OFF**; the greeting plays only from an explicit "▶ Hear the greeting" / "Begin" click, and the welcome sequence renders and animates identically whether audio is on, off, or unavailable. Nothing in the sequence waits on `play()`, and its promise rejection is caught and ignored (a rejected `play()` must never surface as an error).
2. **OS voices are a lottery.** Under (b) this hazard disappears for the four shipped voices. It still applies to the *fallback* path (§5), which is why the fallback must **enumerate and disclose** rather than pretend: filter `voice.localService === true`, score by locale, print the voice actually used, and say plainly when the requested accent is not installed. The prototype's own disclosure line is the pattern: *"no en-AU voice is installed here; the nearest English voice is used"*.
3. **Installer weight.** Budgeted in §3.1: **0.47 MB** (Opus-only) or **1.09 MB** (dual-encoded) across all nine installers, and the number goes in the PR description. Hard budget: **if the four clips exceed 150 KB on disk, stop and re-encode** — that is the tripwire, not a post-hoc discovery. `tests/installer/test_installers.py` must be re-run in the same commit because the embedded wheel changes (lockstep, ADR-0148).

---

## 5. Recommendation

**Option (b), dual-encoded Opus + AAC, four human-recorded clips — with option (a) as the degradation path, not the default.**

Reasoning, in order of weight:

1. **(a) cannot satisfy the requirement.** The accents are the requirement, and they are absent from a default Windows install — measured, not assumed. Shipping (a) alone means shipping an American voice labelled "Australian".
2. **The cost objection does not survive arithmetic.** 93 KB / 1.09 MB across nine installers is noise beside a wheel that embeds the whole app.
3. **Determinism matches the product.** This tool's entire value proposition is that output is reproducible and defensible. A greeting that sounds different on every workstation is off-brand in a way a schedule-forensics tool cannot afford.
4. **(a) has a latent Law 1 defect** — cloud voices in Chromium send text off-machine. Under (b) that risk is structurally absent.

### Degradation ladder (never a broken experience)

```
clip present + audio enabled  ->  play the vendored clip
clip missing (dev checkout)   ->  Web Speech, localService voices only, with the
                                  "requested accent not installed" disclosure
no speech engine / audio off  ->  SILENT. Greeting renders as on-screen text, styled
                                  as the spoken line, with a "voice unavailable" note
any failure at all            ->  the welcome sequence and the app continue normally
```

The greeting text is **always** on screen regardless of audio state, so the sequence is never audio-dependent. Audio is an enhancement; the words are the content.

---

## 6. What step 2 will build, once approved (constraints locked now)

- **Reuse `globe.js`** (282 lines, canvas wireframe Earth with `devicePixelRatio` handling) as the Earth. No second Earth. The Mars body and the transfer arc are added to that same canvas; the existing insignia/status-light usage is untouched.
- **`prefers-reduced-motion`: kills the animation *and* the timers** (DESIGN-SYSTEM §7) — no `requestAnimationFrame` loop, no `setTimeout` chain, no auto-advance. The sequence renders as a **single static frame** with the greeting text and the Continue control.
- **Never blocks startup.** The sequence mounts after first paint, inside a `try`; if it throws, is unsupported, or the canvas is unavailable, it is removed and the app opens at its normal landing. No await, no gate, no spinner. Skippable at all times ("Skip →"), dismissible for good, state in `localStorage["sf-welcome"]` alongside `sf-theme` / `sf-guided`.
- **Voice picker**: 4 options, `localStorage["sf-voice"]`, **default OFF**, with the currently-selected voice named on screen.
- **Air-gap test stays green**: all audio from `/static/audio/`, same-origin; add an assertion that no `<audio>`/`<source>` `src` leaves `/static/`. `pyproject.toml` package-data must include `web/static/audio/*`.

---

## STOP — four decisions needed

1. **Option (a) or (b)?** My recommendation is (b) with (a) as fallback.
2. **If (b): who records?** Four colleagues reading one 12-word line is the cheapest clean path; otherwise I specify the Piper models and you approve their licences.
3. **macOS in scope?** Yes → dual-encode, 93 KB / 1.09 MB. No → Opus-only, 39.8 KB / 0.47 MB.
4. **Exact wording to record** — confirm the line, since re-recording later costs another session:
   *"Hello and welcome back to Astrolabe. How may I serve you today?"*
   (Note: the product name in the repo is **Schedule Forensics**; "Astrolabe" is the design-side name from the prototype. Tell me which name is spoken, because it is baked into the clips.)

No code until these are answered.
