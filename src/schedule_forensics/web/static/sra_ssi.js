/* Schedule Forensics — SSI Schedule Risk & Opportunity Analysis runner (ADR-0123). Vendored,
 * dependency-free, same-origin only (air-gap). The run is OFF the page-load path: clicking "Run SSI
 * SRA" fetches /api/sra/ssi (focus-event finish dates + percentile + per-risk stats + the 5x5
 * Risk/Opportunity matrices); "Run sensitivity" fetches /api/sra/oat (the deterministic one-at-a-time
 * Best/Worst swing). Nothing leaves the machine. */
"use strict";

(function () {
  var runBtn = document.getElementById("ssiRun");
  if (!runBtn) return;
  var status = document.getElementById("ssiStatus");

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

  // Hover/focus call-out on a metric column header, from window.SF_FIELD_HELP (the server-rendered
  // glossary): definition + how it's calculated + a real-world use, reusing the shared DCMA tooltip
  // styling. An empty/unknown key falls back to a plain header.
  var _helpEl = document.getElementById("sfFieldHelp");
  var FIELD_HELP = {};
  if (_helpEl) { try { FIELD_HELP = JSON.parse(_helpEl.textContent || "{}"); } catch (e) { FIELD_HELP = {}; } }
  function tipPara(boldLabel, text) {
    var p = el("p");
    p.appendChild(el("b", null, boldLabel));
    p.appendChild(document.createTextNode(" " + text));
    return p;
  }
  function helpTh(label, key) {
    var h = FIELD_HELP[key];
    if (!h) return el("th", null, label);
    var th = el("th", { class: "metric-th" });
    var title = h.name + ". " + h.definition + " How it's calculated: " + h.formula +
      (h.use ? " Real-world use: " + h.use : "");
    var span = el("span", { class: "dcma-metric mhelp", tabindex: "0", role: "button", title: title });
    span.textContent = label + " ";
    span.appendChild(el("span", { class: "dcma-info", "aria-hidden": "true" }, "ⓘ"));
    th.appendChild(span);
    var tip = el("div", { class: "dcma-tip mtip", role: "tooltip" });
    tip.appendChild(el("b", null, h.name));
    tip.appendChild(el("p", null, h.definition));
    tip.appendChild(tipPara("How it's calculated:", h.formula));
    if (h.use) tip.appendChild(tipPara("Real-world use:", h.use));
    if (h.indicates) tip.appendChild(tipPara("Indicates:", h.indicates));
    th.appendChild(tip);
    return th;
  }
  function headerRow(pairs) {
    var tr = el("tr");
    pairs.forEach(function (p) { tr.appendChild(helpTh(p[0], p[1])); });
    return tr;
  }
  function labelRow(label, key, value) {
    var tr = el("tr");
    var th = helpTh(label, key);
    th.setAttribute("scope", "row");
    tr.appendChild(th);
    tr.appendChild(el("td", null, String(value)));
    return tr;
  }

  // The NASA 5x5 assessment matrix (mirrors the operator's reference image): Likelihood-of-Occurrence
  // rows (5 Near Certainty at top .. 1 Remote), Consequence/Benefit columns (1..5), the fixed NASA
  // priority ranks 1..25 in each cell, tri-band zones (Risk = green/yellow/red; Opportunity = light/
  // medium/dark blue), and a count badge wherever the user's risks land. grid is the engine count
  // grid indexed [consequence-1][probability-1].
  var RANK = [
    [1, 3, 5, 8, 12],     // L1 Remote
    [2, 6, 11, 14, 17],   // L2 Unlikely
    [4, 9, 15, 19, 21],   // L3 Possible
    [7, 13, 18, 22, 24],  // L4 Highly Likely
    [10, 16, 20, 23, 25], // L5 Near Certainty
  ];
  var ZONE = [
    ["g", "g", "g", "g", "y"],
    ["g", "g", "y", "y", "r"],
    ["g", "y", "y", "r", "r"],
    ["g", "y", "r", "r", "r"],
    ["g", "y", "r", "r", "r"],
  ];
  var LIK = ["Remote", "Unlikely", "Possible", "Highly Likely", "Near Certainty"];
  var CONS_RISK = ["Low", "Minor", "Moderate", "Significant", "Severe"];
  var CONS_OPP = ["Low", "Minor", "Moderate", "High", "Very High"];

  // The items (risks or opportunities) that land in one matrix cell — same binning the engine count
  // grid uses: opportunities are impact_days < 0, ratings clamped to 1..5, indexed [consequence][prob].
  function cellItems(risks, opportunity, consequence, likelihood) {
    return (risks || []).filter(function (r) {
      if ((r.impact_days < 0) !== !!opportunity) return false;
      var c = Math.min(5, Math.max(1, r.consequence_rating));
      var p = Math.min(5, Math.max(1, r.probability_rating));
      return c === consequence && p === likelihood;
    });
  }

  function matrix(title, grid, opportunity, risks) {
    var cons = opportunity ? CONS_OPP : CONS_RISK;
    var fam = opportunity ? "o" : "r"; // colour family
    var wrap = el("div", { class: "nasa-matrix cf-zoom-box" });
    wrap.appendChild(el("div", { class: "nm-title" }, title));
    var body = el("div", { class: "nm-body" });
    body.appendChild(el("div", { class: "nm-yaxis" }, "Likelihood of Occurrence"));
    var t = el("table", { class: "nm-grid" });
    var hdr = el("tr");
    hdr.appendChild(el("th", { class: "nm-corner" }, ""));
    for (var c = 1; c <= 5; c++) {
      var th = el("th", { class: "nm-chead" });
      th.appendChild(el("div", { class: "nm-cnum" }, String(c)));
      th.appendChild(el("div", { class: "nm-clab" }, cons[c - 1]));
      hdr.appendChild(th);
    }
    t.appendChild(hdr);
    for (var L = 5; L >= 1; L--) {
      var tr = el("tr");
      var rh = el("th", { class: "nm-rhead" });
      rh.appendChild(el("span", { class: "nm-rnum" }, String(L)));
      rh.appendChild(el("span", { class: "nm-rlab" }, LIK[L - 1]));
      tr.appendChild(rh);
      for (var C = 1; C <= 5; C++) {
        var count = (grid[C - 1] && grid[C - 1][L - 1]) || 0;
        var items = cellItems(risks, opportunity, C, L);
        var td = el("td", { class: "nm-cell nm-" + fam + "-" + ZONE[L - 1][C - 1] +
          (count ? " nm-hit" : "") });
        // hover call-out: name the cell (consequence × likelihood + NASA rank) and list every
        // risk / opportunity that lands here so the operator can dive into the matrix detail.
        var head = cons[C - 1] + (opportunity ? " benefit" : " consequence") + " × " +
          LIK[L - 1] + " likelihood — rank " + RANK[L - 1][C - 1];
        if (items.length) {
          td.setAttribute("data-callout", head + "\n" +
            (opportunity ? "Opportunities here:" : "Risks here:") + "\n" +
            items.map(function (r) {
              return "• " + r.name + " — " + Math.abs(r.impact_days) + " d, " + r.probability +
                "% (" + r.hits + " hits)";
            }).join("\n"));
          td.classList.add("nm-detail");
        } else {
          td.setAttribute("data-callout", head + "\n(no items)");
        }
        td.appendChild(el("span", { class: "nm-rank" }, String(RANK[L - 1][C - 1])));
        if (count) td.appendChild(el("span", { class: "nm-badge" }, String(count)));
        tr.appendChild(td);
      }
      t.appendChild(tr);
    }
    body.appendChild(t);
    wrap.appendChild(body);
    wrap.appendChild(el("div", { class: "nm-xaxis" },
      opportunity ? "Benefit of Occurrence" : "Consequence of Occurrence"));
    var leg = el("div", { class: "nm-legend" });
    [["High", "r"], ["Medium", "y"], ["Low", "g"]].forEach(function (p) {
      var item = el("span", { class: "nm-leg-item" });
      item.appendChild(el("span", { class: "nm-swatch nm-" + fam + "-" + p[1] }));
      item.appendChild(document.createTextNode(" " + p[0]));
      leg.appendChild(item);
    });
    wrap.appendChild(leg);
    return wrap;
  }

  function nonEmpty(grid) {
    return grid.some(function (r) { return r.some(function (x) { return x; }); });
  }

  // Each chart / matrix gets its OWN ".chart-host" so chartframe.js frames it independently with a
  // zoom (− / ＋), full-screen, and reset toolbar plus cursor-following hover call-outs.
  function chartHost(node) {
    var h = el("div", { class: "chart-host" });
    h.appendChild(node);
    return h;
  }

  // --- small, dense vector charts (the operator wanted compact graphs + many data points) -----
  var SVGNS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function txt(node, s) { node.textContent = s; return node; }
  function ms(date) { var t = Date.parse(date); return isNaN(t) ? null : t; }
  // Hover call-out: chartframe.js reads a direct <title> child of any shape and shows it as a styled,
  // cursor-following tooltip — so every charted value can be read on hover with no per-chart wiring.
  function titled(node, s) { var t = svg("title"); t.textContent = s; node.appendChild(t); return node; }

  // The cumulative finish-date confidence curve. The engine emits one point per distinct simulated
  // finish, so the line is dense and smooth; P10/50/80/90 + the deterministic finish are marked.
  function sCurve(points, det, pcts) {
    var W = 380, H = 168, ml = 30, mr = 8, mt = 8, mb = 22;
    var wrap = el("div", { class: "ssi-chart" });
    wrap.appendChild(el("div", { class: "ssi-chart-t" }, "Finish-date confidence (S-curve)"));
    var s = svg("svg", { class: "ssi-svg", viewBox: "0 0 " + W + " " + H, width: "100%" });
    var xs = points.map(function (p) { return ms(p.date); }).filter(function (x) { return x != null; });
    if (xs.length) {
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      var X = function (m) { return ml + (x1 === x0 ? 0 : (m - x0) / (x1 - x0)) * (W - ml - mr); };
      var Y = function (p) { return mt + (1 - p) * (H - mt - mb); };
      [0, 0.25, 0.5, 0.75, 1].forEach(function (p) {
        var y = Y(p);
        s.appendChild(svg("line", { x1: ml, y1: y, x2: W - mr, y2: y, class: "ch-grid" }));
        s.appendChild(txt(svg("text", { x: ml - 2, y: y + 3, class: "ch-yl" }), p * 100 + "%"));
      });
      if (det && ms(det.date) != null) {
        var dx = X(ms(det.date));
        s.appendChild(titled(svg("line", { x1: dx, y1: mt, x2: dx, y2: H - mb, class: "ch-det" }),
          "Deterministic (all-ML) finish — " + det.date));
      }
      s.appendChild(svg("polyline", {
        class: "ch-line",
        points: points.map(function (p) { return X(ms(p.date)) + "," + Y(p.p); }).join(" "),
      }));
      // a transparent hot-spot on every plotted point so hovering anywhere along the curve calls out
      // that finish date and its cumulative confidence (chartframe shows the <title> at the cursor)
      points.forEach(function (p) {
        var mm = ms(p.date);
        if (mm == null) return;
        s.appendChild(titled(svg("circle", { cx: X(mm), cy: Y(p.p), r: 4, class: "ch-hot" }),
          p.date + " — " + Math.round(p.p * 100) + "% confidence"));
      });
      (pcts || []).forEach(function (pc) {
        var mm = ms(pc.date);
        if (mm == null) return;
        s.appendChild(titled(svg("circle", { cx: X(mm), cy: Y(pc.p), r: 2.6, class: "ch-dot" }),
          pc.label + " — " + pc.date + " (" + Math.round(pc.p * 100) + "%)"));
      });
      s.appendChild(svg("line", { x1: ml, y1: mt, x2: ml, y2: H - mb, class: "ch-ax" }));
      s.appendChild(svg("line", { x1: ml, y1: H - mb, x2: W - mr, y2: H - mb, class: "ch-ax" }));
      s.appendChild(txt(svg("text", { x: ml, y: H - 6, class: "ch-xl" }), points[0].date));
      s.appendChild(txt(svg("text", { x: W - mr, y: H - 6, class: "ch-xl", "text-anchor": "end" }),
        points[points.length - 1].date));
    }
    wrap.appendChild(s);
    return wrap;
  }

  // The finish-date distribution (histogram / PDF) as compact bars.
  function histChart(bins) {
    var W = 380, H = 168, ml = 26, mr = 8, mt = 8, mb = 22;
    var wrap = el("div", { class: "ssi-chart" });
    wrap.appendChild(el("div", { class: "ssi-chart-t" }, "Finish-date distribution"));
    var s = svg("svg", { class: "ssi-svg", viewBox: "0 0 " + W + " " + H, width: "100%" });
    var maxc = bins.reduce(function (a, b) { return Math.max(a, b.count); }, 0) || 1;
    var total = bins.reduce(function (a, b) { return a + b.count; }, 0) || 1;
    var bw = (W - ml - mr) / (bins.length || 1);
    bins.forEach(function (b, i) {
      var h = (b.count / maxc) * (H - mt - mb);
      s.appendChild(titled(svg("rect", {
        class: "ch-bar", x: ml + i * bw + 0.5, y: H - mb - h,
        width: Math.max(1, bw - 1), height: h,
      }), b.date + " — " + b.count + " finish" + (b.count === 1 ? "" : "es") +
        " (" + Math.round((b.count / total) * 100) + "%)"));
    });
    s.appendChild(svg("line", { x1: ml, y1: H - mb, x2: W - mr, y2: H - mb, class: "ch-ax" }));
    if (bins.length) {
      s.appendChild(txt(svg("text", { x: ml, y: H - 6, class: "ch-xl" }), bins[0].date));
      s.appendChild(txt(svg("text", { x: W - mr, y: H - 6, class: "ch-xl", "text-anchor": "end" }),
        bins[bins.length - 1].date));
    }
    wrap.appendChild(s);
    return wrap;
  }

  function renderResult(d) {
    var out = document.getElementById("ssiResult");
    out.innerHTML = "";
    out.appendChild(el("p", { class: "muted" },
      "Focus: " + (d.focus_name || "Project finish") + " — " + d.iterations + " iterations, " +
      (d.occurrence_mode === "exact_overall" ? "exact %" : "random each") +
      (d.correlation > 0 ? ", correlation " + d.correlation : "") +
      (d.used_risks ? ", risks on" : "")));
    var t = el("table");
    t.appendChild(row(["Measure", "Date / value"], true));
    t.appendChild(labelRow("Deterministic finish", "deterministic_finish",
      d.deterministic.date + "  (P" + d.deterministic.percentile + ")"));
    d.percentiles.forEach(function (p) { t.appendChild(row([p.label, p.date])); });
    t.appendChild(labelRow("Mean", "mean_finish", d.mean));
    t.appendChild(labelRow("Std deviation", "std_dev_finish",
      d.std_days + " working days (" + d.std_cal_days + " calendar days)"));
    out.appendChild(t);
    if (d.risks && d.risks.length) {
      out.appendChild(el("h3", null, "Risk outcomes"));
      var rt = el("table");
      rt.appendChild(row(["Risk", "Prob", "Impact (d)", "Hits", "Mean Δ (wd)", "P", "C"], true));
      d.risks.forEach(function (r) {
        rt.appendChild(row([r.name, r.probability + "%", r.impact_days, r.hits,
          r.mean_delta_days, r.probability_rating, r.consequence_rating]));
      });
      out.appendChild(rt);
    }
    // probabilistic-branch outcomes (ADR-0273): fired fraction + rework magnitude + finish impact
    if (d.branches && d.branches.length) {
      out.appendChild(el("h3", null, "Probabilistic-branch outcomes"));
      var bt = el("table");
      bt.appendChild(row(["Branch", "Prob", "Fired", "Mean rework (d)", "Mean Δ (wd)", "Status"], true));
      d.branches.forEach(function (b) {
        bt.appendChild(row([b.name, b.probability + "%", b.applied ? b.fired_pct + "%" : "—",
          b.applied ? b.mean_fragnet_days : "—", b.applied ? b.mean_delta_days : "—",
          b.applied ? "applied" : "inert (no FS tie)"]));
      });
      out.appendChild(bt);
    }
    var ch = document.getElementById("ssiCharts");
    ch.innerHTML = "";
    if (d.s_curve && d.s_curve.length) {
      var labels = ["P10", "P50", "P80", "P90"];
      var pc = [10, 50, 80, 90].map(function (q, i) {
        return { label: labels[i], date: d.percentiles[i] && d.percentiles[i].date, p: q / 100 };
      });
      ch.appendChild(chartHost(sCurve(d.s_curve, d.deterministic, pc)));
    }
    if (d.finish_hist && d.finish_hist.length) ch.appendChild(chartHost(histChart(d.finish_hist)));

    var m = document.getElementById("ssiMatrices");
    m.innerHTML = "";
    if (nonEmpty(d.risk_matrix)) {
      m.appendChild(chartHost(matrix("Risk Assessment Matrix", d.risk_matrix, false, d.risks)));
    }
    if (nonEmpty(d.opportunity_matrix)) {
      m.appendChild(
        chartHost(matrix("Opportunity Assessment Matrix", d.opportunity_matrix, true, d.risks)));
    }
    // ADR-0201: the plain-language "what the results mean" cards — deterministic template
    // sentences from the server (engine/sra_conclusions.py), rendered via el() (CSP-safe)
    var concl = document.getElementById("ssiConclusions");
    if (concl) {
      concl.innerHTML = "";
      (d.conclusions || []).forEach(function (c) {
        var card = el("div", { class: "concl-card concl-" + (c.severity || "info") });
        card.appendChild(el("div", { class: "concl-topic" }, c.topic));
        card.appendChild(el("div", { class: "concl-finding" }, c.finding));
        card.appendChild(el("div", { class: "concl-meaning" }, c.meaning));
        card.appendChild(el("div", { class: "concl-evidence" },
          (c.evidence || []).map(function (e) { return e.label + ": " + e.value; }).join("  ·  ")));
        concl.appendChild(card);
      });
    }

    renderCorrBadge(d.correlation_matrix);

    // frame the freshly-built charts/matrices: independent zoom + full screen + hover call-outs
    if (window.SFChartFrame) window.SFChartFrame.scan();
  }

  // The correlation-matrix feasibility badge (ADR-0270): after a run, say whether a supplied
  // matrix was feasible or was repaired to the nearest valid PSD matrix (never a silent fix).
  function renderCorrBadge(cm) {
    var cb = document.getElementById("corrBadge");
    if (!cb) return;
    cb.innerHTML = "";
    if (!cm || !cm.applied) return;
    var note = el("div", { class: "notice " + (cm.repaired ? "warn" : "ok"), role: "note" });
    note.textContent = cm.repaired
      ? "Correlation matrix: infeasible input REPAIRED to the nearest valid PSD matrix (entered " +
        "min eigenvalue " + cm.min_eigenvalue + ", Frobenius distance " + cm.frobenius_distance + ")."
      : "Correlation matrix: feasible (min eigenvalue " + cm.min_eigenvalue + ").";
    cb.appendChild(note);
  }

  function run() {
    var it = (document.getElementById("ssiIters") || {}).value || "1000";
    var dist = (document.getElementById("ssiDist") || {}).value || "triangular";
    status.textContent = "Running the Monte-Carlo…";
    fetch("/api/sra/ssi?iterations=" + encodeURIComponent(it) + "&distribution=" + encodeURIComponent(dist))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { status.textContent = res.j.error || "Run failed."; return; }
        status.textContent = "";
        renderResult(res.j);
        // the run cached a fresh per-activity Criticality Index server-side (ADR-0272); tell the
        // (decoupled) SSI grid to reload so its Gantt can tint by it.
        window.dispatchEvent(new Event("sf-ssi-run"));
      })
      .catch(function () { status.textContent = "Run failed."; });
  }

  function oat() {
    var out = document.getElementById("ssiOatOut");
    out.textContent = "Running deterministic sensitivity (re-solves the schedule twice per task)…";
    fetch("/api/sra/oat")
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        out.innerHTML = "";
        if (!res.ok) { out.textContent = res.j.error || "Sensitivity failed."; return; }
        if (!res.j.rows.length) {
          out.textContent = "No ranked tasks — assign Risk Ranking Factors and calculate Best/Worst durations first.";
          return;
        }
        if (res.j.note) {
          // ADR-0261 P5: a capped sweep says so on the panel — never a silent subset
          out.appendChild(el("div", { "class": "muted" }, res.j.note));
        }
        var t = el("table");
        t.appendChild(headerRow([["UID", ""], ["Task", ""], ["BC d", "bc_duration"],
          ["WC d", "wc_duration"], ["ML d", "ml_duration"],
          ["Opportunity (wd)", "opportunity_accelerate"], ["Risk (wd)", "risk_of_delay"],
          ["Total", "total_sensitivity"]]));
        res.j.rows.forEach(function (r) {
          t.appendChild(row([r.uid, r.name, r.bc_days, r.wc_days, r.ml_days,
            r.opportunity, r.risk, r.total]));
        });
        out.appendChild(t);
      })
      .catch(function () { out.textContent = "Sensitivity failed."; });
  }

  runBtn.addEventListener("click", run);
  var oatBtn = document.getElementById("ssiOat");
  if (oatBtn) oatBtn.addEventListener("click", oat);
})();
