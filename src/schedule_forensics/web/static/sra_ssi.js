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

  // a 5x5 heat grid: rows = consequence 5..1 (worst on top), cols = probability 1..5
  function matrix(title, grid) {
    var wrap = el("div", { class: "ssi-matrix" });
    wrap.appendChild(el("h4", null, title));
    var t = el("table", { class: "risk-matrix" });
    var hdr = el("tr");
    hdr.appendChild(el("th", null, "C\\P"));
    for (var p = 1; p <= 5; p++) hdr.appendChild(el("th", null, String(p)));
    t.appendChild(hdr);
    for (var c = 5; c >= 1; c--) {
      var tr = el("tr");
      tr.appendChild(el("th", null, String(c)));
      for (var pp = 1; pp <= 5; pp++) {
        var n = grid[c - 1][pp - 1];
        var score = c * pp;
        var band = score >= 20 ? "rk-extreme" : score >= 12 ? "rk-high"
          : score >= 6 ? "rk-mod" : score >= 3 ? "rk-low" : "rk-min";
        tr.appendChild(el("td", { class: "rk-cell " + band + (n ? " rk-hit" : "") },
          n ? String(n) : ""));
      }
      t.appendChild(tr);
    }
    wrap.appendChild(t);
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
    if (nonEmpty(d.risk_matrix)) m.appendChild(matrix("Risk Assessment Matrix (consequence × probability)", d.risk_matrix));
    if (nonEmpty(d.opportunity_matrix)) m.appendChild(matrix("Opportunity Assessment Matrix", d.opportunity_matrix));
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
