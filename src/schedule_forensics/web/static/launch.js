/* Schedule Forensics — the Boot Screen (the startup "launch sequence", ADR-0426).
 *
 * NOT to be confused with ADR-0328's Launch Sequence, which is the LOAD OVERLAY (orbiting dots +
 * the Boot Audio Hum that rides an import). This file is the STARTUP screen the launcher opens:
 * a full-bleed particle lightshow, four hero scenes, a staged "travel" transit, and a welcome
 * panel that hands the operator into the deck. It REUSES ADR-0328's audio module rather than
 * synthesizing its own — one sound, one set of controls, one persisted preference.
 *
 * Ported from the operator's Mission Ops v2 prototype (the MERLIN deck). Four differences, all
 * deliberate and all recorded in ADR-0426:
 *
 *   1. NO INLINE HANDLERS. The deck uses onClick= attributes; the strict script-src CSP
 *      (ADR-0268) forbids them, so every control is wired here by id / data-sf-boot attribute.
 *   2. NO FABRICATED TELEMETRY. The deck's tiles count down "225.4 M km" and "14 pre-flight
 *      checks" — theatre with no data behind it. The design system's numbers rule (every
 *      displayed number traces to the engine payload; missing values show an em dash, never a
 *      fabricated figure) forbids that, so the tiles read REAL session facts served in the boot
 *      JSON block, and read an em dash when nothing is loaded.
 *   3. REDUCED MOTION IS A STILL FRAME, NOT A BLANK ONE. prefers-reduced-motion renders one
 *      composed frame and stops — the operator still sees the scene, nothing animates, and no
 *      rAF loop is ever scheduled.
 *   4. TOKENS, NOT HEXES. The particle palette is derived from CSS custom properties at start
 *      (--boot-accent / --boot-warm), so apollo boots amber and jarvis boots its HUD cyan
 *      instead of everything hard-coding the deck's one ramp. The GROUND stays dark in every
 *      theme, daylight included — see the header of launch.css for why an additive particle
 *      field has no light-mode equivalent.
 *
 * Performance note carried over from the prototype, because it is the whole reason this runs at
 * 60fps with ~15k particles: composing an rgba() string per particle per frame dominates the
 * loop. The palette is quantized into a lookup table once, particles are binned by colour into
 * preallocated flat arrays and counting-sorted, and the loop emits ONE fillStyle per non-empty
 * bucket. Additive blending is order-independent, so the regrouping is free visually.
 */
"use strict";

