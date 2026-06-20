/* Schedule Forensics — Schedule Risk Analysis (SRA) Monte-Carlo results.
 *
 * Dependency-free SVG (no CDN — air-gap posture; same-origin /api/sra only). Three charts:
 *   • #sraCdf  — the finish-date confidence S-curve (cumulative probability vs date) with
 *                P10/P50/P80/P90 markers and the deterministic CPM finish annotated with the
 *                percentile it sits at.
 *   • #sraHist — the finish-date histogram (count per date bin).
 *   • #sraSens — a duration-sensitivity tornado (top activities by |Spearman|) + a table.
 *
 * The simulation is run ONLY here (on load and on the Run button), never on page render, so the
 * page opens instantly; a slow run shows a status line, not a frozen page. Every figure is read
 * from the engine payload — the JS computes no schedule numbers of its own.
 */
"use strict";

(function () {
  var NS = "http://www.w3.org/2000/svg";
  var BLUE = "var(--accent)", GOLD = "var(--warn)", GREEN = "var(--ok)", BAD = "var(--bad)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      // CSS variables are invalid as SVG presentation attributes — route via style so the
      // charts recolor live when the light/dark theme switches.
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  // short, axis-friendly date label from an ISO datetime ("2026-06-20T…") → "2026-06-20"
  function shortDate(iso) { return String(iso).slice(0, 10); }

  // ── #sraCdf: the confidence S-curve ───────────────────────────────────────────────────
  function renderCdf(data) {
    var box = document.getElementById("sraCdf");
    if (!box) return;
    box.innerHTML = "";
    var cdf = data.cdf || [];
    if (!cdf.length) { box.textContent = "No simulation data."; return; }
    var W = 980, H = 360, padL = 44, padR = 110, padT = 24, padB = 56;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });

    // x axis is the run of finish dates (index-spaced so the step S-curve reads evenly);
    // y axis is cumulative probability 0–100%.
    var n = cdf.length;
    var x = function (i) { return padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1)); };
    var y = function (p) { return padT + (1 - p) * (H - padT - padB); };

    // y gridlines + % labels
    [0, 0.25, 0.5, 0.75, 1].forEach(function (frac) {
      var gy = y(frac);
      svg.appendChild(svgEl("line", {
        x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1,
      }));
      var lab = svgEl("text", {
        x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
      });
      lab.textContent = Math.round(frac * 100) + "%";
      svg.appendChild(lab);
    });

    // x date labels, thinned
    var step = Math.max(1, Math.ceil(n / 12));
    for (var i = 0; i < n; i++) {
      if (i % step === 0 || i === n - 1) {
        var ml = svgEl("text", {
          x: x(i), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + x(i) + " " + (H - padB + 16) + ")",
        });
        ml.textContent = shortDate(cdf[i][0]);
        svg.appendChild(ml);
      }
    }

    // the S-curve line
    var pts = cdf.map(function (pt, idx) { return x(idx) + "," + y(pt[1]); });
    svg.appendChild(svgEl("polyline", {
      points: pts.join(" "), fill: "none", stroke: BLUE, "stroke-width": 2, "class": "sf-curve-line",
    }));

    // map an ISO date to the nearest x via its first occurrence in the cdf date run
    function indexForDate(iso) {
      for (var j = 0; j < n; j++) { if (cdf[j][0] >= iso) return j; }
      return n - 1;
    }
    function probForDate(iso) {
      for (var j = 0; j < n; j++) { if (cdf[j][0] >= iso) return cdf[j][1]; }
      return 1;
    }

    // P-markers: a vertical drop + horizontal lead to the curve, labelled at the right margin
    (data.percentiles || []).forEach(function (p) {
      var idx = indexForDate(p.date);
      var py = y(probForDate(p.date));
      var px = x(idx);
      svg.appendChild(svgEl("line", {
        x1: px, y1: y(0), x2: px, y2: py, stroke: GOLD, "stroke-width": 1, "stroke-dasharray": "3 3",
      }));
      svg.appendChild(svgEl("circle", { cx: px, cy: py, r: 3, fill: GOLD }));
      var lab = svgEl("text", {
        x: W - padR + 6, y: py + 4, fill: GOLD, "font-size": 11, "font-weight": 600,
      });
      lab.textContent = p.label + " " + shortDate(p.date);
      svg.appendChild(lab);
    });

    // the deterministic CPM finish — a distinct marker annotated with its percentile
    var det = data.deterministic;
    if (det && det.date) {
      var di = indexForDate(det.date);
      var dx = x(di);
      var dy = y(probForDate(det.date));
      svg.appendChild(svgEl("line", {
        x1: dx, y1: padT, x2: dx, y2: y(0), stroke: BAD, "stroke-width": 2, "stroke-dasharray": "6 4",
      }));
      svg.appendChild(svgEl("circle", { cx: dx, cy: dy, r: 4, fill: BAD }));
      var dlab = svgEl("text", { x: dx + 6, y: padT + 10, fill: BAD, "font-size": 11, "font-weight": 700 });
      dlab.textContent = "deterministic finish — P" + det.percentile;
      svg.appendChild(dlab);
    }

    if (window.SFA11y) SFA11y.label(svg, "Finish-date confidence S-curve");
    box.appendChild(svg);

    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Finish-date confidence — cumulative probability by date",
        ["Finish date", "Cumulative probability"],
        cdf.map(function (pt) { return [shortDate(pt[0]), Math.round(pt[1] * 1000) / 10 + "%"]; })
      ));
    }
  }

  // ── #sraHist: the finish-date histogram ───────────────────────────────────────────────
  function renderHist(data) {
    var box = document.getElementById("sraHist");
    if (!box) return;
    box.innerHTML = "";
    var hist = data.histogram || [];
    if (!hist.length) { box.textContent = "No simulation data."; return; }
    var W = 980, H = 320, padL = 40, padR = 14, padT = 20, padB = 56;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = hist.length;
    var top = 1;
    hist.forEach(function (b) { if (b[2] > top) top = b[2]; });
    var slot = (W - padL - padR) / n;
    var barW = Math.max(1.5, slot * 0.8);
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };
    var xc = function (i) { return padL + i * slot + slot / 2; };

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

    var step = Math.max(1, Math.ceil(n / 12));
    for (var i = 0; i < n; i++) {
      var b = hist[i];
      if (b[2] > 0) {
        svg.appendChild(svgEl("rect", {
          x: xc(i) - barW / 2, y: y(b[2]), width: barW, height: y(0) - y(b[2]), fill: GREEN,
        }));
      }
      if (i % step === 0 || i === n - 1) {
        var ml = svgEl("text", {
          x: xc(i), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + xc(i) + " " + (H - padB + 16) + ")",
        });
        ml.textContent = shortDate(b[0]);
        svg.appendChild(ml);
      }
    }

    if (window.SFA11y) SFA11y.label(svg, "Finish-date distribution histogram");
    box.appendChild(svg);

    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Finish-date distribution — count per bin",
        ["Bin start", "Bin end", "Count"],
        hist.map(function (bn) { return [shortDate(bn[0]), shortDate(bn[1]), bn[2]]; })
      ));
    }
  }

  // ── #sraSens: the duration-sensitivity tornado + table ────────────────────────────────
  function renderSens(data) {
    var box = document.getElementById("sraSens");
    if (!box) return;
    box.innerHTML = "";
    var rows = data.sensitivity || [];
    if (!rows.length) { box.textContent = "No sensitivity data."; return; }

    var W = 980, padL = 220, padR = 60, rowH = 22, padT = 10;
    var H = padT * 2 + rows.length * rowH;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var maxAbs = 0;
    rows.forEach(function (r) { if (Math.abs(r.sens) > maxAbs) maxAbs = Math.abs(r.sens); });
    if (maxAbs <= 0) maxAbs = 1;
    var mid = padL + (W - padL - padR) / 2;
    var halfW = (W - padL - padR) / 2;

    // centre axis
    svg.appendChild(svgEl("line", {
      x1: mid, y1: padT, x2: mid, y2: H - padT, stroke: "var(--line)", "stroke-width": 1,
    }));

    rows.forEach(function (r, i) {
      var cy = padT + i * rowH + rowH / 2;
      var w = (Math.abs(r.sens) / maxAbs) * halfW;
      var positive = r.sens >= 0;
      var bx = positive ? mid : mid - w;
      svg.appendChild(svgEl("rect", {
        x: bx, y: cy - rowH * 0.32, width: Math.max(w, 0.5), height: rowH * 0.64,
        fill: positive ? GOLD : BLUE,
      }));
      // activity label (UID + truncated name) on the left
      var name = r.name ? (" " + r.name) : "";
      var label = "UID " + r.uid + name;
      if (label.length > 34) label = label.slice(0, 33) + "…";
      var lab = svgEl("text", {
        x: padL - 8, y: cy + 4, "text-anchor": "end", fill: "var(--ink)", "font-size": 11,
      });
      lab.textContent = label;
      svg.appendChild(lab);
      // sensitivity value at the bar end
      var val = svgEl("text", {
        x: positive ? bx + w + 4 : bx - 4, y: cy + 4,
        "text-anchor": positive ? "start" : "end", fill: "var(--muted)", "font-size": 10,
      });
      val.textContent = r.sens.toFixed(2);
      svg.appendChild(val);
    });

    if (window.SFA11y) SFA11y.label(svg, "Duration-sensitivity tornado");
    box.appendChild(svg);

    // the companion table (UID, name, Criticality Index %, Sensitivity, SSI)
    var tbl = document.createElement("table");
    var thead = document.createElement("thead");
    var htr = document.createElement("tr");
    ["UID", "Activity", "Criticality Index", "Sensitivity", "SSI"].forEach(function (h) {
      var th = document.createElement("th");
      th.setAttribute("scope", "col");
      th.textContent = h;
      htr.appendChild(th);
    });
    thead.appendChild(htr);
    tbl.appendChild(thead);
    var tbody = document.createElement("tbody");
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      var cells = [
        String(r.uid), r.name || "", Math.round(r.ci * 1000) / 10 + "%",
        r.sens.toFixed(3), r.ssi.toFixed(3),
      ];
      cells.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    box.appendChild(tbl);
  }

  function setStatus(text) {
    var el = document.getElementById("sraStatus");
    if (el) el.textContent = text;
  }

  function run() {
    var itersEl = document.getElementById("sraIters");
    var iters = itersEl ? itersEl.value : "1000";
    // The risk inputs (global triangular + per-activity overrides) live on the session and are set
    // via POST /sra/risk (which reloads this page); the run only needs the iteration count.
    setStatus("Running the simulation… (this can take a moment on a large schedule)");
    fetch("/api/sra?iterations=" + encodeURIComponent(iters))
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d && d.error ? d.error : "request failed (" + r.status + ")");
          return d;
        });
      })
      .then(function (data) {
        renderCdf(data);
        renderHist(data);
        renderSens(data);
        var p = {};
        (data.percentiles || []).forEach(function (x) { p[x.label] = shortDate(x.date); });
        var msg = data.iterations + " iterations · P50 " + (p.P50 || "?") + " · P80 " + (p.P80 || "?");
        if (data.auto_used) {
          msg += " · auto defaults used (screening placeholder, not SME-validated)";
        }
        if (data.constraints_flagged) {
          msg += " · warning: " + data.constraints_flagged +
            " hard constraint(s) cap the distribution";
        }
        setStatus(msg);
      })
      .catch(function (err) {
        setStatus("Could not run the simulation: " + (err && err.message ? err.message : err));
      });
  }

  var btn = document.getElementById("sraRun");
  if (btn) btn.addEventListener("click", run);
  run();  // run once on load (off the page-render path)
})();
