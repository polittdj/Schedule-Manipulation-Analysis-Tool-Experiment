/* Schedule Forensics — the Launch Sequence "Boot Audio Hum" (OR-03, ADR-0328).
 *
 * A SYNTHESIZED WebAudio hum that rides the load overlay: it starts when a load begins, runs for
 * the entire import (a minute-long load hums for the whole minute), and fades out — never a hard
 * cut — at most 200ms before the post-load navigation. No audio asset exists anywhere: the sound
 * is generated locally by this file (Law 1 stays trivially true, and the wheel/installers carry
 * zero media bytes). Because the hum is GENERATIVE there is no loop point and therefore no seam
 * to mix: swell pitches come from a shuffled bag (every pitch sounds before any repeats, and a
 * refill never repeats the last pitch back-to-back), so the operator hears a series of similar
 * sounds — a pattern of the Hum — not one repeating sample.
 *
 * Autoplay policy: an AudioContext is created/resumed ONLY inside prime(), and home.js calls
 * prime() only from genuine user-gesture handlers (the pick/folder buttons, the example submit,
 * a drop). start() REFUSES to create a context — a load that arrives with no primed context
 * (e.g. a programmatic file change) is a silent load, by design, never a console warning.
 *
 * Controls: the load card carries a visible mute button + volume slider (WCAG 1.4.2 — sound that
 * starts automatically gets a visible off-switch; the operator asked for audible-by-default, so
 * the default is a low but audible gain, not silence). Both persist in localStorage under the
 * house pattern (sf-hum-mute / sf-hum-vol; cf. theme.js's sf-theme / sf-scale).
 */
"use strict";

