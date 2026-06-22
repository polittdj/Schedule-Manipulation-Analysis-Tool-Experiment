/* Schedule Forensics — animated S-curve (cumulative planned vs actual progress).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Per loaded version, two cumulative curves
 * over a shared month axis on a LOCKED 0-100% scale: gold = planned (baseline finishes), blue
 * = actual/forecast (current finishes). The dashed line is that version's data date — actuals
 * to its left, forecast to its right. Prev/Next steps through the versions; Auto-play flips
 * through them so the actual curve visibly climbs (and lags the plan). Data: local /api/scurve.
 */
"use strict";

(function () {
  var box = document.getElementById("scurveChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var GOLD = "var(--warn)", BLUE = "var(--accent)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  var data = null, index = 0, timer = null;
  var gran = "month";  // time-scale granularity: "year" | "quarter" | "month"

  // ── multi-tier time axis ────────────────────────────────────────────────────────────────────
  // The month labels are the deck's "Mon-YY" form (e.g. "Mar-27"); parse them so the axis can be
  // drawn as up to three STACKED tiers — Year on top, then Quarter, then Month — like a Gantt
  // timeline header. The granularity selector chooses how many tiers show. Parsing is guarded: any
  // label that doesn't match falls the chart back to a single flat month tier (no crash).
  var MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
    Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
  function parseMonth(label) {
    var m = /^([A-Za-z]{3})-(\d{2})$/.exec(String(label));
    if (!m || MONTHS[m[1]] == null) return null;
    return { y: 2000 + parseInt(m[2], 10), m: MONTHS[m[1]] };
  }
  // Group consecutive months sharing a tier key into runs {start,end,label}.
  function tierRuns(months, keyOf, labelOf) {
    var out = [], cur = null;
    for (var i = 0; i < months.length; i++) {
      var pm = parseMonth(months[i]);
      var k = pm ? keyOf(pm) : "?" + i;
      if (cur && cur.key === k) { cur.end = i; }
      else { cur = { key: k, start: i, end: i, label: pm ? labelOf(pm) : months[i] }; out.push(cur); }
    }
    return out;
  }
  function yearRuns(months) {
    return tierRuns(months, function (p) { return p.y; }, function (p) { return String(p.y); });
  }
  function quarterRuns(months) {
    return tierRuns(months,
      function (p) { return p.y + "Q" + (Math.floor(p.m / 3) + 1); },
      function (p) { return "Q" + (Math.floor(p.m / 3) + 1) + " '" + String(p.y % 100); });
  }
  function monthRuns(months) {
    // first letter of each month in the lowest tier (J F M A M J J A S O N D) — the year/quarter
    // tiers above carry the full context, so single letters keep the densest tier legible.
    return tierRuns(months, function (p) { return p.y + "-" + p.m; },
      function (p) { return "JFMAMJJASOND".charAt(p.m); });
  }

  function curve(svg, series, color, x, y, dashed) {
    var pts = series.map(function (v, i) { return x(i) + "," + y(v); });
    var attrs = { points: pts.join(" "), fill: "none", stroke: color, "stroke-width": 2.5 };
    if (dashed) attrs["stroke-dasharray"] = "6 4";
    svg.appendChild(svgEl("polyline", attrs));
  }

  function render() {
    var v = data.versions[index];
    var months = data.months;
    document.getElementById("scurveLabel").textContent =
      (index + 1) + " / " + data.versions.length + " — " + v.label +
      (v.status_date ? " — data date " + v.status_date : "") +
      " (" + v.activities + " activities)";
    box.innerHTML = "";

    var W = 980, H = 360, padL = 40, padR = 14, padB = 46;
    var n = months.length;
    // stacked time tiers (top -> bottom): Year always; + Quarter / Month per the granularity pick.
    var TIER_TOP = 26, TIER_H = 16;
    var tiers;
    if (parseMonth(months[0])) {
      tiers = [{ runs: yearRuns(months), minW: 30 }];
      if (gran === "month" || gran === "quarter") tiers.push({ runs: quarterRuns(months), minW: 34 });
      if (gran === "month") tiers.push({ runs: monthRuns(months), minW: 9 });
    } else {
      tiers = [{ runs: months.map(function (lbl, i) {
        return { start: i, end: i, label: lbl };
      }), minW: 22 }];  // non-standard labels -> one flat month tier
    }
    var padT = TIER_TOP + tiers.length * TIER_H + 10;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "S-curve — cumulative planned vs actual progress");
    var x = function (i) { return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1)); };
    var slot = (n <= 1) ? (W - padL - padR) : (W - padL - padR) / (n - 1);
    // LOCKED 0-100% axis so every version's curves are directly comparable frame to frame.
    var y = function (pct) { return padT + (1 - pct / 100) * (H - padT - padB); };

    function tierEdges(s, e) {
      var left = (n <= 1) ? padL : x(s) - slot / 2;
      var right = (n <= 1) ? (W - padR) : x(e) + slot / 2;
      return [Math.max(padL, left), Math.min(W - padR, right)];
    }
    function drawTiers() {
      tiers.forEach(function (tier, r) {
        var rowTop = TIER_TOP + r * TIER_H;
        tier.runs.forEach(function (run) {
          var ed = tierEdges(run.start, run.end);
          svg.appendChild(svgEl("line", { x1: ed[0], y1: rowTop, x2: ed[0], y2: rowTop + TIER_H,
            stroke: "var(--line)", "stroke-width": 1 }));
          if (ed[1] - ed[0] >= tier.minW) {
            var t = svgEl("text", { x: (ed[0] + ed[1]) / 2, y: rowTop + TIER_H - 4,
              "text-anchor": "middle", fill: "var(--muted)", "font-size": 10 });
            t.textContent = run.label;
            svg.appendChild(t);
          }
        });
        svg.appendChild(svgEl("line", { x1: padL, y1: rowTop + TIER_H, x2: W - padR,
          y2: rowTop + TIER_H, stroke: "var(--line)", "stroke-width": 1 }));
      });
      svg.appendChild(svgEl("line", { x1: W - padR, y1: TIER_TOP, x2: W - padR,
        y2: TIER_TOP + tiers.length * TIER_H, stroke: "var(--line)", "stroke-width": 1 }));
    }

    var title = svgEl("text", { x: W / 2, y: 20, "text-anchor": "middle", fill: "var(--ink)", "font-size": 16, "font-weight": 600 });
    title.textContent = "Cumulative progress — " + v.label;
    svg.appendChild(title);

    drawTiers();  // stacked Year / Quarter / Month time-scale header

    // the planned-vs-actual gap at the data date (the headline number) — pinned to the
    // bottom-right corner so it never overlaps the centered title (which carries the schedule
    // name) or the bottom-left legend.
    if (v.status_index != null) {
      var gap = (v.planned[v.status_index] - v.actual[v.status_index]);
      var note = svgEl("text", { x: W - padR, y: H - 4, "text-anchor": "end", "font-size": 12, "font-weight": 700,
        fill: gap > 0 ? "var(--bad)" : "var(--ok)" });
      note.textContent = "At data date: " + v.actual[v.status_index].toFixed(0) + "% actual vs "
        + v.planned[v.status_index].toFixed(0) + "% planned (" + (gap > 0 ? "+" : "") + gap.toFixed(0) + " pts)";
      svg.appendChild(note);
    }

    // y gridlines at 0/25/50/75/100%
    [0, 25, 50, 75, 100].forEach(function (pct) {
      var gy = y(pct);
      svg.appendChild(svgEl("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1 }));
      var lab = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
      lab.textContent = pct + "%";
      svg.appendChild(lab);
    });

    // (month/quarter/year scale is the stacked tier header drawn above the plot)

    // dashed data-date marker
    if (v.status_index != null) {
      var sx = x(v.status_index);
      svg.appendChild(svgEl("line", { x1: sx, y1: padT, x2: sx, y2: y(0), stroke: "var(--muted)", "stroke-width": 1.5, "stroke-dasharray": "2 3" }));
      var sl = svgEl("text", { x: sx, y: padT - 4, "text-anchor": "middle", fill: "var(--muted)", "font-size": 10 });
      sl.textContent = v.status_date ? "data date " + v.status_date : "data date";
      svg.appendChild(sl);
    }

    curve(svg, v.planned, GOLD, x, y, false);
    curve(svg, v.actual, BLUE, x, y, false);

    // per-point hover call-outs: a transparent hit-strip per month over the plot so hovering
    // anywhere in a month's column shows that month's planned/actual values (shared chartframe tip)
    for (var hi = 0; hi < n; hi++) {
      var hx = (n <= 1) ? padL : x(hi) - slot / 2;
      var hw = (n <= 1) ? (W - padL - padR) : slot;
      if (hx < padL) { hw -= padL - hx; hx = padL; }
      if (hx + hw > W - padR) hw = (W - padR) - hx;
      var strip = svgEl("rect", {
        x: hx, y: padT, width: Math.max(hw, 1), height: (H - padB) - padT, fill: "transparent",
      });
      var stt = svgEl("title", {});
      stt.textContent =
        months[hi] + " — planned " + Math.round(v.planned[hi]) + "%, actual " +
        Math.round(v.actual[hi]) + "%" + (hi === v.status_index ? " · data date" : "");
      strip.appendChild(stt);
      svg.appendChild(strip);
    }

    // legend
    var legend = [["Planned (baseline)", GOLD], ["Actual / forecast", BLUE]];
    var lx = padL;
    legend.forEach(function (item) {
      svg.appendChild(svgEl("line", { x1: lx, y1: H - 8, x2: lx + 16, y2: H - 8, stroke: item[1], "stroke-width": 3 }));
      var lt = svgEl("text", { x: lx + 20, y: H - 4, fill: "var(--muted)", "font-size": 11 });
      lt.textContent = item[0];
      svg.appendChild(lt);
      lx += 20 + item[0].length * 6 + 24;
    });

    box.appendChild(svg);

    // A3 (WCAG 1.1.1): a visually-hidden data table of this version's curve values, so a
    // screen reader can read the planned-vs-actual numbers the curves draw (chart stays visual).
    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Cumulative progress — " + v.label + " (planned vs actual percent by month)",
        ["Month", "Planned %", "Actual %"],
        months.map(function (m, i) {
          return [m, Math.round(v.planned[i]) + "%", Math.round(v.actual[i]) + "%"];
        })
      ));
    }
    syncVersionSelect();
  }

  function step(delta) {
    if (!data) return;
    index = (index + delta + data.versions.length) % data.versions.length;
    render();
  }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("scurvePlay").textContent = "▶ Auto-play";
    syncVersionSelect();
  }
  function startAuto() {
    if (!data || timer) return;
    // A2: honor prefers-reduced-motion — advance one frame, don't auto-flip on a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    document.getElementById("scurvePlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1600);
    syncVersionSelect();
  }
  function toggleAuto() {
    if (!data) return;
    if (timer) { stopAuto(); return; }
    startAuto();
  }

  // ── file/version selector: "All files (chronological)" runs every version in order (Auto-play);
  // picking a single file pins the S-curve to just that one. Shown only when >1 version loaded. ──
  function buildVersionSelect() {
    var wrap = document.getElementById("scurveVersionWrap");
    var sel = document.getElementById("scurveVersion");
    if (!wrap || !sel || !data) return;
    sel.innerHTML = "";
    sel.appendChild(makeOption("all", "All files (chronological)"));
    data.versions.forEach(function (v, i) { sel.appendChild(makeOption(String(i), v.label)); });
    wrap.style.display = data.versions.length > 1 ? "" : "none";
    syncVersionSelect();
  }
  function syncVersionSelect() {
    var sel = document.getElementById("scurveVersion");
    if (sel && data) sel.value = timer ? "all" : String(index);
  }

  // ── per-chart filter: scope THIS S-curve by up to 5 (field, value) conditions over the parent
  // file's fields, independent of the page-wide Groups & Filters. Same-field rows OR; AND across
  // fields (engine filter_schedule semantics). Field values are embedded by the server. ──
  var FIELDS = window.SF_SCURVE_FIELDS || {};
  var MAX_ROWS = 5;

  function makeOption(value, text) {
    var o = document.createElement("option");
    o.value = value;
    o.textContent = text;
    return o;
  }
  function collectFilter() {
    var pairs = [];
    var rows = document.querySelectorAll("#scurveFilter .scf-row");
    for (var i = 0; i < rows.length; i++) {
      var f = rows[i].querySelector(".scf-field").value;
      var v = rows[i].querySelector(".scf-value").value;
      if (f && v) pairs.push([f, v]);
    }
    return pairs.slice(0, MAX_ROWS);
  }
  function buildURL() {
    var q = collectFilter().map(function (p) {
      return "cf=" + encodeURIComponent(p[0]) + "&cv=" + encodeURIComponent(p[1]);
    }).join("&");
    return "/api/scurve" + (q ? "?" + q : "");
  }
  function load() {
    stopAuto();
    fetch(buildURL())
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var lbl = document.getElementById("scurveLabel");
        if (!d.versions || !d.versions.length) {
          data = null;
          box.textContent = "No progress data to plot (no activities match the filter).";
          if (lbl) lbl.textContent = "";
          return;
        }
        data = d;
        index = 0;
        buildVersionSelect();
        render();
      })
      .catch(function () { box.textContent = "Failed to load the S-curve data."; });
  }
  function buildFilterUI() {
    var host = document.getElementById("scurveFilter");
    if (!host) return;
    var names = Object.keys(FIELDS).sort();
    if (!names.length) { var bar = document.getElementById("scurveFilterBar"); if (bar) bar.style.display = "none"; return; }
    for (var i = 0; i < MAX_ROWS; i++) {
      var row = document.createElement("span");
      row.className = "scf-row";
      var fsel = document.createElement("select");
      fsel.className = "scf-field";
      fsel.appendChild(makeOption("", "— field —"));
      names.forEach(function (f) { fsel.appendChild(makeOption(f, f)); });
      var vsel = document.createElement("select");
      vsel.className = "scf-value";
      vsel.appendChild(makeOption("", "— any —"));
      (function (fs, vs) {
        fs.addEventListener("change", function () {
          vs.innerHTML = "";
          vs.appendChild(makeOption("", "— any —"));
          (FIELDS[fs.value] || []).forEach(function (val) { vs.appendChild(makeOption(val, val)); });
          load();
        });
        vs.addEventListener("change", load);
      })(fsel, vsel);
      row.appendChild(fsel);
      row.appendChild(vsel);
      host.appendChild(row);
    }
    var clear = document.createElement("button");
    clear.type = "button";
    clear.className = "scf-clear";
    clear.textContent = "Clear";
    clear.addEventListener("click", function () {
      var fs = document.querySelectorAll("#scurveFilter .scf-field");
      for (var i = 0; i < fs.length; i++) fs[i].value = "";
      var vs = document.querySelectorAll("#scurveFilter .scf-value");
      for (var j = 0; j < vs.length; j++) { vs[j].innerHTML = ""; vs[j].appendChild(makeOption("", "— any —")); }
      load();
    });
    host.appendChild(clear);
  }

  document.getElementById("prevScurve").addEventListener("click", function () { stopAuto(); step(-1); });
  document.getElementById("nextScurve").addEventListener("click", function () { stopAuto(); step(1); });
  document.getElementById("scurvePlay").addEventListener("click", toggleAuto);
  var granSel = document.getElementById("scurveGran");
  if (granSel) {
    granSel.addEventListener("change", function () { gran = granSel.value; if (data) render(); });
  }
  var verSel = document.getElementById("scurveVersion");
  if (verSel) {
    verSel.addEventListener("change", function () {
      if (!data) return;
      if (verSel.value === "all") { stopAuto(); index = 0; render(); startAuto(); }
      else { stopAuto(); index = parseInt(verSel.value, 10) || 0; render(); }
    });
  }
  buildFilterUI();
  load();
})();
