/* Schedule Forensics — Executive Margin Dashboard (NASA Margin/Contingency Burn-Down + MET).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Two charts over the server-embedded dataset
 * (#marginDashData, no network call): a per-status-date burn-down stacking effective schedule
 * margin (work days) with contingency (weekends + holidays to the target) against the NASA
 * Gold-Rule requirement line — a bar turns red the month margin falls below it (the trigger for
 * action); and the Margin Erosion Trend, effective margin over the status dates with a
 * least-squares line extrapolated to the projected zero-margin date. Nothing is imputed: an
 * undefined figure is simply not drawn.
 */
"use strict";

(function () {
  var el = document.getElementById("marginDashData");
  if (!el) return;
  var DATA = {};
  try { DATA = JSON.parse(el.textContent || "{}"); } catch (e) { return; }
  var MONTHS = (DATA.months || []).filter(function (m) { return m.status_date; });
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
      var mark = svgEl(it.dash ? "line" : "rect", it.dash
        ? { x1: cx, y1: y - 3, x2: cx + 14, y2: y - 3, stroke: it.color, "stroke-width": 2, "stroke-dasharray": it.dash === true ? "4 3" : it.dash }
        : { x: cx, y: y - 9, width: 10, height: 8, fill: it.color, opacity: it.op || 0.9 });
      svg.appendChild(mark);
      txt(svg, cx + (it.dash ? 18 : 14), y, it.label, { size: 9 });
      cx += (it.dash ? 18 : 14) + it.label.length * 5.2 + 14;
    });
  }
  function shortDate(iso) { return iso ? iso.slice(0, 7) : ""; }  // YYYY-MM

  /* ---------------------------------------------------- burn-down: margin + contingency bars */
  function renderBurndown() {
    var svg = frame("marginBurndownChart", 720, 360, "Margin and contingency burn-down by status date");
    if (!svg) return;
    if (!MONTHS.length) { txt(svg, 360, 180, "No dated versions loaded.", { anchor: "middle" }); return; }
    var L = 48, R = 708, T = 20, B = 330;
    var maxv = 1;
    MONTHS.forEach(function (m) { maxv = Math.max(maxv, m.total_available, m.nasa_rqmt_wd); });
    var n = MONTHS.length;
    function x(i) { return L + (R - L) * (n === 1 ? 0.5 : i / (n - 1)); }
    function y(v) { return B - (B - T) * (v / (maxv * 1.08)); }
    svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    svg.appendChild(svgEl("line", { x1: L, y1: T, x2: L, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    for (var g = 0; g <= 4; g++) {
      var vv = maxv * 1.08 * g / 4, yy = y(vv);
      svg.appendChild(svgEl("line", { x1: L, y1: yy, x2: R, y2: yy, stroke: MUT, "stroke-width": 0.2, opacity: 0.5 }));
      txt(svg, L - 4, yy + 3, Math.round(vv), { anchor: "end", size: 8.5 });
    }
    var bw = Math.max(3, Math.min(26, (R - L) / n * 0.5));
    MONTHS.forEach(function (m, i) {
      var x0 = x(i) - bw / 2;
      // margin (work days) at the base — red when below the NASA requirement (the trigger)
      var marginColor = m.below_requirement ? BAD : OK;
      var ym = y(m.effective_margin_wd), hm = y(0) - ym;
      var rMar = svgEl("rect", { x: x0, y: ym, width: bw, height: Math.max(0.5, hm), fill: marginColor, opacity: 0.92 });
      tip(rMar, m.status_date + " — effective margin " + m.effective_margin_wd + " wd" + (m.below_requirement ? " (BELOW requirement — trigger)" : ""));
      svg.appendChild(rMar);
      // contingency (weekends + holidays) stacked above
      var yc = y(m.total_available), hc = ym - yc;
      var rCon = svgEl("rect", { x: x0, y: yc, width: bw, height: Math.max(0.5, hc), fill: ACC, opacity: 0.55 });
      tip(rCon, m.status_date + " — contingency " + m.contingency_wd + " days (total available " + m.total_available + ")");
      svg.appendChild(rCon);
      // planned margin at the period START (prior month-end) — a tick showing what was consumed
      if (m.planned_margin_wd != null) {
        var yp = y(m.planned_margin_wd);
        var tick = svgEl("line", { x1: x0 - 2, y1: yp, x2: x0 + bw + 2, y2: yp, stroke: MUT, "stroke-width": 1.6 });
        tip(tick, m.status_date + " — planned (period start) " + m.planned_margin_wd + " wd; consumed " + m.consumed_wd + " wd this period");
        svg.appendChild(tick);
      }
      if (n <= 24) txt(svg, x(i), B + 12, shortDate(m.status_date), { anchor: "middle", size: 8 });
    });
    // NASA Gold-Rule requirement line (per month)
    var d = "";
    MONTHS.forEach(function (m, i) { d += (i ? "L" : "M") + x(i).toFixed(1) + " " + y(m.nasa_rqmt_wd).toFixed(1) + " "; });
    var reqPath = svgEl("path", { d: d, fill: "none", stroke: WARN, "stroke-width": 1.8, "stroke-dasharray": "5 3" });
    tip(reqPath, "NASA Gold-Rule requirement (30 work-days per program year)");
    svg.appendChild(reqPath);
    legend(svg, L + 4, T + 2, [
      { color: OK, label: "Effective margin (wd)" },
      { color: ACC, label: "Contingency (days)", op: 0.55 },
      { color: BAD, label: "Below requirement" },
      { color: WARN, label: "NASA requirement", dash: "5 3" },
      { color: MUT, label: "Planned (period start)", dash: "0" },
    ]);
    txt(svg, R, B + 12, "status date", { anchor: "end", size: 8.5 });
  }

  /* ------------------------------------------------------ MET: erosion line + zero-margin date */
  function renderErosion() {
    var svg = frame("marginErosionChart", 720, 340, "Margin erosion trend");
    if (!svg) return;
    var pts = MONTHS.map(function (m) { return { t: Date.parse(m.status_date + "T00:00:00Z"), y: m.effective_margin_wd, iso: m.status_date }; });
    if (pts.length < 2) { txt(svg, 360, 170, "Load 2+ dated versions to fit an erosion trend.", { anchor: "middle" }); return; }
    var L = 48, R = 708, T = 20, B = 300;
    var zeroT = DATA.zero_margin_date ? Date.parse(DATA.zero_margin_date + "T00:00:00Z") : null;
    var tmin = pts[0].t, tmax = pts[pts.length - 1].t;
    if (zeroT && zeroT > tmax) tmax = zeroT;
    var ymax = 1;
    pts.forEach(function (p) { ymax = Math.max(ymax, p.y); });
    function x(t) { return L + (R - L) * (tmax === tmin ? 0.5 : (t - tmin) / (tmax - tmin)); }
    function y(v) { return B - (B - T) * (v / (ymax * 1.1)); }
    svg.appendChild(svgEl("line", { x1: L, y1: B, x2: R, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    svg.appendChild(svgEl("line", { x1: L, y1: T, x2: L, y2: B, stroke: MUT, "stroke-width": 0.6 }));
    for (var g = 0; g <= 4; g++) {
      var vv = ymax * 1.1 * g / 4, yy = y(vv);
      svg.appendChild(svgEl("line", { x1: L, y1: yy, x2: R, y2: yy, stroke: MUT, "stroke-width": 0.2, opacity: 0.5 }));
      txt(svg, L - 4, yy + 3, Math.round(vv), { anchor: "end", size: 8.5 });
    }
    // least-squares line (mirror the server fit) drawn across the visible time span
    var n = pts.length, t0 = pts[0].t, DAYMS = 86400000;
    var xs = pts.map(function (p) { return (p.t - t0) / DAYMS; });
    var ys = pts.map(function (p) { return p.y; });
    var mx = xs.reduce(function (a, b) { return a + b; }, 0) / n;
    var my = ys.reduce(function (a, b) { return a + b; }, 0) / n;
    var sxx = 0, sxy = 0;
    for (var i = 0; i < n; i++) { sxx += (xs[i] - mx) * (xs[i] - mx); sxy += (xs[i] - mx) * (ys[i] - my); }
    if (sxx > 0) {
      var slope = sxy / sxx, intercept = my - slope * mx;
      function fit(t) { return intercept + slope * (t - t0) / DAYMS; }
      var trend = svgEl("line", {
        x1: x(tmin), y1: y(Math.max(0, fit(tmin))), x2: x(tmax), y2: y(Math.max(0, fit(tmax))),
        stroke: WARN, "stroke-width": 1.6, "stroke-dasharray": "6 4",
      });
      tip(trend, "least-squares erosion trend");
      svg.appendChild(trend);
    }
    // the actual margin line + markers
    var dd = "";
    pts.forEach(function (p, i) { dd += (i ? "L" : "M") + x(p.t).toFixed(1) + " " + y(p.y).toFixed(1) + " "; });
    svg.appendChild(svgEl("path", { d: dd, fill: "none", stroke: ACC, "stroke-width": 1.8 }));
    pts.forEach(function (p) {
      var c = svgEl("circle", { cx: x(p.t), cy: y(p.y), r: 3, fill: ACC });
      tip(c, p.iso + " — effective margin " + p.y + " wd");
      svg.appendChild(c);
      if (n <= 24) txt(svg, x(p.t), B + 12, shortDate(p.iso), { anchor: "middle", size: 8 });
    });
    // projected zero-margin date marker
    if (zeroT) {
      var zx = x(zeroT);
      svg.appendChild(svgEl("line", { x1: zx, y1: T, x2: zx, y2: B, stroke: BAD, "stroke-width": 1.2, "stroke-dasharray": "3 3" }));
      var tri = svgEl("path", { d: "M" + (zx - 5) + " " + B + " L" + (zx + 5) + " " + B + " L" + zx + " " + (B - 9) + " Z", fill: BAD });
      tip(tri, "projected zero-margin date " + DATA.zero_margin_date);
      svg.appendChild(tri);
      txt(svg, zx, T + 8, "zero margin " + shortDate(DATA.zero_margin_date), { anchor: zx > R - 90 ? "end" : "start", fill: BAD, size: 8.5 });
    }
    var rate = DATA.erosion_wd_per_month;
    legend(svg, L + 4, T + 2, [
      { color: ACC, label: "Effective margin (wd)" },
      { color: WARN, label: "Erosion trend" + (rate ? " (" + rate + " wd/mo)" : ""), dash: "6 4" },
      { color: BAD, label: "Zero-margin date", dash: "3 3" },
    ]);
    txt(svg, R, B + 12, "status date", { anchor: "end", size: 8.5 });
  }

  renderBurndown();
  renderErosion();
  if (window.SFChartFrame && SFChartFrame.scan) SFChartFrame.scan();
})();
