/* Schedule Forensics — Year Phases animated stepper.
 *
 * Dependency-free SVG (no CDN — air-gap posture). Steps through every loaded version (oldest
 * first); each frame is that version's per-year activity makeup — complete / in-progress /
 * planned — as stacked bars on a LOCKED axis (years = the union across versions, height = the
 * tallest year in any version), so you watch the work distribution shift submission to
 * submission instead of reading one static chart. Prev/Next step; Auto-play flips through them.
 * Data: the local /api/phases endpoint (binning basis from the container's data-basis).
 */
"use strict";

(function () {
  var box = document.getElementById("phasesChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var OK = "var(--ok)", WARN = "var(--warn)", ACC = "var(--accent)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  var data = null, index = 0, timer = null, top = 1, years = [];

  function render() {
    var v = data.versions[index];
    document.getElementById("phasesLabel").textContent =
      (index + 1) + " / " + data.versions.length + " — " + v.label +
      (v.status_date ? " — data date " + v.status_date : "") +
      (v.undated ? " · " + v.undated + " undated" : "");
    box.innerHTML = "";

    var W = 940, H = 340, padL = 40, padR = 14, padT = 30, padB = 46;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "Year phases — activities per year (" + v.label + ")");
    var n = years.length;
    var slot = (W - padL - padR) / Math.max(n, 1);
    var bw = Math.min(46, slot * 0.6);
    var plotH = H - padT - padB;
    var y = function (val) { return padT + (1 - val / top) * plotH; };

    var title = svgEl("text", { x: W / 2, y: 18, "text-anchor": "middle", fill: "var(--ink)", "font-size": 15, "font-weight": 600 });
    title.textContent = "Activities per year — " + (data.basis_label || "");
    svg.appendChild(title);

    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var gy = y(top * f);
      svg.appendChild(svgEl("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1 }));
      var lab = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
      lab.textContent = String(Math.round(top * f));
      svg.appendChild(lab);
    });

    var step = Math.max(1, Math.ceil(n / 24));
    v.rows.forEach(function (r, i) {
      var cx = padL + slot * i + slot / 2, x0 = cx - bw / 2, ybase = y(0);
      [[r.planned, ACC], [r.in_progress, WARN], [r.complete, OK]].forEach(function (p) {
        if (p[0] <= 0) return;
        var h = (p[0] / top) * plotH;
        svg.appendChild(svgEl("rect", { x: x0, y: ybase - h, width: bw, height: h, fill: p[1] }));
        ybase -= h;
      });
      if (i % step === 0) {
        var yl = svgEl("text", { x: cx, y: H - padB + 15, "text-anchor": "middle", fill: "var(--muted)", "font-size": 10 });
        yl.textContent = r.year;
        svg.appendChild(yl);
      }
      if (r.total > 0) {
        var tl = svgEl("text", { x: cx, y: y(r.total) - 4, "text-anchor": "middle", fill: "var(--ink)", "font-size": 9 });
        tl.textContent = String(r.total);
        svg.appendChild(tl);
      }
    });
    box.appendChild(svg);

    var legend = document.createElement("div");
    legend.className = "chart-legend";
    [["Complete", OK], ["In progress", WARN], ["Planned", ACC]].forEach(function (it) {
      var cell = document.createElement("span");
      cell.className = "chart-legend-item";
      var sw = document.createElement("span");
      sw.className = "chart-swatch";
      sw.style.background = it[1];
      cell.appendChild(sw);
      cell.appendChild(document.createTextNode(it[0]));
      legend.appendChild(cell);
    });
    box.appendChild(legend);

    if (window.SFA11y) {
      box.appendChild(SFA11y.table(
        "Year phases — " + v.label,
        ["Year", "Total", "Complete", "In progress", "Planned", "Milestones"],
        v.rows.map(function (r) {
          return [r.year, r.total, r.complete, r.in_progress, r.planned, r.milestones];
        })
      ));
    }
  }

  function step(delta) {
    index = (index + delta + data.versions.length) % data.versions.length;
    render();
  }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    var p = document.getElementById("phasesPlay");
    if (p) p.textContent = "▶";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    var p = document.getElementById("phasesPlay");
    if (p) p.textContent = "⏸";
    timer = setInterval(function () { step(1); }, 1600);
  }

  var basis = box.getAttribute("data-basis") || "finish";
  fetch("/api/phases?basis=" + encodeURIComponent(basis))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      if (!d.versions || !d.versions.length || !d.years.length) {
        box.textContent = "No dated activities to bin on this basis.";
        return;
      }
      data = d; years = d.years; top = Math.max(1, d.max_total);
      index = 0;
      render();
      function on(id, fn) { var nd = document.getElementById(id); if (nd) nd.addEventListener("click", fn); }
      on("phasesPrev", function () { stopAuto(); step(-1); });
      on("phasesNext", function () { stopAuto(); step(1); });
      on("phasesPlay", toggleAuto);
    })
    .catch(function () { box.textContent = "Failed to load the year-phase data."; });
})();
