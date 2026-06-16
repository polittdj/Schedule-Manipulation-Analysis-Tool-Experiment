/* Schedule Forensics — cross-version quality drill-down + animation (M18 item 8).
 *
 * Dependency-free SVG (no CDN, no external fetch — air-gap posture). A Prev/Next/
 * Auto-play stepper over the loaded versions (oldest first) renders, on a LOCKED y-axis,
 * the count of offending activities for every Acumen section-A quality metric in that
 * version, so bar heights stay comparable frame to frame. Selecting a metric lists the
 * exact activities (UID + name) behind its number in the current version. Data: the
 * local /api/trend.
 */
"use strict";

(function () {
  var bars = document.getElementById("qualBars");
  var drill = document.getElementById("qualDrill");
  var sel = document.getElementById("qualMetric");
  if (!bars || !drill || !sel) return;
  var NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        node.style[k] = attrs[k];
      } else node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  function shortLabel(v, i) {
    var s = String(v.label || "").replace(/\.(mpp|xml|xer|json|mspdi)$/i, "");
    var parts = s.split(/[\\/]/);
    s = parts[parts.length - 1] || s;
    if (s.length > 20) s = s.slice(0, 19) + "…";
    return s || (v.status_date || ("v" + (i + 1)));
  }

  function metricShort(name) {
    return name.length > 12 ? name.slice(0, 11) + "…" : name;
  }

  var data = null, metrics = [], versions = [], current = 0, selId = null, maxCount = 1, timer = null;

  function renderBars() {
    bars.innerHTML = "";
    var v = versions[current];
    document.getElementById("qualLabel").textContent =
      (current + 1) + " / " + versions.length + " — " + shortLabel(v, current) +
      (v.status_date ? " (data date " + v.status_date + ")" : "");

    var W = 940, H = 300, padL = 38, padR = 14, padT = 22, padB = 96;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var plotH = H - padT - padB;
    var n = metrics.length;
    var slot = (W - padL - padR) / n;
    var bw = Math.min(64, slot * 0.6);

    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var yv = padT + plotH * (1 - f);
      svg.appendChild(svgEl("line", {
        x1: padL, y1: yv, x2: W - padR, y2: yv,
        stroke: "var(--line)", "stroke-width": 0.5, "stroke-dasharray": "2,2",
      }));
      var t = svgEl("text", {
        x: padL - 6, y: yv + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 10,
      });
      t.textContent = Math.round(f * maxCount);
      svg.appendChild(t);
    });

    metrics.forEach(function (m, i) {
      var q = data.quality[m];
      var cnt = (q.counts && q.counts[current]) || 0;
      var cx = padL + slot * i + slot / 2;
      var bh = maxCount > 0 ? (cnt / maxCount) * plotH : 0;
      var isSel = m === selId;
      var rect = svgEl("rect", {
        x: cx - bw / 2, y: padT + plotH - bh, width: bw,
        height: Math.max(bh, cnt > 0 ? 1 : 0),
        rx: 2, "class": "qual-bar", fill: isSel ? "var(--accent)" : "var(--beyond)",
      });
      rect.addEventListener("click", function () { sel.value = m; selId = m; render(); });
      svg.appendChild(rect);
      var val = svgEl("text", {
        x: cx, y: padT + plotH - bh - 5, "text-anchor": "middle",
        fill: isSel ? "var(--ink)" : "var(--muted)", "font-size": 11,
        "font-weight": isSel ? 700 : 400,
      });
      val.textContent = String(cnt);
      svg.appendChild(val);
      var lab = svgEl("text", {
        x: cx, y: H - padB + 14, "text-anchor": "end",
        fill: isSel ? "var(--ink)" : "var(--muted)", "font-size": 11, "class": "qual-mlabel",
        transform: "rotate(-40 " + cx + " " + (H - padB + 14) + ")",
      });
      lab.textContent = metricShort(q.name);
      lab.addEventListener("click", function () { sel.value = m; selId = m; render(); });
      svg.appendChild(lab);
    });
    bars.appendChild(svg);
  }

  function renderDrill() {
    var q = data.quality[selId];
    drill.innerHTML = "";
    var h = document.createElement("h3");
    h.textContent = q.name + " — " + shortLabel(versions[current], current);
    drill.appendChild(h);
    var meta = document.createElement("p");
    meta.className = "muted qual-meta";
    if (q.lower_is_better === null) {
      meta.textContent = "Neutral ratio (value " + q.values[current] +
        ") — no specific offending activities.";
      drill.appendChild(meta);
      return;
    }
    var offs = (q.offenders && q.offenders[current]) || [];
    var cnt = (q.counts && q.counts[current]) || 0;
    meta.textContent = cnt === 0
      ? "No offending activities in this version."
      : cnt + " offending " + (cnt === 1 ? "activity" : "activities") + " in this version:";
    drill.appendChild(meta);
    if (!offs.length) return;
    var ul = document.createElement("ul");
    ul.className = "qual-offender-list";
    offs.forEach(function (o) {
      var li = document.createElement("li");
      var uid = document.createElement("span");
      uid.className = "ev-uid";
      uid.textContent = "UID " + o.uid;
      li.appendChild(uid);
      li.appendChild(document.createTextNode(" " + (o.name || "")));
      ul.appendChild(li);
    });
    drill.appendChild(ul);
  }

  function render() { renderBars(); renderDrill(); }

  function step(delta) {
    current = (current + delta + versions.length) % versions.length;
    render();
  }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("qualPlay").textContent = "▶ Auto-play";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    document.getElementById("qualPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1600);
  }

  fetch("/api/trend")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      if (!d.quality || !d.versions || d.versions.length < 2) return;
      data = d;
      versions = d.versions;
      metrics = Object.keys(d.quality);
      if (!metrics.length) return;
      var best = metrics[0], bestSum = -1;
      metrics.forEach(function (m) {
        (d.quality[m].counts || []).forEach(function (c) { if (c > maxCount) maxCount = c; });
        var opt = document.createElement("option");
        opt.value = m;
        opt.textContent = d.quality[m].name;
        sel.appendChild(opt);
        var sum = (d.quality[m].counts || []).reduce(function (a, b) { return a + b; }, 0);
        if (sum > bestSum) { bestSum = sum; best = m; }
      });
      selId = best;
      sel.value = best;
      current = 0;
      render();
      sel.addEventListener("change", function () { selId = sel.value; render(); });
      document.getElementById("qualPrev").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("qualNext").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("qualPlay").addEventListener("click", toggleAuto);
    })
    .catch(function () { bars.textContent = "Failed to load quality drill-down data."; });
})();
