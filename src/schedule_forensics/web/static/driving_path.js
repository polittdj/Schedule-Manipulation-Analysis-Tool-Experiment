/* Schedule Forensics — driving-path corridor animation (ADR-0096).
 *
 * Steps/plays through the loaded versions, drawing the driving corridor between two UIDs as a
 * scalable date-axis Gantt on an axis held FIXED across every version, so the corridor visibly
 * shifts as the schedule slips. Data is embedded in #dpData (computed server-side); activities
 * that ENTERED the corridor since the prior version are outlined. Dependency-free; nothing
 * leaves the machine.
 */
"use strict";

(function () {
  var mount = document.getElementById("dpChart");
  var dataEl = document.getElementById("dpData");
  if (!mount || !dataEl) return;

  var DAY_MS = 86400000;
  var payload = JSON.parse(dataEl.textContent);
  var versions = (payload && payload.versions) || [];
  if (!versions.length) return;

  var idx = versions.length - 1; // start on the newest version
  var px = 6; // pixels per calendar day
  var timer = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  // one date range across ALL versions, so the axis is shared and the bars move between frames
  var t0 = null, t1 = null;
  function span(ms) {
    if (ms === null || isNaN(ms)) return;
    t0 = Math.min(t0 === null ? Infinity : t0, ms);
    t1 = Math.max(t1 === null ? -Infinity : t1, ms);
  }
  versions.forEach(function (v) {
    (v.activities || []).forEach(function (a) {
      if (a.start) span(Date.parse(a.start));
      if (a.finish) span(Date.parse(a.finish));
    });
    if (v.data_date) span(Date.parse(v.data_date));
  });
  if (t0 === null || t1 === null) return;
  t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
  var x = function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); };

  function monthScale(width) {
    var scale = el("div", { class: "path-scale", style: "width:" + width + "px" });
    var d = new Date(t0); d.setDate(1);
    while (d.getTime() <= t1) {
      var tx = x(d.getTime());
      if (tx >= 0) {
        scale.appendChild(el("div", { class: "pv-tick", style: "left:" + tx + "px" }));
        scale.appendChild(el("div", {
          class: "pv-tick-label", style: "left:" + (tx + 3) + "px",
          text: (d.getMonth() + 1) + "/" + String(d.getFullYear()).slice(2),
        }));
      }
      d.setMonth(d.getMonth() + 1);
    }
    return scale;
  }

  function render() {
    var v = versions[idx];
    $("dpLabel").textContent = "Version " + (idx + 1) + "/" + versions.length + " — " + v.label +
      (v.data_date ? " (data date " + v.data_date + ")" : "") + " — " + v.status +
      (v.change_note ? " · " + v.change_note : "");
    mount.textContent = "";
    var acts = v.activities || [];
    if (!acts.length) {
      mount.appendChild(el("p", { class: "muted", text: "No driving corridor in this version." }));
      return;
    }
    var width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);

    var table = el("table", { class: "gantt-grid path-grid" });
    var head = el("tr");
    head.appendChild(el("th", { text: "UID" }));
    head.appendChild(el("th", { text: "Name" }));
    var thTime = el("th", { class: "path-timeline-head" });
    var scale = monthScale(width);
    if (v.data_date) {
      scale.appendChild(el("div", {
        class: "pv-now", style: "left:" + x(Date.parse(v.data_date)) + "px",
        title: "data date " + v.data_date,
      }));
    }
    thTime.appendChild(scale);
    head.appendChild(thTime);
    table.appendChild(head);

    acts.forEach(function (a) {
      var tr = el("tr");
      tr.appendChild(el("td", { text: String(a.uid) }));
      tr.appendChild(el("td", { class: "pv-name", text: a.name }));
      var cell = el("td", { class: "path-timeline" });
      var track = el("div", { class: "path-track", style: "width:" + width + "px" });
      if (v.data_date) {
        track.appendChild(el("div", { class: "pv-now", style: "left:" + x(Date.parse(v.data_date)) + "px" }));
      }
      var entered = a.entered ? " dp-entered" : "";
      if (a.start && a.finish) {
        if (a.is_milestone) {
          track.appendChild(el("div", {
            class: "g-ms tier-DRIVING" + entered, style: "left:" + x(Date.parse(a.finish)) + "px",
            title: a.name + " (milestone) " + a.finish + (a.entered ? " — entered" : ""),
          }));
        } else {
          var left = x(Date.parse(a.start));
          var w = Math.max(2, x(Date.parse(a.finish)) - left);
          track.appendChild(el("div", {
            class: "gantt-bar tier-DRIVING" + entered,
            style: "left:" + left + "px;width:" + w + "px",
            title: a.name + " — " + a.start + " → " + a.finish + (a.entered ? " (entered)" : ""),
          }));
        }
      }
      cell.appendChild(track);
      tr.appendChild(cell);
      table.appendChild(tr);
    });
    mount.appendChild(table);
  }

  function stopPlay() {
    if (timer) { clearInterval(timer); timer = null; $("dpPlay").innerHTML = "&#9654; Auto-play"; }
  }
  function step(delta) { idx = (idx + delta + versions.length) % versions.length; render(); }

  $("dpPrev").addEventListener("click", function () { stopPlay(); step(-1); });
  $("dpNext").addEventListener("click", function () { stopPlay(); step(1); });
  $("dpPlay").addEventListener("click", function () {
    if (timer) { stopPlay(); return; }
    idx = 0; render(); $("dpPlay").innerHTML = "&#9208; Pause";
    timer = setInterval(function () {
      if (idx >= versions.length - 1) { stopPlay(); return; }
      step(1);
    }, 1100);
  });
  $("dpZoomIn").addEventListener("click", function () { px = Math.min(40, px + 2); render(); });
  $("dpZoomOut").addEventListener("click", function () { px = Math.max(1, px - 2); render(); });

  render();
})();
