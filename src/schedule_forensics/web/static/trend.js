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

  // Version names often share a long common prefix (e.g. "USA_marvik_USA_marvik_…");
  // strip it (keeping a leading …) and cap the length so axis labels never overlap.
  function shortLabels(labels) {
    if (labels.length < 2) return labels.map(function (l) { return l.slice(0, 16); });
    var prefix = labels[0];
    labels.forEach(function (l) {
      var i = 0;
      while (i < prefix.length && i < l.length && prefix[i] === l[i]) i++;
      prefix = prefix.slice(0, i);
    });
    var cut = prefix.length >= 6 ? prefix.length : 0;
    return labels.map(function (l) {
      var s = (cut ? "…" + l.slice(cut) : l).replace(/\.(mpp|xml|xer|json|mspdi)$/i, "");
      return s.length > 16 ? s.slice(0, 15) + "…" : s;
    });
  }

  // One line chart: values (numbers) per version label; valueText renders the dot label.
  function lineChart(title, labels, values, valueText, color) {
    var W = 460, H = 210, padL = 14, padR = 14, padT = 26, padB = 54;
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
      // rotated, prefix-stripped labels so long version names never overlap
      var lab = svgEl("text", {
        x: x(i), y: H - padB + 14, "text-anchor": "end", fill: "#8b98a5", "font-size": 10,
        transform: "rotate(-35 " + x(i) + " " + (H - padB + 14) + ")",
      });
      lab.textContent = labels[i];
      svg.appendChild(lab);
    });
    wrap.appendChild(svg);
    box.appendChild(wrap);
  }

  var target = box.dataset.target;
  fetch("/api/trend" + (target ? "?target=" + encodeURIComponent(target) : ""))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var labels = shortLabels(data.versions.map(function (v) { return v.label; }));
      // the focus activity's finish movement leads when a target UID is set
      if (data.target && data.target.finishes && data.target.finishes.some(function (f) { return f; })) {
        var fin = data.target.finishes.map(function (f) { return f ? Date.parse(f) / 86400000 : null; });
        var fbase = null;
        fin.forEach(function (v) { if (fbase == null && v != null) fbase = v; });
        lineChart(
          "UID " + data.target.uid + (data.target.name ? " — " + data.target.name : "") + " finish (days vs first)",
          labels,
          fin.map(function (v) { return v == null ? 0 : v - fbase; }),
          function (v, i) { return data.target.finishes[i] || "n/a"; },
          "#e6a4ff"
        );
      }
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
