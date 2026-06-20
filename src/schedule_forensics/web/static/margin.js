/* Schedule Forensics — schedule-margin burndown across versions (Trend page).
 *
 * Dependency-free SVG (no CDN — air-gap posture, same-origin only). Two lines over the loaded
 * versions on one LOCKED y-axis (working days): TOTAL margin (var(--accent)) = the buffer nominally
 * in the schedule; EFFECTIVE margin (var(--ok)) = the buffer actually protecting the finish. The
 * x-axis is each version's data date (fallback v1, v2 …), so a buffer being spent or quietly removed
 * reads as a falling line left to right. Data: local /api/margin.
 */
"use strict";

(function () {
  var box = document.getElementById("marginBurndown");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var TOTAL = "var(--accent)", EFFECTIVE = "var(--ok)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function xLabels(versions) {
    return versions.map(function (v, i) { return v.status_date || "v" + (i + 1); });
  }

  function draw(versions) {
    box.innerHTML = "";
    var labels = xLabels(versions);
    var totals = versions.map(function (v) { return v.total; });
    var effectives = versions.map(function (v) { return v.effective; });

    var W = 980, H = 320, padL = 40, padR = 14, padT = 24, padB = 50;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = versions.length;
    // LOCKED y-axis: the tallest of either line (min 1) so the two series are directly comparable.
    var top = 1;
    totals.concat(effectives).forEach(function (v) { if (v > top) top = v; });
    var x = function (i) { return padL + (n <= 1 ? (W - padL - padR) / 2 : (i * (W - padL - padR)) / (n - 1)); };
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };

    // y gridlines + working-day labels
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
    var unit = svgEl("text", { x: padL - 6, y: padT - 8, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
    unit.textContent = "working days";
    svg.appendChild(unit);

    // x (version) labels, thinned to avoid overlap, rotated for legibility
    var step = Math.max(1, Math.ceil(n / 16));
    for (var i = 0; i < n; i++) {
      if (i % step === 0) {
        var ml = svgEl("text", {
          x: x(i), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + x(i) + " " + (H - padB + 16) + ")",
        });
        ml.textContent = labels[i];
        svg.appendChild(ml);
      }
    }

    // the two lines + a marker per point
    [
      { values: totals, color: TOTAL },
      { values: effectives, color: EFFECTIVE },
    ].forEach(function (s) {
      var pts = s.values.map(function (v, idx) { return x(idx) + "," + y(v); });
      svg.appendChild(svgEl("polyline", {
        points: pts.join(" "), fill: "none", stroke: s.color, "stroke-width": 2,
        "class": "sf-curve-line",
      }));
      s.values.forEach(function (v, idx) {
        svg.appendChild(svgEl("circle", { cx: x(idx), cy: y(v), r: 3, fill: s.color }));
      });
    });

    // legend
    var legend = [["Total margin", TOTAL], ["Effective margin", EFFECTIVE]];
    var lx = padL;
    legend.forEach(function (item) {
      svg.appendChild(svgEl("line", { x1: lx, y1: H - 6, x2: lx + 16, y2: H - 6, stroke: item[1], "stroke-width": 3 }));
      var lt = svgEl("text", { x: lx + 20, y: H - 2, fill: "var(--muted)", "font-size": 11 });
      lt.textContent = item[0];
      svg.appendChild(lt);
      lx += 20 + item[0].length * 6 + 24;
    });

    if (window.SFA11y) SFA11y.label(svg, "Schedule margin burndown — total vs effective margin by version");
    box.appendChild(svg);

    // A11y (WCAG 1.1.1): a visually-hidden data table of the numbers the lines draw.
    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Schedule margin burndown — total and effective margin (working days) by version",
        ["Version", "Total wd", "Effective wd"],
        versions.map(function (v, i) { return [labels[i], v.total, v.effective]; })
      ));
    }
  }

  fetch("/api/margin")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var versions = data.versions || [];
      if (!versions.length) { box.textContent = "No data."; return; }
      var anyMargin = versions.some(function (v) { return v.total || v.effective; });
      if (!anyMargin) {
        var note = document.createElement("p");
        note.className = "muted";
        note.textContent = "No schedule-margin tasks (named 'margin') in any loaded version.";
        box.innerHTML = "";
        box.appendChild(note);
        return;
      }
      draw(versions);
    })
    .catch(function () { box.textContent = "Failed to load the schedule-margin data."; });
})();
