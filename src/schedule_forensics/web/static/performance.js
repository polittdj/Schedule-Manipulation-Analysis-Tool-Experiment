/* Schedule Forensics — Performance Analysis Summary (operator 2026-07-10, ADR-0182).
 *
 * Recreates the seven graph families of the operator's PerformanceAnalysisSummary reference
 * workbook as dependency-free SVG over the server-embedded dataset (#perfData — no network
 * call, air-gap posture): G1 work-to-go census (2), G2 bow-wave starts/finishes + cumulative
 * S-curves (3), G3 BEI/HMI execution-index curves (2), G4 workoff burden with the negative
 * backlog mirror (2), G5 duration-ratio S-curve + middle-70% histogram (2), and the three
 * portfolio quads (one dot per loaded version). Index curves stop at the data date and every
 * undefined value is simply not drawn — nothing is imputed client-side.
 */
"use strict";

(function () {
  var dataEl = document.getElementById("perfData");
  if (!dataEl) return;
  var DATA = {};
  try { DATA = JSON.parse(dataEl.textContent || "{}"); } catch (e) { return; }
  var CENSUS = DATA.census || [];
  var FLOW = DATA.flow || [];
  var BURDEN = DATA.burden || [];
  var DRM = DATA.drm || { points: [], bins: [] };
  var QUADS = DATA.quads || [];
  var STATUS = DATA.status_month || null;
  var NS = "http://www.w3.org/2000/svg";
  var OK = "var(--ok)", BAD = "var(--bad)", WARN = "var(--warn)", ACC = "var(--accent)";
  var MUT = "var(--muted)";

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
    var a = { x: x, y: y, fill: (opts && opts.fill) || MUT, "font-size": (opts && opts.size) || 10 };
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
  function frame(id, W, H, label) {
    var h = document.getElementById(id);
    if (!h) return null;
    h.textContent = "";
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y && label) SFA11y.label(svg, label);
    h.appendChild(svg);
    return svg;
  }
  function legend(svg, x, y, items) {
    var cx = x;
    items.forEach(function (it) {
      var mark = svgEl(it.dash ? "line" : "rect",
        it.dash
          ? { x1: cx, y1: y - 3, x2: cx + 14, y2: y - 3, stroke: it.color, "stroke-width": 2, "stroke-dasharray": it.dash === true ? "4 3" : it.dash }
          : { x: cx, y: y - 9, width: 10, height: 8, fill: it.color, opacity: it.op || 1 });
      svg.appendChild(mark);
      var t = txt(svg, cx + (it.dash ? 18 : 14), y, it.label, { size: 9 });
      cx += (it.dash ? 18 : 14) + it.label.length * 5.2 + 14;
      void t;
    });
  }

  /* A shared month-axis cartesian frame: returns {svg,x,y,L,R,T,B} with ticks + DD line. */
  function monthFrame(id, months, ymin, ymax, W, H, label) {
    var svg = frame(id, W, H, label);
    if (!svg) return null;
    var L = 46, R = W - 12, T = 16, B = H - 26;
    var n = Math.max(1, months.length);
    function x(i) { return L + (R - L) * (n === 1 ? 0.5 : i / (n - 1)); }
    function y(v) { return B - (B - T) * ((v - ymin) / ((ymax - ymin) || 1)); }
    svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    svg.appendChild(svgEl("line", { x1: L, y1: T, x2: L, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    var step = Math.max(1, Math.ceil(n / Math.floor((R - L) / 55)));
    for (var i = 0; i < n; i += step) {
      txt(svg, x(i), H - 12, months[i], { anchor: "middle", size: 8.5 });
    }
    for (var g = 0; g <= 4; g++) {
      var vv = ymin + ((ymax - ymin) * g) / 4;
      var yy = y(vv);
      svg.appendChild(svgEl("line", { x1: L, y1: yy, x2: R, y2: yy, stroke: MUT, "stroke-width": 0.25, opacity: 0.5 }));
      txt(svg, L - 4, yy + 3, (Math.abs(vv) >= 10 ? Math.round(vv) : Math.round(vv * 100) / 100), { anchor: "end", size: 8.5 });
    }
    var di = months.indexOf(STATUS);
    if (di >= 0) {
      svg.appendChild(svgEl("line", { x1: x(di), y1: T, x2: x(di), y2: B, stroke: BAD, "stroke-width": 1.2, "stroke-dasharray": "5 4" }));
      txt(svg, x(di) + 3, T + 8, "data date", { fill: BAD, size: 8.5 });
    }
    return { svg: svg, x: x, y: y, L: L, R: R, T: T, B: B, n: n };
  }
  function line(f, vals, color, dash, name) {
    var d = "", started = false;
    for (var i = 0; i < vals.length; i++) {
      if (vals[i] === null || vals[i] === undefined) { started = false; continue; }
      d += (started ? "L" : "M") + f.x(i).toFixed(1) + " " + f.y(vals[i]).toFixed(1) + " ";
      started = true;
    }
    if (!d) return;
    var p = svgEl("path", { d: d, fill: "none", stroke: color, "stroke-width": 1.7 });
    if (dash) p.setAttribute("stroke-dasharray", dash);
    if (name) tip(p, name);
    f.svg.appendChild(p);
  }
  function area(f, vals, color, op, name) {
    var d = "", started = false, firstX = null, lastX = null;
    for (var i = 0; i < vals.length; i++) {
      var v = vals[i] === null || vals[i] === undefined ? 0 : vals[i];
      d += (started ? "L" : "M") + f.x(i).toFixed(1) + " " + f.y(v).toFixed(1) + " ";
      if (!started) firstX = f.x(i);
      lastX = f.x(i);
      started = true;
    }
    if (!d) return;
    d += "L" + lastX.toFixed(1) + " " + f.y(0).toFixed(1) + " L" + firstX.toFixed(1) + " " + f.y(0).toFixed(1) + " Z";
    var p = svgEl("path", { d: d, fill: color, opacity: op || 0.3, stroke: "none" });
    if (name) tip(p, name);
    f.svg.appendChild(p);
  }
  function stackedBars(f, rows, keys, colors, labels, baseKeyNames) {
    var bw = Math.max(1.5, Math.min(9, ((f.R - f.L) / f.n) * 0.55));
    rows.forEach(function (r, i) {
      var up = 0, down = 0;
      keys.forEach(function (k, ki) {
        var v = r[k] || 0;
        if (!v) return;
        var x0 = f.x(i) - bw / 2, yv, hh;
        if (v > 0) { yv = f.y(up + v); hh = f.y(up) - yv; up += v; }
        else { yv = f.y(down); hh = f.y(down + v) - yv; down += v; }
        var rect = svgEl("rect", { x: x0, y: yv, width: bw, height: Math.max(0.6, hh), fill: colors[ki], opacity: 0.9 });
        tip(rect, r.month + " — " + labels[ki] + ": " + v + (baseKeyNames ? "" : ""));
        f.svg.appendChild(rect);
      });
    });
  }

  /* ---------------------------------------------------------------- G1 census */
  function g1(id, totalKey, togoKey, lpKey, names) {
    var months = CENSUS.map(function (m) { return m.month; });
    var maxv = 1;
    CENSUS.forEach(function (m) { maxv = Math.max(maxv, m[totalKey]); });
    var f = monthFrame(id, months, 0, maxv * 1.08, 1240, 440, names.title);
    if (!f) return;
    area(f, CENSUS.map(function (m) { return m[togoKey]; }), WARN, 0.35, names.togo);
    line(f, CENSUS.map(function (m) { return m[totalKey]; }), ACC, null, names.total);
    if (names.done) line(f, CENSUS.map(function (m) { return m.tm_completed; }), OK, null, names.done);
    line(f, CENSUS.map(function (m) { return m[lpKey]; }), BAD, "2 3", names.lp);
    var items = [{ color: WARN, label: names.togo, op: 0.5 }, { color: ACC, label: names.total, dash: "0" }];
    if (names.done) items.push({ color: OK, label: names.done, dash: "0" });
    items.push({ color: BAD, label: names.lp, dash: true });
    legend(f.svg, f.L + 4, f.T + 2, items);
  }
  g1("g1Census", "tm_total", "tm_to_go", "lp_tm",
    { title: "G1 completed vs work-to-go", total: "Active T&M", togo: "To-go", done: "Completed", lp: "Longest path" });
  g1("g1Normal", "normal", "normal_to_go", "lp_normal",
    { title: "G1 work-to-go normal tasks", total: "Active normal tasks", togo: "To-go", done: null, lp: "Longest path" });

  /* ------------------------------------------------------------ G2 flow charts */
  function g2(id, pre, title) {
    var months = FLOW.map(function (m) { return m.month; });
    var maxv = 1;
    FLOW.forEach(function (m) {
      maxv = Math.max(maxv, m["baselined_" + pre], m["scheduled_" + pre], m["actual_" + pre],
        (m[pre === "starts" ? "started_late_30" : "finished_late_30"] || 0)
        + (m[pre === "starts" ? "started_late_60" : "finished_late_60"] || 0)
        + (m[pre === "starts" ? "started_late_over" : "finished_late_over"] || 0));
    });
    var f = monthFrame(id, months, 0, maxv * 1.1, 1240, 440, title);
    if (!f) return;
    var lk = pre === "starts" ? ["started_late_30", "started_late_60", "started_late_over"]
      : ["finished_late_30", "finished_late_60", "finished_late_over"];
    stackedBars(f, FLOW, lk, ["var(--warn)", "var(--accent)", "var(--bad)"],
      ["late ≤30d", "late 31–60d", "late >60d"]);
    line(f, FLOW.map(function (m) { return m["baselined_" + pre]; }), MUT, "5 3", "Baselined");
    line(f, FLOW.map(function (m) { return m["scheduled_" + pre]; }), ACC, null, "Scheduled/forecast");
    line(f, FLOW.map(function (m) { return m["actual_" + pre]; }), OK, null, "Actual");
    legend(f.svg, f.L + 4, f.T + 2, [
      { color: MUT, label: "Baselined", dash: "5 3" }, { color: ACC, label: "Scheduled", dash: "0" },
      { color: OK, label: "Actual", dash: "0" }, { color: WARN, label: "late ≤30d", op: 0.9 },
      { color: ACC, label: "31–60d", op: 0.9 }, { color: BAD, label: ">60d", op: 0.9 },
    ]);
  }
  g2("g2Starts", "starts", "G2 activity starts");
  g2("g2Finishes", "finishes", "G2 activity finishes");

  (function g2cum() {
    var months = FLOW.map(function (m) { return m.month; });
    var maxv = 1;
    FLOW.forEach(function (m) { maxv = Math.max(maxv, m.cum_baselined_starts, m.cum_scheduled_starts, m.cum_baselined_finishes, m.cum_scheduled_finishes); });
    var f = monthFrame("g2Cum", months, 0, maxv * 1.06, 1240, 440, "G2 cumulative S-curves");
    if (!f) return;
    line(f, FLOW.map(function (m) { return m.cum_baselined_starts; }), MUT, null, "Baselined starts (cum)");
    line(f, FLOW.map(function (m) { return m.cum_scheduled_starts; }), ACC, null, "Scheduled starts (cum)");
    line(f, FLOW.map(function (m) { return m.cum_actual_starts; }), OK, null, "Actual starts (cum)");
    line(f, FLOW.map(function (m) { return m.cum_baselined_finishes; }), MUT, "5 3", "Baselined finishes (cum)");
    line(f, FLOW.map(function (m) { return m.cum_scheduled_finishes; }), ACC, "5 3", "Scheduled finishes (cum)");
    line(f, FLOW.map(function (m) { return m.cum_actual_finishes; }), OK, "5 3", "Actual finishes (cum)");
    legend(f.svg, f.L + 4, f.T + 2, [
      { color: MUT, label: "BL starts", dash: "0" }, { color: ACC, label: "Sched starts", dash: "0" },
      { color: OK, label: "Actual starts", dash: "0" }, { color: MUT, label: "BL finishes", dash: "5 3" },
      { color: ACC, label: "Sched finishes", dash: "5 3" }, { color: OK, label: "Actual finishes", dash: "5 3" },
    ]);
  })();

  /* ----------------------------------------------------------- G3 index curves */
  function g3(id, beiKey, hmiKey, rollKey, title) {
    var months = FLOW.map(function (m) { return m.month; });
    var maxv = 1.05;
    FLOW.forEach(function (m) {
      if (m[beiKey] !== null) maxv = Math.max(maxv, m[beiKey]);
      if (m[hmiKey] !== null) maxv = Math.max(maxv, m[hmiKey]);
    });
    var f = monthFrame(id, months, 0, maxv * 1.08, 620, 340, title);
    if (!f) return;
    var yg = f.y(0.95);
    f.svg.appendChild(svgEl("line", { x1: f.L, y1: yg, x2: f.R, y2: yg, stroke: OK, "stroke-width": 0.8, "stroke-dasharray": "3 3" }));
    txt(f.svg, f.R - 2, yg - 3, "0.95 practice band", { anchor: "end", size: 8, fill: OK });
    line(f, FLOW.map(function (m) { return m[beiKey]; }), ACC, null, "BEI (cumulative)");
    line(f, FLOW.map(function (m) { return m[rollKey]; }), WARN, null, "HMI 3-mo rolling");
    FLOW.forEach(function (m, i) {
      if (m[hmiKey] === null || m[hmiKey] === undefined) return;
      var c = svgEl("circle", { cx: f.x(i), cy: f.y(m[hmiKey]), r: 2, fill: WARN, opacity: 0.7 });
      tip(c, m.month + " HMI: " + m[hmiKey]);
      f.svg.appendChild(c);
    });
    legend(f.svg, f.L + 4, f.T + 2, [
      { color: ACC, label: "BEI", dash: "0" }, { color: WARN, label: "HMI (monthly + 3-mo avg)", dash: "0" },
    ]);
  }
  g3("g3Starts", "bei_starts", "hmi_starts", "hmi_starts_roll3", "G3 start indices");
  g3("g3Finishes", "bei_finishes", "hmi_finishes", "hmi_finishes_roll3", "G3 finish indices");

  /* ---------------------------------------------------------- G4 workoff burden */
  function g4(id, pre, title) {
    var months = BURDEN.map(function (m) { return m.month; });
    var maxUp = 1, maxDown = 0;
    var upKeys = [pre + "_bl_plan", pre + "_early", pre + "_workoff", pre + "_past_due", pre + "_delayed"];
    BURDEN.forEach(function (m) {
      var s = 0;
      upKeys.forEach(function (k) { s += m[k] || 0; });
      maxUp = Math.max(maxUp, s);
      maxDown = Math.min(maxDown, m[pre + "_backlog"] || 0);
    });
    var f = monthFrame(id, months, maxDown * 1.15, maxUp * 1.1, 1240, 460, title);
    if (!f) return;
    var zero = f.y(0);
    f.svg.appendChild(svgEl("line", { x1: f.L, y1: zero, x2: f.R, y2: zero, stroke: MUT, "stroke-width": 0.8 }));
    stackedBars(f, BURDEN, upKeys.concat([pre + "_backlog"]),
      ["var(--ok)", "var(--accent)", "var(--warn)", "var(--bad)", "#b58cff", "var(--muted)"],
      ["On plan", "Early", "Workoff (was past-due)", "Past-due, forecast here", "Future baseline, slipped here", "Backlog at its baselined month"]);
    legend(f.svg, f.L + 4, f.T + 2, [
      { color: OK, label: "On plan", op: 0.9 }, { color: ACC, label: "Early", op: 0.9 },
      { color: WARN, label: "Workoff done", op: 0.9 }, { color: BAD, label: "Past-due → forecast", op: 0.9 },
      { color: "#b58cff", label: "Future BL slipped", op: 0.9 }, { color: MUT, label: "Backlog (below axis)", op: 0.9 },
    ]);
  }
  g4("g4Starts", "s", "G4 workoff burden starts");
  g4("g4Finishes", "f", "G4 workoff burden finishes");

  /* -------------------------------------------------------- G5 duration ratio */
  (function g5curve() {
    var pts = DRM.points || [];
    var svg = frame("g5Scurve", 620, 340, "G5 duration ratio S-curve");
    if (!svg) return;
    if (!pts.length) { txt(svg, 310, 170, "No completed tasks with a baseline duration.", { anchor: "middle" }); return; }
    var L = 46, R = 606, T = 16, B = 312;
    var bins = DRM.bins || [];
    var xmax = Math.max(2, bins.length ? bins[bins.length - 1].hi * 1.5 : 2);
    var clamped = 0;
    function x(v) { if (v > xmax) { return R; } return L + (R - L) * (v / xmax); }
    function y(p) { return B - (B - T) * p; }
    svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    svg.appendChild(svgEl("line", { x1: L, y1: T, x2: L, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    for (var g = 0; g <= 4; g++) {
      txt(svg, L - 4, y(g / 4) + 3, (g * 25) + "%", { anchor: "end", size: 8.5 });
      txt(svg, L + (R - L) * (g / 4), B + 12, (Math.round(xmax * (g / 4) * 100) / 100).toString(), { anchor: "middle", size: 8.5 });
    }
    var x1 = x(1);
    svg.appendChild(svgEl("line", { x1: x1, y1: T, x2: x1, y2: B, stroke: OK, "stroke-width": 0.8, "stroke-dasharray": "3 3" }));
    txt(svg, x1 + 3, T + 8, "DRM 1.0 = on-baseline", { size: 8, fill: OK });
    var d = "";
    pts.forEach(function (p, i) {
      if (p.drm > xmax) clamped++;
      d += (i ? "L" : "M") + x(Math.min(p.drm, xmax)).toFixed(1) + " " + y(p.cum_prob).toFixed(1) + " ";
    });
    svg.appendChild(svgEl("path", { d: d, fill: "none", stroke: ACC, "stroke-width": 1.6 }));
    var step = Math.max(1, Math.floor(pts.length / 160));
    for (var i = 0; i < pts.length; i += step) {
      var p = pts[i];
      var c = svgEl("circle", { cx: x(Math.min(p.drm, xmax)), cy: y(p.cum_prob), r: 1.8, fill: ACC, opacity: 0.55 });
      tip(c, "UID " + p.uid + " " + p.name + " — DRM " + p.drm + " (baseline " + p.baseline_days + "d → actual " + p.actual_days + "d)");
      svg.appendChild(c);
    }
    txt(svg, R, B + 12, "DRM (actual ÷ baseline duration)" + (clamped ? " — " + clamped + " point(s) beyond axis cap " + xmax : ""), { anchor: "end", size: 8.5 });
  })();

  (function g5hist() {
    var bins = DRM.bins || [];
    var svg = frame("g5Hist", 620, 320, "G5 duration ratio histogram");
    if (svg) {
      if (!bins.length) { txt(svg, 310, 160, "No histogram (no qualifying completed tasks).", { anchor: "middle" }); }
      else {
        var L = 46, R = 606, T = 16, B = 286;
        var maxc = 1;
        bins.forEach(function (b) { maxc = Math.max(maxc, b.count); });
        svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
        var bw = (R - L) / bins.length;
        bins.forEach(function (b, i) {
          var hh = (B - T) * (b.count / maxc);
          var rect = svgEl("rect", { x: L + i * bw + 1, y: B - hh, width: Math.max(1, bw - 2), height: hh, fill: ACC, opacity: 0.8 });
          tip(rect, b.lo + " – " + b.hi + ": " + b.count + " task(s)");
          svg.appendChild(rect);
          if (i % Math.max(1, Math.ceil(bins.length / 8)) === 0) {
            txt(svg, L + i * bw, B + 12, String(b.lo), { size: 8.5 });
          }
        });
        var lo = bins[0].lo, hi = bins[bins.length - 1].hi;
        if (lo < 1 && hi > 1) {
          var xg = L + (R - L) * ((1 - lo) / (hi - lo));
          svg.appendChild(svgEl("line", { x1: xg, y1: T, x2: xg, y2: B, stroke: OK, "stroke-width": 0.8, "stroke-dasharray": "3 3" }));
          txt(svg, xg + 3, T + 8, "1.0", { size: 8, fill: OK });
        }
        txt(svg, R, B + 12, String(hi), { anchor: "end", size: 8.5 });
      }
    }
    var stats = document.getElementById("g5Stats");
    if (stats) {
      stats.textContent = "";
      [["n (completed w/ baseline)", DRM.n], ["min DRM", DRM.min], ["average DRM", DRM.avg],
       ["max DRM", DRM.max], ["excluded (no baseline duration)", DRM.excluded]].forEach(function (kv) {
        var chip = document.createElement("span");
        chip.className = "stat-chip";
        chip.textContent = kv[0] + ": " + (kv[1] === null || kv[1] === undefined ? "N/A" : kv[1]);
        stats.appendChild(chip);
      });
    }
  })();

  /* ------------------------------------------------------------ portfolio quads */
  function quad(id, xKey, yKey, opts) {
    var svg = frame(id, 620, 360, opts.title);
    if (!svg) return;
    var pts = QUADS.filter(function (q) { return q[xKey] !== null && q[xKey] !== undefined && q[yKey] !== null && q[yKey] !== undefined; });
    var skipped = QUADS.length - pts.length;
    if (!pts.length) { txt(svg, 310, 180, "No version has both measures defined (N/A).", { anchor: "middle" }); return; }
    var L = 52, R = 606, T = 18, B = 316;
    var xmax = opts.xmax, ymax = opts.ymax;
    pts.forEach(function (p) { xmax = Math.max(xmax, p[xKey] * 1.15); ymax = Math.max(ymax, p[yKey] * 1.15); });
    function x(v) { return L + (R - L) * (v / xmax); }
    function y(v) { return B - (B - T) * (v / ymax); }
    svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    svg.appendChild(svgEl("line", { x1: L, y1: T, x2: L, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    for (var g = 0; g <= 4; g++) {
      txt(svg, L + (R - L) * (g / 4), B + 12, String(Math.round(xmax * (g / 4) * 100) / 100), { anchor: "middle", size: 8.5 });
      txt(svg, L - 4, y(ymax * (g / 4)) + 3, String(Math.round(ymax * (g / 4) * 100) / 100), { anchor: "end", size: 8.5 });
    }
    if (opts.xGuide !== null) {
      var gx = x(opts.xGuide);
      svg.appendChild(svgEl("line", { x1: gx, y1: T, x2: gx, y2: B, stroke: OK, "stroke-width": 0.9, "stroke-dasharray": "4 3" }));
      txt(svg, gx + 3, T + 9, opts.xGuideLabel, { size: 8, fill: OK });
    }
    if (opts.yGuide !== null) {
      var gy = y(opts.yGuide);
      svg.appendChild(svgEl("line", { x1: L, y1: gy, x2: R, y2: gy, stroke: OK, "stroke-width": 0.9, "stroke-dasharray": "4 3" }));
      txt(svg, R - 2, gy - 3, opts.yGuideLabel, { anchor: "end", size: 8, fill: OK });
    }
    pts.forEach(function (p, i) {
      var short = "V" + (QUADS.indexOf(p) + 1);
      var c = svgEl("circle", { cx: x(p[xKey]), cy: y(p[yKey]), r: 6, fill: ACC, opacity: 0.75, stroke: "var(--panel)", "stroke-width": 1 });
      tip(c, p.label + " — " + opts.xLabel + ": " + p[xKey] + ", " + opts.yLabel + ": " + p[yKey]);
      svg.appendChild(c);
      txt(svg, x(p[xKey]) + 8, y(p[yKey]) + 3, short + " " + p.label.slice(0, 18), { size: 8.5 });
      void i;
    });
    txt(svg, R, B - 4, opts.xLabel, { anchor: "end", size: 9, weight: "bold" });
    txt(svg, L + 4, T + 9, opts.yLabel, { size: 9, weight: "bold" });
    if (skipped) txt(svg, L + 4, B - 4, skipped + " version(s) N/A (undefined measure) — not plotted", { size: 8 });
  }
  quad("quadHmiCei", "hmi", "cei", {
    title: "HMI vs CEI per version", xLabel: "HMI (tasks)", yLabel: "CEI (finish)",
    xmax: 1.05, ymax: 1.05, xGuide: 0.95, xGuideLabel: "0.95", yGuide: 0.95, yGuideLabel: "0.95 practice band",
  });
  quad("quadRatio", "start_ratio", "finish_ratio", {
    title: "To-go starts vs finishes ratio per version", xLabel: "To-go starts ÷ baseline remaining",
    yLabel: "To-go finishes ÷ baseline remaining",
    xmax: 2, ymax: 2, xGuide: 1, xGuideLabel: "1.0 = as planned", yGuide: 1, yGuideLabel: "1.0 = as planned",
  });
  (function () {
    var shares = QUADS.map(function (q) { return q.cp_share; }).filter(function (v) { return v !== null && v !== undefined; }).sort(function (a, b) { return a - b; });
    var median = shares.length ? shares[Math.floor((shares.length - 1) / 2)] : null;
    quad("quadBeiCp", "bei", "cp_share", {
      title: "BEI vs critical share of to-go work", xLabel: "BEI", yLabel: "critical ÷ to-go T&M",
      xmax: 1.05, ymax: 1.0, xGuide: 0.95, xGuideLabel: "BEI 0.95 (DCMA)",
      yGuide: median, yGuideLabel: median === null ? "" : "portfolio median " + median,
    });
  })();
})();
