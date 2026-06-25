/* Schedule Forensics — header insignia: a transparent 3D wireframe Earth that rotates around a
 * STATIONARY "NASA" wordmark (the planet spins, the word does not). Vendored, dependency-free and
 * air-gap-safe — pure <canvas>, no images, no CDN, no WebGL libraries. The far side of the globe is
 * drawn faded so you can see straight through it; the continents are coarse coastline outlines.
 *
 * It also doubles as the page-wide AI status light: ask.js toggles `.ai-thinking` (model is
 * generating → spin up + cyan glow) and briefly `.ai-error` (failed → red flash) on the host, so on
 * EVERY page the operator can see at a glance whether the local AI is working. prefers-reduced-motion
 * stops the rotation (the globe still renders, just still).
 */
"use strict";

(function () {
  var host = document.querySelector(".nasa-globe");
  if (!host) return;
  var cv = host.querySelector("canvas");
  if (!cv || !cv.getContext) return;
  var ctx = cv.getContext("2d");

  // Coarse continent coastlines as [lon, lat] polylines in degrees — recognizable at this size,
  // deliberately low-poly (this is an insignia, not a survey map).
  var LAND = [
    // North America
    [[-168, 65], [-156, 71], [-128, 70], [-95, 70], [-81, 73], [-64, 60], [-78, 62], [-82, 52],
     [-66, 44], [-70, 41], [-81, 31], [-80, 25], [-90, 29], [-97, 26], [-105, 22], [-110, 23],
     [-117, 33], [-124, 40], [-124, 48], [-132, 56], [-150, 59], [-166, 60], [-168, 65]],
    // South America
    [[-78, 8], [-72, 11], [-62, 10], [-50, 0], [-35, -6], [-39, -14], [-48, -25], [-58, -34],
     [-62, -41], [-69, -52], [-74, -50], [-73, -44], [-71, -33], [-71, -18], [-79, -8], [-80, 0],
     [-78, 8]],
    // Africa
    [[-17, 21], [-16, 14], [-10, 6], [3, 6], [9, 4], [9, -1], [13, -6], [12, -16], [15, -28],
     [20, -35], [27, -34], [33, -26], [40, -16], [41, -3], [51, 12], [44, 11], [37, 11], [34, 28],
     [25, 32], [10, 34], [-2, 36], [-10, 30], [-17, 21]],
    // Europe
    [[-10, 37], [-9, 43], [-2, 48], [2, 51], [4, 58], [8, 58], [11, 64], [20, 70], [28, 71],
     [30, 66], [22, 60], [27, 56], [20, 54], [12, 54], [4, 51], [-5, 48], [-10, 43], [-10, 37]],
    // Asia (mainland + a hint of India / the eastern seaboard)
    [[28, 66], [40, 68], [70, 73], [105, 78], [140, 73], [160, 70], [180, 66], [170, 60], [142, 59],
     [135, 48], [122, 40], [121, 31], [110, 22], [105, 10], [100, 6], [98, 16], [90, 22], [80, 14],
     [77, 8], [73, 18], [68, 24], [60, 25], [50, 29], [44, 40], [36, 45], [30, 52], [28, 66]],
    // Australia
    [[114, -22], [122, -18], [130, -12], [137, -12], [142, -11], [146, -18], [151, -24], [153, -28],
     [150, -37], [143, -39], [135, -35], [129, -32], [120, -34], [114, -30], [113, -25], [114, -22]],
    // Greenland
    [[-45, 60], [-42, 66], [-22, 70], [-18, 76], [-30, 83], [-50, 82], [-58, 76], [-52, 68],
     [-45, 60]],
    // Antarctica (a partial rim — reads as the south cap as it spins past)
    [[-60, -63], [-30, -70], [10, -69], [60, -67], [110, -66], [160, -70], [-160, -75], [-110, -73],
     [-60, -63]],
  ];

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var DEG = Math.PI / 180;
  var size = 0, R = 0, cx = 0, cy = 0, dpr = 1;

  function resize() {
    dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    size = cv.clientWidth || 130;
    cv.width = Math.round(size * dpr);
    cv.height = Math.round(size * dpr);
    R = size * 0.46;
    cx = size / 2;
    cy = size / 2;
  }

  // Orthographic projection of (lon,lat) on a globe spun by `rot` (radians) about the polar axis.
  // Returns {x,y,z}; z>0 is the near (facing) hemisphere, z<0 the far side (drawn faded).
  function project(lonDeg, latDeg, rot) {
    var lat = latDeg * DEG;
    var lon = lonDeg * DEG + rot;
    var cl = Math.cos(lat);
    var x = cl * Math.sin(lon);
    var y = Math.sin(lat);
    var z = cl * Math.cos(lon);
    return { x: cx + R * x, y: cy - R * y, z: z };
  }

  // Draw a [lon,lat] polyline, splitting it where it crosses the limb so the far side fades out.
  function strokePath(pts, rot, nearStyle, farStyle, width) {
    var prev = null;
    for (var i = 0; i < pts.length; i++) {
      var p = project(pts[i][0], pts[i][1], rot);
      if (prev) {
        var near = (p.z + prev.z) >= 0;
        ctx.beginPath();
        ctx.moveTo(prev.x, prev.y);
        ctx.lineTo(p.x, p.y);
        ctx.lineWidth = width * (near ? 1 : 0.85);
        ctx.strokeStyle = near ? nearStyle : farStyle;
        ctx.stroke();
      }
      prev = p;
    }
  }

  function graticule(rot, near, far) {
    var lat, lon, pts, j;
    for (lat = -60; lat <= 60; lat += 30) {
      pts = [];
      for (lon = -180; lon <= 180; lon += 12) pts.push([lon, lat]);
      strokePath(pts, rot, near, far, 1);
    }
    for (lon = -180; lon < 180; lon += 30) {
      pts = [];
      for (j = -90; j <= 90; j += 10) pts.push([lon, j]);
      strokePath(pts, rot, near, far, 1);
    }
  }

  function render(rot, busy) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);

    // atmosphere halo
    var glow = busy ? "rgba(120,210,255,0.55)" : "rgba(90,150,230,0.35)";
    var g = ctx.createRadialGradient(cx, cy, R * 0.7, cx, cy, R * 1.18);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(0.82, "rgba(0,0,0,0)");
    g.addColorStop(1, glow);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, R * 1.18, 0, Math.PI * 2);
    ctx.fill();

    // limb (the sphere's outline)
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = busy ? "rgba(150,220,255,0.9)" : "rgba(150,190,240,0.75)";
    ctx.stroke();

    var gridNear = busy ? "rgba(120,200,255,0.34)" : "rgba(130,170,225,0.26)";
    var gridFar = "rgba(120,160,210,0.10)";
    graticule(rot, gridNear, gridFar);

    var landNear = busy ? "rgba(170,235,255,0.95)" : "rgba(120,235,180,0.92)";
    var landFar = busy ? "rgba(120,190,230,0.28)" : "rgba(90,180,150,0.26)";
    for (var i = 0; i < LAND.length; i++) strokePath(LAND[i], rot, landNear, landFar, 1.5);
  }

  resize();
  window.addEventListener("resize", function () { resize(); if (!running) render(rot, false); });

  // PERFORMANCE: the globe is a stroke-heavy 2D canvas (hundreds of ctx.stroke() per frame). A
  // perpetual rAF redrawing it on EVERY page — even idle, even with the tab hidden — pegs a CPU
  // core and starves keyboard/scroll input on heavy pages (e.g. the 1746-row SRA grid). So we only
  // run the animation loop WHILE the AI is generating (the host carries .ai-thinking); when idle we
  // draw one static frame and stop, and we never animate while the tab is hidden. A tiny observer on
  // the host's class restarts the spin the instant ask.js flags the model as thinking.
  //
  // Asking the AI turns .ai-thinking ON, so the spin runs for the WHOLE generation — minutes with a
  // big local model. At 60 fps the stroke-heavy redraw still froze the SRA page for that whole span
  // (operator: "Ask the AI freezes on the SRA page"). So the redraw is throttled to ~15 fps: each
  // frame schedules the next one FRAME_MS later, so the spin never monopolizes the main thread on a
  // heavy page while the model thinks. A slow rotation still reads clearly as "the AI is working".
  var FRAME_MS = 66; // ~15 fps: enough motion to signal activity, ~4x less CPU than an unthrottled rAF
  var rot = 0.6, last = 0, running = false, raf = 0;
  function tick(now) {
    raf = 0;
    if (document.hidden || !host.classList.contains("ai-thinking")) {
      running = false;
      render(rot, false); // settle to a static, idle globe
      return;
    }
    if (!last) last = now;
    var dt = Math.min(120, now - last);
    last = now;
    if (!reduce) rot += 0.0011 * dt; // radians/ms — spins while the AI works
    render(rot, true);
    // schedule the next redraw FRAME_MS out (throttle) rather than back-to-back at the display rate
    setTimeout(function () { raf = window.requestAnimationFrame(tick); }, FRAME_MS);
  }
  function start() {
    if (running || reduce || document.hidden) return;
    if (!host.classList.contains("ai-thinking")) { render(rot, false); return; }
    running = true;
    last = 0;
    raf = window.requestAnimationFrame(tick);
  }
  render(rot, false); // initial static draw (idle); the loop only spins up while the AI works
  // restart the spin when ask.js toggles .ai-thinking, and redraw/resume when the tab returns
  new MutationObserver(start).observe(host, { attributes: true, attributeFilter: ["class"] });
  document.addEventListener("visibilitychange", function () { if (!document.hidden) start(); });
})();
