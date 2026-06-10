/* Schedule Forensics — cross-version trend charts.
 *
 * Dependency-free SVG line charts (no CDN, no external fetch — air-gap posture).
 * Data comes from the local /api/trend endpoint: per-version headline numbers
 * (project finish, completed, in progress, critical) and the quality-metric series.
 */
"use strict";

(function () {
  var box = document.getElementById("trendCharts");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    return node;
  }

  // One line chart: values (numbers) per version label; valueText renders the dot label.
  function lineChart(title, labels, values, valueText, color) {
    var W = 460, H = 200, padL = 14, padR = 14, padT = 26, padB = 44;
    var wrap = document.createElement("div");
    wrap.className = "chart";
    var h = document.createElement("h3");
    h.textContent = title;
    wrap.appendChild(h);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    if (lo === hi) { lo -= 1; hi += 1; }
    var n = values.length;
    var x = function (i) { return padL + (n === 1 ? 0 : (i * (W - padL - padR)) / (n - 1)); };
    var y = function (v) { return padT + ((hi - v) * (H - padT - padB)) / (hi - lo); };
    var pts = values.map(function (v, i) { return x(i) + "," + y(v); }).join(" ");
    svg.appendChild(svgEl("polyline", {
      points: pts, fill: "none", stroke: color, "stroke-width": 2.5,
    }));
    values.forEach(function (v, i) {
      svg.appendChild(svgEl("circle", { cx: x(i), cy: y(v), r: 4, fill: color }));
      var val = svgEl("text", {
        x: x(i), y: y(v) - 9, "text-anchor": "middle", fill: "#e6edf3", "font-size": 12,
      });
      val.textContent = valueText(v, i);
      svg.appendChild(val);
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 16, "text-anchor": "middle", fill: "#8b98a5", "font-size": 11,
      });
      lab.textContent = labels[i].length > 18 ? labels[i].slice(0, 17) + "…" : labels[i];
      svg.appendChild(lab);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  fetch("/api/trend")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var labels = data.versions.map(function (v) { return v.label; });
      // project finish as a date line (days since the first version's finish)
      var finishDays = data.versions.map(function (v) { return Date.parse(v.finish) / 86400000; });
      var base = finishDays[0];
      lineChart(
        "Project finish (days vs first version)",
        labels,
        finishDays.map(function (d) { return d - base; }),
        function (v, i) { return data.versions[i].finish; },
        "#4aa3ff"
      );
      lineChart("Completed activities", labels,
        data.versions.map(function (v) { return v.completed; }),
        function (v) { return String(v); }, "#3fb950");
      lineChart("Critical (incomplete) activities", labels,
        data.versions.map(function (v) { return v.critical; }),
        function (v) { return String(v); }, "#f85149");
      var ml = data.quality.missing_logic;
      if (ml) {
        lineChart("Missing logic (activities)", labels, ml.values,
          function (v) { return String(v); }, "#d29922");
      }
    })
    .catch(function () { box.textContent = "Failed to load trend data."; });
})();
