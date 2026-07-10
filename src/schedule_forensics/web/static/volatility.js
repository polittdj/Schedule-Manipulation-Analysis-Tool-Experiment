/* Schedule Forensics — Critical-Path Volatility (operator 2026-07-09).
 *
 * Ten dependency-free SVG visuals over the per-version critical sets (#volData, embedded
 * server-side — no network call, air-gap posture): stability gauge, Jaccard churn timeline,
 * entry/exit waterfall, composition area, membership heatmap, tenure + jumper leaderboards,
 * dwell histogram, jumper timeline strips, and animated transition ribbons — plus a sortable
 * per-activity scoreboard. One master stepper (Prev/Play/Next) animates the version cursor
 * through every visual in lockstep, mirroring GAO/DCMA stability best practice framing.
 */
"use strict";

(function () {
  var dataEl = document.getElementById("volData");
  if (!dataEl) return;
  var DATA = {};
  try { DATA = JSON.parse(dataEl.textContent || "{}"); } catch (e) { return; }
  var V = DATA.versions || [];
  var TASKS = DATA.tasks || [];
  var PAIRS = DATA.pairs || [];
  var N = V.length;
  if (N < 2) return;
  var NS = "http://www.w3.org/2000/svg";
  var OK = "var(--ok)", BAD = "var(--bad)", WARN = "var(--warn)", ACC = "var(--accent)";
  var cursor = N - 1;  // the animated version index (starts fully revealed)
  var timer = null;

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }
  function txt(svg, x, y, s, opts) {
    var a = { x: x, y: y, fill: (opts && opts.fill) || "var(--muted)", "font-size": (opts && opts.size) || 10 };
    if (opts && opts.anchor) a["text-anchor"] = opts.anchor;
    if (opts && opts.weight) a["font-weight"] = opts.weight;
    var t = svgEl("text", a);
    t.textContent = s;
    svg.appendChild(t);
    return t;
  }
  function tip(node, s) {
    var t = document.createElementNS(NS, "title");
    t.textContent = s;
    node.appendChild(t);
  }
  function host(id) {
    var h = document.getElementById(id);
    if (h) h.textContent = "";
    return h;
  }
  function frame(id, W, H, label) {
    var h = host(id);
    if (!h) return null;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y && label) SFA11y.label(svg, label);
    h.appendChild(svg);
    return svg;
  }
  function shortLabel(i) {
    return V[i].status_date || V[i].label.slice(0, 14);
  }

  // ── 1. stability gauge — mean Jaccard of consecutive paths ─────────────────────────
  function drawGauge() {
    var svg = frame("volGauge", 420, 220, "Critical-path stability gauge");
    if (!svg) return;
    var s = DATA.stability == null ? null : DATA.stability;
    var cx = 210, cy = 185, R = 140;
    function arc(a0, a1, color, width) {
      var x0 = cx + R * Math.cos(Math.PI * (1 - a0)), y0 = cy - R * Math.sin(Math.PI * (1 - a0));
      var x1 = cx + R * Math.cos(Math.PI * (1 - a1)), y1 = cy - R * Math.sin(Math.PI * (1 - a1));
      var large = (a1 - a0) > 0.5 ? 1 : 0;
      var p = svgEl("path", {
        d: "M" + x0 + " " + y0 + " A" + R + " " + R + " 0 " + large + " 1 " + x1 + " " + y1,
        fill: "none", stroke: color, "stroke-width": width || 18, "stroke-linecap": "butt",
      });
      svg.appendChild(p);
      return p;
    }
    // bands: <50% red, 50-70% amber, >70% green (churn heuristics around the GAO/DCMA
    // stable-path expectation). §5.3 honesty: there is NO verified published numeric
    // threshold, so the caveat is rendered ON the chart face, not just in this comment.
    arc(0, 0.5, BAD); arc(0.5, 0.7, WARN); arc(0.7, 1, OK);
    txt(svg, cx, 212, "bands are operator-set display guidance — not a published threshold",
      { anchor: "middle", size: 8.5 });
    if (s != null) {
      var a = Math.max(0, Math.min(1, s));
      var nx = cx + (R - 26) * Math.cos(Math.PI * (1 - a)), ny = cy - (R - 26) * Math.sin(Math.PI * (1 - a));
      svg.appendChild(svgEl("line", { x1: cx, y1: cy, x2: nx, y2: ny, stroke: "var(--ink)", "stroke-width": 3 }));
      svg.appendChild(svgEl("circle", { cx: cx, cy: cy, r: 6, fill: "var(--ink)" }));
      txt(svg, cx, cy - 46, Math.round(s * 100) + "%", { anchor: "middle", size: 30, weight: 700, fill: s >= 0.7 ? OK : s >= 0.5 ? WARN : BAD });
      txt(svg, cx, cy - 24, "mean path similarity between consecutive versions", { anchor: "middle" });
    } else {
      txt(svg, cx, cy - 40, "n/a", { anchor: "middle", size: 24 });
    }
    txt(svg, cx - R, cy + 14, "0%", { anchor: "middle" });
    txt(svg, cx + R, cy + 14, "100%", { anchor: "middle" });
  }

  // shared mini axis helpers for the version-indexed charts
  function vx(i, W, padL, padR) { return padL + (N <= 1 ? 0 : (i * (W - padL - padR)) / (N - 1)); }

  // ── 2. churn timeline — Jaccard % per consecutive pair (revealed to the cursor) ─────
  function drawChurn() {
    var W = 460, H = 240, padL = 40, padR = 12, padT = 18, padB = 46;
    var svg = frame("volChurn", W, H, "Critical-path churn timeline (Jaccard similarity)");
    if (!svg) return;
    var y = function (v) { return padT + (1 - v) * (H - padT - padB); };
    [0, 0.25, 0.5, 0.75, 1].forEach(function (g) {
      svg.appendChild(svgEl("line", { x1: padL, y1: y(g), x2: W - padR, y2: y(g), stroke: "var(--line)", "stroke-width": 1 }));
      txt(svg, padL - 4, y(g) + 3, Math.round(g * 100) + "%", { anchor: "end" });
    });
    svg.appendChild(svgEl("line", { x1: padL, y1: y(0.7), x2: W - padR, y2: y(0.7), stroke: OK, "stroke-width": 1, "stroke-dasharray": "4 4" }));
    txt(svg, W - padR, y(0.7) - 3, "stable ≳70%", { anchor: "end", fill: OK });
    var pts = [];
    PAIRS.forEach(function (p, i) {
      if (p.jaccard == null || i + 1 > cursor) return;
      pts.push(vx(i + 1, W, padL, padR) + "," + y(p.jaccard));
    });
    if (pts.length > 1) {
      svg.appendChild(svgEl("polyline", { points: pts.join(" "), fill: "none", stroke: ACC, "stroke-width": 2.5 }));
    }
    PAIRS.forEach(function (p, i) {
      if (p.jaccard == null || i + 1 > cursor) return;
      var c = svgEl("circle", { cx: vx(i + 1, W, padL, padR), cy: y(p.jaccard), r: 4, fill: p.jaccard >= 0.7 ? OK : p.jaccard >= 0.5 ? WARN : BAD });
      tip(c, p.from + " → " + p.to + ": " + Math.round(p.jaccard * 100) + "% of the path carried over");
      svg.appendChild(c);
    });
    for (var i = 0; i < N; i++) {
      txt(svg, vx(i, W, padL, padR), H - padB + 14, shortLabel(i), { anchor: "end" })
        .setAttribute("transform", "rotate(-30 " + vx(i, W, padL, padR) + " " + (H - padB + 14) + ")");
    }
  }

  // ── 3. entry/exit waterfall — entered up, left down, per version (to the cursor) ────
  function drawFlow() {
    var W = 460, H = 240, padL = 40, padR = 12, padT = 16, padB = 46;
    var svg = frame("volFlow", W, H, "Critical-path entry/exit waterfall");
    if (!svg) return;
    var most = 1;
    PAIRS.forEach(function (p) { most = Math.max(most, p.entered, p.left); });
    var mid = padT + (H - padT - padB) / 2;
    var scale = (H - padT - padB) / 2 / most;
    svg.appendChild(svgEl("line", { x1: padL, y1: mid, x2: W - padR, y2: mid, stroke: "var(--line)", "stroke-width": 1 }));
    var bw = Math.max(6, Math.min(26, (W - padL - padR) / (N * 2)));
    PAIRS.forEach(function (p, i) {
      if (i + 1 > cursor) return;
      var x = vx(i + 1, W, padL, padR) - bw / 2;
      var eh = p.entered * scale, lh = p.left * scale;
      var re = svgEl("rect", { x: x, y: mid - eh, width: bw, height: Math.max(eh, 0.5), fill: BAD });
      tip(re, p.to + ": " + p.entered + " joined the critical path");
      svg.appendChild(re);
      var rl = svgEl("rect", { x: x, y: mid, width: bw, height: Math.max(lh, 0.5), fill: ACC });
      tip(rl, p.to + ": " + p.left + " left the critical path");
      svg.appendChild(rl);
      if (p.entered) txt(svg, x + bw / 2, mid - eh - 3, "+" + p.entered, { anchor: "middle", fill: BAD });
      if (p.left) txt(svg, x + bw / 2, mid + lh + 10, "−" + p.left, { anchor: "middle", fill: ACC });
    });
    txt(svg, padL, padT - 4, "joined ↑ / left ↓ vs the prior version", {});
    for (var i = 0; i < N; i++) {
      txt(svg, vx(i, W, padL, padR), H - padB + 14, shortLabel(i), { anchor: "end" })
        .setAttribute("transform", "rotate(-30 " + vx(i, W, padL, padR) + " " + (H - padB + 14) + ")");
    }
  }

  // ── 4. composition area — stayed vs entered share of each version's path ───────────
  function drawArea() {
    var W = 460, H = 240, padL = 40, padR = 12, padT = 16, padB = 46;
    var svg = frame("volArea", W, H, "Critical-path composition (stayed vs entered)");
    if (!svg) return;
    var most = 1;
    V.forEach(function (v) { most = Math.max(most, v.critical); });
    var y = function (v) { return padT + (1 - v / most) * (H - padT - padB); };
    var stayedPts = [], totalPts = [];
    for (var i = 0; i <= cursor; i++) {
      var stayed = i === 0 ? V[0].critical : PAIRS[i - 1].stayed;
      stayedPts.push([vx(i, W, padL, padR), y(stayed)]);
      totalPts.push([vx(i, W, padL, padR), y(V[i].critical)]);
    }
    function areaPath(upper, lower) {
      var d = "M" + upper.map(function (p) { return p[0] + " " + p[1]; }).join(" L");
      for (var j = lower.length - 1; j >= 0; j--) d += " L" + lower[j][0] + " " + lower[j][1];
      return d + " Z";
    }
    var base = stayedPts.map(function (p) { return [p[0], y(0)]; });
    var a1 = svgEl("path", { d: areaPath(stayedPts, base), fill: OK, "fill-opacity": 0.5 });
    tip(a1, "carried over from the prior version");
    svg.appendChild(a1);
    var a2 = svgEl("path", { d: areaPath(totalPts, stayedPts), fill: BAD, "fill-opacity": 0.45 });
    tip(a2, "newly joined this version");
    svg.appendChild(a2);
    [0.5, 1].forEach(function (g) {
      txt(svg, padL - 4, y(most * g) + 3, Math.round(most * g), { anchor: "end" });
    });
    txt(svg, padL, padT - 4, "green = carried over · red = newly joined", {});
    for (var i2 = 0; i2 < N; i2++) {
      txt(svg, vx(i2, W, padL, padR), H - padB + 14, shortLabel(i2), { anchor: "end" })
        .setAttribute("transform", "rotate(-30 " + vx(i2, W, padL, padR) + " " + (H - padB + 14) + ")");
    }
  }

  // ── 5. membership heatmap — rows = ever-critical activities, cols = versions ───────
  var HEAT_ROWS = 40; // rows drawn; the rest disclosed below the chart
  function drawHeatmap() {
    // §5.2 fix (operator 2026-07-10): sort by INSTABILITY (on/off flips, tenure tiebreak),
    // not by tenure — top-by-tenure showed the most STABLE tasks, inverting the exhibit's
    // purpose (the volatile flappers were buried). weighted_instability (entropy x remaining
    // duration) is a parked engine artifact; flips is the real instability measure here.
    var rows = TASKS.slice()
      .sort(function (a, b) { return b.flips - a.flips || b.tenure - a.tenure; })
      .slice(0, HEAT_ROWS);
    var W = 960, rowH = 13, padL = 250, padT = 34, padB = 8;
    var H = padT + rows.length * rowH + padB;
    var svg = frame("volHeatmap", W, H, "Critical-path membership heatmap");
    if (!svg) return;
    var cw = (W - padL - 10) / N;
    for (var c = 0; c < N; c++) {
      var hx = padL + c * cw + cw / 2;
      var head = txt(svg, hx, 12, shortLabel(c), { anchor: "middle", weight: c === cursor ? 700 : 400, fill: c === cursor ? ACC : "var(--muted)" });
      head.setAttribute("data-no-i18n", "");
      if (c === cursor) {
        svg.appendChild(svgEl("rect", { x: padL + c * cw, y: padT - 14, width: cw, height: rows.length * rowH + 14, fill: ACC, "fill-opacity": 0.10 }));
      }
    }
    rows.forEach(function (t, r) {
      var ty = padT + r * rowH;
      var lab = txt(svg, padL - 6, ty + rowH - 4, t.uid + " " + t.name.slice(0, 34), { anchor: "end", size: 9 });
      lab.setAttribute("data-no-i18n", "");
      for (var c2 = 0; c2 < N; c2++) {
        var on = t.member[c2] === 1;
        var cell = svgEl("rect", {
          x: padL + c2 * cw + 1, y: ty + 1, width: Math.max(cw - 2, 1), height: rowH - 2,
          fill: on ? (c2 === cursor ? ACC : OK) : "var(--field-bg)",
          "fill-opacity": on ? (c2 === cursor ? 0.95 : 0.65) : 1,
        });
        tip(cell, "UID " + t.uid + " — " + t.name + " · " + V[c2].label + " · " + (on ? "ON the critical path" : "off the path"));
        svg.appendChild(cell);
      }
    });
    if (TASKS.length > rows.length) {
      var note = document.createElement("p");
      note.className = "muted";
      note.textContent = "Top " + rows.length + " of " + TASKS.length + " ever-critical activities shown (by instability: on/off flips, tenure tiebreak) — the scoreboard below lists every one.";
      document.getElementById("volHeatmap").appendChild(note);
    }
  }

  // shared horizontal leaderboard
  function leaderboard(id, items, color, valueLabel, a11y) {
    var W = 460, rowH = 20, padL = 220, padT = 6;
    var H = padT + items.length * rowH + 8;
    var svg = frame(id, W, Math.max(H, 60), a11y);
    if (!svg) return;
    var most = 1;
    items.forEach(function (it) { most = Math.max(most, it.value); });
    items.forEach(function (it, r) {
      var y0 = padT + r * rowH;
      var lab = txt(svg, padL - 6, y0 + 13, it.label.slice(0, 36), { anchor: "end", size: 9 });
      lab.setAttribute("data-no-i18n", "");
      var bw = (it.value / most) * (W - padL - 46);
      var bar = svgEl("rect", { x: padL, y: y0 + 3, width: Math.max(bw, 1), height: rowH - 7, fill: color });
      tip(bar, it.label + " — " + it.value + " " + valueLabel);
      svg.appendChild(bar);
      txt(svg, padL + bw + 4, y0 + 13, String(it.value), { size: 10, weight: 600, fill: "var(--ink)" });
    });
    if (!items.length) txt(svg, 10, 24, "none", {});
  }

  // ── 6. tenure leaderboard ───────────────────────────────────────────────────────────
  function drawTenure() {
    leaderboard(
      "volTenure",
      TASKS.slice(0, 12).map(function (t) { return { label: t.uid + " " + t.name, value: t.tenure }; }),
      OK, "version(s) on the path", "Critical-path tenure leaderboard"
    );
  }

  // ── 7. dwell histogram — distribution of versions-on-path ──────────────────────────
  function drawDwell() {
    var counts = [];
    for (var i = 1; i <= N; i++) counts.push(0);
    TASKS.forEach(function (t) { counts[t.tenure - 1] += 1; });
    var W = 460, H = 220, padL = 36, padR = 10, padT = 16, padB = 34;
    var svg = frame("volDwell", W, H, "Critical-path dwell histogram");
    if (!svg) return;
    var most = Math.max.apply(null, counts.concat([1]));
    var bw = (W - padL - padR) / N;
    counts.forEach(function (cnt, i) {
      var bh = (cnt / most) * (H - padT - padB);
      var bar = svgEl("rect", { x: padL + i * bw + 2, y: H - padB - bh, width: Math.max(bw - 4, 1), height: Math.max(bh, cnt ? 1 : 0), fill: ACC });
      tip(bar, cnt + " activity(ies) spent " + (i + 1) + " version(s) on the critical path");
      svg.appendChild(bar);
      if (cnt) txt(svg, padL + i * bw + bw / 2, H - padB - bh - 3, String(cnt), { anchor: "middle" });
      txt(svg, padL + i * bw + bw / 2, H - padB + 12, String(i + 1), { anchor: "middle" });
    });
    txt(svg, W / 2, H - 4, "versions on the critical path", { anchor: "middle" });
  }

  // ── 8. jumper leaderboard — most on/off flips ───────────────────────────────────────
  function jumpers() {
    return TASKS.filter(function (t) { return t.flips > 1; })
      .slice().sort(function (a, b) { return b.flips - a.flips || b.tenure - a.tenure; });
  }
  function drawJumpers() {
    var j = jumpers().slice(0, 12).map(function (t) { return { label: t.uid + " " + t.name, value: t.flips }; });
    if (!j.length) {
      var h = host("volJumpers");
      if (h) { var p = document.createElement("p"); p.className = "muted"; p.textContent = "No activity left and re-joined the critical path — membership only ever changed once per activity (low volatility)."; h.appendChild(p); }
      return;
    }
    leaderboard("volJumpers", j, BAD, "on/off flip(s)", "Critical-path jumper leaderboard");
  }

  // ── 9. jumper timeline strips — on-path intervals for the top jumpers ──────────────
  function drawStrips() {
    var picks = jumpers().slice(0, 12);
    if (!picks.length) picks = TASKS.slice(0, 8);
    var W = 460, rowH = 18, padL = 190, padT = 22;
    var H = padT + picks.length * rowH + 8;
    var svg = frame("volStrips", W, Math.max(H, 60), "Jumper on-path timeline strips");
    if (!svg) return;
    var cw = (W - padL - 10) / N;
    for (var c = 0; c < N; c++) {
      if (c === cursor) svg.appendChild(svgEl("rect", { x: padL + c * cw, y: padT - 4, width: cw, height: picks.length * rowH + 4, fill: ACC, "fill-opacity": 0.10 }));
    }
    picks.forEach(function (t, r) {
      var y0 = padT + r * rowH;
      var lab = txt(svg, padL - 6, y0 + 12, t.uid + " " + t.name.slice(0, 26), { anchor: "end", size: 9 });
      lab.setAttribute("data-no-i18n", "");
      svg.appendChild(svgEl("line", { x1: padL, y1: y0 + 8, x2: W - 10, y2: y0 + 8, stroke: "var(--line)", "stroke-width": 1 }));
      for (var c2 = 0; c2 < N; c2++) {
        if (t.member[c2] !== 1) continue;
        var seg = svgEl("rect", { x: padL + c2 * cw + 1, y: y0 + 2, width: Math.max(cw - 2, 1), height: 12, rx: 3, fill: BAD, "fill-opacity": 0.8 });
        tip(seg, "UID " + t.uid + " on the path in " + V[c2].label);
        svg.appendChild(seg);
      }
    });
    txt(svg, padL, 12, "filled = on the critical path that version", {});
  }

  // ── 10. transition ribbons — stayed/entered/left for the cursor's pair ─────────────
  function drawRibbon() {
    var W = 460, H = 240;
    var svg = frame("volRibbon", W, H, "Critical-path transition flow");
    if (!svg) return;
    var k = Math.max(1, cursor);
    var p = PAIRS[k - 1];
    var leftTotal = p.stayed + p.left, rightTotal = p.stayed + p.entered;
    var most = Math.max(leftTotal, rightTotal, 1);
    var colW = 46, x0 = 70, x1 = W - 70 - colW, top = 40, span = H - top - 34;
    function col(x, parts, labels, colors, side) {
      var yy = top;
      parts.forEach(function (v, i) {
        var hh = (v / most) * span;
        if (v > 0) {
          var r = svgEl("rect", { x: x, y: yy, width: colW, height: Math.max(hh, 1), fill: colors[i] });
          tip(r, labels[i] + ": " + v);
          svg.appendChild(r);
          txt(svg, side === "l" ? x - 6 : x + colW + 6, yy + hh / 2 + 3, labels[i] + " " + v, { anchor: side === "l" ? "end" : "start", size: 10, fill: colors[i], weight: 600 });
        }
        yy += hh;
      });
    }
    // ribbons between the stayed segments
    var stayedH = (p.stayed / most) * span;
    var ribbon = svgEl("path", {
      d: "M" + (x0 + colW) + " " + top + " C " + (W / 2) + " " + top + ", " + (W / 2) + " " + top + ", " + x1 + " " + top +
        " L" + x1 + " " + (top + stayedH) + " C " + (W / 2) + " " + (top + stayedH) + ", " + (W / 2) + " " + (top + stayedH) + ", " + (x0 + colW) + " " + (top + stayedH) + " Z",
      fill: OK, "fill-opacity": 0.35,
    });
    tip(ribbon, p.stayed + " activities stayed on the path " + p.from + " → " + p.to);
    svg.appendChild(ribbon);
    col(x0, [p.stayed, p.left], ["stayed", "left"], [OK, ACC], "l");
    col(x1, [p.stayed, p.entered], ["stayed", "joined"], [OK, BAD], "r");
    var head = txt(svg, W / 2, 18, p.from + "  →  " + p.to, { anchor: "middle", size: 12, weight: 600, fill: "var(--ink)" });
    head.setAttribute("data-no-i18n", "");
  }

  // ── scoreboard table (sortable) ─────────────────────────────────────────────────────
  var sortKey = "flips", sortDir = -1;
  function drawTable() {
    var mount = document.getElementById("volTable");
    if (!mount) return;
    mount.textContent = "";
    var cols = [
      ["uid", "UID"], ["name", "Activity"], ["tenure", "Versions on path"],
      ["streak", "Longest streak"], ["flips", "Jumps (on/off flips)"], ["now", "On path now"],
    ];
    var rows = TASKS.map(function (t) {
      return { uid: t.uid, name: t.name, tenure: t.tenure, streak: t.streak, flips: t.flips, now: t.member[N - 1] ? "yes" : "no" };
    });
    rows.sort(function (a, b) {
      var av = a[sortKey], bv = b[sortKey];
      if (av === bv) return a.uid - b.uid;
      return (av > bv ? 1 : -1) * sortDir;
    });
    var scroller = document.createElement("div");
    scroller.className = "hist-drill-scroll";
    var table = document.createElement("table");
    table.className = "hist-drill-table";
    var thead = document.createElement("thead");
    var hr = document.createElement("tr");
    cols.forEach(function (c) {
      var th = document.createElement("th");
      th.textContent = c[1] + (sortKey === c[0] ? (sortDir < 0 ? " ▾" : " ▴") : "");
      th.style.cursor = "pointer";
      th.title = "Sort by " + c[1];
      th.addEventListener("click", function () {
        if (sortKey === c[0]) sortDir = -sortDir; else { sortKey = c[0]; sortDir = -1; }
        drawTable();
      });
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = document.createElement("tbody");
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      cols.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = String(r[c[0]]);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    scroller.appendChild(table);
    mount.appendChild(scroller);
  }

  // ── master stepper: one cursor animates churn/flow/area/heatmap/strips/ribbon ──────
  function renderAnimated() {
    var lbl = document.getElementById("volLabel");
    if (lbl) lbl.textContent = (cursor + 1) + " / " + N + " — " + V[cursor].label +
      (V[cursor].status_date ? " (data date " + V[cursor].status_date + ")" : "");
    drawChurn(); drawFlow(); drawArea(); drawHeatmap(); drawStrips(); drawRibbon();
  }
  function stepTo(i) {
    cursor = (i + N) % N;
    renderAnimated();
  }
  function stopPlay() {
    if (timer) { clearInterval(timer); timer = null; }
    var b = document.getElementById("volPlay");
    if (b) b.textContent = "▶ Play";
  }
  function togglePlay() {
    if (timer) { stopPlay(); return; }
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      stepTo(cursor + 1); return;
    }
    var b = document.getElementById("volPlay");
    if (b) b.textContent = "⏸ Pause";
    timer = setInterval(function () { stepTo(cursor + 1); }, 1600);
  }
  var prev = document.getElementById("volPrev");
  var next = document.getElementById("volNext");
  var play = document.getElementById("volPlay");
  if (prev) prev.addEventListener("click", function () { stopPlay(); stepTo(cursor - 1); });
  if (next) next.addEventListener("click", function () { stopPlay(); stepTo(cursor + 1); });
  if (play) play.addEventListener("click", togglePlay);

  drawGauge(); drawTenure(); drawDwell(); drawJumpers(); drawTable();
  renderAnimated();
})();