(function () {
  var MUTE_KEY = "sf-hum-mute"; // "1" = muted (persisted operator choice)
  var VOL_KEY = "sf-hum-vol"; // "0".."100" slider position
  var DEFAULT_VOL = 40; // audible-at-low-gain default (operator decision, plan row 10)
  var MAX_GAIN = 0.32; // master ceiling at slider 100 — an ambience, never a foreground sound
  var FADE_CAP_MS = 200; // no stop may ramp longer than this (the pre-navigation ceiling)

  var ctx = null; // created ONLY in prime() — i.e. only inside a real user gesture
  var master = null, bedNodes = null, timer = null;
  var state = "idle"; // idle | running | fading | closed
  var bag = [], lastPitch = 0, nextAt = 0;

  // A-rooted consonant set (A2..A3): the swells stay recognizably "the same hum" at different
  // heights — the operator's "series of similar sounds", not eight unrelated tones.
  var PITCHES = [110, 123.47, 130.81, 146.83, 164.81, 174.61, 196, 220];

  function stored(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function persist(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* in-page only */ } }

  function volume() {
    var v = parseInt(stored(VOL_KEY) || "", 10);
    return isNaN(v) ? DEFAULT_VOL : Math.max(0, Math.min(100, v));
  }
  function muted() { return stored(MUTE_KEY) === "1"; }
  function targetGain() {
    var v = volume() / 100;
    return muted() ? 0 : v * v * MAX_GAIN; // squared: sliders are perceptual, gains are linear
  }

  function swallow(p) { if (p && p.catch) p.catch(function () { /* context refused; stay silent */ }); }

  function prime() {
    if (ctx) {
      if (ctx.state === "suspended") { try { swallow(ctx.resume()); } catch (e) { /* stays primed-suspended */ } }
      return;
    }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    try {
      ctx = new AC();
      if (ctx.state === "suspended") swallow(ctx.resume());
    } catch (e) { ctx = null; }
  }

  function shuffledBag() {
    var b = PITCHES.slice();
    for (var i = b.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = b[i]; b[i] = b[j]; b[j] = t;
    }
    // nextPitch() pops from the END: if a refill would repeat the last swell, swap it deep
    if (b.length > 1 && b[b.length - 1] === lastPitch) {
      b[b.length - 1] = b[0]; b[0] = lastPitch;
    }
    return b;
  }
  function nextPitch() {
    if (!bag.length) bag = shuffledBag();
    lastPitch = bag.pop();
    return lastPitch;
  }

  function swell(at, freq) {
    // One hum swell: a sine fundamental + a quiet detuned octave through a lowpass. The
    // envelope is RAMPED at both ends — a stepped gain clicks; nothing here steps.
    var env = ctx.createGain();
    env.gain.setValueAtTime(0, at);
    var lp = ctx.createBiquadFilter();
    lp.type = "lowpass"; lp.frequency.value = 900; lp.Q.value = 0.5;
    var o1 = ctx.createOscillator(); o1.type = "sine"; o1.frequency.value = freq;
    var o2 = ctx.createOscillator(); o2.type = "sine"; o2.frequency.value = freq * 2;
    o2.detune.value = 7;
    var mix2 = ctx.createGain(); mix2.gain.value = 0.22;
    o1.connect(lp); o2.connect(mix2); mix2.connect(lp);
    lp.connect(env); env.connect(master);
    env.gain.linearRampToValueAtTime(0.5, at + 0.5); // attack
    env.gain.linearRampToValueAtTime(0.0001, at + 1.65); // release
    o1.start(at); o2.start(at);
    o1.stop(at + 1.75); o2.stop(at + 1.75);
  }

  function schedule() {
    // Lookahead scheduler: keep ~0.8s of swells queued on the AUDIO clock, so the setInterval
    // below only tops the queue up — timer jitter can never gap or stack the sound.
    while (nextAt < ctx.currentTime + 0.8) {
      swell(nextAt, nextPitch());
      nextAt += 1.5 + Math.random() * 0.9; // 1.5–2.4s spacing: a pattern, not a metronome
    }
  }

  function start() {
    // Never creates a context (priming is a gesture-only act): un-primed start is a silent no-op.
    if (!ctx || state === "running" || state === "fading") return;
    if (ctx.state === "closed") { ctx = null; return; }
    state = "running";
    var t = ctx.currentTime;
    master = ctx.createGain();
    master.gain.setValueAtTime(0, t);
    master.gain.linearRampToValueAtTime(targetGain(), t + 0.4); // faded in, never stepped
    master.connect(ctx.destination);
    // The bed: two barely-detuned low oscillators whose slow beating keeps the hum alive
    // between swells. Evolving by construction — there is nothing to loop.
    var b1 = ctx.createOscillator(); b1.type = "triangle"; b1.frequency.value = 55;
    var b2 = ctx.createOscillator(); b2.type = "sine"; b2.frequency.value = 55.7;
    var bedGain = ctx.createGain(); bedGain.gain.value = 0.28;
    b1.connect(bedGain); b2.connect(bedGain); bedGain.connect(master);
    b1.start(t); b2.start(t);
    bedNodes = [b1, b2];
    bag = []; nextAt = t + 0.12;
    schedule();
    timer = setInterval(function () { if (state === "running") schedule(); }, 200);
  }

  function applyGain(ms) {
    if (!ctx || !master || state !== "running") return;
    var t = ctx.currentTime;
    master.gain.cancelScheduledValues(t);
    master.gain.setValueAtTime(master.gain.value, t);
    master.gain.linearRampToValueAtTime(targetGain(), t + (ms || 80) / 1000);
  }

  function teardown(close) {
    if (timer) { clearInterval(timer); timer = null; }
    if (bedNodes) {
      for (var i = 0; i < bedNodes.length; i++) { try { bedNodes[i].stop(); } catch (e) { /* already stopped */ } }
      bedNodes = null;
    }
    if (master) { try { master.disconnect(); } catch (e) { /* already gone */ } master = null; }
    if (close && ctx) {
      try { swallow(ctx.close()); } catch (e) { /* navigation tears it down anyway */ }
      ctx = null;
      state = "closed";
    } else {
      state = "idle";
    }
  }

  function fadeStop(ms, close) {
    // EVERY stop is a fade, capped at FADE_CAP_MS — so the pre-navigation fade can never hold
    // the redirect longer than 200ms, and no path ever hard-cuts the waveform (no click).
    var dur = Math.min(ms, FADE_CAP_MS);
    if (!ctx || state !== "running") {
      teardown(close && !!ctx);
      return Promise.resolve();
    }
    state = "fading";
    if (timer) { clearInterval(timer); timer = null; }
    var t = ctx.currentTime;
    master.gain.cancelScheduledValues(t);
    master.gain.setValueAtTime(master.gain.value, t);
    master.gain.linearRampToValueAtTime(0.0001, t + dur / 1000);
    return new Promise(function (resolve) {
      setTimeout(function () { teardown(close); resolve(); }, dur + 20);
    });
  }

  // ── the visible controls (mute + volume on the load card) ──────────────────────────────────
  function reflect() {
    var btn = document.getElementById("humMute");
    if (btn) {
      var m = muted();
      btn.setAttribute("aria-pressed", m ? "true" : "false");
      btn.textContent = m ? "♪ MUTED" : "♪ HUM";
    }
    var vol = document.getElementById("humVol");
    if (vol) vol.value = String(volume());
  }

  function wire() {
    var btn = document.getElementById("humMute");
    if (btn) {
      btn.addEventListener("click", function () {
        persist(MUTE_KEY, muted() ? "0" : "1");
        applyGain(80);
        reflect();
      });
    }
    var vol = document.getElementById("humVol");
    if (vol) {
      vol.addEventListener("input", function () {
        persist(VOL_KEY, String(vol.value));
        if (muted()) persist(MUTE_KEY, "0"); // moving the volume unmutes (OS convention)
        applyGain(80);
        reflect();
      });
    }
    reflect();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();

  // A BFCache/back restore must never revive a hum mid-flight (home.js resets the overlay on
  // the same event): kill the graph outright, keep the persisted controls in sync.
  window.addEventListener("pageshow", function () {
    if (state === "running" || state === "fading") teardown(false);
    reflect();
  });

  window.SFLaunchAudio = {
    prime: prime,
    start: start,
    stop: function () { return fadeStop(120, false); }, // error path: keep the primed context
    fadeOut: function (ms) { return fadeStop(ms || 180, true); }, // pre-navigation
    state: function () { return state; },
    muted: muted,
    volume: volume
  };
})();