(function () {
  var SKIP_KEY = "sf-boot-skip"; // "1" = the operator asked to go straight to the deck

  function stored(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function persist(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* in-page only */ } }

  // ── the opt-out, checked before anything is drawn ────────────────────────────────────────────
  // A boot screen the operator has dismissed must never flash. This runs at parse time (the
  // module is head-loaded), so the redirect happens before the canvas is laid out or painted.
  if (stored(SKIP_KEY) === "1" && !/[?&]replay=1/.test(location.search)) {
    location.replace("/");
    return;
  }

  var boot = null;
  try {
    var el = document.getElementById("sfBootData");
    if (el) boot = JSON.parse(el.textContent || "{}");
  } catch (e) { boot = null; }
  if (!boot) boot = { files: 0, activities: 0, dataDate: null, target: null, actions: [] };

  var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  /* ── stage labels ──────────────────────────────────────────────────────────────────────────
     Labels, not measurements — nothing here claims a number. The transit is a curtain over the
     handoff into the deck, and it says so. */
  var STAGES = ["PRE-FLIGHT", "IGNITION", "TRANS-ORBITAL INJECTION", "CRUISE", "ORBITAL INSERTION", "DECK ONLINE"];

  var HEROSCENES = [
    {
      k: "01 — SYSTEM START · SCHEDULE INTELLIGENCE",
      h: "Every schedule, under one light.",
      s: "Twelve chapters walk from “I know nothing about this project” to a defensible view of its past, its present, and what has to happen next — every number solved on this machine, every claim carrying its citation."
    },
    {
      k: "02 — MANY UPDATES · ONE SIGNAL",
      h: "Everything converges on the date.",
      s: "Thousands of activities, one centre of gravity. The deck turns a shelf of update files into one focused line of evidence about what actually moved, and what moved it."
    },
    {
      k: "03 — THE PROGRAMME, IN MOTION",
      h: "A portfolio already in orbit.",
      s: "Every programme circles one standard of proof: every number cited, every path solved, nothing leaving this machine."
    },
    {
      k: "04 — THE RECORD, BEFORE IT IS READ",
      h: "Evidence arrives as a cloud.",
      s: "Updates land as one undifferentiated field — dense where the record is thick, void where it was never kept. The deck lights the filaments and names what is missing."
    }
  ];

  var TAU = 6.28318, PI = 3.14159;

  var state = { phase: "idle", stage: 0, scene: 0 }; // idle | travel | ready
  var scenePrev = null, sceneT0 = 0, raf = null, swapT = null, stageTimers = [];

  // ── palette, derived from the live theme ────────────────────────────────────────────────────
  // The deck hard-codes a cyan→gold ramp. Reading tokens instead means apollo's amber CRT gets a
  // lightshow that belongs to it. Falls back to the prototype's ramp if a token is missing or
  // unparseable — a boot screen must never fail to paint because a stylesheet was slow.
  function parseColor(str) {
    if (!str) return null;
    str = str.trim();
    var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(str);
    if (m) {
      var hex = m[1];
      if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
      return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
    }
    m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i.exec(str);
    if (m) return [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3])];
    return null;
  }
  function themeColor(name, fallback) {
    var v = null;
    try { v = getComputedStyle(document.documentElement).getPropertyValue(name); } catch (e) { v = null; }
    return parseColor(v) || fallback;
  }
  // COOL is the resting body of the cloud, WARM the crests and knots. The boot palette indirects
  // through --boot-accent / --boot-warm rather than reading --accent / --warn directly: launch.css
  // resolves those to the theme's pair for the three dark views, and re-points them for daylight,
  // whose accent is a deep blue for white paper and reads as nothing at all as emitted light.
  var COOL = themeColor("--boot-accent", [96, 230, 255]);
  var WARM = themeColor("--boot-warm", [255, 168, 127]);

  function startScene() {
    var c = document.getElementById("sfBootCanvas");
    if (!c || !c.getContext) return;
    var ctx = c.getContext("2d");
    if (!ctx) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    var fit = function () { c.width = Math.max(1, c.clientWidth * dpr); c.height = Math.max(1, c.clientHeight * dpr); };
    fit();

    var rnd = Math.random;

    // Particle budget scales with the surface: a laptop pane and a wall display should both
    // stay at frame rate. The prototype's 15,600 is the ceiling, not the constant.
    var area = (c.clientWidth || 1200) * (c.clientHeight || 800);
    var N = Math.max(4200, Math.min(15600, Math.round(area / 78)));

    var stars = [];
    for (var si = 0; si < 240; si++) {
      stars.push({ x: rnd(), y: rnd(), z: rnd() * 0.8 + 0.2, a: rnd() * 0.5 + 0.15, tw: rnd() * TAU, warmish: rnd() < 0.12 });
    }

    // Helix roles: two sugar-phosphate backbones + base-pair rungs are the BRIGHT population;
    // the remainder is dim solvent haze that gives the molecule volume.
    var HB = Math.round(N * 0.372), HBH = HB / 2, HR_ROWS = 42, HR_PER = 40, HR = HR_ROWS * HR_PER;
    var HTURN = 4 * TAU, WCOL = 130, WROW = Math.max(40, Math.floor(N / WCOL));

    var P = [];
    for (var i = 0; i < N; i++) {
      P.push({
        r1: rnd(), r2: rnd(), r3: rnd(), r4: rnd(),
        g1: (rnd() + rnd() + rnd() - 1.5) / 1.5,
        g2: (rnd() + rnd() + rnd() - 1.5) / 1.5,
        sz: 0.7 + rnd() * 2.2
      });
    }
    var CL = [];
    for (var k = 0; k < 9; k++) CL.push({ th: rnd() * TAU, rr: 0.3 + rnd() * 0.6, s: 0.018 + rnd() * 0.034 });
    var orbs = [];
    for (var oi = 0; oi < 26; oi++) orbs.push({ x: rnd(), ph: rnd() * TAU, sz: 1.5 + rnd() * 3 });

    var t = 0, warpT = 0;

    // mix 0 → COOL, mix 1 → WARM.
    function col(mix, al) {
      var r = Math.round(COOL[0] + mix * (WARM[0] - COOL[0]));
      var g = Math.round(COOL[1] + mix * (WARM[1] - COOL[1]));
      var b = Math.round(COOL[2] + mix * (WARM[2] - COOL[2]));
      return "rgba(" + r + "," + g + "," + b + "," + al + ")";
    }

    var MQ = 24, AQ = 8;
    var LUT = new Array(MQ * AQ);
    for (var mi = 0; mi < MQ; mi++) {
      for (var ai = 0; ai < AQ; ai++) LUT[mi * AQ + ai] = col(mi / (MQ - 1), (ai + 1) / AQ);
    }
    var KLUT = new Array(AQ);
    for (var ki = 0; ki < AQ; ki++) KLUT[ki] = "rgba(243,252,255," + ((ki + 1) / AQ).toFixed(3) + ")";

    // Pre-rendered glow blobs: per-particle beginPath+arc+fill under 'lighter' is the other
    // dominant cost. One sprite per hue bucket, drawn with drawImage, costs nothing.
    var NH = 6;
    var NSPR = new Array(NH), NLUT = new Array(NH * AQ);
    for (var hi = 0; hi < NH; hi++) {
      var mixh = hi / (NH - 1);
      var rgb = [
        Math.round(COOL[0] + mixh * (WARM[0] - COOL[0])),
        Math.round(COOL[1] + mixh * (WARM[1] - COOL[1])),
        Math.round(COOL[2] + mixh * (WARM[2] - COOL[2]))
      ];
      for (var ai2 = 0; ai2 < AQ; ai2++) {
        NLUT[hi * AQ + ai2] = "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + ((ai2 + 1) / AQ).toFixed(3) + ")";
      }
      var sc = document.createElement("canvas"); sc.width = 96; sc.height = 96;
      var sx = sc.getContext("2d");
      var sg = sx.createRadialGradient(48, 48, 0, 48, 48, 48);
      sg.addColorStop(0, "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",.88)");
      sg.addColorStop(0.34, "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",.36)");
      sg.addColorStop(0.68, "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",.10)");
      sg.addColorStop(1, "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",0)");
      sx.fillStyle = sg; sx.fillRect(0, 0, 96, 96);
      NSPR[hi] = sc;
    }
    var gcv = NSPR[0];

    var KB = MQ * AQ + NH * AQ, NB = KB + AQ;
    var STY = new Array(NB);
    for (var b1 = 0; b1 < MQ * AQ; b1++) STY[b1] = LUT[b1];
    for (var b2 = 0; b2 < NH * AQ; b2++) STY[MQ * AQ + b2] = NLUT[b2];
    for (var b3 = 0; b3 < AQ; b3++) STY[KB + b3] = KLUT[b3];

    var bKey = new Int32Array(N), bX = new Float32Array(N), bY = new Float32Array(N), bS = new Float32Array(N);
    var bCnt = new Int32Array(NB), bOff = new Int32Array(NB), bCur = new Int32Array(NB), bOrd = new Int32Array(N);

    var smooth = function (x) { return x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x); };
    var lp = function (x, y, m) { return x + (y - x) * m; };

    var O = { x: 0, y: 0, sz: 1, mix: 0, al: 0, knot: 0, soft: 0, neb: 0 };
    var O2 = { x: 0, y: 0, sz: 1, mix: 0, al: 0, knot: 0, soft: 0, neb: 0 };

    /* One pool, four scene targets, true morphing: changing scene interpolates every particle
       from where it IS to where the next scene wants it, so the helix visibly unwinds into the
       wave and the wave spirals up into the galaxy. A crossfade would look like two pictures;
       this looks like one substance rearranging. */
    function tgt(k, i, p, w, h, o) {
      o.soft = 0; o.neb = 0;
      if (k === 0) { // DNA helix — twin backbones, base-pair rungs, solvent haze
        var A = Math.min(w * 0.105, h * 0.19), cx = w / 2, top = h * 0.035, span = h * 0.95;
        if (i < HB) {
          var strand = i & 1, u = (((i >> 1) / (HBH - 1)) + t * 0.028) % 1;
          var ang = u * HTURN - t * 1.1 + strand * PI, sx2 = Math.sin(ang), depth = (Math.cos(ang) + 1) / 2;
          o.x = cx + sx2 * A + p.g1 * A * 0.05;
          o.y = top + span * u + p.g2 * h * 0.0035;
          o.knot = 0;
          o.mix = 0.03 + 0.06 * depth;
          o.al = 0.3 + 0.62 * depth; // the strand in front reads brighter — the woven look
          o.sz = p.sz * (0.8 + depth * 1.25);
        } else if (i < HB + HR) {
          var q = (i - HB) % HR_PER, r = ((i - HB) / HR_PER) | 0;
          var u2 = ((r + 0.5) / HR_ROWS + t * 0.028) % 1;
          var ang2 = u2 * HTURN - t * 1.1, sx3 = Math.sin(ang2), open = Math.abs(sx3);
          var fq = q / (HR_PER - 1), xa = cx + sx3 * A, xb = cx - sx3 * A;
          o.x = xa + (xb - xa) * fq + p.g1 * A * 0.018;
          o.y = top + span * u2 + p.g2 * h * 0.003;
          o.knot = (open > 0.45 && (q === 0 || q === HR_PER - 1)) ? 1 : 0;
          o.mix = (r & 1) ? 0.74 : 0.1; // alternating pairs — warm against cool
          o.al = (0.2 + 0.6 * open) * (0.72 + 0.28 * Math.sin(fq * PI));
          o.sz = p.sz * 0.72;
        } else {
          var ci = i - HB - HR, u3 = ((ci * 0.618034) % 1 + t * 0.028) % 1;
          var ang3 = u3 * HTURN - t * 1.1 + (ci & 1) * PI, depth3 = (Math.cos(ang3) + 1) / 2;
          o.x = cx + Math.sin(ang3) * A * (1 + p.g1 * 0.42) + p.g1 * A * 0.34;
          o.y = top + span * u3 + p.g2 * h * 0.01;
          o.knot = 0;
          o.mix = 0.05 + 0.08 * depth3;
          o.al = 0.05 + 0.12 * depth3;
          o.sz = p.sz * 0.78;
        }
      } else if (k === 1) { // signal-wave terrain
        var cc = i % WCOL, row = (i / WCOL) | 0, px = cc / (WCOL - 1) + p.g1 * 0.003, rf = row / (WROW - 1);
        var ridge = (Math.sin(px * 9 + t * 1.2 + rf * 4.5) + Math.sin(px * 21 - t * 1.7 + rf * 2) * 0.5 + Math.sin(px * 43 + t * 0.8 + row * 0.21) * 0.28) / 1.78;
        var hot = Math.max(0, ridge), sh = Math.max(0, -ridge);
        o.x = px * w;
        o.y = h * 0.56 + rf * h * 0.40 - Math.max(ridge, -0.2) * h * 0.095 * (1 - rf * 0.5) + p.g2 * h * 0.0035;
        o.knot = (hot > 0.84 && i % 29 === 0) ? 1 : 0;
        // colour follows HEIGHT, not position: crests run warm, troughs stay deep
        o.mix = Math.min(1, Math.max(0, 0.04 + 0.92 * hot * hot + px * 0.22));
        o.al = (0.035 + 0.68 * Math.pow(hot, 1.3) + 0.1 * sh) * (1 - rf * 0.34);
        o.sz = p.sz * 0.62 * (1 + hot * 2.2);
      } else if (k === 2) { // galaxy — clustered arms, soft-fading core
        var rr, th0;
        if (p.r4 < 0.14) { var cl = CL[i % 9]; rr = Math.max(0.05, cl.rr + p.g1 * cl.s * 2.4); th0 = cl.th + p.g2 * cl.s * 3.2; }
        else { rr = Math.pow(p.r1, 0.62); th0 = (i % 3) * (TAU / 3) + rr * 5.4 + (p.r2 - 0.5) * 0.5; }
        var th = th0 + t * (0.5 - 0.34 * rr), Rg = Math.min(w, h) * 0.46;
        var coreFade = Math.exp(-rr * 2.4);
        var ember = rr > 0.8 && p.r3 < 0.35, ringHot = rr > 0.3 && rr < 0.42;
        o.x = w / 2 + Math.cos(th) * rr * Rg;
        o.y = h * 0.62 + Math.sin(th) * rr * Rg * 0.38;
        o.knot = 0;
        o.mix = ember ? 0.85 : (0.05 + 0.1 * rr);
        o.al = Math.min(1, (0.10 + 0.5 * coreFade + 0.32 * (1 - rr)) * 0.7 * (ringHot ? 1.3 : 1) * (p.r4 < 0.14 ? 1.35 : 1));
        o.sz = p.sz * (1 + coreFade * 1.5 + (p.r4 < 0.14 ? 0.4 : 0));
      } else { /* nebula — a gaseous field, not a shape. Each particle keeps a fixed home; two
          sine pairs DRAG that home around (domain warp) so the cloud churns instead of
          scrolling. Ridging the noise (1 - |n|) and squaring it drives the voids to true black,
          which is what reads as dust lanes rather than even fog. */
        var nx0 = p.r1, ny0 = p.r2;
        var wx = Math.sin(ny0 * 4.1 + t * 0.21) * 0.17 + Math.sin(ny0 * 9.3 - t * 0.14) * 0.075;
        var wy = Math.cos(nx0 * 3.7 - t * 0.18) * 0.15 + Math.cos(nx0 * 7.9 + t * 0.12) * 0.065;
        var u4 = nx0 + wx, v4 = ny0 + wy;
        var den = 1 - Math.abs((Math.sin(u4 * 5.2 + v4 * 3.1 + t * 0.10)
          + Math.sin(u4 * 11.4 - v4 * 7.7 - t * 0.085) * 0.55
          + Math.sin(u4 * 22.6 + v4 * 17.3 + t * 0.065) * 0.27) / 1.82);
        var dd = den * den;
        o.x = u4 * w * 1.06 - w * 0.03 + p.g1 * w * 0.006;
        o.y = h * 0.05 + v4 * h * 0.93 + p.g2 * h * 0.008;
        o.neb = 1;
        o.mix = Math.min(1, Math.max(0, 0.05 + 0.72 * dd + (u4 - 0.5) * 0.30 - (v4 - 0.5) * 0.16));
        if (i < 140) { o.soft = 30; o.al = 0.018 + 0.05 * den; o.sz = p.sz * 1.4; o.knot = 0; }
        else if (i < 700) { o.soft = 11; o.al = 0.028 + 0.10 * dd; o.sz = p.sz * 1.1; o.knot = 0; }
        else { o.soft = 0; o.al = 0.03 + 0.78 * dd * dd; o.sz = p.sz * 0.58 * (1 + dd * 1.5); o.knot = (dd > 0.93 && i % 37 === 0) ? 1 : 0; }
      }
    }

    function overlay(k, wgt, w, h) {
      if (wgt < 0.03) return;
      if (k === 0) {
        var A = Math.min(w * 0.105, h * 0.19), cx = w / 2;
        var cg = ctx.createRadialGradient(cx, h * 0.5, 0, cx, h * 0.5, A * 2.6);
        cg.addColorStop(0, col(0, 0.09 * wgt)); cg.addColorStop(1, col(0, 0));
        ctx.fillStyle = cg; ctx.fillRect(cx - A * 2.6, 0, A * 5.2, h);
      } else if (k === 1) {
        for (var oj = 0; oj < orbs.length; oj++) {
          var ob = orbs[oj];
          var y = h * 0.55 - Math.abs(Math.sin(t * 0.5 + ob.ph)) * h * 0.3, s = ob.sz * dpr, gr = s * 4.2;
          ctx.globalAlpha = wgt; ctx.drawImage(gcv, ob.x * w - gr, y - gr, gr * 2, gr * 2); ctx.globalAlpha = 1;
          ctx.fillStyle = col(ob.x, wgt * 0.5); ctx.fillRect(ob.x * w - s, y - s, s * 2, s * 2);
        }
      } else if (k === 2) {
        var cx2 = w / 2, cy = h * 0.62, Rg2 = Math.min(w, h) * 0.46;
        var core = ctx.createRadialGradient(cx2, cy, 0, cx2, cy, Rg2 * 0.9);
        core.addColorStop(0, "rgba(255,255,255," + (0.62 * wgt) + ")");
        core.addColorStop(0.16, col(0.05, 0.30 * wgt));
        core.addColorStop(0.42, col(0.02, 0.12 * wgt));
        core.addColorStop(0.72, col(0, 0.045 * wgt));
        core.addColorStop(1, col(0, 0));
        ctx.fillStyle = core; ctx.beginPath(); ctx.ellipse(cx2, cy, Rg2 * 0.9, Rg2 * 0.48, 0, 0, TAU); ctx.fill();
      } else {
        var R = Math.max(w, h);
        var g1 = ctx.createRadialGradient(w * 0.34, h * 0.42, 0, w * 0.34, h * 0.42, R * 0.52);
        g1.addColorStop(0, col(0.9, 0.11 * wgt)); g1.addColorStop(0.5, col(1, 0.055 * wgt)); g1.addColorStop(1, col(1, 0));
        ctx.fillStyle = g1; ctx.fillRect(0, 0, w, h);
        var g2 = ctx.createRadialGradient(w * 0.72, h * 0.64, 0, w * 0.72, h * 0.64, R * 0.44);
        g2.addColorStop(0, col(0.75, 0.09 * wgt)); g2.addColorStop(0.46, col(0.1, 0.045 * wgt)); g2.addColorStop(1, col(0.1, 0));
        ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
      }
    }

    function frame() {
      if (!document.getElementById("sfBootCanvas")) { raf = null; return; }
      if (c.clientWidth * dpr !== c.width) fit();
      var w = c.width, h = c.height, warp = state.phase === "travel";
      warpT = warp ? Math.min(1, warpT + 0.008) : Math.max(0, warpT - 0.02);
      t += 0.006 + warpT * 0.02;
      var now = (window.performance && performance.now) ? performance.now() : 0;
      if (state.phase === "idle" && !reduced && now - sceneT0 > 10500) goScene((state.scene + 1) % HEROSCENES.length);

      ctx.globalCompositeOperation = "source-over";
      ctx.clearRect(0, 0, w, h);
      for (var s1 = 0; s1 < stars.length; s1++) {
        var st = stars[s1];
        st.x -= (0.00035 + warpT * 0.012) * st.z;
        if (st.x < -0.05) { st.x = 1.05; st.y = rnd(); }
        var tw = 0.65 + 0.35 * Math.sin(t * 2.4 + st.tw), len = warpT * st.z * 90 * dpr;
        ctx.globalAlpha = st.a * tw;
        if (len > 2) {
          ctx.strokeStyle = "rgba(190,230,255,.7)"; ctx.lineWidth = dpr * st.z;
          ctx.beginPath(); ctx.moveTo(st.x * w, st.y * h); ctx.lineTo(st.x * w + len, st.y * h); ctx.stroke();
        } else {
          ctx.fillStyle = st.warmish ? col(1, 1) : "#eef7ff";
          ctx.fillRect(st.x * w, st.y * h, dpr * st.z * 1.8, dpr * st.z * 1.8);
        }
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "lighter";

      var m = smooth((now - sceneT0) / 2100);
      var kA = scenePrev, kB = state.scene, morph = kA != null && m < 1;
      var wcx = w / 2, wcy = h * 0.5, exp = 1 + warpT * 0.85, alW = 1 - warpT * 0.35;
      var ns = 0;
      bCnt.fill(0);
      for (var i2 = 0; i2 < N; i2++) {
        var p = P[i2];
        tgt(kB, i2, p, w, h, O);
        var x = O.x, y = O.y, sz = O.sz, mix = O.mix, al = O.al, knot = O.knot, soft = O.soft, neb = O.neb;
        if (morph) {
          tgt(kA, i2, p, w, h, O2);
          x = lp(O2.x, x, m); y = lp(O2.y, y, m); sz = lp(O2.sz, sz, m);
          mix = lp(O2.mix, mix, m); al = lp(O2.al, al, m); soft = lp(O2.soft, soft, m);
          knot = m > 0.5 ? knot : O2.knot; neb = m > 0.5 ? neb : O2.neb;
        }
        if (warpT > 0) { x = wcx + (x - wcx) * exp; y = wcy + (y - wcy) * exp; }
        al *= alW;
        if (al < 0.05) continue; // the haze and the trough floor cost fill and contribute nothing
        var szp = sz * dpr;
        var hu = neb ? Math.min(NH - 1, (Math.min(1, Math.max(0, mix)) * NH) | 0) : 0;
        if (soft > 0.01) {
          var gr2 = szp * soft;
          ctx.globalAlpha = Math.min(1, al);
          ctx.drawImage(NSPR[hu], x - gr2, y - gr2, gr2 * 2, gr2 * 2);
          ctx.globalAlpha = 1;
        } else {
          var ai3 = Math.min(AQ - 1, (Math.min(1, al) * AQ) | 0);
          var key = knot ? KB + Math.min(AQ - 1, (Math.min(1, al * 1.55) * AQ) | 0)
            : neb ? MQ * AQ + hu * AQ + ai3
              : Math.min(MQ - 1, (Math.max(0, mix) * MQ) | 0) * AQ + ai3;
          bKey[ns] = key; bX[ns] = x; bY[ns] = y; bS[ns] = szp; ns++; bCnt[key]++;
          if (knot) { var gr3 = szp * 5.2; ctx.drawImage(neb ? NSPR[NH - 1] : gcv, x - gr3, y - gr3, gr3 * 2, gr3 * 2); }
        }
      }
      for (var b = 0, acc = 0; b < NB; b++) { bOff[b] = acc; bCur[b] = acc; acc += bCnt[b]; }
      for (var s2 = 0; s2 < ns; s2++) bOrd[bCur[bKey[s2]]++] = s2;
      for (var b4 = 0; b4 < NB; b4++) {
        var cn = bCnt[b4];
        if (!cn) continue;
        ctx.fillStyle = STY[b4];
        var st0 = bOff[b4];
        for (var j = st0; j < st0 + cn; j++) { var sj = bOrd[j], sp = bS[sj]; ctx.fillRect(bX[sj] - sp * 0.5, bY[sj] - sp * 0.5, sp, sp); }
      }
      if (morph) { overlay(kA, 1 - m, w, h); overlay(kB, m, w, h); }
      else { scenePrev = null; overlay(kB, 1, w, h); }

      // A dark vignette behind the hero copy — the text must stay readable over any scene.
      ctx.globalCompositeOperation = "source-over";
      var pk = ctx.createRadialGradient(w / 2, h * 0.26, 0, w / 2, h * 0.26, h * 0.42);
      pk.addColorStop(0, "rgba(3,7,13,.42)"); pk.addColorStop(0.6, "rgba(3,7,13,.2)"); pk.addColorStop(1, "rgba(3,7,13,0)");
      ctx.fillStyle = pk; ctx.beginPath(); ctx.arc(w / 2, h * 0.26, h * 0.42, 0, TAU); ctx.fill();

      // Reduced motion: ONE composed frame, then stop. The operator sees the scene; nothing moves.
      raf = reduced ? null : requestAnimationFrame(frame);
    }

    sceneT0 = (window.performance && performance.now) ? performance.now() : 0;
    raf = requestAnimationFrame(frame);
  }

  // ── hero copy + scene navigation ────────────────────────────────────────────────────────────
  function paintHero() {
    var sc = HEROSCENES[state.scene] || HEROSCENES[0];
    var kick = document.getElementById("sfBootKicker");
    var h1 = document.getElementById("sfBootH1");
    var sub = document.getElementById("sfBootSub");
    if (kick) kick.textContent = sc.k;
    if (h1) h1.textContent = sc.h;
    if (sub) sub.textContent = sc.s;
    var dots = document.querySelectorAll("[data-sf-boot-dot]");
    for (var i = 0; i < dots.length; i++) {
      var on = +dots[i].getAttribute("data-sf-boot-dot") === state.scene;
      dots[i].classList.toggle("on", on);
      dots[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }
  function goScene(k) {
    if (k === state.scene && scenePrev == null) return;
    scenePrev = state.scene;
    state.scene = k;
    sceneT0 = (window.performance && performance.now) ? performance.now() : 0;
    clearTimeout(swapT);
    var hero = document.getElementById("sfBootHero");
    if (hero) hero.classList.add("fading");
    swapT = setTimeout(function () {
      paintHero();
      if (hero) hero.classList.remove("fading");
    }, reduced ? 0 : 420);
  }

  // ── the transit ─────────────────────────────────────────────────────────────────────────────
  function setStage(n) {
    state.stage = n;
    var el = document.getElementById("sfBootStage");
    if (el) el.textContent = STAGES[n] || STAGES[0];
    var tile = document.getElementById("sfBootSeq");
    if (tile) tile.textContent = STAGES[n] || STAGES[0];
  }

  function showReady() {
    state.phase = "ready";
    setStage(STAGES.length - 1);
    var root = document.getElementById("sfBoot");
    if (root) { root.classList.remove("is-travel"); root.classList.add("is-ready"); }
    var focus = document.getElementById("sfBootEnter");
    if (focus && focus.focus) { try { focus.focus(); } catch (e) { /* not focusable yet */ } }
  }

  function begin() {
    if (state.phase !== "idle") return;
    // The AudioContext is created HERE and only here — inside a genuine click handler. ADR-0328's
    // module refuses to create one anywhere else, so a programmatic begin() is a silent begin().
    if (window.SFLaunchAudio) {
      try { window.SFLaunchAudio.prime(); window.SFLaunchAudio.start(); } catch (e) { /* silent transit */ }
    }
    state.phase = "travel";
    var root = document.getElementById("sfBoot");
    if (root) root.classList.add("is-travel");
    setStage(1);

    // Reduced motion gets the destination, not the journey: no 7-second wait for someone who
    // has asked the platform for less movement.
    if (reduced) { showReady(); return; }

    [1, 2, 3, 4].forEach(function (s, i) {
      stageTimers.push(setTimeout(function () { setStage(s + 1); }, 900 + i * 1500));
    });
    stageTimers.push(setTimeout(showReady, 7000));
  }

  function leave(href) {
    // Never hard-cut the hum: ADR-0328 caps the fade at 200ms, so this can never hold the
    // navigation hostage, and the waveform never clicks.
    var go = function () { location.href = href; };
    if (window.SFLaunchAudio && window.SFLaunchAudio.state && window.SFLaunchAudio.state() !== "idle") {
      try { window.SFLaunchAudio.fadeOut(180).then(go, go); return; } catch (e) { /* fall through */ }
    }
    go();
  }

  function wire() {
    paintHero();
    setStage(0);
    startScene();

    var beginBtn = document.getElementById("sfBootBegin");
    if (beginBtn) beginBtn.addEventListener("click", begin);

    var skip = document.getElementById("sfBootSkip");
    if (skip) skip.addEventListener("click", function () { leave("/"); });

    var enter = document.getElementById("sfBootEnter");
    if (enter) enter.addEventListener("click", function () { leave(enter.getAttribute("data-sf-boot-href") || "/"); });

    var actions = document.querySelectorAll("[data-sf-boot-href]");
    for (var i = 0; i < actions.length; i++) {
      if (actions[i].id === "sfBootEnter") continue;
      (function (el) {
        el.addEventListener("click", function () { leave(el.getAttribute("data-sf-boot-href") || "/"); });
      })(actions[i]);
    }

    var dots = document.querySelectorAll("[data-sf-boot-dot]");
    for (var d = 0; d < dots.length; d++) {
      (function (el) {
        el.addEventListener("click", function () {
          if (state.phase !== "idle") return;
          goScene(+el.getAttribute("data-sf-boot-dot") || 0);
        });
      })(dots[d]);
    }

    var never = document.getElementById("sfBootNever");
    if (never) {
      never.checked = stored(SKIP_KEY) === "1";
      never.addEventListener("change", function () { persist(SKIP_KEY, never.checked ? "1" : "0"); });
    }

    // Escape is the universal "let me out" — it goes to the deck from any phase.
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") leave("/");
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();

  window.addEventListener("pagehide", function () {
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    clearTimeout(swapT);
    stageTimers.forEach(clearTimeout);
    stageTimers = [];
  });

  // Exposed for the behavioral tests (and nothing else): the scene/stage tables are the
  // contract this screen is judged against, and a test that re-declares them proves nothing.
  window.SFBoot = {
    stages: STAGES,
    scenes: HEROSCENES,
    phase: function () { return state.phase; },
    scene: function () { return state.scene; },
    begin: begin,
    goScene: goScene,
    reduced: function () { return reduced; }
  };
})();
