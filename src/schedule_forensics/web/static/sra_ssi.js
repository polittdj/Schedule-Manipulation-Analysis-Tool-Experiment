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

  function matrix(title, grid, opportunity) {
    var cons = opportunity ? CONS_OPP : CONS_RISK;
    var fam = opportunity ? "o" : "r"; // colour family
    var wrap = el("div", { class: "nasa-matrix" });
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
        var td = el("td", { class: "nm-cell nm-" + fam + "-" + ZONE[L - 1][C - 1] +
          (count ? " nm-hit" : "") });
        td.appendChild(el("span", { class: "nm-rank" }, String(RANK[L - 1][C - 1])));
        if (count) {
          td.appendChild(el("span", { class: "nm-badge", title: count + " here" }, String(count)));
        }
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
    t.appendChild(row(["Deterministic finish", d.deterministic.date + "  (P" + d.deterministic.percentile + ")"]));
    d.percentiles.forEach(function (p) { t.appendChild(row([p.label, p.date])); });
    t.appendChild(row(["Mean", d.mean]));
    t.appendChild(row(["Std deviation (working days)", d.std_days]));
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
    var m = document.getElementById("ssiMatrices");
    m.innerHTML = "";
    if (nonEmpty(d.risk_matrix)) m.appendChild(matrix("Risk Assessment Matrix", d.risk_matrix, false));
    if (nonEmpty(d.opportunity_matrix)) {
      m.appendChild(matrix("Opportunity Assessment Matrix", d.opportunity_matrix, true));
    }
  }

  function run() {
    var it = (document.getElementById("ssiIters") || {}).value || "1000";
    var dist = (document.getElementById("ssiDist") || {}).value || "triangular";
    status.textContent = "Running the SSI Monte-Carlo…";
    fetch("/api/sra/ssi?iterations=" + encodeURIComponent(it) + "&distribution=" + encodeURIComponent(dist))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { status.textContent = res.j.error || "Run failed."; return; }
        status.textContent = "";
        renderResult(res.j);
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
        var t = el("table");
        t.appendChild(row(["UID", "Task", "BC d", "WC d", "ML d",
          "Opportunity (wd)", "Risk (wd)", "Total"], true));
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
