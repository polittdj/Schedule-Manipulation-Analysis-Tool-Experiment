/* Schedule Forensics — JCL Joint Cost-&-Schedule Confidence runner (ADR-0269). Vendored,
 * dependency-free, same-origin only (air-gap). The run is OFF the page-load path: "Run JCL"
 * fetches /api/sra/jcl (the joint (finish, cost) Monte-Carlo — the SAME schedule inputs as the
 * SSI run, so the football chart's schedule axis is exactly the SSI S-curve) and renders the
 * football scatter, the cost S-curve, the FICSM SCL/CCL/JCL strip, and the quadrant table.
 * Nothing leaves the machine. */
"use strict";

(function () {
  var runBtn = document.getElementById("jclRun");
  if (!runBtn) return;
  var status = document.getElementById("jclStatus");

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    return n;
  }
  function row(cells, head) {
    var tr = el("tr");
    cells.forEach(function (c) { tr.appendChild(el(head ? "th" : "td", null, String(c))); });
    return tr;
  }
  var SVGNS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function txt(node, s) { node.textContent = s; return node; }
  function ms(date) { var t = Date.parse(date); return isNaN(t) ? null : t; }
  function titled(node, s) { var t = svg("title"); t.textContent = s; node.appendChild(t); return node; }
  function chartHost(node) {
    var h = el("div", { class: "chart-host" });
    h.appendChild(node);
    return h;
  }
  function money(v) {
    return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  function isoDay(msEpoch) {
    return new Date(msEpoch).toISOString().slice(0, 10);
  }

  // The classic JCL "football" — the joint (finish date, EAC) cloud with the target crosshair,
  // quadrant shares in the corners, the deterministic point, and the iso-confidence frontier.
  function football(d) {
    var W = 420, H = 250, ml = 64, mr = 10, mt = 12, mb = 24;
    var wrap = el("div", { class: "ssi-chart", style: "width:420px" });
    wrap.appendChild(el("div", { class: "ssi-chart-t" },
      "JCL football — cost × finish cloud (" + d.levels.jcl + "% joint at the targets)"));
    var s = svg("svg", { class: "ssi-svg", viewBox: "0 0 " + W + " " + H, width: "100%" });
    var pts = d.points.filter(function (p) { return ms(p[0]) != null; });
    if (!pts.length) { wrap.appendChild(s); return wrap; }
    var xs = pts.map(function (p) { return ms(p[0]); });
    var ys = pts.map(function (p) { return p[1]; });
    var tx = ms(d.targets.date), tdet = ms(d.deterministic.date);
    if (tx != null) xs.push(tx);
    if (tdet != null) xs.push(tdet);
    ys.push(d.targets.cost, d.deterministic.eac);
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (x1 === x0) x1 = x0 + 1;
    if (y1 === y0) y1 = y0 + 1;
    var X = function (m) { return ml + ((m - x0) / (x1 - x0)) * (W - ml - mr); };
    var Y = function (c) { return mt + (1 - (c - y0) / (y1 - y0)) * (H - mt - mb); };
    // grid + $ labels on 4 y ticks
    [0, 1 / 3, 2 / 3, 1].forEach(function (f) {
      var c = y0 + f * (y1 - y0), y = Y(c);
      s.appendChild(svg("line", { x1: ml, y1: y, x2: W - mr, y2: y, class: "ch-grid" }));
      s.appendChild(txt(svg("text", { x: ml - 3, y: y + 3, class: "ch-yl" }), money(c)));
    });
    // the cloud — blue meets BOTH targets, red misses either (the football itself)
    pts.forEach(function (p) {
      var okDate = p[0] <= d.targets.date, okCost = p[1] <= d.targets.cost;
      var cls = okDate && okCost ? "ch-pt" : "ch-pt miss";
      s.appendChild(titled(svg("circle", { cx: X(ms(p[0])), cy: Y(p[1]), r: 1.8, class: cls }),
        p[0] + " — " + money(p[1]) +
        (okDate && okCost ? " (on time & on cost)" :
          okDate ? " (on time, over cost)" : okCost ? " (late, on cost)" : " (late & over cost)")));
    });
    // iso-confidence frontier (dates ascending; cost non-increasing)
    var fr = d.frontier.filter(function (p) { return ms(p[0]) != null; });
    if (fr.length > 1) {
      s.appendChild(titled(svg("polyline", {
        class: "ch-frontier",
        points: fr.map(function (p) { return X(ms(p[0])) + "," + Y(p[1]); }).join(" "),
      }), "P" + Math.round(d.targets.confidence) +
        " frontier — every (date, cost) on this line reaches the joint confidence"));
      fr.forEach(function (p) {
        s.appendChild(titled(svg("circle", { cx: X(ms(p[0])), cy: Y(p[1]), r: 3.5, class: "ch-hot" }),
          "P" + Math.round(d.targets.confidence) + " jointly: finish " + p[0] +
          " needs ≤ " + money(p[1])));
      });
    }
    // target crosshair
    if (tx != null) {
      s.appendChild(titled(svg("line", { x1: X(tx), y1: mt, x2: X(tx), y2: H - mb, class: "ch-tgt" }),
        "Target date — " + d.targets.date));
    }
    s.appendChild(titled(
      svg("line", { x1: ml, y1: Y(d.targets.cost), x2: W - mr, y2: Y(d.targets.cost), class: "ch-tgt" }),
      "Target cost — " + money(d.targets.cost)));
    // deterministic (all-ML) point
    if (tdet != null) {
      s.appendChild(titled(
        svg("circle", { cx: X(tdet), cy: Y(d.deterministic.eac), r: 3, class: "ch-dot" }),
        "Deterministic (all-ML): " + d.deterministic.date + " — " + money(d.deterministic.eac)));
    }
    // quadrant shares in the corners (top-left = on time & on cost region is bottom-left in
    // cost space; label each corner with its share and a call-out naming the quadrant)
    var q = d.quadrants;
    [
      { x: ml + 4, y: H - mb - 6, a: "start", v: q.both, n: "on time & on cost" },
      { x: ml + 4, y: mt + 10, a: "start", v: q.date_only, n: "on time, over cost" },
      { x: W - mr - 4, y: H - mb - 6, a: "end", v: q.cost_only, n: "late, on cost" },
      { x: W - mr - 4, y: mt + 10, a: "end", v: q.neither, n: "late & over cost" },
    ].forEach(function (c) {
      s.appendChild(titled(txt(svg("text", {
        x: c.x, y: c.y, class: "ch-ql", "text-anchor": c.a,
      }), c.v + "%"), c.n + " — " + c.v + "% of iterations"));
    });
    s.appendChild(svg("line", { x1: ml, y1: mt, x2: ml, y2: H - mb, class: "ch-ax" }));
    s.appendChild(svg("line", { x1: ml, y1: H - mb, x2: W - mr, y2: H - mb, class: "ch-ax" }));
    // label the AXIS BOUNDS (points arrive in iteration order, so first/last are not min/max)
    s.appendChild(txt(svg("text", { x: ml, y: H - 6, class: "ch-xl" }), isoDay(x0)));
    s.appendChild(txt(svg("text", { x: W - mr, y: H - 6, class: "ch-xl", "text-anchor": "end" }),
      isoDay(x1)));
    wrap.appendChild(s);
    return wrap;
  }

  // The cost marginal as an S-curve: cumulative probability of the EAC landing at or below x.
  function costCurve(d) {
    var W = 380, H = 168, ml = 34, mr = 8, mt = 8, mb = 22;
    var wrap = el("div", { class: "ssi-chart" });
    wrap.appendChild(el("div", { class: "ssi-chart-t" }, "EAC confidence (cost S-curve)"));
    var s = svg("svg", { class: "ssi-svg", viewBox: "0 0 " + W + " " + H, width: "100%" });
    var pts = d.cost_cdf;
    if (pts.length) {
      var x0 = pts[0][0], x1 = pts[pts.length - 1][0];
      x0 = Math.min(x0, d.targets.cost); x1 = Math.max(x1, d.targets.cost);
      if (x1 === x0) x1 = x0 + 1;
      var X = function (c) { return ml + ((c - x0) / (x1 - x0)) * (W - ml - mr); };
      var Y = function (p) { return mt + (1 - p) * (H - mt - mb); };
      [0, 0.25, 0.5, 0.75, 1].forEach(function (p) {
        var y = Y(p);
        s.appendChild(svg("line", { x1: ml, y1: y, x2: W - mr, y2: y, class: "ch-grid" }));
        s.appendChild(txt(svg("text", { x: ml - 2, y: y + 3, class: "ch-yl" }), p * 100 + "%"));
      });
      s.appendChild(titled(
        svg("line", { x1: X(d.targets.cost), y1: mt, x2: X(d.targets.cost), y2: H - mb, class: "ch-tgt" }),
        "Target cost — " + money(d.targets.cost) + " (CCL " + d.levels.ccl + "%)"));
      s.appendChild(titled(
        svg("line", { x1: X(d.deterministic.eac), y1: mt, x2: X(d.deterministic.eac), y2: H - mb, class: "ch-det" }),
        "Deterministic EAC — " + money(d.deterministic.eac)));
      s.appendChild(svg("polyline", {
        class: "ch-line",
        points: pts.map(function (p) { return X(p[0]) + "," + Y(p[1]); }).join(" "),
      }));
      pts.forEach(function (p) {
        s.appendChild(titled(svg("circle", { cx: X(p[0]), cy: Y(p[1]), r: 4, class: "ch-hot" }),
          money(p[0]) + " — " + Math.round(p[1] * 100) + "% confidence"));
      });
      d.cost_percentiles.forEach(function (pc) {
        var pr = { P10: 0.1, P50: 0.5, P80: 0.8, P90: 0.9 }[pc.label];
        if (pr == null) return;
        s.appendChild(titled(svg("circle", { cx: X(pc.value), cy: Y(pr), r: 2.6, class: "ch-dot" }),
          pc.label + " — " + money(pc.value)));
      });
      s.appendChild(svg("line", { x1: ml, y1: mt, x2: ml, y2: H - mb, class: "ch-ax" }));
      s.appendChild(svg("line", { x1: ml, y1: H - mb, x2: W - mr, y2: H - mb, class: "ch-ax" }));
      s.appendChild(txt(svg("text", { x: ml, y: H - 6, class: "ch-xl" }), money(x0)));
      s.appendChild(txt(svg("text", { x: W - mr, y: H - 6, class: "ch-xl", "text-anchor": "end" }),
        money(x1)));
    }
    wrap.appendChild(s);
    return wrap;
  }

  // The FICSM strip: SCL / CCL / JCL as labeled 0-100% bars (JCL can never exceed either marginal).
  function ficsmStrip(levels) {
    var W = 380, H = 76, ml = 40, mr = 34, bh = 12;
    var wrap = el("div", { class: "ssi-chart" });
    wrap.appendChild(el("div", { class: "ssi-chart-t" },
      "FICSM levels — JCL ≤ min(SCL, CCL)"));
    var s = svg("svg", { class: "ssi-svg", viewBox: "0 0 " + W + " " + H, width: "100%" });
    [
      { label: "SCL", v: levels.scl, cls: "ch-lvl", tip: "Schedule confidence — P(finish on/before the target date)" },
      { label: "CCL", v: levels.ccl, cls: "ch-lvl", tip: "Cost confidence — P(EAC at/below the target cost)" },
      { label: "JCL", v: levels.jcl, cls: "ch-lvl jcl", tip: "JOINT confidence — P(both at once); never exceeds either marginal" },
    ].forEach(function (b, i) {
      var y = 8 + i * (bh + 10);
      s.appendChild(txt(svg("text", { x: ml - 4, y: y + bh - 3, class: "ch-yl" }), b.label));
      s.appendChild(svg("rect", { x: ml, y: y, width: W - ml - mr, height: bh, class: "ch-lvl-bg" }));
      s.appendChild(titled(svg("rect", {
        x: ml, y: y, width: Math.max(0, (b.v / 100) * (W - ml - mr)), height: bh, class: b.cls,
      }), b.tip + " — " + b.v + "%"));
      s.appendChild(txt(svg("text", { x: W - mr + 4, y: y + bh - 3, class: "ch-yl", "text-anchor": "start" }),
        b.v + "%"));
    });
    wrap.appendChild(s);
    return wrap;
  }

  function renderResult(d) {
    var out = document.getElementById("jclSummary");
    out.innerHTML = "";
    out.appendChild(el("p", { class: "muted" },
      "Focus: " + (d.focus_name || "Project finish") + " — " + d.iterations +
      " iterations. Targets: " + d.targets.date + " / " + money(d.targets.cost) +
      " (confidence target " + d.targets.confidence + "%)."));
    var t = el("table");
    t.appendChild(row(["Measure", "Value"], true));
    t.appendChild(row(["Deterministic finish (all-ML)", d.deterministic.date]));
    t.appendChild(row(["Deterministic EAC = AC + (BAC − EV)", money(d.deterministic.eac)]));
    t.appendChild(row(["SCL — P(finish ≤ " + d.targets.date + ")", d.levels.scl + "%"]));
    t.appendChild(row(["CCL — P(EAC ≤ " + money(d.targets.cost) + ")", d.levels.ccl + "%"]));
    t.appendChild(row(["JCL — P(both)", d.levels.jcl + "%"]));
    d.finish_percentiles.forEach(function (p) {
      t.appendChild(row(["Finish " + p.label, p.date]));
    });
    d.cost_percentiles.forEach(function (p) {
      t.appendChild(row(["EAC " + p.label, money(p.value)]));
    });
    t.appendChild(row(["EAC mean / std", money(d.cost_mean) + " / " + money(d.cost_std)]));
    out.appendChild(t);
    // quadrant 2x2
    out.appendChild(el("h3", null, "Quadrants at the targets"));
    var qt = el("table");
    qt.appendChild(row(["", "On/before target date", "Late"], true));
    qt.appendChild(row(["At/below target cost", d.quadrants.both + "%", d.quadrants.cost_only + "%"]));
    qt.appendChild(row(["Over target cost", d.quadrants.date_only + "%", d.quadrants.neither + "%"]));
    out.appendChild(qt);
    var pv = d.provenance;
    out.appendChild(el("p", { class: "muted" },
      "Cost basis: sunk " + money(pv.sunk) + " + remaining time-dependent " +
      money(pv.remaining_td) + " (τ " + pv.td_share_pct + "%) + time-independent " +
      money(pv.remaining_ti) + ", across " + pv.incomplete_costed +
      " incomplete costed task(s) (" + pv.completed + " completed). Cost-estimating uncertainty " +
      (pv.cost_uncertainty_on ? "ON." : "off — duration-driven cost only (screening).")));

    var ch = document.getElementById("jclCharts");
    ch.innerHTML = "";
    ch.appendChild(chartHost(football(d)));
    ch.appendChild(chartHost(costCurve(d)));
    ch.appendChild(chartHost(ficsmStrip(d.levels)));

    // the correlation-matrix feasibility badge (ADR-0270), shared with the SSI panel's #corrBadge
    var cb = document.getElementById("corrBadge");
    var cm = d.correlation_matrix;
    if (cb && cm && cm.applied) {
      cb.innerHTML = "";
      var note = el("div", { class: "notice " + (cm.repaired ? "warn" : "ok"), role: "note" });
      note.textContent = cm.repaired
        ? "Correlation matrix: infeasible input REPAIRED to the nearest valid PSD matrix (entered " +
          "min eigenvalue " + cm.min_eigenvalue + ", Frobenius distance " + cm.frobenius_distance + ")."
        : "Correlation matrix: feasible (min eigenvalue " + cm.min_eigenvalue + ").";
      cb.appendChild(note);
    }
    if (window.SFChartFrame) window.SFChartFrame.scan();
  }

  function run() {
    var it = (document.getElementById("jclIters") || {}).value || "1000";
    // the joint run shares the SSI panel's distribution choice (one coherent story)
    var dist = (document.getElementById("ssiDist") || {}).value || "triangular";
    status.textContent = "Running the joint cost+schedule Monte-Carlo…";
    fetch("/api/sra/jcl?iterations=" + encodeURIComponent(it) +
      "&distribution=" + encodeURIComponent(dist))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { status.textContent = res.j.error || "Run failed."; return; }
        status.textContent = "";
        renderResult(res.j);
      })
      .catch(function () { status.textContent = "Run failed."; });
  }

  runBtn.addEventListener("click", run);
})();
