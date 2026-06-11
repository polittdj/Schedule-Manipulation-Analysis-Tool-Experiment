/* Schedule Forensics — Bow Wave / CEI animated snapshot charts.
 *
 * Dependency-free SVG (no CDN — air-gap posture). Mimics the reference briefing chart:
 * per snapshot, a grouped monthly bar chart — gold "Baselined to Finish", blue "Scheduled
 * to Finish", green "Finished" — with a dashed data-date marker and the snapshot's CEI
 * callout. Prev/Next steps through snapshots; Auto-play flips through them like a movie
 * so the bow wave visibly pushes right. Data: the local /api/cei endpoint.
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

  var data = null, index = 0, timer = null;

  function maxCount(snap) {
    var m = 1;
    [snap.baselined, snap.scheduled, snap.finished].forEach(function (series) {
      series.forEach(function (v) { if (v > m) m = v; });
    });
    return m;
  }

  function render() {
    var snap = data.snapshots[index];
    var months = data.months;
    document.getElementById("snapLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label;
    box.innerHTML = "";

    var W = 980, H = 360, padL = 34, padR = 12, padT = 44, padB = 42;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var n = months.length;
    var slot = (W - padL - padR) / n;
    var barW = Math.max(1.5, Math.min(7, slot / 4));
    var top = maxCount(snap);
    var y = function (v) { return padT + (1 - v / top) * (H - padT - padB); };

    // title + CEI callout (the reference deck's "CEI - .36")
    var title = svgEl("text", { x: W / 2, y: 20, "text-anchor": "middle", fill: "var(--ink)", "font-size": 16, "font-weight": 600 });
    title.textContent = "Activity Finishes — As of " + snap.label;
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

    // bars: gold/blue/green per month
    for (var i = 0; i < n; i++) {
      var x0 = padL + i * slot + slot / 2;
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
      // month labels, thinned to avoid overlap
      var step = Math.ceil(n / 16);
      if (i % step === 0) {
        var ml = svgEl("text", { x: x0, y: H - padB + 16, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
          transform: "rotate(-35 " + x0 + " " + (H - padB + 16) + ")" });
        ml.textContent = months[i];
        svg.appendChild(ml);
      }
    }

    // dashed data-date marker
    if (snap.status_index != null) {
      // the dashed marker sits at the right edge of the data-date month (as in the deck)
      var sx = padL + (snap.status_index + 1) * slot;
      svg.appendChild(svgEl("line", { x1: sx, y1: padT, x2: sx, y2: y(0), stroke: BLUE, "stroke-width": 2, "stroke-dasharray": "6 5" }));
      var sl = svgEl("text", { x: sx, y: padT - 4, "text-anchor": "middle", fill: BLUE, "font-size": 10 });
      sl.textContent = "data date";
      svg.appendChild(sl);
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
    document.getElementById("autoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1600);
  }

  fetch("/api/cei")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      render();
      document.getElementById("prevSnap").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("nextSnap").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("autoPlay").addEventListener("click", toggleAuto);
    })
    .catch(function () { box.textContent = "Failed to load the bow-wave data."; });
})();
