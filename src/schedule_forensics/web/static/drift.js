/* Schedule Forensics — forecast-drift animation (Bow-Wave-style stepper).
 *
 * Dependency-free SVG (no CDN — air-gap posture). Steps through the loaded versions
 * (oldest first); each frame plots that version's three finish forecasts — Schedule
 * logic (CPM), Completion-rate, Earned-schedule — as labeled markers on a LOCKED date
 * axis spanning every version's forecasts/data dates/baseline finishes, so the time
 * scale is held fixed and the forecasts visibly drift right as the project progresses.
 * The prior version's markers stay as a faint trail. Data: the local /api/forecast.
 */
"use strict";

(function () {
  var box = document.getElementById("driftChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var DAY = 86400000;
  // lane color per forecast method id (theme variables; routed via style by svgEl)
  var COLORS = { cpm: "var(--accent)", rate: "var(--ok)", earned_schedule: "var(--bad)" };

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  var data = null, index = 0, timer = null, methods = [], lo = 0, hi = 1;

  function render() {
    var versions = data.versions;
    var v = versions[index];
    document.getElementById("driftLabel").textContent =
      (index + 1) + " / " + versions.length + " — " + v.label +
      (v.as_of ? " (data date " + v.as_of + ")" : "");
    box.innerHTML = "";

    var W = 980, H = 80 + methods.length * 64, padL = 12, padR = 14, padT = 44, padB = 36;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var x = function (ms) { return padL + ((ms - lo) / (hi - lo)) * (W - padL - padR); };

    var title = svgEl("text", { x: W / 2, y: 20, "text-anchor": "middle", fill: "var(--ink)", "font-size": 16, "font-weight": 600 });
    title.textContent = "Finish forecasts — as of " + (v.as_of || v.label);
    svg.appendChild(title);

    // Adaptive date ticks along the locked axis: a year-only scale was empty/unreadable when
    // every forecast sits inside a year or two. Pick year / quarter / month granularity by the
    // span so a short window still shows a meaningful, readable scale (≈ a dozen ticks).
    var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var months = (hi - lo) / DAY / 30.44;
    var stepMonths = months > 48 ? 12 : months > 16 ? 3 : months > 8 ? 2 : 1;
    var d = new Date(lo); d.setDate(1); d.setHours(0, 0, 0, 0);
    if (stepMonths === 12) d.setMonth(0);
    else if (stepMonths === 3) d.setMonth(Math.floor(d.getMonth() / 3) * 3);
    while (d.getTime() <= hi) {
      var tx = x(d.getTime());
      if (tx >= padL && tx <= W - padR) {
        svg.appendChild(svgEl("line", { x1: tx, y1: padT, x2: tx, y2: H - padB, stroke: "var(--line)", "stroke-width": 1 }));
        var lab = svgEl("text", { x: tx + 2, y: H - padB + 14, fill: "var(--muted)", "font-size": 10 });
        lab.textContent = stepMonths === 12
          ? String(d.getFullYear())
          : MON[d.getMonth()] + " " + ("" + d.getFullYear()).slice(2);
        svg.appendChild(lab);
      }
      d.setMonth(d.getMonth() + stepMonths);
    }

    // baseline planned finish — a fixed gold reference the forecasts drift past
    if (v.planned_finish) {
      var px = x(Date.parse(v.planned_finish));
      svg.appendChild(svgEl("line", { x1: px, y1: padT, x2: px, y2: H - padB, stroke: "var(--warn)", "stroke-width": 2, "stroke-dasharray": "5 4" }));
      var pl = svgEl("text", { x: px, y: padT - 4, "text-anchor": "middle", fill: "var(--warn)", "font-size": 10 });
      pl.textContent = "baseline " + v.planned_finish;
      svg.appendChild(pl);
    }
    // data-date marker
    if (v.as_of) {
      var ax = x(Date.parse(v.as_of));
      svg.appendChild(svgEl("line", { x1: ax, y1: padT, x2: ax, y2: H - padB, stroke: "var(--muted)", "stroke-width": 1.5, "stroke-dasharray": "2 3" }));
    }

    var prior = index > 0 ? versions[index - 1] : null;
    methods.forEach(function (m, li) {
      var ly = padT + 14 + li * 64;
      svg.appendChild(svgEl("line", { x1: padL, y1: ly + 18, x2: W - padR, y2: ly + 18, stroke: "var(--line)", "stroke-width": 1 }));
      var name = svgEl("text", { x: padL, y: ly + 2, fill: "var(--muted)", "font-size": 11 });
      name.textContent = m.name;
      svg.appendChild(name);
      var color = COLORS[m.id] || "var(--ink)";
      // faint trail: the prior version's forecast for this method
      if (prior && prior.forecasts[m.id]) {
        var gx = x(Date.parse(prior.forecasts[m.id]));
        svg.appendChild(svgEl("circle", { cx: gx, cy: ly + 18, r: 4, fill: color, opacity: 0.28 }));
      }
      var iso = v.forecasts[m.id];
      if (iso) {
        var cx = x(Date.parse(iso));
        // an arrow from the prior marker shows the drift direction/magnitude
        if (prior && prior.forecasts[m.id]) {
          var gx2 = x(Date.parse(prior.forecasts[m.id]));
          if (Math.abs(cx - gx2) > 1) {
            svg.appendChild(svgEl("line", { x1: gx2, y1: ly + 18, x2: cx, y2: ly + 18, stroke: color, "stroke-width": 1.5, opacity: 0.5 }));
          }
        }
        svg.appendChild(svgEl("circle", { cx: cx, cy: ly + 18, r: 6, fill: color }));
        var val = svgEl("text", { x: cx, y: ly + 36, "text-anchor": "middle", fill: "var(--ink)", "font-size": 11 });
        val.textContent = iso;
        svg.appendChild(val);
      } else {
        var na = svgEl("text", { x: padL + 90, y: ly + 22, fill: "var(--muted)", "font-size": 11 });
        na.textContent = "— (inputs missing)";
        svg.appendChild(na);
      }
    });

    box.appendChild(svg);

    var leg = document.createElement("div");
    leg.className = "chart-legend";
    methods.forEach(function (m) {
      var cell = document.createElement("span");
      cell.className = "chart-legend-item";
      var sw = document.createElement("span");
      sw.className = "chart-swatch";
      sw.style.background = COLORS[m.id] || "var(--ink)";
      var lab = document.createElement("span");
      lab.textContent = m.name;
      cell.appendChild(sw);
      cell.appendChild(lab);
      leg.appendChild(cell);
    });
    var refs = document.createElement("span");
    refs.className = "chart-legend-item";
    refs.style.color = "var(--muted)";
    refs.textContent = "— gold dashed = baseline finish · grey dotted = data date";
    leg.appendChild(refs);
    box.appendChild(leg);
  }

  function step(delta) {
    index = (index + delta + data.versions.length) % data.versions.length;
    render();
  }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("driftPlay").textContent = "▶ Auto-play";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    // A2: honor prefers-reduced-motion — advance one frame, don't auto-flip on a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    document.getElementById("driftPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1600);
  }

  fetch("/api/forecast")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      if (!d.versions || d.versions.length < 2 || !d.axis || !d.axis.min) return;
      data = d;
      methods = d.methods || [];
      lo = Date.parse(d.axis.min); hi = Date.parse(d.axis.max);
      if (!(hi > lo)) { hi = lo + 30 * DAY; }
      var pad = (hi - lo) * 0.04;  // keep edge markers off the frame border
      lo -= pad; hi += pad;
      index = 0;
      render();
      document.getElementById("prevDrift").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("nextDrift").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("driftPlay").addEventListener("click", toggleAuto);
    })
    .catch(function () { box.textContent = "Failed to load the forecast-drift data."; });
})();
