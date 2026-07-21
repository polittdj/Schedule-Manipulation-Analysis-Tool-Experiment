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
  // Each non-static entry is a clickable <g data-series-toggle> so SFLegend (ADR-0276) shows/hides the
  // matching data-series mark(s); the key is it.key||it.label. A `static:true` entry renders as a
  // plain, NON-clickable color key — e.g. "Below requirement" is a per-month RE-COLORING of the margin
  // bars (a threshold state), not a separable series, so it explains a color rather than toggling one.
  // A trailing "all / none" control toggles every togglable series. (These charts render once — not an
  // animation stepper — so the legend's svg scope is stable; no data-series-scope host marker needed.)
  function legend(svg, x, y, items) {
    // wraps to the next row instead of overflowing the frame (the burn-down now carries 7 items)
    var cx = x, cy = y, MAXX = 700, toggles = 0;
    function wrap(w) { if (cx + w > MAXX && cx > x) { cx = x; cy += 13; } }
    items.forEach(function (it) {
      var w = (it.dash ? 18 : 14) + it.label.length * 5.2 + 14;
      wrap(w);
      var parent = svg;
      if (!it.static) {
        var g = svgEl("g", {
          "data-series-toggle": it.key || it.label, role: "button", tabindex: "0",
          "aria-pressed": "true", "aria-label": "Show / hide " + it.label,
        });
        g.style.cursor = "pointer";
        svg.appendChild(g);
        parent = g;
        toggles += 1;
      }
      var mark = svgEl(it.dash ? "line" : "rect", it.dash
        ? { x1: cx, y1: cy - 3, x2: cx + 14, y2: cy - 3, stroke: it.color, "stroke-width": 2, "stroke-dasharray": it.dash === true ? "4 3" : it.dash }
        : { x: cx, y: cy - 9, width: 10, height: 8, fill: it.color, opacity: it.op || 0.9 });
      parent.appendChild(mark);
      txt(parent, cx + (it.dash ? 18 : 14), cy, it.label, { size: 9 });
      // a transparent hit area so the whole entry (not just the glyphs) is a click target
      if (!it.static) parent.appendChild(svgEl("rect", { x: cx - 1, y: cy - 11, width: w, height: 14, fill: "transparent" }));
      cx += w;
    });
    if (toggles > 1) {
      wrap(54);
      var ctrl = svgEl("g", { "data-series-all": "1", role: "button", tabindex: "0", "aria-label": "Show all series, or hide all" });
      ctrl.style.cursor = "pointer";
      txt(ctrl, cx + 2, cy, "all / none", { size: 9, fill: "var(--focus)" });
      ctrl.appendChild(svgEl("rect", { x: cx, y: cy - 11, width: 52, height: 14, fill: "transparent" }));
      svg.appendChild(ctrl);
    }
  }
  function shortDate(iso) { return iso ? iso.slice(0, 7) : ""; }  // YYYY-MM

  /* ---------------------------------------------------- burn-down: margin + contingency bars */
  function renderBurndown() {
    var svg = frame("marginBurndownChart", 720, 360, "Margin and contingency burn-down by status date");
    if (!svg) return;
    if (!MONTHS.length) { txt(svg, 360, 180, "No dated versions loaded.", { anchor: "middle" }); return; }
    var L = 48, R = 708, T = 20, B = 330;
    // Fig 5-30 guideline band (ADR-0254): per-month expected-margin (low, high) edges, present
    // only when the operator entered the phase dates. Month verdicts are null on a mixed
    // work-day basis (the server suppressed them — disclosed, not fabricated).
    var BAND = DATA.band || null;
    var bandByIso = {};
    if (BAND) (BAND.months || []).forEach(function (b) { bandByIso[b.date] = b; });
    var maxv = 1;
    MONTHS.forEach(function (m) {
      maxv = Math.max(maxv, m.total_available, m.nasa_rqmt_wd);
      var b = bandByIso[m.status_date];
      if (b) maxv = Math.max(maxv, b.high_wd);
    });
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
    // band polygon UNDER the bars: top edge = high, bottom edge = low, at each month's x
    var bandPts = MONTHS.map(function (m, i) { return { i: i, b: bandByIso[m.status_date] }; })
      .filter(function (p) { return p.b; });
    var bw = Math.max(3, Math.min(26, (R - L) / n * 0.5));
    if (bandPts.length >= 1) {
      // a single dated month has no polygon width — draw a bar-width segment so the band the
      // legend advertises is actually visible (audit F3, ADR-0256)
      var xAt = function (i) { return bandPts.length === 1 ? [x(i) - bw, x(i) + bw] : [x(i), x(i)]; };
      var dPoly = "";
      bandPts.forEach(function (p, k) {
        var xs2 = xAt(p.i);
        dPoly += (k ? "L" : "M") + xs2[0].toFixed(1) + " " + y(p.b.high_wd).toFixed(1) + " ";
        if (bandPts.length === 1) dPoly += "L" + xs2[1].toFixed(1) + " " + y(p.b.high_wd).toFixed(1) + " ";
      });
      for (var k2 = bandPts.length - 1; k2 >= 0; k2--) {
        var xs3 = xAt(bandPts[k2].i);
        if (bandPts.length === 1) dPoly += "L" + xs3[1].toFixed(1) + " " + y(bandPts[k2].b.low_wd).toFixed(1) + " ";
        dPoly += "L" + xs3[0].toFixed(1) + " " + y(bandPts[k2].b.low_wd).toFixed(1) + " ";
      }
      var poly = svgEl("path", { d: dPoly + "Z", fill: ACC, opacity: 0.14, stroke: "none", "data-series": "Fig 5-30 band (operator-set)" });
      tip(poly, "Fig 5-30 guideline band (operator-set rates; SMH §5.5.11.2 / §7.3.3.1.6)");
      svg.appendChild(poly);
    }
    MONTHS.forEach(function (m, i) {
      var x0 = x(i) - bw / 2;
      // margin (work days) at the base — red when below the NASA requirement (the trigger)
      var marginColor = m.below_requirement ? BAD : OK;
      var ym = y(m.effective_margin_wd), hm = y(0) - ym;
      // one series regardless of the per-month color (green above / red below the requirement); the
      // "Below requirement" legend entry is a static color key, not a separate togglable series.
      var rMar = svgEl("rect", { x: x0, y: ym, width: bw, height: Math.max(0.5, hm), fill: marginColor, opacity: 0.92, "data-series": "Effective margin (wd)" });
      tip(rMar, m.status_date + " — effective margin " + m.effective_margin_wd + " wd" + (m.below_requirement ? " (BELOW requirement — trigger)" : ""));
      svg.appendChild(rMar);
      // contingency (weekends + holidays) stacked above
      var yc = y(m.total_available), hc = ym - yc;
      var rCon = svgEl("rect", { x: x0, y: yc, width: bw, height: Math.max(0.5, hc), fill: ACC, opacity: 0.55, "data-series": "Contingency (days)" });
      tip(rCon, m.status_date + " — contingency " + m.contingency_wd + " days (total available " + m.total_available + ")");
      svg.appendChild(rCon);
      // planned margin at the period START (prior month-end) — a tick showing what was consumed
      if (m.planned_margin_wd != null) {
        var yp = y(m.planned_margin_wd);
        var tick = svgEl("line", { x1: x0 - 2, y1: yp, x2: x0 + bw + 2, y2: yp, stroke: MUT, "stroke-width": 1.6, "data-series": "Planned depletion" });
        tip(tick, m.status_date + " — planned (period start) " + m.planned_margin_wd + " wd; consumed " + m.consumed_wd + " wd this period");
        svg.appendChild(tick);
      }
      // corrective-action flag: >=50% of the planned margin consumed this period — the Schedule
      // Management Handbook's EXAMPLE corrective-action threshold (§7.3.3.2.3 Sufficiency of
      // Margin; citation corrected from §7.3.3.1.6, ADR-0254). A caret above the stack.
      if (m.corrective_action) {
        var yt = y(m.total_available);
        var mk = svgEl("path", { d: "M" + (x(i) - 5) + " " + (yt - 6) + " L" + (x(i) + 5) + " " + (yt - 6) + " L" + x(i) + " " + (yt - 14) + " Z", fill: WARN, "data-series": "Corrective ≥ 50%" });
        tip(mk, m.status_date + " — " + (m.consumed_pct != null ? Math.round(100 * m.consumed_pct) : "50+") + "% of planned margin consumed (>=50% — the Schedule Management Handbook's example corrective-action threshold, §7.3.3.2.3)");
        svg.appendChild(mk);
      }
      // Fig 5-30 guideline deviation: a hollow diamond at the month's effective margin when it
      // sits BELOW the operator-set band's low edge (§7.3.3.1.6: deviations from the guidelines
      // trigger an explanation or mitigation).
      var bnd = bandByIso[m.status_date];
      if (bnd && bnd.position === "below") {
        var yd = y(m.effective_margin_wd);
        var dia = svgEl("path", {
          d: "M" + x(i) + " " + (yd - 6) + " L" + (x(i) + 6) + " " + yd + " L" + x(i) + " " + (yd + 6) + " L" + (x(i) - 6) + " " + yd + " Z",
          fill: "none", stroke: BAD, "stroke-width": 1.6, "data-series": "Fig 5-30 band (operator-set)",
        });
        tip(dia, m.status_date + " — effective margin " + m.effective_margin_wd + " wd is BELOW the Fig 5-30 guideline band (" + bnd.low_wd + "-" + bnd.high_wd + " wd; operator-set rates, SMH §5.5.11.2 / §7.3.3.1.6)");
        svg.appendChild(dia);
      }
      if (n <= 24) txt(svg, x(i), B + 12, shortDate(m.status_date), { anchor: "middle", size: 8 });
    });
    // planned-depletion line: connect each month's period-start planned margin (dashed), so the
    // planned trajectory reads against the actual bars.
    var pd = "", pstarted = false;
    MONTHS.forEach(function (m, i) {
      if (m.planned_margin_wd == null) return;
      pd += (pstarted ? "L" : "M") + x(i).toFixed(1) + " " + y(m.planned_margin_wd).toFixed(1) + " ";
      pstarted = true;
    });
    if (pd) {
      var pline = svgEl("path", { d: pd, fill: "none", stroke: MUT, "stroke-width": 1.4, "stroke-dasharray": "2 2", "data-series": "Planned depletion" });
      tip(pline, "planned margin (period-start, carried forward)");
      svg.appendChild(pline);
    }
    // NASA Gold-Rule requirement line (per month)
    var d = "";
    MONTHS.forEach(function (m, i) { d += (i ? "L" : "M") + x(i).toFixed(1) + " " + y(m.nasa_rqmt_wd).toFixed(1) + " "; });
    var reqPath = svgEl("path", { d: d, fill: "none", stroke: WARN, "stroke-width": 1.8, "stroke-dasharray": "5 3", "data-series": "NASA requirement" });
    tip(reqPath, "NASA Gold-Rule requirement (" + (DATA.gold_rule_per_year || 30) + " work-days per program year; operator-set, ADR-0253)");
    svg.appendChild(reqPath);
    var legendItems = [
      { color: OK, label: "Effective margin (wd)" },
      { color: ACC, label: "Contingency (days)", op: 0.55 },
      // a static color key: the same margin bars, re-colored red the months they breach the
      // requirement — a threshold state of "Effective margin", not a separately togglable series.
      { color: BAD, label: "Below requirement", static: true },
      { color: WARN, label: "NASA requirement", dash: "5 3" },
      { color: MUT, label: "Planned depletion", dash: "2 2" },
      { color: WARN, label: "Corrective ≥ 50%" },
    ];
    if (bandPts.length) legendItems.push({ color: ACC, label: "Fig 5-30 band (operator-set)", op: 0.2 });
    legend(svg, L + 4, T + 2, legendItems);
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
        stroke: WARN, "stroke-width": 1.6, "stroke-dasharray": "6 4", "data-series": "Erosion trend",
      });
      tip(trend, "least-squares erosion trend");
      svg.appendChild(trend);
    }
    // the actual margin line + markers
    var dd = "";
    pts.forEach(function (p, i) { dd += (i ? "L" : "M") + x(p.t).toFixed(1) + " " + y(p.y).toFixed(1) + " "; });
    svg.appendChild(svgEl("path", { d: dd, fill: "none", stroke: ACC, "stroke-width": 1.8, "data-series": "Effective margin (wd)" }));
    pts.forEach(function (p) {
      var c = svgEl("circle", { cx: x(p.t), cy: y(p.y), r: 3, fill: ACC, "data-series": "Effective margin (wd)" });
      tip(c, p.iso + " — effective margin " + p.y + " wd");
      svg.appendChild(c);
      if (n <= 24) txt(svg, x(p.t), B + 12, shortDate(p.iso), { anchor: "middle", size: 8 });
    });
    // projected zero-margin date marker
    if (zeroT) {
      var zx = x(zeroT);
      // the three parts of the zero-margin marker share one series key so the legend hides them together
      svg.appendChild(svgEl("line", { x1: zx, y1: T, x2: zx, y2: B, stroke: BAD, "stroke-width": 1.2, "stroke-dasharray": "3 3", "data-series": "Zero-margin date" }));
      var tri = svgEl("path", { d: "M" + (zx - 5) + " " + B + " L" + (zx + 5) + " " + B + " L" + zx + " " + (B - 9) + " Z", fill: BAD, "data-series": "Zero-margin date" });
      tip(tri, "projected zero-margin date " + DATA.zero_margin_date);
      svg.appendChild(tri);
      var zt = txt(svg, zx, T + 8, "zero margin " + shortDate(DATA.zero_margin_date), { anchor: zx > R - 90 ? "end" : "start", fill: BAD, size: 8.5 });
      zt.setAttribute("data-series", "Zero-margin date");
    }
    var rate = DATA.erosion_wd_per_month;
    legend(svg, L + 4, T + 2, [
      { color: ACC, label: "Effective margin (wd)" },
      // explicit stable key: the label carries a dynamic rate, but the mark's data-series does not
      { color: WARN, label: "Erosion trend" + (rate ? " (" + rate + " wd/mo)" : ""), dash: "6 4", key: "Erosion trend" },
      { color: BAD, label: "Zero-margin date", dash: "3 3" },
    ]);
    txt(svg, R, B + 12, "status date", { anchor: "end", size: 8.5 });
  }

  /* ---------------------- risk-based margin sufficiency (SRA; §7.3.3.2.3) — button-triggered */
  function el2(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function renderRisk(d) {
    var host = document.getElementById("marginRisk");
    if (!host) return;
    host.textContent = "";
    if (d.error) { host.appendChild(el2("p", "muted", d.error)); return; }
    // KPI cards: covered percentile, verdict, margin window
    var cards = el2("div", "stat-grid");
    function card(value, label) {
      var c = el2("div", "stat-card");
      c.appendChild(el2("div", "stat-value", value));
      c.appendChild(el2("div", "stat-label", label));
      cards.appendChild(c);
    }
    var verdictText = d.degenerate
      ? "no verdict — point mass"
      : (d.verdict || "—").toUpperCase();
    card(d.covered_pct + "%", "covered percentile (CDF at deterministic finish)");
    card(verdictText, "verdict vs Watch " + d.watch_pct + "% / Corrective " + d.corrective_pct + "% (example thresholds, operator-set)");
    card(d.margin_wd + " wd", "margin window E → D (all-ML solve, margin zeroed vs at plan)");
    host.appendChild(cards);
    if (d.degenerate) {
      host.appendChild(el2("p", "muted",
        "Every iteration finished at one offset — no duration uncertainty or risks have been " +
        "entered on the Risk Analysis page, so the percentile spread is undefined (no verdict is issued)."));
    }
    if (!d.have_margin) {
      host.appendChild(el2("p", "muted",
        "No schedule margin found to measure sufficiency of (margin tasks: " + d.margin_task_count + ")."));
    }
    // P10-P90 spread strip with D and E markers (SVG, theme tokens)
    var W = 720, H = 96, Ls = 40, Rs = 700, mid = 46;
    var wrap = el2("div", "chart-host");
    host.appendChild(wrap);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "SRA finish percentile spread against the margin window");
    wrap.appendChild(svg);
    var offs = d.rows.map(function (r) { return r.finish_offset; }).concat([d.deterministic_finish, d.zero_margin_finish]);
    var omin = Math.min.apply(null, offs), omax = Math.max.apply(null, offs);
    function sx(o) { return omax === omin ? (Ls + Rs) / 2 : Ls + (Rs - Ls) * (o - omin) / (omax - omin); }
    // margin window [E, D] underlay
    var rw = svgEl("rect", { x: sx(d.zero_margin_finish), y: mid - 12, width: Math.max(1, sx(d.deterministic_finish) - sx(d.zero_margin_finish)), height: 24, fill: OK, opacity: 0.18 });
    tip(rw, "margin window: zero-margin finish E " + d.zero_margin_finish_date + " → deterministic finish D " + d.deterministic_finish_date + " (" + d.margin_wd + " wd)");
    svg.appendChild(rw);
    // the percentile interval line
    var lo = d.rows[0], hi = d.rows[d.rows.length - 1];
    svg.appendChild(svgEl("line", { x1: sx(lo.finish_offset), y1: mid, x2: sx(hi.finish_offset), y2: mid, stroke: ACC, "stroke-width": 2 }));
    d.rows.forEach(function (r) {
      var cx = sx(r.finish_offset);
      var c = svgEl("circle", { cx: cx, cy: mid, r: 4, fill: r.covered ? OK : BAD });
      tip(c, "P" + r.pct + " " + r.finish_date + " — delta vs plan " + r.delta_vs_plan_wd + " wd; margin needed " + r.margin_needed_wd + " wd; " + (r.covered ? "covered" : "NOT covered"));
      svg.appendChild(c);
      txt(svg, cx, mid + 22, "P" + r.pct, { anchor: "middle", size: 8.5 });
    });
    [{ o: d.deterministic_finish, lbl: "D (plan)", col: WARN }, { o: d.zero_margin_finish, lbl: "E (zero margin)", col: MUT }].forEach(function (mkr) {
      var mx = sx(mkr.o);
      svg.appendChild(svgEl("line", { x1: mx, y1: mid - 18, x2: mx, y2: mid + 12, stroke: mkr.col, "stroke-width": 1.6, "stroke-dasharray": "4 2" }));
      txt(svg, mx, mid - 24, mkr.lbl, { anchor: "middle", size: 8.5, fill: mkr.col });
    });
    // the table
    var tbl = el2("table", "card-table");
    var hd = el2("tr");
    ["Percentile", "Finish", "Δ vs plan (wd)", "Margin needed (wd)", "Covered"].forEach(function (h) {
      var th = el2("th", null, h); th.setAttribute("scope", "col"); hd.appendChild(th);
    });
    tbl.appendChild(hd);
    d.rows.forEach(function (r) {
      var tr = el2("tr");
      tr.appendChild(el2("td", null, "P" + r.pct));
      tr.appendChild(el2("td", null, r.finish_date));
      tr.appendChild(el2("td", "num", String(r.delta_vs_plan_wd)));
      tr.appendChild(el2("td", "num", String(r.margin_needed_wd)));
      tr.appendChild(el2("td", null, r.covered ? "yes" : "NO"));
      tbl.appendChild(tr);
    });
    host.appendChild(tbl);
    // provenance chip: every parameter of the seeded run
    host.appendChild(el2("p", "muted",
      "Run: " + d.file + " — focus UID " + (d.focus_uid == null ? "project finish" : d.focus_uid) +
      "; " + d.iterations + " iterations, seed " + d.seed + ", " + d.distribution +
      ", occurrence " + d.occurrence_mode + ", risk register " + (d.use_risk_register ? "on" : "off") +
      ", correlation " + d.correlation + "; margin tasks " + d.margin_task_count +
      "; curve basis: " + d.curve_basis +
      ". Deterministic by seed — rerunning reproduces these figures exactly."));
  }
  var riskBtn = document.getElementById("marginRiskRun");
  if (riskBtn) riskBtn.addEventListener("click", function () {
    var status = document.getElementById("marginRiskStatus");
    if (status) status.textContent = "running…";
    riskBtn.disabled = true;
    // ADR-0266: the checkbox selects the Fig 7-43 zero-margin curve; the payload's
    // curve_basis names whichever basis produced the figures (shown in the provenance line)
    var zeroBox = document.getElementById("marginRiskZero");
    var zero = zeroBox && zeroBox.checked ? 1 : 0;
    fetch("/api/margin/risk?zero_margin=" + zero).then(function (r) { return r.json(); }).then(function (d) {
      if (status) status.textContent = "";
      riskBtn.disabled = false;
      renderRisk(d);
    }).catch(function (e) {
      if (status) status.textContent = "failed: " + e;
      riskBtn.disabled = false;
    });
  });

  renderBurndown();
  renderErosion();
  if (window.SFChartFrame && SFChartFrame.scan) SFChartFrame.scan();
})();
