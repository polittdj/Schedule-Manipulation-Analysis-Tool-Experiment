/* Schedule Forensics — Bow Wave / CEI animated snapshot charts.
 *
 * Dependency-free SVG (no CDN — air-gap posture). Mimics the reference briefing chart:
 * per snapshot, a grouped monthly bar chart — gold "Baselined to Finish", blue "Scheduled
 * to Finish", green "Finished" — with a dashed data-date marker and the snapshot's CEI
 * callout. Prev/Next steps through snapshots; Auto-play flips through them like a movie
 * so the bow wave visibly pushes right.
 *
 * Item F: a "Running totals" toggle redraws the three series as cumulative finish curves
 * (running totals through each month, on a locked cumulative axis), and a focused Target
 * UID is marked where it is scheduled / actually finishes in each snapshot — so you can
 * watch one activity slide right frame to frame. Data: the local /api/cei endpoint.
 */
"use strict";

(function () {
  var box = document.getElementById("ceiChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var GOLD = "var(--warn)", BLUE = "var(--accent)", GREEN = "var(--ok)";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      // CSS variables are not valid in SVG presentation attributes; route them via style
      // so the charts recolor live when the light/dark theme switches.
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  // running total (cumulative sum) of a per-month series
  function cumulative(arr) {
    var out = [], sum = 0;
    for (var i = 0; i < arr.length; i++) { sum += arr[i]; out.push(sum); }
    return out;
  }

  var data = null, index = 0, timer = null, totals = false, cumTop = 1;

  function render() {
    var snap = data.snapshots[index];
    var months = data.months;
    document.getElementById("snapLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label;
    box.innerHTML = "";

    var W = 980, H = 360, padL = 34, padR = 12, padT = 44, padB = 42;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) {
      SFA11y.label(svg, "Bow wave — activity finishes by month (" + snap.label + ")" +
        (totals ? " — running totals" : ""));
    }
    var n = months.length;
    var slot = (W - padL - padR) / n;
    var barW = Math.max(1.5, Math.min(7, slot / 4));
    // LOCKED Y-axis: per-month uses the max bar across ALL snapshots; running-totals uses the
    // max cumulative total across ALL snapshots — either way held through the animation so the
    // bow wave's growth is visible, not normalized away.
    var top = totals ? cumTop : Math.max(1, data.max_count || 0);
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };
    var xc = function (i) { return padL + i * slot + slot / 2; };  // month-slot centre

    // title + CEI callout (the reference deck's "CEI - .36")
    var title = svgEl("text", { x: W / 2, y: 20, "text-anchor": "middle", fill: "var(--ink)", "font-size": 16, "font-weight": 600 });
    title.textContent = "Activity Finishes — As of " + snap.label + (totals ? " (running totals)" : "");
    svg.appendChild(title);
    if (snap.cei != null || snap.cei_planned != null) {
      var cei = svgEl("text", { x: W - padR, y: 22, "text-anchor": "end", "font-size": 18, "font-weight": 700,
        fill: snap.cei != null && snap.cei < 0.8 ? "var(--bad)" : "var(--ok)" });
      cei.textContent = "CEI – " + (snap.cei != null ? snap.cei.toFixed(2) : "n/a") +
        (snap.cei_period ? " (" + snap.cei_period + ")" : "");
      svg.appendChild(cei);
    }

    // y gridlines
    [0.25, 0.5, 0.75, 1].forEach(function (frac) {
      var gy = y(top * frac);
      svg.appendChild(svgEl("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: "var(--line)", "stroke-width": 1 }));
      var lab = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10 });
      lab.textContent = String(Math.round(top * frac));
      svg.appendChild(lab);
    });

    if (totals) {
      // running totals: three cumulative finish curves (gold/blue/green)
      [[snap.baselined, GOLD], [snap.scheduled, BLUE], [snap.finished, GREEN]].forEach(function (pair) {
        var cum = cumulative(pair[0]);
        var pts = cum.map(function (v, i) { return xc(i) + "," + y(v); });
        svg.appendChild(svgEl("polyline", { points: pts.join(" "), fill: "none", stroke: pair[1], "stroke-width": 2 }));
      });
    } else {
      // per-month grouped bars: gold/blue/green
      for (var i = 0; i < n; i++) {
        var x0 = xc(i);
        var series = [
          [snap.baselined[i], GOLD, -1.15],
          [snap.scheduled[i], BLUE, 0],
          [snap.finished[i], GREEN, 1.15],
        ];
        series.forEach(function (sd) {
          var v = sd[0];
          if (!v) return;
          var bx = x0 + sd[2] * barW - barW / 2;
          svg.appendChild(svgEl("rect", { x: bx, y: y(v), width: barW, height: y(0) - y(v), fill: sd[1] }));
          if (slot > 26) {
            var t = svgEl("text", { x: bx + barW / 2, y: y(v) - 3, "text-anchor": "middle", fill: "var(--ink)", "font-size": 9 });
            t.textContent = String(v);
            svg.appendChild(t);
          }
        });
      }
    }

    // month labels, thinned to avoid overlap (both modes)
    var step = Math.max(1, Math.ceil(n / 16));
    for (var j = 0; j < n; j++) {
      if (j % step === 0) {
        var ml = svgEl("text", { x: xc(j), y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + xc(j) + " " + (H - padB + 16) + ")" });
        ml.textContent = months[j];
        svg.appendChild(ml);
      }
    }

    // dashed data-date marker (right edge of the data-date month, as in the deck)
    if (snap.status_index != null) {
      var sx = padL + (snap.status_index + 1) * slot;
      svg.appendChild(svgEl("line", { x1: sx, y1: padT, x2: sx, y2: y(0), stroke: BLUE, "stroke-width": 2, "stroke-dasharray": "6 5" }));
      var sl = svgEl("text", { x: sx, y: padT - 4, "text-anchor": "middle", fill: BLUE, "font-size": 10 });
      sl.textContent = "data date";
      svg.appendChild(sl);
    }

    // item F: mark where the focused target activity lands this snapshot (scheduled + actual)
    function targetMark(idx, color, label, ytext) {
      if (idx == null) return;
      var mx = xc(idx);
      svg.appendChild(svgEl("line", { x1: mx, y1: padT, x2: mx, y2: y(0), stroke: color, "stroke-width": 2, "stroke-dasharray": "2 3" }));
      svg.appendChild(svgEl("path", { d: "M" + (mx - 5) + " " + (padT - 11) + " L" + (mx + 5) + " " + (padT - 11) + " L" + mx + " " + (padT - 3) + " Z", fill: color }));
      var t = svgEl("text", { x: mx + 6, y: ytext, fill: color, "font-size": 10, "font-weight": 600 });
      t.textContent = label;
      svg.appendChild(t);
    }
    if (data.target_uid != null) {
      targetMark(snap.target_scheduled_index, BLUE, "UID " + data.target_uid + " scheduled", padT - 13);
      targetMark(snap.target_finished_index, GREEN, "finished", padT + 2);
    }

    // legend
    var legend = [["Baselined to Finish", GOLD], ["Scheduled to Finish", BLUE], ["Finished", GREEN]];
    var lx = padL;
    legend.forEach(function (item) {
      svg.appendChild(svgEl("rect", { x: lx, y: H - 12, width: 10, height: 10, fill: item[1] }));
      var lt = svgEl("text", { x: lx + 14, y: H - 3, fill: "var(--muted)", "font-size": 11 });
      lt.textContent = item[0];
      svg.appendChild(lt);
      lx += 14 + item[0].length * 6 + 22;
    });

    box.appendChild(svg);
  }

  function step(delta) {
    index = (index + delta + data.snapshots.length) % data.snapshots.length;
    render();
  }

  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("autoPlay").textContent = "▶ Auto-play";
  }

  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    // A2: honor prefers-reduced-motion — advance one frame, don't auto-flip on a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    document.getElementById("autoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1600);
  }

  fetch("/api/cei")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      // locked cumulative axis: the largest running total any series reaches in any snapshot
      data.snapshots.forEach(function (s) {
        ["baselined", "scheduled", "finished"].forEach(function (k) {
          var sum = 0;
          s[k].forEach(function (v) { sum += v; });
          if (sum > cumTop) cumTop = sum;
        });
      });
      render();
      document.getElementById("prevSnap").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("nextSnap").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("autoPlay").addEventListener("click", toggleAuto);
      var cb = document.getElementById("ceiTotals");
      if (cb) cb.addEventListener("change", function () { totals = cb.checked; render(); });
    })
    .catch(function () { box.textContent = "Failed to load the bow-wave data."; });
})();
