/* Schedule Forensics — total-float distribution histogram (handbook §6.3.2.5.2.2; assessment deck).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Bins every non-summary activity by its Total Float
 * (working days) into DCMA-aligned buckets, so the *shape* of the float distribution is visible: mass
 * at 0 / negative is the critical+behind core, a spike in the high (> 44 d) bucket is float padding /
 * missing successor logic. Data: the local /api/analysis/<name> endpoint (the same activity rows the
 * grid and scatter use); the page's full activity grid is the accessible data table.
 */
"use strict";

(function () {
  var box = document.getElementById("floatHist");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";

  // fixed, meaningful buckets (aligned to the DCMA float bands: 0, <5, <10, high > 44 working days)
  var BUCKETS = [
    { label: "< 0", lo: -Infinity, hi: 0, crit: true },     // negative float — behind a constraint
    { label: "0", lo: 0, hi: 0, crit: true },               // zero float — critical
    { label: "1–5", lo: 1, hi: 5 },
    { label: "6–10", lo: 6, hi: 10 },
    { label: "11–20", lo: 11, hi: 20 },
    { label: "21–44", lo: 21, hi: 44 },
    { label: "> 44", lo: 45, hi: Infinity, high: true },    // high float — DCMA-06 / missing logic
  ];

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function bucketOf(v) {
    if (v < 0) return 0;
    if (v === 0) return 1;
    for (var i = 2; i < BUCKETS.length; i++) {
      if (v <= BUCKETS[i].hi) return i;  // 0 < v <= hi (fractional floats land in the 1-5 band)
    }
    return BUCKETS.length - 1;  // the open-ended high bucket
  }

  // ---- the click-drill panel (operator 2026-07-08): chart on the left, the selected band's
  // activities on the right, with a Gantt-style add/remove-columns dropdown (standard + custom
  // fields) and an Excel export of exactly the selection ----------------------------------
  var drill = document.getElementById("floatHistDrill");
  var acts = [];            // every non-summary activity with a float value
  var customLabels = [];    // the schedule's mapped custom fields (payload-discovered)
  var drillCols = [];       // [{key, label, on, custom}] — persists across bar clicks
  var selectedBand = null;

  function drillFields() {
    if (drillCols.length) return drillCols;
    drillCols = [
      { key: "unique_id", label: "UID", on: true },
      { key: "name", label: "Name", on: true },
      { key: "total_float_days", label: "Total float (d)", on: true },
      { key: "start", label: "Start", on: false },
      { key: "finish", label: "Finish", on: false },
      { key: "duration_days", label: "Duration (d)", on: false },
      { key: "free_float_days", label: "Free float (d)", on: false },
      { key: "percent_complete", label: "% complete", on: false },
      { key: "is_critical", label: "Critical", on: false },
      { key: "resource_names", label: "Resources", on: false },
      { key: "wbs", label: "WBS", on: false },
      { key: "baseline_start", label: "Baseline start", on: false },
      { key: "baseline_finish", label: "Baseline finish", on: false },
    ];
    customLabels.forEach(function (lbl) {
      drillCols.push({ key: lbl, label: lbl, on: false, custom: true });
    });
    return drillCols;
  }

  function cellValue(a, f) {
    var v = Object.prototype.hasOwnProperty.call(a, f.key) ? a[f.key]
      : (a.custom ? a.custom[f.key] : null);
    if (v === true) return "yes";
    if (v === false) return "no";
    if (v == null) return "";
    var s = String(v);
    return (window.SFGantt && SFGantt.fmtMDY(s)) || s;
  }

  function el(tag, attrs) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else if (k === "class") node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function renderDrill() {
    if (!drill || selectedBand === null) return;
    var i = selectedBand;
    var rows = acts.filter(function (a) { return bucketOf(a.total_float_days) === i; });
    var fields = drillFields().filter(function (f) { return f.on; });
    drill.textContent = "";
    var name = box.getAttribute("data-name") || "";
    drill.appendChild(el("h3", {
      text: rows.length + (rows.length === 1 ? " activity" : " activities") +
        " with total float " + BUCKETS[i].label + " working days",
    }));
    var bar = el("div", { class: "hist-drill-bar" });
    var colMount = el("span", { class: "field-toggles" });
    if (window.SFChecklist) {
      colMount.appendChild(SFChecklist.filter({
        values: drillFields().map(function (f) { return f.label; }),
        selected: new Set(drillFields().filter(function (f) { return f.on; })
          .map(function (f) { return f.label; })),
        label: "Columns",
        title: "Add or remove columns (standard and custom fields, like the Gantt)",
        onChange: function (sel) {
          drillFields().forEach(function (f) { f.on = sel ? sel.has(f.label) : true; });
          renderDrill();
        },
      }));
    }
    bar.appendChild(colMount);
    // Excel export of exactly this selection: the band index + the extra columns beyond UID/Name/float
    var extra = fields.filter(function (f) {
      return ["unique_id", "name", "total_float_days"].indexOf(f.key) < 0;
    }).map(function (f) { return f.key; });
    var href = "/export/xlsx/float-band/" + encodeURIComponent(name) + "?band=" + i +
      (extra.length ? "&cols=" + encodeURIComponent(extra.join(",")) : "");
    var x = el("a", { class: "btn-link", href: href, text: "Excel (this selection)" });
    bar.appendChild(x);
    drill.appendChild(bar);
    var scroller = el("div", { class: "hist-drill-scroll" });
    var table = el("table", { class: "hist-drill-table" });
    var thead = el("thead");
    var hr = el("tr");
    fields.forEach(function (f) { hr.appendChild(el("th", { text: f.label })); });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = el("tbody");
    rows.forEach(function (a) {
      var tr = el("tr");
      fields.forEach(function (f) { tr.appendChild(el("td", { text: cellValue(a, f) })); });
      tbody.appendChild(tr);
    });
    if (!rows.length) {
      var tr0 = el("tr");
      tr0.appendChild(el("td", { class: "muted", text: "No activities in this band." }));
      tbody.appendChild(tr0);
    }
    table.appendChild(tbody);
    scroller.appendChild(table);
    drill.appendChild(scroller);
  }

  var lastFloats = null; // repaint source for the selected-band outline

  function render(floats) {
    lastFloats = floats;
    box.innerHTML = "";
    var counts = BUCKETS.map(function () { return 0; });
    floats.forEach(function (v) { counts[bucketOf(v)] += 1; });
    var top = Math.max.apply(null, counts) || 1;
    var total = floats.length;

    var n = BUCKETS.length;
    var W = 940, H = 360, padL = 44, padR = 16, padT = 18, padB = 54;
    var slot = (W - padL - padR) / n;
    var barW = slot * 0.7;
    var y = function (c) { return padT + (1 - c / top) * (H - padT - padB); };
    var xc = function (i) { return padL + i * slot + slot / 2; };

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "Total-float distribution histogram");

    // y gridlines + count labels
    [0, 0.25, 0.5, 0.75, 1].forEach(function (frac) {
      var gy = y(top * frac);
      svg.appendChild(svgEl("line", {
        x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1,
      }));
      var lab = svgEl("text", {
        x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
      });
      lab.textContent = String(Math.round(top * frac));
      svg.appendChild(lab);
    });

    BUCKETS.forEach(function (b, i) {
      var c = counts[i];
      var col = b.crit ? "var(--bad)" : (b.high ? "var(--warn)" : "var(--accent)");
      if (c > 0) {
        var pct = total ? Math.round((c / total) * 100) : 0;
        var bar = svgEl("rect", {
          x: xc(i) - barW / 2, y: y(c), width: barW, height: y(0) - y(c), fill: col,
        });
        var bt = svgEl("title", {});
        bt.textContent =
          b.label + " working days: " + c + (c === 1 ? " activity" : " activities") +
          " (" + pct + "% of " + total + ")";
        bar.appendChild(bt);  // shared chartframe call-out reads this on hover
        svg.appendChild(bar);
        var cn = svgEl("text", {
          x: xc(i), y: y(c) - 5, "text-anchor": "middle", fill: "var(--ink)", "font-size": 11,
        });
        cn.textContent = String(c);
        svg.appendChild(cn);
      }
      var lab = svgEl("text", {
        x: xc(i), y: H - padB + 18, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11,
      });
      lab.textContent = b.label;
      svg.appendChild(lab);
      // full-height transparent hit strip: EVERY band is clickable (even a zero-count one) —
      // the click fills the right-hand drill panel with the band's activities
      var hit = svgEl("rect", {
        x: padL + i * slot, y: padT, width: slot, height: H - padT - padB,
        fill: "transparent", "data-band": String(i),
      });
      hit.style.cursor = "pointer";
      var ht = svgEl("title", {});
      ht.textContent = "Click to list the " + b.label + "-day activities on the right";
      hit.appendChild(ht);
      hit.addEventListener("click", function () {
        selectedBand = i;
        render(lastFloats); // repaint so the selected band is outlined
        renderDrill();
      });
      svg.appendChild(hit);
      if (selectedBand === i) {
        svg.appendChild(svgEl("rect", {
          x: padL + i * slot + 1, y: padT, width: slot - 2, height: H - padT - padB,
          fill: "none", stroke: "var(--focus)", "stroke-width": 1.5, "stroke-dasharray": "4 3",
          "pointer-events": "none",
        }));
      }
    });
    // x-axis caption
    var cap = svgEl("text", {
      x: (padL + W - padR) / 2, y: H - 6, "text-anchor": "middle", fill: "var(--muted)",
      "font-size": 11,
    });
    cap.textContent = "Total float (working days)";
    svg.appendChild(cap);
    box.appendChild(svg);

    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Total-float distribution — activity count per band",
        ["Total float (working days)", "Activities"],
        BUCKETS.map(function (b, i) { return [b.label, counts[i]]; })
      ));
    }
  }

  var name = box.getAttribute("data-name") || "";
  fetch("/api/analysis/" + encodeURIComponent(name))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      acts = (d.activities || [])
        .filter(function (a) { return !a.is_summary && a.total_float_days != null; });
      customLabels = d.custom_field_labels || [];
      var floats = acts.map(function (a) { return a.total_float_days; });
      if (!floats.length) { box.textContent = "No activity float data to plot."; return; }
      render(floats);
    })
    .catch(function () { box.textContent = "Failed to load the float-distribution data."; });
})();
